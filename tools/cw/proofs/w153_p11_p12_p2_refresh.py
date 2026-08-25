# P11/P12 计算脚本(W153 批,零随机纯表值+回放账;可重跑复核)
#
# 用途:docs/game/currency_war/research/proofs/p11/p12 两篇的数据源。
#   - P11:溢余金(gold>50)机会成本表——interest(g)=min(g//10,5)(cw_horizon.interest
#     同式),P2 收入率 13-19 金/轮(W151 四局实测)下的回档轮数与 C_interest;
#   - P12:V_D 收益侧的 P2 存活口径(P2 实测掉血 15-17/败 × hp_to_gold=0.5
#     × 本位面剩余战斗数)vs 批口径 spend(expected_refreshes_for_card×2)。
#
# 重跑:uv run python tools/cw/proofs/w153_p11_p12_p2_refresh.py
# (需 PYTHONPATH=src;或 uv run --env-file .env)
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                '..', 'src'))

from sr_od.application.currency_war.cw_horizon import interest  # noqa: E402
from sr_od.application.currency_war.cw_shop_odds import (  # noqa: E402
    expected_refreshes_for_card,
)
from sr_od.application.currency_war.decision_v2.registry import (  # noqa: E402
    DecisionV2Registry,
)

REG = DecisionV2Registry()

# ---- P2 实测锚(W151 四局 / W152 回放,数据边界=4 局 87 条 P2 记录 14 shop 帧) ----
P2_LOSS_RANGE = (15, 17)        # P2 每败掉血(W151:1 胜 8 败,每败 15-17)
P2_INCOME_RANGE = (13, 19)      # P2 金堆积速率(W152:金按 +13~19/轮堆到死)
P2_GOLD_FRAMES = (85, 160)      # 四局 P2 shop 帧金区间(W152)
SPEND_FRAMES = (42, 135)        # 批口径 spend 区间(W152 实算)
NODES_PER_PLANE = 9             # cw_horizon.NODES_PER_PLANE

XP_CLICK = 4                    # cw_state.XP_CLICK_COST_FALLBACK(升级单击价)
INTEREST_CAP = 5                # 满息 5 金/轮
HP_TO_GOLD = REG.hp_to_gold     # 0.5
DRUNG_12 = REG.rung_value[2] - REG.rung_value[1]        # 1.6
DWIN_12 = REG.h3_win_rate[2] - REG.h3_win_rate[1]      # 0.362


def fmt(x: float) -> str:
    return f'{x:.1f}'


def p11_table() -> None:
    """溢余金机会成本:C_interest(g,s) 与回档轮数(P2 收入率口径)。"""
    print('=' * 72)
    print('P11 溢余金机会成本:interest(g)=min(g//10,5);P2 收入 13-19/轮')
    print('=' * 72)
    print(f"{'g':>4} {'s':>4} | {'息前':>4} {'息后':>4} {'Δ档':>4}"
          f" {'回档轮@13':>9} {'回档轮@19':>9} {'C_int上界':>9}")
    for g in (85, 100, 120, 160):
        for s in (42, 60, 90, 135):
            if s > g:
                continue
            i0, i1 = interest(g), interest(g - s)
            dt = i0 - i1
            if dt == 0:
                rec13 = rec19 = 0.0
            else:
                # 回到花前息档需补的缺口 = 被打穿到 50 线以下的部分
                gap = max(0, min(g, 50) - (g - s)) if g - s < 50 else 0
                gap = max(gap, dt * 10)  # 至少补 Δ档×10
                rec13 = gap / P2_INCOME_RANGE[0]
                rec19 = gap / P2_INCOME_RANGE[1]
            c_int_ub = dt * max(rec13, 1.0)  # 上界=Δ档×回档轮(≥Δ档×1)
            print(f'{g:>4} {s:>4} | {i0:>4} {i1:>4} {dt:>4}'
                  f' {rec13:>9.2f} {rec19:>9.2f} {c_int_ub:>9.1f}')
    print()
    print('对照:批口径把成本记为 spend 面值(s 本身)。')
    for g, s in ((85, 42), (100, 60), (120, 90), (160, 135)):
        i0, i1 = interest(g), interest(g - s)
        dt = i0 - i1
        # 面值/真实息机会成本 的比值(息通道)
        c = dt * 2.0  # 回档 ≤2 轮的折中(P6 下界/P2 高收入 → 更短)
        print(f'  g={g} spend={s}:面值 {s} vs 息通道机会成本 ≤{fmt(c)}'
              f' → 批口径高估 ≥{fmt(s / c) if c else "∞"}×'
              f'{" (纯溢余,Δ档=0,C=0)" if dt == 0 else ""}')


def p12_table() -> None:
    """V_D 收益侧:P1 口径(registry 骨架)vs P2 存活口径;对照批口径 spend。"""
    print()
    print('=' * 72)
    print('P12 V_D 收益侧口径对照(成本=expected_refreshes×2,批口径)')
    print('=' * 72)
    # P1 口径(现行 scoring.vd_refresh_score):loss=10, battles=5, R=12-18
    for r in (12, 18):
        b = DRUNG_12 * r + DWIN_12 * REG.expected_battle_loss * HP_TO_GOLD * 5
        print(f'P1 口径(R={r}):benefit = 1.6×{r} + 0.362×10×0.5×5'
              f' = {fmt(b)}')
    print()
    # P2 存活口径:loss=15-17(W151), battles=P2 剩余节点(3-9), R=P2+P3 剩余
    print('P2 存活口径:benefit = 1.6×R + 0.362×loss_P2×0.5×battles_P2')
    print(f"{'R':>3} {'loss':>5} {'battles':>8} | {'benefit':>8}")
    for r in (12, 18):
        for loss in P2_LOSS_RANGE:
            for battles in (3, 5, 7, 9):
                b = DRUNG_12 * r + DWIN_12 * loss * HP_TO_GOLD * battles
                print(f'{r:>3} {loss:>5} {battles:>8} | {b:>8.1f}')
    print()
    # 临界:battles 使 P2 口径超批口径 spend 的 j=2 帧
    print('批口径 spend(expected_refreshes_for_card star=2):')
    print(f"{'lv':>3} {'cost':>5} | {'E(j=0)':>8} {'E(j=1)':>8} {'E(j=2)':>8}"
          f" | {'spend(j=2)':>11}")
    for lv in (5, 6, 7, 8):
        for cost in (2, 3):
            es = [expected_refreshes_for_card(lv, cost, 2, owned=j)
                  for j in (0, 1, 2)]
            print(f'{lv:>3} {cost:>5} |'
                  + ''.join(f' {e:>8.1f}' for e in es)
                  + f' | {es[2] * 2:>11.1f}')
    print()
    # 拒绝域移动:P2 口径下 j=2 帧的 V_D(成本=批 spend vs 成本=C_eff)
    print('V_D(j=2, cost=2) 拒绝域对照(benefit 取 loss=16, battles=7, R=15):')
    b_p2 = DRUNG_12 * 15 + DWIN_12 * 16 * HP_TO_GOLD * 7
    for lv in (6, 7):
        e2 = expected_refreshes_for_card(lv, 2, 2, owned=2)
        spend = e2 * 2
        print(f'  lv{lv}: benefit={fmt(b_p2)} | 批口径 V={fmt(b_p2 - spend)}'
              f' | 溢余口径(g-spend>=50)V={fmt(b_p2)}')


def main() -> None:
    p11_table()
    p12_table()


if __name__ == '__main__':
    main()
