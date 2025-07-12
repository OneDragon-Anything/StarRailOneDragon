from typing import Optional

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.sr_map.operations.transport_by_map import TransportByMap
from sr_od.sr_map.sr_map_def import SpecialPoint


class TransportToRecover(SrOperation):

    def __init__(self, ctx: SrContext, tp: Optional[SpecialPoint] = None):
        """
        到一个传送点恢复
        :param ctx: 上下文
        :param tp: 当前传送点
        """
        self.tp: SpecialPoint = ctx.map_data.best_match_sp_by_all_name(
            '空间站「黑塔」',
            '主控舱段',
            '核心通路'
        )
        # TODO 如果已经当前传送点 就找一个近的恢复

        SrOperation.__init__(
            self, ctx,
            op_name='%s %s %s %s' % (
                gt('传送恢复'),
                self.tp.planet.display_name,
                self.tp.region.display_name,
                self.tp.display_name
            ))

    @operation_node(name='传送', is_start_node=True)
    def transport(self) -> OperationRoundResult:
        op = TransportByMap(self.ctx, self.tp)
        return self.round_by_op_result(op.execute())
