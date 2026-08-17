"""离线校准环境 v0(02 号提案主张三的 salvage;ADR-0168;2026-08-16)。

**处置背景**:02 号主张一(统计 outcome model)被 19 号伤害账本取代(ADR-0166 不等式括号
法,十几战定参 vs ~540 样本);主张二(ΔE[生存] 计价)被 18 号首达泛函修正(ADR-0161:分位
族只是数据输入,消费泛函应是路径首达概率);**主张三(校准环境)未被取代且是多层的共同
依赖**——ADR-0155 的 V3(DP 切流离线 A/B)/ADR-0166 的 L2-L3/ADR-0167 的 K2 都等它。

**零件已齐**(02 号当年缺的现在全有):
- 经济/商店/升星规则引擎:``cw_state.simulate`` + ``cw_shop_odds.REFRESH_PROB`` + ``cw_economy``;
- 战斗 stub:``cw_horizon`` 掉血先验(板强→掉血,与 DP 同源 → A/B 结果对 DP 公平)+ 随机项;
- 收入:``cw_horizon.node_income``(连胜-板强耦合)。

**v0 落地**:
- ``SimEnv``:GameState 驱动的对局模拟器(shop 采样/战斗结算/收入/升级),种子确定性
  (F-4);策略钩子(policy callable)可插——现状栈启发式 vs DP 姿态 vs 任意实验策略;
- ``run_batch(policy, n)``:批量跑局 → 结果指标(存活率/到达位面/终局金/等级);
- 默认策略 ``baseline_policy``:近似现状栈(攒息→买 target 牌→deploy→按金升级)。

诚实边界:v0 战斗 = 掉血先验 × 噪声(非 ledger 实测;ledger 有数据后替换 stub 即升级);
装备/事件/遭遇不建模(策略侧影响二阶)。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_chars import chars_by_cost
from sr_od.application.currency_war.cw_horizon import (
    NODES_PER_PLANE,
    _hp_loss,
    b_eff,
    interest,
    level_cost,
    node_income,
)
from sr_od.application.currency_war.cw_shop_odds import REFRESH_PROB
from sr_od.application.currency_war.cw_state import (
    BuyCard,
    DeployMove,
    GameState,
    LevelUp,
    RefreshShop,
    ShopCard,
    simulate,
)


def _sample_shop(level: int, rng: random.Random) -> list[ShopCard]:
    """按 REFRESH_PROB 采 5 格(费用轮盘 + 同费均匀)。"""
    probs = REFRESH_PROB.get(level, {})
    out: list[ShopCard] = []
    for i in range(5):
        r, acc, pick = rng.random(), 0.0, None
        for c, p in probs.items():
            acc += p
            if r <= acc:
                pick = c
                break
        if pick is None:
            pick = next(iter(probs), 1)
        pool = chars_by_cost(pick)
        ch = rng.choice(pool) if pool else None
        # ''=已知无阵营(白厄类;sim 池来自注册表恒已知,与 shop/identity/shop_cards 同语义)
        out.append(ShopCard(x=i + 1, faction=(ch.factions[0] if ch and ch.factions else ''),
                            name=(ch.name if ch else ''), cost=pick))
    return out


@dataclass
class SimResult:
    survived: bool
    plane_reached: int
    round_reached: int
    hp_end: int
    gold_end: int
    level_end: int
    hp_trace: list[int] = field(default_factory=list)


class SimEnv:
    """对局模拟器 v0(种子确定;策略钩子可插)。"""

    def __init__(self, seed: int = 0, *, target_faction: str = '列车同行'):
        self.rng = random.Random(seed)
        self.target_faction = target_faction
        self.rb = 0.0   # 刷牌板强加成(与 cw_horizon 同语义)

    def run(self, policy) -> SimResult:
        st = GameState(gold=10, round_num=1, level=1, plane=1, hp=100,
                       shop=_sample_shop(1, self.rng), bench=[], deployed=[], board={})
        trace: list[int] = []
        t = 0
        while st.hp > 0 and st.plane <= 3:
            # 1) 备战:策略产动作序列 → simulate 应用
            for act in policy(st, self):
                st = simulate(st, act)
                if isinstance(act, RefreshShop):
                    st.shop = _sample_shop(st.level, self.rng)
                elif isinstance(act, BuyCard):
                    self.rb = min(1.0, self.rb + 0.12)
            # 2) 战斗结算(掉血先验 × 对数正态噪声;与 DP 同源 → 对 DP 公平)
            drop = _hp_loss(t, st.level, self.rb) * self.rng.lognormvariate(0, 0.35)
            st.hp = max(0, int(st.hp - drop))
            trace.append(st.hp)
            # 3) 收入(连胜-板强耦合)+ 位面推进
            income = node_income(t, b_eff(st.level, self.rb)) + interest(min(st.gold, 50))
            st.gold = min(110, st.gold + income)
            st.round_num += 1
            if st.round_num > NODES_PER_PLANE:
                st.round_num = 1
                st.plane += 1
            t += 1
            st.shop = _sample_shop(st.level, self.rng)
        return SimResult(survived=st.hp > 0,
                         plane_reached=st.plane if st.hp > 0 else st.plane,
                         round_reached=st.round_num, hp_end=st.hp,
                         gold_end=st.gold, level_end=st.level, hp_trace=trace)


def baseline_policy(st: GameState, env: SimEnv):
    """默认策略(近似现状栈骨架):金≥升级价+50 → 连点升级;买得起 target 牌 → 买+deploy;
    金≥20 → 刷一次找 target;否则存息。LevelUp = 单击(+XP_PER_BUY;ADR-0129 语义)。"""
    from sr_od.application.currency_war.cw_horizon import clicks_to_level
    acts = []
    if st.gold >= level_cost(st.level) + 50 and st.level < 10:
        return [LevelUp(cost=4) for _ in range(clicks_to_level(st.level))]
    for _i, c in enumerate(st.shop):
        if c.name and c.faction == env.target_faction and st.gold >= c.cost:
            acts.append(BuyCard(card=c))
            if len(st.bench) < 8:
                acts.append(DeployMove(bench_idx=len(st.bench), to_row='back',
                                       faction=c.faction))
            break
    if not acts and st.gold >= 20:
        acts.append(RefreshShop(cost=2))
    return acts


def run_batch(policy, n: int = 100, seed0: int = 0) -> dict:
    """批量对局 → 结果指标(胜率/位面到达/终局分布)。"""
    rs = [SimEnv(seed0 + i).run(policy) for i in range(n)]
    return {
        'n': n,
        'survival_rate': sum(r.survived for r in rs) / n,
        'mean_plane': sum(min(r.plane_reached, 3) for r in rs) / n,
        'p3_rate': sum(r.plane_reached >= 3 for r in rs) / n,
        'mean_gold_end': sum(r.gold_end for r in rs) / n,
        'mean_level_end': sum(r.level_end for r in rs) / n,
    }
