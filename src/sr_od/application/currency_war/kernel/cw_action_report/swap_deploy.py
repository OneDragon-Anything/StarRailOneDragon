"""货币战争动作上报:bench ↔ deployed 换位(report_action_swap_deploy_param)。

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
    _validate_sig,
    bench_slots_of,
    bench_view_of_slots,
    deployed_slots_of,
    deployed_slots_to_rows,
)


def report_action_swap_deploy_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """bench ↔ deployed 换位上报:原槽对调(置空/置位不移位坐标系)+
    上场者继承下场者排(含开拓者形态归一,``_apply_row_to_char``)+
    同名唯一性守卫(W43 裁决 1,与 simulate 同源)。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_exec_state import (
        _apply_row_to_char,
        deployed_slot_no,
    )
    from sr_od.application.currency_war.kernel.cw_vocab import (
        board_unique_key,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionSwapDeployParam',
                       evidence=evidence, sig=_grp_sig)

    d_idx = int(param.deployed_idx)
    b_idx = int(param.bench_idx)
    dep_slots = deployed_slots_of(gs)
    bench_slots = bench_slots_of(gs)
    if not (0 <= d_idx < len(dep_slots)) or dep_slots[d_idx] is None \
            or not (0 <= b_idx < len(bench_slots)) \
            or bench_slots[b_idx] is None:
        return LogicOutcome(
            applied=False, reason=f'idx_out_of_range:d{d_idx}/b{b_idx}')
    out_char = dep_slots[d_idx]
    in_char = bench_slots[b_idx]
    if (getattr(param, 'expect_deployed', '')
            and out_char.char_id != param.expect_deployed) \
            or (getattr(param, 'expect_bench', '')
                and in_char.char_id != param.expect_bench):
        return LogicOutcome(
            applied=False,
            reason=(f'stale_proposal:{param.expect_deployed}'
                    f'/{param.expect_bench}'
                    f'!={out_char.char_id}/{in_char.char_id}'))
    _k = board_unique_key(in_char)
    if _k is not None and any(
            board_unique_key(d) == _k
            for _i, d in enumerate(dep_slots)
            if d is not None and _i != d_idx):
        return LogicOutcome(applied=False, reason=f'duplicate_on_board:{_k}')
    scratch_d = list(dep_slots)
    scratch_b = list(bench_slots)
    scratch_d[d_idx] = in_char
    scratch_b[b_idx] = out_char
    _apply_row_to_char(in_char, out_char.position_pref)
    in_char.slot = deployed_slot_no(d_idx)
    _w(gs.bench, bench_view_of_slots(scratch_b), 'proj_swap_bench')
    front, back = deployed_slots_to_rows(scratch_d)
    _w(gs.front_row, front, 'proj_deployed_front')
    _w(gs.back_row, back, 'proj_deployed_back')
    return LogicOutcome(applied=True,
                        reason=str(getattr(param, 'reason', '') or ''))

