from typing import Optional, Callable

from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class WaitInWorld(SrOperation):

    """
    等待加载 直到进入游戏主界面 右上角有角色图标
    """

    def __init__(self, ctx: SrContext, wait: float = 20,
                 wait_after_success: float = 0,
                 op_callback: Optional[Callable[[OperationResult], None]] = None):
        """
        :param ctx:
        :param wait: 最多等待秒数
        :param op_callback: 回调
        """
        SrOperation.__init__(self, ctx, op_name=gt('等待主界面'), timeout_seconds=wait, op_callback=op_callback)
        self.wait_after_success: float = wait_after_success

    @operation_node(name='画面识别', is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if common_screen_state.is_normal_in_world(self.ctx, screen):
            return self.round_success(wait=self.wait_after_success)

        return self.round_wait(wait=1)
