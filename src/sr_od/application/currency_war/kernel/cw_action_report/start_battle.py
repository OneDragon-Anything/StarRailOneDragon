"""货币战争动作上报:出战(report_action_start_battle_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留在 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。

**后果声明**(动作后果声明化迭代,详设 world-decl.md §2 表 #3):applied
出口构造 ``WorldDecl``(trigger = ``battle_resolve``;``next_screen`` =
结算屏,权威 = screens/prep.md §5 出战终结 + sim ``_resolve_battle``
呈现),转移事件广播随本动作单轨切换摘除。
"""

from __future__ import annotations

from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    SCREEN_SETTLE,
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
    game_state_of,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

#: 出战声明的推进分派类别(详设 §2 表 #3;封闭集单一源 = sim 后端
#: advance 分派表键集,值零新词沿用归并过程名)。
_DECL_TRIGGER: str = 'battle_resolve'


def report_action_start_battle_param(gs: GameState, param: Any, sig: ChannelSig,
                                     session: object = None,
                                     skip_substate: bool = False) -> LogicOutcome:
    """出战上报:hp/gold/streak 由结算屏观察覆盖接管,唯一逻辑推进 =
    免战牌跳过递减(上报时递减,非「验证落地后」;标记由出战 op 上报,
    递减 best-effort,未登记 → consume_use 返 None 零动作)。
    applied 出口构造后果声明(battle_resolve;喂入与消费面 =
    ``cw_sim_ports.declare_world`` / sim 后端 advance)。"""
    _validate_sig(sig, ('logic_action',))
    decl = WorldDecl(next_screen=SCREEN_SETTLE, trigger=_DECL_TRIGGER)
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
                    reason=f'remaining_uses→{_left}(跳过上报递减)',
                    world_decl=decl)
    return LogicOutcome(applied=True, world_decl=decl)
