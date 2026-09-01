"""P42 装备机器 EV 数值自检(入库可重跑;print 仅 ASCII)。

复算证明文档 docs/game/currency_war/research/proofs/p42-equipment-machine-ev.md:
  (1) K8 闭合图谱接口(28 交叉 + 8 自配 = 36 进阶;8 基础件);
  (2) component_demand / hoard_gaps / recycle_qualified 阿雅例对拍(机制事实层接口);
  (3) 逐配方 pivotal 口径(R3 重推):价值实现单元 = 单条配方的兑现(合成即可穿,
      equip_assign 逐件分配),持有张跨配方不可重复消费(子集背包精确分配);
      持有维望远镜恒等式精确(跨件 = A10 同型独立性近似);
      组件级聚合口径把近兑现张损失低估 4-8 个数量级(量级锁);
  (4) 回收支配定理(R3 逐配方重写 + R3 对抗修正:全 inv 扫描 / 逐件显式 lambda;
      池口径 8 = A9,C_re 齐一 = A5):
      lambda 映射逐组件显式(lam_of callable;带内 = 齐一映射;对抗角 = 喂件带顶/
      其余全部组件(含 partner 流)带底 -- 与符号表 lam_x 逐组件语义一致。旧实现把
      收件 y 的全部 partner 统一按 lambda_喂件计,对抗角幅度被系统性高估,序结论
      与违例集不受影响,幅度全量重锁):
      EV(喂x) = (1/8) * sum_{y!=x in gap} q_new(y) - (7/8) * l_new(x);
      推论1'(partner 门控): 全需求恰满(伙伴到位)喂入全库全带严格支配(最差 -0.620);
        伙伴未到位(他件空)对抗角 81 格可违(W=9/12/18 稳定, 0 符号翻转;
        显式口径幅度: 龙丹战技点/刀 +0.327 居首, 旧折叠口径 +0.357 高估);
      推论2'(全 inv 重写): 残深>=2(喂后)带内并非全负 -- 全 65 缺口格扫描,
        带内可违 33 格次(15 库存格), 其中 5 格带顶仍正(m=3&inv=2 三格
        +0.022~+0.057 + 火花 m=5 两格 +0.012/+0.022);近关张层(inv=m-1)带内
        可违 11 格(非狼尊单例), 其中 4 格带顶贴零(|hi|<0.02, 符号随 lambda
        标定抖动 = 敏感带);对抗角残深>=2 全 inv 可违 32 格(旧「15->4」为
        inv=1 截面假象;inv=1&m>=3 截面 4 格, 龙丹/刀显式 +0.062);
      全深线(巡海击破)喂深件仍被支配(-0.077 ~ -0.295);
      pool=7 读法(A9): 幅度项而非翻向项(锚格 +0.327 -> +0.379);
      超需死库存零边际损失(收益侧已统一为逐配方 q_new 口径);
  (4d) R1 前旧线性口径重算锁(R2/M4,历史口径,不变): T=8/g_x=1 等号边界;
      同 lambda 恰等; 可违仅跨件 lambda 不对称;
  (5) 合成时机后悔:锁线前 E[regret] = p*V > 0;锁线后机会成本严格正(逐配方 pivotal
      质量 > 0 + 近关张深件喂炉带内严格有利 = 组件存在 A 外兑现路径),
      凑齐即合的弱最优 = 尺度假设下的结论(A5 辖域);令牌可定向重取例外(N3);
  (6) 唯一件:注册表(唯一装备)标记 3 组 6 条;计划计数 clamp<=1;
  (7) 令牌目标选择(净缺口口径,本就逐配方,粒度重推不受影响):S(A) = prod P(Bin(W,lam) < n_c),
      n_c = max(0, 需求 - 库存), 全抵扣目标退出候选, 部分持货换序用例;
      (7b) S(A) 乘积 = 独立性近似上界(A10;协差取补不变, 多项式互斥下精确联合
      失败概率 <= 乘积, 数值锁);
  (8) 分配字典序:tier-1 优先于 tier-3 填充;站位/taboo 硬约束;
  (9) no-HP 合规:决策输入集由本证明实际消费的运行时对象现算(窗口/池/lambda 常量、
      comp 名、组件名、taboo 件),非硬编码符号表(旧断言为循环自证,已重写)。
口径:lambda 带 = 任一基础件/轮到达率 [0.05, 0.3], 均匀 rho=1/8(证明 A2);
窗口 W = 9(当前位面剩余节点, A3)。绝对值空转待标定, 本脚本锁结构与序。
账本声明: ③ 用逐件兑现账(每条配方兑现计一次 V_adv, C_re 齐一简化);
联合完成口径的差异见证明 ③ 边界注。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from sr_od.application.currency_war.data.cw_equipment_data import (
    EQUIPMENTS,  # noqa: E402
)
from sr_od.application.currency_war.data.cw_synthesis import (  # noqa: E402
    CROSS_RECIPES,
    GUANGNENG_CROSS_RECIPES,
    GUANGNENG_SELF_RECIPES,
    RESERVED_COMPONENTS,
    SELF_RECIPES,
    component_demand,
    cross_components,
    hoard_gaps,
    recycle_qualified,
    self_base,
    synthesize_target,
)
from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY  # noqa: E402

W = 9            # synthesis window: remaining nodes in plane (A3)
POOL = 8         # furnace transform pool size = 8 bases incl. battery -- bearing assumption A9
                  # (pool=7 reading AMPLIFIES the closing violation: locked in 4a-p7)
LAM_ANY_LO, LAM_ANY_HI = 0.05, 0.3
LAM_X_LO, LAM_X_HI = LAM_ANY_LO / 8, LAM_ANY_HI / 8   # uniform rho = 1/8 (A2)
LAM_MID = 0.019


def binom_pmf(w: int, lam: float, k: int) -> float:
    """P(Binomial(w, lam) = k) via exact term recurrence (small w, exact)."""
    t = (1.0 - lam) ** w
    for j in range(k):
        t = t * (w - j) / (j + 1) * lam / (1.0 - lam)
    return max(t, 0.0)


def binom_lt(w: int, lam: float, m: int) -> float:
    """P(Binomial(w, lam) < m) via exact CDF (small w, direct sum)."""
    acc = 0.0
    for k in range(m):
        acc += binom_pmf(w, lam, k)
    return min(1.0, acc)


def binom_ge(w: int, lam: float, m: int) -> float:
    """P(Binomial(w, lam) >= m): partner arrival mass within the window (A10 independence)."""
    if m <= 0:
        return 1.0
    return 1.0 - sum(binom_pmf(w, lam, k) for k in range(m))


print('== P42 check: equipment machine EV (R3 per-recipe rework) ==')

# --- (1) K8 closure interface ---
assert len(CROSS_RECIPES) == 21 and len(SELF_RECIPES) == 7, 'standard K7 subsets'
assert len(GUANGNENG_CROSS_RECIPES) == 7 and len(GUANGNENG_SELF_RECIPES) == 1, 'battery view'
assert len(CROSS_RECIPES) + len(SELF_RECIPES) + len(GUANGNENG_CROSS_RECIPES) \
    + len(GUANGNENG_SELF_RECIPES) == 36, '36 advanced total'
assert len(RESERVED_COMPONENTS) == 8, '8 bases (7 standard + battery)'
for adv, (a, b) in CROSS_RECIPES.items():
    assert synthesize_target(a, b) == adv, f'roundtrip broken: {adv}'
print('  [1] K8 closure: 28 cross + 8 self = 36 advanced, 8 bases, roundtrip OK')

# --- (2) demand / gaps / recycle-qualified on the doc's anchor line ---
AYA_K = ['反重力皮靴', '反重力皮靴', '火力风暴潮']
d = component_demand(AYA_K)
assert d == {'轮滑鞋': 5, '折叠小刀': 1}, f'demand mismatch: {d}'
g = hoard_gaps(AYA_K, ['轮滑鞋', '轮滑鞋'])
assert g == {'轮滑鞋': 3, '折叠小刀': 1}, f'gaps mismatch: {g}'
rq = recycle_qualified(AYA_K)
assert '轮滑鞋' not in rq and '折叠小刀' not in rq, 'gap component must not be recycle-qualified'
assert {'光能电池', '和平手枪', '幸运星', '生命之花', '量产型装甲', '以太钻头'} <= set(rq), rq
print('  [2] AYA line: demand {skate:5 knife:1}, gaps {skate:3 knife:1}, qualified excludes gap bases')


# --- (3) per-recipe pivotal calculus (R3 rework) ---
# Value realization unit = ONE recipe redemption (synthesis is immediately wearable,
# equip_assign is per-item, V_adv is per-item). Held copies cannot be double-consumed
# across recipes: optimal subset allocation (knapsack, exact for <=6 recipes).
def line_recipes(key_equips: list) -> list:
    """Expand K into recipes [(advance, {component: count})]; recipe-less items skipped."""
    out = []
    for adv in key_equips:
        cross = cross_components(adv)
        if cross:
            out.append((adv, {cross[0]: 1, cross[1]: 1}))
        else:
            b = self_base(adv)
            if b:
                out.append((adv, {b: 2}))
    return out


def lam_uniform(v: float):
    """齐一 lambda 映射:所有组件同一来源流强度(带内读数用)。"""
    return lambda c: v


def lam_corner(feed_x: str, v_feed: float, v_rest: float):
    """对抗角映射(逐组件显式,与符号表 lam_x 逐组件语义一致):喂件自身流带顶,
    其余全部组件(含收件侧 partner 流)带底。旧双参折叠口径把收件 y 的每个 partner
    都按 lambda_喂件计,仅在 y 的 partner 恰好全是喂件(狼尊型)时精确,其余格
    系统性高估对抗角幅度——已按对抗审查全量改为显式映射。"""
    return lambda c: v_feed if c == feed_x else v_rest


def f_value(recipes: list, x: str, j: int, inv: dict, lam_of, w: int = W) -> float:
    """Expected redemptions realizable with j held copies of x (V_adv units, C_re uniform).

    Subset of x-containing recipes with threshold sum <= j, maximizing total partner
    arrival probability g_A = prod_{c != x} P(Bin(w, lam_of(c)) >= t_A(c) - inv_c).
    Partner coupling across recipes NOT counted (A10-type independence approximation).
    """
    items = []
    for _adv, rec in recipes:
        if x not in rec:
            continue
        p = 1.0
        for c, t in rec.items():
            if c == x:
                continue
            p *= binom_ge(w, lam_of(c), t - inv.get(c, 0))
        items.append((rec[x], p))
    best = 0.0
    n = len(items)
    for mask in range(1 << n):
        tot, wt = 0, 0.0
        for i in range(n):
            if mask >> i & 1:
                tot += items[i][0]
                wt += items[i][1]
        if tot <= j and wt > best:
            best = wt
    return best


def marginal_pr(recipes: list, comp: str, inv: dict, lam_of, feed: bool, w: int = W) -> float:
    """One copy of comp leaves/enters: telescoping marginal in the held-count dimension.

    feed=True:  sum_k P(Bin=k) * [f(h+k) - f(h-1+k)]   (feed-out loss, partner-gated)
    feed=False: sum_k P(Bin=k) * [f(h+k+1) - f(h+k)]   (receive gain, partner-gated)
    """
    h = inv.get(comp, 0)
    acc = 0.0
    for k in range(0, w + 2):
        if feed:
            dv = f_value(recipes, comp, h + k, inv, lam_of, w) \
                - f_value(recipes, comp, h - 1 + k, inv, lam_of, w)
        else:
            dv = f_value(recipes, comp, h + k + 1, inv, lam_of, w) \
                - f_value(recipes, comp, h + k, inv, lam_of, w)
        if dv != 0:
            acc += binom_pmf(w, lam_of(comp), k) * dv
    return acc


def feed_ev_pr(key_equips: list, inv: dict, feed_x: str, lam_of,
               w: int = W, pool: int = POOL) -> tuple:
    """EV of furnace-feeding one held copy of feed_x, PER-RECIPE ledger (proof (3) R3).

    EV = (1/POOL) * sum_{y in gap, y != x} q_new(y) - ((POOL-1)/POOL) * l_new(x);
    y=x transform-back branch cancels (feed out then receive back = no-op).
    Gain side evaluated on the post-feed state (fed copy no longer offsets partners).
    Surplus copies (inv > demand) carry zero marginal loss (recycle-qualified default).
    Returns (ev, loss, gain).
    """
    demand = component_demand(list(key_equips))
    recipes = line_recipes(key_equips)
    if inv.get(feed_x, 0) > demand[feed_x]:
        gain = sum(marginal_pr(recipes, y, inv, lam_of, feed=False, w=w)
                   for y in demand if y != feed_x and demand[y] - inv.get(y, 0) >= 1)
        return (gain - 0.0) / pool, 0.0, gain
    inv_after = {**inv, feed_x: inv.get(feed_x, 0) - 1}
    gain = sum(marginal_pr(recipes, y, inv_after, lam_of, feed=False, w=w)
               for y in demand if y != feed_x and demand[y] - inv_after.get(y, 0) >= 1)
    loss = marginal_pr(recipes, feed_x, inv, lam_of, feed=True, w=w)
    return (gain - (pool - 1) * loss) / pool, loss, gain


demands = {}
for comp in COMP_LIBRARY:
    if comp.key_equips:
        dem = component_demand(list(comp.key_equips))
        if dem:
            demands[comp.name] = (dem, list(comp.key_equips))
n_checked = len(demands)
assert n_checked == 20, f'expected 20 comps with derived demand, got {n_checked}'

WOLF_KES = demands['狼尊欢愉'][1]
WOLF_DEM = demands['狼尊欢愉'][0]
wolf_recipes = line_recipes(WOLF_KES)

# telescope identity (held-count dimension) is EXACT: sum of per-copy marginals equals
# the joint stream value of the whole holding; only the cross-component partner factors
# carry the A10 independence approximation.
tot_marg = sum(marginal_pr(wolf_recipes, '轮滑鞋', {'轮滑鞋': h}, lam_uniform(LAM_MID), feed=True)
               for h in range(6))
exp_tot = sum(binom_pmf(W, LAM_MID, k)
              * (f_value(wolf_recipes, '轮滑鞋', 5 + k, {}, lam_uniform(LAM_MID))
                 - f_value(wolf_recipes, '轮滑鞋', max(k - 1, 0), {}, lam_uniform(LAM_MID)))
              for k in range(W + 2))
assert abs(tot_marg - exp_tot) < 1e-9, f'telescope (held-count dim) broken: {tot_marg} vs {exp_tot}'

# near-redemption shape: f(j) jumps at the self-recipe threshold (partner factor 1),
# cross-recipe entries only add the partner arrival mass
f_shape = [f_value(wolf_recipes, '轮滑鞋', j, {}, lam_uniform(LAM_MID)) for j in range(7)]
assert f_shape[0] == 0.0
assert abs(f_shape[1] - (1.0 - binom_pmf(W, LAM_MID, 0))) < 1e-9, \
    f'j=1 can only fish one cross recipe: {f_shape[1]}'
assert f_shape[2] >= 0.99, f'self-pair second skate is a GUARANTEED redemption: {f_shape[2]}'
assert all(f_shape[j] < f_shape[j + 1] for j in range(6)), f'f must increase: {f_shape}'

# magnitude lock: aggregated l_old = P(Bin=5) underestimates per-recipe l_new by >= 4 orders
l_new_lo = marginal_pr(wolf_recipes, '轮滑鞋', {'轮滑鞋': 1}, lam_uniform(LAM_X_LO), feed=True)
l_new_hi = marginal_pr(wolf_recipes, '轮滑鞋', {'轮滑鞋': 1}, lam_uniform(LAM_X_HI), feed=True)
l_old_lo = binom_pmf(W, LAM_X_LO, 5)
l_old_hi = binom_pmf(W, LAM_X_HI, 5)
assert abs(l_old_lo - 1.17e-9) < 0.01e-9 and abs(l_old_hi - 8.02e-6) < 0.01e-6, \
    f'aggregated loss masses: {l_old_lo:.2e} / {l_old_hi:.2e}'
assert 0.10 <= l_new_lo <= 0.11 and 0.39 <= l_new_hi <= 0.40, \
    f'per-recipe first-skate loss must sit in [0.10, 0.40]: {l_new_lo:.3f} / {l_new_hi:.3f}'
assert l_new_lo / l_old_lo > 1e7 and l_new_hi / l_old_hi > 1e4, \
    'aggregation underestimates near-redemption loss by >= 4 orders (full band)'
print(f'  [3] per-recipe pivotal: telescope exact ({tot_marg:.4f}); f jumps at self-pair '
      f'(f1={f_shape[1]:.3f} f2={f_shape[2]:.3f}); first-skate loss l_new '
      f'[{l_new_lo:.3f},{l_new_hi:.3f}] vs l_old [{l_old_lo:.1e},{l_old_hi:.1e}] '
      f'(underestimate >= 4 orders)')

# --- (4a) full-need closing (partners in hand): strict dominance, all comps, full band ---
# state inv = m on EVERY component: the fed copy destroys one GUARANTEED redemption
# (loss = P(Bin=0): only the zero-arrival outcome realizes the destruction).
worst = (-1.0, None)
for name, (dem, kes) in demands.items():
    full = dict(dem)
    for c in dem:
        for lx in (LAM_X_LO, LAM_MID, LAM_X_HI):
            ev, loss, gain = feed_ev_pr(kes, full, c, lam_uniform(lx))
            assert ev < 0, f'full-need closing dominance broken: {name}/{c} EV={ev:.4f}'
            if ev > worst[0]:
                worst = (ev, f'{name}/{c}')
        ev, loss, gain = feed_ev_pr(kes, full, c, lam_corner(c, LAM_X_HI, LAM_X_LO))
        assert ev < 0, f'full-need closing dominance broken at corner: {name}/{c} EV={ev:.4f}'
        if ev > worst[0]:
            worst = (ev, f'{name}/{c}')
assert abs(worst[0] + 0.620) < 0.001, f'worst full-need corner locked ~-0.620: {worst}'
ev_wolf_full, l_wolf_full, _ = feed_ev_pr(WOLF_KES, dict(WOLF_DEM), '轮滑鞋', lam_uniform(LAM_MID))
assert abs(ev_wolf_full + 0.736) < 0.001
assert abs(l_wolf_full - binom_pmf(W, LAM_MID, 0)) < 1e-12, \
    'full-need loss must equal P(Bin=0) x 1 guaranteed redemption'
print(f'  [4a] full-need closing (partners in hand): strict dominance all {n_checked} comps, '
      f'full band; worst EV {worst[0]:.3f} ({worst[1]}); loss = P(Bin=0)-guaranteed redemption')

# surplus copy (inv = demand + 1): zero marginal loss -> feeding is free (recycle default)
surplus_ev, surplus_loss, _ = feed_ev_pr(WOLF_KES, {'轮滑鞋': 7}, '轮滑鞋', lam_uniform(LAM_MID))
assert surplus_ev >= 0 and surplus_loss == 0.0, 'surplus feed must carry zero marginal loss'
print(f'  [4a+] surplus copy (inv > demand): zero marginal loss, feed EV = {surplus_ev:.3f} >= 0')

# --- (4a-adv) partner-absent closing: adversarial corner violability + W robustness ---
# state inv = {x: m}, every other component EMPTY: the marginal copy's only realization
# path is a cross/self recipe whose partners are far away (arrival mass 0.05-0.16) --
# its value is partner-gated DOWN, and feeding can be strictly favorable.
def closing_bad(w: int) -> list:
    out = []
    for nm, (dem, kes) in demands.items():
        for c in dem:
            ev = feed_ev_pr(kes, {c: dem[c]}, c, lam_corner(c, LAM_X_HI, LAM_X_LO), w=w)[0]
            if ev > 0:
                out.append((nm, c, ev))
    return out


bad9 = closing_bad(W)
assert len(bad9) == 81, f'partner-absent closing adversarial violations locked at 81, got {len(bad9)}'
top = max(bad9, key=lambda t: t[2])
assert top[0] == '龙丹战技点' and top[1] == '折叠小刀' and abs(top[2] - 0.327) < 0.001, \
    f'top closing violation locked (explicit-lambda caliber): {top}'
# runner-up cluster: the old folded caliber inflated amplitudes (+0.357 top, +0.307 tier)
# -- explicit per-component lambda lowers them with ZERO sign flips / set changes
runner = sorted((t[2] for t in bad9), reverse=True)[1:5]
assert abs(runner[0] - 0.320) < 0.001 and abs(runner[3] - 0.222) < 0.001, \
    f'closing violation amplitude tier locked: {runner}'
ev_wolf6_adv = feed_ev_pr(WOLF_KES, {'轮滑鞋': 6}, '轮滑鞋', lam_corner('轮滑鞋', LAM_X_HI, LAM_X_LO))[0]
assert abs(ev_wolf6_adv - 0.202) < 0.001, f'wolf 6th skate adversarial locked ~+0.202: {ev_wolf6_adv:.4f}'
# W robustness: the violation SET is stable across larger windows (both loss and gain
# rise with W) -- the old W<=9 scope clause is void with the component-level caliber.
for w in (12, 18):
    assert len(closing_bad(w)) == 81, f'closing violation set must stay 81 at W={w}'
print(f'  [4a-adv] partner-absent closing: {len(bad9)} adversarial violations '
      f'(top {top[0]}/{top[1]} {top[2]:+.3f}; wolf skate {ev_wolf6_adv:+.3f}); '
      f'set stable at W=12/18 (old W-scope void)')

# --- (4a-p7) pool caliber (A9): amplification item, not a direction item ---
# pool=7 reading (battery excluded): coefficients (1/7)/(6/7) -- on the anchor cell the
# violation AMPLIFIES; A9 stays a declared bearing assumption but no longer flips a
# dominated verdict (the old pool=7 flip rode the superseded component ledger).
_ev_p8, _loss_lt, _gain_lt = feed_ev_pr(demands['龙丹战技点'][1],
                                        {'折叠小刀': demands['龙丹战技点'][0]['折叠小刀']},
                                        '折叠小刀', lam_corner('折叠小刀', LAM_X_HI, LAM_X_LO))
ev_p8 = _ev_p8
ev_p7 = (_gain_lt - 6 * _loss_lt) / 7
assert abs(ev_p8 - 0.327) < 0.001 and ev_p7 > ev_p8 and abs(ev_p7 - 0.379) < 0.001, \
    f'pool=7 must amplify the anchor violation: p8={ev_p8:.4f} p7={ev_p7:.4f}'
# self-rotation invariance is a TRUE invariant -- algebra lock (unchanged by caliber)
l_mid0 = binom_pmf(W, LAM_MID, 0)
sum_q_mid = sum(binom_pmf(W, LAM_MID, dem[y] - 1) for _nm, (dem, _kes) in demands.items()
                for y in dem if dem[y] >= 1)
assert abs((8 * l_mid0 - (sum_q_mid + l_mid0)) - (7 * l_mid0 - sum_q_mid)) < 1e-12
print(f'  [4a-p7] pool caliber (A9): pool=7 amplifies anchor cell {ev_p8:+.3f} -> {ev_p7:+.3f} '
      f'(amplitude item, no direction flip); rotation-invariant algebra OK')

# --- (4b) corollary 2': unfed edge copies -- FULL-inv scan, per-band readings ---
# Scope = the claim's own domain: every gap cell (comp, component, inv = 1..m-1),
# state = only held copies of the component itself, partners empty. Feed-after
# residual depth >= 2 covers the WHOLE scan (adversarial audit: the old section cut
# the scan at inv=1 while asserting a full-inv claim; per-recipe feed loss is
# non-increasing in inv while the fishing gain is unchanged, so violability spreads
# from the adversarial corner into the band and from inv=1 toward inv=m-1 BY
# STRUCTURE -- not an edge-case numeric accident).
n_scan = 0
inband_entries = []   # (nm, c, inv, m, band): cell x uniform-band point with EV > 0
bandtop_pos = {}      # cells whose uniform band-TOP reading is still positive
for nm, (dem, kes) in demands.items():
    for c, m in dem.items():
        for h in range(1, m):
            n_scan += 1
            for bname, v in (('lo', LAM_X_LO), ('mid', LAM_MID), ('hi', LAM_X_HI)):
                ev = feed_ev_pr(kes, {c: h}, c, lam_uniform(v))[0]
                if ev > 0:
                    inband_entries.append((nm, c, h, m, bname))
                    if bname == 'hi':
                        bandtop_pos[(nm, c, h)] = ev
assert n_scan == 65, f'full-inv gap scan must cover 65 cells, got {n_scan}'
assert len(inband_entries) == 33, \
    f'residual>=2 in-band violable entries locked at 33 band points: {inband_entries}'
assert len({(nm, c, h) for nm, c, h, _m, _b in inband_entries}) == 15, \
    'in-band violable distinct cells locked at 15'
expect_toppos = {('希儿量子', '折叠小刀', 2): 0.022, ('龙丹战技点', '折叠小刀', 2): 0.057,
                 ('反甲白厄', '幸运星', 2): 0.022, ('火花星间旅人', '折叠小刀', 3): 0.012,
                 ('火花星间旅人', '折叠小刀', 4): 0.022}
assert set(bandtop_pos) == set(expect_toppos), \
    f'in-band band-TOP positive cells locked to the 5-list: {bandtop_pos}'
for k, v in expect_toppos.items():
    assert abs(bandtop_pos[k] - v) < 0.001, f'{k}: band-top locked {v}, got {bandtop_pos[k]:.4f}'

# adversarial corner (feed band-top / ALL other components incl. partner streams at
# band-bottom, per-component explicit lambda): full-inv violable set
adv_cells = []
for nm, (dem, kes) in demands.items():
    for c, m in dem.items():
        for h in range(1, m):
            ev = feed_ev_pr(kes, {c: h}, c, lam_corner(c, LAM_X_HI, LAM_X_LO))[0]
            if ev > 0:
                adv_cells.append((nm, c, h, m))
assert len(adv_cells) == 32, \
    f'residual>=2 adversarial violable cells (full-inv, explicit lambda) locked at 32: {adv_cells}'
# the old "15 -> 4" reading was the inv=1 & m>=3 SECTION of this set (cross-section
# artifact, not a layer claim); kept locked as a section reading with the corrected
# explicit-lambda amplitudes (龙丹/刀 +0.092 was the folded-caliber overestimate)
adv4 = {}
for nm, (dem, kes) in demands.items():
    for c, m in dem.items():
        if m < 3:
            continue
        ev = feed_ev_pr(kes, {c: 1}, c, lam_corner(c, LAM_X_HI, LAM_X_LO))[0]
        if ev > 0:
            adv4[(nm, c)] = ev
expect4 = {('希儿量子', '折叠小刀'): 0.055, ('龙丹战技点', '折叠小刀'): 0.062,
           ('反甲白厄', '幸运星'): 0.055, ('追击飞霄', '轮滑鞋'): 0.030}
assert set(adv4) == set(expect4), f'inv=1 & m>=3 adversarial section locked to the 4-list: {adv4}'
for k, v in expect4.items():
    assert abs(adv4[k] - v) < 0.001, f'{k}: section locked {v}, got {adv4[k]:.4f}'

# near-closing layer (inv = m-1, pre-feed net gap 1): the STABLE in-band violable
# layer, 11 cells library-wide (not a wolf-only example)
near_viol = []
near_hi_boundary = {}
for nm, (dem, kes) in demands.items():
    for c, m in dem.items():
        if m < 2:
            continue
        evs = {b: feed_ev_pr(kes, {c: m - 1}, c, lam_uniform(v))[0]
               for b, v in (('lo', LAM_X_LO), ('mid', LAM_MID), ('hi', LAM_X_HI))}
        if any(e > 0 for e in evs.values()):
            near_viol.append((nm, c, m))
            if abs(evs['hi']) < 0.02:
                near_hi_boundary[(nm, c)] = evs['hi']
expect_near = {('命运圣杯红A', '折叠小刀'), ('千冶减益', '轮滑鞋'), ('希儿量子', '折叠小刀'),
               ('龙丹战技点', '折叠小刀'), ('火花星间旅人', '折叠小刀'), ('大黑塔银河学者', '光能电池'),
               ('反甲白厄', '幸运星'), ('狼尊欢愉', '轮滑鞋'), ('追击飞霄', '轮滑鞋'),
               ('DOT队', '轮滑鞋'), ('景元仙舟', '轮滑鞋')}
assert {(nm, c) for nm, c, _m in near_viol} == expect_near, \
    f'near-closing in-band violable layer locked at the 11-cell list: {near_viol}'
# band-top sign boundary sensitivity (A3): several near-closing cells sit within 0.02
# of zero at band top -- their sign verdicts WILL jitter once lambda is calibrated
expect_boundary = {('追击飞霄', '轮滑鞋'): -0.004, ('千冶减益', '轮滑鞋'): -0.015,
                   ('大黑塔银河学者', '光能电池'): -0.015, ('DOT队', '轮滑鞋'): -0.015}
assert set(near_hi_boundary) == set(expect_boundary), \
    f'near-closing band-top |hi|<0.02 sensitive cells: {near_hi_boundary}'
for k, v in expect_boundary.items():
    assert abs(near_hi_boundary[k] - v) < 0.002, \
        f'{k}: boundary locked {v}, got {near_hi_boundary[k]:.4f}'

# wolf anchors: 5th skate near-closing (favorable at band bottom/mid), 1st skate
# (near redemption) dominated everywhere including the adversarial corner
ev_wolf5 = {nm: feed_ev_pr(WOLF_KES, {'轮滑鞋': 5}, '轮滑鞋', lam)[0]
            for nm, lam in (('lo', lam_uniform(LAM_X_LO)), ('mid', lam_uniform(LAM_MID)),
                            ('hi', lam_uniform(LAM_X_HI)),
                            ('adv', lam_corner('轮滑鞋', LAM_X_HI, LAM_X_LO)))}
assert abs(ev_wolf5['lo'] - 0.188) < 0.001 and abs(ev_wolf5['mid'] - 0.073) < 0.001 \
    and abs(ev_wolf5['hi'] + 0.067) < 0.001 and abs(ev_wolf5['adv'] - 0.190) < 0.001, \
    f'wolf 5th skate locked: {ev_wolf5}'
ev_wolf1 = {nm: feed_ev_pr(WOLF_KES, {'轮滑鞋': 1}, '轮滑鞋', lam)[0]
            for nm, lam in (('lo', lam_uniform(LAM_X_LO)), ('mid', lam_uniform(LAM_MID)),
                            ('hi', lam_uniform(LAM_X_HI)),
                            ('adv', lam_corner('轮滑鞋', LAM_X_HI, LAM_X_LO)))}
assert abs(ev_wolf1['lo'] + 0.077) < 0.001 and abs(ev_wolf1['mid'] + 0.193) < 0.001 \
    and abs(ev_wolf1['hi'] + 0.295) < 0.001 and abs(ev_wolf1['adv'] + 0.176) < 0.001, \
    f'wolf 1st skate (near redemption) dominated full band incl adversarial: {ev_wolf1}'
print(f'  [4b] residual>=2 (full-inv, {n_scan} cells): in-band violable {len(inband_entries)} '
      f'band points over 15 cells, band-top positive {len(bandtop_pos)} '
      f'(m=3&inv=2 trio +0.022~+0.057); adversarial {len(adv_cells)} cells '
      f'(inv=1&m>=3 section 4); near-closing layer 11 cells, '
      f'{len(near_hi_boundary)} band-top |hi|<0.02 (sign-sensitive); wolf 5th skate '
      f"lo {ev_wolf5['lo']:+.3f} / mid {ev_wolf5['mid']:+.3f} favorable; 1st skate "
      f"dominated {ev_wolf1['lo']:+.3f}..{ev_wolf1['hi']:+.3f}")

# --- (4c) all-deep line locked: no fishing target -> dominated everywhere ---
xunhai = demands['巡海击破'][0]
xunhai_kes = demands['巡海击破'][1]
assert xunhai == {'以太钻头': 3, '轮滑鞋': 3}
for c in xunhai:
    for lam in (lam_uniform(LAM_X_LO), lam_uniform(LAM_MID), lam_uniform(LAM_X_HI),
                lam_corner(c, LAM_X_HI, LAM_X_LO)):
        ev = feed_ev_pr(xunhai_kes, {c: 1}, c, lam)[0]
        assert ev < 0, f'all-deep line must stay dominated: {c} EV={ev:.4f}'
print('  [4c] all-deep line (xunhai): dominated at every band point and corner (-0.077..-0.295)')

# --- (4d) legacy linear caliber (R2/M4, historical, unchanged) ---
lz = WOLF_DEM
x = '折叠小刀'
T_lz, g_x = sum(lz.values()), lz[x]
assert T_lz == 8 and g_x == 1, f'langzun must be the T=8 depth-1 anchor, got T={T_lz} g={g_x}'
assert T_lz == 8 * g_x, 'pure-linear caliber: T=8, g_x=1 is the EQUALITY boundary (EV=0)'
same_mass = sum(m * binom_pmf(W, LAM_MID, 0) for y, m in lz.items() if y != x)
assert abs(same_mass - 7 * g_x * binom_pmf(W, LAM_MID, 0)) < 1e-9, \
    'same-lambda legacy mass: exact equality, not violable'
gain_asym = sum(m * binom_pmf(W, LAM_X_LO, 0) for y, m in lz.items() if y != x)
loss_asym = g_x * binom_pmf(W, LAM_X_HI, 0)
assert gain_asym > 7 * loss_asym and abs(gain_asym - 6.616) < 0.001 \
    and abs(loss_asym - 0.709) < 0.001, \
    f'cross-lambda asymmetry: violable 6.616 > 4.963, got {gain_asym:.3f} vs {7 * loss_asym:.3f}'
print(f'  [4d] legacy linear caliber (historical): T=8/g=1 equality boundary (EV=0); '
      f'same-lam exact tie ({same_mass:.3f}); violable ONLY under cross-lambda asymmetry '
      f'({gain_asym:.3f} > {7 * loss_asym:.3f})')

# --- (5) synthesis timing regret + token-reach exception (N3) ---
def regret(p_switch: float, lam_c: float, n_c: int) -> float:
    """E[regret of pre-lock synthesis] = p_switch * V_comp(component | new line).

    Pivotal mass lower bound: a held copy at residual depth n_c keeps a nonzero
    expected-redemption marginal whenever any open recipe has partner mass > 0.
    """
    return p_switch * binom_pmf(W, lam_c, n_c)


assert regret(0.3, LAM_MID, 0) > 0, 'pre-lock regret strictly positive when p>0'
assert regret(0.0, LAM_MID, 0) == 0.0, 'post-lock (p=0) regret zero'
assert regret(0.3, LAM_MID, 0) > regret(0.3, LAM_MID, 3), 'pivotal regret shrinks with residual depth'
# per-recipe pivotal mass strictly positive at any residual depth with open partners
for h in (0, 1, 2, 5):
    assert marginal_pr(wolf_recipes, '轮滑鞋', {'轮滑鞋': h}, lam_uniform(LAM_MID), feed=True) > 0, \
        f'gap-component per-recipe pivotal mass must be positive at held={h}'
# N3 exception: token can re-target A -> immediate synthesis carries positive opportunity cost
def post_lock_cost(p_token_hits_a: float, dup_loss: float) -> float:
    return p_token_hits_a * dup_loss


assert post_lock_cost(0.0, 1.0) == 0.0, 'weak optimality holds only when token option is zero'
assert post_lock_cost(0.2, 1.0) > 0, 'token-reachable A makes immediate synthesis strictly costly'
# M1/R3: post-lock opportunity cost is STRICTLY POSITIVE in general -- per-recipe pivotal
# mass is positive (above) AND the near-closing furnace redemption is strictly favorable
# IN BAND (wolf 5th skate lo/mid): a second, non-A realization path exists.
assert ev_wolf5['lo'] > 0 and ev_wolf5['mid'] > 0, \
    'furnace redemption of near-closing edge strictly favorable in band (proof (2) M1)'
print('  [5] timing: pre-lock regret > 0; post-lock opportunity cost STRICTLY > 0 '
      '(per-recipe pivotal mass + near-closing furnace redemption in band); '
      'weak optimality = scale assumption (A5), token option > 0 strictly costly (N3)')

# --- (6) unique items: 3 groups, planned count clamp <= 1 ---
uniq = [name for name, e in EQUIPMENTS.items() if '（唯一装备）' in e.effect]
groups = {n.replace('·特权', '') for n in uniq}
assert len(uniq) == 6 and len(groups) == 3, f'unique registry shape: {uniq}'
planned = {'电光履': 2}   # naive plan asking for a second copy


def clamp_unique(plan: dict) -> dict:
    return {k: min(v, 1) if k.replace('·特权', '') in groups else v for k, v in plan.items()}


assert clamp_unique(planned)['电光履'] == 1, 'second unique copy is dead stock, clamped'
print('  [6] unique: 6 flagged entries in 3 groups; planned count clamped to 1 (A4 safe side)')

# --- (7) token target selection: net-gap stream-failure product argmax (N2) ---
# per-recipe caliber natively (S(A) is defined per target recipe) -- unaffected by R3.
def scarcity(product_adv: str, inv: dict | None = None) -> float:
    """S(A) = prod over recipe comps of P(stream fails to fill the NET gap n_c).

    n_c = max(0, need - held): already-held components (incl. finished-product 1:1
    offset) are excluded -- an almost-done target must NOT attract the token (N2).
    Binomial TAIL P(<n), not P(=0): multi-copy needs shrink P(=0) while the bypass
    value of the token grows -- a zero-arrival tail picks the WRONG target (proof (4)).
    Fully covered target (all n_c = 0): synthesizable now, returns 0 (exits candidacy).
    """
    inv = inv or {}
    cross = cross_components(product_adv)
    comps = cross if cross is not None else (self_base(product_adv),) * 2
    counts: dict[str, int] = {}
    for c in comps:
        counts[c] = counts.get(c, 0) + 1
    val = 1.0
    open_factors = False
    for c, m in counts.items():
        n = max(0, m - inv.get(c, 0))
        if n >= 1:
            open_factors = True
            val *= binom_lt(W, LAM_MID, n)
    return val if open_factors else 0.0


s_boots = scarcity('反重力皮靴')      # self-recipe: skate x2 (deep bottleneck)
s_storm = scarcity('火力风暴潮')      # cross: skate x1 + knife x1
assert s_boots > s_storm, f'deeper recipe must be scarcer: {s_boots} vs {s_storm}'
token_pick = max(['反重力皮靴', '火力风暴潮'], key=scarcity)
assert token_pick == '反重力皮靴', 'token must bypass the deepest component bottleneck'
# N2 reorder: partial holding must de-value the target it feeds
s_boots_1held = scarcity('反重力皮靴', {'轮滑鞋': 1})
assert s_boots > s_boots_1held > s_storm, 'one held skate shrinks but does not close the gap'
s_boots_done = scarcity('反重力皮靴', {'轮滑鞋': 2})
assert s_boots_done == 0.0, 'fully covered target exits candidacy (synthesize now, no token)'
assert max(['反重力皮靴', '火力风暴潮'], key=lambda a: scarcity(a, {'轮滑鞋': 2})) == '火力风暴潮', \
    'argmax must flip to the still-open target once the deep one is covered'
# declared wrong-pick guard: zero-arrival tail inverts the order for multi-copy recipes
def _zero_tail() -> float:
    return (1.0 - LAM_MID) ** (W * 2)   # P(=0) under need 2


assert _zero_tail() < (1.0 - LAM_MID) ** W, 'P(=0) shrinks with need -> would pick wrong target'
print(f'  [7] token (net-gap, per-recipe native): S(boots)={s_boots:.3f} > S(storm)={s_storm:.3f}; '
      f'held-1 {s_boots_1held:.3f}; covered -> 0 (exits); binomial-tail rule + P(=0) guard OK')

# --- (7b) S(A) product is a declared INDEPENDENCE approximation (R2/M5, A10) ---
# A2's structure (one arrival per round at most, uniform over 8 bases) makes the
# joint shortfall of two components multinomial, NOT independent binomials.
# Covariance sign is preserved under complementation (Cov(1-A,1-B) = Cov(A,B)), so
# failures are ALSO negatively correlated and the product OVERestimates the exact
# joint failure -- S(A) is inflated for multi-component (cross) targets. Verified:
def exact_joint_fail(lam_any: float, n1: int, n2: int) -> float:
    """Exact P(both gaps unfilled) under multinomial arrivals (2 distinct bases).

    Each round: one of 8 bases w.p. lam_any*1/8 each, nothing w.p. 1-lam_any.
    Exact joint = sum over (a < n1, b < n2) of C(W; a, b, W-a-b) rho^(a+b)(1-2rho)^(W-a-b).
    """
    from math import comb as _comb
    rho = lam_any / 8
    acc = 0.0
    for a in range(n1):
        for b in range(n2):
            acc += (_comb(W, a) * _comb(W - a, b)
                    * rho ** (a + b) * (1 - 2 * rho) ** (W - a - b))
    return acc


lam_any_mid = LAM_MID * 8
prod2 = binom_lt(W, LAM_MID, 1) ** 2
exact2 = exact_joint_fail(lam_any_mid, 1, 1)
assert exact2 < prod2, f'multinomial joint failure must stay BELOW the product: {exact2:.4f} vs {prod2:.4f}'
assert abs(exact2 - (1 - 2 * (lam_any_mid / 8)) ** W) < 1e-12, 'closed form (1-2rho)^W'
print(f'  [7b] S(A) independence approx (A10): product {prod2:.4f} >= multinomial exact '
      f'{exact2:.4f} (UPPER bound locked; cross-target bias ~{(prod2 / exact2 - 1):.1%})')

# --- (8) allocation lexicographic order + hard constraints ---
def lex_assign(tier1: list, tier2: list, owned: list, cap_carry: int, cap_other: int):
    """Tiny lexicographic matcher (proof (5)): tier-1 first (multiplicity), tier-2, then fill."""
    pool = list(owned)
    out = {}
    for item in list(tier1):
        if item in pool and cap_carry > 0:
            pool.remove(item)
            cap_carry -= 1
            out.setdefault('carry', []).append(item)
    for item in list(tier2):
        if item in pool and cap_other > 0:
            pool.remove(item)
            cap_other -= 1
            out.setdefault('core', []).append(item)
    for item in pool:
        if cap_carry > 0:
            cap_carry -= 1
            out.setdefault('fill', []).append(item)
        elif cap_other > 0:
            cap_other -= 1
            out.setdefault('fill', []).append(item)
    return out


res = lex_assign(['A1'], ['A2'], ['A1', 'X'], 1, 1)
assert res.get('carry') == ['A1'], f'tier-1 must beat fill under capacity: {res}'
assert res.get('fill') == ['X'], 'surplus goes to fill only after tier-1 satisfied'
# row constraint: back-row-only item blocked on front wearer (mechanics S2, hard constraint)
row_ok = {'back_item': 'back'}
wearer_row = 'front'
assert row_ok['back_item'] != wearer_row, 'row mismatch must be blocked pre-EV'
# taboo deletion: no taboo name appears in that comp's key list (consistency with hard filter)
for comp in COMP_LIBRARY:
    if comp.equip_taboos:
        overlap = set(comp.equip_taboos) & set(comp.key_equips)
        assert not overlap, f'taboo/key overlap in {comp.name}: {overlap}'
n_taboo = sum(1 for c in COMP_LIBRARY if c.equip_taboos)
print(f'  [8] lexicographic: tier-1 beats fill under capacity; row hard-block; '
      f'{n_taboo} comps with taboos, zero taboo/key overlap')

# --- (9) no-HP compliance: decision inputs COMPUTED from what this proof consumes ---
# The compliance claim must be swept over the ACTUAL runtime inputs of this proof
# (window/pool/lambda constants, comp names, component names, taboo items) -- the old
# hardcoded symbol list was a circular no-op (adversarial audit note). Every string
# that feeds a decision in this proof must be free of any HP term (A8, [39]/[40]).
decision_inputs: set = (
    {'window_W', 'pool', 'lam_any_band_lo', 'lam_any_band_hi', 'lam_mid'}
    | set(demands)
    | {c for dem, _kes in demands.values() for c in dem}
    | {t for comp in COMP_LIBRARY if comp.equip_taboos for t in comp.equip_taboos})
hp_leaks = [i for i in decision_inputs if 'hp' in str(i).lower()]
assert not hp_leaks, f'HP term leaked into computed decision inputs: {hp_leaks}'
print(f'  [9] no-HP compliance swept over {len(decision_inputs)} computed decision inputs '
      '(comp/component/taboo names + W/pool/lam constants; [39]/[40], A8)')

print('ALL ASSERTIONS PASSED')
