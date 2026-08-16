"""牌池余量信念层 v0(16 号重设计提案;ADR-0157;2026-08-16)。

**诊断(16 号)**:机制确认牌库有限(1/2费 27 张、3/4/5费 9 张;买减卖回、NPC 也消耗),但
策略栈把它拆碎扔掉:`cw_shop_odds` 假设池永远「满池减自己持有」(`acquirability_factor` 实传
c=0 连这部分都没接线);drought 用「本回合 shop 有无阵营卡」二值信号(DROUGHT_BAIL 3→5 的
调参史 = 单观测回答分布问题的信噪比病)。同一份地基该喂四个决策族:D 成本/成型概率/搜牌
窗口/转型时机。

**v0(独立 Beta,提案 §2.1)**:每卡一个 Beta(α,β) 信念 on ρ_c = n_c/a_c(池内余量比例);
观测流 = 每次刷新的 5 格(见同名 → α+;见同费他名 → β+,即 rival 抽取的聚合证据)+ 自身
买/卖(确定移入移出)。冷启动 = 满池先验(行为=现状,无害启动)。**rival 建模按提案风险 1
「先定案后上」**:v0 的 β 增长即聚合 rival 抽压的唯象刻画,单/共享池定案(P0)后校准。

纯函数 + 离线可测;消费端切换(D 成本/drought/窗口)在切流 A/B 后逐个进行(灰度路径)。
"""
from __future__ import annotations

import math

from sr_od.application.currency_war.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    refresh_prob,
)

# 先验强度:κ 越小越接近满池(冷启动≈现状);κ 大 = 先验弱、观测主导。校准点。
PRIOR_KAPPA: float = 2.0
OBS_WEIGHT: float = 1.0


class CardBelief:
    """单卡池余量信念:Beta(α,β) on ρ = n/a;E[n] = a·mean;P(n≥k) 用正态近似(确定性)。"""

    __slots__ = ('name', 'cost', 'a', 'alpha', 'beta', 'removed')

    def __init__(self, name: str, cost: int):
        self.name = name
        self.cost = cost
        self.a = POOL_COPIES_PER_CARD.get(cost, 9)
        v = DISTINCT_CARDS_PER_COST.get(cost, 13)
        # 满池均匀先验:ρ 的均值 = 1/v(每张占同费池 1/v);κ 控先验强度
        self.alpha = max(0.5, self.a * (1.0 / v) * PRIOR_KAPPA)
        self.beta = max(0.5, self.a * (1.0 - 1.0 / v) * PRIOR_KAPPA)
        self.removed = 0   # 自身买入移出(确定);卖回 −

    # --- 观测 ---
    def observe_seen(self, w: float = OBS_WEIGHT) -> None:
        """刷新面见同名:池内确实还有(ρ 上行证据)。"""
        self.alpha += w

    def observe_other_same_cost(self, w: float = OBS_WEIGHT) -> None:
        """刷新面见同费他名:该费池在被抽(rival/自家买他卡)→ 本卡相对份额被挤压的弱证据。"""
        self.beta += w

    def record_self_buy(self) -> None:
        """自身买入:确定移出一张。"""
        self.removed += 1

    def record_self_sell(self) -> None:
        """卖回:确定移回一张。"""
        self.removed = max(0, self.removed - 1)

    # --- 后验 ---
    @property
    def mean_rho(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def e_remaining(self) -> float:
        """E[n] = (a − 自持移出) × ρ 后验均值(removed 是确定部分,先扣)。"""
        return max(0.0, (self.a - self.removed)) * self.mean_rho

    def p_at_least(self, k: int) -> float:
        """P(n ≥ k):正态近似(mean/var of Beta→n 尺度);确定性(无采样)。"""
        n_mean = self.e_remaining()
        var_rho = (self.alpha * self.beta) / ((self.alpha + self.beta) ** 2 * (self.alpha + self.beta + 1))
        n_sd = max(1e-6, (self.a - self.removed) * math.sqrt(var_rho))
        z = (k - 0.5 - n_mean) / n_sd   # 连续性校正
        return max(0.0, min(1.0, 0.5 * (1 - math.erf(z / math.sqrt(2.0)))))


class PoolBelief:
    """全池信念簿:每卡独立 CardBelief;刷面流喂 update,买卖喂确定性移入移出。"""

    def __init__(self):
        self.cards: dict[str, CardBelief] = {}

    def _card(self, name: str, cost: int) -> CardBelief:
        if name not in self.cards:
            self.cards[name] = CardBelief(name, cost)
        return self.cards[name]

    def observe_refresh(self, shop_slots: list, level: int) -> None:
        """一次刷新的 5 格(ShopCard 或 (name, cost) 对):同名→seen;同费他名→other。"""
        for c in shop_slots:
            name = getattr(c, 'name', None) or (c[0] if isinstance(c, tuple) else None)
            cost = getattr(c, 'cost', None) or (c[1] if isinstance(c, tuple) else 3)
            if not name:
                continue   # 漏读格:不更新(04 约定:未观测≠空格)
            self._card(name, cost)
        for c in shop_slots:
            name = getattr(c, 'name', None) or (c[0] if isinstance(c, tuple) else None)
            cost = getattr(c, 'cost', None) or (c[1] if isinstance(c, tuple) else 3)
            if not name:
                continue
            for other in shop_slots:
                oname = getattr(other, 'name', None) or (other[0] if isinstance(other, tuple) else None)
                ocost = getattr(other, 'cost', None) or (other[1] if isinstance(other, tuple) else 3)
                if oname and ocost == cost:
                    (self.cards[oname].observe_seen() if oname == name
                     else self.cards[oname].observe_other_same_cost(OBS_WEIGHT / 4.0))
        # 缺席证据(该费全部已知卡中未上镜的 → β):目标卡从不上镜本身是余量下行证据
        # (v0 无此更新则未见过的卡永远满池,枯池 D 成本测试失效)。权重 = 本刷新「应现未现」质量。
        from sr_od.application.currency_war.cw_chars import chars_by_cost
        seen_names = {getattr(c, 'name', None) or (c[0] if isinstance(c, tuple) else None)
                      for c in shop_slots}
        costs_seen = {getattr(c, 'cost', None) or (c[1] if isinstance(c, tuple) else 3)
                      for c in shop_slots
                      if (getattr(c, 'name', None) or (c[0] if isinstance(c, tuple) else None))}
        for d in costs_seen:
            p_slot = refresh_prob(level, d) / max(DISTINCT_CARDS_PER_COST.get(d, 13), 1)
            w_absence = max(0.0, 1.0 - (1.0 - min(p_slot, 0.5)) ** 5)
            for _ch in chars_by_cost(d):
                cname = _ch.name
                cb = self._card(cname, d)
                if cname not in seen_names:
                    cb.observe_other_same_cost(w_absence * 0.5)

    def record_buy(self, name: str, cost: int) -> None:
        self._card(name, cost).record_self_buy()

    def record_sell(self, name: str, cost: int) -> None:
        self._card(name, cost).record_self_sell()

    def e_remaining(self, name: str) -> float | None:
        b = self.cards.get(name)
        return b.e_remaining() if b else None

    def p_at_least(self, name: str, k: int) -> float | None:
        b = self.cards.get(name)
        return b.p_at_least(k) if b else None

    def acquirability_prior(self, name: str, cost: int) -> float:
        """余量比 E[n]/满池 → 消费端(如 acquirability_factor 的 c 通道/D 成本)的输入。"""
        b = self.cards.get(name)
        if b is None:
            return 1.0   # 无观测 = 满池先验(冷启动=现状)
        return max(0.0, min(1.0, b.e_remaining() / b.a))


def expected_refresh_cost(level: int, cost: int, belief: PoolBelief, name: str,
                          refresh_price: int = 2) -> float:
    """D 牌期望成本(消费端一,16 号 §2.3):满池超几何期望 × 余量比缩放 → 期望金曲线。

    v0 近似:E[refreshes] 满池值 × 1/max(ρ, floor)(余量枯 → 成本爬升);精确积分(三点
    分位离散)留校准后。floor 防除零(池真枯 → 成本→∞ 语义正确:该换目标了)。
    """
    p = refresh_prob(level, cost)
    v = DISTINCT_CARDS_PER_COST.get(cost, 13)
    if p <= 0:
        return float('inf')
    e_full = v / (5 * p)          # 满池:见一张指定牌的期望刷新数(几何近似)
    ratio = belief.acquirability_prior(name, cost)
    ratio = max(ratio, 0.05)
    return e_full * (1.0 / ratio) * refresh_price
