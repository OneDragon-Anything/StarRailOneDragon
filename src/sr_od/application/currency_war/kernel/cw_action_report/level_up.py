"""货币战争动作上报:购买经验(单击/多击)(report_action_level_up_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    _validate_sig,
    level_of,
)


def report_action_level_up_param(gs: GameState, param: Any, sig: ChannelSig,
                                 executed: ShopActionExecuted | None = None) -> LogicOutcome:
    """购买经验上报(单击/多击):xp/level 跨门槛推进(推进算子单一源 =
    ``xp_apply_clicks``,跨级连跳+溢出结转)+ gold −cost×clicks 直写。
    满级 = applied=False + reason='level_cap' 零写(MAX_PLAYER_LEVEL
    封顶单一源);executed None = 击数自算 1(理想执行,sim 路径)。
    CwActionLevelUpShopParam 同字段双类型共用本函数。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_economy import (
        MAX_PLAYER_LEVEL,
        XP_TO_NEXT_LEVEL,
        xp_apply_clicks,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionLevelUpParam',
                       evidence=evidence, sig=_grp_sig)

    clicks = executed.levelup_clicks if executed is not None else 1
    if clicks is None:
        return LogicOutcome(applied=False, reason='levelup_clicks_not_fed')
    clicks = max(0, int(clicks))
    if level_of(gs) >= MAX_PLAYER_LEVEL:
        return LogicOutcome(applied=False, reason='level_cap')
    g = gs.gold.value
    if g is not None:
        _w(gs.gold, int(g) - int(getattr(param, 'cost', 0) or 0) * clicks,
           'proj_levelup_gold')
    _lv_v = gs.level.value
    xp_v = gs.xp.value
    if xp_v is not None and _lv_v is not None:
        _new_lvl, _cur = xp_apply_clicks(int(_lv_v), int(xp_v[0]), clicks)
        _w(gs.xp, (_cur, XP_TO_NEXT_LEVEL.get(_new_lvl, _cur)),
           'proj_levelup_xp')
        if _new_lvl != int(_lv_v):
            _w(gs.level, _new_lvl, 'proj_levelup_level')
    return LogicOutcome(applied=True)

