from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.sim_uni_const import SimUniPath
from sr_od.config import game_const
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class SimUniChoosePath(SrOperation):

    PATH_RECT: ClassVar[Rect] = Rect(134, 665, 1788, 708)  # 命途
    CONFIRM_BTN: ClassVar[Rect] = Rect(1529, 957, 1869, 1006)  # 确认命途

    def __init__(self, ctx: SrContext, path: SimUniPath):
        """
        需要在模拟宇宙-选择命途页面中使用
        选择对应的命途
        :param ctx:
        :param path: 目标命途
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('选择命途')),
                             )
        self.path: SimUniPath = path

    @operation_node(name='选择命途', node_max_retry_times=5, is_start_node=True)
    def _choose_target_path(self) -> OperationRoundResult:
        """
        选择命途
        :return:
        """
        screen = self.screenshot()

        if not sim_uni_screen_state.in_sim_uni_choose_path(self.ctx, screen):
            return self.round_retry('未在模拟宇宙命途页面', wait=1)

        area = self.ctx.screen_loader.get_area('模拟宇宙', '入口-命途区域')
        result = self.round_by_ocr_and_click(screen, self.path.value, area=area)
        if result.is_success:
            return self.round_success(wait=1)

        # 找不到的时候往右滑一下
        drag_from = game_const.STANDARD_CENTER_POS
        drag_to = drag_from + Point(-200, 0)
        self.ctx.controller.drag_to(end=drag_to, start=drag_from)
        return self.round_retry('未找到目标命途', wait=1)

    @node_from(from_name='选择命途')
    @operation_node(name='确认命途')
    def _confirm_path(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '入口-确认命途',
                                                 success_wait=1, retry_wait=1)
