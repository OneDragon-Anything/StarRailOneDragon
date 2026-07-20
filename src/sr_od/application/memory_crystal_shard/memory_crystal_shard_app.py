from one_dragon.base.operation.operation_notify import NotifyTiming, node_notify
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.application.memory_crystal_shard import memory_crystal_shard_const
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.custom_combine_op.custom_combine_op import CustomCombineOp


class MemoryCrystalShardApp(SrApplication):

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, memory_crystal_shard_const.APP_ID,
                               op_name=gt('领取记忆残晶'),
                               run_record=ctx.memory_crystal_shard_run_record)

    @node_notify(when=NotifyTiming.CURRENT_DONE)
    @operation_node(name='执行自定义指令', is_start_node=True)
    def run_op(self) -> OperationRoundResult:
        op = CustomCombineOp(self.ctx, 'memory_crystal_shard', no_battle=True)
        result = op.execute()
        return self.round_by_op_result(result)
