"""货币战争动作上报:出战(report_action_start_battle_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
    game_state_of,
)


def report_action_start_battle_param(gs: GameState, param: Any, sig: ChannelSig,
                                     session: object = None,
                                     skip_substate: bool = False) -> LogicOutcome:
    """出战上报:hp/gold/streak 由结算屏观察覆盖接管,唯一逻辑推进 =
    免战牌跳过递减(上报时递减,非「验证落地后」;标记由出战 op 上报,
    递减 best-effort,未登记 → consume_use 返 None 零动作)。"""
    _validate_sig(sig, ('logic_action',))
    if skip_substate and session is not None:
        from sr_od.application.currency_war.kernel.cw_investments import (
            STRATEGY_EFFECTS,
        )
        _spec = STRATEGY_EFFECTS.get('免战牌')
        if _spec is not None:
            _left = game_state_of(session).effects.consume_use(_spec.id)
            if _left is not None:
                log.info('[cw][battle] 免战牌跳过上报 → 次数递减(余 %s)', _left)
                return LogicOutcome(
                    applied=True,
                    reason=f'remaining_uses→{_left}(跳过上报递减)')
    return LogicOutcome(applied=True)

