import math
from concurrent.futures import Future

import concurrent.futures
import cv2
import numpy as np
import os
from cv2.typing import MatLike
from typing import List, Optional, Tuple

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult, MatchResultList
from one_dragon.utils import cal_utils, cv2_utils, os_utils, thread_utils
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.sr_map import mini_map_utils
from sr_od.sr_map.large_map_info import LargeMapInfo
from sr_od.sr_map.mini_map_info import MiniMapInfo
from sr_od.sr_map.sr_map_def import Region

cal_pos_executor = concurrent.futures.ThreadPoolExecutor(thread_name_prefix='sr_od_cal_pos')


def get_mini_map_scale_list(running: bool, real_move_time: float = 0, is_debug: bool = False):
    """
    :param running: 是否在移动
    :param real_move_time: 真正按住移动的时间
    :return:
    """
    if is_debug:
        return get_mini_map_scale_list_new(running, real_move_time)
    else:
        return get_mini_map_scale_list_old(running, real_move_time)


def get_mini_map_scale_list_new(running: bool, real_move_time: float = 0):
    """
    :param running: 是否在移动
    :param real_move_time: 真正按住移动的时间
    :return:
    """
    max_scale = 1.35
    old_max_scale = 1.25
    min_scale = 1.00
    if running:
        # 每0.6秒最小缩放比例增加 0.05
        min_scale = round(min_scale + 0.05 * math.floor(real_move_time // 0.6), 2)
        if min_scale > old_max_scale:
            min_scale = old_max_scale
    else:
        # 不移动的时候可以尝试所有缩放比例 因为这时候没有效率的要求
        pass

    scale_list = [min_scale]
    while min_scale < max_scale:
        min_scale = round(min_scale + 0.01, 2)
        scale_list.append(min_scale)

    return scale_list


def get_mini_map_scale_list_old(running: bool, real_move_time: float = 0):
    """
    :param running: 是否在移动
    :param real_move_time: 真正按住移动的时间
    :return:
    """
    scale = 1.25
    scale_list = [scale]
    if running:
        # 0 ~ 3秒 每0.6秒减少一个缩放比例
        max_to_add = 5 - math.floor(real_move_time // 0.6)
        if max_to_add < 0:
            max_to_add = 0
    else:
        # 不移动的时候可以尝试所有缩放比例 因为这时候没有效率的要求
        max_to_add = 5

    for i in range(max_to_add):
        scale = round(scale - 0.05, 2)
        scale_list.append(scale)

    return scale_list


class VerifyPosInfo:

    def __init__(self,
                 last_pos: Optional[Point] = None,
                 max_distance: Optional[float] = None,
                 line_p1: Optional[Point] = None,
                 line_p2: Optional[Point] = None,
                 max_line_distance: float = 20):
        """
        校验位置需要用的信息
        """
        self.last_pos: Point = last_pos  # 上一个点的位置
        self.max_distance: float = max_distance  # 可以接受的最大距离

        self.line_p1: Point = line_p1  # 当前移动直线的点1
        self.line_p2: Point = line_p2  # 当前移动直线的点2
        self.max_line_distance: float = max_line_distance  # 距离直线允许的最大的距离

    @property
    def yml_str(self) -> str:
        yml = ''

        if self.last_pos is not None:
            yml += f'last_pos: {self.last_pos}\n'

        if self.max_distance is not None:
            yml += f'max_distance: {self.max_distance}\n'

        if self.line_p1 is not None:
            yml += f'line_p1: {self.line_p1}\n'

        if self.line_p2 is not None:
            yml += f'line_p2: {self.line_p2}\n'

        return yml


def similar_result(result_list: List[MatchResult], least_result_cnt: int = 2) -> Optional[MatchResult]:
    """
    使用不同的匹配方法时 只有较小几率会出现多个相同的错误结果
    判断结果列表中是否有相似的结果 有的话就采用
    :param result_list: 不同匹配方法得到的结果
    :param least_result_cnt: 只是需要多少个结果相似 自己也算一个
    :return:
    """
    for r1 in result_list:
        if r1 is None:
            continue
        similar_cnt: int = 0
        for r2 in result_list:
            if r2 is None:
                continue
            if cal_utils.distance_between(r1.center, r2.center) < 5:
                similar_cnt += 1

        if similar_cnt >= least_result_cnt:
            return r1

    return None


def cal_character_pos(ctx: SrContext,
                      lm_info: LargeMapInfo, mm_info: MiniMapInfo,
                      lm_rect: Rect = None, show: bool = False,
                      retry_without_rect: bool = False,
                      running: bool = False,
                      real_move_time: float = 0,
                      verify: Optional[VerifyPosInfo] = None) -> Optional[MatchResult]:
    """
    根据小地图 匹配大地图 判断当前的坐标
    :param ctx: 上下文
    :param lm_info: 大地图信息
    :param mm_info: 小地图信息
    :param lm_rect: 大地图特定区域
    :param retry_without_rect: 失败时是否去除特定区域进行全图搜索
    :param show: 是否显示结果
    :param running: 角色是否在移动 移动时候小地图会缩小
    :param real_move_time: 真实移动时间
    :param verify: 校验结果需要的信息
    :return:
    """
    # 匹配结果 是缩放后的 offset 和宽高
    result: Optional[MatchResult] = None

    scale_list = get_mini_map_scale_list(running, real_move_time, is_debug=ctx.env_config.is_debug)
    r1 = None
    r2 = None
    r3 = None
    r4 = None

    if result is None:  # 使用模板匹配 用道路掩码的
        r1 = cal_character_pos_by_road_mask(ctx, lm_info, mm_info, lm_rect=lm_rect, scale_list=scale_list, show=show)
        if is_valid_result(r1, verify):
            result = r1

    if result is None:  # 看看有没有特殊点 使用特殊点倒推位置
        r2 = cal_character_pos_by_sp_result(ctx, lm_info, mm_info, lm_rect=lm_rect)
        if r2 is not None and (r2.template_scale > 1.3 or r2.template_scale < 0.9):  # 不应该有这样的缩放 放弃这个结果
            log.debug('特殊点定位使用的缩放比例不符合预期')
            pass
        else:
            result = r2

    if result is None:  # 使用模板匹配 用灰度图的
        r3 = cal_character_pos_by_gray(ctx, lm_info, mm_info, lm_rect=lm_rect, scale_list=scale_list, show=show)
        if is_valid_result(r3, verify):
            result = r3

    if result is None:  # 使用模板匹配 用原图的
        r4 = cal_character_pos_by_raw(ctx, lm_info, mm_info, lm_rect=lm_rect, scale_list=scale_list, show=show)
        if is_valid_result(r4, verify):
            result = r4

    if result is None:
        result = similar_result([r1, r2, r3, r4])

    if result is None:
        if lm_rect is not None and retry_without_rect:  # 整张大地图试试
            return cal_character_pos(ctx, lm_info, mm_info, running=False, show=show)
        else:
            return None

    if show:
        # result中是缩放后的宽和高
        cv2_utils.show_overlap(lm_info.raw, mm_info.raw,
                               result.x, result.y,
                               template_scale=result.template_scale,
                               win_name='overlap')

    log.debug('计算当前坐标为 %s 使用缩放 %.2f 置信度 %.2f', result.center, result.template_scale, result.confidence)

    return result


def cal_character_pos_by_gray(ctx: SrContext,
                              lm_info: LargeMapInfo, mm_info: MiniMapInfo,
                              lm_rect: Rect = None,
                              scale_list: List[float] = None,
                              show: bool = False) -> Optional[MatchResult]:
    """
    使用模板匹配 在大地图上匹配小地图的位置 会对小地图进行缩放尝试
    使用灰度图进行匹配
    :param ctx: 上下文
    :param lm_info: 大地图信息
    :param mm_info: 小地图信息
    :param lm_rect: 圈定的大地图区域 传入后更准确
    :param scale_list: 缩放比例
    :param show: 是否显示调试结果
    :return:
    """
    source, lm_rect = cv2_utils.crop_image(lm_info.raw, lm_rect)
    source = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    # 使用道路掩码
    mm_del_radio = mm_info.raw_del_radio
    template = cv2.cvtColor(mm_del_radio, cv2.COLOR_BGR2GRAY)

    mini_map_utils.init_road_mask_for_world_patrol(mm_info, another_floor=lm_info.region.another_floor)
    template_mask = mm_info.road_mask_with_edge

    target: MatchResult = template_match_with_scale_list_parallely(ctx, source, template, template_mask,
                                                                   scale_list, 0.3)

    if show:
        scale = target.template_scale if target is not None else 1
        template_usage = cv2_utils.scale_image(template, scale, copy=False)
        template_mask_usage = cv2_utils.scale_image(template_mask, scale, copy=False)
        cv2_utils.show_image(mm_del_radio, win_name='mini_map')
        cv2_utils.show_image(source, win_name='template_match_source')
        cv2_utils.show_image(cv2.bitwise_and(template_usage, template_usage, mask=template_mask_usage),
                             win_name='template_match_template')
        cv2_utils.show_image(template_mask, win_name='template_match_template_mask')

    if target is not None:
        offset_x = target.x + (lm_rect.x1 if lm_rect is not None else 0)
        offset_y = target.y + (lm_rect.y1 if lm_rect is not None else 0)
        return MatchResult(target.confidence, offset_x, offset_y, target.w, target.h, target.template_scale)
    else:
        return None


def cal_character_pos_by_raw(ctx: SrContext,
                             lm_info: LargeMapInfo, mm_info: MiniMapInfo,
                             lm_rect: Rect = None,
                             show: bool = False,
                             scale_list: List[float] = None,
                             match_threshold: float = 0.3) -> Optional[MatchResult]:
    """
    使用模板匹配 在大地图上匹配小地图的位置 会对小地图进行缩放尝试
    使用小地图原图 - 需要到这一步 说明背景比较杂乱 因此道路掩码只使用中心点包含的连通块
    :param ctx: 上下文
    :param lm_info: 大地图信息
    :param mm_info: 小地图信息
    :param lm_rect: 圈定的大地图区域 传入后更准确
    :param show: 是否显示调试结果
    :param scale_list: 缩放比例
    :param match_threshold: 模板匹配的阈值
    :return:
    """
    source, lm_rect = cv2_utils.crop_image(lm_info.raw, lm_rect)
    # 使用道路掩码
    template = mm_info.raw_del_radio
    mini_map_utils.init_road_mask_for_world_patrol(mm_info, another_floor=lm_info.region.another_floor)
    template_mask = mm_info.road_mask_with_edge

    target: MatchResult = template_match_with_scale_list_parallely(ctx, source, template, template_mask,
                                                                   scale_list, match_threshold)

    if show:
        scale = target.template_scale if target is not None else 1
        template_usage = cv2_utils.scale_image(template, scale, copy=False)
        template_mask_usage = cv2_utils.scale_image(template_mask, scale, copy=False)
        cv2_utils.show_image(mm_info.raw, win_name='mini_map')
        cv2_utils.show_image(source, win_name='template_match_source')
        cv2_utils.show_image(cv2.bitwise_and(template_usage, template_usage, mask=template_mask_usage),
                             win_name='template_match_template')
        cv2_utils.show_image(template_mask, win_name='template_match_template_mask')

    if target is not None:
        offset_x = target.x + (lm_rect.x1 if lm_rect is not None else 0)
        offset_y = target.y + (lm_rect.y1 if lm_rect is not None else 0)
        return MatchResult(target.confidence, offset_x, offset_y, target.w, target.h, target.template_scale)
    else:
        return None


def cal_character_pos_by_sp_result(ctx: SrContext,
                                   lm_info: LargeMapInfo, mm_info: MiniMapInfo,
                                   lm_rect: Rect = None) -> Optional[MatchResult]:
    """
    根据特殊点 计算小地图在大地图上的位置
    :param ctx: 上下文
    :param lm_info: 大地图信息
    :param mm_info: 小地图信息
    :param lm_rect: 圈定的大地图区域 传入后更准确
    :return:
    """
    lm_sp_map = ctx.map_data.get_sp_type_in_rect(lm_info.region, lm_rect)
    if len(lm_sp_map) == 0:
        return None
    mini_map_utils.init_sp_mask_by_feature_match(ctx, mm_info, set(lm_sp_map.keys()))

    mm_height, mm_width = mm_info.raw.shape[:2]

    cal_pos_list = []

    for template_id, v in mm_info.sp_result.items():
        lm_sp = lm_sp_map.get(template_id) if template_id in lm_sp_map else []
        if len(lm_sp) == 0:
            continue
        for r in v:
            # 特殊点是按照大地图缩放比例获取的 因为可以反向将小地图缩放回人物静止时的大小
            mm_scale = 1 / r.template_scale
            x = r.x / r.template_scale
            y = r.y / r.template_scale
            # 特殊点中心在小地图上的位置
            cx = int(x + r.w // 2)
            cy = int(y + r.h // 2)
            scaled_width = int(mm_width / r.template_scale)
            scaled_height = int(mm_height / r.template_scale)

            # 通过大地图上相同的特殊点 反推小地图在大地图上的偏移量
            for sp in lm_sp:
                cal_x = sp.lm_pos.x - cx
                cal_y = sp.lm_pos.y - cy
                cal_pos_list.append(MatchResult(1, cal_x, cal_y, scaled_width, scaled_height, template_scale=mm_scale))

    if len(cal_pos_list) == 0:
        return None

    # 如果小地图上有个多个特殊点 则合并临近的结果 越多相同结果代表置信度越高
    merge_pos_list = []
    for pos_1 in cal_pos_list:
        merge = False
        for pos_2 in merge_pos_list:
            if cal_utils.distance_between(Point(pos_1.x, pos_1.y), Point(pos_2.x, pos_2.y)) < 10:
                merge = True
                pos_2.confidence += 1

        if not merge:
            merge_pos_list.append(pos_1)

    # 找出合并个数最多的 如果有合并个数一样的 则放弃本次结果
    target_pos = None
    same_confidence = False
    for pos in merge_pos_list:
        if target_pos is None:
            target_pos = pos
        elif pos.confidence > target_pos.confidence:
            target_pos = pos
            same_confidence = False
        elif pos.confidence == target_pos.confidence:
            same_confidence = True

    return None if same_confidence else target_pos


def cal_character_pos_by_road_mask(ctx: SrContext,
                                   lm_info: LargeMapInfo, mm_info: MiniMapInfo,
                                   lm_rect: Rect = None,
                                   show: bool = False,
                                   scale_list: List[float] = None) -> Optional[MatchResult]:
    """
    使用模板匹配 在大地图上匹配小地图的位置 会对小地图进行缩放尝试
    使用处理过后的道路掩码图
    :param ctx: 上下文
    :param lm_info: 大地图信息
    :param mm_info: 小地图信息
    :param lm_rect: 圈定的大地图区域 传入后更准确
    :param show: 是否显示调试结果
    :param scale_list: 缩放比例
    :return:
    """
    source, lm_rect = cv2_utils.crop_image(lm_info.mask, lm_rect)
    # 使用道路掩码
    mini_map_utils.init_road_mask_for_world_patrol(mm_info, another_floor=lm_info.region.another_floor)
    template = cv2.bitwise_or(mm_info.road_mask, mm_info.arrow_mask)  # 需要把中心补上
    template_mask = mm_info.circle_mask

    target: MatchResult = template_match_with_scale_list_parallely(ctx, source, template, template_mask,
                                                                   scale_list,
                                                                   0.4)

    if show:
        scale = target.template_scale if target is not None else 1
        template_usage = cv2_utils.scale_image(template, scale, copy=False)
        template_mask_usage = cv2_utils.scale_image(template_mask, scale, copy=False)
        cv2_utils.show_image(mm_info.raw, win_name='mini_map')
        cv2_utils.show_image(source, win_name='template_match_source')
        cv2_utils.show_image(cv2.bitwise_and(template_usage, template_usage, mask=template_mask_usage),
                             win_name='template_match_template')
        cv2_utils.show_image(template_mask, win_name='template_match_template_mask')

    if target is not None:
        offset_x = target.x + (lm_rect.x1 if lm_rect is not None else 0)
        offset_y = target.y + (lm_rect.y1 if lm_rect is not None else 0)
        return MatchResult(target.confidence, offset_x, offset_y, target.w, target.h, target.template_scale)
    else:
        return None


def merge_road_mask(road_mask, edge_mask):
    mask = np.full(road_mask.shape, fill_value=127, dtype=np.uint8)
    mask[np.where(road_mask > 0)] = 0
    mask[np.where(edge_mask > 0)] = 255
    return mask


def template_match_with_scale_list_parallely(ctx: SrContext,
                                             source: MatLike, template: MatLike, template_mask: MatLike,
                                             scale_list: List[float],
                                             threshold: float) -> MatchResult:
    """
    按一定缩放比例进行模板匹配，并行处理不同的缩放比例，返回置信度最高的结果
    :param ctx: 上下文
    :param source: 原图
    :param template: 模板图
    :param template_mask: 模板掩码
    :param scale_list: 模板的缩放比例
    :param threshold: 匹配阈值
    :return: 置信度最高的结果
    """
    future_list: List[Future] = []
    for scale in scale_list:
        f = cal_pos_executor.submit(template_match_with_scale, ctx, source, template, template_mask, scale, threshold)
        thread_utils.handle_future_result(f)
        future_list.append(f)

    target: Optional[MatchResult] = None
    for future in future_list:
        try:
            result: MatchResult = future.result(1)
            if result is not None:
                # log.debug('缩放比例 %.2f 置信度 %.2f', result.template_scale, result.confidence)
                if target is None or result.confidence > target.confidence:
                    target = result
        except concurrent.futures.TimeoutError:
            log.error('模板匹配超时', exc_info=True)

    return target


def template_match_with_scale(ctx: SrContext,
                              source: MatLike, template: MatLike, template_mask: MatLike, scale: float,
                              threshold: float) -> MatchResult:
    """
    按一定缩放比例进行模板匹配，返回置信度最高的结果
    :param ctx: 上下文
    :param source: 原图
    :param template: 模板图
    :param template_mask: 模板掩码
    :param scale: 模板的缩放比例
    :param threshold: 匹配阈值
    :return:
    """
    template_scale = cv2_utils.scale_image(template, scale, copy=False)
    template_mask_scale = cv2_utils.scale_image(template_mask, scale, copy=False)

    # 放大后 截取中心部分来匹配 防止放大后的图片超过了原图的范围
    template_usage = np.zeros_like(template, dtype=np.uint8)
    template_mask_usage = np.zeros_like(template_mask, dtype=np.uint8)

    height, width = template.shape[:2]
    scale_height, scale_width = template_scale.shape[:2]
    cx = scale_width // 2
    cy = scale_height // 2
    sx = cx - width // 2
    ex = sx + width
    sy = cy - width // 2
    ey = sy + height

    template_usage[:, :] = template_scale[sy:ey, sx:ex]
    template_mask_usage[:, :] = template_mask_scale[sy:ey, sx:ex]

    result: MatchResultList = cv2_utils.match_template(source, template_usage,
                                                       mask=template_mask_usage, threshold=threshold,
                                                       only_best=True, ignore_inf=True)
    if result.max is not None:
        result.max.x -= sx
        result.max.y -= sy
        result.max.w = scale_width
        result.max.h = scale_height
        result.max.template_scale = scale

    return result.max


def sim_uni_cal_pos(
        ctx: SrContext,
        lm_info: LargeMapInfo, mm_info: MiniMapInfo,
        lm_rect: Rect = None, show: bool = False,
        running: bool = False, real_move_time: float = 0,
        verify: Optional[VerifyPosInfo] = None) -> Optional[MatchResult]:
    """
    根据小地图 匹配大地图 判断当前的坐标。模拟宇宙中使用
    :param ctx: 上下文
    :param lm_info: 大地图信息
    :param mm_info: 小地图信息
    :param lm_rect: 大地图特定区域
    :param show: 是否显示结果
    :param running: 角色是否在移动 移动时候小地图会缩小
    :param real_move_time: 真正按住移动的时间
    :param verify: 校验结果需要的信息
    :return:
    """
    # 匹配结果 是缩放后的 offset 和宽高
    result: Optional[MatchResult] = None

    scale_list = get_mini_map_scale_list(running, real_move_time, is_debug=ctx.env_config.is_debug)
    r1 = None
    r2 = None
    r3 = None

    # 模拟宇宙中 不需要考虑特殊点
    # 模拟宇宙中 由于地图都是裁剪的 小地图缺块 不能直接使用道路掩码匹配（误报率非常高）

    if result is None:  # 使用模板匹配 灰度图
        r1 = sim_uni_cal_pos_by_gray(ctx, lm_info, mm_info, lm_rect=lm_rect, scale_list=scale_list, show=show)
        if is_valid_result(r1, verify):
            result = r1

    if result is None:  # 使用模板匹配 原图
        r2 = sim_uni_cal_pos_by_raw(ctx, lm_info, mm_info, lm_rect=lm_rect, scale_list=scale_list, show=show)
        if is_valid_result(r2, verify):
            result = r2

    if result is None:  # 如果两个结果相似 直接采纳
        result = similar_result([r1, r2])

    if result is None:
        return None

    scale = result.template_scale
    # 小地图缩放后中心点在大地图的位置 即人物坐标
    target = result.center

    if show:
        cv2_utils.show_overlap(lm_info.raw, mm_info.raw, result.x, result.y, template_scale=scale,
                               win_name='overlap')
        cv2_utils.show_image(lm_info.raw, MatchResult(1, result.center.x - 2, result.center.y - 2, 4, 4),
                             win_name='sim_uni_cal_pos_point')

    log.debug('计算当前坐标为 %s 使用缩放 %.2f 置信度 %.2f', target, scale, result.confidence)

    return result


def sim_uni_cal_pos_by_gray(ctx: SrContext,
                            lm_info: LargeMapInfo, mm_info: MiniMapInfo,
                            lm_rect: Rect = None,
                            show: bool = False,
                            scale_list: List[float] = None,
                            match_threshold: float = 0.3) -> Optional[MatchResult]:
    """
    使用模板匹配 在大地图上匹配小地图的位置 会对小地图进行缩放尝试
    使用模拟宇宙专用的道路掩码图 + 灰度图
    :param ctx: 上下文
    :param lm_info: 大地图信息
    :param mm_info: 小地图信息
    :param lm_rect: 圈定的大地图区域 传入后更准确
    :param show: 是否显示调试结果
    :param scale_list: 缩放比例
    :param match_threshold: 模板匹配的阈值
    :return:
    """
    source, lm_rect = cv2_utils.crop_image(lm_info.raw, lm_rect)
    source = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    # 使用道路掩码
    template = cv2.cvtColor(mm_info.raw_del_radio, cv2.COLOR_BGR2GRAY)
    mini_map_utils.init_road_mask_for_sim_uni(mm_info)
    template_mask = mm_info.road_mask_with_edge  # 把白色边缘包括进来

    target: MatchResult = template_match_with_scale_list_parallely(ctx, source, template, template_mask, scale_list,
                                                                   match_threshold)

    if show:
        scale = target.template_scale if target is not None else 1
        template_usage = cv2_utils.scale_image(template, scale, copy=False)
        template_mask_usage = cv2_utils.scale_image(template_mask, scale, copy=False)
        cv2_utils.show_image(mm_info.raw_del_radio, win_name='mini_map')
        cv2_utils.show_image(mm_info.road_mask_with_edge, win_name='road_mask')
        cv2_utils.show_image(source, win_name='template_match_source')
        cv2_utils.show_image(cv2.bitwise_and(template_usage, template_usage, mask=template_mask_usage),
                             win_name='template_match_template')
        cv2_utils.show_image(template_mask, win_name='template_match_template_mask')

    if target is not None:
        offset_x = target.x + (lm_rect.x1 if lm_rect is not None else 0)
        offset_y = target.y + (lm_rect.y1 if lm_rect is not None else 0)
        return MatchResult(target.confidence, offset_x, offset_y, target.w, target.h, target.template_scale)
    else:
        return None


def sim_uni_cal_pos_by_raw(ctx: SrContext,
                           lm_info: LargeMapInfo, mm_info: MiniMapInfo,
                           lm_rect: Rect = None,
                           show: bool = False,
                           scale_list: List[float] = None,
                           match_threshold: float = 0.3) -> Optional[MatchResult]:
    """
    使用模板匹配 在大地图上匹配小地图的位置 会对小地图进行缩放尝试
    使用模拟宇宙专用的道路掩码图 + 原图
    :param ctx: 上下文
    :param lm_info: 大地图信息
    :param mm_info: 小地图信息
    :param lm_rect: 圈定的大地图区域 传入后更准确
    :param show: 是否显示调试结果
    :param scale_list: 缩放比例
    :return:
    """
    source, lm_rect = cv2_utils.crop_image(lm_info.raw, lm_rect)
    # 使用道路掩码
    template = mm_info.raw_del_radio
    mini_map_utils.init_road_mask_for_sim_uni(mm_info)
    template_mask = mm_info.road_mask_with_edge

    target: MatchResult = template_match_with_scale_list_parallely(ctx, source, template, template_mask,
                                                                   scale_list,
                                                                   threshold=match_threshold)

    if show:
        scale = target.template_scale if target is not None else 1
        template_usage = cv2_utils.scale_image(template, scale, copy=False)
        template_mask_usage = cv2_utils.scale_image(template_mask, scale, copy=False)
        cv2_utils.show_image(mm_info.raw_del_radio, win_name='mini_map')
        cv2_utils.show_image(source, win_name='template_match_source')
        cv2_utils.show_image(cv2.bitwise_and(template_usage, template_usage, mask=template_mask_usage),
                             win_name='template_match_template')
        cv2_utils.show_image(template_mask, win_name='template_match_template_mask')

    if target is not None:
        offset_x = target.x + (lm_rect.x1 if lm_rect is not None else 0)
        offset_y = target.y + (lm_rect.y1 if lm_rect is not None else 0)
        return MatchResult(target.confidence, offset_x, offset_y, target.w, target.h, target.template_scale)
    else:
        return None


def is_valid_result_with_possible_pos(result: Optional[MatchResult],
                                      possible_pos: Optional[Tuple[int, int, float]],
                                      current_angle: Optional[float],
                                      pos_to_cal_angle: Optional[Point] = None) -> bool:
    """
    判断当前计算坐标是否合理
    :param result: 坐标结果
    :param possible_pos: 可能位置 前两个为上一次的坐标，第三个为预估移动距离
    :param current_angle: 当前人物朝向
    :param pos_to_cal_angle: 用于计算朝向的位置 通常用移动的开始点比较好 可以防止惯性撞怪导致的偏移（会产生横向移动 路程又短 计算的角度很可以大于30）
    :return:
    """
    if result is None:
        return False
    if possible_pos is None:  # 无传入时不判断
        return True

    last_pos = Point(possible_pos[0], possible_pos[1])
    move_distance = possible_pos[2]
    next_pos = result.center

    dis = cal_utils.distance_between(last_pos, next_pos)
    if dis > move_distance * 1.1:
        log.debug('计算坐标 %s 与 当前坐标 %s 距离较远 %.2f 舍弃', next_pos, last_pos, dis)
        return False

    if current_angle is None:
        return True

    if pos_to_cal_angle is None:
        next_angle = cal_utils.get_angle_by_pts(last_pos, next_pos)
    else:
        next_angle = cal_utils.get_angle_by_pts(pos_to_cal_angle, next_pos)
    angle_delta = cal_utils.angle_delta(current_angle, next_angle)
    if dis > 5 and abs(angle_delta) > 40:
        log.debug('计算坐标 %s 的角度 %.2f 与 当前朝向 %.2f 相差较大 %.2f 舍弃',
                  next_pos, next_angle, current_angle, angle_delta)
        return False

    return True


def is_valid_result(result: MatchResult, verify: VerifyPosInfo) -> bool:
    """
    判断当前计算坐标是否合理
    :param result: 坐标识别结果
    :param verify: 验证结果需要的信息
    :return:
    """
    if result is None:
        return False
    if verify is None:
        return True

    last_pos = verify.last_pos
    next_pos = result.center
    dis = cal_utils.distance_between(last_pos, next_pos)
    if dis > verify.max_distance * 1.1:
        log.debug('计算坐标 %s 与 当前坐标 %s 距离较远 %.2f 舍弃', next_pos, last_pos, dis)
        return False

    if verify.line_p1 is not None and verify.line_p2 is not None:
        dis = cal_utils.distance_to_line(next_pos, verify.line_p1, verify.line_p2)
        if dis > 20:
            log.debug('计算坐标 %s 与 移动直线 ( %s %s )距离较远 %.2f 舍弃',
                      next_pos, verify.line_p1, verify.line_p2, dis)
            return False

    return True


def save_as_test_case_async(mm: MatLike, region: Region, verify: VerifyPosInfo):
    cal_pos_executor.submit(save_as_test_case, mm, region, verify)


def save_as_test_case(mm: MatLike, region: Region, verify: VerifyPosInfo):
    """
    保存成测试样例
    :param mm: 小地图图片
    :param region: 所属区域
    :param verify: 验证信息
    :return:
    """
    now = os_utils.now_timestamp_str()
    log.info('保存样例 %s %s', region.prl_id, now)
    base = os_utils.get_path_under_work_dir('.debug', 'cal_pos_fail',
                                            region.prl_id, now)

    cv2_utils.save_image(mm, os.path.join(base, 'mm.png'))

    with open(os.path.join(base, 'verify.yml'), 'w', encoding='utf-8') as file:
        file.write(verify.yml_str)

