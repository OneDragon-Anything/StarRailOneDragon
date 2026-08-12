# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 D牌期望模型(A4 牌池概率;纯逻辑,可测,不碰游戏)。

**依据**(米游社 V4.4 权威计算,2026-08-03 采集):
- [article/77124902](https://www.miyoushe.com/sr/article/77124902) D牌期望表补充(计算方法)
- [article/77074467](https://www.miyoushe.com/sr/article/77074467) D牌期望表主文(30 场景表)

**模型**(详 ``docs/game/currency_war/data/economy_research.md``):
1. 每次刷新 5 格,每格独立以概率 p 出目标费用 → 出目标费用数 M ~ 二项 B(5, p)。
2. m 张目标费用里,出 x 张目标牌 = **超几何**(剩余目标副本 a−j / 剩余同费非目标副本 (v−1)a−c)。
3. 状态转移方程算**期望刷新次数** E_j(找 k 张目标牌,从手上有 j 张起)。

**池参数**:
- a = 每种牌副本数(1/2费=27 可升4星 / 3/4/5费=9 最高3星;均 3 倍数,3合1 决定;权威源 V3.7 必修二,
  5费=9 与 [NGA tid=45557485](https://bbs.nga.cn/read.php?tid=45557485) 实锤吻合;2026-08-12 用户确认)
- v = 同费用种类数(1费14/2费13/3费13/4费12/5费9,from characters.md)
- p(level, cost) = 刷新概率(Lv1-10 × 1-5费 权威表,2026-08-11 游戏内"商店刷新概率"实机 OCR,见 REFRESH_PROB;D-91)

供 ``cw_decisions._refresh_expected_delta`` 的 D牌蒙特卡洛用(替代 ``_sample_shop`` 粗近似):
当期望刷新次数 × 刷新成本 < 买到目标牌的收益时才值得 D。
"""
from __future__ import annotations

import math

from sr_od.application.currency_war.cw_chars import CHARACTERS, chars_by_cost

SHOP_SLOTS: int = 5  # 每次刷新 5 格(不考虑昔涟诗篇)

# a:每种牌的副本数 —— 1/2费=27(可升 4 星:27=3 个 3 星=9×3)、3/4/5费=9(最高 3 星)。均 3 的倍数(3合1 决定)。
# 权威源:V3.7 必修二。V4.2 银狼档「30/25/18/10/9」含非 3 倍数(25/10)→ 不可信弃用。
# (5费=9 NGA tid=45557485 实锤吻合;1/2费=27 由「可升 4 星」推出,2026-08-12 用户确认)
POOL_COPIES_PER_CARD: dict[int, int] = {1: 27, 2: 27, 3: 9, 4: 9, 5: 9}
# v:同费用的种类数 —— 从角色注册表派生(单一真相源;改 CHARACTERS 自动传导,非硬编码)
# 注:3费=13 与 D牌期望表(77124902)实测点吻合;其余费用随注册表,实机校准
DISTINCT_CARDS_PER_COST: dict[int, int] = {cost: len(chars_by_cost(cost)) for cost in range(1, 6)}

# 刷新概率 p[level][cost](V4.4 权威,2026-08-11 游戏内"商店刷新概率"表实机 OCR;D-91)
# 入口:备战-商店面板-点底部百分比条(y≈375)弹完整 Lv1-10 表。每行概率和=100%。
# 规律:随等级升,高费概率提升(低级 1 费主导 → 高级 4/5 费主导);1-3 级纯 1 费,4 级起混 2/3 费,7 级起出 5 费。
REFRESH_PROB: dict[int, dict[int, float]] = {
    1: {1: 1.0},
    2: {1: 1.0},
    3: {1: 1.0},
    4: {1: 0.65, 2: 0.25, 3: 0.10},
    5: {1: 0.45, 2: 0.33, 3: 0.20, 4: 0.02},
    6: {1: 0.30, 2: 0.40, 3: 0.25, 4: 0.05},
    7: {1: 0.19, 2: 0.30, 3: 0.40, 4: 0.10, 5: 0.01},
    8: {1: 0.18, 2: 0.25, 3: 0.32, 4: 0.22, 5: 0.03},
    9: {1: 0.15, 2: 0.20, 3: 0.25, 4: 0.30, 5: 0.10},
    10: {1: 0.05, 2: 0.10, 3: 0.20, 4: 0.40, 5: 0.25},
}


def refresh_prob(level: int, cost: int) -> float:
    """查询 p(level, cost);无数据返回 0(该等级不出该费用)。"""
    return REFRESH_PROB.get(level, {}).get(cost, 0.0)


def _refresh_dist(p: float, v: int, a: int, c: int, k_need: int, j: int) -> list[float]:
    """一次刷新得 x 张目标牌的概率分布(x=0..k_need);k_need=还需目标牌数。

    M~B(5,p) 出目标费用数;给定 m,出 x 张目标牌 = 超几何(剩余目标 a−j / 同费非目标 (v−1)a−c)。
    """
    rem_target = a - j                  # 牌库剩余目标牌(拥有 j 张已离池)
    rem_nontarget = (v - 1) * a - c     # 牌库剩余同费非目标牌(买走 c 张)
    total = rem_target + rem_nontarget  # 牌库剩余同费总牌 = va - j - c(拥有的 j 张已离开牌库)
    dist = [0.0] * (k_need + 1)         # dist[x], x=0..k_need
    if total <= 0:
        return dist
    for m in range(0, SHOP_SLOTS + 1):
        p_m = math.comb(SHOP_SLOTS, m) * (p ** m) * ((1.0 - p) ** (SHOP_SLOTS - m))
        if p_m <= 0:
            continue
        denom = math.comb(total, m)
        if denom == 0:
            continue
        for x in range(0, min(m, k_need) + 1):
            if x > rem_target or (m - x) > rem_nontarget:
                continue
            p_x = math.comb(rem_target, x) * math.comb(rem_nontarget, m - x) / denom
            dist[x] += p_m * p_x
    return dist


def expected_refreshes(p: float, v: int, a: int, c: int, k: int, j: int = 0) -> float:
    """找 k 张目标牌(2星 k=3、3星 k=9)的**期望刷新次数**(从手上有 j 张起)。

    状态转移:E_j = (1 + Σ_{x≥1} P_j(x)·E_{j+x}) / (1 − P_j(0)),边界 E_k=0,从 k−1 倒推到 j。
    :param p: 目标费用刷新概率
    :param v: 同费用种类数
    :param a: 每种牌副本数
    :param c: 同费非目标牌已被拿走数(牌池操纵:买同费非目标 → c↑ → 目标相对更密 → 期望↓)
    :param k: 想要的目标牌总数(2星=3、3星=9)
    :param j: 手上已有的目标牌数
    :return: 期望刷新次数;p≤0 或 j≥k → 0;P_j(0)≈1(几乎刷不到)→ inf
    """
    if p <= 0 or k <= 0:
        return 0.0
    if j >= k:
        return 0.0
    # 倒推动态规划:E[j..k],E[k]=0
    E = [0.0] * (k + 1)
    for j_cur in range(k - 1, j - 1, -1):
        k_need = k - j_cur
        dist = _refresh_dist(p, v, a, c, k_need, j_cur)
        p0 = dist[0]
        denom = 1.0 - p0
        if denom < 1e-12:
            E[j_cur] = float("inf")
            continue
        numer = 1.0
        for x in range(1, len(dist)):
            nxt = j_cur + x
            if nxt <= k:
                numer += dist[x] * E[nxt]
        E[j_cur] = numer / denom
    return E[j]


def expected_refreshes_for_card(level: int, cost: int, target_star: int,
                                 owned: int = 0, non_target_taken: int = 0) -> float:
    """便捷查询:在 level 级 D 一个 cost 费角色到 target_star 星(2/3)的期望刷新次数。

    :param owned: 已有该角色张数(j)
    :param non_target_taken: 已买走的同费非目标牌数(c;牌池操纵)
    """
    p = refresh_prob(level, cost)
    v = DISTINCT_CARDS_PER_COST.get(cost, 13)
    a = POOL_COPIES_PER_CARD.get(cost, 9)
    # target_star 对需 k 张:2星=3、3星=9(货币战争 3 合 1)
    k = {2: 3, 3: 9}.get(target_star, 3)
    return expected_refreshes(p, v, a, non_target_taken, k, owned)


def acquirability_factor(core_chars: list[str], level: int,
                         held: dict[str, int] | None = None) -> float:
    """comp 核心角色的**牌池感知**可得性 [0,1](select_comp 用;ADR-0110 牌池模型,补 ADR-0092 理论法)。

    P(单次刷新 5 格中至少出 1 张该角色)= 1 - P(0 张),用 ``_refresh_dist`` 精确超几何算:
    - P(出该费用)= refresh_prob(level, cost);M~B(5, p) 出该费用格数;
    - 给定 m 格该费用,出该角色 = 超几何(剩余该角色副本 a−j / 同费剩余总副本 v·a−j);
    - **j = 玩家已持有该角色的基础副本数**(1星1/2星3/3星9/4星27,3合1 折算)→ 持有越多,剩余越少,越难再刷
      (牌库有限:买掉即减,用户根因;ADR-0109 副本数 27/9)。忽略 NPC 消耗(未知,保守:只扣自己持有的)。
    comp 取核心角色里**最低**(阵容受最稀卡限制)。

    :param held: {char_name: 已持基础副本数 j},默认 None=全 0(早期未持,纯满池理论)。
    :return: [0,1];p=0(该等级不出该费)→ 0;无识别角色 → 1.0(中性不降权)。

    select_comp 用法:s *= (0.5 + 0.5 * acq)(ADR-0105:acq 作次级 tiebreak,非主导;牌池感知后范围收窄
    至 ~0.005-0.3 → 乘子 0.50-0.65,仍提供「低费核心早期更易刷」的 tiebreak 区分)。
    理论依据(ADR-0092):刷新概率独立 → 观察(shop 本回合/历史)无预测力,用理论 REFRESH_PROB + 牌池模型。
    """
    held = held or {}
    probs: list[float] = []
    for name in core_chars:
        c = CHARACTERS.get(name)
        if not c:
            continue
        p_cost = refresh_prob(level, c.cost)
        if p_cost <= 0:
            probs.append(0.0)          # 该等级不出该费用 → 0(刷不出)
            continue
        a = POOL_COPIES_PER_CARD.get(c.cost, 9)
        v = DISTINCT_CARDS_PER_COST.get(c.cost, 13)
        j = held.get(name, 0)
        # P(0 张该角色)经超几何(j 张已离池 → rem_target=a-j);1-P(0)=P(≥1)
        dist0 = _refresh_dist(p_cost, v, a, c=0, k_need=1, j=j)[0]
        probs.append(1.0 - dist0)
    if not probs:
        return 1.0
    return min(probs)
