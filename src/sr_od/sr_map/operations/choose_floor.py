from cv2.typing import MatLike
from typing import Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.sr_map import large_map_utils


class ChooseFloor(SrOperation):

    def __init__(self, ctx: SrContext, floor: int, sub_region: bool = False):
        self.floor: int = floor
        self.target_floor_str = gt('%d层' % self.floor, 'ocr')
        self.neg_target_floor_str = gt('%d层' % (-self.floor), 'ocr')
        self.sub_region: bool = sub_region  # 是否子地图
        SrOperation.__init__(self, ctx, op_name='%s %d' % (gt('选择楼层'), floor))

    @operation_node(name='画面识别', node_max_retry_times=20, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.screenshot()

        # 已经选好了区域 还需要选择层数
        if self.floor != 0:
            current_floor_str = large_map_utils.get_active_floor(self.ctx, screen)
            log.info('当前层数 %s', current_floor_str)
            if current_floor_str is None:
                log.error('未找到当前选择的层数')
            log.info('目标层数 %s', self.target_floor_str)
            if self.target_floor_str != current_floor_str:
                cl = self.click_target_floor(screen)
                if not cl:
                    log.error('未成功点击层数')
                    return self.round_retry(wait=0.5)
                else:
                    return self.round_success(wait=0.5)
            else:  # 已经是目标楼层
                return self.round_success(wait=0.5)
        else:
            return self.round_success()

    def click_target_floor(self, screen) -> bool:
        """
        点击目标层数
        :param screen: 大地图界面截图
        :return:
        """
        pos = self.get_target_floor_pos(screen)
        if pos is not None:
            log.debug('选择楼层点击 %s', pos)
            return self.ctx.controller.click(pos)
        else:
            return False

    def get_target_floor_pos(self, screen: MatLike) -> Optional[Point]:
        """
        获取目标楼层的位置
        :param screen:
        :return:
        """
        area = self.ctx.screen_loader.get_area('大地图', '楼层列表')
        part = cv2_utils.crop_image_only(screen, area.rect)
        # cv2_utils.show_image(part, wait=0)
        ocr_results = self.ctx.ocr.run_ocr(part)

        if self.target_floor_str in ocr_results:
            mrl = ocr_results[self.target_floor_str]
        elif self.floor < 0 and self.neg_target_floor_str in ocr_results:  # 中文负数的识别结果比较不好 看看有没有正数的结果
            mrl = ocr_results[self.neg_target_floor_str]
        else:
            mrl = None

        if mrl is None:
            return None
        elif len(mrl) == 1:
            return mrl.max.center + area.rect.left_top
        else:
            target_mr: Optional[MatchResult] = None
            for mr in mrl:
                if (
                        target_mr is None
                        or (self.floor < 0 and mr.center.y > target_mr.center.y)  # 负数楼层选y轴大的
                        or (self.floor > 0 and mr.center.y < target_mr.center.y)  # 正数楼层选y轴小的
                ):
                    target_mr = mr
            return target_mr.center + area.rect.left_top
