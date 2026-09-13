"""P49 压库期望价值 数值自检(不进 src、不提交;print 仅 ASCII)。

复算证明文档 docs/game/currency_war/research/proofs/p49-pool-compression-ev.md:
  (1) 口述/演示锚点:3费杂牌 ≈0.27 金/窗口、1费 ≈0.07(白压)、5费正确参数补算(k=9,j=7,池 81);
  (2) 边际压缩价值二维表(费用档 × 等级,Δ金/张;文档表 = 本节打印的誊录,全格断言 ±2%);
  (3) 线性律:3费@L7 边际在 taken∈[0,24] 恒定(±1.5%)——「每张杂牌恒定省」的数学形态;
  (4) 单调性:E[refreshes] 随 taken 单调降(全网格);
  (5) 3费追3星(k=9,j=7)补充行(压库在深缺口的值更大);
  (6) 窗口聚合:V_comp = A×Δ金(A=激活概率带),「一张 3费杂牌的窗口内价值」量级(下界,见 C3);
  (7) [34] 数学化:目标档匹配=必要条件(跨档购零压缩;_refresh_dist 双路径行为断言);
      V_opt(p41 公式现场重算,非誊录) vs V_comp 档间比较;
  (8) 2★ 合成 tradeoff:sell_refund 往返账;r=3 已收口(2026-08-31 用户裁定,
      economy §1 二次确认版):合成后卖出压缩保留 (3−r)×Δ金 ≡ 0;
  (9) [11] 联合:卖回概率 π 下的期望保留压缩 + 卖回档序 = argmin 每金压缩损失(Δ金/cost),
      含 L7 序翻转断言(2费→3费→1费,旧「1费先卖」被证伪)。

口径:E 全部走 expected_refreshes 的 taken 参数精确超几何 DP(命题 1 硬要求,非独立近似);
场景 = 追 2星差 2 张(k=3,j=1;c=1-4)/ 5费追 3星差 2 张(k=9,j=7),A3 声明。
池参数为注册表基线;resolved 口径(专家顾问族/黑塔纪元/援军等池构成族突变)下
v_c/a_c 变化 → 概率表/压缩表整体重生成(设计 §4.10,本脚本不覆盖该语境)。
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from sr_od.application.currency_war.data.cw_shop_odds import (  # noqa: E402
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    _refresh_dist,
    expected_refreshes,
    refresh_prob,
)
from sr_od.application.currency_war.kernel.cw_state import sell_refund  # noqa: E402

C_EFF = 2  # SHOP_REFRESH_COST(cw_economy,经 p40 转引;刷价突变语境由调用方替换)
SLOTS = 5  # cw_shop_odds.SHOP_SLOTS

# A3 场景:目标件在追的典型活跃搜牌窗口(差 2 张 = [economy §5] 「key 牌差 1-2 张成型」带)
SCEN: dict[int, tuple[int, int]] = {1: (3, 1), 2: (3, 1), 3: (3, 1), 4: (3, 1), 5: (9, 7)}
LEVELS = (4, 5, 6, 7, 8, 9, 10)


def e_ref(cost: int, level: int, taken: int) -> float:
    """E[refreshes] | 场景(cost,level),池被压 taken 张(精确超几何 DP)。"""
    k, j = SCEN[cost]
    return expected_refreshes(
        refresh_prob(level, cost), DISTINCT_CARDS_PER_COST[cost],
        POOL_COPIES_PER_CARD[cost], taken, k, j)


def dgold(cost: int, level: int, taken: int = 0) -> float:
    """第 taken+1 张同费杂牌的边际压缩价值(金)= ΔE × c_eff(条件值:窗口全程付费刷)。"""
    return (e_ref(cost, level, taken) - e_ref(cost, level, taken + 1)) * C_EFF


def per_gold(cost: int, level: int) -> float:
    """每金压缩损失 = Δ金/refund(1★ refund=cost)——凑息卖回的正确目标函数(B1)。

    凑息约束是 Σrefund ≥ G(金计),同为凑 1 金息,低退金牌要多卖几张——
    应比「每牺牲 1 金息损失多少压缩」,不是每张。
    """
    return dgold(cost, level) / cost


print('== P49 check: pool compression EV ==')

# --- (1) 锚点:演示脚本三行对拍(demo_compress.py 同源;5费行原参数传错,此处为正确参数补算) ---
anchors = [
    ('3cost@L7 per-card gold', dgold(3, 7), 0.24, 0.30),      # 用户读数 ≈0.27
    ('1cost@L5 per-card gold', dgold(1, 5), 0.06, 0.08),      # 用户读数 ≈0.07(白压)
    ('5cost@L8 per-card gold (k=9,j=7)', dgold(5, 8), 19.0, 21.0),  # 补算(条件值,见 (6) 激活门)
    ('5cost@L9 per-card gold (k=9,j=7)', dgold(5, 9), 5.5, 6.5),
]
for tag, val, lo, hi in anchors:
    print(f'  anchor {tag}: {val:.3f}  (band {lo}-{hi})')
    assert lo <= val <= hi, f'anchor {tag} out of band: {val}'
print('  [1] demo anchors HIT (3cost 0.27 / 1cost 0.07 / 5cost corrected 20.0@L8)')

# --- (2) 边际压缩价值二维表(文档表 = 本节打印的誊录,单一源;全格断言 ±2%) ---
DGOLD_TRUTH: dict[int, dict[int, float]] = {  # 生成期锁定的真值(3 位;±2% 带)
    1: {4: 0.048, 5: 0.070, 6: 0.105, 7: 0.165, 8: 0.174, 9: 0.209, 10: 0.628},
    2: {4: 0.126, 5: 0.095, 6: 0.078, 7: 0.105, 8: 0.126, 9: 0.157, 10: 0.314},
    3: {4: 1.071, 5: 0.536, 6: 0.428, 7: 0.268, 8: 0.335, 9: 0.428, 10: 0.536},
    4: {5: 5.357, 6: 2.143, 7: 1.071, 8: 0.487, 9: 0.357, 10: 0.268},
    5: {7: 60.000, 8: 20.000, 9: 6.000, 10: 2.400},
}
print('  (2) marginal compression value dGold/card 2D table -- doc tables are transcriptions:')
print('      | cost(k,j) | ' + ' | '.join(f'L{L}' for L in LEVELS) + ' |')
for cost in (1, 2, 3, 4, 5):
    cells = []
    for level in LEVELS:
        if refresh_prob(level, cost) <= 0:
            cells.append('-')
            continue
        val = dgold(cost, level)
        truth = DGOLD_TRUTH[cost][level]
        rel = abs(val - truth) / truth
        assert rel < 0.02, f'2D table drift at c={cost} L={level}: calc={val} truth={truth}'
        cells.append(f'{val:.2f}')
    k, j = SCEN[cost]
    print(f'      | {cost}(k{k}j{j}) | ' + ' | '.join(cells) + ' |')
print('  [2] full-grid 2D table within 2% of locked truth')

# --- (3) 线性律:3费@L7 边际在 taken∈[0,24] 恒定(±1.5%) ---
# 失效边界(文档边界节声明):仿射性在 rem_nontarget 近耗尽(≳90%)处失效——
# 5费@L8 taken=67→72(非目标池容量 8×9=72 邻域)边际 20.0→25.5(+27%),带外不可外推。
base = dgold(3, 7, 0)
for n in (1, 6, 12, 24):
    m = dgold(3, 7, n)
    rel = abs(m - base) / base
    print(f'    marginal at taken={n}: {m:.4f} (rel {rel:.4f})')
    assert rel < 0.015, f'linearity broken at taken={n}: {m} vs {base}'
print('  [3] marginal exactly constant in taken (linear law, +/1.5%) within [0,24]')

# --- (4) 单调性:E 随 taken 单调降(全网格) ---
for cost in (1, 2, 3, 4, 5):
    for level in LEVELS:
        if refresh_prob(level, cost) <= 0:
            continue
        es = [e_ref(cost, level, t) for t in (0, 6, 12, 24)]
        assert all(es[i] > es[i + 1] for i in range(len(es) - 1)), \
            f'monotonicity broken at c={cost} L={level}'
print('  [4] E[refreshes] strictly decreasing in taken, full grid')

# --- (5) 3费追3星补充行(k=9,j=7:深缺口搜牌量大 → 每张压缩值更大) ---
for level, truth in ((7, 1.500), (8, 1.875), (9, 2.400)):
    k, j = 9, 7
    e0 = expected_refreshes(refresh_prob(level, 3), 14, 9, 0, k, j)
    e1 = expected_refreshes(refresh_prob(level, 3), 14, 9, 1, k, j)
    val = (e0 - e1) * C_EFF
    print(f'    3cost 3star(k9j7) L{level}: dGold={val:.3f}')
    assert abs(val - truth) / truth < 0.02, f'3star row drift at L{level}'
print('  [5] 3cost 3star supplement row locked (1.50/1.88/2.40 @L7/8/9)')

# --- (6) 窗口聚合:V_comp = A x dGold(A=该缺口实际进入付费 D 的概率,待标定) ---
# E[refreshes] 的 taken 差分是「当前活跃窗口」的累计节省(当前窗口的窗口数因子已被 DP
# 积分掉);未来同档新窗口(下一个目标/加深)不在该 DP 内——本式是下界(C3 方向声明)。
d3 = dgold(3, 7)
for a in (0.25, 0.5, 1.0):
    print(f'    A={a}: V_comp(3cost junk @L7) = {a * d3:.3f} gold')
    assert a * d3 < 0.30, 'global value of one 3cost junk must stay under 0.30 gold'
d5 = dgold(5, 8)
gated = d5 * 0.05
print(f'    5cost@L8 conditional {d5:.1f} x A(<=0.05, V*=148 gate rarely passes) '
      f'= {gated:.2f} gold -> de-facto zero')
print('  [6] window aggregation: V_comp = A x dGold; 3cost global ~0.07-0.27 (lower bound), 5cost ~0 (gate)')

# --- (7) [34] 数学化:目标档匹配必要 + V_opt vs V_comp ---
# 跨档购零压缩是模型结构事实:q_X = p(L,X)*(a_X-j)/(v_X*a_X-taken_X) 不含 taken_Y。
# 行为断言(替代原恒真式):用独立重建的超几何路径对拍 _refresh_dist 本体——
# 重建式的非目标池项 = (v-1)*a - c 只含同费 (v,a,c),对拍通过即 _refresh_dist
# 的行为与「c 只扣同费池」的读码结论一致(文档 ③ 保留文字版结论)。
def refresh_dist_ref(p: float, v: int, a: int, c: int, k_need: int, j: int) -> list[float]:
    rem_t = a - j
    rem_n = (v - 1) * a - c
    total = rem_t + rem_n
    dist = [0.0] * (k_need + 1)
    if total <= 0:
        return dist
    for m in range(SLOTS + 1):
        p_m = math.comb(SLOTS, m) * (p ** m) * ((1.0 - p) ** (SLOTS - m))
        if p_m <= 0:
            continue
        denom = math.comb(total, m)
        if denom == 0:
            continue
        for x in range(min(m, k_need) + 1):
            if x > rem_t or (m - x) > rem_n:
                continue
            dist[x] += p_m * math.comb(rem_t, x) * math.comb(rem_n, m - x) / denom
    return dist


for cost in (1, 3):
    for c_taken in (0, 4, 12):
        d_impl = _refresh_dist(refresh_prob(7, cost), DISTINCT_CARDS_PER_COST[cost],
                               POOL_COPIES_PER_CARD[cost], c_taken, 3, 1)
        d_ref = refresh_dist_ref(refresh_prob(7, cost), DISTINCT_CARDS_PER_COST[cost],
                                 POOL_COPIES_PER_CARD[cost], c_taken, 3, 1)
        assert all(abs(x - y) < 1e-12 for x, y in zip(d_impl, d_ref, strict=True)), \
            f'_refresh_dist deviates from same-cost-only hypergeometric rebuild: c={cost} taken={c_taken}'
print('    _refresh_dist matches independent rebuild (c enters same-cost pool only)')

# V_opt 现场重算(p41 ① 公式 u·P_miss·(c_eff/P_shop),H=10,分档 u 与 p41 同参)——
# 不再誊录 p41 表常数(C4):手抄是漂移源。与 p41 文档表(1 位小数)逐档对拍,
# 差异应 ≤0.1 金;p41 的 5费 L7 格若因末位舍入漂移,登记 p41 下次触碰时勘误(本次不改 p41)。
U_BAND = {1: 0.05, 2: 0.4, 3: 1.0, 4: 0.8, 5: 0.15}  # p41 分档 u(同参,来源 p41_check)


def p_shop(level: int, cost: int) -> float:
    v = DISTINCT_CARDS_PER_COST[cost]
    a = POOL_COPIES_PER_CARD[cost]
    q = refresh_prob(level, cost) * a / (v * a)
    return 1.0 - (1.0 - q) ** SLOTS


def v_opt(level: int, cost: int, u: float, h: int) -> float:
    ps = p_shop(level, cost)
    return u * ((1.0 - ps) ** h) * (C_EFF / ps)


V_OPT_P41_DOC = {1: 1.3, 2: 3.0, 3: 3.5, 4: 31.8, 5: 51.2}  # p41 文档表誊录(仅对拍用)
V_OPT_L7 = {c: v_opt(7, c, U_BAND[c], 10) for c in (1, 2, 3, 4, 5)}
for c in (1, 2, 3, 4, 5):
    diff = abs(V_OPT_L7[c] - V_OPT_P41_DOC[c])
    print(f'    V_opt {c}cost@L7 = {V_OPT_L7[c]:.2f} vs p41 doc {V_OPT_P41_DOC[c]:.1f} '
          f'(diff {diff:.2f}{" <=0.1 ok" if diff <= 0.1 else " <-- DRIFT"})')
    assert diff <= 0.1, f'V_opt recalc drifts from p41 doc by >0.1 at c={c}'
# 激活带上界 A_max:该档缺口实际进入付费 D 的概率上界。A 的物理来源 = p40 R1 完成门
# (c_eff·E[refreshes] <= V_gap);p40 ③ 的 V*=c_eff/P 是单步价值门阈值(表值 19.2/148.4
# 两行),1-4费带上界取 1;5费深缺口完成门常态不过 → A ≈ 0(首版带上界 0.05)。
A_MAX = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 0.05}
print('    tier | V_comp(A=1) | A_max | V_comp effective | V_opt(L7 recalc) | ratio')
for cost in (1, 2, 3, 4, 5):
    level = 7
    vc = dgold(cost, level) if refresh_prob(level, cost) > 0 else dgold(cost, 8)
    eff = A_MAX[cost] * vc
    ratio = V_OPT_L7[cost] / eff
    print(f'    {cost}cost | {vc:.2f} | {A_MAX[cost]:.2f} | {eff:.2f} | '
          f'{V_OPT_L7[cost]:.1f} | {ratio:.0f}x')
    assert V_OPT_L7[cost] > eff, \
        f'hoard option must dominate effective compression at c={cost}'
print('  [7] V_opt > V_comp(effective) all tiers; raw 5cost@L7 conditional 60 > V_opt ~51 '
      'but gated by A<=0.05 (search itself non-executable, E0=2200 refreshes)')

# --- (8) 2★ 合成 tradeoff(sell_refund 往返账;r=3 已收口) ---
assert sell_refund(2, 1) == 3 and sell_refund(2, 3) == 8  # 2star 1cost=+3 live(实证)
rt_1c = sell_refund(2, 1) - 3 * 1
rt_3c = sell_refund(2, 3) - 3 * 3
assert rt_1c == 0, '1cost 2star round trip must be net 0 (frictionless)'
assert rt_3c == -1, '3cost 2star round trip must be -1 (fee)'
print(f'    round trip: 1cost 2star net {rt_1c:+d}; 3cost 2star net {rt_3c:+d}')
# r=3 收口(2026-08-31 用户裁定,economy §1 二次确认版):卖 2★ 回池 3 张 1★——
# 不变量 = 剩余池 − resolved 固定池 − 持有副本总数(合成不销毁副本,2★ 计 3 张)。
# 推论:①持有 2★ 期间压缩 3 张等效(合成不动池);②卖 2★ 一次性释放全部 3 张压缩,
# cost≥2 另 −1 手续费 → merge-then-sell 相对卖 3×1★ 的压缩保留 (3−r)×Δ金 ≡ 0——
# 「为保留压缩而合成」通道死,合成的理由只剩槽位(释放 2 槽);
# ③卖回序更不该先卖 2★(见 (9))。
r = 3
assert (3 - r) * dgold(3, 7) == 0 and (3 - r) * 1.500 == 0, \
    'r=3 closing: merge-then-sell retains zero compression in any window'
print('    r=3 closed: merge-then-sell retains 0 compression (all windows); '
      'slot gain is the only merge motive')
print('  [8] 2star tradeoff: 1cost frictionless; cost>=2 fee 1; r=3 -> no compression retention')

# --- (9) [11] 联合:卖回概率 pi 下的期望保留压缩 + 卖回档序(每金目标函数) ---
# 卖回档序 = argmin 每金压缩损失 Δ金/cost(B1:凑息约束 Σrefund>=G 是金计,比每金不比每张):
#   第一优先:V_comp=0 的档(∉T_search 的持有杂牌)恒先卖——零压缩损失白卖
#             (旧「1费先卖」仅在该分支下成立,是 T_search 过滤的推论);
#   第二优先:T_search∩bench 可卖集上按 Δ金/cost 升序;1费粒度 1 金做尾差贴息线(最后项);
#   2★ 排同档最后(每金损失 = 3Δ/3c = Δ/c 与同档 1★ 同,但粒度粗 3c + 手续费)。
for level in (7,):
    pg = {c: per_gold(c, level) for c in (1, 2, 3, 4)}
    print(f'    L{level} per-gold loss: ' + ' '.join(f'{c}c={pg[c]:.4f}' for c in pg))
    assert pg[2] < pg[3] < pg[1] < pg[4], \
        f'L{level} per-gold order must be 2cost->3cost->1cost->4cost: {pg}'
# 翻转断言:L7 双窗(1费/3费都在 T_search)同活时凑 3 金——
# 卖 1×3费损失 0.268 < 卖 3×1费损失 0.496:旧「1费先卖(每张口径)」被证伪。
loss_via_3c = per_gold(3, 7) * 3
loss_via_1c = per_gold(1, 7) * 3
print(f'    raise 3 gold @L7: sell 1x3cost loss={loss_via_3c:.3f} '
      f'vs sell 3x1cost loss={loss_via_1c:.3f}')
assert loss_via_3c < loss_via_1c, 'flip assertion: 3cost must beat 1cost for raising 3 gold @L7'
d3 = dgold(3, 7)
for pi in (0.0, 0.3, 0.6):
    print(f'    pi={pi}: E[retained comp] 3cost/card = {(1 - pi) * d3:.3f} '
          f'(sold cards return to pool, compression undone)')
print('  [9] sellback order: V_comp=0 tiers first, then min per-gold loss dGold/cost '
      '(L7: 2c->3c->1c; 1cost tail-fits interest line; 2star last within tier)')

print('ALL ASSERTIONS PASSED')
