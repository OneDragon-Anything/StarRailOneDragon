from cv2.typing import MatLike
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class SimUniStart(SrOperation):

    STATUS_RESTART: ClassVar[str] = '重新开始'
    STATUS_CONTINUE: ClassVar[str] = '继续'

    def __init__(self, ctx: SrContext):
        """
        需要在模拟宇宙入口页面中使用 且先选择了普通模拟宇宙
        选择 重新开始 或 继续
        :param ctx:
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('开始挑战'))
                             )

    @operation_node(name='开始', is_start_node=True)
    def _restart_or_continue(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()

        if not sim_uni_screen_state.in_sim_uni_secondary_ui(self.ctx, screen):
            return self.round_retry('未在模拟宇宙页面', wait=1)

        result = self.round_by_find_and_click_area(screen, '模拟宇宙', '入口-下载初始角色')
        if result.is_success:
            return self.round_success(status=result.status, wait=2)

        result = self.round_by_find_and_click_area(screen, '模拟宇宙', '入口-继续')
        if result.is_success:
            return self.round_success(status=result.status, wait=2)

        return self.round_retry('点击开始失败', wait=1)

    @node_from(from_name='开始', status='入口-下载初始角色')
    @operation_node(name='启动模拟宇宙')
    def _start(self) -> OperationRoundResult:
        """
        启动模拟宇宙
        :return:
        """
        screen: MatLike = self.screenshot()
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '入口-启动模拟宇宙',
                                                 success_wait=2, retry_wait=1)

    @node_from(from_name='启动模拟宇宙')
    @operation_node(name='确认')
    def _confirm(self) -> OperationRoundResult:
        """
        低等级确认
        :return:
        """
        screen: MatLike = self.screenshot()

        if sim_uni_screen_state.in_sim_uni_choose_path(self.ctx, screen):
            return self.round_success()

        return self.round_by_find_and_click_area(screen, '模拟宇宙', '入口-低等级确认',
                                                 success_wait=2, retry_wait=1)

    @node_from(from_name='确认')
    @node_from(from_name='确认', success=False)  # 不一定有对话框确认
    @operation_node(name='完成')
    def finish(self) -> OperationRoundResult:
        return self.round_success(SimUniStart.STATUS_RESTART)

    @node_from(from_name='开始', status='入口-继续')
    @operation_node(name='继续-完成')
    def continue_finish(self) -> OperationRoundResult:
        return self.round_success(SimUniStart.STATUS_CONTINUE)
