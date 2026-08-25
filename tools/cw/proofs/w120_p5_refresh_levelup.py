# 数学证明计算脚本:P5 刷新-升级选择定理 + P6 前两轮压库账(证明见
# docs/game/currency_war/research/proofs/p05-refresh-vs-levelup.md 与 p06-first-two-rounds-option.md)
# 只读真实表(REFRESH_PROB/升级成本/收入三件套),零随机纯表值,可重跑复核。
# 运行: $env:PYTHONPATH="src"; uv run python tools/cw/proofs/w120_p5_refresh_levelup.py
# 产出对应证明单篇的数字表;游戏版本改概率/成本表后重跑本脚本即可复核命题是否仍成立。
from math import comb

from sr_od.application.currency_war.cw_shop_odds import (
    REFRESH_PROB, DISTINCT_CARDS_PER_COST, POOL_COPIES_PER_CARD,
    _refresh_dist, expected_refreshes, refresh_prob,
)

SHOP_SLOTS = 5
REFRESH_COST = 2          # cw_economy.SHOP_REFRESH_COST
XP_PER_BUY = 4            # cw_state
XP_TO_NEXT = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}  # cw_state
CLICK_COST = 4            # cw_state.XP_CLICK_COST_FALLBACK(flat-4,ADR-0275)


def p_at_least_one(level: int, cost: int, j: int = 0) -> float:
    """一次刷新(5格)至少出 1 张目标牌的概率(超几何,真实表)。"""
    p = refresh_prob(level, cost)
    if p <= 0:
        return 0.0
    v, a = DISTINCT_CARDS_PER_COST[cost], POOL_COPIES_PER_CARD[cost]
    dist = _refresh_dist(p, v, a, 0, 1, j)
    return 1.0 - dist[0]


def upgrade_clicks(lv_from: int, lv_to: int) -> int:
    import math
    n = 0
    for lv in range(lv_from, lv_to):
        xp = XP_TO_NEXT.get(lv)
        if xp is None:
            return None
        n += -(-xp // XP_PER_BUY)
    return n


def e_ref(level: int, cost: int, k: int = 1) -> float:
    """找 k 张特定目标牌的期望刷新次数(k=1 一张;k=3 合 2星)。"""
    p = refresh_prob(level, cost)
    v, a = DISTINCT_CARDS_PER_COST[cost], POOL_COPIES_PER_CARD[cost]
    return expected_refreshes(p, v, a, 0, k, 0)


print('=== P5-1: p(L,c) 曲线(单张目标牌,一次刷新至少出 1) ===')
header = 'L\\c ' + ''.join(f'{c:>10}' for c in (1, 2, 3, 4, 5))
print(header)
for lv in range(1, 11):
    row = f'{lv:>3} '
    for c in (1, 2, 3, 4, 5):
        row += f'{p_at_least_one(lv, c):>10.4f}'
    print(row)

print()
print('=== P5-2: 峰值级与相邻差(c=1..5) ===')
for c in (1, 2, 3, 4, 5):
    curve = [(lv, p_at_least_one(lv, c)) for lv in range(1, 11)]
    peak_lv, peak_p = max(curve, key=lambda t: t[1])
    prev_p = p_at_least_one(peak_lv - 1, c) if peak_lv > 1 else None
    next_p = p_at_least_one(peak_lv + 1, c) if peak_lv < 10 else None
    print(f'c={c}: 峰值级 L*={peak_lv} p*={peak_p:.4f} '
          f'(prev={prev_p if prev_p is None else round(prev_p,4)}, '
          f'next={next_p if next_p is None else round(next_p,4)})')

print()
print('=== P5-3: 期望刷金 E_refresh×2(找 1 张目标牌;c=2/3/5) ===')
for c in (2, 3, 5):
    row = f'c={c} '
    for lv in range(1, 11):
        e = e_ref(lv, c, k=1)
        row += f'L{lv}:{e * REFRESH_COST:>7.1f}g '
    print(row)
print()
print('=== P5-3b: 合 2星(k=3)期望刷金 ===')
for c in (2, 3, 5):
    row = f'c={c} '
    for lv in range(1, 11):
        e = e_ref(lv, c, k=3)
        row += f'L{lv}:{e * REFRESH_COST:>8.1f}g '
    print(row)

print()
print('=== P5-4: 升级成本(flat-4 单击价 × clicks;XP_TO_NEXT_LEVEL 真值) ===')
for lv in range(3, 10):
    xp = XP_TO_NEXT[lv]
    clicks = -(-xp // XP_PER_BUY)
    print(f'lv{lv}->lv{lv+1}: xp={xp} clicks={clicks} cost={clicks*CLICK_COST}g')

print()
print('=== P5-5: EV argmin 总账:从等级 L 起找 1 张 c 费目标牌 ===')
print('策略 = argmin_{L2>=L} [升级金(L->L2) + 2*E_refresh(L2)] (纯金口径,V_buy 同一张牌相消) ===')
for c in (2, 3, 5):
    print(f'--- c={c} ---')
    for lv in range(3, 10):
        cands = []
        for lt in range(lv, 11):
            up = upgrade_clicks(lv, lt)
            upg = 0 if up is None else up * CLICK_COST
            e = e_ref(lt, c, k=1)
            if e == float('inf'):
                continue
            cands.append((upg + e * REFRESH_COST, lt, upg, e * REFRESH_COST))
        cands.sort()
        best = cands[0]
        stay = [x for x in cands if x[1] == lv][0]
        verdict = 'D(留在本级)' if best[1] == lv else f'升到 L*={best[1]}'
        print(f'  L={lv}: 最优 {verdict} 总金={best[0]:.1f} '
              f'(升级{best[2]}g+刷{best[3]:.1f}g) | 留本级总金={stay[0]:.1f}')

print()
print('=== P6: 开局收支推演(开局金 5,基础 5,连胜档真值表 (1,1,2,2,2,3,4)) ===')
STREAK = (1, 1, 2, 2, 2, 3, 4)


def streak_gold(n):
    return STREAK[max(0, min(n, len(STREAK) - 1))]


def sim(buys_r1, buys_r2, buys_r3, win_r3=True):
    """买均为 1 费(cost=1,卖出全额退,息损只看跨档)。r1/r2 奖励节点必过=r1/r2 视作连胜累计。
    收入口径:节点结算时 base5+streak+interest(gold//10 cap5)。"""
    g = 5
    traj = []
    streak = 0
    plans = [(buys_r1, True), (buys_r2, True), (buys_r3, win_r3)]
    for rnd, (b, win) in enumerate(plans, 1):
        g -= b  # 备战期买牌(1费×b)
        interest = min(5, g // 10)
        g += 5 + streak_gold(streak) + interest
        traj.append((rnd, b, interest, g))
        streak = streak + 1 if win else 0
    return traj


print('三臂(r1/r2 各买 0/1/2/3 张 1费,r3 假设买 0、胜):')
for b1 in range(4):
    for b2 in range(4):
        t = sim(b1, b2, 0)
        g3 = t[-1][3]
        # 无买对照
        t0 = sim(0, 0, 0)
        print(f'  b1={b1} b2={b2}: r1末金={t[0][3]} r2末金={t[1][3]} r3末金={g3} '
              f'(零买对照 r3末金={t0[-1][3]})')

print()
print('=== P6-2: 息损逐格(买 1 张后 5 轮内的累计息差;收入=5+streak) ===')
def interest_path(g0, buys_per_round, rounds=5, start_streak=1):
    g = g0
    s = start_streak
    tot_int = 0
    path = []
    for r in range(rounds):
        g -= buys_per_round
        it = min(5, g // 10)
        tot_int += it
        g += 5 + streak_gold(s) + it
        path.append((r + 1, g, it))
        s += 1
    return tot_int, path

for g0 in (5, 9, 10, 11, 15, 19, 20, 21, 25, 29, 30):
    base_tot, base_path = interest_path(g0, 0)
    buy_tot, buy_path = interest_path(g0, 1)
    loss = base_tot - buy_tot
    print(f'开局金 {g0}: r1 买 1 张 1费 → 5 轮累计息差 = {loss} 金 '
          f'(不买轨迹金 {[p[1] for p in base_path]} / 买 {[p[1] for p in buy_path]})')

print()
print('=== P7: 基础奖励 3-8 敏感性(从金 40 回 50 的轮数,零花口径) ===')
for base in range(3, 9):
    g = 40
    s = 1
    r = 0
    while g < 50 and r < 20:
        g += base + streak_gold(s) + min(5, g // 10)
        s += 1
        r += 1
    print(f'base={base}: 40→50 需 {r} 轮(零花,连胜档递增)')
