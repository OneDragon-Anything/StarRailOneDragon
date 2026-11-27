"""货币战争 羁绊口径单一源(判断层,手维护)。

**board 口径的 per-unit 标签函数**——各消费方共用本函数,规则同源(一个函数):

- 羁绊计数:``_recount_board``(本模块;board 的唯一算法);
- 同一标签函数套在状态容器行上的入口:``cw_game_state._row_unit_tags``(只服务模拟器后端的盛会之星判定,不参与羁绊计数);
- 资格判定与部署搜索:``cw_faction_callbacks``、``strategies/impl/mandate_v1/deploy_search.py``。

口径分层(sim-wiring.md「羁绊口径分层」节):

- **L1 纯羁绊全集**:factions + schools + independent(三类都从角色注册表直取);
- **L2 装备羁绊贡献(雏形,本模块落地)**:**星徽 = 额外增加一个羁绊**
  (add-if-absent;装备者已拥有该羁绊时不重复计数,用户口述裁定)/
  欢愉卡带与星核猎手卡带 = **计数 +1**
  (无条件,可双计)——装备授予的羁绊计入羁绊计数(缺计会让带星徽的
  对局档位系统性低估);
- L3 全战力(装备 props 强度/投资环境/档位效果数值)**不在本模块**,
  归 win_model 迭代(分层裁决)。
"""
from __future__ import annotations

import re

from sr_od.application.currency_war.data.cw_chars import (
    get_char,
)
from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS
from sr_od.application.currency_war.data.cw_traits_data import trait_by_name

# 星徽:「装备者加入【X】羁绊。」(装备注册表 22 张星徽 desc 统一句式,
# cw_equipment_data.py:102-123;数据层 plaza API 溯源)
_RX_BADGE = re.compile(r'加入【(.+?)】羁绊')
# 骇客卡带:「装备者加入「X」羁绊,若…已是…成员,则…计数+1」(欢愉卡带系)
_RX_TAPE = re.compile(r'加入「(.+?)」羁绊')
# 骇客卡带:「「X」羁绊计数+1。」(星核猎手卡带系,无条件 +1)
_RX_TAPE_COUNT = re.compile(r'「(.+?)」羁绊计数\+1')


def _parse_badge(eq) -> tuple[str, ...]:
    """星徽的羁绊贡献 → (羁绊名) 或 ()。

    **语义(用户口述裁定,最高权威)**:星徽 = 给装备者**额外增加一个羁绊**
    ——只把没有该羁绊的单位变成成员;装备者已是该羁绊成员时**不重复计数**
    (≠ 卡带的「计数+1」)。unit_bond_tags 按 add-if-absent 消费本表。
    """
    if eq is None or eq.category != '星徽':
        return ()
    m = _RX_BADGE.search(eq.effect or '')
    return (m.group(1),) if m else ()


def _parse_tape(eq) -> tuple[str, ...]:
    """骇客卡带的羁绊贡献 → (羁绊名) 或 ()。

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
# 并集视图(查询面兼容;语义分流见上两表)
_EQUIP_BOND_GRANTS: dict[str, tuple[str, ...]] = {
    eq.name: _parse_grants(eq) for eq in EQUIPMENTS.values()
}


def equip_bond_grants(equip_name: str) -> tuple[str, ...]:
    """查单件装备的羁绊贡献(羁绊名元组;无贡献=())。"""
    return _EQUIP_BOND_GRANTS.get(equip_name, ())


def unit_bond_tags(bc) -> tuple[str, ...]:
    """一个已上阵单位的羁绊标签**多集**(L1 全集 + L2 装备贡献)。

    - 角色:CHARACTERS 注册表 factions + schools + independent 全集;
    - 装备分两类语义(用户口述裁定,最高权威):
      * **星徽 = 额外增加一个羁绊**(add-if-absent):只把没有该羁绊的
        单位变成成员;装备者已拥有该羁绊(自报或其他装备已授)时**不重复计数**;
      * **卡带(欢愉/星核猎手系)= 计数 +1**(无条件,可双计:成员佩戴者
        对该羁绊贡献 2 = 自身 1 + 卡 1);
    - 身份未知(char_id 空/'?'/不在注册表)→ **空元组**:该单位对任何羁绊
      零贡献(``_recount_board`` 不计它,也不回退别的字段;状态容器行上的入口
      ``cw_game_state._row_unit_tags`` 调的是本函数,结果同样是空元组——Unit 无 faction 位)。

    duck-typed:凡带 char_id/equips 属性(Unit 或
    SimpleNamespace shim)皆可——实机/sim/检查三侧同函数。
    """
    cid = getattr(bc, 'char_id', '') or ''
    if not cid or cid == '?':
        return ()
    ch = get_char(cid)
    if ch is None:
        return ()
    tags: list[str] = [*ch.factions, *ch.schools]
    if ch.independent:
        tags.append(ch.independent)
    seen = set(tags)
    equips = list(getattr(bc, 'equips', None) or [])
    # 两遍法(幂等性):第一遍收齐全部门卡带授予集 T̄——星徽的「已有不重复」
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


# ============================================================
# 羁绊计数(board)
# _recount_board:构建于本模块 unit_bond_tags 之上,board 的唯一算法。
# ============================================================

# 羁绊注册表 Trait.count_mode 的取值之一:「只数三星」。取值由生成器
# skills/sr-od-dev-currency-war/scripts/gen_traits.py 的覆盖表产出;注册表文件
# 是生成器整文件重写的产物,常量不放那边(手加的下次重跑生成就没了)。
_COUNT_MODE_STAR3: str = 'STAR3'


def _recount_board(deployed: list) -> dict[str, int]:
    """上阵单位的羁绊计数(board 的唯一算法,读时现算)。

    输入 = **不截断的平铺列表**:前排单位 + 后排单位的全子表
    (``cw_game_state.deployed_rows_of_view`` 返回的两段拼起来)。后排第 7–9
    格的单位必须在表里——传定长 10 格工作表(``deployed_indexed_of_view``)
    会把它们截掉,计数随之偏少。空表或 None → ``{}``,表内的空槽(None)跳过。

    口径:

    - 单位标签 = :func:`unit_bond_tags`(出身羁绊 + 装备授予的羁绊);
    - **按羁绊注册表的计数方式数**(``data/cw_traits_data.py`` 的
      ``trait_by_name[羁绊名].count_mode``):「只数三星」的羁绊只计星级
      不低于 3 的单位,其余羁绊与不在注册表的标签按上场人数计;
    - 星级门对该羁绊的全部标签一视同仁:出身标签、星徽与卡带授予的标签
      都设门。依据 = 官方原文「每上场 1 位 3 星【千星商会】角色,将激活
      1 级羁绊效果」讲的是这个羁绊怎么数,读不出只限出身成员;
    - 用「不低于 3」而非「等于 3」:该羁绊高档位的官方效果会把商店角色
      升到 4 星,升星反而丢计数与效果自相矛盾;
    - 单位没有星级属性时,「只数三星」的羁绊不计;
    - **未知身份的单位不计**(char_id 空 / '?' / 不在注册表 → 零贡献),
      同表其余单位照计。
    """
    out: dict[str, int] = {}
    for d in (deployed or []):
        if d is None:
            continue
        star = getattr(d, 'star', None)
        star3_ok = star is not None and int(star) >= 3
        for t in unit_bond_tags(d):
            trait = trait_by_name.get(t)
            if (trait is not None
                    and trait.count_mode == _COUNT_MODE_STAR3
                    and not star3_ok):
                continue
            out[t] = out.get(t, 0) + 1
    return out

