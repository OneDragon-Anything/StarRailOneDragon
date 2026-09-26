"""货币战争动作上报:bench ↔ deployed 换位(report_action_swap_deploy_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察写
端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    DEPLOYED_FRONT_CAPACITY_DEFAULT,
    BenchSlot,
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    _validate_sig,
    bench_view_of_working,
    deployed_indexed_of_view,
    deployed_view_of_indexed,
)


def report_action_swap_deploy_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """bench ↔ deployed 换位上报:原槽对调(置空/置位不移位坐标系)+
    上场者继承下场者排(排归属 = 子表承载,overlay-trigger 3.1;含开拓者
    形态归一,归一核单一源 = ``cw_exec_state.trailblazer_row_identity``)+
    同名唯一性守卫(W43 裁决 1,与 simulate 同源)。

    P1 容器原生:bench 写回 = 工作槽表直构(占位件 kind 原样保留,
    原换形口降级路径退役);deployed = 单字段视图整值替换(3.1 合一写)。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_exec_state import (
        trailblazer_row_unit,
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
    _bview = gs.bench.value
    bench_slots = list(_bview.slots) if _bview is not None else []
    view = gs.deployed.value
    dep_slots = deployed_indexed_of_view(view)
    if not (0 <= d_idx < len(dep_slots)) or dep_slots[d_idx] is None \
            or not (0 <= b_idx < len(bench_slots)) \
            or bench_slots[b_idx] is None \
            or bench_slots[b_idx].kind != 'unit' \
            or bench_slots[b_idx].unit is None:
        return LogicOutcome(
            applied=False, reason=f'idx_out_of_range:d{d_idx}/b{b_idx}')
    out_unit = dep_slots[d_idx]
    in_slot = bench_slots[b_idx]
    in_unit = in_slot.unit
    if (getattr(param, 'expect_deployed', '')
            and out_unit.char_id != param.expect_deployed) \
            or (getattr(param, 'expect_bench', '')
                and in_unit.char_id != param.expect_bench):
        return LogicOutcome(
            applied=False,
            reason=(f'stale_proposal:{param.expect_deployed}'
                    f'/{param.expect_bench}'
                    f'!={out_unit.char_id}/{in_unit.char_id}'))
    _k = board_unique_key(in_unit)
    if _k is not None and any(
            board_unique_key(d) == _k
            for _i, d in enumerate(dep_slots)
            if d is not None and _i != d_idx):
        return LogicOutcome(applied=False, reason=f'duplicate_on_board:{_k}')
    # 上场者继承下场者排(排归属 = 子表承载)+ 开拓者形态归一(与
    # mutate_bench_deployed 同核)。
    _row = 'front' if d_idx < DEPLOYED_FRONT_CAPACITY_DEFAULT else 'back'
    scratch_d = list(dep_slots)
    scratch_b = list(bench_slots)
    scratch_d[d_idx] = trailblazer_row_unit(in_unit, _row)
    scratch_b[b_idx] = BenchSlot(kind='unit', unit=out_unit)
    _w(gs.bench, bench_view_of_working(scratch_b, _bview), 'proj_swap_bench')
    _w(gs.deployed, deployed_view_of_indexed(scratch_d, view),
       'proj_deployed')
    return LogicOutcome(applied=True,
                        reason=str(getattr(param, 'reason', '') or ''))
