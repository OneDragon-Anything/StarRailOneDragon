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
- **L2 装备羁绊贡献(雏形,本模块落地)**:星徽「装备者加入【X】羁绊」/
  欢愉卡带「加入欢愉,已是成员则计数+1」/星核猎手卡带「羁绊计数+1」
  ——装备后左面板该羁绊行人数 +1,是面板真值的一部分(W49 §2:
  此前三处全缺 → computed_vs_ocr 常态化误报 + 星徽局档位系统性低估);
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


def _parse_grants(eq) -> tuple[str, ...]:
    """单件装备的羁绊贡献解析 → (羁绊名, ...)。

    - 星徽(category='星徽')→ 「装备者加入【X】羁绊」;
    - 骇客卡带:欢愉卡带系「加入「X」羁绊,若已是成员则计数+1」——
      **净效果 = 无条件 +1**(非成员:加入即 +1;已是成员:条款保证
      计数仍 +1——这是唯一突破「一人一标签」上限的机制:成员佩戴者
      对该羁绊贡献 2 = 自身 1 + 卡 1,W49 §2);星核猎手卡带系
      「「X」羁绊计数+1」同无条件 +1;
    - 其余装备(进阶/特权/白昼/命运/简易/工具)无羁绊贡献 → ()。
    """
    if eq is None:
        return ()
    if eq.category == '星徽':
        m = _RX_BADGE.search(eq.effect or '')
        return (m.group(1),) if m else ()
    if eq.category == '骇客':
        m = _RX_TAPE.search(eq.effect or '')
        if m:
            return (m.group(1),)
        m2 = _RX_TAPE_COUNT.search(eq.effect or '')
        if m2:
            return (m2.group(1),)
    return ()


# 装备 → 羁绊贡献表(import 时从注册表派生;注册表数据层演进自动跟)
_EQUIP_BOND_GRANTS: dict[str, tuple[str, ...]] = {
    eq.name: _parse_grants(eq) for eq in EQUIPMENTS.values()
}


def equip_bond_grants(equip_name: str) -> tuple[str, ...]:
    """查单件装备的羁绊贡献(羁绊名元组;无贡献=())。"""
    return _EQUIP_BOND_GRANTS.get(equip_name, ())


def unit_bond_tags(bc) -> tuple[str, ...]:
    """一个已上阵单位的羁绊标签**多集**(L1 全集 + L2 星徽装备贡献;ADR-0312)。

    - 角色:CHARACTERS 注册表 factions + flows + independent 全集;
      开拓者按 ``position_pref`` 归一形态(前排=记忆/后排=欢愉,
      与 board_from_tracked/W21 #13 同口径);
    - 装备:``bc.equips`` 逐件查 ``equip_bond_grants``——加入式星徽/卡带
      追加该羁绊(净效果无条件 +1;成员佩戴者对该羁绊贡献 2 = 自身 1 +
      卡 1,「一人一标签」上限的唯一突破机制);
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
    for eq in (getattr(bc, 'equips', None) or []):
        tags.extend(_EQUIP_BOND_GRANTS.get(eq, ()))
    return tuple(tags)
