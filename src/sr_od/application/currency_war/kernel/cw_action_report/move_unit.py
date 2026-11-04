"""货币战争动作上报:统一拖动(report_action_move_unit_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。状态容器、写入口与观察写
端留在 ``kernel/cw_game_state``,本包 → 状态容器单向依赖。
语义权威版本 = 函数 docstring。

统一拖动(部署统一批,用户指令 2026-10-30):四元组全域移动,
字段写侧按「源域 × 目标域 × 目标槽占用态」写分支(推演矩阵 =
unified-deploy-order 详设 §4 动作词表行):
- bench→场上空槽 = 直落(锁校验 + 银狼变换窗 + 开拓者形态);
- bench→场上被占槽 = 交换(被占者回 bench 源槽;锁校验辖上场者);
- 场上→场上 = 纯换位(目标被占 = 场上互换;**无锁无变换**);
- 场上→bench 空槽 = 下场(开拓者保守归一);
- 场上→bench 被占槽 = 交换(被挤出 bench 件上 field——**锁校验辖
  此新上场件**);
- bench→bench = 席内挪位。
锁校验辖「新单位入场上」全形态;变换窗只 bench→上场触发;开拓者
按目标排定形态、下场取保守归一(原样保留场上形态名 = 不变换即
保守,现行 deploy_move/swap_deploy 同款边界申报)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
)

#: 变换窗触发单位(银狼LV.999,3★):拖上场变下一费用档 1★
#: (design §2.1A;名单与星级 = 定案口径,机制单一源 =
#: docs/game/gameplay/currency_war.md「银狼LV.999 升星升费」条;
#: 常量宿主原 = deploy_move 上报模块,随其戊批纳入统一管理删除迁入——
#: 现役唯一消费者 = 本模块上场分支)。
_TRANSFORM_CHAR_ID: str = '银狼LV.999'
_TRANSFORM_STAR: int = 3
_TRANSFORMED_STAR: int = 1


def _slot_of(bench_slots: list, front_slots: list, back_slots: list,
             domain: str, slot: int) -> tuple[list, int] | None:
    """域/槽(基随域)→ (工作列表, 0 基下标) 换算;非法域/越界 → None。

    front/back 基 1(排内画面槽号),bench 基 0(状态容器槽位表下标)——
    单坐标系声明见 ``CwActionMoveUnitParam``。"""
    if domain == 'bench':
        if not 0 <= slot < len(bench_slots):
            return None
        return bench_slots, slot
    if domain == 'front':
        if not 1 <= slot <= len(front_slots):
            return None
        return front_slots, slot - 1
    if domain == 'back':
        if not 1 <= slot <= len(back_slots):
            return None
        return back_slots, slot - 1
    return None


def report_action_move_unit_param(gs: GameState, param: Any,
                                  sig: ChannelSig) -> LogicOutcome:
    """统一拖动上报:四元组载荷按推演矩阵写 bench/deployed 两状态容器
    (一次写 = 一次完整语义变更,两域各单字段整值替换)。

    拖拽语义 = 游戏规则:目标槽空 = 放置,有角色 = 交换——执行层
    零判效,本函数按同一规则推演字段写;源槽空/域外/槽越界/expect
    失配 = applied=False 零写(陈旧提案)。上场分支(scr=bench ∧
    dst=场上,含交换挤出形态)带三守卫:唯一性键(上场者与场上现存
    无同名,``board_unique_key``)/ 上场锁(``deploy_lock_block_
    reason``)/ 银狼变换窗(落场写下一费用档 1★ + 档行 + 级联,与
    旧 deploy_move 上报同核,随其戊批纳入统一管理并入本核)。场上→场上纯换位与
    下场/席内挪位无锁无变换(开拓者形态归一除外)。

    bench/deployed 写后 board 羁绊计数随行写端挂钩重算(禁手写)。
    """
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        board_unique_key,
    )
    from sr_od.application.currency_war.kernel.cw_economy import (
        effective_cost,
    )
    from sr_od.application.currency_war.kernel.cw_effect_inventory import (
        merge_cascade_write,
    )
    from sr_od.application.currency_war.kernel.cw_env_grants import (
        deploy_lock_block_reason,
    )
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        trailblazer_row_unit,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BENCH_CAPACITY_DEFAULT,
        BenchSlot,
        BenchView,
        DeployedView,
        Field,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionMoveUnitParam',
                       evidence=evidence, sig=_grp_sig)

    src_domain = str(getattr(param, 'src_domain', '') or '')
    dst_domain = str(getattr(param, 'dst_domain', '') or '')
    _bview = gs.bench.value
    bench_slots = list(_bview.slots) if _bview is not None else []
    view = gs.deployed.value
    front_slots = list(view.front_slots) if view is not None else []
    back_slots = list(view.back_slots) if view is not None else []

    src_ref = _slot_of(bench_slots, front_slots, back_slots,
                       src_domain, int(param.src_slot))
    dst_ref = _slot_of(bench_slots, front_slots, back_slots,
                       dst_domain, int(param.dst_slot))
    if src_ref is None or dst_ref is None:
        return LogicOutcome(
            applied=False,
            reason=(f'move_slot_invalid:{src_domain}{param.src_slot}'
                    f'->{dst_domain}{param.dst_slot}'))
    src_list, src_i = src_ref
    dst_list, dst_i = dst_ref
    raw_src = src_list[src_i]
    if src_domain == 'bench':
        if raw_src is None or getattr(raw_src, 'kind', 'unit') != 'unit' \
                or raw_src.unit is None:
            return LogicOutcome(
                applied=False,
                reason=f'src_empty:{src_domain}{param.src_slot}')
        unit = raw_src.unit
    else:
        if raw_src is None:
            return LogicOutcome(
                applied=False,
                reason=f'src_empty:{src_domain}{param.src_slot}')
        unit = raw_src
    if unit is None or not (getattr(unit, 'char_id', '') or ''):
        return LogicOutcome(
            applied=False,
            reason=f'src_no_identity:{src_domain}{param.src_slot}')
    if getattr(param, 'expect', '') \
            and unit.char_id != param.expect:
        return LogicOutcome(
            applied=False,
            reason=f'stale_proposal:{param.expect}!={unit.char_id}')

    # bench 域槽值 = BenchSlot(空槽 = kind 'empty' 对象,非 None);
    # 场上域槽值 = Unit | None。归一提取:bench 空/占位件 → None(占位
    # 件不可交互,fail-closed 拒);bench unit → 内嵌 Unit;场上直取。
    def _bench_entry(slot_val):
        if slot_val is None or getattr(slot_val, 'kind', 'unit') != 'unit':
            return None, (getattr(slot_val, 'kind', 'empty') != 'empty'
                          and slot_val is not None)
        return slot_val.unit, False

    raw_dst = dst_list[dst_i]
    if dst_domain == 'bench':
        occupier_unit, dst_blocked = _bench_entry(raw_dst)
        if dst_blocked:
            return LogicOutcome(
                applied=False,
                reason=f'dst_not_unit_slot:{dst_domain}{param.dst_slot}')
        occupier = occupier_unit   # bench 域:occupier 即 Unit|None
    else:
        occupier = raw_dst
        occupier_unit = raw_dst
    if occupier_unit is not None and src_domain == 'bench' \
            and not (getattr(occupier_unit, 'char_id', '') or ''):
        # 场上目标为未知身份件(char_id 空):差分执行器禁挤未知件
        # (详设 §2 段 0 D3-13),上报侧同款 fail-closed。
        return LogicOutcome(
            applied=False,
            reason=f'dst_unknown_unit:{dst_domain}{param.dst_slot}')
    # 同槽直拖(源 == 目标)= 幂等零写成功(执行层噪声形态,零行为)。
    if src_ref == dst_ref:
        return LogicOutcome(applied=True)

    def _bench_slot(u) -> BenchSlot:
        return BenchSlot(kind='unit', unit=u)

    def _empty() -> BenchSlot:
        return BenchSlot(kind='empty')

    # —— 上场分支守卫(bench→场上 与 场上→bench 被占挤出形态)——
    to_field = dst_domain in ('front', 'back') and src_domain == 'bench'
    swap_to_field = (dst_domain == 'bench' and src_domain in ('front', 'back')
                     and occupier is not None)
    if to_field or swap_to_field:
        # 上场者 = bench 侧单位(to_field = 源;swap_to_field = 目标占者)。
        up_unit = unit if to_field else occupier_unit
        _k = board_unique_key(up_unit)
        _others = [d for d in (*front_slots, *back_slots) if d is not None]
        if src_domain in ('front', 'back'):
            _others = [d for d in _others if d is not unit]
        if _k is not None and any(board_unique_key(d) == _k
                                  for d in _others):
            return LogicOutcome(applied=False,
                                reason=f'duplicate_on_board:{_k}')
        _lock_reason = deploy_lock_block_reason(gs, up_unit)
        if _lock_reason is not None:
            return LogicOutcome(applied=False, reason=_lock_reason)

    # —— 字段写推演(按源域 × 目标域全分支)——
    transform = False
    _tier_before = 0
    if src_domain == 'bench' and dst_domain in ('front', 'back'):
        # bench → 场上:直落(dst 空)或被占者回 bench 源槽(交换)。
        moved = trailblazer_row_unit(unit, dst_domain)
        _tier_before = effective_cost(gs, _TRANSFORM_CHAR_ID)
        transform = (moved.char_id == _TRANSFORM_CHAR_ID
                     and moved.star == _TRANSFORM_STAR
                     and _tier_before < 5)
        if transform:
            moved = _dc_replace(moved, star=_TRANSFORMED_STAR)
        dst_list[dst_i] = moved
        src_list[src_i] = _empty() if occupier is None \
            else _bench_slot(occupier_unit)
    elif src_domain in ('front', 'back') and dst_domain == 'bench':
        # 场上 → bench:下场(dst 空)或交换(被挤出 bench 件上 field)。
        if occupier is None:
            dst_list[dst_i] = _bench_slot(unit)   # 下场保守归一 = 原样
            src_list[src_i] = None
        else:
            up_unit = occupier_unit
            moved = trailblazer_row_unit(up_unit, src_domain)
            _tier_before = effective_cost(gs, _TRANSFORM_CHAR_ID)
            transform = (moved.char_id == _TRANSFORM_CHAR_ID
                         and moved.star == _TRANSFORM_STAR
                         and _tier_before < 5)
            if transform:
                moved = _dc_replace(moved, star=_TRANSFORMED_STAR)
            src_list[src_i] = moved
            dst_list[dst_i] = _bench_slot(unit)
    elif src_domain in ('front', 'back') and dst_domain in ('front', 'back'):
        # 场上 → 场上:纯换位(dst 空 = 挪排;被占 = 场上互换)。
        # 无锁无变换;开拓者按目标排定形态。
        moved = trailblazer_row_unit(unit, dst_domain)
        src_list[src_i] = (trailblazer_row_unit(occupier_unit, src_domain)
                           if occupier is not None else None)
        dst_list[dst_i] = moved
    else:
        # bench → bench:席内挪位(两槽互换或移入空槽)。
        dst_list[dst_i] = src_list[src_i]
        src_list[src_i] = _bench_slot(occupier_unit) if occupier is not None \
            else _empty()

    _new_view = DeployedView(front_slots=front_slots,
                             back_slots=back_slots)
    _w(gs.bench, BenchView(slots=bench_slots,
                           capacity=(_bview.capacity if _bview is not None
                                     else BENCH_CAPACITY_DEFAULT)),
       'proj_move_unit_bench')
    _w(gs.deployed, _new_view, 'proj_move_unit_deployed')
    if transform:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            deployed_indexed_of_view,
        )
        _w(gs.lv999_cost_tier, _tier_before + 1, 'deploy_upgrade_tier')
        merge_cascade_write(
            gs, bench_slots, deployed_indexed_of_view(_new_view),
            rand=False, evidence='proj_move_lv999_merge',
            producer='CwActionMoveUnitParam', sig=_grp_sig,
            orig_view=_bview)
    return LogicOutcome(
        applied=True,
        reason=str(getattr(param, 'reason', '') or ''))

