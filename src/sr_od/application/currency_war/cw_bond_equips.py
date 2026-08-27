"""货币战争 羁绊口径单一源(判断层,手维护;W50,ADR-0312;2026-08-25)。

**board 口径的 per-unit 标签函数**——三处统计实机/派生/检查共用本函数,
规则同源(一个函数):

- 实机计算路径:``cw_observation.board_from_tracked``(面板真值对齐);
- sim/状态派生路径:``cw_state._recount_board``(= ``cw_sim._board_counts_of``,
  DeployMove/事务/围栏后的 board 维护);
- 检查镜像:``cw_sim_checks._board_agg_of_deployed_row``(账本行聚合)。

口径分层(ADR-0312;sim-wiring.md「羁绊口径分层」节):

- **L1 纯羁绊全集**:factions + flows + independent(独立羁绊行与左面板
  同口径),开拓者按当前排归一形态(前排=记忆/后排=欢愉);
- **L2 装备羁绊贡献(雏形,本模块落地)**:**星徽 = 额外增加一个羁绊**
  (add-if-absent;装备者已拥有该羁绊时不重复计数,用户口述 2026-08-28
  修订 W49 的「无条件+1」口径)/ 欢愉卡带与星核猎手卡带 = **计数 +1**
  (无条件,可双计)——装备贡献是面板真值的一部分(W49 §2:此前三处全缺
  → computed_vs_ocr 常态化误报 + 星徽局档位系统性低估);
- L3 全战力(装备 props 强度/投资环境/档位效果数值)**不在本模块**,
  归 win_model 迭代(W49 裁决 4)。
"""
from __future__ import annotations

import re

from sr_od.application.currency_war.cw_chars import (
    CHARACTERS,
    is_trailblazer,
    trailblazer_form,
)
from sr_od.application.currency_war.cw_equipment_data import EQUIPMENTS

# 星徽:「装备者加入【X】羁绊。」(装备注册表 22 张星徽 desc 统一句式,
# cw_equipment_data.py:102-123;数据层 plaza API 溯源)
_RX_BADGE = re.compile(r'加入【(.+?)】羁绊')
# 骇客卡带:「装备者加入「X」羁绊,若…已是…成员,则…计数+1」(欢愉卡带系)
_RX_TAPE = re.compile(r'加入「(.+?)」羁绊')
# 骇客卡带:「「X」羁绊计数+1。」(星核猎手卡带系,无条件 +1)
_RX_TAPE_COUNT = re.compile(r'「(.+?)」羁绊计数\+1')


def _parse_badge(eq) -> tuple[str, ...]:
    """星徽的羁绊贡献 → (羁绊名,) 或 ()。

    **语义(用户口述 2026-08-28,最高权威)**:星徽 = 给装备者**额外增加一个羁绊**
    ——只把没有该羁绊的单位变成成员;装备者已是该羁绊成员时**不重复计数**
    (≠ 卡带的「计数+1」)。unit_bond_tags 按 add-if-absent 消费本表。
    """
    if eq is None or eq.category != '星徽':
        return ()
    m = _RX_BADGE.search(eq.effect or '')
    return (m.group(1),) if m else ()


def _parse_tape(eq) -> tuple[str, ...]:
    """骇客卡带的羁绊贡献 → (羁绊名,) 或 ()。

    两系卡带都是**无条件计数 +1**(可双计,区别于星徽):
    - 欢愉卡带系「加入…若已是成员,则计数+1」——净效果无条件 +1
      (非成员:加入即 +1;已是成员:条款保证仍 +1);
    - 星核猎手卡带系「计数+1」直接无条件。
    """
    if eq is None or eq.category != '骇客':
        return ()
    m = _RX_TAPE.search(eq.effect or '')
    if m:
        return (m.group(1),)
    m2 = _RX_TAPE_COUNT.search(eq.effect or '')
    if m2:
        return (m2.group(1),)
    return ()


def _parse_grants(eq) -> tuple[str, ...]:
    """单件装备的羁绊贡献解析(星徽+卡带并集)→ (羁绊名, ...)。

    仅作查询面兼容(equip_bond_grants 消费);计数语义的分流
    (星徽 add-if-absent / 卡带无条件+1)在 unit_bond_tags 内按类别表执行。
    """
    return _parse_badge(eq) or _parse_tape(eq)


# 星徽授予表(import 时从注册表派生;unit_bond_tags 按 add-if-absent 消费)
_BADGE_BOND_GRANTS: dict[str, tuple[str, ...]] = {
    eq.name: _parse_badge(eq) for eq in EQUIPMENTS.values()
}
# 卡带授予表(无条件 +1,可双计)
_TAPE_BOND_GRANTS: dict[str, tuple[str, ...]] = {
    eq.name: _parse_tape(eq) for eq in EQUIPMENTS.values()
}
# 并集视图(查询面兼容;W50 起存在,语义分流见上两表)
_EQUIP_BOND_GRANTS: dict[str, tuple[str, ...]] = {
    eq.name: _parse_grants(eq) for eq in EQUIPMENTS.values()
}


def equip_bond_grants(equip_name: str) -> tuple[str, ...]:
    """查单件装备的羁绊贡献(羁绊名元组;无贡献=())。"""
    return _EQUIP_BOND_GRANTS.get(equip_name, ())


def unit_bond_tags(bc) -> tuple[str, ...]:
    """一个已上阵单位的羁绊标签**多集**(L1 全集 + L2 装备贡献;ADR-0312)。

    - 角色:CHARACTERS 注册表 factions + flows + independent 全集;
      开拓者按 ``position_pref`` 归一形态(前排=记忆/后排=欢愉,
      与 board_from_tracked/W21 #13 同口径);
    - 装备分两类语义(用户口述 2026-08-28,最高权威):
      * **星徽 = 额外增加一个羁绊**(add-if-absent):只把没有该羁绊的
        单位变成成员;装备者已拥有该羁绊(自报或其他装备已授)时**不重复计数**;
      * **卡带(欢愉/星核猎手系)= 计数 +1**(无条件,可双计:成员佩戴者
        对该羁绊贡献 2 = 自身 1 + 卡 1);
    - 身份未知(char_id 空/'?'/不在注册表)→ **空元组**(调用方决定兜底:
      board_from_tracked 整体 bail;_recount_board 回退 faction 字段)。

    duck-typed:凡带 char_id/position_pref/equips 属性(BenchChar 或
    SimpleNamespace shim)皆可——实机/sim/检查三侧同函数。
    """
    cid = getattr(bc, 'char_id', '') or ''
    if not cid or cid == '?':
        return ()
    row = getattr(bc, 'position_pref', 'back') or 'back'
    if is_trailblazer(cid):
        cid = trailblazer_form(cid, row)
    ch = CHARACTERS.get(cid)
    if ch is None:
        return ()
    tags: list[str] = [*ch.factions, *ch.flows]
    if ch.independent:
        tags.append(ch.independent)
    seen = set(tags)
    equips = list(getattr(bc, 'equips', None) or [])
    # 两遍法(P19 幂等性):第一遍收齐全部门卡带授予集 T̄——星徽的「已有不重复」
    # 以终局成员身份为准,与装备穿戴顺序无关(「卡带X+星徽X」无论先后均计 1);
    # 第二遍星徽判 x∉seen∪T̄、卡带无条件 +1(可双计,不查 seen)。
    tape_grants = {b for eq in equips for b in _TAPE_BOND_GRANTS.get(eq, ())}
    for eq in equips:
        for b in _TAPE_BOND_GRANTS.get(eq, ()):
            tags.append(b)                 # 卡带:无条件 +1(可双计)
        for b in _BADGE_BOND_GRANTS.get(eq, ()):
            if b not in seen and b not in tape_grants:
                seen.add(b)                # 星徽:额外增加一个羁绊(已有[自报/卡带/先到星徽]不重复)
                tags.append(b)
    return tuple(tags)
