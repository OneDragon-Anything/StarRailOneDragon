"""货币战争动作上报:上阵单步(report_action_deploy_move_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。

**上阵变换窗**(银狼闭环迭代 design.md §2.1A):落位腿对 =
(银狼LV.999, 3★) 时,落场写**下一费用档的 1★**(角色固有升星升费:
备战栏不升费、拖上场才触发;单位身份保持银狼LV.999,费用档升一级
不建模——cost=起始费,多档待策略层需要时扩);其余单位恒等搬运
零行为差。升费连锁(场上同名同星不变量)经常规级联覆盖
(:func:`cw_effect_inventory.merge_cascade_write` 正常推演——费用档
不同时存在[口述·权威 2026-09-18],merge 分组键 (char_id, star)
无跨档歧义)。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    merge_cascade_write,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    deployed_indexed_to_rows,
    deployed_rows_to_indexed,
    place_unit_in_deployed,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    BENCH_CAPACITY_DEFAULT,
    BenchSlot,
    BenchView,
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    _validate_sig,
)

#: 变换窗触发单位(银狼LV.999,3★):拖上场变下一费用档 1★
#: (design §2.1A;名单与星级 = 定谳口径,机制单一源 =
#: docs/game/gameplay/currency_war.md「银狼LV.999 升星升费」条)。
_TRANSFORM_CHAR_ID: str = '银狼LV.999'
_TRANSFORM_STAR: int = 3
_TRANSFORMED_STAR: int = 1


def report_action_deploy_move_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """上阵上报:bench 源槽摘槽(原生 BenchSlot 形态)+ deployed 目标排
    首空落位(行域下标派生表上 ``place_unit_in_deployed``,按目标排路由
    首选排,排满 fallback 另一排;§2.1 下标派生单一源)+ board 羁绊计数
    派生重算(行写端挂钩 ``_resync_board_delta`` 自动,禁手写 board)。
    to_row 非法/源槽空/两排全满 = applied=False 零写(陈旧提案)。
    落位腿对 (银狼LV.999,3★) = 上阵变换窗:落场写下一费用档 1★
    (非 3★ 原样)+ 级联常规覆盖;其余单位恒等搬运零行为差。

    P1 申报现状不对称(§3 不变量 5,归一口统一归 P3):本上报**缺开拓者
    形态归一**(char_id 不随排切换)——现状缺陷锚
    test_cw_trailblazer_stance_normalization 钉住,禁顺带修复。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionDeployMoveParam',
                       evidence=evidence, sig=_grp_sig)

    _bview = gs.bench.value
    bench_slots = list(_bview.slots) if _bview is not None else []
    dep_table = deployed_rows_to_indexed(gs.front_row.value, gs.back_row.value)
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
    moved = replace(_mu, slot=from_idx + 1)
    # 上阵变换窗(design §2.1A):拖拽载荷唯一指定源(恰此一枚,无歧义)
    # → 落场写下一费用档 1★(身份保持,槽位随拖拽落点,观察为真值)。
    _transform = (moved.char_id == _TRANSFORM_CHAR_ID
                  and moved.star == _TRANSFORM_STAR)
    if _transform:
        moved = replace(moved, star=_TRANSFORMED_STAR)
    scratch = list(dep_table)
    placed_idx = place_unit_in_deployed(scratch, moved, to_row)
    if placed_idx is None:
        return LogicOutcome(applied=False, reason='deployed_full')
    bench_slots[from_idx] = BenchSlot(kind='empty')
    _w(gs.bench, BenchView(slots=bench_slots,
                           capacity=(_bview.capacity
                                     if _bview is not None
                                     else BENCH_CAPACITY_DEFAULT)),
       'proj_deploy_src_clear')
    front, back = deployed_indexed_to_rows(scratch)
    _w(gs.front_row, front, 'proj_deploy_front')
    _w(gs.back_row, back, 'proj_deploy_back')
    if _transform:
        # 升费连锁(场上同名同星不变量)经常规级联覆盖(正常推演,
        # 费用档不同时存在定谳)。
        merge_cascade_write(
            gs, bench_slots, scratch,
            rand=False, evidence='proj_deploy_lv999_merge',
            producer='CwActionDeployMoveParam', sig=_grp_sig,
            orig_view=_bview)
    return LogicOutcome(applied=True)
