from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.custom_combine_op.custom_combine_op import CustomCombineOp


class MemoryCrystalShardApp(SrApplication):

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, 'memory_crystal_shard',
                               op_name=gt('领取记忆残晶', 'ui'),
                               run_record=ctx.memory_crystal_shard_run_record,
                               need_notify=True)

    @operation_node(name='执行自定义指令', is_start_node=True)
    def run_op(self) -> OperationRoundResult:
        op = CustomCombineOp(self.ctx, 'memory_crystal_shard', no_battle=True)
        result = op.execute()
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        return self.round_by_op_result(result)