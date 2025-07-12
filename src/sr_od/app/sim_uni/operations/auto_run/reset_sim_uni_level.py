from typing import ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni.operations.entry.choose_sim_uni_num import ChooseSimUniNum
from sr_od.app.sim_uni.operations.entry.sim_uni_start import SimUniStart
from sr_od.context.sr_context import SrContext
from sr_od.operations.interact.move_interact import MoveInteract
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.wait.wait_in_world import WaitInWorld


class ResetSimUniLevel(SrOperation):

    TEMP_LEAVE: ClassVar[Rect] = Rect  # 暂离

    def __init__(self, ctx: SrContext):
        """
        需要在模拟宇宙 移动画面中使用
        暂离后重新进入 用于重置位置 脱困
        :param ctx:
        """
        SrOperation.__init__(
            self, ctx,
            op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('暂离重进')),
        )

    @operation_node(name='暂离', node_max_retry_times=10, is_start_node=True)
    def _temp_leave(self) -> OperationRoundResult:
        """
        暂离
        :return:
        """
        screen = self.screenshot()
        result = self.round_by_find_and_click_area(screen, '模拟宇宙', '菜单-暂离')
        if result.is_success:
            return self.round_success(result.status, wait=5)
        else:
            self.ctx.controller.esc()  # 打开菜单
            return self.round_retry(status=result.status, wait=1)

    @node_from(from_name='暂离')
    @operation_node(name='等待退出')
    def _wait_exit(self) -> OperationRoundResult:
        op = WaitInWorld(self.ctx, wait_after_success=1)
        op_result = op.execute()
        if op_result.success:
            return self.round_success()
        else:
            return self.round_fail()

    @node_from(from_name='等待退出')
    @operation_node(name='黑塔办公室交互')
    def _interact(self) -> OperationRoundResult:
        op = MoveInteract(self.ctx, '模拟宇宙', lcs_percent=0.1, single_line=True)
        op_result = op.execute()
        if op_result.success:
            return self.round_success(wait=2)
        else:
            return self.round_fail('加载失败')

    @node_from(from_name='黑塔办公室交互')
    @operation_node(name='选择宇宙')
    def _choose_uni(self) -> OperationRoundResult:
        """
        选择宇宙
        :return:
        """
        op = ChooseSimUniNum(self.ctx, num=1)  # 继续之前的 哪个宇宙没所谓
        op_result = op.execute()
        if op_result.success:
            return self.round_success()
        else:
            return self.round_fail('选择宇宙失败')

    @node_from(from_name='选择宇宙')
    @operation_node(name='继续挑战')
    def _continue(self) -> OperationRoundResult:
        op = SimUniStart(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_success()
        else:
            return self.round_fail('继续进度失败')

    @node_from(from_name='继续挑战')
    @operation_node(name='等待模拟宇宙加载')
    def _wait(self) -> OperationRoundResult:
        op = WaitInWorld(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_success()
        else:
            return self.round_fail('加载失败')
