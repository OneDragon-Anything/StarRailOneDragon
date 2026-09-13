"""P43 数值自检:连胜-息取舍的经济账(连胜金流模型 / 破息保连胜判据 / 弃连胜保息判据)。

重跑:PYTHONPATH=src uv run python tools/cw/proofs/p43_check.py
数据源(不 import,值按代码注册表与 docs/game/currency_war/research 转写,本脚本自含):
  - 连胜表 STREAK_GOLD_TABLE = (1,1,2,2,2,3,4)(cw_economy,索引=连胜数,越界取尾;
    economy.md 10.1 弹窗实测 49/49)
  - 败轮金 LOSS_GOLD_BY_NODE = battle 2 / encounter 4 / boss 4(实机差分)
  - 奖励轮照发连胜金 streak_gold(进轮连胜),计数不动(85/85 零散布)
  - 利息 interest(g)=min(g//10,5)(p47 A1 同源;本脚本只复用其 L 递推做对拍)

收入口径 = 引擎口径(engine_p1.py 收入段,R1 对抗 B1 修正):
  - 每轮收入在**轮首**入账,连胜金 = streak_gold(进轮连胜 s)——胜轮发 T[s],
    胜的增量只影响下一轮(不是胜后取 T[s+1]);
  - 败轮金 = LOSS_GOLD_BY_NODE[败掉轮节点],在败轮的**下一轮**轮首补发,
    且仅当下一轮是战斗类节点(supply/reward 分支优先,败轮后跟奖励轮时
    发 T[0]=1 而非 loss——齐次战斗轮模型天然忽略该分支,序列模型 P4/P6 带上);
  - 奖励轮照发 streak_gold(进轮连胜)不动计数;补给轮零发不动计数。

七段自检(对应证明 p43 命题 1/1/2/2/3/4/2):
  1) 胜/输转移的期望收益差 D(s):次轮金差 vs 续期(重建)差分解(引擎口径);
  2) 重建账:闭式(连续 s 胜期望轮数)与精确 DP 对拍 + R 饱和性检验;
  3) ΔV_streak(s,R,Δp) 网格 + 单调性断言(对 s/R/Δp)+ 短视界结构(R=1 恒 0);
  4) 破息保连胜的盈亏平衡带:给定息损 L,求最小 Δp*(s,R,p);
  5) 三态谱判定表:(连胜在手 x 来牌 x 息差) -> 花/忍;
  6) 全局量级对拍:近似节点序列(含奖励轮)整局连胜账 vs 攻略「连胜全程多 ~100 金」;
  7) 位面末熄火带:含奖励轮尾段的 ΔV(与读数 3 对拍)。
print 全 ASCII(>= / ->,无特殊符号,防 GBK 控制台炸)。
"""
from __future__ import annotations

# —— 机制常量(单一源转写,见模块 docstring)——
STREAK_TABLE = (1, 1, 2, 2, 2, 3, 4)
LOSS_BATTLE = 2
LOSS_HARD = 4          # encounter / boss 同值 4
GOLD_CAP = 50          # 息封顶(p47 同源)
SMAX = 12              # DP 内连胜数上限(table 饱和于 6,12 足够)


def sg(s: int) -> int:
    """连胜奖励金,越界取表尾(与 cw_economy.streak_gold 同构)。"""
    return STREAK_TABLE[min(max(s, 0), len(STREAK_TABLE) - 1)]


# —— 引擎口径 DP:状态 = (连胜 s, 上轮是否败掉的战斗轮 lost) ——
def v_table(r: int, p: float, loss: int = LOSS_BATTLE) -> list[list[float]]:
    """V[(s,lost)]:该状态下未来 r 轮的期望连胜金+败轮金总和(引擎口径)。

    轮首收入:lost 且 s==0 -> loss(上一轮败掉轮的补发金,齐次模型按同节点取值);
    否则 -> table[s](进轮连胜发金,奖励轮同式、计数不动——齐次战斗轮模型
    只辖战斗节点,奖励/补给分支见 v_seq)。
    转移:本轮胜(概率 p)-> (min(s+1,SMAX), lost=0);败 -> (0, lost=1)。
    基础奖励与利息两条轨迹同得,不入账(差分中消去;见证明 A2/A5)。
    """
    v = [[0.0] * 2 for _ in range(SMAX + 1)]
    for _ in range(r):
        nv = [[0.0] * 2 for _ in range(SMAX + 1)]
        for s in range(SMAX + 1):
            for lost in (0, 1):
                inc = loss if (lost and s == 0) else sg(s)
                nv[s][lost] = inc + p * v[min(s + 1, SMAX)][0] \
                    + (1 - p) * v[0][1]
        v = nv
    return v


def v_of(s: int, r: int, p: float, loss: int = LOSS_BATTLE) -> float:
    """V(s,R,p):连胜 s 进场(上轮非败)的期望连胜账。"""
    return v_table(r, p, loss)[min(s, SMAX)][0]


def d_eng(s: int, r: int, p: float, loss: int = LOSS_BATTLE) -> float:
    """引擎口径 D(s):本轮赢 vs 输的全部账差。

    本轮轮首收入 T[s] 两分支同得(胜负不改本轮账)消去;差分整体移到
    从**下一状态**起的轨迹:V(s+1,R-1,进胜态) - V(0,R-1,败态)。
    """
    tab = v_table(r - 1, p, loss)
    return tab[min(s + 1, SMAX)][0] - tab[0][1]


def d_split(s: int, r: int, p: float, loss: int = LOSS_BATTLE) -> tuple[float, float]:
    """命题 1 分解(引擎口径):D(s) = 次轮金差 + 续期差。

    次轮金差 = table[s+1] - loss(决策的**下一轮**轮首:胜分支发 T[s+1]、
    败分支补发 loss——引擎时序下即期账恒同,首个金差出现在次轮);
    续期差 = D - 次轮金差(此后维持连胜 vs 归零重爬的账)。
    返回 (次轮金差, 续期差);D = 两者之和。
    """
    immediate = float(sg(s + 1) - loss)
    cont = d_eng(s, r, p, loss) - immediate
    return immediate, cont


def rebuild_rounds_closed(s: int, p: float) -> float:
    """重建闭式:从 0 连拿 s 胜的期望轮数 = sum_{k=1..s} p^{-k}(经典连掷公式)。"""
    return sum(p ** (-k) for k in range(1, s + 1))


def delta_v(s: int, r: int, dp: float, p: float, loss: int = LOSS_BATTLE) -> float:
    """ΔV_streak(s,R,Δp) = V(s,R,p+Δp) - V(s,R,p):胜率提升 Δp 的连胜账增量。"""
    return v_of(s, r, p + dp, loss) - v_of(s, r, p, loss)


def break_even_dp(s: int, r: int, p: float, target: float,
                  loss: int = LOSS_BATTLE) -> float:
    """命题 2 盈亏平衡:使 ΔV_streak >= target 的最小 Δp(0.01 步扫描)。

    扫满 [0.01, 1-p] 全带(无截断伪迹):返回 nan = 视界内数学上不可达,
    即 p 提到 1.0 也盖不过 target——语义见文档 P2b 表注。
    """
    step = 0.01
    dp = 0.0
    while dp < 1.0 - p - 1e-9:
        dp += step
        if delta_v(s, r, dp, p, loss) >= target:
            return round(dp, 4)
    return float('nan')  # 视界内不可达(扫满全带,非扫描伪迹)


# —— 引擎口径:带节点序列(奖励轮照发 / 补给零发 / 败轮金按败掉轮节点) ——
_SEQ_MEMO: dict = {}


def v_seq(s0: int, seq: tuple[str, ...], p: float) -> float:
    """从连胜 s0 进场、沿节点序列 seq 的期望连胜账(引擎口径,只含 streak 分量)。

    战斗类(battle/encounter/boss)按胜率 p;reward = 照发 T[进轮连胜] 不动计数
    ;supply = 零发不动计数。败轮金按**败掉轮**节点类型
    (battle->2, 其余->4),在下一轮轮首补发且仅当下一轮是战斗类节点
    (reward/supply 分支优先——引擎 L738-746 分支序)。
    """
    def rec(i: int, s: int, lost: int, loss_val: int) -> float:
        if i == len(seq):
            return 0.0
        key = (i, min(s, SMAX), lost, loss_val, p)
        if key in _SEQ_MEMO:
            return _SEQ_MEMO[key]
        node = seq[i]
        if node == 'supply':
            val = rec(i + 1, s, 0, 0)
        elif node == 'reward':
            val = sg(s) + rec(i + 1, s, 0, 0)
        else:
            lv = LOSS_BATTLE if node == 'battle' else LOSS_HARD
            inc = lv if (lost and s == 0) else sg(s)
            val = inc + p * rec(i + 1, min(s + 1, SMAX), 0, 0) \
                + (1 - p) * rec(i + 1, 0, 1, lv)
        _SEQ_MEMO[key] = val
        return val

    return rec(0, min(s0, SMAX), 0, 0)


# —— p47 的 L 递推(自含复刻,做对拍用;规范源 = p47_check.py)——
def _interest(g: int) -> int:
    return min(max(g, 0) // 10, 5)


def loss_exact(g: int, spend: int, rounds: int, net_income: int) -> int:
    """p47 命题二:金位 g 花 spend 后未来 rounds 轮的精确期望息损(双轨迹)。"""
    b = min(g, GOLD_CAP)
    a = max(g - spend, 0)
    total = 0
    for _ in range(rounds):
        ib, ia = _interest(b), _interest(a)
        total += ib - ia
        b = min(b + net_income + ib, GOLD_CAP)
        a = min(a + net_income + ia, GOLD_CAP)
    return total


def main() -> None:
    print('=== P1: win-vs-lose transfer differential D(s), R=9, p=0.7 (engine caliber) ===')
    print('s : next-round(battle) : cont(battle) : D(battle) : next-round(hard=4)')
    imm_battle_max, imm_hard_min = -99.0, 99.0
    for s in range(0, 7):
        ib, cb = d_split(s, 9, 0.7, LOSS_BATTLE)
        ih, _ = d_split(s, 9, 0.7, LOSS_HARD)
        imm_battle_max = max(imm_battle_max, ib)
        imm_hard_min = min(imm_hard_min, ih)
        print(f'  {s} : {ib:+.1f} : {cb:+6.2f} : {ib + cb:+6.2f} : {ih:+.1f}')
    assert imm_battle_max == 2.0, 'next-round delta max = table[6]-2 = 2'
    assert imm_hard_min == -3.0, 'next-round delta min = table[1]-4 = -3 (s=0 hard node)'
    print('  [assert] next-round delta in [-3, +2]; hard-node delta <= 0 for s<=5')
    # 引擎时序:同轮即期差恒 0(本轮发金在轮首、胜负不改本轮账)——结构断言
    # R=1 时 V(s,lost) = inc 只依赖 (s,lost),不依赖 p -> 同轮收入与胜负无关
    for s in range(0, 7):
        for p0 in (0.3, 0.7):
            assert v_of(s, 1, p0) == v_of(s, 1, 0.5), \
                'R=1 account must be p-independent (round-start income)'
    print('  [assert] R=1: V(s,1,p) == T[s] independent of p (same-round delta = 0)')
    # 续期差主导:s>=2 且 R 长时续期差 > |次轮金差|
    for s in (2, 4, 6):
        _, cb = d_split(s, 9, 0.7, LOSS_BATTLE)
        assert cb > 2.0, f'continuation account must dominate at s={s}'

    print()
    print('=== P1b: rebuild account, closed-form vs exact DP (p=0.7, battle) ===')
    print('s : E[rebuild rounds] : cont account V(s+1,8)-V(0,8) : crude = E*premium')
    for s in (2, 3, 4, 5):
        er = rebuild_rounds_closed(s, 0.7)
        cont = d_eng(s, 9, 0.7) - float(sg(s + 1) - LOSS_BATTLE)
        premium = sg(s + 1) - sg(1)          # 维持连胜 vs 重爬期的每轮金差上界
        print(f'  {s} : {er:6.2f} : {cont:6.2f} : {er * premium:8.2f}')
    assert rebuild_rounds_closed(4, 0.7) > 10, 'E[4 straight wins] ~ 10.5 rounds at p=0.7'
    # 闭式 crude 是上界形态——真因=溢价上界恒松(重爬期绝大多数轮低连胜,
    # 每轮金差达不到 T[s+1]-T[1]),与视界无关;断言只锁方向(精确 <= crude)
    for s in (2, 3, 4, 5):
        cont = d_eng(s, 9, 0.7) - float(sg(s + 1) - LOSS_BATTLE)
        assert cont <= rebuild_rounds_closed(s, 0.7) * (sg(s + 1) - sg(1)) + 1e-9
    # R 饱和:精确续期差在 R~8 已饱和成常数——长视界不改善闭式(归因证据)
    for s in (2, 4, 5):
        c8 = d_eng(s, 8, 0.7) - float(sg(s + 1) - LOSS_BATTLE)
        c40 = d_eng(s, 40, 0.7) - float(sg(s + 1) - LOSS_BATTLE)
        assert abs(c8 - c40) < 1e-6, f'continuation account must saturate by R=8 at s={s}'
    print('  [assert] exact continuation saturates by R=8 (R=40 identical); '
          'closed-form overestimate persists at any horizon')

    print()
    print('=== P2: dV_streak(s,R,dp) grid, p=0.7 -> 0.8 (dp=0.1), battle ===')
    print('s\\\\R :  3  :  6  :  9')
    prev_row = None
    for s in (0, 1, 2, 3, 4, 5, 6):
        row = [delta_v(s, r, 0.1, 0.7) for r in (3, 6, 9)]
        print(f'  {s}  : ' + ' : '.join(f'{x:5.2f}' for x in row))
        if prev_row is not None:
            for a, b in zip(row, prev_row, strict=True):
                assert a >= b - 1e-9, 'dV must be non-decreasing in s'
        prev_row = row
    # 对 R 单调(s>=2;s=0 在短视界有下陷——R=1 恒 0、R=2 因次轮败轮金替换
    # streak_gold(0) 可微负,是结构发现不是断言对象,见下方短视界结构断言)
    for s in (2, 4, 6):
        vals = [delta_v(s, r, 0.1, 0.7) for r in range(1, 10)]
        assert all(vals[i + 1] >= vals[i] - 1e-9 for i in range(len(vals) - 1)), \
            'dV must be non-decreasing in R at s>=2'
    # 对 Δp 的方向:长视界(s>=2,R>=6)单调增
    for s in (2, 4, 6):
        for r in (6, 9):
            vals = [delta_v(s, r, dp / 100, 0.5) for dp in range(0, 50)]
            assert all(vals[i + 1] >= vals[i] - 1e-9 for i in range(len(vals) - 1)), \
                'dV must be non-decreasing in dp at long horizon'
    # 短视界结构(引擎时序):R=1 恒 0(本轮账与 p 无关);R=2 起可微负
    # (机制=下一轮败轮金 loss 替换 streak_gold(0)=1,是下一轮效应)
    assert delta_v(0, 1, 0.5, 0.5) == 0.0, 'R=1: dV must be exactly 0'
    neg_found = any(delta_v(0, 2, dp / 100, 0.5) < 0 for dp in range(1, 50))
    assert neg_found, 'R=2: dV(0,2) can be negative (next-round loss-gold replacement)'
    print('  [assert] dV non-decreasing in s / R(s>=2) / dp at long horizon; '
          'dV(0,1)=0 exactly; dV(0,2) can be negative')
    # 未连胜 vs 连胜在手:全网格 s=0 严格小于 s>=2
    for r in (3, 6, 9):
        assert delta_v(0, r, 0.1, 0.7) < delta_v(2, r, 0.1, 0.7), \
            'no-streak account must be strictly smaller'

    print()
    print('=== P2b: break-even dp* (min win-prob lift paying for interest loss L) ===')
    print('target L from p47 representative values: plateau d=10->L=1, d=20->3, '
          'd=30->9, d=40->14 (I=7, R=9); scan covers full [0.01, 1-p] band')
    for p0 in (0.5, 0.7):
        print(f'  base p={p0}:')
        print('  s\\\\R :  L=1  :  L=3  :  L=9  :  L=14 :  L=20')
        for s in (0, 2, 4, 6):
            cells = []
            for target in (1, 3, 9, 14, 20):
                be = break_even_dp(s, 9, p0, target)
                cells.append(f'{be:5.2f}' if be == be else '  n/a')
            print(f'    {s}  : ' + ' : '.join(cells))
    # 断言:s=0 的盈亏平衡 Δp 恒大于 s=6(未连胜更难盖过息损;nan=视界内
    # 不可达,按"最难"处理,断言自动成立)
    for target in (3, 9):
        be0 = break_even_dp(0, 9, 0.7, target)
        be6 = break_even_dp(6, 9, 0.7, target)
        if be0 == be0:
            assert be0 > be6
    # 可达性披露:各 (p,s) 的连胜账上限 V(s,9,1.0)-V(s,9,p)——n/a 的格
    # = target 超过该上限(视界内数学不可达,p 提到 1.0 也盖不过,非扫描伪迹)
    for p0 in (0.5, 0.7):
        caps = [v_of(s, 9, 1.0) - v_of(s, 9, p0) for s in (0, 2, 4, 6)]
        print(f'  [cap] max dV(R=9, p={p0}): s=0/2/4/6 -> '
              + '/'.join(f'{c:.1f}' for c in caps))
    # 量级带:Δp=0.1、R=9 时连胜账上下沿(供文档引用)
    band_hi = delta_v(6, 9, 0.1, 0.7)
    band_lo = delta_v(2, 9, 0.1, 0.7)
    print(f'  [band] dV(dp=0.1, R=9, p=0.7): s=2 -> {band_lo:.2f}, s=6 -> {band_hi:.2f}')
    assert band_lo < band_hi

    print()
    print('=== P3: three-state verdict table (battle node, R=9, p_lo=0.55) ===')
    print('cols: L(g,d,9,7) from p47 recursion; rows: state x dp(channel) -> verdict')
    scen = [
        ('s=0, card-ok  dp=0.15', 0, 0.15),
        ('s=4, card-ok  dp=0.15', 4, 0.15),
        ('s=6, card-ok  dp=0.15', 6, 0.15),
        ('s=4, no-card  dp=0    ', 4, 0.0),
        ('s=6, no-card  dp=0    ', 6, 0.0),
    ]
    spend_cases = [(50, 8, 1), (50, 20, 3), (50, 30, 9), (30, 25, 15)]
    print('  state                : dV    : vs L(d=8)=1 : L(20)=3 : L(30)=9 : L(30,25)=15')
    for label, s, dp in scen:
        dv = delta_v(s, 9, dp, 0.55)
        cells = []
        for g, d, _ in spend_cases:
            li = loss_exact(g, d, 9, 7)
            verdict = 'SPEND(streak)' if dv >= li else 'HOLD(interest)'
            if dp == 0.0:
                verdict = 'HOLD(no channel)'
            cells.append(verdict)
        print(f'  {label} : {dv:5.2f} : ' + ' : '.join(cells))
    # 关键断言 1:无牌通道关闭时无论连胜账多大都判 HOLD
    assert delta_v(6, 9, 0.0, 0.55) == 0.0
    # 关键断言 2(引擎口径翻案格):s=0/牌顺/L=1 时连胜账单独不再证成
    assert delta_v(0, 9, 0.15, 0.55) < loss_exact(50, 8, 9, 7), \
        'engine caliber: no-streak + dp=0.15 must NOT clear L=1 (flipped cell)'

    print()
    print('=== P3b: hold-side criterion L(ren) = streak account at risk ===')
    print('L(ren)(s,dp) = dV_streak: the account sacrificed by not spending')
    for s in (2, 4, 6):
        for dp in (0.10, 0.20):
            print(f'  s={s} dp={dp:.2f} -> L(ren) = {delta_v(s, 9, dp, 0.55):5.2f}')

    print()
    print('=== P4: whole-game magnitude cross-check vs guide "~100 gold" ===')
    # 近似节点序列(25 节点 / 18 战斗轮,位面轮布局近似;含奖励轮照发、
    # 补给零发、败轮金按节点——引擎口径序列模型,非纯战斗轮齐次式)
    p1 = ('battle', 'battle', 'encounter', 'reward', 'encounter', 'reward',
          'battle', 'supply', 'battle')
    p2 = ('battle', 'battle', 'supply', 'battle', 'encounter', 'reward', 'boss')
    p3 = ('battle', 'encounter', 'reward', 'battle', 'encounter', 'reward',
          'boss', 'battle', 'battle')
    seq = p1 + p2 + p3
    n_combat = sum(1 for x in seq if x not in ('reward', 'supply'))
    _SEQ_MEMO.clear()
    full = v_seq(1, seq, 1.0)     # 进场连胜 1、全胜(奖励轮照发不增计数)
    base = v_seq(0, seq, 0.55)
    _SEQ_MEMO.clear()
    full_s0 = v_seq(0, seq, 1.0)  # s0=0 对照(结论不依赖进场连胜口径)
    print(f'  approx node sequence: {len(seq)} nodes, {n_combat} combat rounds')
    print(f'  full streak account: {full:.1f} ; p=0.55 baseline account: {base:.1f}')
    print(f'  s0=0 full account: {full_s0:.1f} (differential {full_s0 - base:.1f})')
    print(f'  differential (full - baseline): {full - base:.1f} '
          f'(guide claim ~100, combat.md sec.4)')
    # 文档 P4 行的演示口径数值锚(s0=1 为主口径,s0=0 为敏感性对照)
    assert abs(full - 79.0) < 0.05 and abs(base - 38.7) < 0.05 \
        and abs(full - base - 40.3) < 0.05, 'P4 anchor values drifted'
    assert abs(full_s0 - base - 36.3) < 0.05, 's0=0 differential anchor drifted'
    assert full - base > 30, 'streak account must be material at whole-game scale'
    # 解析锚:V(0,0,2) = 3 - p(短视界负斜率的闭式;R=2 起连胜账可对 p 微负)
    for p0 in (0.3, 0.5, 0.7):
        assert abs(v_of(0, 2, p0) - (3.0 - p0)) < 1e-9, \
            'V(0,0,2) must equal 3-p analytically'

    print()
    print('=== P6: plane-tail streak account (with reward round, engine sequence) ===')
    # P2 尾段(r5 encounter, r6 reward, r7 boss):剩余 2 战斗轮 + 1 奖励轮
    # 奖励轮照发连胜金使尾段账高于齐次纯战斗口径——熄火带对拍
    tail = ('encounter', 'reward', 'boss')
    for s in (2, 4, 6):
        _SEQ_MEMO.clear()
        dv_seq = v_seq(s, tail, 0.65) - v_seq(s, tail, 0.55)
        dv_hom = delta_v(s, 2, 0.10, 0.55, LOSS_HARD)
        print(f'  s={s}: dV(seq tail, dp=0.10) = {dv_seq:+.2f} ; '
              f'homogeneous 2-round dV = {dv_hom:+.2f}')
    # 断言:尾段连胜账仍小于 L=1 档(位面末熄火结论在奖励轮口径下保留)
    _SEQ_MEMO.clear()
    assert v_seq(6, tail, 0.65) - v_seq(6, tail, 0.55) < 1.0, \
        'plane-tail streak account must stay below L=1 tier even with reward round'

    print()
    print('=== P5: compliance & second-order interest reaction band ===')
    # 连胜/败轮的收入差对 p47 L 的影响:Ī 带-win 6-9 / lose 7-9,带内 L 变化
    l_win = loss_exact(40, 20, 9, 8)
    l_lose = loss_exact(40, 20, 9, 9)
    print(f'  L(40,20,9): I=8(win-mix) -> {l_win}, I=9(lose-mix) -> {l_lose}; '
          f'band delta {l_lose - l_win}')
    print('  [declared] win/lose income mix shifts L by <= band above; '
          'p43 account excludes interest (no double count with p47)')


if __name__ == '__main__':
    main()
