"""sim 重做·装备系统(M10)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M10、U24 第一期定稿口径
(依据 ``research/equipment_mechanics.md`` 全篇):

- **状态** = 容器 ``equips``(owned 装备库存,设计稿口径工具亦在此栏)
  / ``BenchChar``/``Unit.equips``(worn 穿戴);
- **穿着即合成 = 游戏规则,sim 必须模拟**(§2.4.2:现行「执行链不拦截」
  缺口在 sim 侧补齐)——穿戴后该角色 worn 集内可合成的两件(基础件
  两两配方 = ``cw_synthesis.synthesize_target`` K8 闭合)立即合成为
  进阶件;装备栏内主动合成同路径;两路径均不耗金。kernel 对
  CwActionWearEquipParam 为视觉域零写面(PREP_PROJECTION_DOMAINS 登记面「禁扩
  静默」),装备动作腿 = sim 侧游戏规则建模(本模块);
- **角色上限 3 件**;产物占最左简易槽(worn 序内替换语义);卖出角色
  装备全量回装备区(卖出腿归 M07/M09 卖出路径,kernel 腿承载);
- **发放引擎 = U24 空表**(首版不发放,随局披露 ``unmodeled_grants``;
  参数逐项回填后生效);
- **冶金炉**(效果原文有档):拖装备 = 变为**同类型**(同 category)
  随机装备,使用后消失;``M10/炉/{uses}`` 流承载重掷;拖角色模式
  (全拆+每件变异)首版不建模,披露;
- 其余工具(特权赋予卡/投影仪×2/好运令牌)= 消耗型动作腿框架之外
  的效果面,首版披露未建模(特权卡确定变换映射在册
  ``cw_effect_inventory.privilege_counterpart``,效果应用归效果批);
  拆装扳手/精密拆装扳手 = 取下全部穿戴回装备区(有档确定面),扳手
  消耗、精密不消耗。

随机流键(引擎侧装配):``M10/炉/{uses}``(冶金炉重掷)、
``M10/发放/{plane}/{round}``(发放采样,U24 空表下无消费)。
"""
from __future__ import annotations

import random
from collections.abc import Callable

from sr_od.application.currency_war.data.cw_equipment_data import (
    EQUIPMENTS,
    get_equip,
)
from sr_od.application.currency_war.data.cw_synthesis import synthesize_target
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    Unit,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPrecisionWrenchUseParam,
    CwActionWearEquipParam,
    CwActionWrenchUseParam,
)
from sr_od.application.currency_war.sim.cw_sim_base import obs_sig, sim_evidence

#: 角色穿戴上限(equipment_mechanics.md「角色上限 3 件」定谳)。
WEAR_LIMIT: int = 3

#: U24 发放引擎空表披露键(首版不发放)。
UNMODELED_GRANTS: str = 'unmodeled_grants'

#: 冶金炉拖角色模式未建模披露键。
FURNACE_CHAR_MODE_PENDING: str = 'furnace_char_mode_pending_m10'

#: 特权卡/投影仪/好运令牌效果面未建模披露键。
TOOL_EFFECTS_PENDING: str = 'tool_effects_pending_m10'


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


def _find_and_mutate_unit(gs: GameState, char_name: str,
                          mutate: Callable[[Unit], Unit | None]) -> bool:
    """按注册名定位单位(bench → deployed)并整体重建其所在容器域。

    ``mutate`` = 单位 → 变换单位(None = 拒:变更非法,整体不写);
    未命中 → False。容器视图为 frozen dataclass 链,穿戴写 = 对应域
    整表重建后 obs 写(与 CwActionDeployMoveParam 的整表平移契约同形)。

    P1 容器原生直写(§3.2):bench 域 = 槽序摘换后 BenchView 直构——
    原有 ``_slots_to_chars``→``bench_view_of_slots`` 旧形往返随换形口
    退役;保真修复(设计 §2.2 申报第 2 项):非 unit 槽(占位件三分类
    kind)原样保留,重建不再降级 empty。
    """
    from dataclasses import replace

    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchView,
    )

    def _mutated(u: Unit | None) -> Unit | None:
        if u is not None and u.char_id == char_name:
            return mutate(u)
        return u

    # bench 域:BenchSlot.unit 摘换 → BenchView 直构(占位件槽原样)
    bench_view = gs.bench.value
    if bench_view is not None:
        slots = list(bench_view.slots)
        hit = any(s is not None and s.kind == 'unit' and s.unit is not None
                  and s.unit.char_id == char_name for s in slots)
        if hit:
            new_slots: list = []
            for s in slots:
                unit = s.unit if (s is not None and s.kind == 'unit'
                                  and s.unit is not None) else None
                if unit is None:
                    new_slots.append(s)
                    continue
                m = _mutated(unit)
                if m is None:
                    return False
                new_slots.append(replace(s, unit=m))
            gs.observe(gs.bench,
                       BenchView(slots=new_slots,
                                 capacity=bench_view.capacity),
                       evidence=sim_evidence('equip:worn'),
                       sig=obs_sig(group_id='sim:equip'))
            return True
    # deployed 域:front_row/back_row 摘换 → 整行重建(空槽 None 保持)
    for field in (gs.front_row, gs.back_row):
        rows = list(field.value or [])
        hit = any(u is not None and u.char_id == char_name for u in rows)
        if hit:
            new_rows: list[Unit | None] = []
            for u in rows:
                if u is None:
                    new_rows.append(None)
                    continue
                m = _mutated(u)
                if m is None:
                    return False
                new_rows.append(m)
            gs.observe(field, new_rows, evidence=sim_evidence('equip:worn'),
                       sig=obs_sig(group_id='sim:equip'))
            return True
    return False


def apply_wear_equip(gs: GameState, action: CwActionWearEquipParam) -> bool:
    """穿装备腿(游戏规则建模:摘件 → 穿戴 → 穿着即合成)。

    拒绝形态(静默拒 = False,调用方按动作未生效处理):owned 无该
    件 / 目标角色不在册 / 合成后仍超上限。目标域未写(bench/deployed
    均 None)→ False。
    """
    owned = list(gs.equips.value or [])
    if action.item_name not in owned:
        return False

    def _mutate(u: Unit) -> Unit | None:
        return _wear_to(u, action.item_name)

    ok = _find_and_mutate_unit(gs, action.char_name, _mutate)
    if not ok:
        return False
    owned.remove(action.item_name)
    gs.observe(gs.equips, owned, evidence=sim_evidence('equip:own'),
               sig=obs_sig(group_id='sim:equip'))
    return True


def _wear_to(u: Unit, item_name: str) -> Unit | None:
    """穿戴单元变换(上限按合成后计:穿着即合成可能净减件数;超限
    返 None = 拒,穿戴合法性由发射位判据辖,sim 侧不炸错)。"""
    from dataclasses import replace

    worn = list(u.equips) + [item_name]
    worn = _wear_synthesis(worn)
    if len(worn) > WEAR_LIMIT:
        return None
    return replace(u, equips=worn)


def _unequip_all(gs: GameState, row: str, slot: int) -> list[str] | None:
    """取下目标角色全部穿戴 → owned(扳手族共用;装备归属面回区)。

    Returns:
        取下的装备名表(角色未命中/域未写 → None)。
    """
    taken: list[str] | None = None

    def _grab(u: Unit) -> Unit:
        nonlocal taken
        taken = list(u.equips)
        from dataclasses import replace
        return replace(u, equips=[])

    found = _find_and_mutate_by_slot(gs, row, slot, _grab)
    if not found or taken is None:
        return None
    if taken:
        gs.observe(gs.equips, list(gs.equips.value or []) + taken,
                   evidence=sim_evidence('equip:unequip'),
                   sig=obs_sig(group_id='sim:equip'))
    return taken


def _find_and_mutate_by_slot(gs: GameState, row: str, slot: int,
                             mutate: Callable[[Unit], Unit]) -> bool:
    """按画面物理槽位(row/slot)定位单位并重建域(扳手族坐标系 =
    cw_vocab 通用声明:row ∈ 'front'|'back',slot 画面 1 基)。"""
    from dataclasses import replace

    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchView,
    )
    if row == 'front':
        rows = list(gs.front_row.value or [])
        idx = slot - 1
        if not (0 <= idx < len(rows)) or rows[idx] is None:
            return False
        new_rows = [mutate(u) if i == idx else u
                    for i, u in enumerate(rows)]
        gs.observe(gs.front_row, new_rows,
                   evidence=sim_evidence('equip:worn'),
                   sig=obs_sig(group_id='sim:equip'))
        return True
    if row == 'back':
        rows = list(gs.back_row.value or [])
        idx = slot - 1
        if not (0 <= idx < len(rows)) or rows[idx] is None:
            return False
        new_rows = [mutate(u) if i == idx else u
                    for i, u in enumerate(rows)]
        gs.observe(gs.back_row, new_rows,
                   evidence=sim_evidence('equip:worn'),
                   sig=obs_sig(group_id='sim:equip'))
        return True
    # 非排坐标 → bench 槽序画面位(视图槽 i ↔ 画面槽位 i+1)
    bench_view = gs.bench.value
    if bench_view is None:
        return False
    idx = slot - 1
    slots = list(bench_view.slots)
    if not (0 <= idx < len(slots)):
        return False
    s = slots[idx]
    if s is None or s.kind != 'unit' or s.unit is None:
        return False
    slots[idx] = replace(s, unit=mutate(s.unit))
    gs.observe(gs.bench, BenchView(slots=slots, capacity=bench_view.capacity),
               evidence=sim_evidence('equip:worn'),
               sig=obs_sig(group_id='sim:equip'))
    return True


def apply_wrench(gs: GameState, action: CwActionWrenchUseParam) -> bool:
    """拆装扳手腿:取下全部穿戴回装备区,工具消耗(用后消失)。"""
    taken = _unequip_all(gs, action.row, action.slot)
    if taken is None:
        return False
    owned = list(gs.equips.value or [])
    if '拆装扳手' in owned:
        owned.remove('拆装扳手')
        gs.observe(gs.equips, owned, evidence=sim_evidence('tool:consume'),
                   sig=obs_sig(group_id='sim:equip'))
    return True


def apply_precision_wrench(gs: GameState,
                           action: CwActionPrecisionWrenchUseParam) -> bool:
    """精密拆装扳手腿:同拆装扳手但库存不递减(无限次用)。"""
    return _unequip_all(gs, action.row, action.slot) is not None


def furnace_reroll(rng: random.Random, item_name: str) -> str:
    """冶金炉重掷(效果原文「变为同类型的随机装备」:同 category 池
    均匀,排除自身;``M10/炉/{uses}`` 流,引擎装配)。"""
    src = get_equip(item_name)
    if src is None:
        raise ValueError(f'冶金炉目标 {item_name!r} 不在装备注册表')
    pool = sorted(name for name, e in EQUIPMENTS.items()
                  if e.category == src.category and name != item_name)
    return pool[rng.randrange(len(pool))]


def apply_furnace_equip_mode(gs: GameState, item_name: str, *,
                             rng: random.Random) -> str | None:
    """冶金炉 equip 模式腿:库存摘旧件 → 同类型随机新件入账。

    Returns:
        新件名(库存无该件 → None 拒)。
    """
    owned = list(gs.equips.value or [])
    if item_name not in owned:
        return None
    new_name = furnace_reroll(rng, item_name)
    owned.remove(item_name)
    owned.append(new_name)
    gs.observe(gs.equips, owned, evidence=sim_evidence('furnace:reroll'),
               sig=obs_sig(group_id='sim:furnace'))
    return new_name
