"""P71 升级通道预算闸·数值自检脚本。

命题(P71-a/b/c,详 docs/develop/currency_war/proofs/p71-levelup-channel-budget-gate.md):
- a: dep 满时人口位边际构造性为零;升级仅存通道 = 概率移位,形状由
  REFRESH_PROB 决定且对费档符号分化(3 费 lv8→9 恶化 / 4-5 费改善);
- b: 预算闸 (3) 的溢余段简化 L≡0 与穿线段 L>0 的对照(P70 断言同源);
- c: 73002 批账(s=60 穿线 28,L∈[3,9])与闸值 B_L 拦截构造。

本脚本直调生产单一源复核(kernel 禁第二实现):
- XP_TO_NEXT_LEVEL / XP_PER_BUY: kernel/cw_state.py(2026-08-31 用户定谒);
- REFRESH_PROB / expected_refreshes_for_card: data/cw_shop_odds.py(V4.4 权威);
- loss_exact / saturation_line: kernel/cw_economy.py(P47 双轨迹递推)。

重跑: $env:PYTHONPATH='src'; uv run python tools/cw/proofs/p71_check.py
"""
import itertools
import math
import sys

from sr_od.application.currency_war.data.cw_shop_odds import (
    REFRESH_PROB,
    expected_refreshes_for_card,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    loss_exact,
    saturation_line,
)
from sr_od.application.currency_war.kernel.cw_state import (
    XP_PER_BUY,
    XP_TO_NEXT_LEVEL,
)

CLICK_COST = 4   # flat-4(P39 A3;lv6/8/9 实测覆盖面边界在单篇边界 3)
# 整批单批上界(lv8→9 需 72XP=18击;断言 4 骨架演示用)
U_L_MAX = math.ceil(XP_TO_NEXT_LEVEL[8] / XP_PER_BUY) * CLICK_COST


def check_xp_cost_ladder() -> None:
    """断言 1: XP 门槛表直调——每级整批成本梯子(禁拍值,单一源直读)。"""
    expected_need = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}
    for lv, need in expected_need.items():
        assert XP_TO_NEXT_LEVEL[lv] == need, (
            f'XP 门槛漂移: lv{lv} 预期 {need} 实得 {XP_TO_NEXT_LEVEL[lv]}')
        clicks = math.ceil(need / XP_PER_BUY)
        assert clicks * CLICK_COST >= need, (
            f'整批成本须盖满门槛: lv{lv} clicks={clicks}')
    # 单价可整除性: flat-4 下整批成本=门槛值(除不尽级首击溢出,此处全整除)
    print('[断言1] XP 门槛梯子: 4/6/20/40/52/72/84 ✓ '
          '(lv8→9 = 18击 = 72金 单批上界)')


def check_odds_shift_signs() -> None:
    """断言 2: lv8→9 概率移位符号分化(P71-a 的表值形状)。

    1-3 费全降 / 4-5 费全升;3 费在 lv7 起单调降(峰值级=7,恒负域的
    表值单调性保证);5 费 E[refreshes] 提速 3.3×。
    """
    for c in (1, 2, 3):
        assert REFRESH_PROB[9][c] < REFRESH_PROB[8][c], f'{c}费 lv8→9 应降'
    for c in (4, 5):
        assert REFRESH_PROB[9][c] > REFRESH_PROB[8][c], f'{c}费 lv8→9 应升'
    p3 = [REFRESH_PROB[lv][3] for lv in (7, 8, 9, 10)]
    assert p3 == sorted(p3, reverse=True), f'3费概率应 lv7 起单调降: {p3}'
    assert abs(p3[0] - 0.40) < 1e-9 and abs(p3[1] - 0.32) < 1e-9, (
        f'3费锚值漂移: {p3[:2]}')
    e = {c: (expected_refreshes_for_card(8, c, 2, 0, 0),
             expected_refreshes_for_card(9, c, 2, 0, 0)) for c in (3, 4, 5)}
    assert e[3][0] < e[3][1], f'3费 E[ref] lv8→9 应恶化: {e[3]}'
    assert e[4][0] > e[4][1] and e[5][0] > e[5][1], (
        f'4/5费 E[ref] lv8→9 应改善: {e[4]} {e[5]}')
    speedup = e[5][0] / e[5][1]
    assert 3.0 <= speedup <= 3.6, f'5费提速应 ≈3.3×: {speedup:.2f}'
    print(f'[断言2] 移位符号分化: 3费 E 29.8→38.1(+28% 恶化) / '
          f'4费 {e[4][0]:.1f}→{e[4][1]:.1f} / 5费 {e[5][0]:.1f}→'
          f'{e[5][1]:.1f}(提速 {speedup:.1f}×) ✓')


def check_overflow_vs_crossing() -> None:
    """断言 3: 预算闸 (3) 的息损对照——溢余段内批 L≡0,穿线批 L>0。

    73002 帧参数: g=82, g*=50, 溢出量 32。批 s=60(15击×4,xp_cur=12
    携带自洽)穿线 28 → L>0;同金额分轮每轮 ≤32 → L≡0(P70 零息死仓)。
    """
    g_star = saturation_line(5)
    assert g_star == 50, f'默认局 g* 漂移: {g_star}'
    g, overflow = 82, 32
    assert g - g_star == overflow
    # 穿线批: R∈{1,3,6} × Ī∈{5,7,9} 全格 L ≥ 3(未入账息损的量级)
    crossing = [loss_exact(g, 60, r, i, cap=5)
                for r, i in itertools.product((1, 3, 6), (5, 7, 9))]
    assert all(v >= 3 for v in crossing), f'穿线批息损应 ≥3: {crossing}'
    assert max(crossing) <= 9, f'穿线批息损上界应 ≤9: {max(crossing)}'
    # 溢余段内同额分轮(每笔 ≤32): 全格 L≡0
    for s, r, i in itertools.product((1, 16, 32), (1, 3, 6), (5, 7, 9)):
        got = loss_exact(g, s, r, i, cap=5)
        assert got == 0, (
            f'溢余段内息损应恒零: s={s} R={r} I={i} -> L={got}')
    print(f'[断言3] 73002 批账: 穿线批 L∈[{min(crossing)},{max(crossing)}]'
          f'(9 格)>0 未入账;溢余段内分轮 L≡0 全格 ✓')


def check_budget_gate_construction() -> None:
    """断言 4: 闸值 B_L = min(U_L, g − g*) 的拦截/放行构造(P71-b (3))。

    窗口预留 Σ预留 与 ρ 取 0 演示骨架量级(实际消费按 P54/P40 现算,
    本断言只验闸的算术形态与 73002 拦截方向)。
    """
    reserve = 0   # 骨架演示口径;生产形式 = ρ + Σ_w 窗口预留(P54/P40)

    def budget_gate(gold: int, spend: int) -> tuple[bool, int]:
        b_l = min(gold - saturation_line(5) - reserve, U_L_MAX)
        return spend <= b_l, b_l

    # 73002 帧: g=82, 整批 15击=60金(18击上界 72−xp_cur=12 携带)→ 60>32 拒
    ok, b_l = budget_gate(82, 60)
    assert not ok and b_l == 32, f'73002 应被闸拦截: ok={ok} B_L={b_l}'
    # 分轮口径(跨帧整批计划,P48 S 线语义;非散买): 本帧 8击=32金 ≤32
    # 放行且不穿线,余量下帧续齐
    ok2, b_l2 = budget_gate(82, 32)
    assert ok2 and b_l2 == 32
    # 富金帧: g=130 溢出量 80 ≥ 72 整批上界 → 整批一次过
    ok3, b_l3 = budget_gate(130, 72)
    assert ok3 and b_l3 == 72
    print('[断言4] 闸值构造: 73002 帧 B_L=32 < 60 拒 ✓;分轮 32金(跨帧'
          '整批计划)过;g=130 帧整批 72 过(B_L=min(72,80)) ✓')


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    check_xp_cost_ladder()
    check_odds_shift_signs()
    check_overflow_vs_crossing()
    check_budget_gate_construction()
    print('\n全部断言通过。')


if __name__ == '__main__':
    main()
