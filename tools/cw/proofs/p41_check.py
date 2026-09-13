"""P41 囤积/卖出 EV 数值自检(不进 src、不提交;print 仅 ASCII)。

复算证明文档 docs/game/currency_war/research/proofs/p41-hoard-sell-ev.md:
  (1) 口述锚点 [22]-(3) 四组再遇数字(公式退化情形 u=H=1);
  (2) expected_refreshes(k=1) 与独立近似 1/P_shop 的口径对账;
  (3) V_opt 二维表(L7-L10 全列 × 五档,脚本生成并逐格断言——文档表 = 本节打印的誊录);
  (4) 序对 u/H 标定误差的稳健性 + 独立档间扰动翻序数精确锁定(带序谓词口径);
  (5) 卖出判定场景(sell_refund 接口;K 内件 max(V_opt, V_ms·ΔP̂) 双通道);
  (6) bench 槽定价示例([34] 稀缺性序)。
口径:q = p(L,c) * a/(v*a) 满池;j/taken 的衰减项由调用方按状态传入,首版表用满池。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from sr_od.application.currency_war.data.cw_shop_odds import (  # noqa: E402
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    expected_refreshes,
    refresh_prob,
)
from sr_od.application.currency_war.kernel.cw_state import sell_refund  # noqa: E402

C_EFF = 2  # SHOP_REFRESH_COST(cw_economy,经 p40 转引;刷价突变语境由调用方替换)
SLOTS = 5  # cw_shop_odds.SHOP_SLOTS


def p_shop(level: int, cost: int, j: int = 0, taken: int = 0) -> float:
    """一轮商店(5 槽)至少出这张特定牌的概率(槽间独立近似,A2)。"""
    v = DISTINCT_CARDS_PER_COST[cost]
    a = POOL_COPIES_PER_CARD[cost]
    q = refresh_prob(level, cost) * (a - j) / (v * a - taken)
    return 1.0 - (1.0 - q) ** SLOTS


def v_opt(level: int, cost: int, u: float, h: int) -> float:
    """V_opt = u * P_miss * C_rescue(P_miss=(1-P_shop)^H,C_rescue=c_eff/P_shop)。"""
    ps = p_shop(level, cost)
    return u * ((1.0 - ps) ** h) * (C_EFF / ps)


print('== P41 check: hoard/sell EV ==')

# --- (1) 口述锚点(user_playstyle [22]-(3);u=H=1 的退化情形) ---
anchors = [
    ('1cost@L5 rounds', 1 / p_shop(5, 1), 7, 15),
    ('5cost@L8 rounds', 1 / p_shop(8, 5), 55, 65),
    ('5cost@L7 rounds', 1 / p_shop(7, 5), 170, 190),
    ('5cost@L9 rounds', 1 / p_shop(9, 5), 15, 20),
    ('5cost@L10 rounds', 1 / p_shop(10, 5), 6, 10),
    ('5cost rescue L8 gold', C_EFF / p_shop(8, 5), 110, 130),
    ('5cost rescue L7 gold', C_EFF / p_shop(7, 5), 340, 380),
]
for tag, val, lo, hi in anchors:
    print(f'  anchor {tag}: {val:.1f}  (claim band {lo}-{hi})')
    assert lo <= val <= hi, f'anchor {tag} out of band: {val}'
print('  [1] all [22]-(3) anchor bands HIT')

# --- (2) 口径对账: expected_refreshes(k=1) vs 1/P_shop(独立近似) ---
# 网格扩到 L∈{7,8,9,10}(A2 声明全表口径,断言覆盖对齐)
print('  (2) registry vs independent approx (k=1):')
for cost in (1, 2, 3, 4, 5):
    for level in (7, 8, 9, 10):
        ps = p_shop(level, cost)
        if ps <= 0:
            continue
        er = expected_refreshes(
            refresh_prob(level, cost), DISTINCT_CARDS_PER_COST[cost],
            POOL_COPIES_PER_CARD[cost], 0, 1, 0)
        rel = abs(er - 1.0 / ps) * ps  # relative to 1/P
        print(f'    c={cost} L={level}: exact={er:.3f} indep={1.0 / ps:.3f} rel={rel:.4f}')
        assert rel < 0.02, f'A2 violated at c={cost} L={level}'
print('  [2] hypergeometric vs independent within 2% (A2 declared)')

# --- (3) V_opt 二维表(规范形式,L7-L10 × 五档全网格;H=10, u 分档) ---
# 表由脚本生成(文档两处表 = 本节打印的誊录,单一源),全表格断言 ±2%(不只 L7 列)。
# 真值口径 = 文档 ① 公式 u·P_miss·(c_eff/P_shop) 满池退化式亲算;与红方脚本
# 与独立复算脚本逐格对齐一致(该临时脚本已清,断言即持久对账)。
U_BAND = {1: 0.05, 2: 0.4, 3: 1.0, 4: 0.8, 5: 0.15}
H_REF = 10
L_REF = 7
LEVELS = (7, 8, 9, 10)
V_OPT_TRUTH = {  # 生成期锁定的真值(2 位小数;文档表按打印值 1 位小数誊录)
    1: {7: 1.33, 8: 1.44, 9: 1.86, 10: 7.09},
    2: {7: 3.03, 8: 4.28, 9: 6.30, 10: 17.41},
    3: {7: 3.48, 8: 5.76, 9: 9.43, 10: 14.03},
    4: {7: 31.76, 8: 9.52, 9: 5.28, 10: 2.78},
    5: {7: 51.19, 8: 15.33, 9: 3.16, 10: 0.56},
}
vals2d = {}
print(f'  (3) V_opt 2D table (H={H_REF}, u per tier) -- doc tables are transcriptions of this print:')
print('      | cost | ' + ' | '.join(f'L{L}' for L in LEVELS) + ' |')
for cost in (1, 2, 3, 4, 5):
    cells = []
    for level in LEVELS:
        vo = v_opt(level, cost, U_BAND[cost], H_REF)
        vals2d[(level, cost)] = vo
        truth = V_OPT_TRUTH[cost][level]
        rel = abs(vo - truth) / truth
        assert rel < 0.02, f'2D table drift at c={cost} L={level}: calc={vo} truth={truth}'
        cells.append(f'{vo:.1f}')
    print(f'      | {cost}cost(u{U_BAND[cost]}) | ' + ' | '.join(cells) + ' |')
# L7 列对拍 p46 首版保守序 1-2 / 3-8 / >=30(原 ③ 断言保留;仅 L7 列受此带约束)
assert 1 <= vals2d[(7, 1)] <= 2, f'1cost band: {vals2d[(7, 1)]}'
assert 3 <= vals2d[(7, 2)] <= 8, f'2cost band: {vals2d[(7, 2)]}'
assert 3 <= vals2d[(7, 3)] <= 8, f'3cost band: {vals2d[(7, 3)]}'
assert vals2d[(7, 4)] >= 30, f'4cost band: {vals2d[(7, 4)]}'
assert vals2d[(7, 5)] >= 30, f'5cost band: {vals2d[(7, 5)]}'
print('  [3] full-grid 2D table within 2% of locked truth (L7-L10 all covered); '
      'L7 column vs p46 first-version bands consistent')
# L7 列明细(文档首表誊录源:P_shop / 轮数 / 补救金 / P_miss / V_opt)
for cost in (1, 2, 3, 4, 5):
    ps = p_shop(L_REF, cost)
    print(f'    L7 {cost}cost: P_shop={ps:.4f} rounds={1 / ps:.1f} rescue={C_EFF / ps:.1f} '
          f'P_miss={(1 - ps) ** H_REF:.3f} V_opt={vals2d[(L_REF, cost)]:.1f}')

# --- (4) 稳健性: u 同乘常数 / H 网格,档间**序**不翻转(绝对带心随 u 缩放是标定事项,非序) ---
def band_order(v4: dict) -> bool:
    # 序断言(纯序,不含绝对带心):1费 < 2/3费带 < 4/5费带,且带间严格分离
    return (v4[1] < min(v4[2], v4[3])
            and max(v4[2], v4[3]) < min(v4[4], v4[5]))

for mult in (0.5, 1.0, 2.0):
    for h in (6, 10, 14):
        v4 = {c: v_opt(L_REF, c, U_BAND[c] * mult, h) for c in U_BAND}
        ok = band_order(v4)
        print(f'    robust u*{mult} H={h}: order_ok={ok} '
              f'vals={[round(v4[c], 1) for c in sorted(v4)]}')
        assert ok, f'order flipped at u*{mult} H={h}'
print('  [4] band ORDER robust to u scale x0.5-x2 and H in [6,14] '
      '(absolute band center scales with u = calibration matter, not order)')

# --- (5) 卖出判定场景(卖 ⇔ refund + V_slot > max(V_opt, V_ms·ΔP̂·[x∈K]) + V_power) ---
def should_sell(refund: int, v_slot: float, v_opt_: float, v_power: float,
                v_ms_dp: float = 0.0) -> bool:
    """主式落地 max 双通道——K 内件弃购成本取 max(V_opt, V_ms·ΔP̂)
    (骨架件走完成概率损失通道,单用 V_opt 低估保留价值);
    K 外件 ΔP̂=0 → v_ms_dp 缺省 0,max 退化为单通道,与 ⑤ 互斥分域自洽。"""
    return refund + v_slot > max(v_opt_, v_ms_dp) + v_power

# refund 接口对拍(sell_refund 机制事实)
assert sell_refund(1, 1) == 1 and sell_refund(1, 4) == 4
assert sell_refund(2, 1) == 3, '2star 1cost = +3 live measured, no fee'
assert sell_refund(2, 3) == 8, '2star 3cost = 9-1 fee'
assert sell_refund(3, 3) == 26, '3star 3cost = 27-1 (speculative)'

# S-a 燃料件: bench 满(V_slot=6 被阻断插件),1star 1cost,V_power=0(K 外件,v_ms_dp=0)
vo1 = v_opt(L_REF, 1, U_BAND[1], H_REF)
assert should_sell(sell_refund(1, 1), 6.0, vo1, 0.0), 'fuel 1cost must sell under pressure'
print(f'  S-a fuel 1star1cost full-bench: refund 1 + slot 6 > V_opt {vo1:.1f} -> SELL')

# S-b 骨架件: 同压力 1star 4cost 目标件(持有收益 >0 只作符号,取 0 已足够不卖)
vo4 = v_opt(L_REF, 4, U_BAND[4], H_REF)
assert not should_sell(sell_refund(1, 4), 6.0, vo4, 0.0), 'skeleton 4cost must hold'
print(f'  S-b skeleton 1star4cost full-bench: refund 4 + slot 6 < V_opt {vo4:.1f} -> HOLD')

# S-b2 K 内件 max 通道接管:骨架件在目标线 K 内,弃购成本走 V_ms·ΔP̂ 通道。
# 构造 = L10 的 4费 K 内件:V_opt 已缩到 2.8,单通道会被 refund+V_slot=10 误卖;
# max 通道(V_ms·ΔP̂=40)接管后不卖——这正是 R1-N1 要堵的 K 内骨架件误卖形态。
vo4_l10 = v_opt(10, 4, U_BAND[4], H_REF)
assert should_sell(sell_refund(1, 4), 6.0, vo4_l10, 0.0), \
    'control: single channel WOULD sell this low-V_opt case (demonstrates the hazard)'
assert not should_sell(sell_refund(1, 4), 6.0, vo4_l10, 0.0, v_ms_dp=40.0), \
    'K-internal piece must hold when V_ms*dP channel dominates'
print(f'  S-b2 K-internal 1star4cost@L10: single-channel would SELL (V_opt {vo4_l10:.1f} < 10), '
      'max(V_opt, V_ms*dP=40) -> HOLD')

# S-c 冗余 2star 3cost 副本(压库完成、非插件需求、有空槽 V_slot=0)
vo3 = v_opt(L_REF, 3, U_BAND[3], H_REF)
assert should_sell(sell_refund(2, 3), 0.0, vo3, 0.0), 'redundant 2star 3cost sells (refund 8)'
print(f'  S-c redundant 2star3cost free-slot: refund 8 > V_opt {vo3:.1f} -> SELL')

# S-d 1费零成本往返(economy S3)
assert sell_refund(2, 1) - 3 * 1 == 0, '1cost any star round trip net 0'
print('  S-d 1cost round trip net 0 (free pool manipulation, slot is the only cost)')

# S-e 终局清仓: G->0 => V_opt -> 0 => 全体翻卖
assert should_sell(sell_refund(1, 4), 0.0, 0.0, 0.0), 'end-of-game liquidation'
print('  S-e game-end: V_opt -> 0 -> sell everything (liquidation always optimal)')

# --- (6) bench 槽定价示例([34] 稀缺性序;R3-N3:净口径与文档 ③ 对齐) ---
v_plugin = 6.0
vo5_gross = v_opt(L_REF, 5, U_BAND[5], H_REF)
vo5_net = vo5_gross - 5.0  # net caliber: V_opt - card price (doc section 3 N2 fix; gross would double-count the buy price)
v_slot_full = max(v_plugin, vo5_net)  # max of blocked-action NET EVs (merge-completing buys excluded)
assert abs(vo5_gross - 51.2) < 0.5 and abs(vo5_net - 46.2) < 0.5, 'gross/net calibers both declared'
assert v_slot_full == vo5_net
assert v_plugin < v_slot_full, 'plugin blocked when last slot priced by 5cost hoard option (net)'
v_slot_free = 0.0
assert v_plugin >= v_slot_free, 'plugin allowed with free slots'
print(f'  (6) V_slot(net): free<=1 -> {v_slot_full:.1f} (gross {vo5_gross:.1f}; blocks plugin EV {v_plugin}); '
      f'free>=2 -> 0 (plugin allowed)')
print('  [34] scarcity order mathematized: plugin buy iff V_plugin >= V_slot')

# 单调性 sanity: V_opt 随等级升(5费)单调降(补救变便宜)、随 P_miss 主导项自洽
assert v_opt(7, 5, 1, 10) > v_opt(10, 5, 1, 10), 'higher level -> cheaper rescue -> lower V_opt'
print('monotonicity: V_opt(5cost, L7) > V_opt(5cost, L10) OK')

# 独立档间扰动翻序数(实证:u 各档独立扰动会翻档序,档间标定不可省)。
# 「翻序」判据显式化(本篇统一口径) = 自检 (4) 的带序谓词 band_order 被破坏:
#   带序 = 1费 < min(2费,3费) 且 max(2费,3费) < min(4费,5费)(严格分离)。
# 对照口径(只打印不断言为文档值,数值与带序口径不可比):
#   链式谓词 not(v1<=v2<=v3<=v4) —— 红方脚本口径,{0.5,2}^5 下 16/32、3^5 下 108/243;
#   相邻五对口径 any(v[c]>v[c+1]) —— {0.5,2}^5 下 20/32。
import itertools  # noqa: E402

REFRESH_PROB = {L: {c: refresh_prob(L, c) for c in (1, 2, 3, 4, 5)} for L in (6, 7, 8, 9, 10)}
base_u = {1: 0.05, 2: 0.4, 3: 1.0, 4: 0.8, 5: 0.15}
base_v = {}
for c in (1, 2, 3, 4, 5):
    q = REFRESH_PROB[7][c] / DISTINCT_CARDS_PER_COST[c]  # 满池近似(正文退化式同口径)
    P_shop = 1.0 - (1.0 - q) ** 5
    base_v[c] = base_u[c] * (1.0 - P_shop) ** 10 * (C_EFF / P_shop)
for grid_name, grid in (('2^5(x0.5/2)', (0.5, 2.0)), ('3^5(+x1)', (0.5, 1.0, 2.0))):
    flips = flips_chain = total = 0
    for scale in itertools.product(grid, repeat=5):
        vv = {c: base_v[c] * scale[c - 1] for c in base_v}
        total += 1
        if not band_order(vv):
            flips += 1
        if not (vv[1] <= vv[2] <= vv[3] <= vv[4]):
            flips_chain += 1
    print(f'independent per-tier u perturbation {grid_name}: band-order flips={flips}/{total} '
          f'(canonical), chain4 flips={flips_chain}/{total} (red-side criterion)')
    if grid_name == '2^5(x0.5/2)':
        assert flips == 12, f'band-order flips must be 12/32, got {flips}'
    else:
        assert flips == 45, f'band-order flips must be 45/243, got {flips}'
# 相邻带基础间隔(边界容错声明):1->2 2.28x / 2->3 1.15x / 3->4 9.13x / 4->5 1.61x
for (lo, hi), expect in (((1, 2), 2.28), ((2, 3), 1.15), ((3, 4), 9.13), ((4, 5), 1.61)):
    ratio = base_v[hi] / base_v[lo]
    assert abs(ratio - expect) / expect < 0.02, f'adjacent interval {lo}->{hi} drifted: {ratio}'
print('adjacent base intervals locked: 2.28/1.15/9.13/1.61')

# 等级敏感二维抽查(5费 L7 vs L9 约 16x)
def _v5(Lv):
    q5 = REFRESH_PROB[Lv][5] / DISTINCT_CARDS_PER_COST[5]
    P5 = 1.0 - (1.0 - q5) ** 5
    return 0.15 * (1.0 - P5) ** 10 * (C_EFF / P5)

r79 = _v5(7) / _v5(9)
print(f'5cost V_opt L7/L9 ratio = {r79:.1f} (B2: ~16x level sensitivity)')
assert r79 > 10

# C_rescue 通道集(声明,不计算): = {当前级付费刷, 升级后再刷(净账=升级后级
# C_rescue + 升级金成本,升级 EV 归 p39 不在此重算)};「放弃」通道不入 min(其代价 = A7 已略的
# 截止损失,按 0 金入 min 会使 V_opt 塌缩为 0);金截断 = 通道净账 > 当前可支金即从 min 集剔除。
# 本脚本全部表值按「当前级付费刷」通道计算(文档 ① 已声明);升级通道需 p39 升级金成本输入,列修订方向。
print('N2 declared: C_rescue channel set {current-level, upgrade-then-refresh}; '
      'tables computed on current-level channel (upgrade channel = revision direction)')

# N3: P_shop=0 分支显式判(5费@L6 不进店 -> 无决策对象)
assert REFRESH_PROB[6][5] == 0, 'L6 5cost prob should be 0'
print('L6 5cost p=0 -> not a decision object (no discard choice exists)')

print('ALL ASSERTIONS PASSED')
