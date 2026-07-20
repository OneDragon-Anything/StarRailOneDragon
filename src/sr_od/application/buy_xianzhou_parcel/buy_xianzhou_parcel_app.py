from one_dragon.base.operation.operation_notify import NotifyTiming, node_notify
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.application.buy_xianzhou_parcel import buy_xianzhou_parcel_const
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.custom_combine_op.custom_combine_op import CustomCombineOp


class BuyXianzhouParcelApp(SrApplication):

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, buy_xianzhou_parcel_const.APP_ID,
                               op_name=gt('仙舟过期邮包'),
                               run_record=ctx.buy_xz_parcel_run_record)

    @node_notify(when=NotifyTiming.CURRENT_DONE)
    @operation_node(name='执行自定义指令', is_start_node=True)
    def run_op(self) -> OperationRoundResult:
        op = CustomCombineOp(self.ctx, 'buy_xianzhou_parcel', no_battle=True)
        result = op.execute()
        return self.round_by_op_result(result)

