from typing import Optional

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ClickDialogConfirm(SrOperation):
    """点击通用确认对话框的「确认」按钮(如模拟宇宙丢弃奇物/祝福的确认)。
    起点:任意出现确认对话框的画面;终点:弹窗已确认关闭(后续画面由调用场景决定)。
    """

    def __init__(self, ctx: SrContext,
                 wait_after_success: Optional[int] = None):
        """
        :param ctx: 上下文
        :param wait_after_success: 点击成功后等待的秒数(None 用框架默认)
        """
        SrOperation.__init__(self, ctx, op_name=gt('点击确认'))
        self.wait_after_success: Optional[int] = wait_after_success

    @operation_node(name='点击', is_start_node=True)
    def click(self) -> OperationRoundResult:
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(screen, '通用画面', '对话框-确认',
                                                 success_wait=self.wait_after_success, retry_wait=1)
