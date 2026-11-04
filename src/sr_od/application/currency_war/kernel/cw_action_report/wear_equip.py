"""货币战争动作上报:穿装备(report_action_wear_equip_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。状态容器、写入口与观察
写端留在 ``kernel/cw_game_state``,本包 → 状态容器单向依赖。

**穿着即合成分支**(游戏规则,语义权威版本 =
``docs/game/currency_war/research/equipment_mechanics.md``「穿着即合成」:
穿戴后该角色 worn 集内可合成的两件立即合成为进阶件,循环至无可合成,
两两配方 = ``cw_synthesis.synthesize_target`` K8 闭合):穿戴落位与
合成在同一写序内完成——owned 摘件 → worn 集合成 → 目标域整表重建写
(bench/deployed 两域,合成产物落 worn 集尾;
前后排 = deployed 单字段视图)。持装备获得转换卡局的合成产物经转换
预测面替换(判定单源 = cw_gain_chain 转换登记表,合成域与获得域同判,
禁第二份类别谓词——预测产物与实机游戏自算转换同形,对账不失真)。
规则住本上报
= kernel 单一源(sim 与实机动作分支同构消费,禁第二份实现);合成改变
板面装备贡献 → 落地写后广播 ``board_changed`` 事实事件。

拒绝语义(布尔契约,统一回声;拒绝 = 零写 + 留存证据,禁半写):
- owned 无该件 → ``wear_item_not_owned``(合法穿戴前置,漏 = 计划失效);
- 目标槽位解析失败(越界/空槽/在位者与 char_name 不符 = 陈旧提案;
  计划步恒戳物理槽位定位,定位序见 :func:`_locate_unit`)→
  ``wear_target_unit_missing``(front-only 回退步拖空槽 avatar = 游戏
  侧静默拒,上报如实拒);
- 合成后仍超 ``WEAR_LIMIT`` → ``wear_over_cap_rejected``(上限按合成后
  计:穿着即合成可能净减件数)。
"""

from __future__ import annotations

from collections.abc import Callable
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

#: 角色穿戴上限(equipment_mechanics.md「角色上限 3 件」定案)。
WEAR_LIMIT: int = 3

_PRODUCER = 'CwActionWearEquipParam'


def _wear_synthesis(equips: list[str],
                    convert: Callable[[str], str] | None = None
                    ) -> list[str]:
    """穿着即合成(worn 集内两两配方,循环至无可合成;K8 闭合保证
    终止:基础件对数有限,每次合成件数 −1)。

    convert = 合成产物获得转换注入(持「合成与获得进阶装备时改为获得Y」
    卡局的产物替换,判定单源 = cw_gain_chain 转换登记表预测面;None =
    零转换感知)。转换产物以替换名入 worn 集——登记目标不属配方组件域
    (recipes 空,如好运令牌工具类),不再参与后续配方,终止性不变。"""
    items = list(equips)
    changed = True
    while changed:
        changed = False
        for i in range(len(items)):
            merged = False
            for j in range(i + 1, len(items)):
                target = synthesize_target(items[i], items[j])
                if target is not None:
                    if convert is not None:
                        target = convert(target)
                    items = [t for k, t in enumerate(items)
                             if k not in (i, j)]
                    items.append(target)
                    merged = True
                    changed = True
                    break
            if merged:
                break
    return items


def _synthesis_convert(gs: GameState) -> Callable[[str], str] | None:
    """合成产物转换判定构建(持装备获得转换卡局返回产物替换回调,判定
    单源 = cw_gain_chain 转换预测面惰性转调;不持卡 = None,连链模块
    import 都不发生,零转换感知局零开销)。穿着即合成的产物 = 游戏侧
    「合成获得进阶装备」,持「改为获得」卡局的预测须与获得链同判定,
    禁第二份类别谓词表达式。"""
    if not gs.active_strategies.value:
        return None
    from sr_od.application.currency_war.kernel.cw_gain_chain import (
        equip_gain_conversion_target,
    )
    return lambda item: equip_gain_conversion_target(gs, item) or item


def _locate_unit(gs: GameState, param: Any) -> tuple[str, int, Unit] | None:
    """定位穿戴目标单位。

    定位序 = **物理槽位定位先行**:计划步恒戳 (row, slot)
    (``cw_equip_wear_plan`` M7 分配自 deployed 视图派生 / front-only
    回退步空槽序),且机械拖拽的真实落点 = 该槽位 avatar——账随拖点走。
    同名角色跨域在场(deployed + bench 各一份)时,名匹配 bench 先序会
    记到**另一个**单位身上:席上副本穿满 → 超限拒单零写 → 决策环同
    输入重派无限自旋(sim 实证);实机同构时账面与画面分裂(下一入口
    观察失配)。槽位解析失败/在位者身份与 char_name 不符 = 陈旧提案,
    拒单(禁静默按名改目标)。row/slot 缺省(row 空)的调用面走原名
    匹配回退(bench → deployed 全域,char_name 空按槽位现读的原
    front-only 形态已被槽位先行覆盖)。[索引定义] row ∈ 'front'|'back'
    (词表通用声明),slot = 画面物理槽位 1 基,deployed 域 = DeployedView
    子表下标 + 1(位置 = 子表下标派生);bench 域 = BenchView 槽序
    (视图槽 i ↔ 画面槽位 i+1)。

    Returns:
        ``(域键, 下标, 单位)``;未命中 = None。
    """
    char_name = str(getattr(param, 'char_name', '') or '')
    row = str(getattr(param, 'row', '') or '')
    slot = int(getattr(param, 'slot', 0) or 0)
    view = gs.deployed.value
    if view is not None and row in ('front', 'back') and slot >= 1:
        sub = (view.front_slots if row == 'front'
               else view.back_slots) or []
        if 1 <= slot <= len(sub):
            u = sub[slot - 1]
            if u is not None and (not char_name
                                  or u.char_id == char_name):
                return (('front_row' if row == 'front' else 'back_row'),
                        slot - 1, u)
        # 槽位已戳但解析不得(越界/空槽)或身份不符 = 陈旧提案,如实拒
        #(零写返回主循环重派,下帧计划重戳新槽位);禁回退名匹配静默改目标。
        return None
    bench_view = gs.bench.value
    if char_name and bench_view is not None:
        for i, s in enumerate(bench_view.slots):
            if (s is not None and s.kind == 'unit' and s.unit is not None
                    and s.unit.char_id == char_name):
                return ('bench', i, s.unit)
    if view is not None:
        for key, sub in (('front_row', view.front_slots),
                         ('back_row', view.back_slots)):
            if char_name:
                for i, u in enumerate(sub or []):
                    if u is not None and u.char_id == char_name:
                        return (key, i, u)
    return None


def _write_mutated_domain(gs: GameState, domain: str, idx: int,
                          unit: Unit, sig: ChannelSig) -> None:
    """目标域整表重建写(状态容器视图 frozen 链,穿戴写 = 域整表重建;
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
    物理槽位(词表定义;计划步恒戳,机械拖拽落点),目标定位 =
    ``_locate_unit`` 槽位定位先行 + 无槽位调用面名匹配回退
    (3.2 起 tracked 第二账停用,主域单点)。

    拒绝分支(零写 + 留存证据,布尔契约见模块头):owned 无件 / 目标不已登记 /
    合成后超上限。``board_changed`` 事实事件仅 applied 出口广播
    (拒绝 = 零写 = 无状态副本变化)。
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
    worn = _wear_synthesis(list(unit.equips) + [param.item_name],
                           convert=_synthesis_convert(gs))
    if len(worn) > WEAR_LIMIT:
        return _reject('wear_over_cap_rejected',
                       f'合成后 ≤{WEAR_LIMIT} 件',
                       f'合成后 {len(worn)} 件:{worn}')
    new_unit = replace(unit, equips=worn)
    _write_mutated_domain(gs, domain, idx, new_unit, _grp_sig)
    owned.remove(param.item_name)
    gs.write_logic(gs.equips, owned, produced_by=_PRODUCER,
                   evidence=f'owned[{param.item_name}] -1(穿戴)', sig=_grp_sig)
    # (tracked 第二账已停用:状态容器侧本函数
    #  _write_mutated_domain 整值替换写已是单点,原「tracked deployed
    #  穿戴随动分支」无可同步;session 形参兼容保留。)
    # (事实事件广播已停用。)
    # 合成事件发放条目(「合成装备时获得2次刷新」卡效果):穿着即合成的
    # 合成次数 = 输入件数 − 输出件数,>0 才查账——三拒绝分支在上方早退
    # (applied=False)不达此处,零合成零发放天然成立。惰性 import:效果
    # 账本模块头零包内 import 契约同族纪律,防反向拉起成环。
    merged = (len(unit.equips) + 1) - len(worn)
    if merged > 0:
        from sr_od.application.currency_war.kernel.cw_effect_inventory import (
            apply_on_merge_refresh_grant,
        )
        apply_on_merge_refresh_grant(gs, merges=merged, frame='wear')
    return LogicOutcome(applied=True)
