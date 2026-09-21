"""货币战争动作上报:上阵单步(report_action_deploy_move_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。

**上阵变换窗**(银狼闭环迭代 design.md §2.1A + 银狼升星记账批 §2.5):落位腿对 =
(银狼LV.999, 3★) 且现档 < 5 时,落场写**下一费用档的 1★**(角色固有升星升费:
备战栏不升费、拖上场才触发;单位身份保持银狼LV.999)+ **档行**
(``lv999_cost_tier`` 现档+1,牌库改变的容器表达);现档 = 5(费用封顶)恒等
搬运。其余单位恒等搬运零行为差。升费连锁(场上同名同星不变量)经常规级联覆盖
(:func:`cw_effect_inventory.merge_cascade_write` 正常推演——费用档
不同时存在[口述·权威 2026-09-18],merge 分组键 (char_id, star)
无跨档歧义)。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sr_od.application.currency_war.kernel.cw_economy import effective_cost
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    merge_cascade_write,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    deployed_idx_of,
    deployed_indexed_to_rows,
    deployed_row_slot,
    deployed_rows_to_indexed,
    trailblazer_row_unit,
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
    """上阵上报:bench 源槽摘槽 + 载荷 (to_row, to_slot) 直落
    (排内 1 基槽号经下标换算单一源 ``deployed_idx_of`` 定表下标,与执行
    拖点同源无分叉;§2.1 下标派生表)+ 开拓者形态归一(归一核单一源 =
    ``cw_exec_state.trailblazer_row_identity``,与 swap 上报同源——
    benchchar-retirement P3 统一申报的缺陷修复:换排 = 命途切换,char_id
    随目标排形态,欢愉/记忆羁绊计数不再错账)+ board 羁绊计数派生重算
    (行写端挂钩 ``_resync_board_delta`` 自动,禁手写 board)。
    to_row 非法/源槽空/载荷槽越出定长表或跨排 = applied=False 零写
    (陈旧提案)。拖拽语义 = 游戏规则:目标槽空 = 放置;有人 = 交换——
    被占位单位回源 bench 槽(与 ``report_action_swap_deploy_param`` 换位
    契约同语义:单位对象整体回填,装备随对象,槽号信息位随落位归一);
    禁占位拒绝、禁静默换槽。
    落位腿对 (银狼LV.999,3★) = 上阵变换窗:落场写下一费用档 1★
    (非 3★ 原样)+ 级联常规覆盖;其余单位恒等搬运零行为差。"""
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
    # 载荷槽 → 表下标(单一源换算);越出定长表或换算回读与载荷 (排, 槽)
    # 不符(跨排,如 front 5 号落在表后段)= 载荷非法,零写。
    to_slot = int(param.to_slot)
    to_idx = deployed_idx_of(to_row, to_slot)
    if not (0 <= to_idx < len(dep_table)) \
            or deployed_row_slot(to_idx) != (to_row, to_slot):
        return LogicOutcome(applied=False,
                            reason=f'to_slot_invalid:{to_row}{to_slot}')
    if not (0 <= from_idx < len(bench_slots)) \
            or bench_slots[from_idx] is None \
            or bench_slots[from_idx].kind != 'unit' \
            or bench_slots[from_idx].unit is None:
        return LogicOutcome(applied=False,
                            reason=f'bench_idx_out_of_range:{from_idx}')
    _mu = bench_slots[from_idx].unit
    # 开拓者形态归一先于槽位/星级改写(与 swap 同核;非开拓者原样返回)。
    moved = trailblazer_row_unit(replace(_mu, slot=to_slot), to_row)
    # 上阵变换窗(design §2.1A/§2.5):拖拽载荷唯一指定源(恰此一枚,无歧义)
    # → 落场写下一费用档 1★(身份保持,槽位随拖拽落点,观察为真值);
    # 现档 = 5(费用封顶,无下一档)恒等搬运[机制推断·实机候证,与「5 费
    # 升 2 星两选项皆装备」同源口径]。
    _tier_before = effective_cost(gs, _TRANSFORM_CHAR_ID)
    _transform = (moved.char_id == _TRANSFORM_CHAR_ID
                  and moved.star == _TRANSFORM_STAR
                  and _tier_before < 5)
    if _transform:
        moved = replace(moved, star=_TRANSFORMED_STAR)
    scratch = list(dep_table)
    _occupier = scratch[to_idx]
    scratch[to_idx] = moved   # 空 = 放置;有人 = 交换(占位不拒,见 docstring)
    bench_slots[from_idx] = (
        BenchSlot(kind='empty') if _occupier is None
        else BenchSlot(kind='unit',
                       unit=replace(_occupier, slot=from_idx + 1)))
    _w(gs.bench, BenchView(slots=bench_slots,
                           capacity=(_bview.capacity
                                     if _bview is not None
                                     else BENCH_CAPACITY_DEFAULT)),
       'proj_deploy_src_clear')
    front, back = deployed_indexed_to_rows(scratch)
    _w(gs.front_row, front, 'proj_deploy_front')
    _w(gs.back_row, back, 'proj_deploy_back')
    if _transform:
        # 档行(银狼升星记账批 §2.5):现档+1,牌库改变的容器表达——落行
        # 时序 = 行域写后、级联前(与 planner 升费腿同约定,design §2.2)。
        _w(gs.lv999_cost_tier, _tier_before + 1, 'deploy_upgrade_tier')
        # 升费连锁(场上同名同星不变量)经常规级联覆盖(正常推演,
        # 费用档不同时存在定谳)。
        merge_cascade_write(
            gs, bench_slots, scratch,
            rand=False, evidence='proj_deploy_lv999_merge',
            producer='CwActionDeployMoveParam', sig=_grp_sig,
            orig_view=_bview)
    return LogicOutcome(applied=True)
