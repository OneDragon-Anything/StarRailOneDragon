"""货币战争动作上报:上阵单步(report_action_deploy_move_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留在 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。

**上阵变换窗**(升费腿语义):落位腿对 =
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
    trailblazer_row_unit,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    BENCH_CAPACITY_DEFAULT,
    BenchSlot,
    BenchView,
    ChannelSig,
    DeployedView,
    Field,
    GameState,
    LogicOutcome,
    _validate_sig,
    deployed_indexed_of_view,
)

#: 变换窗触发单位(银狼LV.999,3★):拖上场变下一费用档 1★
#: (design §2.1A;名单与星级 = 定案口径,机制单一源 =
#: docs/game/gameplay/currency_war.md「银狼LV.999 升星升费」条)。
_TRANSFORM_CHAR_ID: str = '银狼LV.999'
_TRANSFORM_STAR: int = 3
_TRANSFORMED_STAR: int = 1


def report_action_deploy_move_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """上阵上报:bench 源槽摘槽 + 载荷 (to_row, to_slot) 直落
    (排内 1 基槽号直址子表下标,与执行拖点同源无分叉;一次写 = 一次完整
    语义变更——落位/交换都是 deployed 单字段整值替换)
    + 开拓者形态归一(归一核单一源 =
    ``cw_exec_state.trailblazer_row_identity``,与 swap 上报同源——
    benchchar-retirement P3 统一申报的缺陷修复:换排 = 命途切换,char_id
    随目标排形态,欢愉/记忆羁绊计数不再错账)+ board 羁绊计数派生重算
    (行写端挂钩 ``_resync_board_delta`` 自动,禁手写 board)。
    to_row 非法/源槽空/载荷槽越出物理容量(前排 >4 / 后排 > back_layout
    现值)或跨排 = applied=False 零写(陈旧提案)。拖拽语义 = 游戏规则:
    目标槽空 = 放置;有人 = 交换——被占位单位回源 bench 槽(与
    ``report_action_swap_deploy_param`` 换位契约同语义:单位对象整体回填,
    装备随对象);禁占位拒绝、禁静默换槽。
    落位腿对 (银狼LV.999,3★) = 上阵变换窗:落场写下一费用档 1★
    (非 3★ 原样)+ 级联常规覆盖;其余单位恒等搬运零行为差。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_game_state import (
        DEPLOYED_FRONT_CAPACITY_DEFAULT,
        back_capacity_of,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionDeployMoveParam',
                       evidence=evidence, sig=_grp_sig)

    _bview = gs.bench.value
    bench_slots = list(_bview.slots) if _bview is not None else []
    view = gs.deployed.value
    front_slots = list(view.front_slots) if view is not None \
        else [None] * DEPLOYED_FRONT_CAPACITY_DEFAULT
    back_slots = list(view.back_slots) if view is not None else []
    from_idx = int(param.bench_idx)   # 槽位表下标直取(统一坐标系)
    to_row = getattr(param, 'to_row', '')
    if to_row not in ('front', 'back'):
        return LogicOutcome(applied=False,
                            reason=f'to_row_invalid:{to_row!r}')
    # 载荷槽 → 物理容量校验(前排恒 4;后排 = back_layout 现值 6-9——
    # 3.1 起 deployed 视图后排动态容量,定长 10 表上限缺陷消失;载荷超
    # 容量 = 陈旧载荷零写)。
    to_slot = int(param.to_slot)
    cap = (DEPLOYED_FRONT_CAPACITY_DEFAULT if to_row == 'front'
           else back_capacity_of(gs))
    if not 1 <= to_slot <= cap:
        return LogicOutcome(applied=False,
                            reason=f'to_slot_invalid:{to_row}{to_slot}')
    if not (0 <= from_idx < len(bench_slots)) \
            or bench_slots[from_idx] is None \
            or bench_slots[from_idx].kind != 'unit' \
            or bench_slots[from_idx].unit is None:
        return LogicOutcome(applied=False,
                            reason=f'bench_idx_out_of_range:{from_idx}')
    _mu = bench_slots[from_idx].unit
    # 开拓者形态归一先于星级改写(与 swap 同核;非开拓者原样返回)。
    moved = trailblazer_row_unit(_mu, to_row)
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
    # 载荷落位(单写:视图整值替换)。目标槽有人 = 交换,被占位单位回源
    # bench 槽(占位不拒,见 docstring);后排载荷越出现视图长度 = 容量内
    # 扩展格,视图随落位扩容(容量变化 = 整视图结构性写)。两排均带
    # 防御性 pad(前排定长 4 是设计不变量,规范形写端恒满足;pad 兜底
    # 任何非规范形残留视图,评审 需修-1)。
    if to_row == 'front':
        while len(front_slots) < to_slot:
            front_slots.append(None)
        _occupier = front_slots[to_slot - 1]
        front_slots[to_slot - 1] = moved
    else:
        while len(back_slots) < to_slot:
            back_slots.append(None)
        _occupier = back_slots[to_slot - 1]
        back_slots[to_slot - 1] = moved
    bench_slots[from_idx] = (
        BenchSlot(kind='empty') if _occupier is None
        else BenchSlot(kind='unit', unit=_occupier))
    _w(gs.bench, BenchView(slots=bench_slots,
                           capacity=(_bview.capacity
                                     if _bview is not None
                                     else BENCH_CAPACITY_DEFAULT)),
       'proj_deploy_src_clear')
    # 合成级联工作副本 = 定长 10 下标表(3.1 窗口期桥;与视图同源派生)。
    _new_view = DeployedView(front_slots=front_slots, back_slots=back_slots)
    scratch = deployed_indexed_of_view(_new_view)
    _w(gs.deployed, _new_view, 'proj_deploy_move')
    if _transform:
        # 档行(银狼升星记账批 §2.5):现档+1,牌库改变的容器表达——落行
        # 时序 = 行域写后、级联前(与 planner 升费腿同约定,design §2.2)。
        _w(gs.lv999_cost_tier, _tier_before + 1, 'deploy_upgrade_tier')
        # 升费连锁(场上同名同星不变量)经常规级联覆盖(正常推演,
        # 费用档不同时存在定案)。
        merge_cascade_write(
            gs, bench_slots, scratch,
            rand=False, evidence='proj_deploy_lv999_merge',
            producer='CwActionDeployMoveParam', sig=_grp_sig,
            orig_view=_bview)
    # (事实事件广播已停用:
    #  sim 呈现/登记经容器值回调与问询时点呈现检查承载。)
    return LogicOutcome(applied=True)
