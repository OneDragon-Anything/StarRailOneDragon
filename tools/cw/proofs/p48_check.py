"""P48 数值自检:经验整买纪律与超息线囤钱(口述 [41] 的数学化)。

重跑:PYTHONPATH=src uv run python tools/cw/proofs/p48_check.py
数据源(不 import,值按代码注册表/证明件转写,本脚本自含以便离线审阅):
  - XP 机制:单击 +4 经验/4 金(XP_PER_BUY,ADR-0275 flat 三帧);等级门槛
    XP_TO_NEXT_LEVEL = {3:4, 4:6, 5:20, 6:40, 7:52, 8:72, 9:84}(cw_state,economy.md
    §9 粗估 ±20%);买牌同源 +4 经验/张(sim engine_p1,ADR-0286)。
  - 利息 interest(g) = min(g//10, 5),50 封顶(cw_plane_table,p47 A1)。
  - 净收入率 I 带 [6,9](p47 A3 同源;胜轮 5+连胜金)。
  - p39 移位价值示例:4费2星 L7->L8 ΔV_band=103.3;4费2星 L8->L9 ΔV=23.0;
    4费2星 L6->L7 ΔV=28.4(< U=40,门不过例);5费2星 L8->L9 ΔV=282.7
    (p39 数值表,REFRESH_PROB 复算)。

四段自检(对应证明 p48 的命题 1/3/2/4):
  1) 整买 vs 零散的机会成本(零散买的死库存金 x 轮数的息损账);
  2) 囤钱汇率判据(有/无正 EV 边际动作两态 + 门未过时 rho=0);
  3) 目标线 S 的动态轨迹(含自然 XP 抵扣,S 单调不增);
  4) 双目标排队(每金价值率序 vs 裸每轮价值率序的对拍)。
print 全 ASCII(>= / ->,无特殊符号,防 GBK 控制台炸)。
"""
from __future__ import annotations

GOLD_CAP = 50          # 息封顶金位(满息 5/轮;p47 A1)
INTEREST_CAP = 5
XP_PER_BUY = 4         # 单击经验量与单击金成本(cw_state,flat)
XP_TO_NEXT_LEVEL = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}


def interest(g: int) -> int:
    """利息 = min(g//10, 5);g<0 按 0 计。"""
    return min(max(g, 0) // 10, INTEREST_CAP)


def clicks_needed(level: int, xp_cur: int) -> int:
    """当前级攒到恰升 1 级所需最少单击数 = ceil((need - xp)/4)(cw_state.xp_clicks_to_level 同构)。"""
    if level >= 10:
        return 0
    need = XP_TO_NEXT_LEVEL.get(level, 4)
    gap = need - xp_cur
    if gap <= 0:
        return 1
    return (gap + XP_PER_BUY - 1) // XP_PER_BUY


def batch_cost(level: int, xp_cur: int, nat_xp: int = 0) -> int:
    """批成本 B = 4 * clicks(need - xp_cur - 期望自然 XP)(自然 XP 抵扣,p48 A3)。"""
    if level >= 10:
        return 0
    need = XP_TO_NEXT_LEVEL.get(level, 4)
    gap = max(0, need - xp_cur - nat_xp)
    return XP_PER_BUY * ((gap + XP_PER_BUY - 1) // XP_PER_BUY)


# ------------------------------------------------------------------ 单轮演化

def round_step(g: int, total_int: int, inc: int, spend: int) -> tuple[int, int]:
    """统一单轮演化:轮初计息 -> 备战期花金 -> 结算收入(p47 A2 轮初口径)。

    返回 (新金, 累计息)。所有策略模拟共用本步,保证对拍口径一致。
    """
    i = interest(g)
    return max(0, g - spend) + inc + i, total_int + i


def sim_dribble(g0: int, level: int, inc: int,
                clicks_per_round: int = 1, max_rounds: int = 30
                ) -> tuple[int, int, int]:
    """零散策略:每轮买 clicks_per_round 次经验(不等批)。

    返回 (升级轮, 升级时金, 累计息)。
    """
    g, total_int = g0, 0
    k_star = clicks_needed(level, 0)
    bought = 0
    for r in range(1, max_rounds + 1):
        n = min(clicks_per_round, k_star - bought)
        bought += n
        g, total_int = round_step(g, total_int, inc, n * XP_PER_BUY)
        if bought >= k_star:
            return r, g, total_int
    return -1, g, total_int


def sim_defer(g0: int, level: int, inc: int, t_buy: int) -> tuple[int, int, int]:
    """延迟对照:同样在第 t_buy 轮升级,但 t_buy 前持金不买,t_buy 轮一次性买齐。

    与 sim_dribble 同轮对拍:两者 XP 总投入相同(4*k* 金),差 = 零散买把金
    提前变成零收益 XP 后,金位轨迹被压低所损失的息与金(p47 轨迹占优:
    持金轨迹逐轮 >= 花后轨迹)。返回 (升级轮, 升级时金, 累计息)。
    """
    g, total_int = g0, 0
    k_star = clicks_needed(level, 0)
    for _ in range(1, t_buy):
        g, total_int = round_step(g, total_int, inc, 0)
    g, total_int = round_step(g, total_int, inc, k_star * XP_PER_BUY)
    return t_buy, g, total_int


def sim_batch(g0: int, level: int, inc: int, floor: int = GOLD_CAP,
              max_rounds: int = 30) -> tuple[int, int, int]:
    """整买策略:攒到 g >= S = B + floor + reserve(N4:C1 修正后的 S 形态,reserve=窗口预留)
    一次性买齐(无自然 XP 的保守版;reserve 首版=0 示范形态,真值来自 p39 臂二窗口)。

    轮序:轮初金位(含上轮结算)上判触发,触发轮花 B 并升级。
    返回 (升级轮, 升级时金, 累计息)。
    """
    g, total_int = g0, 0
    b = batch_cost(level, 0)
    for r in range(1, max_rounds + 1):
        if b > 0 and g >= b + floor:
            g, total_int = round_step(g, total_int, inc, b)
            return r, g, total_int
        g, total_int = round_step(g, total_int, inc, 0)
    return -1, g, total_int


# ---------------------------------------------------------------- 1) 整买 vs 零散

def check_batch_vs_dribble() -> None:
    print('=== 1) batch vs dribble: opportunity cost of piecemeal XP ===')
    print('policy tuple = (levelup_round, gold_at_levelup, total_interest)')
    n_total = 0
    n_strict = 0
    for level in (5, 7):
        for g0 in (50, 30):
            for inc in (6, 7, 9):
                for cpr in (1, 3):
                    d = sim_dribble(g0, level, inc, clicks_per_round=cpr)
                    f = sim_defer(g0, level, inc, d[0])   # 同升级轮的延迟对照
                    # 死库存成本(R2-N2 勘误:金+息是同一笔损失的两种记账,只计金差——
                    # 恒等式:两策略总收支相同 => 升级轮金差 ≡ 累计息差;加式会双计)
                    dead = (f[1] - d[1])
                    dead_id = (f[2] - d[2])
                    assert abs(dead - dead_id) <= max(1, abs(dead)), (
                        f'identity check failed: gold-diff {dead} vs interest-diff {dead_id} '
                        f'(lv{level} g0={g0} I={inc} cpr={cpr})')
                    n_total += 1
                    if dead > 0:
                        n_strict += 1
                    print(f'  lv{level}(need={XP_TO_NEXT_LEVEL[level]:2d}) g0={g0} '
                          f'I={inc} cpr={cpr}: dribble{d} defer{f} dead_cost={dead}')
                    # Leontief 占优(同升级轮):持金轨迹逐轮 >= 花后轨迹
                    assert f[1] >= d[1], f'defer gold < dribble: lv{level} g0={g0} I={inc} cpr={cpr}'
                    assert f[2] >= d[2], f'defer interest < dribble: lv{level} g0={g0} I={inc} cpr={cpr}'
                    if cpr == 1:
                        b = sim_batch(g0, level, inc)
                        # 批触发轮只作报告对照,不作断言:低金位下零散 1/轮 可更早
                        # 升级,但代价是击穿保息地板(批策略刻意保住的下限);
                        # 定理主张的是「同升级轮下持金占优」,不是「批恒更早」
                        print(f'    [report] batch trigger round = {b[0]} (gold {b[1]}, int {b[2]})')
    print('  (dead_cost = gold+interest forgone by converting gold to sub-threshold')
    print(f'   XP early; strictly positive in {n_strict}/{n_total} scenarios -- the rest sit')
    print('   at the 5/round interest plateau where partial-XP cost is only option value)')
    # 部分购买零收益的结构性检查:不足 k* 次的任何前缀都不升级
    for level in (5, 6, 8):
        k = clicks_needed(level, 0)
        xp = 0
        for _ in range(k - 1):
            xp += XP_PER_BUY
            assert xp < XP_TO_NEXT_LEVEL[level], f'partial buy leveled: lv{level}'
    print('  assert OK: defer dominates dribble at equal levelup round;')
    print('            partial prefix never levels')
    print()


# ---------------------------------------------------------------- 2) 汇率判据

def check_exchange_criterion() -> None:
    print('=== 2) hoard exchange criterion: V_action(x) vs rho * x / I (+L if g<50) ===')
    rho_cases = [
        # (label, dV_band+dV_pop, R, gate_positive)  -- p39 数值表转写
        ('4cost2star L7->L8', 103.3, 6, True),
        ('4cost2star L8->L9', 23.0, 6, True),
        ('5cost2star L8->L9', 282.7, 6, True),
        ('4cost2star L6->L7 (gate fail, dV<U)', 28.4, 6, False),
    ]
    inc = 7
    thrs: list[tuple[str, float]] = []
    for label, dv, r_rem, gate in rho_cases:
        rho = (dv / r_rem) if gate else 0.0     # 门未过 -> 无待执行整买 -> rho=0
        thr = rho * 2 / inc                     # 边际动作 x=2 金(一次刷新)
        thrs.append((label, thr))
        print(f'  {label}: rho/round={rho:6.2f}  x=2 threshold={thr:5.2f} gold')
        if gate:
            # 演示两分支:高价值动作花(如 p40 S1 场景刷新 EV ~19 金),低价值动作囤
            v_hi = max(19.2, thr * 1.5)
            v_lo = min(3.0, thr * 0.5)
            print(f'    V={v_hi:5.1f} action -> {"spend" if v_hi > thr else "hoard"}')
            print(f'    V={v_lo:5.1f} action -> {"spend" if v_lo > thr else "hoard"}')
            # 场景 c:合格集空(p40 R0)-> 无动作 -> 恒囤
            print('    qualified-set empty (p40 R0) -> hoard (no action available)')
        else:
            # 门未过:任何正 EV 动作都该花,纯囤无目标
            assert thr == 0.0
            print('    gate negative -> rho=0, no hoard toward levelup')
    # 结构断言:阈值随 rho 单调(汇率判据的方向性);rho 最高 = 5费移位带
    gate_thrs = [t for lbl, t in thrs if 'gate fail' not in lbl]
    assert gate_thrs[2] > gate_thrs[0] > gate_thrs[1], 'threshold must track rho'
    assert thrs[-1][1] == 0.0
    print('  assert OK: threshold monotone in rho; gate-negative -> rho=0; verdict = (V > thr)')
    print()


# ---------------------------------------------------------------- 3) 目标线 S 轨迹

def check_target_line_trajectory() -> None:
    print('=== 3) dynamic target line S = B(t) + floor (with natural-XP offset) ===')
    for level, g0 in ((6, 50), (8, 50)):
        inc, nat_per_round = 7, 4               # 每轮期望买 1 张 -> +4 自然 XP
        g, xp, floor = g0, 0, GOLD_CAP
        print(f'  lv{level} (need={XP_TO_NEXT_LEVEL[level]}) g0={g0} I={inc} nat_xp=4/round:')
        print('   round :  g  :  xp  :  B  :  S  : trigger')
        s_prev = batch_cost(level, 0) + floor
        triggered = False
        for r in range(1, 12):
            i = interest(g)
            g = g + inc + i
            xp = min(XP_TO_NEXT_LEVEL[level], xp + nat_per_round)
            b = batch_cost(level, 0, xp)        # 储蓄期自然 XP 抵扣后的批成本
            s = b + floor
            assert s <= s_prev, f'S increased: round {r}'
            s_prev = s
            fire = g >= s
            print(f'    {r:2d}   : {g:3d} : {xp:3d}  : {b:3d} : {s:3d} : {"YES" if fire else "-"}')
            if fire:
                g_after = g - b
                print(f'    -> buy batch {b} gold, gold {g}->{g_after}, levelup')
                triggered = True
                assert g_after >= floor
                break
        assert triggered
    print('  assert OK: S non-increasing; post-batch gold stays >= 50 floor')
    print()


# ---------------------------------------------------------------- 4) 双目标排队

def queue_total_value(order: list[tuple[int, float]], t_total: int, inc: int) -> float:
    """按 order 顺序逐个攒齐目标的总价值 = sum rho_i * (T - C_i)。

    C_i = 目标 i 攒齐轮(从 0 起按 S/inc 折算,线性近似)。
    """
    c = 0.0
    total = 0.0
    for s_i, rho_i in order:
        c += s_i / inc
        total += rho_i * max(0.0, t_total - c)
    return total


def check_two_target_queue() -> None:
    print('=== 4) two-target queue: per-gold rate rho/S orders the savings ===')
    inc, t_total = 7, 9
    cases = [
        # (label, T1(S,rho), T2(S,rho), note)
        ('case A: same direction', (40, 17.2), (30, 8.0),
         'rho/S: T1 0.430 > T2 0.267, raw-rho agrees'),
        ('case B: disagreement', (72, 17.2), (12, 10.0),
         'rho/S: T2 0.833 > T1 0.239, raw-rho would pick T1'),
    ]
    for label, t1, t2, _note in cases:
        pg_first = queue_total_value([t1, t2], t_total, inc)
        pg_second = queue_total_value([t2, t1], t_total, inc)
        r1, r2 = t1[1] / t1[0], t2[1] / t2[0]
        pick = 'T1' if r1 >= r2 else 'T2'
        best = max(pg_first, pg_second)
        chosen = 'T1-first' if pg_first == best else 'T2-first'
        print(f'  {label}: T1(S={t1[0]},rho={t1[1]}) T2(S={t2[0]},rho={t2[1]})')
        print(f'    per-gold pick={pick}; T1-first={pg_first:7.2f} T2-first={pg_second:7.2f} -> {chosen}')
        # 每金价值率序 = 交换论证的最优序(Smith rule 形态)
        if r1 >= r2:
            assert pg_first >= pg_second - 1e-9
        else:
            assert pg_second >= pg_first - 1e-9
        # 裸 rho 序在 case B 会选错 -> 精确比较器是 rho/S 不是 rho
        if label.startswith('case B'):
            # 裸 rho 序会选 T1(rho 17.2 > 10),但每金率与总值都判 T2 先
            assert t1[1] > t2[1] and r1 < r2 and pg_second > pg_first, \
                'raw-rho ordering must lose here'
    print('  assert OK: per-gold rate (rho/S) is the correct comparator (interchange lemma)')
    print()
    # 视界截断域反例(证明命题 4 修正;数值=正文亲算例转写,禁改动):
    # 每金率序只在「全部目标视界内可完成」域内精确;截断域下不再最优,
    # 正确解法 = 小规模枚举/DP,每金率序降为首序启发式
    inc_t, t_t = 1, 7
    ct1, ct2 = (6, 10.0), (4, 6.5)
    trunc_t1_first = queue_total_value([ct1, ct2], t_t, inc_t)
    trunc_t2_first = queue_total_value([ct2, ct1], t_t, inc_t)
    print(f'  truncation counterexample (inc={inc_t}, T={t_t}): '
          f'T1(S={ct1[0]},rho={ct1[1]}) T2(S={ct2[0]},rho={ct2[1]})')
    print(f'    per-gold rates: T1 {ct1[1]/ct1[0]:.3f} > T2 {ct2[1]/ct2[0]:.3f} -> naive pick T1; '
          f'T1-first={trunc_t1_first:.2f} T2-first={trunc_t2_first:.2f}')
    assert abs(trunc_t1_first - 10.0) < 1e-9, f'truncation T1-first must be 10.0, got {trunc_t1_first}'
    assert abs(trunc_t2_first - 19.5) < 1e-9, f'truncation T2-first must be 19.5, got {trunc_t2_first}'
    assert ct1[1] / ct1[0] > ct2[1] / ct2[0] and trunc_t2_first > trunc_t1_first, \
        'per-gold order must lose in the truncation domain'
    print('  assert OK: per-gold order loses in truncation domain (enumerate/DP required)')
    print()


def main() -> None:
    check_batch_vs_dribble()
    check_exchange_criterion()
    check_target_line_trajectory()
    check_two_target_queue()
    print('ALL P48 CHECKS PASSED')


if __name__ == '__main__':
    main()
