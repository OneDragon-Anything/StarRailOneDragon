import time

import cv2
import numpy as np
from cv2.typing import MatLike
from typing import ClassVar, Optional

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult, MatchResultList
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.config import game_const
from sr_od.config.game_config import GameLanguageEnum
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.sr_map import large_map_utils
from sr_od.sr_map.large_map_info import LargeMapInfo
from sr_od.sr_map.sr_map_def import SpecialPoint


class ChooseSpecialPoint(SrOperation):

    drag_distance: ClassVar[int] = -200

    def __init__(self, ctx: SrContext, tp: SpecialPoint):
        SrOperation.__init__(self, ctx, op_name=gt('选择传送点 %s') % tp.display_name)
        self.tp: SpecialPoint = tp
        self.lm_info: LargeMapInfo = self.ctx.map_data.get_large_map_info(self.tp.region)

        self.click_sp_in_last_round: bool = False  # 上一轮点击了特殊点

    @operation_node(name='画面识别', node_max_retry_times=10, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 判断地图中间是否有目标点中文可选
        if self.check_and_click_sp_cn(screen):
            time.sleep(1)
            return self.round_wait(wait=1)

        # 先判断右边是不是出现传送了
        if self.check_and_click_transport(screen):
            self.ctx.pos_info.update_pos_after_tp(self.tp)
            return self.round_success(wait=2)

        # 目标点中文 不是传送 或者不是目标传送点 点击一下地图空白位置
        self.ctx.controller.click(large_map_utils.EMPTY_MAP_POS)
        time.sleep(0.5)
        self.click_sp_in_last_round = False

        screen_part, offset = large_map_utils.match_screen_in_large_map(self.ctx, screen, self.tp.region)
        if offset is None:
            log.error('匹配大地图失败')
            large_map_utils.drag_in_large_map(self.ctx)
            return self.round_retry(wait=0.5)

        dx, dy = large_map_utils.get_map_next_drag(self.tp.lm_pos, offset)

        if dx == 0 and dy == 0:  # 当前就能找传送点
            target: MatchResult = self.get_tp_pos(screen_part, offset)
            screen_map_rect = large_map_utils.get_screen_map_rect(self.tp.region)
            if target is None:  # 没找到的话 按计算坐标点击
                to_click = self.tp.lm_pos - offset.left_top + screen_map_rect.left_top
                self.ctx.controller.click(to_click)
                time.sleep(0.5)
            else:
                to_click = target.center + screen_map_rect.left_top
                self.ctx.controller.click(to_click)
                time.sleep(0.5)
            self.click_sp_in_last_round = True

        if dx != 0 or dy != 0:
            large_map_utils.drag_in_large_map(self.ctx, dx, dy)
            time.sleep(0.5)

        return self.round_retry()

    def check_and_click_transport(self, screen: MatLike):
        """
        判断右侧是否出现传送 已经是否对应的传送点
        如果是 则点击
        :param screen: 屏幕截图
        :return: 是否点击传送
        """
        area = self.ctx.screen_loader.get_area('大地图', '按钮-传送')
        tp_btn_part, _ = cv2_utils.crop_image(screen, area.rect)
        # cv2_utils.show_image(tp_btn_part, win_name='tp_btn_part')
        tp_btn_ocr = self.ctx.ocr.match_words(tp_btn_part, ['传送'])
        if len(tp_btn_ocr) > 0:
            do_tp: bool = False  # 进行传送
            # 看看是否目标传送点
            tp_name_area = self.ctx.screen_loader.get_area('大地图', '文本-传送点名称')
            tp_name_part, _ = cv2_utils.crop_image(screen, tp_name_area.rect)
            current_lang: str = self.ctx.game_config.lang
            tp_name_str: Optional[str] = None
            if current_lang == GameLanguageEnum.CN.value.value:
                tp_name_str = self.ctx.ocr.run_ocr_single_line(tp_name_part)
            elif current_lang == GameLanguageEnum.EN.value.value:
                ocr_result: dict = self.ctx.ocr.run_ocr(tp_name_part)
                tp_name_str = None
                for k in ocr_result.keys():
                    if tp_name_str is None:
                        tp_name_str = k
                    else:
                        tp_name_str += ' ' + k

            log.info('当前选择传送点名称 %s', tp_name_str)
            lcs_percent = 0.5 if self.tp.planet.cn == '翁法罗斯' else self.ctx.game_config.special_point_lcs_percent
            if (tp_name_str is not None and
                    str_utils.find_by_lcs(gt(self.tp.cn, 'ocr'), tp_name_str, ignore_case=True,
                                          percent=lcs_percent)):
                do_tp = True

            if self.click_sp_in_last_round:
                do_tp = True

            if do_tp:
                # 点击传送
                to_click = area.center
                for r in tp_btn_ocr.values():
                    to_click = to_click + r.max.center
                    break
                return self.ctx.controller.click(to_click)

        return False

    def get_tp_pos(self, screen_part: MatLike, offset: MatchResult):
        """
        在当前屏幕地图上匹配传送点 在传送点位置
        :param screen_part: 屏幕上的地图部分
        :param offset: 屏幕上的地图在完整大地图上的偏移量
        :return:
        """
        if self.tp.lm_pos is not None:
            sm_offset_x = self.tp.lm_pos.x - offset.x
            sm_offset_y = self.tp.lm_pos.y - offset.y
            sp_rect = Rect(sm_offset_x - 100, sm_offset_y - 100, sm_offset_x + 100, sm_offset_y + 100)
            crop_screen_map, sp_rect = cv2_utils.crop_image(screen_part, sp_rect)
            result: MatchResultList = self.ctx.tm.match_template(crop_screen_map, 'mm_icon', self.tp.template_id,
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
            result: MatchResultList = self.ctx.tm.match_template(screen_part, self.tp.template_id,
                                                                 threshold=game_const.THRESHOLD_SP_TEMPLATE_IN_LARGE_MAP)
            return result.max

    def check_and_click_sp_cn(self, screen) -> bool:
        """
        判断地图中间是否有目标点中文可选 两个特殊点重叠的时候会出现
        发现的话进行点击
        :param screen: 屏幕截图
        :return:
        """
        screen_map_rect = large_map_utils.get_screen_map_rect(self.tp.region)
        screen_map = cv2_utils.crop_image_only(screen, screen_map_rect)

        l = 190
        u = 255
        lower_color = np.array([l, l, l], dtype=np.uint8)
        upper_color = np.array([u, u, u], dtype=np.uint8)
        white_part = cv2.inRange(screen_map, lower_color, upper_color)  # 提取白色部分方便匹配

        # cv2_utils.show_image(white_part, win_name='check_and_click_sp_cn')
        part = cv2.bitwise_and(screen_map, screen_map, mask=white_part)
        ocr_result = self.ctx.ocr.match_words(part, words=[self.tp.cn],
                                              lcs_percent=self.ctx.game_config.special_point_lcs_percent)

        for r in ocr_result.values():
            to_click = r.max.center + screen_map_rect.left_top
            return self.ctx.controller.click(to_click)

        return False