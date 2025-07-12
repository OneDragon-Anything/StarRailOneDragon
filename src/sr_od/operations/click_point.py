from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ClickPoint(SrOperation):

    def __init__(self, ctx: SrContext, point: Point):
        """
        点击指定坐标
        :param ctx: 上下文
        :param point: 坐标
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