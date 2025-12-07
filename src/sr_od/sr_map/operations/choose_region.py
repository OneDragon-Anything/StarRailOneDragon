import difflib
from cv2.typing import MatLike
from typing import List

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult, MatchResultList
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.config import game_const
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.sr_map import large_map_utils
from sr_od.sr_map.operations.choose_floor import ChooseFloor
from sr_od.sr_map.operations.scale_large_map import ScaleLargeMap
from sr_od.sr_map.sr_map_def import Planet, Region


class ChooseRegion(SrOperation):

    def __init__(self, ctx: SrContext, region: Region,
                 skip_planet_check: bool = False):
        """
        默认已经打开了大地图 且选择了正确的星球。
        选择目标区域
        :param ctx: 上下文
        :param region: 区域
        :param skip_planet_check: 跳过当前星球的检测
        """
        self.skip_planet_check: bool = skip_planet_check  # 跳过当前星球的检测
        self.planet: Planet = region.planet
        self.region: Region = region  # 目标区域
        self.region_to_choose_1: Region = region if region.parent is None else region.parent  # 第一步需要选择的区域
        self.sub_region_clicked: bool = False  # 是否已经点击了子区域

        SrOperation.__init__(self, ctx, op_name=gt('选择区域 %s') % region.display_name)

    @operation_node(name='检测星球', is_start_node=True)
    def _check_planet(self) -> OperationRoundResult:
        if self.skip_planet_check:
            return self.round_success()
        screen = self.last_screenshot

        planet = large_map_utils.get_planet(self.ctx, screen)
        if planet is None or planet != self.planet:
            return self.round_retry('未在星球 %s' % self.planet.cn, wait=1)
        else:
            return self.round_success()

    @node_from(from_name='检测星球')
    @operation_node(name='选择区域')
    def _choose_region(self) -> OperationRoundResult:
        screen = self.last_screenshot

        result = self.round_by_find_and_click_area(screen, '大地图', '按钮-传送')
        if result.is_success:
            return self.round_wait(wait=1)

        # 判断当前选择区域是否目标区域
        current_region_name = large_map_utils.get_active_region_name(self.ctx, screen)
        current_region = self.ctx.map_data.best_match_region_by_name(current_region_name, planet=self.planet)
        log.info('当前区域文本 %s 匹配区域名称 %s', current_region_name, current_region.cn if current_region is not None else '')

        is_current: bool = (current_region is not None and current_region.pr_id == self.region_to_choose_1.pr_id)

        # 还没有选好区域
        if not is_current:
            region_pos_list = self.get_region_pos_list(screen)
            pr_id_set: set[str] = set()
            for region_pos in region_pos_list:
                pr_id_set.add(region_pos.data.pr_id)
                if region_pos.data.pr_id == self.region_to_choose_1.pr_id:
                    self.ctx.controller.click(region_pos.center)
                    return self.round_retry(wait=1)

            # 没有发现目标区域 需要滚动
            with_before_region: bool = False  # 当前区域列表在目标区域之前
            region_list = self.ctx.map_data.get_region_list_by_planet(self.region_to_choose_1.planet)
            for r in region_list:
                if r.pr_id in pr_id_set:
                    with_before_region = True
                if r.pr_id == self.region_to_choose_1.pr_id:
                    break

            self.scroll_region_area(1 if with_before_region else -1)
            return self.round_retry(wait=1)
        else:
            return self.round_success()

    def get_region_pos_list(self, screen: MatLike, confidence:int = 0.3) -> List[MatchResult]:
        """
        获取当前屏幕显示的区域
        MatchResult.data = Region
        匹配全部显示的区域，是为了可以明确知道最后需要往哪个方向滚动。随机滚动存在卡死的可能。
        :param screen:
        :param confidence: 文本匹配的阈值 后续考虑替换掉 lcs_percent
        :return:
        """
        area = self.ctx.screen_loader.get_area('大地图', '区域列表')
        part = cv2_utils.crop_image_only(screen, area.rect)
        ocr_map = self.ctx.ocr.run_ocr(part, merge_line_distance=40)

        # 初始化data 原来应该是 ocr 的文本
        for word, mrl in ocr_map.items():
            result = mrl.max
            if result is None:
                continue
            result.data = None
            result.x += area.rect.left_top.x
            result.y += area.rect.left_top.y

        # 匹诺康尼中 存在【现实】和【梦境】的小分类
        # 通过使用区域列表 在匹配结果中找到最合适的 避免选择到【现实】和【梦境】
        word_2_region_list: dict[str, List[Region]] = {}
        ocr_word_list = list(ocr_map.keys())
        plan_region_list = self.ctx.map_data.get_region_list_by_planet(self.region_to_choose_1.planet)
        for real_region in plan_region_list:
            match = difflib.get_close_matches(gt(real_region.cn, 'ocr'),
                                              ocr_word_list, n=1, cutoff=confidence)
            if len(match) == 0:
                continue

            # 理论上 可能出现两个区域(real_region)都匹配到一个目标(ocr_word)上
            # 例如 基座舱段 和 收容舱段 (real_region) 都匹配到了 收容舱段(ocr_word) 上
            # 但如果截图上就只有 收容舱段(ocr_word) 想要选择 基座舱段(real_region) 也会点击到 收容舱段(ocr_word) 上
            # 这时候先保存下来，再用 收容舱段(ocr_word) 匹配一个最佳的 real_region
            if match[0] not in word_2_region_list:
                word_2_region_list[match[0]] = [real_region]
            else:
                word_2_region_list[match[0]].append(real_region)

        # 最终返回结果
        result_list: List[MatchResult] = []
        for ocr_word, mrl in ocr_map.items():
            result = mrl.max
            if result is None:
                continue
            if ocr_word not in word_2_region_list:
                continue

            region_list: List[Region] = word_2_region_list[ocr_word]
            if len(region_list) == 1:
                result.data = region_list[0]
            else:
                region_name_list = [gt(region.cn, 'ocr') for region in region_list]
                match = difflib.get_close_matches(ocr_word, region_name_list, n=1, cutoff=confidence)
                if len(match) == 0:
                    continue
                for region in region_list:
                    if gt(region.cn, 'ocr') == match[0]:
                        result.data = region
                        break

            if result.data is not None:
                result_list.append(result)

        return result_list

    def scroll_region_area(self, d: int = 1):
        """
        在选择区域的地方滚动鼠标
        :param d: 滚动距离 正向下 负向上
        :return:
        """
        drag_to = large_map_utils.REGION_LIST_RECT.center
        drag_from = Point(0, d * 200) + drag_to
        self.ctx.controller.drag_to(start=drag_from, end=drag_to, duration=0.5)

    @node_from(from_name='选择区域')
    @operation_node(name='选择楼层')
    def _choose_floor(self):
        op = ChooseFloor(self.ctx, self.region_to_choose_1.floor)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择楼层')
    @operation_node(name='主区域缩放地图')
    def _scale_main_region(self) -> OperationRoundResult:
        if self.ctx.pos_info.pos_lm_scale != self.region_to_choose_1.large_map_scale:
            op = ScaleLargeMap(self.ctx, self.region_to_choose_1.large_map_scale, is_main_region=True)
            return self.round_by_op_result(op.execute())
        else:
            return self.round_success('无需缩放')

    @node_from(from_name='主区域缩放地图')
    @operation_node(name='选择子区域', node_max_retry_times=20)
    def _choose_sub_region(self) -> OperationRoundResult:
        if self.region.parent is None:
            return self.round_success('非子区域无需操作')

        screen = self.last_screenshot

        if self.sub_region_clicked and self._in_sub_region(screen):
            return self.round_success(wait=1)

        screen_part, offset = large_map_utils.match_screen_in_large_map(self.ctx, screen, self.region_to_choose_1)
        if offset is None:
            log.error('匹配大地图失败')
            large_map_utils.drag_in_large_map(self.ctx)
            return self.round_retry(wait=0.5)
        else:
            dx, dy = large_map_utils.get_map_next_drag(self.region.enter_lm_pos, offset)
            screen_map_rect = large_map_utils.get_screen_map_rect(self.region_to_choose_1)

            if dx == 0 and dy == 0:  # 当前就能找传送点
                target: MatchResult = self._get_sub_enter_pos(screen_part, offset)
                if target is None:  # 没找到的话 按计算坐标点击
                    to_click = self.region.enter_lm_pos - offset.left_top + screen_map_rect.left_top
                    self.ctx.controller.click(to_click)
                else:
                    to_click = target.center + screen_map_rect.left_top
                    self.ctx.controller.click(to_click)
                self.sub_region_clicked = True
            else:
                large_map_utils.drag_in_large_map(self.ctx, dx, dy)

            return self.round_retry(wait=0.5)

    def _in_sub_region(self, screen: MatLike) -> bool:
        """
        判断是否已经进入子区域 左上角显示的父区域的名字
        :return:
        """
        area = self.ctx.screen_loader.get_area('大地图', '星球名称')
        title_part = cv2_utils.crop_image_only(screen, area.rect)
        ocr_result = self.ctx.ocr.run_ocr_single_line(title_part)
        ocr_region = self.ctx.map_data.best_match_region_by_name(ocr_result, self.region.planet)
        if ocr_region is None:
            return False
        else:
            return ocr_region.pr_id == self.region.parent.pr_id

    def _get_sub_enter_pos(self, screen_part: MatLike, offset: MatchResult):
        """
        在当前屏幕地图上匹配子区域入口
        :param screen_part: 屏幕上的大地图部分
        :param offset: 屏幕上的地图在完整大地图上的偏移量
        :return:
        """
        if self.region.enter_lm_pos is not None:
            sm_offset_x = self.region.enter_lm_pos.x - offset.x
            sm_offset_y = self.region.enter_lm_pos.y - offset.y
            sp_rect = Rect(sm_offset_x - 100, sm_offset_y - 100, sm_offset_x + 100, sm_offset_y + 100)
            crop_screen_map, sp_rect = cv2_utils.crop_image(screen_part, sp_rect)
            result: MatchResultList = self.ctx.tm.match_template(crop_screen_map, 'mm_icon', self.region.enter_template_id,
                                                                 threshold=game_const.THRESHOLD_SP_TEMPLATE_IN_LARGE_MAP)

            if result.max is not None:
                return MatchResult(result.max.confidence,
                                   result.max.x + sp_rect.x1,
                                   result.max.y + sp_rect.y1,
                                   result.max.w,
                                   result.max.h
                                   )
            else:
                return None
        else:
            result: MatchResultList = self.ctx.tm.match_template(screen_part, self.region.enter_template_id,
                                                                 threshold=game_const.THRESHOLD_SP_TEMPLATE_IN_LARGE_MAP)
            return result.max

    @node_from(from_name='选择子区域')
    @operation_node(name='子区域缩放地图')
    def _scale_sub_region(self):
        """
        进入子区域后进行缩放
        :return:
        """
        if self.region.parent is None:
            return self.round_success('非子区域无需操作')

        if self.ctx.pos_info.pos_lm_scale != self.region.large_map_scale:
            op = ScaleLargeMap(self.ctx, self.region.large_map_scale, is_main_region=False)
            return self.round_by_op_result(op.execute())
        else:
            return self.round_success('无需缩放')