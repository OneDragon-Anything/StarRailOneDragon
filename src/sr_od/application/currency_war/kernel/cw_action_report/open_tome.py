"""货币战争动作上报:开秘密典籍(report_action_open_tome_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    BenchView,
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    _validate_sig,
)


def report_action_open_tome_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """开秘密典籍上报:bench 槽位 kind → empty(开件即腾席,占席事实
    进容器)。槽不存在/类型不符 = applied=False 零写(陈旧提案)。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionOpenTomeParam',
                       evidence=evidence, sig=_grp_sig)

    view = gs.bench.value
    if view is None:
        return LogicOutcome(applied=True, reason='bench_unobserved')
    slots = list(view.slots)
    _idx = (int(param.slot) - 1 if param.slot is not None
            else next((i for i, s in enumerate(slots)
                       if s is not None and s.kind == 'tome'), None))
    if _idx is None or not (0 <= _idx < len(slots)) \
            or slots[_idx] is None or slots[_idx].kind != 'tome':
        return LogicOutcome(applied=False, reason='tome_slot_missing')
    slots[_idx] = BenchSlot(kind='empty')
    _w(gs.bench, BenchView(slots=slots, capacity=view.capacity),
       'proj_open_item_clear')
    return LogicOutcome(applied=True)

