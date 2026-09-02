"""货币战争 简报 op(W971 P3a 新入口薄封装;01-opening §1)。

开局序列第一步:简报观察(词缀/敌人难度/三 boss)+ 词缀效果采集(best-effort)
+ 点「下一步」。观察/采集/点击的完整现役逻辑在 ``HandleBriefing``——本 op 是
薄封装委托(handler 退役归 P3b),额外职责:
① 写局状态 session(01-opening §1:替代 ctx 信箱;现役 battle_loop 靠
   ``__init__`` 从 ctx copy,过渡期两处都写,接线批拆 ctx 信箱);
② 完成承诺 = DD-011 形态①固定时长(BRIEFING_SETTLE_S,#1 锚后 ~1s)。

下游链路(不变):session.briefing_affixes → state.enemy_affixes → mechanics_fit;
session.briefing_bosses(位面序真值,ADR-0397)→ state.plane_bosses → boss_fit。
"""
from collections.abc import Callable
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.operations.cw_flow.cw_flow_const import (
    BRIEFING_SETTLE_S,
)
from sr_od.application.currency_war.operations.handlers.handle_briefing import (
    HandleBriefing,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class BriefingOp(SrOperation):
    """简报:委托 HandleBriefing(观察+采集+点下一步+出口验转移)→ 写 session → 固定时长交回。"""

    #: 与 HandleBriefing.SCREEN_NAME 同源(简报独有 id_mark「标识-本场对局首领」)。
    SCREEN_NAME: ClassVar[str] = HandleBriefing.SCREEN_NAME
    MARK_AREA: ClassVar[str] = '标识-本场对局首领'
    #: 现役 handler 工厂(薄封装委托;P3b handler 退役后内联观察+采集+点下一步)。
    HANDLER_FACTORY: ClassVar[Callable[[SrContext], SrOperation]] = HandleBriefing

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-简报(开局序列)')

    @operation_node(name='简报', is_start_node=True, node_max_retry_times=3)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            # 非简报屏(接管局/序列中后段首帧分流)→ fail 交编排壳按步分流。
            return self.round_fail('非简报屏')
        _handler = self.HANDLER_FACTORY(self.ctx)
        _result = self.round_by_op_result(_handler.execute())
        if not _result.is_success:
            return _result
        self._sync_session()
        # 完成承诺 = DD-011 形态①:锚已验消失(handler 出口),固定时长等动画完结。
        return self.round_success('已离开简报(写局状态完成)', wait=BRIEFING_SETTLE_S)

    def _sync_session(self) -> None:
        """ctx 信箱 → session 局状态(对局已建时;简报先于 loop 建 match,
        正常开局走 battle_loop.__init__ copy,本写点服务接管/重入场景)。"""
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is None:
            return
        _match.session.briefing_affixes = list(self.ctx.cw_briefing_affixes or [])
        _match.session.briefing_bosses = list(self.ctx.cw_briefing_bosses or [])
        _match.session.enemy_difficulty = self.ctx.cw_enemy_difficulty
        log.info('[cw-flow-briefing] session 写入: affixes=%s bosses=%s difficulty=%s',
                 _match.session.briefing_affixes,
                 _match.session.briefing_bosses,
                 _match.session.enemy_difficulty)
