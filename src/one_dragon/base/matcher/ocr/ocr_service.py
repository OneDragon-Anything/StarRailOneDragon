import time
from dataclasses import dataclass

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResultList
from one_dragon.base.matcher.ocr.ocr_match_result import OcrMatchResult
from one_dragon.base.matcher.ocr.ocr_matcher import OcrMatcher
from one_dragon.utils import cal_utils, cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log


@dataclass(frozen=True)
class OcrCacheEntry:
    """OCR缓存条目"""
    image_id: int  # 图片在内存中的ID
    image: MatLike  # 将图片也缓存起来 防止旧图片没引用被回收 导致出现新图片ID与旧图片重复
    ocr_result_list: list[OcrMatchResult]  # OCR识别结果
    create_time: float  # 创建时间
    color_range: list[list[int]] | None  # 颜色范围
    rect: Rect | None = None  # 识别区域
    crop_first: bool = False  # 先裁剪再识别 用于从连续文本中只提取特定区域的文本


#: color_range 裁剪路径的扩边像素(1080p 基准):rect 过滤阈值 70% 允许结果外溢
#: rect 外 30%,margin 需覆盖此外溢 + det 贴边漏检余量;量值按样本帧对拍校准
#(2026-09-03,hp/gold/level/board 等现役 color_range 区与全图路径逐 token 一致)。
_COLOR_CROP_MARGIN = 15


class OcrService:
    """
    OCR服务
    - 提供缓存
    - 提供并发识别 (未实现)

    缺点：
    - 全图识别后，识别得到的文本无法按选定区域进行精准切割。
      - 例如 [图标]真实文本，会将图标错误识别成某些文本拼在一起，无法通过选择区域精准识别真实文本部分.
    """

    def __init__(
        self,
        ocr_matcher: OcrMatcher,
        max_cache_size: int = 32,
    ):
        """
        初始化OCR服务

        Args:
            ocr_matcher: OCR匹配器实例
            max_cache_size: 最大缓存条目数(color_range 裁剪化后按 (图片, 颜色, 区域)
                分条,单帧 heavy 可有 4-6 条,原值 5 会同帧自逐出,放大到 32;
                条目只持图片引用+结果列表,内存代价可忽略)
        """
        self.ocr_matcher = ocr_matcher
        self.max_cache_size = max_cache_size

        # 缓存存储：key=图片ID，value为缓存条目
        self._cache: dict[int, list[OcrCacheEntry]] = {}
        self._cache_list: list[OcrCacheEntry] = []

    def _clean_expired_cache(self) -> None:
        """
        清除过期缓存
        Returns:

        """
        while len(self._cache_list) > self.max_cache_size:
            oldest_entry = self._cache_list.pop(0)
            image_id = oldest_entry.image_id

            if image_id in self._cache:
                # 从与 image_id 关联的列表中移除特定的条目
                try:
                    self._cache[image_id].remove(oldest_entry)
                    # 如果这个 image_id 的列表现在为空，则从字典中移除该键
                    if not self._cache[image_id]:
                        self._cache.pop(image_id)
                except ValueError:
                    # 在罕见的并发场景下，如果条目已经被移除，可能会发生这种情况，但可以安全地忽略。
                    pass

    def _apply_color_filter(self, image: MatLike, color_range: list[list[int]]) -> MatLike:
        """
        应用颜色过滤，最后返回RGB格式的黑白图，用于OCR。
        不返回原图颜色是因为，如果使用黑色过滤，最后得到会是一个全黑的图片，无法进行识别。

        Args:
            image: 输入图片
            color_range: 颜色范围 [[lower], [upper]]

        Returns:
            过滤后的图片
        """
        if color_range is None:
            return image

        # 应用颜色范围过滤
        mask = cv2.inRange(image, np.array(color_range[0]), np.array(color_range[1]))
        return cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)

    def _get_ocr_result_list_from_cache(
        self,
        image: MatLike,
        color_range: list[list[int]] | None = None,
        rect: Rect | None = None,
        crop_first: bool = False,
    ) -> OcrCacheEntry | None:
        """
        从缓存中获取OCR结果
        Args:
            image: 输入图片
            color_range: 颜色范围过滤 [[lower], [upper]]
            rect: 指定区域。识别结果后，筛选在指定区域中出现的结果，即文本所在的矩形有70%以上在指定区域内
            crop_first: 先裁剪再识别 用于从连续文本中只提取特定区域的文本

        Returns:
            缓存条目
        """
        image_id = id(image)
        cache_list = self._cache.get(image_id)
        if cache_list is None:
            return None

        # 缓存 key 含 rect 的两种形态:crop_first(旧);color_range+rect 裁剪化路径
        # (结果按区域裁剪 OCR,异区结果不同,必须分条,防误命中)。color_range 无 rect
        # 的全图路径保持跨 rect 复用(同一次全图识别可按不同 rect 过滤)。
        need_rect_key = crop_first or (color_range is not None and rect is not None)

        for cache_entry in cache_list:
            # Python 的列表 == 操作符会自动处理嵌套结构和值的比较 包括None
            if cache_entry.color_range != color_range:
                continue
            if cache_entry.crop_first != crop_first:
                continue
            if need_rect_key and cache_entry.rect != rect:
                continue
            return cache_entry

        return None

    def get_ocr_result_list(
        self,
        image: MatLike,
        color_range: list[list[int]] | None = None,
        rect: Rect | None = None,
        crop_first: bool = False,
        threshold: float = 0,
        merge_line_distance: float = -1,
    ) -> list[OcrMatchResult]:
        """
        获取全图OCR结果，优先从缓存获取

        color_range + rect 组合走裁剪化路径(纯性能,对外语义不变):小图过滤+OCR
        后坐标映射回全图,返回结果与全图路径一致;缓存 key 含 rect(异区不误命中)。

        Args:
            image: 输入图片
            color_range: 颜色范围过滤 [[lower], [upper]]
            rect: 指定区域。识别结果后，筛选在指定区域中出现的结果，即文本所在的矩形有70%以上在指定区域内
            crop_first: 先裁剪再识别 用于从连续文本中只提取指定区域的文本。默认 False：
                全图 OCR 后按 rect 过滤，结果按 id(image) 缓存、同帧多区域查询复用同一次识别；
                True 为按 rect 先裁剪再 OCR，弃缓存复用且小/紧框裁剪后文字检测器易漏字
            threshold: OCR阈值
            merge_line_distance: 行合并距离

        Returns:
            ocr_result_list: OCR识别结果列表
        """
        # 生成缓存键
        image_id = id(image)

        cache_entity = self._get_ocr_result_list_from_cache(
            image=image,
            color_range=color_range,
            rect=rect,
            crop_first=crop_first,
        )

        # 检查缓存
        if cache_entity is not None:
            ocr_result_list = cache_entity.ocr_result_list
        else:
            bus = getattr(self.ocr_matcher, 'overlay_debug_bus', None)
            if crop_first and rect is not None:
                # 先裁原图再过滤:inRange 是逐像素算子,先裁后滤与旧「先滤全图再裁」
                # 结果一致,省全图 inRange(纯性能)。小/紧框裁剪后 det 易漏字是
                # 调用方自担的既有语义,不在本路径扩边。
                crop_image, crop_rect = cv2_utils.crop_image(image, rect)
                processed_image = self._apply_color_filter(crop_image, color_range)
                if bus is not None:
                    bus.set_crop_offset(crop_rect.x1, crop_rect.y1)
                ocr_result_list = self.ocr_matcher.ocr(
                    crop_image,
                    threshold,
                    merge_line_distance,
                )
                if bus is not None:
                    bus.reset_crop_offset()
                for ocr_result in ocr_result_list:
                    ocr_result.add_offset(crop_rect.left_top)
            elif color_range is not None and rect is not None:
                # color_range 裁剪化路径(纯性能,语义不变):全图 inRange + 全图 OCR
                # 换成 rect+margin 小图过滤 + 小图 OCR(10-30ms 级),结果坐标加裁剪
                # 偏移映射回全图坐标系,对外返回语义与全图路径一致。margin 防贴边
                # 文字被切(crop_image 自带越界钳制)。
                crop_image, crop_rect = cv2_utils.crop_image(
                    image,
                    Rect(rect.x1 - _COLOR_CROP_MARGIN, rect.y1 - _COLOR_CROP_MARGIN,
                         rect.x2 + _COLOR_CROP_MARGIN, rect.y2 + _COLOR_CROP_MARGIN))
                processed_image = self._apply_color_filter(crop_image, color_range)
                if bus is not None:
                    bus.set_crop_offset(crop_rect.x1, crop_rect.y1)
                ocr_result_list = self.ocr_matcher.ocr(
                    processed_image,
                    threshold,
                    merge_line_distance,
                )
                if bus is not None:
                    bus.reset_crop_offset()
                for ocr_result in ocr_result_list:
                    ocr_result.add_offset(crop_rect.left_top)
            else:
                # 应用颜色过滤
                processed_image = self._apply_color_filter(image, color_range)

                # 执行OCR
                ocr_result_list = self.ocr_matcher.ocr(processed_image, threshold, merge_line_distance)

            # 存储到缓存
            cache_entry = OcrCacheEntry(
                ocr_result_list=ocr_result_list,
                create_time=time.time(),
                color_range=color_range,
                image_id=image_id,
                image=image,
                rect=rect,
                crop_first=crop_first,
            )
            if image_id not in self._cache:
                self._cache[image_id] = []
            self._cache[image_id].append(cache_entry)
            self._cache_list.append(cache_entry)
            self._clean_expired_cache()

        if rect is not None:
            # 过滤出指定区域内的结果
            area_result_list: list[OcrMatchResult] = []

            for ocr_result in ocr_result_list:
                # 检查匹配结果是否和指定区域重叠
                if cal_utils.cal_overlap_percent(ocr_result.rect, rect, base=ocr_result.rect) > 0.7:
                    area_result_list.append(ocr_result)

            return area_result_list
        else:
            return ocr_result_list

    def get_ocr_result_map(
        self,
        image: MatLike,
        color_range: list[list[int]] | None = None,
        rect: Rect | None = None,
        crop_first: bool = False,
        threshold: float = 0,
        merge_line_distance: float = -1,
    ) -> dict[str, MatchResultList]:
        """"
        获取全图OCR结果，优先从缓存获取

        Args:
            image: 输入图片
            color_range: 颜色范围过滤 [[lower], [upper]]
            rect: 指定区域。识别结果后，筛选在指定区域中出现的结果，即文本所在的矩形有70%以上在指定区域内
            crop_first: 先裁剪再识别 用于从连续文本中只提取特定区域的文本
            threshold: OCR阈值
            merge_line_distance: 行合并距离

        Returns:
            ocr_result_map: key=识别文本 value=识别结果列表
        """
        ocr_result_list = self.get_ocr_result_list(
            image=image,
            color_range=color_range,
            rect=rect,
            crop_first=crop_first,
            threshold=threshold,
            merge_line_distance=merge_line_distance
        )
        return self.convert_list_to_map(ocr_result_list)

    def convert_list_to_map(self, ocr_result_list: list[OcrMatchResult]) -> dict[str, MatchResultList]:
        """
        转换OCR识别结果 list -> map
        Args:
            ocr_result_list: OCR识别结果列表

        Returns:
            ocr_result_map: key=识别文本 value=识别结果列表
        """
        result_map: dict[str, MatchResultList] = {}
        for mr in ocr_result_list:
            word: str = mr.data
            if word not in result_map:
                result_map[word] = MatchResultList(only_best=False)
            result_map[word].append(mr, auto_merge=False)
        return result_map

    def find_text_in_area(
        self,
        image: MatLike,
        rect: Rect,
        crop_first: bool,
        target_text: str,
        color_range: list[list[int]] = None,
        threshold: float = 0.6
    ) -> bool:
        """
        在指定区域内查找目标文本

        Args:
            image: 输入图片
            rect: 目标区域
            crop_first: 先裁剪再识别 用于从连续文本中只提取特定区域的文本
            target_text: 要查找的文本
            color_range: 颜色范围过滤
            threshold: 文本匹配阈值

        Returns:
            是否找到目标文本
        """
        ocr_result_list: list[OcrMatchResult] = self.get_ocr_result_list(
            image=image,
            rect=rect,
            crop_first=crop_first,
            color_range=color_range,
        )
        ocr_word_list: list[str] = [i.data for i in ocr_result_list]

        target_word = gt(target_text, 'game')
        target_idx = str_utils.find_best_match_by_difflib(target_word, ocr_word_list, cutoff=threshold)
        return target_idx is not None and target_idx >= 0

    def clear_cache(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        log.debug("OCR缓存已清空")
