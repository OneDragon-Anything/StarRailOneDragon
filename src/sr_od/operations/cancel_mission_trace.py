from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class CancelMissionTrace(SrOperation):

    STATUS_CANCELLED: ClassVar[str] = '已取消'
    STATUS_CLICK_TRACE: ClassVar[str] = '尝试点击追踪任务'

    def __init__(self, ctx: SrContext):
        """
        尝试取消任务追踪 在需要使用大地图的app启动时调用
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name=gt('取消任务追踪'))

        self.in_world_times: int = 0  # 判断在大世界的次数

    @operation_node(name='点击追踪任务', is_start_node=True)
    def _try_open_mission(self) -> OperationRoundResult:
        """
        有任务追踪时 左方有一个当前追踪的显示
        尝试点击左方这个任务唤出任务列表
        :return:
        """
        if self.ctx.pos_info.pos_cancel_mission_trace:
            return self.round_success()

        return self.round_by_click_area('大世界', '追踪任务图标',
                                          success_wait=1, retry_wait=1)

    @node_from(from_name='点击追踪任务')
    @operation_node(name='取消追踪')
    def _cancel_trace(self) -> OperationRoundResult:
        """
        根据当前屏幕状态 尝试取消追踪
        :return:
        """
        screen = self.screenshot()
        if common_screen_state.is_normal_in_world(self.ctx, screen):  # 依旧在大地图 说明没有追踪任务
            self.ctx.pos_info.pos_cancel_mission_trace = True
            return self.round_success()

        return self.round_by_find_and_click_area(screen, '任务', '按钮-停止追踪',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='取消追踪')
    @node_from(from_name='取消追踪', success=False)
    @operation_node(name='取消后返回')
    def back_to_normal_world(self) -> OperationRoundResult:
        """
        返回大世界
        :return:
        """
        self.ctx.pos_info.pos_cancel_mission_trace = True
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())
