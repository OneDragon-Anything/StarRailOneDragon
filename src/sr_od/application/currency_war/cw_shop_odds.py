"""货币战争 D牌期望模型(A4 牌池概率;纯逻辑,可测,不碰游戏)。

**依据**(米游社 V4.4 权威计算,2026-08-03 采集):
- [article/77124902](https://www.miyoushe.com/sr/article/77124902) D牌期望表补充(计算方法)
- [article/77074467](https://www.miyoushe.com/sr/article/77074467) D牌期望表主文(30 场景表)

**模型**(详 ``.debug/temp/currency_war/cw_data/economy_research.md``):
1. 每次刷新 5 格,每格独立以概率 p 出目标费用 → 出目标费用数 M ~ 二项 B(5, p)。
2. m 张目标费用里,出 x 张目标牌 = **超几何**(剩余目标副本 a−j / 剩余同费非目标副本 (v−1)a−c)。
3. 状态转移方程算**期望刷新次数** E_j(找 k 张目标牌,从手上有 j 张起)。

**V4.4 池参数**(实测,推翻旧"统一9张"推测):
- a = 18 张/种(3费实测;1/2/4/5费待核,placeholder 同 18)
- v = 同费用种类数(1费14/2费13/3费13/4费12/5费9,from characters.md)
- p(level, cost) = 刷新概率(7级3费=0.4 实测;其余 placeholder 待折叠栏/实机核)

供 ``cw_decisions._refresh_expected_delta`` 的 D牌蒙特卡洛用(替代 ``_sample_shop`` 粗近似):
当期望刷新次数 × 刷新成本 < 买到目标牌的收益时才值得 D。
"""
from __future__ import annotations

import math

SHOP_SLOTS: int = 5  # 每次刷新 5 格(不考虑昔涟诗篇)

# a:每种牌的副本数(V4.4 3费实测=18;1/2/4/5费待核,placeholder=18)
POOL_COPIES_PER_CARD: dict[int, int] = {1: 18, 2: 18, 3: 18, 4: 18, 5: 18}
# v:同费用的种类数(from cw_data/characters.md V4.4=74 种分布)
DISTINCT_CARDS_PER_COST: dict[int, int] = {1: 14, 2: 13, 3: 13, 4: 12, 5: 9}

# 刷新概率 p[level][cost](V4.4;7级3费=0.4 实测点,其余 placeholder 待 77074467 折叠栏/实机核)
# 粗规律:随等级升,高费概率提升(低级低费主导、高级高费主导)。
REFRESH_PROB: dict[int, dict[int, float]] = {
    4: {1: 1.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0},
    5: {1: 0.85, 2: 0.15, 3: 0.0, 4: 0.0, 5: 0.0},
    6: {1: 0.65, 2: 0.30, 3: 0.05, 4: 0.0, 5: 0.0},
    7: {1: 0.45, 2: 0.35, 3: 0.40, 4: 0.0, 5: 0.0},   # 7级3费=0.4 实测(注:原表概率和可能>1,待核归一)
    8: {1: 0.25, 2: 0.30, 3: 0.45, 4: 0.15, 5: 0.0},
    9: {1: 0.15, 2: 0.20, 3: 0.30, 4: 0.40, 5: 0.15},
    10: {1: 0.10, 2: 0.15, 3: 0.20, 4: 0.35, 5: 0.45},
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
    a = POOL_COPIES_PER_CARD.get(cost, 18)
    # target_star 对需 k 张:2星=3、3星=9(货币战争 3 合 1)
    k = {2: 3, 3: 9}.get(target_star, 3)
    return expected_refreshes(p, v, a, non_target_taken, k, owned)
