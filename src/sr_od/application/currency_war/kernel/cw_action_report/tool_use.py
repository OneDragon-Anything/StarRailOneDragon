"""货币战争动作上报:工具原子七类容器写(report_action_*_use_param 七函数)。

**机械执行直接上报**(用户裁定 2026-09-21,正本 =
changes/2026-09-21-tool-gain-report/design.md §2.0):动作 op = 机械执行
不判成败,上报**无条件按成功写容器**——确定面
:meth:`GameState.write_logic`、随机面(效果含采样):
:meth:`GameState.write_logic_rand` 采样链。「失败」不是本层概念,容器与
实机出入归观察对账机制按其契约处置。本批自 ``zero_writes`` 零写占位升格
(七函数退役迁入,包级 ``__getattr__`` 命名规约解析具名模块先于零写族,
op 侧调用形态不变)。

记账载体 = ``gs.equips``(工具件住装备库存,观察/策略同口径):**工具
消耗移除与效果腿同域合并单笔写,禁拆两笔**(拆两笔 = 中间态 + 二次失配
面);``gs.consumables`` 为独立死字段不入本面。

- **获得走链**:投影仪复制进席 = 标准「获得角色」,经
  :func:`cw_gain_chain.gain_character` 统一时序(落位 → 回调 → 3 合 1
  升星判断 → 产物递归;复制触发三合一 = 口述·权威 2026-09-21);
- **变异面不走链**:冶金炉/特权卡 = 原地替换数量不变,非获得——直写、
  不触发获得回调(候实机采证;采证钩子 = 变异产物命中
  ``EQUIP_ACQUIRE_CONSEQUENCES`` 键集落
  ``furnace_mutate_consequence_candidate`` 留证行);
- **冶金炉采样池 v0** = ``cw_sim_equips.furnace_reroll`` 同源(同类别池
  均匀、排除被变异件自身;两实现等价由对拍锁钉死,禁第二套口径);披露键
  :data:`FURNACE_MUTATE_POOL_ASSUMPTION_KEYS`;rng = pick_invest 关键字
  带缺省形态(缺省未播种 = 采样是猜测);
- **失败安全**(沿 gain-chain §2.7 同款):目标单位未观察/漂移、桥零写
  分支(库存未观察/无此件)= bug 面零写 + 留证不停机;rand 写吸收工具
  消失的成败差异 = 预期自愈形态,不落缺陷。

动作上报函数族拆分件(每动作一文件;族规约 = 包
``cw_action_report.__init__`` docstring;工具七类机械半同构,同住一文件
= pick_equip 族先例「一族一文件」)。本包 → 容器单向依赖。
"""
from __future__ import annotations

import random
from dataclasses import replace
from typing import Any

from sr_od.application.currency_war.data.cw_equipment_data import (
    EQUIPMENTS,
    get_equip,
)
from sr_od.application.currency_war.kernel.cw_economy import bench_char_cost
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    EQUIP_ACQUIRE_CONSEQUENCES,
    privilege_counterpart,
)
from sr_od.application.currency_war.kernel.cw_gain_chain import (
    gain_character,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    Unit,
    _emit_defect,
    _validate_sig,
)

#: 链内写端署名(gain-chain 同纪律:新写端新名,不沿用旧名伪装连续;
#: 投影仪 ``gain_character`` 调用与各直写腿 produced_by 同值)。
TOOL_USE_REPORT_PRODUCER: str = 'CwActionToolUseReport'

#: 缺陷留证 kind 词表(_emit_defect 台账行分键;留证不停机)。
DEFECT_PRIVILEGE_WORN_UNSUPPORTED: str = 'tool_privilege_worn_unsupported'
DEFECT_TARGET_UNIT_MISSING: str = 'tool_target_unit_missing'
DEFECT_BRIDGE_ZERO_WRITE: str = 'tool_bridge_zero_write'
DEFECT_TOKEN_NOT_ADMITTED: str = 'tool_token_not_admitted'
DEFECT_MUTATE_CONSEQUENCE_CANDIDATE: str = 'furnace_mutate_consequence_candidate'

#: 冶金炉采样池 v0 建模假设档披露键(pick_invest 先例形态):池语义 =
#: 同类别均匀、排除自身,成员资格轴 = 注册表 category。已知边角:简易池
#: 8 件 vs 实机 7 件(光能电池归属)在 game 侧待实测,在册待校准批。
FURNACE_MUTATE_POOL_ASSUMPTION_KEYS: tuple[str, ...] = (
    'furnace_mutate_pool_v0_same_category',
)

#: 模块级缺省 rng(rng=None 时取用;缺省未播种 = 实机采样是猜测,
#: sim/live 同语义,真实度归观察对账;注入槽模式测试同种子可复现)。
_DEFAULT_RNG: random.Random = random.Random()


# ============================================================ 采样池(sim 同源)

def furnace_mutate_pool(item_name: str) -> list[str] | None:
    """冶金炉同类别变异池(采样池单一源对齐 sim
    ``cw_sim_equips.furnace_reroll``:同 category 池升序、排除被变异件
    自身;成员资格轴 = 注册表 category)。目标件不在注册表 → None
    (调用侧 fail-closed 禁猜);空池 → [](无同类别可替换件)。"""
    src = get_equip(item_name)
    if src is None:
        return None
    return sorted(name for name, e in EQUIPMENTS.items()
                  if e.category == src.category and name != item_name)


def furnace_mutate_sample(rng: random.Random, item_name: str) -> str | None:
    """冶金炉单次变异采样(:func:`furnace_mutate_pool` 均匀取一;
    采样算子与 sim furnace_reroll 同形 ``pool[rng.randrange(len(pool))]``,
    同种子同输入逐次等值由对拍锁钉死)。池不可用 → None。"""
    pool = furnace_mutate_pool(item_name)
    if not pool:
        return None
    return pool[rng.randrange(len(pool))]


# ============================================================ 共用腿

def _remove_one(items: list[str], name: str) -> bool:
    """多重集移除该名一个实例(在册才减;不在 = 零移除返 False,
    上报无条件不判成败,不因此拒绝)。"""
    if name in items:
        items.remove(name)
        return True
    return False


def _resolve_row_unit(gs: GameState, row: str, slot: int) -> Unit | None:
    """目标身份解析:``row``/``slot``(画面物理排 + 排内槽位 1 基,与执行
    拖点同源坐标)→ 容器行域派生表现读单位(下标换算单一源 =
    ``cw_exec_state.deployed_idx_of``;取值时机 = 上报期现读)。
    行域未观察/槽位无单位(漂移)= None,bug 面由调用方留证零写。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        deployed_idx_of,
        deployed_rows_to_indexed,
    )
    dep = deployed_rows_to_indexed(gs.front_row.value, gs.back_row.value)
    idx = deployed_idx_of(row, slot)
    if not 0 <= idx < len(dep):
        return None
    return dep[idx]


def _write_row_equips_cleared(gs: GameState, row: str, unit: Unit, *,
                              evidence: str, sig: ChannelSig) -> bool:
    """行域穿戴清空写(扳手族/炉 char 腿共用):目标单位 ``equips`` 清空,
    其余成员原样;只写目标所在行域(效果行局部,禁把未观察姊妹行写成
    空表造假值)。行域值必已观察(单位自行域现读解析而来)。"""
    fld = gs.front_row if row == 'front' else gs.back_row
    units = fld.value
    if units is None:
        return False
    new_units = [replace(u, equips=[]) if u == unit else u for u in units]
    gs.write_logic(fld, new_units, produced_by=TOOL_USE_REPORT_PRODUCER,
                   evidence=evidence, sig=sig)
    return True


def _defect_zero_write(sig: ChannelSig, kind: str, *,
                       field_name: str, expected: Any, actual: Any,
                       evidence: str, detail: str) -> None:
    """零写分支统一留证(留证不停机;detail 区分因,消费真值归观察)。"""
    _emit_defect(field_name=field_name, expected=expected, actual=actual,
                 evidence=f'{evidence}:{detail}' if detail else evidence,
                 sig=sig, kind=kind)


def _equips_inv(gs: GameState) -> list[str] | None:
    """装备库存现读快照(None = 未观察,bug 面由调用方留证零写)。"""
    inv = gs.equips.value
    return None if inv is None else list(inv)


# ============================================================ 冶金炉

def report_action_furnace_use_param(gs: GameState, param: Any, sig: ChannelSig,
                                    *, rng: random.Random | None = None
                                    ) -> LogicOutcome:
    """冶金炉上报(变异面,双模式;容器写形态):
    - ``target_kind='equip'``(拖装备):**单笔 write_logic_rand 合并写**
      equips = 移除工具 ∧ 目标件 → 同类别采样替换;
    - ``target_kind='char'``(拖角色):①equips 单笔 write_logic_rand
      合并写 = 移除工具 ∧ 移除穿戴件 ∧ 追加各穿戴件同类别采样替换;
      ②目标角色行域 write_logic(穿戴清空)。
    变异面不走获得链、不触发获得回调(原地替换数量不变,候实机采证);
    采样命中 ``EQUIP_ACQUIRE_CONSEQUENCES`` 键集 → 留证行
    (kind=``furnace_mutate_consequence_candidate``,变异产物是否触发后果
    的实机采证钩子)。
    ``rng`` = 采样注入(pick_invest 先例关键字带缺省;None = 模块级缺省
    rng,实机缺省未播种 = 采样是猜测,sim 传流键 = 采样即世界真值)。
    """
    _validate_sig(sig, ('logic_action',))
    roll_rng = rng if rng is not None else _DEFAULT_RNG
    if param.target_kind == 'equip':
        return _furnace_equip_leg(gs, param, sig, roll_rng)
    if param.target_kind == 'char':
        return _furnace_char_leg(gs, param, sig, roll_rng)
    # 词表外 target_kind = bug 面:零写留证禁猜(禁猜出口保持受理,
    # 消费真值归观察)。
    _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                       field_name='equips',
                       expected="target_kind ∈ {'equip', 'char'}",
                       actual=repr(param.target_kind),
                       evidence='tool_furnace', detail='unknown_target_kind')
    return LogicOutcome(applied=True, reason='furnace_unknown_target_kind')


def _furnace_equip_leg(gs: GameState, param: Any, sig: ChannelSig,
                       rng: random.Random) -> LogicOutcome:
    """炉·拖装备腿:单笔合并采样替换写(rand 面)。"""
    inv = _equips_inv(gs)
    if inv is None:
        _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                           field_name='equips', expected='equips 已观察',
                           actual='equips 未观察(None)',
                           evidence='tool_furnace_equip',
                           detail='equips_unobserved')
        return LogicOutcome(applied=True, reason='furnace_equips_unobserved')
    if param.item_name not in inv:
        _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                           field_name='equips',
                           expected=f'目标件 {param.item_name!r} 在库',
                           actual=f'不在库(inv={inv!r})',
                           evidence='tool_furnace_equip',
                           detail='target_item_missing')
        return LogicOutcome(applied=True, reason='furnace_target_missing')
    new_item = furnace_mutate_sample(rng, param.item_name)
    if new_item is None:
        _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                           field_name='equips',
                           expected=f'{param.item_name!r} 同类别池可采样',
                           actual='目标件不在注册表/池空(禁猜)',
                           evidence='tool_furnace_equip',
                           detail='mutate_pool_unavailable')
        return LogicOutcome(applied=True, reason='furnace_pool_unavailable')
    # 合并单笔:移除工具 ∧ 移除目标件 ∧ 追加采样替换(禁拆两笔)。
    new_inv = list(inv)
    _remove_one(new_inv, '冶金炉')
    _remove_one(new_inv, param.item_name)
    new_inv.append(new_item)
    gs.write_logic_rand(
        gs.equips, new_inv, produced_by=TOOL_USE_REPORT_PRODUCER,
        evidence=f'tool_furnace_equip:{param.item_name}>{new_item}', sig=sig)
    _emit_consequence_candidates(gs, sig, [(param.item_name, new_item)],
                                 evidence='tool_furnace_equip')
    return LogicOutcome(
        applied=True,
        reason=f'furnace_mutated({param.item_name}>{new_item})')


def _furnace_char_leg(gs: GameState, param: Any, sig: ChannelSig,
                      rng: random.Random) -> LogicOutcome:
    """炉·拖角色腿:①equips 采样链 rand 合并写;②行域穿戴清空 logic 写。"""
    unit = _resolve_row_unit(gs, param.row, param.slot)
    if unit is None:
        _defect_zero_write(sig, DEFECT_TARGET_UNIT_MISSING,
                           field_name='front_row',
                           expected=f'({param.row},{param.slot}) 有单位',
                           actual='未观察/漂移无单位',
                           evidence='tool_furnace_char',
                           detail='target_unit_missing')
        return LogicOutcome(applied=True, reason='tool_target_unit_missing')
    worn = list(unit.equips or [])
    replacements: list[str] = []
    for w in worn:
        new_item = furnace_mutate_sample(rng, w)
        if new_item is None:
            _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                               field_name='equips',
                               expected=f'穿戴件 {w!r} 同类别池可采样',
                               actual='不在注册表/池空(禁猜)',
                               evidence='tool_furnace_char',
                               detail='mutate_pool_unavailable')
            return LogicOutcome(applied=True,
                                reason='furnace_pool_unavailable')
        replacements.append(new_item)
    inv = _equips_inv(gs)
    if inv is None:
        _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                           field_name='equips', expected='equips 已观察',
                           actual='equips 未观察(None)',
                           evidence='tool_furnace_char',
                           detail='equips_unobserved')
        return LogicOutcome(applied=True, reason='furnace_equips_unobserved')
    # ①合并单笔 rand:移除工具 ∧ 移除全部穿戴 ∧ 追加各采样替换。
    new_inv = list(inv)
    _remove_one(new_inv, '冶金炉')
    for w in worn:
        _remove_one(new_inv, w)
    new_inv.extend(replacements)
    ev = f'tool_furnace_char@{param.row}{param.slot}'
    gs.write_logic_rand(gs.equips, new_inv,
                        produced_by=TOOL_USE_REPORT_PRODUCER,
                        evidence=ev, sig=sig)
    _emit_consequence_candidates(gs, sig,
                                 list(zip(worn, replacements, strict=True)),
                                 evidence='tool_furnace_char')
    # ②行域穿戴清空(确定面:清空本身无随机)。
    _write_row_equips_cleared(gs, param.row, unit, evidence=f'{ev}#unequip',
                              sig=sig)
    return LogicOutcome(applied=True,
                        reason=f'furnace_char_mutated({len(worn)} items)')


def _emit_consequence_candidates(gs: GameState, sig: ChannelSig,
                                 pairs: list[tuple[str, str]], *,
                                 evidence: str) -> None:
    """变异后果采证钩子:采样命中 ``EQUIP_ACQUIRE_CONSEQUENCES`` 键集成员
    → 留证行,供实机局判读比对「变异产物是否触发后果」(推翻「变异不
    触发」即升格 ``on_equipment_gained``,design §1.4 采证点)。"""
    for src, new_item in pairs:
        if new_item in EQUIP_ACQUIRE_CONSEQUENCES:
            _emit_defect(field_name='equips',
                         expected='变异面不触发获得后果(候实机采证)',
                         actual=f'{src} → {new_item}(后果表成员)',
                         evidence=f'{evidence}:{src}>{new_item}',
                         sig=sig, kind=DEFECT_MUTATE_CONSEQUENCE_CANDIDATE)


# ============================================================ 特权赋予卡

def report_action_privilege_card_use_param(gs: GameState, param: Any,
                                           sig: ChannelSig) -> LogicOutcome:
    """特权赋予卡上报(双腿):
    - ``target_kind='equip'``(库存腿):**单笔 write_logic 合并写**
      equips = 移除工具 ∧ 目标件名 → ``privilege_counterpart`` 替换
      (映射桥;同名多件全替换与库存桥 ``transform_equip_to_privilege``
      同口径,禁第二套);桥零写分支透传(库存未观察/无此件)→ 留证
      kind=``tool_bridge_zero_write``;
    - 其余(拖角色腿):**fail-closed 零写** + 留证
      (kind=``tool_privilege_worn_unsupported``;用户裁定 2026-09-21 按
      不能拖角色处理候实机测试,判据面现役只产库存腿,收到 char 腿 =
      bug 面留证)。
    变异面(数量不变的原地变换)不走获得链、不触发获得回调。
    """
    _validate_sig(sig, ('logic_action',))
    if param.target_kind != 'equip':
        _defect_zero_write(sig, DEFECT_PRIVILEGE_WORN_UNSUPPORTED,
                           field_name='front_row',
                           expected='库存腿(target_kind=equip,判据面现役只产库存腿)',
                           actual=f'target_kind={param.target_kind!r}',
                           evidence='tool_privilege',
                           detail='worn_unsupported')
        return LogicOutcome(applied=True,
                            reason='privilege_worn_unsupported')
    inv = _equips_inv(gs)
    if inv is None:
        _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                           field_name='equips', expected='equips 已观察',
                           actual='equips 未观察(None)',
                           evidence='tool_privilege_equip',
                           detail='equips_unobserved')
        return LogicOutcome(applied=True,
                            reason='privilege_equips_unobserved')
    if param.item_name not in inv:
        _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                           field_name='equips',
                           expected=f'目标件 {param.item_name!r} 在库',
                           actual=f'不在库(inv={inv!r})',
                           evidence='tool_privilege_equip',
                           detail='target_item_missing')
        return LogicOutcome(applied=True, reason='privilege_target_missing')
    target = privilege_counterpart(param.item_name)
    # 合并单笔:移除工具 ∧ 变换同笔(映射桥 privilege_counterpart;
    # 禁拆两笔——拆两笔 = 中间态 + 二次失配面)。
    new_inv = list(inv)
    _remove_one(new_inv, '特权赋予卡')
    new_inv = [target if n == param.item_name else n for n in new_inv]
    gs.write_logic(gs.equips, new_inv, produced_by=TOOL_USE_REPORT_PRODUCER,
                   evidence=f'tool_privilege_equip:{param.item_name}>{target}',
                   sig=sig)
    return LogicOutcome(applied=True,
                        reason=f'privilege_transformed({target})')


# ============================================================ 扳手族

def _wrench_report(gs: GameState, param: Any, sig: ChannelSig, *,
                   tool_name: str, consume: bool) -> LogicOutcome:
    """扳手族共用实现:**两笔 write_logic**——①equips 合并写 = 移除工具
    (``consume``;精密扳手无限次不递减)+ 追加目标角色全部穿戴件;
    ②目标角色行域穿戴清空。归属迁移非获得,不走获得链。"""
    _validate_sig(sig, ('logic_action',))
    unit = _resolve_row_unit(gs, param.row, param.slot)
    if unit is None:
        _defect_zero_write(sig, DEFECT_TARGET_UNIT_MISSING,
                           field_name='front_row',
                           expected=f'({param.row},{param.slot}) 有单位',
                           actual='未观察/漂移无单位',
                           evidence=f'tool_{tool_name}',
                           detail='target_unit_missing')
        return LogicOutcome(applied=True, reason='tool_target_unit_missing')
    worn = list(unit.equips or [])
    ev = f'tool_{tool_name}@{param.row}{param.slot}'
    inv = _equips_inv(gs)
    if inv is None:
        # ①腿 bug 面(库存未观察):零写留证;②腿(行域)独立事实照写。
        _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                           field_name='equips', expected='equips 已观察',
                           actual='equips 未观察(None)',
                           evidence=ev, detail='equips_unobserved')
    else:
        new_inv = list(inv)
        if consume:
            _remove_one(new_inv, tool_name)
        new_inv.extend(worn)
        gs.write_logic(gs.equips, new_inv,
                       produced_by=TOOL_USE_REPORT_PRODUCER,
                       evidence=f'{ev}#return', sig=sig)
    _write_row_equips_cleared(gs, param.row, unit, evidence=f'{ev}#unequip',
                              sig=sig)
    return LogicOutcome(applied=True,
                        reason=f'wrench_unequipped({len(worn)} items,'
                               f'consume={consume})')


def report_action_wrench_use_param(gs: GameState, param: Any,
                                   sig: ChannelSig) -> LogicOutcome:
    """拆装扳手上报:目标角色装备全量回区(两笔 logic 合并写:equips =
    移除工具 ∧ 追加穿戴件;行域穿戴清空),工具消耗品 −1(合并同笔)。"""
    return _wrench_report(gs, param, sig, tool_name='拆装扳手', consume=True)


def report_action_precision_wrench_use_param(gs: GameState, param: Any,
                                             sig: ChannelSig) -> LogicOutcome:
    """精密拆装扳手上报:同拆装扳手,**equips 不移除工具**(无限次用
    不递减;重复获得改 +1 金 = 贡献算术获得回执窗,不在本上报辖)。"""
    return _wrench_report(gs, param, sig, tool_name='精密拆装扳手',
                          consume=False)


# ============================================================ 投影仪族

def _projector_report(gs: GameState, param: Any, sig: ChannelSig, *,
                      tool_name: str, cost_gate: int) -> LogicOutcome:
    """投影仪族共用实现:①equips ``write_logic`` 移除工具;②获得走链
    ``gain_character(char, 1★)``(复制进席触发 3 合 1 = 口述·权威
    2026-09-21;席满溢出/落点 = 链语义承接)。费用门(≤3,注册表现读
    ``bench_char_cost``)前置查 = 防御纵深(发射位判据面已辖),超门 =
    留证零写。"""
    _validate_sig(sig, ('logic_action',))
    unit = _resolve_row_unit(gs, param.row, param.slot)
    if unit is None:
        _defect_zero_write(sig, DEFECT_TARGET_UNIT_MISSING,
                           field_name='front_row',
                           expected=f'({param.row},{param.slot}) 有单位',
                           actual='未观察/漂移无单位',
                           evidence=f'tool_{tool_name}',
                           detail='target_unit_missing')
        return LogicOutcome(applied=True, reason='tool_target_unit_missing')
    char = str(unit.char_id or '')
    if cost_gate > 0:
        cost = bench_char_cost(unit)
        if cost > cost_gate:
            _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                               field_name='equips',
                               expected=f'拖动目标 ≤{cost_gate} 费(官方前置门)',
                               actual=f'{char} 费用 {cost}(注册表现读)',
                               evidence=f'tool_{tool_name}',
                               detail='cost_gate_over')
            return LogicOutcome(applied=True, reason='projector_cost_gate')
    ev = f'tool_{tool_name}@{param.row}{param.slot}'
    inv = _equips_inv(gs)
    if inv is None:
        _defect_zero_write(sig, DEFECT_BRIDGE_ZERO_WRITE,
                           field_name='equips', expected='equips 已观察',
                           actual='equips 未观察(None)',
                           evidence=ev, detail='equips_unobserved')
    else:
        new_inv = list(inv)
        _remove_one(new_inv, tool_name)
        gs.write_logic(gs.equips, new_inv,
                       produced_by=TOOL_USE_REPORT_PRODUCER,
                       evidence=f'{ev}#consume', sig=sig)
    outcome = gain_character(gs, char, 1, rand=False, sig=sig,
                             evidence=f'{ev}:copy', producer=TOOL_USE_REPORT_PRODUCER)
    return LogicOutcome(
        applied=True,
        reason=f'projector_copied({char},landing={outcome.landing},'
               f'merges={outcome.merge_levels})')


def report_action_staff_projector_use_param(gs: GameState, param: Any,
                                            sig: ChannelSig) -> LogicOutcome:
    """员工投影仪上报:复制进席走获得链(费用门 ≤3 前置查,防御纵深)。"""
    return _projector_report(gs, param, sig, tool_name='员工投影仪',
                             cost_gate=3)


def report_action_perfect_projector_use_param(gs: GameState, param: Any,
                                              sig: ChannelSig) -> LogicOutcome:
    """完美投影仪上报:同员工投影仪,无费用门。"""
    return _projector_report(gs, param, sig, tool_name='完美投影仪',
                             cost_gate=0)


# ============================================================ 好运令牌

def report_action_lucky_token_use_param(gs: GameState, param: Any,
                                        sig: ChannelSig) -> LogicOutcome:
    """好运令牌上报:**零写 + 留证**(kind=``tool_token_not_admitted``
    注记)。发射位判据面 fail-closed 永不准入(R9 判据批挂账,禁无判据
    发射),写端随 R9 判据批;本函数在场 = 命名规约完备锁对象。"""
    _validate_sig(sig, ('logic_action',))
    _ = gs
    _emit_defect(field_name='equips',
                 expected='令牌发射永不准入(判据面 fail-closed,写端随 R9 判据批)',
                 actual=f'收到令牌上报(row={param.row!r},slot={param.slot!r})',
                 evidence='tool_lucky_token', sig=sig,
                 kind=DEFECT_TOKEN_NOT_ADMITTED)
    return LogicOutcome(applied=True, reason='token_not_admitted')
