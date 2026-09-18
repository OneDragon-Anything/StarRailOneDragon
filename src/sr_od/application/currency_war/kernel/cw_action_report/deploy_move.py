"""货币战争动作上报:上阵单步(report_action_deploy_move_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    BENCH_CAPACITY_DEFAULT,
    BenchSlot,
    BenchView,
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    _validate_sig,
    deployed_slots_of,
    deployed_slots_to_rows,
)


def report_action_deploy_move_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """上阵上报:bench 源槽摘槽(原生 BenchSlot 形态)+ deployed 目标排
    首空落位(``deployed_place`` 单一源,按 position_pref 路由首选排,
    排满 fallback 另一排)+ board 羁绊计数派生重算(行写端挂钩
    ``_resync_board_delta`` 自动,禁手写 board)。
    to_row 非法/源槽空/两排全满 = applied=False 零写(陈旧提案)。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_exec_state import (
        BenchChar,
        deployed_place,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionDeployMoveParam',
                       evidence=evidence, sig=_grp_sig)

    _bview = gs.bench.value
    bench_slots = list(_bview.slots) if _bview is not None else []
    dep_slots = deployed_slots_of(gs)
    from_idx = int(param.bench_idx)   # 槽位表下标直取(统一坐标系)
    to_row = getattr(param, 'to_row', '')
    if to_row not in ('front', 'back'):
        return LogicOutcome(applied=False,
                            reason=f'to_row_invalid:{to_row!r}')
    if not (0 <= from_idx < len(bench_slots)) \
            or bench_slots[from_idx] is None \
            or bench_slots[from_idx].kind != 'unit' \
            or bench_slots[from_idx].unit is None:
        return LogicOutcome(applied=False,
                            reason=f'bench_idx_out_of_range:{from_idx}')
    _mu = bench_slots[from_idx].unit
    moved = BenchChar(slot=from_idx + 1,
                      char_id=str(_mu.char_id or ''),
                      star=int(_mu.star or 1),
                      equips=list(_mu.equips or []))
    scratch = list(dep_slots)
    moved.position_pref = to_row
    placed_idx = deployed_place(scratch, moved)
    if placed_idx is None:
        return LogicOutcome(applied=False, reason='deployed_full')
    bench_slots[from_idx] = BenchSlot(kind='empty')
    _w(gs.bench, BenchView(slots=bench_slots,
                           capacity=(_bview.capacity
                                     if _bview is not None
                                     else BENCH_CAPACITY_DEFAULT)),
       'proj_deploy_src_clear')
    front, back = deployed_slots_to_rows(scratch)
    _w(gs.front_row, front, 'proj_deploy_front')
    _w(gs.back_row, back, 'proj_deploy_back')
    return LogicOutcome(applied=True)

