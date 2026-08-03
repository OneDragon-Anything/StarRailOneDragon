"""货币战争 装备领域模型(Equipment + EQUIPMENTS 注册表;meta 层,V4.4)。

**来源**:米游社百科「货币战争图鉴·装备」`channel/map/209/211`(content/info API,2026-08-03),
详 ``docs/game/currency_war/data/equipment.md``(~130 件:简易7/进阶33/特权27/星徽22/白昼6/Fate~24/工具11)。

**用途**:装备规范名单一真相源 —— COMP_LIBRARY.key_equips / 补给决策 / equip_fit 都引用规范装备名。
本注册表先收**策略相关 key 装备**(COMP_LIBRARY 引用 + meta 核心);全量 ~130 在 equipment.md,
随补给/合成决策(阶段 3a)接线时补全。

**为什么建模**(用户 2026-08-03):核心实体建正规 model 类 + 注册表(可查询/可校验),非魔法字符串。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Equipment:
    """单件装备(V4.4 图鉴规范数据)。"""
    name: str           # 规范名
    category: str       # "简易"/"进阶"/"特权"/"星徽"/"白昼"/"Fate"/"工具"
    effect: str         # 效果原文
    stacking: bool      # 效果可叠加(多件同戴 / 多层)"可叠加""叠加N层"→ True
    source: str = ""    # 米游社 content_id


def _eq(name: str, category: str, effect: str, stacking: bool, source: str = "") -> Equipment:
    return Equipment(name=name, category=category, effect=effect, stacking=stacking, source=source)


# ===== EQUIPMENTS 注册表(策略相关 key 装备;🟢 米游社原文,全量在 equipment.md)=====
EQUIPMENTS: dict[str, Equipment] = {e.name: e for e in [
    # —— 进阶装备(COMP_LIBRARY key_equips + meta 核心)——
    _eq("冷笑话引擎", "进阶", "终结技时幸运一击率+10%,最多叠加4层", True, "6152"),
    _eq("火力风暴潮", "进阶", "每次攻击后前/后台强度+8%,可叠加", True, "6164"),
    _eq("高周波电锯", "进阶", "战斗开始时前台幸运一击伤害+10%", False, "6175"),
    _eq("掩体生成枪", "进阶", "回合开始为我方全体前台提供30%生命上限护盾,2回合", False, "6156"),
    _eq("反重力皮靴", "进阶", "每回合开始速度增幅+15%,可叠加(鞋修流核心,阿雅/桑博/那刻夏需×2)", True, "6145"),
    _eq("光速螺旋桨", "进阶", "每10点速度→2%前台强度+1%后台强度(鞋修流核心,3昼之半神获得)", False, "6177"),
    _eq("物质分解液", "进阶", "每回合首次攻击后对随机目标造3%最大生命真伤", False, "6150"),
    _eq("以牙还牙甲", "进阶", "战斗开始前台获300%防御护盾;受击后对攻击者造250%护盾量物理反伤(反甲流,需×3)", False, "6170"),
    _eq("热血沸腾拳", "进阶", "生命上限>5000后每1000血+2%幸运一击率,最多40%(万敌核心)", False, "6171"),
    _eq("动能激发剑", "进阶", "回合开始恢1战技点,消耗后再获1,每回合最多3点(青雀无穷动)", False, "6159"),
    _eq("胜利之旗", "进阶", "全队幸运一击率+12%+抵抗4次控制,可叠加", True, "6169"),
    # —— 星徽(加入羁绊)——
    _eq("追击星徽", "星徽", "加入【追击】羁绊,所有伤害视为追击,行动后提前10%(青雀无穷动)", False, "7300"),
]}

EQUIPMENT_ROSTER: frozenset[str] = frozenset(EQUIPMENTS.keys())


def get_equip(name: str) -> Equipment | None:
    """按规范名取 Equipment;无则 None(全量未收的查 equipment.md)。"""
    return EQUIPMENTS.get(name)


def is_key_equip(name: str) -> bool:
    """是否为策略相关 key 装备(在 EQUIPMENTS 内)。"""
    return name in EQUIPMENTS
