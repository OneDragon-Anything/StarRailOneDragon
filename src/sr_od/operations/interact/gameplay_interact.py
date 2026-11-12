from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class GameplayInteract(SrOperation):
    """按下玩法专用交互键(如翁法罗斯时光倒流),按住指定秒数后松开。
    起点:对应玩法画面;终点:原画面(交互动作完成)。
    """

    def __init__(self, ctx: SrContext, seconds: int = 0):
        """
        :param ctx: 上下文
        :param seconds: 按键持续秒数,0 为点按
        """
        SrOperation.__init__(self, ctx, op_name=gt('玩法交互'))

        self.seconds: int = seconds

    @operation_node(name='按键', is_start_node=True)
    def press(self) -> OperationRoundResult:
        self.ctx.controller.gameplay_interact(self.seconds)
        return self.round_success()
