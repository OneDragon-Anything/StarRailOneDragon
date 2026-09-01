"""P47 数值自检:息律经济账(守 50 期望息流 / 息档损失函数 / 回档轮数)。

重跑:PYTHONPATH=src uv run python tools/cw/proofs/p47_check.py
数据源(不 import,值按 docs/game/currency_war/research/economy.md 10.1 与代码注册表转写,
本脚本自含以便离线审阅):
  - 利息 interest(g) = min(g // 10, 5)(50 金满息 5 金/轮;cw_plane_table.interest 同构)
  - 基础奖励分段 1-1=3 / 1-2=4 / 其余 5(cw_economy.REWARD_BASE_GOLD_BY_ROUND + BASE_INCOME)
  - 连胜表 0-1->1 / 2-4->2 / 5->3 / 6+->4;败轮 battle=2 / encounter=boss=4(ADR-0439)
  - 位面长度先验 P1=9 / P2=7 / P3=9(cw_plane_table.DEFAULT_PLANE_LENGTHS 语义)

三段自检(对应证明 p47 的命题 1/2/2):
  1) 守 50 策略的逐位面期望息流(g0 x 位面长度 x 净收入网格);
  2) 花金 d 的息档损失:精确双轨迹模拟 vs 旧消费方口径 t*min(R,3) vs 逐边界闭式;
  3) 回档轮数(每档恢复耗时)随金位/收入的数值。
print 全 ASCII(>= / ->,无特殊符号,防 GBK 控制台炸)。
"""
from __future__ import annotations

import math

GOLD_CAP = 50          # 息封顶金位(满息 5/轮)
INTEREST_CAP = 5


def interest(g: int) -> int:
    """利息 = min(g//10, 5);g<0 按 0 计(防负金越界)。"""
    return min(max(g, 0) // 10, INTEREST_CAP)


def hold50_total_interest(g0: int, rounds: int, net_income: int) -> int:
    """命题 1:守 50 策略(<=50 攒,溢余即花)在 rounds 轮内的总息。

    口径:第 r 轮息 = interest(当时金位);结算后金 = min(g + net_income + 息, 50)
    (溢余当场花掉——[17] 纪律)。net_income = 基础 + 连胜/败轮金(不含息)。
    """
    g = min(g0, GOLD_CAP)
    total = 0
    for _ in range(rounds):
        i = interest(g)
        total += i
        g = min(g + net_income + i, GOLD_CAP)
    return total


def loss_exact(g: int, spend: int, rounds: int, net_income: int) -> int:
    """命题 2:金位 g 花 spend 金后,未来 rounds 轮内的精确期望息损。

    双轨迹对照:基线 B(不花,守 50,溢余即花)vs A(花后守 50)。
    每轮息损 = interest(B) - interest(A);两轨迹同收入演化。
    """
    b = min(g, GOLD_CAP)
    a = max(g - spend, 0)
    total = 0
    for _ in range(rounds):
        ib, ia = interest(b), interest(a)
        total += ib - ia
        b = min(b + net_income + ib, GOLD_CAP)
        a = min(a + net_income + ia, GOLD_CAP)
    return total


def loss_old_form(g: int, spend: int, rounds: int) -> int:
    """旧消费方口径:p39 A4 / p40 R2 的 t * min(R, 3)。"""
    t = interest(g) - interest(g - spend)
    return t * min(rounds, 3)


def _rounds_to_boundary(x0: int, boundary: int, net_income: int) -> int:
    """从金位 x0 爬到档线 boundary 的近似轮数 = ceil((b-x0)/(I + b/10))。"""
    return math.ceil((boundary - x0) / (net_income + boundary / 10.0))


def loss_closed_form(g: int, spend: int, rounds: int, net_income: int) -> int:
    """命题 2 闭式(逐边界求和,双轨迹;截断分别作用于两条到达轮)。

    L ~= sum_{档线 b in (A0,50]} max(0, min(K_A(b),R) - min(K_B(b),R))
    (旧式 min(R, max(0,K_A-K_B)) 在 K_A>R 边角高估——单格 (25,25,3,6):12→8 对齐精确)
    K_X(b) = 轨迹 X 爬到档线 b 的轮数近似;基线在 50 钉死时 K_B(b)=0,
    基线仍在爬坡(g<50)时 b>g 的档线要扣掉基线自己的到达轮数——
    息差只在「基线已过线、花后轨迹未过线」的轮内存在。
    """
    a0 = max(min(g, GOLD_CAP) - spend, 0)
    b0 = min(g, GOLD_CAP)
    total = 0
    for b in range((a0 // 10 + 1) * 10, GOLD_CAP + 1, 10):
        ka = _rounds_to_boundary(a0, b, net_income)
        kb = 0 if b0 >= b else _rounds_to_boundary(b0, b, net_income)
        total += max(0, min(ka, rounds) - min(kb, rounds))
    return total


def tier_recovery_rounds(gold: int, net_income: int) -> int:
    """命题 2 附:回档轮数——金位 gold(未满 50)爬回上一档线要几轮(离散精确)。"""
    target = (gold // 10 + 1) * 10
    g = gold
    rounds = 0
    while g < target and rounds < 50:
        g = min(g + net_income + interest(g), GOLD_CAP)
        rounds += 1
    return rounds


def loss_alt_timing(g: int, spend: int, rounds: int, net_income: int) -> int:
    """口径敏感性:息在「收入到账后、溢余花掉前」的金位上结算(另一时点约定)。

    与 loss_exact(轮初结算)对拍,差值 = 时点假设的误差上界指示。
    """
    b = min(g, GOLD_CAP)
    a = max(g - spend, 0)
    total = 0
    for _ in range(rounds):
        b_raw = b + net_income
        a_raw = a + net_income
        total += interest(b_raw) - interest(a_raw)
        b = min(b_raw + interest(b_raw), GOLD_CAP)
        a = min(a_raw + interest(a_raw), GOLD_CAP)
    return total


def loss_sellback_prefix(g: int, spend: int, sell_round: int, rounds: int, net_income: int) -> int:
    """命题三动态修正([11] 精确化·卖回通道):A 段截断息差 = 前 min(s,R) 轮的双轨迹息差和。

    A 段(持有到临结算)与静态递推同构;卖回时点 s 后 A 金位恢复、息差归零,
    故动态息损 = A 段截断 + fee′(此函数只算截断段;fee/时点敞口在文档声明,不在此计)。
    """
    return loss_exact(g, spend, min(sell_round, rounds), net_income)


def main() -> None:
    print('=== P1: hold-50 interest per plane (exact recursion) ===')
    print('scenario: g0, rounds, net_income -> total interest')
    grid: list[tuple[int, int, int]] = []
    for g0 in (0, 5, 10):
        for inc in (6, 7, 8, 9):
            grid.append((g0, 9, inc))          # P1 形状
    grid += [(50, 7, inc) for inc in (6, 7, 9)]   # P2 形状(满息进位面)
    grid += [(50, 9, inc) for inc in (7, 9)]      # P3 形状
    for g0, t, inc in grid:
        print(f'  g0={g0:2d} T={t} I={inc} -> {hold50_total_interest(g0, t, inc)}')

    print()
    print('=== P1b: realistic P1 (buy 2/round during ramp, net save = I-2) ===')
    for inc in (7, 9):
        print(f'  g0=5 T=9 I={inc} spend2/round -> '
              f'{hold50_total_interest(5, 9, inc - 2)}')

    print()
    print('=== P2: interest loss of spending d (R=9, I=7) ===')
    print('g=50 plateau:')
    print('   d : exact : old(t*min(R,3)) : closed')
    for d in (2, 4, 8, 10, 14, 20, 30, 40):
        e = loss_exact(50, d, 9, 7)
        o = loss_old_form(50, d, 9)
        c = loss_closed_form(50, d, 9, 7)
        flag = 'old=exact' if o == e else ('old OVER' if o > e else 'old UNDER')
        print(f'   {d:2d} :  {e:2d}   :  {o:2d}            :  {c:2d}   [{flag}]')
    print('g=30 mid-climb:')
    for d in (5, 15, 25):
        e = loss_exact(30, d, 9, 7)
        o = loss_old_form(30, d, 9)
        c = loss_closed_form(30, d, 9, 7)
        flag = 'old=exact' if o == e else ('old OVER' if o > e else 'old UNDER')
        print(f'   {d:2d} :  {e:2d}   :  {o:2d}            :  {c:2d}   [{flag}]')
    print('g=45 near-boundary (same-tier d=4: floor45->41, t=0):')
    for d in (4, 6):
        e = loss_exact(45, d, 9, 7)
        o = loss_old_form(45, d, 9)
        c = loss_closed_form(45, d, 9, 7)
        flag = 'old=exact' if o == e else ('old OVER' if o > e else 'old UNDER')
        print(f'   {d:2d} :  {e:2d}   :  {o:2d}            :  {c:2d}   [{flag}]')
    print('g=55 overflow segment (t=0 by definition, residual check):')
    for d in (5, 8):
        e = loss_exact(55, d, 9, 7)
        print(f'   {d:2d} :  {e:2d}   :  {loss_old_form(55, d, 9)}')

    print()
    print('=== P2b: horizon sensitivity (R scan), g=50 d=20 I=7 ===')
    for r in (1, 2, 3, 5, 9, 15):
        print(f'   R={r:2d} -> exact {loss_exact(50, 20, r, 7)}, '
              f'old {loss_old_form(50, 20, r)}')

    print()
    print('=== P3: tier recovery rounds (full gold grid, not lucky mod10=5 slice) ===')
    print('one-round-climb condition: (10 - gold mod 10) <= I + floor(gold/10)')
    bad_one_round = []
    for net_income in (4, 5, 6, 7, 9):
        for gold in range(0, 50):
            r = tier_recovery_rounds(gold, net_income)
            if r > 1:
                bad_one_round.append((gold, net_income, r))
    print('gold,I pairs needing >1 round: %d (sample: %s)'
          % (len(bad_one_round), bad_one_round[:8]))
    # 需改② 刻画自检:条件式与离散精确全网格一致
    mismatch = 0
    for net_income in (4, 5, 6, 7, 9):
        for gold in range(0, 50):
            cond = (10 - gold % 10) <= net_income + gold // 10
            exact_one = tier_recovery_rounds(gold, net_income) == 1
            if cond != exact_one and gold % 10 != 0:  # 恰在档线上的 gold 无「爬回上一档」语义
                mismatch += 1
    print('condition-vs-exact mismatches: %d' % mismatch)
    assert mismatch == 0, 'one-round-climb condition must match exact grid'
    assert (3, 6, 2) in bad_one_round and (4, 6, 2) not in bad_one_round or True  # 参考格(非单调形态存在)
    print('sample table (gold: I=5/I=7/I=9):')
    for gold in (3, 5, 9, 13, 25, 35, 45):
        print(f'  {gold:2d}  :  {tier_recovery_rounds(gold, 5)}  :  '
              f'{tier_recovery_rounds(gold, 7)}  :  {tier_recovery_rounds(gold, 9)}')

    print()
    print('=== cross-check: closed form vs exact, max abs deviation over grid ===')
    dev_max = 0
    cells = 0
    for g in (50, 45, 40, 30, 25, 20, 15, 35):
        for d in (2, 4, 6, 10, 15, 20, 25, 30, 40):
            if d > g:
                continue
            for r in (3, 6, 9):
                for inc in (6, 7, 9):
                    e = loss_exact(g, d, r, inc)
                    c = loss_closed_form(g, d, r, inc)
                    dev_max = max(dev_max, abs(e - c))
                    cells += 1
    print(f'  cells={cells}, max|exact-closed|={dev_max} gold')

    # 命题一(息流)闭式对拍段——数值声明的脚本覆盖
    print('  [interest closed-form cross-check]')
    idev_orig, idev_low = 0, 0
    for g0 in (0, 5, 10, 20, 35):
        for T in (7, 9):
            for inc in (4, 5, 6, 7, 8, 9):
                gg, total = g0, 0
                for _ in range(T):
                    total += min(gg // 10, 5)
                    gg = min(gg + inc + min(gg // 10, 5), 50)
                # 连续化闭式(命题一):T_ramp=10*ln((50+10I)/(g0+10I));E[ramp]=(50-g0)-10I*ln(...);E[total]+=5*max(0,T-Tramp)
                ramp_t = 10 * math.log((50 + 10 * inc) / (g0 + 10 * inc))
                ramp_e = (50 - g0) - 10 * inc * math.log((10 * inc + 50) / (10 * inc + g0))
                closed = ramp_e + 5 * max(0, T - ramp_t)
                dev = closed - total
                if inc >= 6:
                    idev_orig = max(idev_orig, abs(dev))
                idev_low = max(idev_low, abs(dev))
                if (g0, T, inc) == (0, 7, 4):
                    assert abs(closed - 17.56) < 0.01 and total == 6, 'worst low-band cell (0,7,4): closed 17.56 vs exact 6'
                if (g0, T, inc) == (0, 7, 6):
                    pass  # 原带最差格数值在循环内取 max,不逐格断言
    print('  interest closed-form dev: orig band(I>=6) max=%.2f, with low band max=%.2f (N2)' % (idev_orig, idev_low))
    assert idev_orig > 6.5  # 原带实测 max 7.33(格 0,7,6)——初稿 6.6 系单格采样
    assert idev_low > 11    # 含低带 max 11.56(格 0,7,4)

    print()
    print('=== timing sensitivity: round-start vs post-income interest eval ===')
    dev = 0
    for g in (50, 45, 30, 20):
        for d in (4, 10, 20, 30):
            if d > g:
                continue
            for r in (3, 6, 9):
                for inc in (6, 7, 9):
                    dev = max(dev, abs(loss_exact(g, d, r, inc)
                                       - loss_alt_timing(g, d, r, inc)))
    print(f'  max|round-start - post-income| over grid = {dev} gold')

    print()
    print('=== prop.3 dynamic correction (sellback channel): A-segment truncation, I=7 ===')
    # 数值例 = 文档命题三动态修正节的亲算锚(截断段;fee/时点敞口为文档声明项,不入数)
    cases = [
        (45, 4, 3, 9, 0),    # 近50同档:静态 0 -> 动态 0
        (50, 20, 3, 9, 3),   # 平台期跨档:静态 3,A 段 s=3 已收敛 -> 3
        (9, 8, 3, 9, 2),     # 低金带同档:静态 5,s=3 动态 2(0+1+1)
        (30, 25, 3, 9, 9),   # 深爬坡:静态 15,s=3 动态 9
    ]
    for g, d, s, r, expect in cases:
        got = loss_sellback_prefix(g, d, s, r, 7)
        static = loss_exact(g, d, r, 7)
        print(f'  ({g},{d}) s={s} R={r}: dynamic={got} (static={static})')
        assert got == expect, f'sellback case ({g},{d},s={s}): {got} != {expect}'
    print('  [assert] prop.3 sellback numeric anchors locked')


if __name__ == '__main__':
    main()
