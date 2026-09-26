"""货币战争动作上报:穿装备(report_action_wear_equip_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。

**穿着即合成腿**(世界规则,语义正本 =
``docs/game/currency_war/research/equipment_mechanics.md``「穿着即合成」:
穿戴后该角色 worn 集内可合成的两件立即合成为进阶件,循环至无可合成,
两两配方 = ``cw_synthesis.synthesize_target`` K8 闭合):穿戴落位与
合成在同一写序内完成——owned 摘件 → worn 集合成 → 目标域整表重建写
(bench/deployed 两域,合成产物落 worn 集尾;
前后排 = deployed 单字段视图)。规则住本上报
= kernel 单一源(sim 与实机动作腿同构消费,禁第二份实现);合成改变
板面装备贡献 → 落地写后广播 ``board_changed`` 事实事件。

拒绝语义(布尔契约,统一回声;拒绝 = 零写 + 留证,禁半写):
- owned 无该件 → ``wear_item_not_owned``(合法穿戴前置,漏 = 计划失效);
- 目标角色不在册(char_name 空按 (row, slot) 现读;槽空/未命中)→
  ``wear_target_unit_missing``(front-only 回退步拖空槽 avatar = 游戏
  侧静默拒,上报如实拒);
- 合成后仍超 ``WEAR_LIMIT`` → ``wear_over_cap_rejected``(上限按合成后
  计:穿着即合成可能净减件数)。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sr_od.application.currency_war.data.cw_synthesis import synthesize_target
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchView,
    ChannelSig,
    GameState,
    LogicOutcome,
    Unit,
    _emit_defect,
    _validate_sig,
)

#: 角色穿戴上限(equipment_mechanics.md「角色上限 3 件」定谳)。
WEAR_LIMIT: int = 3

_PRODUCER = 'CwActionWearEquipParam'


def _wear_synthesis(equips: list[str]) -> list[str]:
    """穿着即合成(worn 集内两两配方,循环至无可合成;K8 闭合保证
    终止:基础件对数有限,每次合成件数 −1)。"""
    items = list(equips)
    changed = True
    while changed:
        changed = False
        for i in range(len(items)):
            merged = False
            for j in range(i + 1, len(items)):
                target = synthesize_target(items[i], items[j])
                if target is not None:
                    items = [t for k, t in enumerate(items)
                             if k not in (i, j)]
                    items.append(target)
                    merged = True
                    changed = True
                    break
            if merged:
                break
    return items


def _locate_unit(gs: GameState, param: Any) -> tuple[str, int, Unit] | None:
    """定位穿戴目标单位。

    定位序 = char_name 在册名匹配(bench → deployed 全域,
    合法穿戴前置 = 计划指名;char_name 空 = front-only 回退步,按
    (row, slot) 现读)。[索引定义] row ∈ 'front'|'back'(词表通用声明),
    slot = 画面物理槽位 1 基,deployed 域 = DeployedView 子表下标 + 1
    (位置 = 子表下标派生);bench 域 = BenchView 槽序
    (视图槽 i ↔ 画面槽位 i+1)。

    Returns:
        ``(域键, 下标, 单位)``;未命中 = None。
    """
    char_name = str(getattr(param, 'char_name', '') or '')
    row = str(getattr(param, 'row', '') or '')
    slot = int(getattr(param, 'slot', 0) or 0)
    bench_view = gs.bench.value
    if char_name and bench_view is not None:
        for i, s in enumerate(bench_view.slots):
            if (s is not None and s.kind == 'unit' and s.unit is not None
                    and s.unit.char_id == char_name):
                return ('bench', i, s.unit)
    view = gs.deployed.value
    if view is not None:
        for key, sub in (('front_row', view.front_slots),
                         ('back_row', view.back_slots)):
            if char_name:
                for i, u in enumerate(sub or []):
                    if u is not None and u.char_id == char_name:
                        return (key, i, u)
            elif ('front' if key == 'front_row' else 'back') == row \
                    and 1 <= slot <= len(sub or []):
                u = (sub or [])[slot - 1]
                if u is not None:
                    return (key, slot - 1, u)
    return None


def _write_mutated_domain(gs: GameState, domain: str, idx: int,
                          unit: Unit, sig: ChannelSig) -> None:
    """目标域整表重建写(容器视图 frozen 链,穿戴写 = 域整表重建;
    deployed 域 = 单字段视图整值替换)。"""
    if domain == 'bench':
        view = gs.bench.value
        slots = list(view.slots)
        slots[idx] = replace(slots[idx], unit=unit)
        gs.write_logic(gs.bench,
                       BenchView(slots=slots, capacity=view.capacity),
                       produced_by=_PRODUCER, evidence='wear_worn', sig=sig)
        return
    view = gs.deployed.value
    sub = list(view.front_slots if domain == 'front_row'
               else view.back_slots)
    sub[idx] = unit
    new_view = (replace(view, front_slots=sub) if domain == 'front_row'
                else replace(view, back_slots=sub))
    gs.write_logic(gs.deployed, new_view,
                   produced_by=_PRODUCER,
                   evidence='wear_worn', sig=sig)


def report_action_wear_equip_param(gs: GameState, param: Any,
                                   sig: ChannelSig) -> LogicOutcome:
    """穿装备上报(穿戴原子,发出即记账):owned −1 + worn 集穿着即合成
    + 目标单位所在域整表重建单写(equips 随对象)。row/slot = 画面
    物理槽位(词表定义),目标定位 = ``_locate_unit`` 全域定位(bench/
    前排/后排;3.2 起 tracked 第二账退役,主域单点)。

    拒绝分支(零写 + 留证,布尔契约见模块头):owned 无件 / 目标不在册 /
    合成后超上限。``board_changed`` 事实事件仅 applied 出口广播
    (拒绝 = 零写 = 无世界变化)。
    """
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _reject(reason: str, expected: str, actual: str) -> LogicOutcome:
        _emit_defect(field_name='equips', expected=expected, actual=actual,
                     evidence='wear_equip_report', sig=_grp_sig, kind=reason)
        return LogicOutcome(applied=False, reason=reason)

    owned = list(gs.equips.value or [])
    if param.item_name not in owned:
        return _reject('wear_item_not_owned', f"owned 含 {param.item_name}",
                       f'owned={owned}')
    located = _locate_unit(gs, param)
    if located is None:
        return _reject('wear_target_unit_missing',
                       f'{param.char_name!r} 在册(bench/rows)',
                       f'char_name={param.char_name!r} '
                       f'row={getattr(param, "row", "")!r} '
                       f'slot={getattr(param, "slot", 0)!r}')
    domain, idx, unit = located
    worn = _wear_synthesis(list(unit.equips) + [param.item_name])
    if len(worn) > WEAR_LIMIT:
        return _reject('wear_over_cap_rejected',
                       f'合成后 ≤{WEAR_LIMIT} 件',
                       f'合成后 {len(worn)} 件:{worn}')
    new_unit = replace(unit, equips=worn)
    _write_mutated_domain(gs, domain, idx, new_unit, _grp_sig)
    owned.remove(param.item_name)
    gs.write_logic(gs.equips, owned, produced_by=_PRODUCER,
                   evidence=f'owned[{param.item_name}] -1(穿戴)', sig=_grp_sig)
    # (tracked 第二账已退役:容器侧本函数
    #  _write_mutated_domain 整值替换写已是单点,原「tracked deployed
    #  穿戴随动腿」无可同步;session 形参兼容保留。)
    # (事实事件广播已随事实事件槽退役删除。)
    return LogicOutcome(applied=True)
