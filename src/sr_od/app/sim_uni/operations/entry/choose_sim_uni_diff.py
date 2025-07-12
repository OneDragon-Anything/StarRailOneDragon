from cv2.typing import MatLike
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class ChooseSimUniDiff(SrOperation):

    DIFF_POINT_MAP: ClassVar[dict[int, Point]] = {
        1: Point(132, 166),
        2: Point(132, 269),
        3: Point(132, 380),
        4: Point(132, 485),
        5: Point(132, 597),
    }

    def __init__(self, ctx: SrContext, num: int):
        """
        需要在模拟宇宙入口页面中使用 且先选择了普通模拟宇宙
        选择对应的难度
        :param ctx:
        :param num: 难度 支持 1~5
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s %s' % (gt('模拟宇宙', 'game'), gt('选择难度'),
                                                   gt('默认') if num == 0 else str(num))
                             )

        self.num: int = num

    @operation_node(name='选择', node_max_retry_times=5, is_start_node=True)
    def choose(self) -> OperationRoundResult:
        if self.num == 0:  # 默认难度
            return self.round_success()
        screen: MatLike = self.screenshot()

        if not common_screen_state.in_secondary_ui(
                self.ctx, screen,
                sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value):
            return self.round_retry('未在模拟宇宙页面', wait=1)

        if not self.ctx.controller.click(ChooseSimUniDiff.DIFF_POINT_MAP[self.num]):
            return self.round_retry('点击难度失败', wait=1)

        return self.round_success(wait=1)
