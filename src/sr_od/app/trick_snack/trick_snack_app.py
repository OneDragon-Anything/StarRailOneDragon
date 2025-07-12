from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.custom_combine_op.custom_combine_op import CustomCombineOp


class TrickSnackApp(SrApplication):

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, 'trick_snack', op_name=gt('奇巧零食', 'game'),
                               run_record=ctx.trick_snack_run_record, need_notify=True)

    @operation_node(name='购买路线1', is_start_node=True)
    def buy_1(self) -> OperationRoundResult:
        if not self.ctx.trick_snack_config.route_yll6_xzq:
            return self.round_success('路线未启用')

        op = CustomCombineOp(self.ctx, 'buy_trick_snack_route_yll6_xzq', no_battle=True)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='购买路线1')
    @operation_node(name='购买路线2')
    def buy_2(self) -> OperationRoundResult:
        if not self.ctx.trick_snack_config.route_xzlf_xchzs:
            return self.round_success('路线未启用')

        op = CustomCombineOp(self.ctx, 'buy_trick_snack_route_xzlf_xchzs', no_battle=True)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='购买路线2')
    @operation_node(name='合成')
    def synthesize_trick_snack(self) -> OperationRoundResult:
        if not self.ctx.trick_snack_config.synthesize_trick_snack:
            return self.round_success('合成功能未启用')

        op = CustomCombineOp(self.ctx, 'synthesize_trick_snack', no_battle=True)
        result = op.execute()
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        return self.round_by_op_result(result)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    app = TrickSnackApp(ctx)
    app.execute()


if __name__ == '__main__':
    __debug()
