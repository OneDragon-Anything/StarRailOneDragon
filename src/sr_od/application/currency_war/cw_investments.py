"""货币战争 投资策略 + 投资环境领域模型(meta 层,V4.4)。

**来源**:米游社百科「货币战争图鉴」投资策略 `channel/map/209/212`(216)、投资环境 `/213`(74),
详 ``.debug/temp/currency_war/cw_data/investment_strategies.md`` / ``investment_envs.md``。

**用途**:
- ``InvestmentEnv``(概念股/邀请…):**带 faction 字段** —— 概念股/邀请对应哪个阵营是派生 ENV_FACTION_MAP
  的单一真相源(改注册表自动传导,取代 cw_comps 里硬编码的 ENV_FACTION_MAP)。
- ``InvestmentStrategy``(局内 3 选 1):event_whitelist 的规范名来源。

**为什么建模**(用户 2026-08-03):核心实体建正规 model 类 + 注册表(可查询/校验/派生),非散 dict。

⚠️ 本注册表先收**概念股 + 邀请**(select_comp env 契合用)+ T0 投资策略;全量(216 策略 / 74 环境)
在 cw_data docs,随事件/补给决策(阶段 3a)接线补全。版本依赖:赛季扩充会新增/调整。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InvestmentEnv:
    """投资环境(开局/固定节点整局增益)。"""
    name: str           # 规范名(如"昼之半神概念股")
    category: str       # "概念股"/"邀请"/"契约"/"时代"/"经济"/"规则"/"专家"
    effect: str         # 效果原文
    faction: str = ""   # 对应阵营(概念股/邀请 boosts 的羁绊;ENV_FACTION_MAP 派生用;无则 "")
    source: str = ""    # content_id


@dataclass(frozen=True)
class InvestmentStrategy:
    """投资策略(局内 3 选 1,可刷新)。"""
    name: str           # 规范名
    rarity: str         # "棱彩"/"金"/"银"
    effect: str
    source: str = ""


def _env(name: str, category: str, effect: str, faction: str = "", source: str = "") -> InvestmentEnv:
    return InvestmentEnv(name=name, category=category, effect=effect, faction=faction, source=source)


def _strat(name: str, rarity: str, effect: str, source: str = "") -> InvestmentStrategy:
    return InvestmentStrategy(name=name, rarity=rarity, effect=effect, source=source)


# ===== INVESTMENT_ENVS 注册表(概念股 + 邀请;🟢 米游社原文,带 faction)=====
# 概念股:开局送该阵营角色+装备+提高该阵营刷新率 → faction = 该阵营
# 邀请:获得该阵营星徽 → faction = 该阵营
INVESTMENT_ENVS: dict[str, InvestmentEnv] = {e.name: e for e in [
    # —— 概念股(开局送阵营角色+装备+刷新率)——
    _env("追击概念股", "概念股", "开局获得【追击】角色+简易装备,【追击】刷新率提高", "追击", "6107"),
    _env("击破概念股", "概念股", "开局获得【击破】角色+简易装备,【击破】刷新率提高", "击破", "6139"),
    _env("群攻概念股", "概念股", "开局获得【群攻】角色+简易装备,【群攻】刷新率提高", "群攻", "6138"),
    _env("能量概念股", "概念股", "开局获得【能量】角色+简易装备,【能量】刷新率提高", "能量", "6109"),
    _env("燃血概念股", "概念股", "开局获得【燃血】角色+简易装备,【燃血】刷新率提高", "燃血", "6108"),
    _env("减益概念股", "概念股", "开局获得【减益】角色+简易装备,【减益】刷新率提高", "减益", "6124"),
    _env("持续伤害概念股", "概念股", "开局获得【持续伤害】角色+简易装备,刷新率提高", "持续伤害"),
    _env("战技点概念股", "概念股", "开局获得【战技点】角色+简易装备,刷新率提高", "战技点"),
    _env("量子同频概念股", "概念股", "开局获得【量子同频】角色+简易装备,刷新率提高", "量子同频"),
    _env("仙舟概念股", "概念股", "开局获得【仙舟】角色+简易装备,【仙舟】刷新率提高", "仙舟", "6142"),
    _env("贝洛伯格概念股", "概念股", "开局获得【贝洛伯格】角色+简易装备,【贝洛伯格】刷新率提高", "贝洛伯格", "6144"),
    _env("狼狩概念股", "概念股", "开局获得【狼狩】角色+简易装备,【狼狩】刷新率提高", "狼狩", "6141"),
    _env("星间旅人概念股", "概念股", "开局获得【星间旅人】角色+简易装备,刷新率提高", "星间旅人", "6143"),
    _env("银河学者概念股", "概念股", "开局获得【银河学者】角色+简易装备,刷新率提高", "银河学者", "6111"),
    _env("列车同行概念股", "概念股", "开局获得【列车同行】角色+简易装备,刷新率提高", "列车同行", "6110"),
    _env("昼之半神概念股", "概念股", "开局获得【昼之半神】角色+简易装备,刷新率提高", "昼之半神", "6140"),
    _env("夜之半神概念股", "概念股", "开局获得【夜之半神】角色+简易装备,刷新率提高", "夜之半神", "6122"),
    # —— 邀请(获得该阵营星徽)——
    _env("仙舟邀请", "邀请", "获得一个【仙舟星徽】", "仙舟", "6128"),
    _env("贝洛伯格邀请", "邀请", "获得一个【贝洛伯格星徽】", "贝洛伯格", "6127"),
    _env("狼狩邀请", "邀请", "获得一个【狼狩星徽】", "狼狩", "6129"),
    _env("盛会之星邀请", "邀请", "获得一个【盛会之星星徽】", "盛会之星", "6130"),
    _env("星间旅人邀请", "邀请", "获得一个【星间旅人星徽】", "星间旅人", "6126"),
    _env("银河学者邀请", "邀请", "获得一个【银河学者星徽】", "银河学者", "6125"),
    _env("列车同行邀请", "邀请", "获得一个【列车同行星徽】", "列车同行", "6123"),
    _env("昼之半神邀请", "邀请", "获得一个【昼之半神星徽】", "昼之半神", "6131"),
    _env("夜之半神邀请", "邀请", "获得一个【夜之半神星徽】", "夜之半神", "6112"),
    _env("追击邀请", "邀请", "获得一个【追击星徽】", "追击", "6113"),
    _env("击破邀请", "邀请", "获得一个【击破星徽】", "击破", "6114"),
    _env("群攻邀请", "邀请", "获得一个【群攻星徽】", "群攻", "6115"),
    _env("能量邀请", "邀请", "获得一个【能量星徽】", "能量", "6116"),
    _env("燃血邀请", "邀请", "获得一个【燃血星徽】", "燃血", "6117"),
    _env("减益邀请", "邀请", "获得一个【减益星徽】", "减益", "6119"),
    _env("持续伤害邀请", "邀请", "获得一个【持续伤害星徽】", "持续伤害", "6118"),
    _env("量子同频邀请", "邀请", "获得一个【量子同频星徽】", "量子同频", "6120"),
    _env("战技点邀请", "邀请", "获得一个【战技点星徽】", "战技点", "6121"),
    _env("欢愉邀请", "邀请", "获得一个【欢愉星徽】", "欢愉", "7451"),
]}

# ===== INVESTMENT_STRATEGIES 注册表(T0 投资策略,event_whitelist 规范名来源;全量 216 在 doc)=====
INVESTMENT_STRATEGIES: dict[str, InvestmentStrategy] = {s.name: s for s in [
    _strat("高效决策", "棱彩", "商店刷新费用减半(D牌成本降,关键回合多刷)"),
    _strat("价值投资·彩", "棱彩", "存金生息增强(经济)"),
    _strat("采购专员·彩", "棱彩", "刷新返现(刷得越多返越多,D牌变便宜)"),
    _strat("返利+", "金", "刷新返利"),
    _strat("采购专员·金", "金", "刷新返现"),
    _strat("定期福利", "金", "定期金币"),
    _strat("定点爆破", "金", "爆发伤害"),
    _strat("加油站", "金", "刷新减费"),
    _strat("数值碾压", "金", "强度增益"),
    _strat("攻防一体", "金", "攻防增益"),
    _strat("羁绊的力量", "金", "羁绊增益"),
    _strat("基本保障", "金", "保底经济"),
    # 注:砂里淘金(电表倒转核心)是已知场景但难操作+耗时,非推荐 bot 玩法,不入白名单(economy_research §3)
]}


# ===== 派生:ENV_FACTION_MAP(投资环境 → 加成阵营;从 INVESTMENT_ENVS 派生,单一真相源)=====
def env_faction(env_name: str) -> str:
    """投资环境加成的阵营(概念股/邀请的 faction;无则 "")。"""
    e = INVESTMENT_ENVS.get(env_name)
    return e.faction if e is not None else ""


def envs_boosting_faction(faction: str) -> list[str]:
    """加成某阵营的全部投资环境名(概念股 + 邀请)。"""
    return [name for name, e in INVESTMENT_ENVS.items() if e.faction == faction]


def get_env(name: str) -> InvestmentEnv | None:
    """按规范名取 InvestmentEnv;无则 None。"""
    return INVESTMENT_ENVS.get(name)


def get_strategy(name: str) -> InvestmentStrategy | None:
    """按规范名取 InvestmentStrategy;无则 None(全量未收的查 investment_strategies.md)。"""
    return INVESTMENT_STRATEGIES.get(name)
