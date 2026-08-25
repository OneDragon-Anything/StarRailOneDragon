"""W178 P13 守50期望账 + 息律分段函数——数据面计算脚本(可重跑;精确 DP 零蒙特卡洛)。

对应证明:docs/game/currency_war/research/proofs/p13-hold50-expected-account.md

数据源(单一源真值,全部 import,不抄数值):
- cw_horizon: interest(g)=min(g//10, cap) / NODES_PER_PLANE / TOTAL_NODES
- cw_economy: BASE_REWARD_GOLD / STREAK_GOLD_TABLE / streak_gold
- decision_v2 registry: h3_win_rate / rung_value(P3 边际) / interest_cap /
  interest_recovery_rounds / hp_to_gold / interest_floor / form_floor / boss_floor

三问:
① 守50 vs 底线40/30/20 vs 不守 的期望出口金+方差+累计利息(9 轮精确 DP);
② 破50买牌的 EV 边界 Δp*(轮次, 跨档数) 与硬节点旁路;
③ 息律分段函数(同档零损/攒息/溢余)的一致性检验。

用法: uv run python tools/cw/proofs/w178_p13_hold50_expected_account.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / 'pyproject.toml').exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / 'src'))

from sr_od.application.currency_war.cw_economy import (  # noqa: E402
    BASE_REWARD_GOLD,
    streak_gold,
)
from sr_od.application.currency_war.cw_horizon import (  # noqa: E402
    NODES_PER_PLANE,
    TOTAL_NODES,
    interest,
)
from sr_od.application.currency_war.decision_v2.registry import (  # noqa: E402
    DecisionV2Registry,
)

REG = DecisionV2Registry()
R_LEFT_TOTAL = TOTAL_NODES - NODES_PER_PLANE   # P1 出口后 P2+P3 剩余节点 = 18

# Δ池硬节点掉血桶均值(w135 checks:encounter 桶9 −17.7 / boss 桶9 −24.9;
# 与 P10 ③ 同源,口径见 p10 单篇数据源行)
HP_LOSS_ENCOUNTER = 17.7
HP_LOSS_BOSS = 24.9


# ============================================================ #
# ① 三策略族期望账:精确 DP(状态=(轮,金,连胜),无随机误差)
# ============================================================ #

def dp_floor(floor: int, p: float, g0: int = 10,
             rounds: int = NODES_PER_PLANE,
             mandatory: tuple[int, ...] | None = None) -> dict[str, float]:
    """floor 策略(溢余即花、袋子保持 ≥floor)的 9 轮精确推演。

    模型(假设显式,证明单篇 §假设节同文):
    - 每轮收入 = interest(g) + BASE_REWARD_GOLD + streak_gold(s)(结算到袋);
    - optional ``mandatory``:每轮固定必要支出(过渡件/人口位,先于溢余扣);
    - 轮末把 floor 之上的溢余全部转板面资产(袋子回落 floor);
    - 连胜链:s → s+1 概率 p(胜),否则归 0(败);p 取 h3_win_rate 按形态档;
    - 出口金 = 第 9 轮结算+花余后的袋金。
    返回:E[出口金] / Var[出口金] / E[累计利息] / P(出口在 floor 上)。
    """
    mand = mandatory or (0,) * rounds
    dist: dict[tuple[int, int], float] = {(g0, 0): 1.0}
    cum_interest = 0.0
    on_floor = 0.0
    for t in range(rounds):
        nxt: dict[tuple[int, int], float] = {}
        round_int = 0.0
        on_floor = 0.0
        for (g, s), w in dist.items():
            inc = interest(g) + BASE_REWARD_GOLD + streak_gold(s)
            round_int += w * interest(g)
            g2 = max(0, min(g + inc, 80) - mand[t])
            spend = max(0, g2 - floor)
            g3 = g2 - spend
            if g3 >= floor:
                on_floor += w
            for s2, w2 in ((s + 1, p), (0, 1.0 - p)):
                key = (g3, min(s2, 7))
                nxt[key] = nxt.get(key, 0.0) + w * w2
        dist = nxt
        cum_interest += round_int
    # 出口金边际分布
    marg: dict[int, float] = {}
    for (g, _s), w in dist.items():
        marg[g] = marg.get(g, 0.0) + w
    ev = sum(g * w for g, w in marg.items())
    var = sum((g - ev) ** 2 * w for g, w in marg.items())
    return {'ev': ev, 'var': var, 'cum_interest': cum_interest,
            'p_reach': on_floor}


def q1_table() -> dict[tuple[int, float], dict[str, float]]:
    print('=' * 76)
    print('① 三策略族期望账(9 轮精确 DP;g0=10;净收入=息+基础+连胜金)')
    print(f'   胜率档 p ∈ h3_win_rate = {REG.h3_win_rate}(形态档驱动,带状)')
    floors = (REG.interest_floor, 40, 30, REG.form_floor, 0)
    results: dict[tuple[int, float], dict[str, float]] = {}
    for p in (REG.h3_win_rate[0], REG.h3_win_rate[1], REG.h3_win_rate[2]):
        print(f'   -- p={p:.3f} '
              f'({"e0 弱形态" if p == REG.h3_win_rate[0] else "e1" if p == REG.h3_win_rate[1] else "e2 强形态"}) --')
        print(f'   {"底线F":>6} {"E[出口金]":>9} {"sd[出口金]":>9} '
              f'{"E[累计息]":>9} {"P(出口在F)":>8}')
        for f in floors:
            r = dp_floor(f, p)
            results[(f, p)] = r
            print(f'   {f:>6} {r["ev"]:>9.2f} {r["var"] ** 0.5:>9.2f} '
                  f'{r["cum_interest"]:>9.2f} {r["p_reach"]:>8.2f}')
    return results


def q1_account_decomposition(res: dict[tuple[int, float], dict[str, float]]) -> None:
    print('-' * 76)
    print('   守50期望账分解(vs 各底线;p=e1 基线)')
    p = REG.h3_win_rate[1]
    base = res[(REG.interest_floor, p)]
    for f in (40, 30, REG.form_floor, 0):
        r = res[(f, p)]
        d_i = base['cum_interest'] - r['cum_interest']
        d_bag = base['ev'] - r['ev']
        print(f'   守50 - 守{f:>2}: 息流差 {d_i:5.2f} 金/位面 + '
              f'袋差 {d_bag:5.2f} 金 → 守{f} 比 守50 多转板面 '
              f'{d_i + d_bag:5.2f} 金(=被推迟/被授权提前的板面支出)')
    print('   → 守50 的经济内容 = 把 (袋差+息流差) 的板面支出推迟到 EV 边界'
          '(②)授权的时点;出口金 50 是该过程在袋子上的表征([28])。')


def q1_sensitivity() -> None:
    print('-' * 76)
    print('   稳健性:g0 ∈ {5,10} × 必要支出带(过渡件 4金×r1-r4 / 6金×r1-r5)')
    p = REG.h3_win_rate[1]
    cases = (
        ('g0=5 无必要支出', 5, None),
        ('g0=10 过渡件 4金×r1-r4', 10, (4, 4, 4, 4, 0, 0, 0, 0, 0)),
        ('g0=10 过渡件 6金×r1-r5', 10, (6, 6, 6, 6, 6, 0, 0, 0, 0)),
    )
    for name, g0, mand in cases:
        r = dp_floor(REG.interest_floor, p, g0=g0, mandatory=mand)
        print(f'   守50 {name}: E[出口]={r["ev"]:.1f} sd={r["var"] ** 0.5:.2f} '
              f'E[累计息]={r["cum_interest"]:.1f}')
    print('   → 必要支出压缩息流但不破坏登板(收入下界 6/轮×9=54 ≥ '
          '50−g0+支出带宽);守50 全程可行,失败线(局70)是破纪律不是不可行。')


# ============================================================ #
# ② 破50买牌的 EV 边界:Δp*(轮次, 跨档数)
# ============================================================ #

def tiers_crossed(g: int, c: int) -> int:
    """买入 c 金使息档下穿的档数(同息档=0;溢余段自然为 0)。"""
    return max(0, interest(g) - interest(g - c))


def c_interest(r: int, t: int) -> float:
    """跨档息损 C = t × min(位面剩余轮, interest_recovery_rounds)。"""
    r_left = NODES_PER_PLANE - r
    return t * min(r_left, REG.interest_recovery_rounds)


def v_formation(dp_gain: float, r: int) -> float:
    """成型通道 V = ΔP(升档) × P3 边际 × 位面剩余轮。"""
    m = REG.rung_value[2] - REG.rung_value[1]   # 1.6(e1→e2 边际)
    return dp_gain * m * (NODES_PER_PLANE - r)


def q2_boundary() -> None:
    print('=' * 76)
    print('② 破50买牌 EV 边界:Δp* = C/(边际×R)(买牌使形态升档的最小概率)')
    m_lo = REG.rung_value[1]                    # 1.4(e0→e1 边际)
    m_hi = REG.rung_value[2] - REG.rung_value[1]  # 1.6
    print(f'   C = t×min(R,{REG.interest_recovery_rounds});'
          f' V = Δp×m×R;m ∈ [{m_lo}, {m_hi}](P3 边际);R = 9 − r')
    print(f'   {"r":>3} {"R":>3} {"C(t=1)":>7} {"C(t=2)":>7} '
          f'{"Δp*@m1.4":>9} {"Δp*@m1.6":>9}')
    for r in range(1, NODES_PER_PLANE + 1):
        rl = NODES_PER_PLANE - r
        c1, c2 = c_interest(r, 1), c_interest(r, 2)
        p1 = c1 / (m_lo * rl) if rl else float('inf')
        p2h = c1 / (m_hi * rl) if rl else float('inf')
        print(f'   {r:>3} {rl:>3} {c1:>7.1f} {c2:>7.1f} '
              f'{p1 if rl else float("nan"):>9.2f} {p2h if rl else float("nan"):>9.2f}')
    print('   → R≥3(早中段):Δp* = 3/(m·R) 随轮次推进升高(破50越来越贵);')
    print('     R<3(r7-r8):C 与 V 同乘 R → Δp* = t/m 轮无关(≈0.63-0.71/t);')
    print('     r9(R=0):位面内 C=0,只剩出口携带溢价 ≤0.83/t(P10①)——')
    print('     allin/boss_floor 的极限形态,与现行阶梯同向。')
    v_hp_e = HP_LOSS_ENCOUNTER * REG.hp_to_gold
    v_hp_b = HP_LOSS_BOSS * REG.hp_to_gold
    print(f'   硬节点旁路(boss/遭遇,连胜在手):V_hp = 掉血×{REG.hp_to_gold}'
          f' = {v_hp_e:.1f}(遭遇)/{v_hp_b:.1f}(boss) ≫ C ≤ '
          f'{c_interest(7, 2):.0f} → 无条件授权深花(P10③,[19]①)。')


# ============================================================ #
# ③ 息律分段函数一致性检验
# ============================================================ #

def q3_piecewise() -> None:
    print('=' * 76)
    print('③ 息律分段函数:同档零损区 / 20-50 攒息区 / ≥50 溢余区(同一公式)')
    bad = 0
    for g in range(0, 71):
        for c in range(1, 6):
            same_tier = (g - c) // 10 == g // 10 and g < 50
            if same_tier and interest(g) - interest(g - c) != 0:
                bad += 1
            if g >= 50 + c and interest(g) - interest(g - c) != 0:
                bad += 1   # 溢余段花到 50 线以上,息档不动
    print(f'   同息档购买(t=0)恒零息损:g∈[0,70]×c∈[1,5] 全表枚举,'
          f'违例 {bad} 个')
    print('   分段(<20 无损区只是「便宜卡天然同档」的特例,W175 口径推广到全金位):')
    for g in (8, 15, 25, 38, 47, 52, 60):
        c = 2
        t = tiers_crossed(g, c)
        zone = ('<20 档内零损' if g < 20 else
                '20-50 攒息区' if g < 50 else '溢余区')
        print(f'     g={g:>2} 买{c}费: 跨档 t={t}, C(r5)={c_interest(5, t):.1f}'
              f'  [{zone}]')
    print('   → 三段是同一决策规则 buy iff V ≥ C = t×min(R,3) 的段位特写:')
    print('     t=0(同档/溢余)→ C=0 → 有非负边际价值即买([11]/[17]/P11);')
    print('     t≥1(攒息区)→ 需 Δp ≥ Δp*(②);例外=[6] 店全想要、'
          '[19]① 硬节点连胜旁路。')


# ============================================================ #
# 断言锁(推导结论的数值面;失败=推导或常量漂移,必须人查)
# ============================================================ #

def assertions(res: dict[tuple[int, float], dict[str, float]]) -> None:
    p1 = REG.h3_win_rate[1]
    e50, e40, e30, e20, e0f = (res[(f, p1)] for f in
                                (REG.interest_floor, 40, 30,
                                 REG.form_floor, 0))
    # A1 出口金期望随底线单调
    assert e50['ev'] >= e40['ev'] >= e30['ev'] >= e20['ev'] >= e0f['ev']
    # A2 守50 几乎必然登板:出口金均值 ≥ 45(P(到过F) ≥ 0.9)
    assert e50['ev'] >= 45.0, e50['ev']
    assert e50['p_reach'] >= 0.9
    # A3 守50 出口方差小(平台吸收收入随机性):sd ≤ 5
    assert e50['var'] ** 0.5 <= 5.0, e50['var']
    # A4 息流差量级:守50 vs 不守 ≥ 25 金/位面;vs 守40 为 1-2 金/轮 × 平台轮
    assert e50['cum_interest'] - e0f['cum_interest'] >= 25.0
    d40 = e50['cum_interest'] - e40['cum_interest']
    assert 1.0 <= d40 <= 6.0, d40
    # A5 e0 弱形态下守50 仍登板(纪律不依赖形态;只是更慢)
    assert res[(REG.interest_floor, REG.h3_win_rate[0])]['ev'] >= 40.0
    # A6 边界单调:Δp* 随轮次推进非降(破50越来越贵),R<3 段轮无关
    m = REG.rung_value[2] - REG.rung_value[1]
    ps = [c_interest(r, 1) / (m * (NODES_PER_PLANE - r))
          for r in range(1, NODES_PER_PLANE)]
    assert all(a <= b + 1e-9 for a, b in zip(ps[:-1], ps[1:], strict=True)), ps
    assert abs(ps[-1] - 1 / m) < 1e-9          # R=1 极限 = t/m 轮无关段
    # A7 同档零损全表枚举无违例(③的枚举内嵌断言)
    for g in range(0, 71):
        for c in range(1, 6):
            assert interest(g) - interest(max(0, g - c)) >= 0
            if (g - c) // 10 == g // 10:
                assert interest(g) - interest(g - c) == 0
    # A8 r9 位面内 C=0(只剩携带溢价)
    assert c_interest(NODES_PER_PLANE, 1) == 0.0
    print('=' * 76)
    print('断言锁 A1-A8 全部通过。')


if __name__ == '__main__':
    res = q1_table()
    q1_account_decomposition(res)
    q1_sensitivity()
    q2_boundary()
    q3_piecewise()
    assertions(res)
