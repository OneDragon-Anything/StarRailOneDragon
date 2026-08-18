"""既持效果台账 v0(redesign 53 号;ADR-0202):现金日程+机制突变+免费额度。

**诊断(53 号)**:持有效果的确定性现金流被摊平成等效息——时机信息在表示层就被扔掉;
DP effect-blind(买断制照样攒息/连胜 ×3 照 ×1 算);效果表无验证通道。

**v0 落地**(纯函数,离线;53 号 §2.1/§2.2 核心):
- ``EffectLedger`` 三层:calendar(节点索引确定收入日程)/mutations(对 23 号常量的
  局内覆写:息 cap/单击 XP Δ/胜金乘子)/budgets(免费刷额度);
- ``build_ledger``:aggregate 语义效果(注入式,测试 mock)→ 三类结构归一化;
- 注入式消费接口:``node_income_with`` / ``interest_with`` / ``level_cost_with``
  (DP 参数化接缝;商业间谍/长期主义/买断制三算例的涌现方向由测试验证);
- 四象限分类路由(确定性收入→calendar/费率覆写→mutations/统计性→分布参数/
  行为义务→33 号合同台)。

DP 网格约束 D1(金步长 1 或累计跨步入账)挂 DP 改造批次;验证层(守恒对账)挂
telemetry 批次。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AggregateEffect:
    """一条聚合后的持有效果(注入式;生产接 aggregate_economy)。"""

    name: str
    kind: str                      # 'per_node' | 'next_nodes' | 'boss_node' | 'level_up'
                                   # | 'interest_cap' | 'xp_click_delta' | 'win_mult' | 'free_refresh'
                                   # | 'free_refresh_burst' | 'surprise_every' | 'gold_per_three_5cost'
                                   # | 'xp_per_refresh' | 'xp_per_node' | 'plane_start_gold'
                                   # | 'refresh_discount_after'
    value: float = 0.0
    remaining_nodes: int = 0       # next_nodes 类的余期;plane_start_gold 类的位面号


@dataclass
class MechanismMutation:
    """对 23 号注册表常量的局内覆写(突变视图)。"""

    interest_cap: int | None = None     # 绝对覆写(买断制 0/利息上调 10)
    xp_click_delta: float = 0.0         # Δ(商业间谍 −1)
    win_reward_mult: float = 1.0        # 乘子(伟大征服 ×3)
    free_refresh_per_node: int = 0
    free_refresh_burst: int = 0
    # —— v1 扩展(2026-08-17 全量效果扫描:overlay 已有字段的路由补全)——
    refresh_surprise_every: int = 0     # 每 N 刷同费面(采购专员;38 号会话消费)
    gold_per_three_5cost: int = 0       # 每买 3 张 5 费给金(返利系)
    xp_per_refresh: float = 0.0         # 每刷 +经验(淘金客)
    xp_per_node: float = 0.0            # 每节点 +经验(买断制)
    refresh_price_after: int | None = None   # 长线利好:30 刷后刷新价 1(环境侧)
    refresh_discount_at: int = 0             # 解锁刷次线(与 38 号 DISCOUNT_AT_REFRESH 同源)


@dataclass
class EffectLedger:
    """持有效果台账(表示层;消费端按需读三类结构)。"""

    calendar: dict[int, float] = field(default_factory=dict)   # 节点偏移 → 确定收入
    mutations: MechanismMutation = field(default_factory=MechanismMutation)

    def calendar_at(self, t: int) -> float:
        return self.calendar.get(t, 0.0)


def build_ledger(effects: list[AggregateEffect]) -> EffectLedger:
    """聚合效果 → 三类结构(四象限路由)。"""
    led = EffectLedger()
    m = led.mutations
    for e in effects:
        if e.kind == 'per_node':
            # 每节点确定收入:全节点日程(剩余期未知时按全程;精确余期由 state 注入)
            for t in range(27):
                led.calendar[t] = led.calendar.get(t, 0.0) + e.value
        elif e.kind == 'next_nodes':
            for t in range(max(1, e.remaining_nodes)):
                led.calendar[t] = led.calendar.get(t, 0.0) + e.value
        elif e.kind == 'boss_node':
            for t in (8, 17, 26):    # boss 位粗锚(节点序列标注挂批次)
                led.calendar[t] = led.calendar.get(t, 0.0) + e.value
        elif e.kind == 'level_up':
            led.calendar[-1] = led.calendar.get(-1, 0.0) + e.value   # 等级计划联解挂 DP 批次
        elif e.kind == 'interest_cap':
            m.interest_cap = int(e.value)
        elif e.kind == 'xp_click_delta':
            m.xp_click_delta += e.value
        elif e.kind == 'win_mult':
            m.win_reward_mult *= e.value
        elif e.kind == 'free_refresh':
            m.free_refresh_per_node += int(e.value)
        elif e.kind == 'free_refresh_burst':
            m.free_refresh_burst += int(e.value)
        elif e.kind == 'surprise_every':
            # 多个稳定器共存取更密者(每 5 与每 7 → 每 5)
            cur = m.refresh_surprise_every
            m.refresh_surprise_every = int(e.value) if cur == 0 else min(cur, int(e.value))
        elif e.kind == 'gold_per_three_5cost':
            m.gold_per_three_5cost += int(e.value)
        elif e.kind == 'xp_per_refresh':
            m.xp_per_refresh += e.value
        elif e.kind == 'xp_per_node':
            m.xp_per_node += e.value
        elif e.kind == 'plane_start_gold':
            # 环境侧:增发货币(位面开始 6/8/12 金)→ 位面首节点日程
            plane = int(e.remaining_nodes) if e.remaining_nodes else 1
            t = (min(plane, 3) - 1) * 9
            led.calendar[t] = led.calendar.get(t, 0.0) + e.value
        elif e.kind == 'refresh_discount_after':
            # 环境侧:长线利好(30 刷后刷新价 1)——与 38 号会话的跨线投资联动
            m.refresh_discount_at = int(e.value)
            m.refresh_price_after = 1
    return led


# ===== 环境侧效果扩展(ADR-0144 挂账缺口;效果原文 = cw_invest_data 83 条) =====
# v1 先落「可数值化且机制明确」的环境经济效果(官方原文照录注释;其余战力/规则类走原通道)。
ENV_ECONOMY_EFFECTS: tuple[AggregateEffect, ...] = (
    AggregateEffect('增发货币', 'plane_start_gold', 6.0, remaining_nodes=1),
    # ↑ 官方:第一/二/三位面开始时获得 6/8/12 金晶矿(v1 取下界 6 全位面;分位面精确值挂批次)
    AggregateEffect('蓝海', 'per_node', 0.0),
    # ↑ 官方:开局额外 6 金 + 进入随机环境(金部分=一次性,instant 语义不进台账日程)
    AggregateEffect('长线利好', 'refresh_discount_after', 30.0),
    # ↑ 官方:30 次刷新后获 20 金 + 之后刷新 1 金(20 金返手挂 38 号跨线;价降进 mutations)
)


def build_env_ledger(env_names: list[str]) -> EffectLedger:
    """环境名列表 → 台账(ENV_ECONOMY_EFFECTS 子集;未覆盖环境=空台账=现状)。"""
    return build_ledger([e for e in ENV_ECONOMY_EFFECTS if e.name in env_names])


# ===== 注入式消费接口(DP 参数化接缝;53 号 §2.2) =====

def node_income_with(t: int, base_income: float, streak_gold: float,
                     ledger: EffectLedger) -> float:
    """node_income(t, ledger) = base + streak×win_mult + calendar[t]。"""
    return (base_income + streak_gold * ledger.mutations.win_reward_mult
            + ledger.calendar_at(t))


def interest_with(gold: int, ledger: EffectLedger, default_cap: int = 5) -> int:
    """interest(gold, ledger) = min(gold//10, mutations.interest_cap)。"""
    cap = ledger.mutations.interest_cap if ledger.mutations.interest_cap is not None else default_cap
    return min(gold // 10, cap)


def level_cost_with(clicks: int, ledger: EffectLedger, base_click_cost: float = 4.0) -> float:
    """level_cost = clicks × max(0, base + xp_delta)。"""
    return clicks * max(0.0, base_click_cost + ledger.mutations.xp_click_delta)


# ===== v2:ADR-0205 调研新字段 → 台账路由(API 文本明说的数值) =====

def effects_from_strategies(strategy_names: list[str]) -> list[AggregateEffect]:
    """注册表 EconomyEffect → AggregateEffect 路由(生产接法:state.active_strategies)。

    只路由**台账可表达**的字段;行为条件流(存款回报/招财狗/星星相印)、期权类
    (期货系,33 号合同台)、难度类(36 号账本)各自归位,不进本台账。
    """
    from sr_od.application.currency_war.cw_investments import get_strategy
    out: list[AggregateEffect] = []
    for name in strategy_names:
        s = get_strategy(name)
        if s is None or s.economy is None:
            continue
        e = s.economy
        if e.interest_cap_override is not None:
            out.append(AggregateEffect(name, 'interest_cap', float(e.interest_cap_override)))
        if e.xp_buy_cost_discount:
            out.append(AggregateEffect(name, 'xp_click_delta', -float(e.xp_buy_cost_discount)))
        if e.win_reward_mult != 1.0:
            out.append(AggregateEffect(name, 'win_mult', float(e.win_reward_mult)))
        if e.gold_per_node:
            out.append(AggregateEffect(name, 'per_node', float(e.gold_per_node)))
        if e.gold_next_nodes_amount:
            out.append(AggregateEffect(name, 'next_nodes', float(e.gold_next_nodes_amount),
                                       remaining_nodes=e.gold_next_nodes_count))
        if e.gold_per_boss_node:
            out.append(AggregateEffect(name, 'boss_node', float(e.gold_per_boss_node)))
        if e.free_refresh_per_node:
            out.append(AggregateEffect(name, 'free_refresh', float(e.free_refresh_per_node)))
        if e.free_refresh_burst:
            out.append(AggregateEffect(name, 'free_refresh_burst', float(e.free_refresh_burst)))
        if e.refresh_surprise_every:
            out.append(AggregateEffect(name, 'surprise_every', float(e.refresh_surprise_every)))
        if e.xp_per_refresh:
            out.append(AggregateEffect(name, 'xp_per_refresh', float(e.xp_per_refresh)))
        if e.xp_per_node:
            out.append(AggregateEffect(name, 'xp_per_node', float(e.xp_per_node)))
        # v2 新字段
        if e.interest_flat_per_node:
            # 固定息:每节点平金流,与 cap 息并行
            out.append(AggregateEffect(name, 'per_node', float(e.interest_flat_per_node)))
        if e.gold_at_node:
            out.append(AggregateEffect(name, 'next_nodes', float(e.gold_at_node),
                                       remaining_nodes=e.gold_at_node_offset))
            # ↑ 时点大额用 next_nodes 语义(t+offset 一次性);超发货币的负债部分
            # 由调用方补 AggregateEffect('超发货币:负债', 'next_nodes', -gold_held, offset)
    return out


def conditional_effects_at(state) -> list[AggregateEffect]:
    """等级条件突变(成长的快乐:8 级起单击 −1)——按当前等级激活。

    调用时机:等级变化或建 session 时。DP 消费:mutations.xp_click_delta 注入。
    """
    from sr_od.application.currency_war.cw_investments import get_strategy
    out: list[AggregateEffect] = []
    level = getattr(state, 'level', 0) or 0
    for name in getattr(state, 'active_strategies', None) or []:
        s = get_strategy(name)
        if s is None or s.economy is None:
            continue
        e = s.economy
        if e.xp_click_discount_from_level and level >= e.xp_click_discount_from_level_at:
            out.append(AggregateEffect(name, 'xp_click_delta',
                                       -float(e.xp_click_discount_from_level)))
    return out


def gold_at_level_effect(target_level: int,
                         strategy_names: list[str]) -> list[AggregateEffect]:
    """成长基金:到达 9 级给 40 金——等级触发日程(DP 等级路径联解时注入:
    预计到达 9 级的节点偏移处一次性 +40;节点偏移由调用方按 level_plan 换算)。"""
    from sr_od.application.currency_war.cw_investments import get_strategy
    out: list[AggregateEffect] = []
    for name in strategy_names:
        s = get_strategy(name)
        if (s is not None and s.economy is not None
                and s.economy.gold_at_level
                and s.economy.gold_at_level_target == target_level):
            out.append(AggregateEffect(name, 'next_nodes', float(s.economy.gold_at_level),
                                       remaining_nodes=1))
    return out
