"""W137 P10 出口金保留量期望底线——数据面计算脚本(可重跑;P3 脚本佚失教训)。

对应证明:docs/game/currency_war/research/proofs/p10-exit-gold-floor.md

数据源(单一源真值,零随机):
- cw_economy: STREAK_GOLD_TABLE / BASE_REWARD_GOLD(利息结构 min(5, gold//10))
- cw_state: XP_TO_NEXT_LEVEL / XP_PER_BUY=4 / XP_CLICK_COST_FALLBACK=4 / sell_refund
- cw_horizon: NODES_PER_PLANE=9 / TOTAL_NODES=27
- decision_v2 registry: h3_win_rate / hp_to_gold=0.5 / interest_recovery_rounds=3.0
- sim 账本: .debug/temp/currency_war/w135_crosscheck/metrics_w135.json
  (seeds 0-99,池指纹 bab146c68c5df11a;不存在时⑤节跳过);
  W128 口径出口金 27.3 引自 deep_read/W128_单局复盘_给用户.md

用法: uv run python tools/cw/proofs/w137_p10_exit_gold_floor.py
"""
from __future__ import annotations

import json
import statistics
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
    STREAK_GOLD_TABLE,
    streak_gold,
)
from sr_od.application.currency_war.cw_horizon import (  # noqa: E402
    NODES_PER_PLANE,
    TOTAL_NODES,
)
from sr_od.application.currency_war.cw_state import (  # noqa: E402
    XP_CLICK_COST_FALLBACK,
    XP_TO_NEXT_LEVEL,
    sell_refund,
)

W135 = (ROOT / '.debug' / 'temp' / 'currency_war' / 'w135_crosscheck'
        / 'metrics_w135.json')
HP_TO_GOLD = 0.5        # registry.hp_to_gold(P3:4.4HP≈2.2金)
H3 = {0: 0.139, 1: 0.416, 2: 0.778}   # registry.h3_win_rate(P3 配套阶梯)
RECOVERY = 3.0          # registry.interest_recovery_rounds(ADR-0352)
INTEREST_CAP = 5        # registry.interest_cap([17] 50 息律)
#: Δ池硬节点掉血桶均值(w135 checks: encounter 桶9 -17.7 / boss 桶9 -24.9)
HP_LOSS_ENCOUNTER = 17.7
HP_LOSS_BOSS = 24.9
W128_EXIT_MEAN = 27.3   # W128 单局复盘(deep_read,faa66abc 前链同种子批)


def interest(g: int) -> int:
    """每轮利息 = min(5, gold//10)([17] 50 息律)。"""
    return min(INTEREST_CAP, max(0, g) // 10)


def carry_premium(g0: int, net_income: float, r_left: int) -> float:
    """P1 出口多留 1 金的利息溢价(金/金)。

    T(g0) = 该金在 50 息帽下继续吃息的期望轮数
          = min((50−g0)/净收入率, 剩余节点)
    溢价 = 0.1 × T(线性段每金每轮 0.1 金)。
    """
    t = min((50 - g0) / net_income, r_left)
    return 0.1 * max(0.0, t)


def interest_cost_recovery(gold: int, cost: int) -> float:
    """ADR-0352 回档口径 C_interest(跨档数 × min(R跨位面, 3);P1 末段近似)。"""
    tiers = gold // 10 - (gold - cost) // 10
    r_eff = min(TOTAL_NODES - NODES_PER_PLANE, RECOVERY)
    return float(max(0, tiers) * r_eff)


def p1_exit_account() -> None:
    print('=' * 72)
    print('① P1 出口 1 金的携带溢价(利息通道;净收入率带宽 6-8 金/轮)')
    r_left = TOTAL_NODES - NODES_PER_PLANE
    print(f'   P1 出口后剩余节点 = P2+P3 = {r_left}')
    print(f'   净收入率假设: 基础 {BASE_REWARD_GOLD}/轮 + 连胜金期望'
          f'(表 {STREAK_GOLD_TABLE};e1 胜率 {H3[1]} 期望 ≈1.7)→ 6.7 取带 6-8')
    print(f'   {"出口金 g0":>10} {"T(g0)@6":>8} {"T(g0)@8":>8} '
          f'{"溢价@6":>7} {"溢价@8":>7}')
    for g0 in (0, 10, 20, 30, 40, 49):
        p6 = carry_premium(g0, 6.0, r_left)
        p8 = carry_premium(g0, 8.0, r_left)
        t6 = min((50 - g0) / 6.0, r_left)
        t8 = min((50 - g0) / 8.0, r_left)
        print(f'   {g0:>10} {t6:>8.1f} {t8:>8.1f} {p6:>7.2f} {p8:>7.2f}')
    print('   → 携带溢价上界 0.1×min(50/6,18)≈0.83(g0=0);g0≥20 后 <0.5;'
          '利息通道撑不起 40+ 底线。')


def p2_tempo_table() -> None:
    print('=' * 72)
    print('② P2 早段节奏的整笔金需求(保险项量化,表值)')
    lv78 = XP_TO_NEXT_LEVEL[7] // 4 * XP_CLICK_COST_FALLBACK
    lv89 = XP_TO_NEXT_LEVEL[8] // 4 * XP_CLICK_COST_FALLBACK
    print(f'   升 7→8 需 XP {XP_TO_NEXT_LEVEL[7]} = '
          f'{XP_TO_NEXT_LEVEL[7] // 4} 击 × {XP_CLICK_COST_FALLBACK} 金 = {lv78} 金')
    print(f'   升 8→9 需 XP {XP_TO_NEXT_LEVEL[8]} = '
          f'{XP_TO_NEXT_LEVEL[8] // 4} 击 × {XP_CLICK_COST_FALLBACK} 金 = {lv89} 金')
    print(f'   P2-1 找主C(_expected_level:2-1 即 7;升 8 {lv78} 金'
          f'+4费核心 1 张 ≈ {lv78 + 4} 金起)')
    print('   → P2 首窗「能动作」的流动性下限 ≈ 1-2 击经验+1 张 3费+2 刷 ≈ 15-20 金;'
          '整窗重投 ≈ 50-60 金。出口金 <20 ⇒ P2-1 零响应(局70 病理)。')


def hard_node_win_account() -> None:
    print('=' * 72)
    print('③ 硬节点(遭遇 r7 / boss r9)赢下 vs 折断的边际账(金当量)')
    for name, hp_l, remaining in (('遭遇r7', HP_LOSS_ENCOUNTER, 2),
                                  ('boss r9', HP_LOSS_BOSS, 0)):
        v_hp = hp_l * HP_TO_GOLD
        lo = (streak_gold(2) - 1) * remaining * H3[1]
        hi = (streak_gold(6) - 1) * remaining * H3[1]
        print(f'   {name}: 免掉血 {v_hp:.1f} 金 + 连胜续期 '
              f'{lo:.2f}-{hi:.2f} 金(胜率 {H3[1]} 加权)')
    print(f'   C 侧: boss 窗多花 5 金的息损 = 跨档数×min(R跨位面,{RECOVERY})'
          ' ≤ 3 金(ADR-0352 回档口径)。'
          'boss r9 时 remaining=0 → 连胜续期=0,支柱只剩免掉血项。')


def streak_floor_calibration() -> None:
    print('=' * 72)
    print('④ discipline._streak_floor 旧账 vs 标定账(fire 条件对照)')
    print('   旧: reward=(tier−1)×plane_remaining(平面全胜上界) vs cost=0.25(魔数)')
    print(f'   {"streak":>7} {"轮":>3} {"rem":>4} {"旧reward":>8} '
          f'{"新reward(胜率加权)":>16} {"C(g=15)":>8} {"C(g=25)":>8}')
    for streak in (2, 4, 5, 6):
        for rnd in (6, 7):
            rem = max(0, NODES_PER_PLANE - rnd)
            tier = streak_gold(streak)
            old_r = (tier - 1) * rem
            new_r = (tier - 1) * rem * H3[1]
            print(f'   {streak:>7} r{rnd} {rem:>4} {old_r:>8.1f} '
                  f'{new_r:>16.2f} {interest_cost_recovery(15, 5):>8.1f} '
                  f'{interest_cost_recovery(25, 5):>8.1f}')
    print('   → 旧账 r7 遭遇恒 fire(reward≥2>0.25);只算连胜金的标定账'
          'reward 0.83-2.50(胜率加权)——但③表明真支柱是免掉血项'
          '(8.8-12.4 金,旧账漏计),补上后 floor-5 授权在硬节点+连胜在手带'
          '仍为 EV 正。')


def sim_gap() -> None:
    print('=' * 72)
    print('⑤ sim 出口金均值与分布结构(w135 seeds 0-99,池 bab146c68c5df11a)')
    if not W135.exists():
        print(f'   [跳过] 账本不存在: {W135}')
        return
    m = json.loads(W135.read_text(encoding='utf-8'))
    ps = m['per_seed']
    eg = [s['exit_gold'] for s in ps]
    hp = [s['final_hp'] for s in ps]
    n = len(ps)
    mx, my = statistics.mean(eg), statistics.mean(hp)
    cov = sum((a - mx) * (b - my) for a, b in zip(eg, hp, strict=True)) / n
    r = cov / (statistics.pstdev(eg) * statistics.pstdev(hp))
    print(f'   exit_gold mean={mx:.2f}(W128 口径 {W128_EXIT_MEAN});'
          f' final_hp mean={my:.2f}; pearson r(exit,hp)={r:.3f}')
    for lo, hi in ((0, 10), (10, 20), (20, 30), (30, 50), (50, 70)):
        b = [s for s in ps if lo <= s['exit_gold'] < hi]
        if not b:
            continue
        hpm = statistics.mean(s['final_hp'] for s in b)
        hp0 = sum(1 for s in b if s['final_hp'] == 0) / len(b)
        fok = sum(1 for s in b if s['first_form_ok_round'] is not None)
        print(f'   exit[{lo:>2},{hi:>3}) n={len(b):>3} hp_mean={hpm:5.1f} '
              f'hp0_share={hp0:.2f} form_ok_ever={fok}')
    alive = [s['exit_gold'] for s in ps if s['final_hp'] > 0]
    dead = [s['exit_gold'] for s in ps if s['final_hp'] == 0]
    print(f'   存活局(hp>0) n={len(alive)} exit_mean='
          f'{statistics.mean(alive):.2f} | 死亡局 n={len(dead)} exit_mean='
          f'{statistics.mean(dead):.2f}')
    print(f"   form_ok_ever={m['headline']['form_ok_ever']['k']}/100; "
          f"exit>=50: {m['headline']['p1_exit_gold_ge50']['k']}/100; "
          f"p1_pass_dual={m['headline']['p1_pass_dual']['k']}/100")


def refundable_channel() -> None:
    print('=' * 72)
    print('⑥ 出口财富口径:袋子金 vs 可回收 1★(卖出全额退)')
    for cost in (1, 2, 3, 4, 5):
        print(f'   {cost}费 1★: 买 {cost} 金 → 卖回 {sell_refund(1, cost)} 金'
              f'(净 {sell_refund(1, cost) - cost}); '
              f'2★: 买 {cost * 3} → 卖回 {sell_refund(2, cost)}'
              f'(净 {sell_refund(2, cost) - cost * 3})')
    print('   → 1★卡=活期金(净0),出口金底线只对**沉没通道**(经验/刷新/'
          '2★合成)有约束力。')


if __name__ == '__main__':
    p1_exit_account()
    p2_tempo_table()
    hard_node_win_account()
    streak_floor_calibration()
    sim_gap()
    refundable_channel()
