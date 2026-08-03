from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.application.currency_war import currency_war_const
from sr_od.application.currency_war.currency_war_run_record import CurrencyWarRunRecord
from sr_od.application.currency_war.operations.battle_loop import CurrencyWarRunLoop
from sr_od.application.currency_war.operations.entry.enter_currency_war import (
    EnterCurrencyWar,
)
from sr_od.application.currency_war.operations.entry.start_currency_war_match import (
    StartCurrencyWarMatch,
)
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext


class CurrencyWarApp(SrApplication):
    """货币战争应用。纯代码自主打完整局(无 LLM,实机验证):

    大世界 → 货币战争大厅(`EnterCurrencyWar`)→ 开始对局到备战(`StartCurrencyWarMatch`)
    → 对局循环到结束(`CurrencyWarRunLoop`:备战 买/升等级/deploy/出战 + 多类事件 + 结算回大厅)。

    naive 策略 + 购买经验升等级,实测赢下位面 1、打完整两位面局(输位面 2 boss)。
    打赢更高难度需 Strategy 精修(羁绊/经济/deploy 智能化,见 design.md)。
    """

    STATUS_AT_LOBBY: ClassVar[str] = EnterCurrencyWar.STATUS_AT_LOBBY

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(
            self, ctx, currency_war_const.APP_ID,
            op_name=gt('货币战争', 'game'),
            run_record=CurrencyWarRunRecord(ctx.current_instance_idx),
        )

    @operation_node(name='进入货币战争大厅', is_start_node=True)
    def _enter_lobby(self) -> OperationRoundResult:
        op = EnterCurrencyWar(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='进入货币战争大厅')
    @operation_node(name='开始对局到备战阶段')
    def _start_match(self) -> OperationRoundResult:
        op = StartCurrencyWarMatch(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始对局到备战阶段')
    @operation_node(name='对局循环到结束')
    def _run_loop(self) -> OperationRoundResult:
        op = CurrencyWarRunLoop(self.ctx)
        return self.round_by_op_result(op.execute())
