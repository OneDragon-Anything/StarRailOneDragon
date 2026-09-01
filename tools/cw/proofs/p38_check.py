# -*- coding: utf-8 -*-
"""P38 数值自检:K 缺口集齐概率 —— 精确 DP vs 独立乘积闭式近似的偏差对拍。

不进 src、不提交;重跑:PYTHONPATH=src uv run python tools/cw/proofs/p38_check.py
数据源:REFRESH_PROB / SHOP_SLOTS / POOL_COPIES_PER_CARD(cw_shop_odds,实机 OCR 权威表)。
"""
from __future__ import annotations

import math

from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    REFRESH_PROB,
    SHOP_SLOTS,
)


# ---------- 玩具用例定义 ----------
# item = (need, cost, set_size):需要 need 张,合格集 = 同费 set_size 种牌(各 a 副本)。
# 设计成跨费用带 + 混单卡需求(need>1)/集合需求(need=1, set_size>1)。
def case_p9_l9() -> list[tuple[int, int, int]]:
    # P3 场景:Lv9;item1=3费羁绊档+1人(set 3 种);item2=4费单卡 need2;set 与 item1 不同费不重叠
    return [(1, 3, 3), (2, 4, 1)]


def case_p2_l7() -> list[tuple[int, int, int]]:
    # P2 场景:Lv7;item1=3费核心 need3(set 1 种,2星);item2=2费羁绊档+1人(set 5 种)
    return [(3, 3, 1), (1, 2, 5)]


def case_dense() -> list[tuple[int, int, int]]:
    # 高密度压力:同费三件竞争(3费 set 各 2 种,need 各 1)——负关联最强的形态
    return [(1, 3, 2), (1, 3, 2), (1, 3, 2)]


# ---------- 精确模型:单店(5 槽)转移 ----------
def shop_transition(level: int, items: list[tuple[int, int, int]],
                    owned: tuple[int, ...]) -> dict[tuple[int, ...], float]:
    """一次刷新(5 槽)在 owned 状态下的增量分布。

    模型(与 cw_shop_odds._refresh_dist 同构,推广到多件):
    1) 槽位费用档计数 (m_1..m_5) ~ Multinomial(5, REFRESH_PROB[level]);
    2) 给定 m_c,该 m_c 张 = 从剩余同费池(分类:各 item 的合格副本 / 非目标)
       无放回抽 m_c 张(多元超几何);
    3) 增量按 need 封顶。池衰减只计自购目标牌(OPEN INPUT:NPC 消耗未知)。
    """
    needs = [it[0] for it in items]
    # 各费用档的池分类:cost -> (各 item 剩余目标副本, 非目标副本)
    cats: dict[int, tuple[list[int], int]] = {}
    for c in range(1, 6):
        target_counts = []
        nontarget = POOL_COPIES_PER_CARD[c] * _v(c)  # 先按满池
        for (need, cost, set_size), j in zip(items, owned):
            if cost != c:
                continue
            rem_t = set_size * POOL_COPIES_PER_CARD[c] - j
            target_counts.append(rem_t)
            nontarget -= set_size * POOL_COPIES_PER_CARD[c]
        cats[c] = (target_counts, nontarget)

    costs = [c for c in range(1, 6) if REFRESH_PROB[level].get(c, 0) > 0]
    probs = [REFRESH_PROB[level][c] for c in costs]

    out: dict[tuple[int, ...], float] = {}

    def enumerate_ms(idx: int, slots_left: int, coef: float, ms: list[int] | None = None):
        """枚举各费用档的槽数分配(multi-index),Σm 必须 = 5(行概率和=1,无剩余档)。"""
        if ms is None:
            ms = []
        if idx == len(costs):
            if slots_left == 0:
                yield (list(ms), coef)
            return
        p = probs[idx]
        for m in range(0, slots_left + 1):
            yield from enumerate_ms(idx + 1, slots_left - m, coef * (p ** m), ms + [m])

    def draw_cost(c: int, m: int) -> dict[tuple[int, ...], float]:
        """该费用档 m 槽 → 各 item 增量分布(多元超几何,增量封顶 need)。"""
        target_counts, nontarget = cats[c]
        local_items = [k for k, (need, cost, _) in enumerate(items) if cost == c]
        pool = sum(target_counts) + nontarget
        dist: dict[tuple[int, ...], float] = {}
        denom = math.comb(pool, m)

        def rec2(i: int, taken: int, w: float, incs: list[int]):
            if i == len(target_counts):
                rest = m - taken
                if rest > nontarget:
                    return
                w2 = w * math.comb(nontarget, rest)
                key = tuple(incs)
                dist[key] = dist.get(key, 0.0) + w2 / denom
                return
            k_global = local_items[i]
            need = needs[k_global]
            for x in range(0, min(target_counts[i], m - taken) + 1):
                # 增量封顶:抽到超过 need 的张数按 need 计(分布不截断,质量并入封顶档)
                rec2(i + 1, taken + x,
                     w * math.comb(target_counts[i], x), incs + [min(x, need)])

        if m == 0:
            return {tuple([0] * len(target_counts)): 1.0}
        rec2(0, 0, 1.0, [])
        return dist

    for ms, coef in enumerate_ms(0, SHOP_SLOTS, 1.0):
        ways = math.factorial(SHOP_SLOTS)
        for m in ms:
            ways //= math.factorial(m)
        joint = {(): 1.0}
        for c, m in zip(costs, ms):
            if m == 0:
                continue
            d = draw_cost(c, m)
            merged: dict[tuple[int, ...], float] = {}
            for prev, wp in joint.items():
                for inc, wi in d.items():
                    # prev 是已处理档的局部增量序列,需按全局 item 对齐
                    merged_key = _merge(prev, inc, costs, c, items)
                    merged[merged_key] = merged.get(merged_key, 0.0) + wp * wi
            joint = merged
            if not joint:
                break
        for inc_key, w in joint.items():
            full = tuple(inc_key) if len(inc_key) == len(items) else inc_key
            out[full] = out.get(full, 0.0) + ways * coef * w
    # 归一化校验
    tot = sum(out.values())
    assert abs(tot - 1.0) < 1e-9, f"transition not normalized: {tot}"
    return out


def _merge(prev: tuple[int, ...], inc: tuple[int, ...], costs, c, items) -> tuple[int, ...]:
    """把费用档 c 的局部增量序列并进全局增量向量。"""
    if not prev:
        prev = (0,) * len(items)
    res = list(prev)
    local_items = [k for k, (need, cost, _) in enumerate(items) if cost == c]
    for k_local, k_global in enumerate(local_items):
        res[k_global] += inc[k_local]
    return tuple(res)


def _v(c: int) -> int:
    """同费种类数(单一源=注册表派生,防硬编码漂移)。"""
    return DISTINCT_CARDS_PER_COST[c]


# ---------- 精确 DP:N 次刷新内全部集齐 ----------
def exact_dp(level: int, items: list[tuple[int, int, int]], n_shops: int) -> float:
    needs = [it[0] for it in items]
    caps = needs

    def flatten(state: tuple[int, ...]) -> int:
        idx = 0
        for s, cap in zip(state, caps):
            idx = idx * (cap + 1) + s
        return idx

    def unflatten(idx: int) -> tuple[int, ...]:
        st = []
        for cap in reversed(caps):
            st.append(idx % (cap + 1))
            idx //= (cap + 1)
        return tuple(reversed(st))

    S = 1
    for cap in caps:
        S *= (cap + 1)
    trans_cache: dict[tuple[int, ...], dict[tuple[int, ...], float]] = {}
    dist = [0.0] * S
    dist[flatten((0,) * len(items))] = 1.0
    for _ in range(n_shops):
        nd = [0.0] * S
        for s_idx, w in enumerate(dist):
            if w == 0.0:
                continue
            st = unflatten(s_idx)
            if st not in trans_cache:
                trans_cache[st] = shop_transition(level, items, st)
            for inc, p in trans_cache[st].items():
                nxt = tuple(min(a + b, cap) for a, b, cap in zip(st, inc, caps))
                nd[flatten(nxt)] += w * p
        dist = nd
    done_idx = flatten(tuple(caps))
    return dist[done_idx]


# ---------- 单件边际(精确,自衰减,共享 N)----------
def marginal(level: int, item: tuple[int, int, int], n_shops: int) -> float:
    return exact_dp(level, [item], n_shops)


# ---------- 闭式近似:初始 q 的 Poisson 尾 + 二项尾 ----------
def slot_q(level: int, item: tuple[int, int, int]) -> float:
    need, c, set_size = item
    a = POOL_COPIES_PER_CARD[c]
    p = REFRESH_PROB[level].get(c, 0.0)
    return p * (set_size * a) / (_v(c) * a)


def closed_form_poisson(level: int, items, n_shops: int) -> float:
    prod = 1.0
    for it in items:
        q = slot_q(level, it)
        lam = n_shops * SHOP_SLOTS * q
        need = it[0]
        # Poisson 尾 P(X>=need)
        tail = 1.0 - math.exp(-lam) * sum(lam ** i / math.factorial(i) for i in range(need))
        prod *= tail
    return prod


def closed_form_binomial(level: int, items, n_shops: int) -> float:
    prod = 1.0
    n = n_shops * SHOP_SLOTS
    for it in items:
        q = slot_q(level, it)
        need = it[0]
        tail = 1.0 - sum(math.comb(n, i) * q ** i * (1 - q) ** (n - i) for i in range(need))
        prod *= tail
    return prod


# ---------- 变等级日程用例(平均 q̄ 的二项近似误差,④层声明 ≤0.4pp 的断言锁) ----------
def variable_level_check() -> None:
    """④层声明「平均 q̄ 的 Binomial 近似误差二阶」的补验:变等级日程下
    Poisson-binomial(逐店精确卷积)vs Binomial(5N, q̄) 的尾概率偏差。"""
    def shop_pmf(q: float) -> list[float]:
        # 单店 5 槽命中数 ~ Binomial(5, q)(静态池,与闭式同口径)
        return [math.comb(5, k) * q ** k * (1 - q) ** (5 - k) for k in range(6)]

    def poisson_binomial_tail(schedule: list[float], need: int) -> float:
        dist = [1.0]
        for q in schedule:
            pmf = shop_pmf(q)
            nd = [0.0] * (len(dist) + 5)
            for i, w in enumerate(dist):
                if w == 0.0:
                    continue
                for k, p in enumerate(pmf):
                    nd[i + k] += w * p
            dist = nd
        return sum(dist[need:])

    def mean_binomial_tail(schedule: list[float], need: int) -> float:
        qbar = sum(schedule) / len(schedule)
        n = 5 * len(schedule)
        return 1.0 - sum(math.comb(n, i) * qbar ** i * (1 - qbar) ** (n - i) for i in range(need))

    scenarios = [
        ("5费单张 20xL7+5xL10", [(1, 5, 1)], [7.0] * 20 + [10.0] * 5),
        ("3费2星 12xL6+13xL7", [(3, 3, 1)], [6.0] * 12 + [7.0] * 13),
    ]
    print("\n=== 变等级日程:平均q二项近似 vs Poisson-binomial(逐店卷积) ===")
    for name, items, levels in scenarios:
        for need, cost, set_size in items:
            qs = [slot_q(int(lv), (need, cost, set_size)) for lv in levels]
            pb = poisson_binomial_tail(qs, need)
            mb = mean_binomial_tail(qs, need)
            print(f"{name:<30} P-B={pb:.4f}  均值二项={mb:.4f}  偏差={mb - pb:+.4f} ({(mb - pb) * 100:+.2f}pp)")
            # 断言锁(数值=证明 ④层声明转写:变等级混合下平均 q 二项近似的
            # 绝对偏差实测 ≤0.4pp 且方向保守即不高于逐店精确卷积)
            assert abs(mb - pb) <= 0.004, f"variable-level binomial dev > 0.4pp: {name} dev={(mb - pb) * 100:.2f}pp"
            assert mb <= pb + 1e-12, f"variable-level binomial not conservative: {name} dev={(mb - pb) * 100:.2f}pp"


# ---------- 跑对拍 ----------
def main() -> None:
    cases = [
        ("P3 Lv9 item=(1,c3,set3)+(2,c4,set1)", 9, case_p9_l9()),
        ("P2 Lv7 item=(3,c3,set1)+(1,c2,set5)", 7, case_p2_l7()),
        ("压力 Lv9 同费三件 (1,c3,set2)x3", 9, case_dense()),
    ]
    for n_shops in (6, 12, 25, 50):
        print(f"\n=== N_shops = {n_shops}(含自动+付费刷新) ===")
        print(f"{'用例':<38}{'精确DP':>10}{'边际乘积':>10}{'二项闭式':>10}{'Poisson闭式':>12}")
        for name, level, items in cases:
            ex = exact_dp(level, items, n_shops)
            marg = 1.0
            for it in items:
                marg *= marginal(level, it, n_shops)
            bin_ = closed_form_binomial(level, items, n_shops)
            poi = closed_form_poisson(level, items, n_shops)
            print(f"{name:<38}{ex:>10.4f}{marg:>10.4f}{bin_:>10.4f}{poi:>12.4f}")
            print(f"{'  偏差(闭式-精确)':<38}{'':>10}{marg-ex:>+10.4f}{bin_-ex:>+10.4f}{poi-ex:>+12.4f}")
    variable_level_check()


if __name__ == "__main__":
    main()
