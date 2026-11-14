from __future__ import annotations

import logging
import time
from enum import Enum
from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.screen.screen_area import ScreenArea
from one_dragon.base.screen.screen_info import ScreenInfo
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    from one_dragon.base.operation.one_dragon_context import OneDragonContext


class OcrClickResultEnum(Enum):

    OCR_CLICK_SUCCESS = 1  # OCR并点击成功
    OCR_CLICK_FAIL = 0  # OCR成功但点击失败 基本不会出现
    OCR_CLICK_NOT_FOUND = -1  # OCR找不到目标
    AREA_NO_CONFIG = -2  # 区域配置找不到


class FindAreaResultEnum(Enum):

    TRUE = 1  # 找到了
    FALSE = 0  # 找不到
    AREA_NO_CONFIG = -2  # 区域配置找不到


def _area_log_key(screen_name: str | None, area: ScreenArea) -> str:
    """B 组 debug 日志的区域上下文:有画面名时 '<画面.区域>';旧调用方不传画面名时退化为裸区域名。"""
    return f'{screen_name}.{area.area_name}' if screen_name is not None else area.area_name


def _lcs_ratio_of(target_text: str, ocr_text: str) -> float:
    """LCS 长度占目标文本长度的比例,与 str_utils.find_by_lcs 的判定分母同口径。"""
    if len(target_text) == 0:
        return 0.0
    return str_utils.longest_common_subsequence_length(
        target_text.lower(), ocr_text.lower()) / len(target_text)


def find_area(
    ctx: OneDragonContext,
    screen: MatLike,
    screen_name: str,
    area_name: str,
    crop_first: bool = False,
) -> FindAreaResultEnum:
    """
    游戏截图中 是否能找到对应的区域
    Args:
        ctx: 上下文
        screen: 游戏截图
        screen_name: 画面名称
        area_name: 区域名称
        crop_first: 在传入区域时 是否先裁剪再进行文本识别

    Returns:
        bool: 是否可以匹配到指定区域
    """
    area: ScreenArea = ctx.screen_loader.get_area(screen_name, area_name)
    if area is None:
        # 运行时 screen_loader 只加载 _od_merged.yml;代码引用的画面/区域名若
        # 未随 merged 再生(改名后未重生成),get_area 静默 None → 分发分支被
        # 当成「未命中」跳过(实机卡死级事故形态)。显式告警区分
        # 「配置缺失」与「画面上没找到」。
        log.warning('区域未配置(画面名或 area 名不在运行时 screen_info 中): %s.%s',
                    screen_name, area_name)
        return FindAreaResultEnum.AREA_NO_CONFIG
    result = find_area_in_screen(ctx, screen, area, crop_first, screen_name=screen_name)
    log.debug('find_area %s.%s: %s', screen_name, area_name,
              '命中' if result == FindAreaResultEnum.TRUE else '未命中')
    return result


def find_area_binary(
    ctx: OneDragonContext,
    screen: MatLike,
    screen_name: str,
    area_name: str,
    binary_threshold: int = 127,
    crop_first: bool = False,
) -> FindAreaResultEnum:
    """
    使用二值化图像在游戏截图中查找区域
    Args:
        ctx: 上下文
        screen: 游戏截图
        screen_name: 画面名称
        area_name: 区域名称
        binary_threshold: 二值化阈值，默认为127
        crop_first: 在传入区域时 是否先裁剪再进行识别

    Returns:
        FindAreaResultEnum: 是否可以匹配到指定区域
    """
    area: ScreenArea = ctx.screen_loader.get_area(screen_name, area_name)
    if area is None:
        log.warning('区域未配置(画面名或 area 名不在运行时 screen_info 中): %s.%s',
                    screen_name, area_name)
        return FindAreaResultEnum.AREA_NO_CONFIG
    result = find_area_in_screen_binary(ctx, screen, area, binary_threshold, crop_first,
                                        screen_name=screen_name)
    log.debug('find_area %s.%s: %s', screen_name, area_name,
              '命中' if result == FindAreaResultEnum.TRUE else '未命中')
    return result


def find_area_in_screen_binary(
    ctx: OneDragonContext,
    screen: MatLike,
    area: ScreenArea,
    binary_threshold: int = 127,
    crop_first: bool = False,
    screen_name: str | None = None,
) -> FindAreaResultEnum:
    """
    使用二值化图像在截图中查找区域
    Args:
        ctx: 上下文
        screen: 游戏截图
        area: 区域
        binary_threshold: 二值化阈值，默认为127
        crop_first: 在传入区域时 是否先裁剪再进行识别
        screen_name: 画面名称 仅用于 debug 日志上下文 不传时日志只打区域名

    Returns:
        FindAreaResultEnum: 是否可以匹配到指定区域
    """
    if area is None:
        return FindAreaResultEnum.AREA_NO_CONFIG

    area_key = _area_log_key(screen_name, area)

    # 对屏幕进行二值化处理
    binary_screen = cv2_utils.to_binary(screen, threshold=binary_threshold)

    find: bool = False
    if area.is_text_area:
        ocr_result_list = ctx.ocr_service.get_ocr_result_list(
            image=binary_screen,
            rect=area.rect,
            color_range=area.color_range,
            crop_first=crop_first,
        )

        target_text = gt(area.text, 'game')
        for ocr_result in ocr_result_list:
            hit = str_utils.find_by_lcs(target_text, ocr_result.data, percent=area.lcs_percent)
            if log.isEnabledFor(logging.DEBUG):
                # lcs 值与 find_by_lcs 同口径(LCS 长度占目标文本长度的比例),日志值与判定结果才自洽
                lcs_ratio = _lcs_ratio_of(target_text, ocr_result.data)
                log.debug('find_area %s: OCR"%s" vs "%s" lcs=%.2f/%.2f → %s',
                          area_key, ocr_result.data, target_text, lcs_ratio,
                          area.lcs_percent, '命中' if hit else '未命中')
            if hit:
                find = True
                break
    elif area.is_template_area:
        # 裁剪区域
        rect = area.rect

        # 使用二值化模板匹配
        mrl = ctx.tm.crop_and_match_template_binary(
            binary_screen,
            rect,
            area.template_sub_dir,
            area.template_id,
            threshold=area.template_match_threshold,
            binary_threshold=binary_threshold,
        )
        find = mrl.max is not None
        # 低于阈值时 mrl.max 为 None,原始 conf 已被 cv2_utils.match_template 过滤,日志打 '-'
        log.debug('find_area %s: 模板%s conf=%s/%.2f → %s',
                  area_key, area.template_id,
                  f'{mrl.max.confidence:.2f}' if mrl.max is not None else '-',
                  area.template_match_threshold, '命中' if find else '未命中')

    return FindAreaResultEnum.TRUE if find else FindAreaResultEnum.FALSE


def find_area_in_screen(
    ctx: OneDragonContext,
    screen: MatLike,
    area: ScreenArea,
    crop_first: bool = False,
    screen_name: str | None = None,
) -> FindAreaResultEnum:
    """
    游戏截图中 是否能找到对应的区域

    Args:
        ctx: 上下文
        screen: 游戏截图
        area: 区域
        crop_first: 在传入区域时 是否先裁剪再进行文本识别
        screen_name: 画面名称 仅用于 debug 日志上下文 不传时日志只打区域名

    Returns:
        bool: 是否可以匹配到指定区域
    """
    if area is None:
        return FindAreaResultEnum.AREA_NO_CONFIG

    area_key = _area_log_key(screen_name, area)

    find: bool = False
    if area.is_text_area:
        ocr_result_list = ctx.ocr_service.get_ocr_result_list(
            image=screen,
            rect=area.rect,
            color_range=area.color_range,
            crop_first=crop_first,
        )

        target_text = gt(area.text, 'game')
        for ocr_result in ocr_result_list:
            hit = str_utils.find_by_lcs(target_text, ocr_result.data, percent=area.lcs_percent)
            if log.isEnabledFor(logging.DEBUG):
                # lcs 值与 find_by_lcs 同口径(LCS 长度占目标文本长度的比例),日志值与判定结果才自洽
                lcs_ratio = _lcs_ratio_of(target_text, ocr_result.data)
                log.debug('find_area %s: OCR"%s" vs "%s" lcs=%.2f/%.2f → %s',
                          area_key, ocr_result.data, target_text, lcs_ratio,
                          area.lcs_percent, '命中' if hit else '未命中')
            if hit:
                find = True
                break
    elif area.is_template_area:
        rect = area.rect

        mrl = ctx.tm.crop_and_match_template(screen, rect, area.template_sub_dir, area.template_id,
                                             threshold=area.template_match_threshold)
        find = mrl.max is not None
        # 低于阈值时 mrl.max 为 None,原始 conf 已被 cv2_utils.match_template 过滤,日志打 '-'
        log.debug('find_area %s: 模板%s conf=%s/%.2f → %s',
                  area_key, area.template_id,
                  f'{mrl.max.confidence:.2f}' if mrl.max is not None else '-',
                  area.template_match_threshold, '命中' if find else '未命中')

    return FindAreaResultEnum.TRUE if find else FindAreaResultEnum.FALSE


def find_template_coord_in_area(
    ctx: OneDragonContext,
    screen: MatLike,
    screen_name: str,
    area_name: str,
) -> MatchResult | None:
    """
    在指定区域内进行模板匹配，返回匹配到的绝对坐标

    Args:
        ctx: 上下文
        screen: 游戏截图
        screen_name: 画面名称
        area_name: 区域名称

    Returns:
        MatchResult | None: 匹配结果（包含绝对坐标），如果未匹配到则返回 None
    """
    area: ScreenArea = ctx.screen_loader.get_area(screen_name, area_name)
    if area is None or not area.is_template_area:
        return None

    # 在裁剪区域内进行模板匹配
    mrl = ctx.tm.crop_and_match_template(
        screen,
        area.rect,
        area.template_sub_dir,
        area.template_id,
        threshold=area.template_match_threshold,
        only_best=True,
    )

    if mrl.max is None:
        return None

    # 将相对坐标转换为绝对坐标
    result = MatchResult(
        mrl.max.confidence,
        mrl.max.x + area.rect.x1,
        mrl.max.y + area.rect.y1,
        mrl.max.w,
        mrl.max.h
    )

    return result


def find_and_click_area(
    ctx: OneDragonContext,
    screen: MatLike,
    screen_name: str,
    area_name: str,
    crop_first: bool = False,
    center_x: bool = False,
) -> OcrClickResultEnum:
    """
    在指定画面中找到目标区域并点击，按区域类型分三种行为：

    - 文本区：区域内 OCR 命中目标文本才点击，点其命中位置；
    - 模板区：区域内模板匹配达标才点击，点其命中位置；
    - 纯定位区（text 与 template 均为空）：不做任何匹配，直接点区域
      中心坐标，恒返回 OCR_CLICK_SUCCESS（click 执行失败也返回成功，
      仅记日志）——无论当前实际是什么画面。

    调用方注意：纯定位区没有匹配条件，坐标点击在任何画面上都会发出并
    返回成功——使用前须自行确认当前画面（画面级判定），或点后用
    until 锚验证转移（round_by_find_and_click_area 的 until 即为此设计）。

    Args:
        ctx: 运行上下文
        screen: 游戏截图
        screen_name: 画面名称
        area_name: 区域名称
        crop_first: 在传入区域时 是否先裁剪再进行文本识别
        center_x: 模板区域点击时是否固定使用游戏中心点的 x 坐标

    Returns:
        OcrClickResultEnum: 点击结果
    """
    area: ScreenArea = ctx.screen_loader.get_area(screen_name, area_name)
    if area is None:
        log.warning('区域未配置(画面名或 area 名不在运行时 screen_info 中): %s.%s',
                    screen_name, area_name)
        return OcrClickResultEnum.AREA_NO_CONFIG
    if area.is_text_area:
        ocr_result_list = ctx.ocr_service.get_ocr_result_list(
            image=screen,
            rect=area.rect,
            color_range=area.color_range,
            crop_first=crop_first,
        )

        for ocr_result in ocr_result_list:
            if str_utils.find_by_lcs(gt(area.text, 'game'), ocr_result.data, percent=area.lcs_percent):
                if ctx.controller.click(ocr_result.center, pc_alt=area.pc_alt, gamepad_key=area.gamepad_key):
                    log.debug('点击 %s.%s @ (%d,%d) pc_alt=%s → 成功',
                              screen_name, area_name, ocr_result.center.x, ocr_result.center.y,
                              'T' if area.pc_alt else 'F')
                    return OcrClickResultEnum.OCR_CLICK_SUCCESS
                else:
                    log.debug('点击 %s.%s @ (%d,%d) pc_alt=%s → 失败',
                              screen_name, area_name, ocr_result.center.x, ocr_result.center.y,
                              'T' if area.pc_alt else 'F')
                    return OcrClickResultEnum.OCR_CLICK_FAIL

        log.debug('find_area %s.%s: 未命中(不点击)', screen_name, area_name)
        return OcrClickResultEnum.OCR_CLICK_NOT_FOUND
    elif area.is_template_area:
        rect = area.rect

        mrl = ctx.tm.crop_and_match_template(screen, rect, area.template_sub_dir, area.template_id,
                                             threshold=area.template_match_threshold)
        if mrl.max is None:
            log.debug('find_area %s.%s: 未命中(不点击)', screen_name, area_name)
            return OcrClickResultEnum.OCR_CLICK_NOT_FOUND

        matched_center = mrl.max.center + rect.left_top
        to_click = Point(ctx.controller.center_point.x, matched_center.y) if center_x else matched_center

        if ctx.controller.click(to_click, pc_alt=area.pc_alt, gamepad_key=area.gamepad_key):
            log.debug('点击 %s.%s @ (%d,%d) pc_alt=%s → 成功',
                      screen_name, area_name, to_click.x, to_click.y,
                      'T' if area.pc_alt else 'F')
            return OcrClickResultEnum.OCR_CLICK_SUCCESS
        else:
            log.debug('点击 %s.%s @ (%d,%d) pc_alt=%s → 失败',
                      screen_name, area_name, to_click.x, to_click.y,
                      'T' if area.pc_alt else 'F')
            return OcrClickResultEnum.OCR_CLICK_FAIL
    else:
        clicked = ctx.controller.click(area.center, pc_alt=area.pc_alt, gamepad_key=area.gamepad_key)
        # 纯定位区点击:返回枚举保持既有语义恒为 SUCCESS,日志如实记录 click 执行结果
        log.debug('点击 %s.%s @ (%d,%d) pc_alt=%s → %s',
                  screen_name, area_name, area.center.x, area.center.y,
                  'T' if area.pc_alt else 'F', '成功' if clicked else '失败')
        return OcrClickResultEnum.OCR_CLICK_SUCCESS


def scroll_area(
    ctx: OneDragonContext,
    area: ScreenArea,
    direction: str = 'down',
    start_ratio: float = 0.9,
    end_ratio: float = 0.1,
) -> None:
    """
    在指定区域内滚动屏幕

    Args:
        ctx: 运行上下文
        area: 区域
        direction: 滚动方向，'down' 表示往下滚（从下往上滑），'up' 表示往上滚（从上往下滑）
        start_ratio: 起始位置比例（距顶部的比例）。默认0.9，即区域底部10%处
        end_ratio: 结束位置比例（距顶部的比例）。默认0.1，即区域顶部10%处
    """
    rect = area.rect
    height = rect.height

    # 统一按“距顶部比例”计算位置，避免 start/end 计算成同一点
    start_ratio = max(0.0, min(1.0, start_ratio))
    end_ratio = max(0.0, min(1.0, end_ratio))
    y_start = rect.y1 + int(height * start_ratio)
    y_end = rect.y1 + int(height * end_ratio)

    if direction == 'up':
        # 往上滚：手势从上往下划
        start = Point(rect.center.x, y_end)
        end = Point(rect.center.x, y_start)
    else:
        # 往下滚：手势从下往上划
        start = Point(rect.center.x, y_start)
        end = Point(rect.center.x, y_end)

    # 防止极端情况下 start/end 重合导致“看起来没有滚动”
    if start.y == end.y:
        if start.y >= rect.center.y:
            end = Point(end.x, max(rect.y1 + 1, end.y - 1))
        else:
            end = Point(end.x, min(rect.y2 - 1, end.y + 1))

    ctx.controller.drag_to(start=start, end=end)


def get_match_screen_name(
    ctx: OneDragonContext,
    screen: MatLike,
    screen_name_list: list[str] | None = None,
    crop_first: bool = False,
) -> str | None:
    """
    根据游戏截图 匹配一个最合适的画面

    Args:
        ctx: 上下文
        screen: 游戏截图
        screen_name_list: 画面列表 传入时 只判断这里的画面
        crop_first: 在传入区域时 是否先裁剪再进行文本识别

    Returns:
        str | None: 画面名称
    """
    start_time = time.time()
    # 判定序 = 实际调用过 is_target_screen 的画面(scope 跳过/提前命中后未判定的不计)
    tried_screen_names: list[str] = []
    result: str | None = None

    if screen_name_list is not None:
        for screen_info in ctx.screen_loader.screen_info_list:
            if screen_info.screen_name not in screen_name_list:
                continue
            tried_screen_names.append(screen_info.screen_name)
            if is_target_screen(ctx, screen, screen_info=screen_info, crop_first=crop_first):
                result = screen_info.screen_name
                break
    elif ctx.screen_loader.current_screen_name is not None or ctx.screen_loader.last_screen_name is not None:
        result = get_match_screen_name_from_last(ctx, screen, crop_first=crop_first,
                                                 tried_screen_names=tried_screen_names)
    else:
        for screen_info in ctx.screen_loader.active_screen_info_list:
            tried_screen_names.append(screen_info.screen_name)
            if is_target_screen(ctx, screen, screen_info=screen_info, crop_first=crop_first):
                result = screen_info.screen_name
                break

    log.debug('画面判定: %s (判定 %d, %.2fs)',
              result, len(tried_screen_names), time.time() - start_time)
    if result is None:
        log.debug('画面判定: None (试过 [%s] 全未中)',
                  ', '.join(tried_screen_names[:10]))

    return result


def get_match_screen_name_from_last(
    ctx: OneDragonContext,
    screen: MatLike,
    crop_first: bool = False,
    tried_screen_names: list[str] | None = None,
) -> str | None:
    """
    根据游戏截图 从上次记录的画面开始 匹配一个最合适的画面
    Args:
        ctx: 上下文
        screen: 游戏截图
        crop_first: 在传入区域时 是否先裁剪再进行文本识别
        tried_screen_names: 出参 收集实际调用过 is_target_screen 的画面判定序
            (scope 跳过的只展开邻居不判定,不计入),供父函数打判定日志

    Returns:
        str | None: 画面名称
    """
    active_names = ctx.screen_loader.active_screen_names  # set or None

    bfs_list = []

    if ctx.screen_loader.current_screen_name is not None:  # 如果有记录上次所在画面 则从这个画面开始搜索
        bfs_list.append(ctx.screen_loader.current_screen_name)
    if ctx.screen_loader.last_screen_name is not None:
        bfs_list.append(ctx.screen_loader.last_screen_name)

    if len(bfs_list) == 0:
        return None

    bfs_idx = 0
    while bfs_idx < len(bfs_list):
        current_screen_name = bfs_list[bfs_idx]
        bfs_idx += 1

        # 在 scope 模式下 跳过非活跃 screen 的匹配（但仍展开其邻居以保持图连通性）
        if active_names is not None and current_screen_name not in active_names:
            screen_info = ctx.screen_loader.screen_info_map.get(current_screen_name)
            if screen_info is not None:
                for area in screen_info.area_list:
                    if area.goto_list is None or len(area.goto_list) == 0:
                        continue
                    for goto_screen in area.goto_list:
                        if goto_screen not in bfs_list:
                            bfs_list.append(goto_screen)
            continue

        if tried_screen_names is not None:
            tried_screen_names.append(current_screen_name)
        if is_target_screen(ctx, screen, screen_name=current_screen_name, crop_first=crop_first):
            return current_screen_name

        screen_info = ctx.screen_loader.get_screen(current_screen_name)
        if screen_info is None:
            continue
        for area in screen_info.area_list:
            if area.goto_list is None or len(area.goto_list) == 0:
                continue
            for goto_screen in area.goto_list:
                if goto_screen not in bfs_list:
                    bfs_list.append(goto_screen)

    # 最后 尝试搜索中没有出现的画面
    for screen_info in ctx.screen_loader.active_screen_info_list:
        if screen_info.screen_name in bfs_list:
            continue
        if tried_screen_names is not None:
            tried_screen_names.append(screen_info.screen_name)
        if is_target_screen(ctx, screen, screen_info=screen_info, crop_first=crop_first):
            return screen_info.screen_name

    return None

def is_target_screen(
    ctx: OneDragonContext,
    screen: MatLike,
    screen_name: str | None = None,
    screen_info: ScreenInfo | None = None,
    crop_first: bool = False,
) -> bool:
    """
    根据游戏截图 判断是否目标画面

    Args:
        ctx: 上下文
        screen: 游戏截图
        screen_name: 目标画面名称
        screen_info: 目标画面信息 传入时优先使用
        crop_first: 在传入区域时 是否先裁剪再进行文本识别

    Returns:
        bool: 是否目标画面
    """
    if screen_info is None:
        if screen_name is None:
            return False
        screen_info = ctx.screen_loader.get_screen(screen_name)
        if screen_info is None:
            return False

    existed_id_mark: bool = False
    fit_id_mark: bool = True
    for screen_area in screen_info.area_list:
        if not screen_area.id_mark:
            continue
        existed_id_mark = True

        # 透传 screen_name 让 B1a 详情行带画面上下文(area_name 跨画面不唯一,否则无法对号)
        if find_area_in_screen(ctx, screen, screen_area, crop_first,
                               screen_name=screen_info.screen_name) != FindAreaResultEnum.TRUE:
            fit_id_mark = False
            break

    return existed_id_mark and fit_id_mark


def find_by_ocr(
    ctx: OneDragonContext,
    screen: MatLike,
    target_cn: str,
    area: ScreenArea | None = None,
    lcs_percent: float = 0.5,
    color_range: list[list[int]] | None = None,
    crop_first: bool = False,
) -> bool:
    """
    判断画面中是否有目标文本

    Args:
        ctx: 上下文
        screen: 游戏截图
        target_cn: 目标中文文本
        area: 指定区域
        lcs_percent: 文本匹配阈值
        color_range: 区域筛选的颜色范围
        crop_first: 在传入区域时 是否先裁剪再进行文本识别

    Returns:
        bool: 是否有目标文本
    """
    if lcs_percent is None:
        lcs_percent = area.lcs_percent

    if color_range is None and area is not None:
        color_range = area.color_range
    ocr_result_list = ctx.ocr_service.get_ocr_result_list(
        image=screen,
        rect=area.rect if area is not None else None,
        color_range=color_range,
        crop_first=crop_first,
    )

    to_click: Point | None = None
    for ocr_result in ocr_result_list:
        if str_utils.find_by_lcs(gt(target_cn, 'game'), ocr_result.data, percent=lcs_percent):
            to_click = ocr_result.center
            break

    return to_click is not None
