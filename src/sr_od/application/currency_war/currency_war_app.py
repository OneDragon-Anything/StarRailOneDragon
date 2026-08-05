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

    **中间态接手(D-26,2026-08-04)**:app 不再总从大世界线性起 —— 各入口 op 先检测当前态,
    已在 CW(大厅/对局中)就跳过 enter/start、直接进 loop。故 bot crash/重启/手动接管后,
    从任何态(大世界 / 大厅 / 备战 / 事件 / 战斗 / 结算)重跑 app 都能 resume,不卡 entry。

    naive 策略 + 购买经验升等级,实测赢下位面 1、打完整两位面局(输位面 2 boss)。
    打赢更高难度需 Strategy 精修(羁绊/经济/deploy 智能化,见 design.md)。
    """

    STATUS_AT_LOBBY: ClassVar[str] = EnterCurrencyWar.STATUS_AT_LOBBY

    # 对局中态 OCR 锚点(备战 / 事件 overlay / 战斗结算)—— 命中任一 = 已在对局里,跳过 enter+start
    _IN_MATCH_KEYWORDS: ClassVar[tuple[str, ...]] = (
        '购买经验', '备战阶段', '投资策略', '投资环境', '补给阶段',
        '遭遇其一', '盛会之星', '出战', '挑战结束', '请选择投资',
    )

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(
            self, ctx, currency_war_const.APP_ID,
            op_name=gt('货币战争', 'game'),
            run_record=CurrencyWarRunRecord(ctx.current_instance_idx),
        )

    def _at_lobby(self, screen) -> bool:
        """已在货币战争大厅(「创业指南」大厅独有锚点,lobby screen_info area)。"""
        return self.round_by_find_area(screen, EnterCurrencyWar.LOBBY_SCREEN, '标识-创业指南').is_success

    def _in_match(self, screen) -> bool:
        """已在货币战争对局中(备战/事件/战斗/结算任一态)。"""
        return any(self.round_by_ocr(screen, kw).is_success for kw in self._IN_MATCH_KEYWORDS)

    @operation_node(name='进入货币战争大厅', is_start_node=True)
    def _enter_lobby(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 中间态接手(D-26):已在 CW(大厅/对局中)→ 跳过 enter(无需从大世界进)。
        if self._at_lobby(screen) or self._in_match(screen):
            return self.round_success('已在 CW(大厅/对局中),跳过 enter')
        op = EnterCurrencyWar(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='进入货币战争大厅')
    @operation_node(name='开始对局到备战阶段')
    def _start_match(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 中间态接手(D-26):已在对局中 → 跳过 start(无需从大厅开始),直接交 loop。
        if self._in_match(screen):
            return self.round_success('已在对局中,跳过 start 交 loop')
        op = StartCurrencyWarMatch(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始对局到备战阶段')
    @operation_node(name='对局循环到结束')
    def _run_loop(self) -> OperationRoundResult:
        op = CurrencyWarRunLoop(self.ctx)
        return self.round_by_op_result(op.execute())
