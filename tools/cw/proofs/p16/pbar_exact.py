# P16 锚点重算:p̄(持续伤害, lv6) 三口径对拍(2026-09 P16 修复批)
#
# 背景:P16_VALIDATION.md 瑕疵 A —— 原实现/证明把 Σ_cost P(≥1|cost) 当精确式,
# 实为并集上界(同一次刷新可在多个费用档同时出目标件)。本脚本算三个口径:
#   (1) union   = Σ_cost Σ_m B(m;5,p_c)·[1−C(T−A,m)/C(T,m)]   —— 原口径(并集上界)
#   (2) iid     = 1−(1−q)^5, q=Σ_c p_c·n_c/v_c                  —— 逐格 iid 闭式
#   (3) exact   = 1 − Σ_{m} Mult(m;p)·Π_c C(T_c−A_c,m_c)/C(T_c,m_c)
#                 —— 游戏模型(费用多项分配 + 同档不放回)下的精确值
# 用法:uv run python tools/cw/proofs/p16/pbar_exact.py [tag] [level]
from __future__ import annotations

import itertools
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'src'))

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    REFRESH_PROB,
    SHOP_SLOTS,
)


def char_has_tag(ch, tag: str) -> bool:
    return tag in (getattr(ch, 'factions', None) or ()) \
        or tag in (getattr(ch, 'flows', None) or ())


def tier_stats(tag: str) -> dict[int, tuple[int, int]]:
    """{cost: (目标张数 A, 池总张数 T)}。"""
    out: dict[int, tuple[int, int]] = {}
    for cost in sorted({ch.cost for ch in CHARACTERS.values()
                        if char_has_tag(ch, tag)}):
        a = POOL_COPIES_PER_CARD[cost]
        v = DISTINCT_CARDS_PER_COST[cost]
        n = len([ch for ch in CHARACTERS.values()
                 if ch.cost == cost and char_has_tag(ch, tag)])
        if n:
            out[cost] = (n * a, v * a)
    return out


def union_bound(tag: str, level: int) -> float:
    """口径(1):Σ_cost P(≥1|cost) —— cw_line_switch.p_bar_faction 原口径(并集上界)。"""
    s = 0.0
    for cost, (a_tgt, total) in tier_stats(tag).items():
        p_cost = REFRESH_PROB.get(level, {}).get(cost, 0.0)
        if p_cost <= 0:
            continue
        for m in range(1, SHOP_SLOTS + 1):
            p_m = math.comb(SHOP_SLOTS, m) * p_cost ** m * (1 - p_cost) ** (SHOP_SLOTS - m)
            p_none = (math.comb(total - a_tgt, m) / math.comb(total, m)
                      if total - a_tgt >= m else 0.0)
            s += p_m * (1 - p_none)
    return min(1.0, s)


def iid_closed(tag: str, level: int) -> float:
    """口径(2):逐格 iid 闭式 1−(1−q)^5, q=Σ_c p_c·n_c/v_c(单格命中概率)。"""
    q = 0.0
    for cost, (a_tgt, _total) in tier_stats(tag).items():
        p_cost = REFRESH_PROB.get(level, {}).get(cost, 0.0)
        v = DISTINCT_CARDS_PER_COST[cost]
        n = a_tgt // POOL_COPIES_PER_CARD[cost]
        q += p_cost * n / v
    return 1.0 - (1.0 - q) ** SHOP_SLOTS


def exact_multinom(tag: str, level: int) -> float:
    """口径(3):精确值 —— 费用档按多项分配 5 格,同档内不放回超几何。

    P(全空) = Σ_{m_c} [5!/Πm_c!·Πp_c^{m_c}] · Π_c C(T_c−A_c, m_c)/C(T_c, m_c)
    对全部成本构成(含出现的档)枚举 m_c≥0、Σm_c=5。
    """
    # 多项分配覆盖该等级全部费用档(REFRESH_PROB 行和=1);无目标件的档 A=0 → 全空概率=1
    tiers = sorted(REFRESH_PROB.get(level, {}).items())
    tiers = [(c, p) for c, p in tiers if p > 0]
    stats = tier_stats(tag)
    n = len(tiers)
    total_none = 0.0
    for m_vec in itertools.product(range(SHOP_SLOTS + 1), repeat=n):
        if sum(m_vec) != SHOP_SLOTS:
            continue
        # 多项概率:5!/Π m! · Π p^m —— 但档未覆盖的剩余格(Σm<5)概率 0,已排除
        logp = math.lgamma(SHOP_SLOTS + 1) - sum(math.lgamma(m + 1) for m in m_vec)
        for (_cost, p), m in zip(tiers, m_vec, strict=True):
            logp += m * math.log(p)
        none_prod = 1.0
        for (cost, _p), m in zip(tiers, m_vec, strict=True):
            if m == 0 or cost not in stats:
                continue  # 无目标件的档:超几何全空概率恒 1,不乘
            a_tgt, tot = stats[cost]
            none_prod *= (math.comb(tot - a_tgt, m) / math.comb(tot, m)
                          if tot - a_tgt >= m else 0.0)
        total_none += math.exp(logp) * none_prod
    return 1.0 - total_none


def monte_carlo_simple(tag: str, level: int, n_sim: int = 500_000, seed: int = 20260901) -> float:
    """独立复核(第三法):直接模拟「5 格各按 p_cost 选档、档内不放回抽卡」。

    与口径(3)的解析式不共享代码路径,交叉验证枚举实现。
    """
    rng = random.Random(seed)
    stats = tier_stats(tag)
    costs = sorted(REFRESH_PROB.get(level, {}))
    probs = [REFRESH_PROB[level][c] for c in costs]
    base_pools = {c: ([1] * a) + ([0] * (t - a)) for c, (a, t) in stats.items()}
    hits = 0
    for _ in range(n_sim):
        pool = {c: list(p) for c, p in base_pools.items()}
        for _slot in range(SHOP_SLOTS):
            c = rng.choices(costs, weights=probs)[0]
            lst = pool.get(c)
            if not lst:
                continue
            if lst.pop(rng.randrange(len(lst))) == 1:
                hits += 1
                break
    return hits / n_sim


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else '持续伤害'
    level = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    print(f'tag={tag!r} level={level}')
    print('  tier stats (cost: A目标张/T池张): '
          + ', '.join(f'{c}:{a}/{t}' for c, (a, t) in sorted(tier_stats(tag).items())))
    u = union_bound(tag, level)
    i = iid_closed(tag, level)
    e = exact_multinom(tag, level)
    print(f'  (1) 并集上界 Σ_c P(≥1|c)      = {u:.6f}  (原锚点口径)')
    print(f'  (2) 逐格 iid 闭式 1−(1−q)^5   = {i:.6f}')
    print(f'  (3) 多项×超几何精确值          = {e:.6f}')
    mc = monte_carlo_simple(tag, level)
    print(f'  (4) 蒙特卡洛 50 万次           = {mc:.6f}  (独立复核)')
    print(f'  上界相对精确值高估: {(u / e - 1) * 100:.2f}%')


if __name__ == '__main__':
    main()
