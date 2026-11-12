from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ClickPoint(SrOperation):
    """点击指定坐标(1080p 游戏空间)。非 MCP 传参单元:point 参数为运行时
    坐标对象,仅限代码内调用。
    起点:任意画面;终点:原画面(点击动作完成,后续画面由点击目标决定)。
    """

    def __init__(self, ctx: SrContext, point: Point):
        """
        :param ctx: 上下文
        :param point: 点击坐标(1920×1080 游戏空间)
        """
        SrOperation.__init__(
            self, ctx,
            op_name='%s %s' % (
                gt('点击'),
                point
            ),
        )
        self.point: Point = point

    @operation_node(name='点击', is_start_node=True)
    def click(self) -> OperationRoundResult:
        if not self.ctx.controller.click(self.point):
            return self.round_retry('点击失败', wait=1)
        else:
            return self.round_success(wait=1)