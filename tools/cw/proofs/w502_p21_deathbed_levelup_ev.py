"""P21 · P2 濒死 CwActionLevelUpParam 雨的期望收益模型(可重跑计算脚本)。

命题(math_proofs P21):hp ≤ H0(P2 濒死段)时连发 CwActionLevelUpParam 换人口的期望收益为负;
判据形式给出「升级不再负」的参数域。模型与常量出处见单篇
docs/game/currency_war/research/proofs/p21-p2-deathbed-levelup-ev.md。

模型:
- 一次升级burst(跨 1 级)= k 次单击 × 单击价 c;等级点击数 = ceil(XP_TO_NEXT_LEVEL[lv]/XP_PER_BUY)
  (cw_state 注册表真值)。收益 = +1 人口 → 边际胜率 Δp,到账延迟 d 轮。
- 掉血轴:濒死段 hp ≤ H0 < L_c(P2 条件败局伤害经验下界)⇒ 任一败局即死,
  存活要求剩余 B_r 场全胜。升级只影响到账后的 m = B_r − d 场:
  S0 = p^B_r,S1 = p^d · p'^m,ΔS = S1 − S0。
- EV = ΔS·V_live − C − I;I = 利息损失(破息 5金/轮 × min(d, 存活备战轮)),
  g−C ≥ 50 时 I=0(P3 溢余段零息损)。
- 对照域(非濒死,h > d·L_c):收益 = Δp · Σ_{b≥d} L_c·S(b)(逐场避免的条件伤害),
  判据 = 该和 > C + I。
"""
import itertools
import json
import math

# —— 机制常量(cw_state 注册表镜像;单一源在 src/sr_od/application/currency_war/kernel/cw_state.py)——
XP_PER_BUY = 4
XP_TO_NEXT_LEVEL = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}
INTEREST_FLOOR = 50
INTEREST_PER_ROUND = 5

# —— 语料标定(.debug/temp/currency_war/w502_deathbed_levelup/damage_dist.json;W502)——
H0 = 10                      # 濒死段阈值(命题主域;W490 §三-5 判读口径)
L_C = 15.39                  # P2 条件败局伤害经验均值(loss-only,n=92 败样本/114 场)
L_C_LB = 9.0                 # 濒死非截断伤害下界(保守取 p2_hp_le_20 max;濒死桶被死亡截断不可用)
P_BASE = 0.19                # P2 语料胜率(1−loss_rate 0.807;弱板语料=濒死人群同族)


def clicks_to_level(level: int) -> int:
    need = XP_TO_NEXT_LEVEL.get(level, 84)
    return max(1, math.ceil(need / XP_PER_BUY))


def deathbed_ev(p: float, dp: float, d: int, b: int, cost: float, v_live: float,
                interest: bool = True, g: float = 60.0) -> float:
    """濒死域(hp≤H0<L_C)连发升级的期望收益。"""
    if b - d <= 0:
        return -cost  # 到账前已无战斗:纯支出
    s0 = p ** b
    s1 = (p ** d) * ((p + dp) ** (b - d))
    i = 0.0
    if interest and g - cost < INTEREST_FLOOR:
        i = INTEREST_PER_ROUND * min(d, 3)
    return (s1 - s0) * v_live - cost - i


def alive_domain_ev(p: float, dp: float, d: int, b: int, cost: float,
                    l_c: float = L_C, g: float = 60.0) -> float:
    """对照域(h > d·L_c):升级到账后逐场避免的条件伤害期望 − 成本。"""
    if b - d <= 0:
        return -cost
    benefit = 0.0
    # 逐场存活概率(到账前每场以 p 活下来)
    surv = 1.0
    for j in range(b):
        if j >= d:
            benefit += dp * l_c * surv
            surv *= (p + dp)  # 简化:受益场存活率用升级后胜率
        else:
            surv *= p
    i = INTEREST_PER_ROUND * min(d, 3) if g - cost < INTEREST_FLOOR else 0.0
    return benefit - cost - i


def main() -> None:
    out: dict = {'model': 'p21', 'H0': H0, 'L_C': L_C, 'P_BASE': P_BASE}

    # ① 濒死域主表:等级 × 到账延迟(Δp=P20 口径 +11.7pp;V_live 取 300 金当量≈P3 全程经济)
    print('=== ① 濒死域(hp≤10)EV 主表:V_live=300, Δp=0.12, p=0.19 ===')
    print(f"{'等级跨度':<10}{'点击数':>6}{'C(c=4)':>8}{'d=0':>10}{'d=1':>10}{'d=2':>10}{'B=6':>6}")
    grid = []
    for lv in (5, 6, 7, 8):
        k = clicks_to_level(lv)
        row = [deathbed_ev(P_BASE, 0.12, d, 6, k * 4, 300.0) for d in (0, 1, 2)]
        grid.append({'lv': lv, 'lv_next': lv + 1, 'clicks': k, 'cost_c4': k * 4,
                     'ev_d0': row[0], 'ev_d1': row[1], 'ev_d2': row[2]})
        print(f"lv{lv}->lv{lv+1:<4}{k:>6}{k*4:>8}" + ''.join(f'{v:>10.2f}' for v in row))
    out['deathbed_main'] = grid

    # ② 濒死域翻正所需 V_live*(break-even):EV=0 ⟺ V_live* = (C+I)/ΔS
    print('\n=== ② 翻正所需存活价值 V_live*(Δp=0.12, B=6, p=0.19, c=4) ===')
    be = []
    for lv in (6, 7, 8):
        for d in (0, 1, 2):
            cost = clicks_to_level(lv) * 4
            i = INTEREST_PER_ROUND * min(d, 3)
            s0 = P_BASE ** 6
            s1 = (P_BASE ** d) * ((P_BASE + 0.12) ** (6 - d))
            delta_s = s1 - s0
            v_star = (cost + i) / delta_s if delta_s > 0 else float('inf')
            be.append({'lv': lv, 'd': d, 'delta_S': round(delta_s, 6), 'v_live_star': round(v_star, 1)})
            print(f"lv{lv}->lv{lv+1} d={d}: ΔS={delta_s:.6f}  V_live*={v_star:.0f} 金当量")
    out['break_even_v_live'] = be

    # ③ 敏感性:结论在 (p, Δp, d, c) 网格上是否恒负(B=6, V_live=300)
    print('\n=== ③ 敏感性网格:濒死域 EV(V_live=300, B=6);cell=最不利参数组合最大值 ===')
    worst = -math.inf
    worst_at = None
    all_neg = True
    for p, dp, d, c in itertools.product((0.10, 0.19, 0.30), (0.05, 0.12, 0.28), (0, 1, 2), (4, 6, 8)):
        ev = deathbed_ev(p, dp, d, 6, clicks_to_level(7) * c, 300.0)
        if ev > worst:
            worst, worst_at = ev, (p, dp, d, c)
        if ev >= 0:
            all_neg = False
    print(f'网格 3×3×3×3=81 cells:全部为负={all_neg};最大 EV={worst:.2f} @ p,Δp,d,c={worst_at}')
    out['sensitivity'] = {'all_negative': all_neg, 'max_ev': round(worst, 2), 'max_at': worst_at}

    # ④ 对照域(判据域):h > d·L_c 时 alive_domain_ev 何时翻正
    print('\n=== ④ 对照域判据(h > d·L_c 才谈收益):alive_domain_ev,B=6,Δp=0.12,c=4 ===')
    alive = []
    for h, d in ((16, 1), (31, 2), (10, 1)):
        for lv in (6, 7, 8):
            cost = clicks_to_level(lv) * 4
            ev = alive_domain_ev(P_BASE, 0.12, d, 6, cost)
            alive.append({'h': h, 'd': d, 'lv': lv, 'ev': round(ev, 2)})
            print(f'h={h} d={d} lv{lv}->lv{lv+1} (C={cost}): EV={ev:.2f} {"允许" if h > d*L_C and ev > 0 else "禁止"}')
    out['alive_domain'] = alive

    dst = __import__('pathlib').Path('.debug/temp/currency_war/w502_deathbed_levelup/p21_ev_results.json')
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nresults -> {dst}')


if __name__ == '__main__':
    main()
