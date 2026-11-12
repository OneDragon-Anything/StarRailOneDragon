from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class WaitInSeconds(SrOperation):
    """在当前画面原地等待指定秒数,不做任何操作(如疾跑后等角色停稳再截图)。
    起点:任意画面;终点:原画面。
    """

    def __init__(self, ctx: SrContext, seconds: float = 10):
        """
        :param ctx: 上下文
        :param seconds: 等待秒数,支持小数
        """
        SrOperation.__init__(self, ctx, op_name=gt('等待秒数 %.2f') % seconds)
        self.seconds: float = float(seconds)

    @operation_node(name='等待', is_start_node=True)
    def wait_seconds(self) -> OperationRoundResult:
        return self.round_success(wait=self.seconds)
