"""P70 发射帧溢出段花费弱支配留存·数值自检脚本。

命题: 溢出段 D_ovf = {(g, spend): g > g*, spend ≤ g − g*} 上息损
L(g, spend, R, Ī) ≡ 0(零息死仓构造,弱支配的息账项),零自由参数。
本脚本直调生产单一源复核(kernel 禁第二实现):
- loss_exact / interest / saturation_line: src/sr_od/application/currency_war/
  kernel/cw_economy.py(P47 命题 2 双轨迹递推);
- 掉血锚 S(n): cw_registry.streak_floor_loss_damage(辖域声明面,不入推导);
- boss P15v2 锚 26.79 [24.25, 29.23]: p15 冻结语料值直录(math_proofs P15)。

重跑: $env:PYTHONPATH='src'; uv run python tools/cw/proofs/p70_check.py
"""
import itertools
import sys

from sr_od.application.currency_war.kernel.cw_economy import (
    interest,
    loss_exact,
    saturation_line,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
)

OVERFLOW_OFFSET_MAX = 120   # 溢出量扫描上界(g = g* + 1 .. g* + 120)
INCOME_BAND = range(4, 10)  # Ī 带 4-9(p47 A3 低带含败轮金口径)
ROUNDS_MAX = 12             # R 扫描 0-12(P1=9/P2=7/P3=9 全覆盖)
# boss P15v2 冻结语料锚(math_proofs P15 行,p15/p15v2_fit.py 冻结产物直录)
BOSS_P15V2_POINT, BOSS_P15V2_LO, BOSS_P15V2_HI = 26.79, 24.25, 29.23


def check_overflow_zero_interest_loss() -> int:
    """断言 1: 溢出段全域 L(g, spend, R, Ī) ≡ 0(侧 1 的直证复算)。

    网格: cap ∈ {5(默认), 9(开源节流), 10(利息上调)} × 溢出量
    1-120 × spend 采样 × R 0-12 × Ī 4-9。spend 全量扫描在 120 溢出量
    网格下是 O(Σ offset) ≈ 7260 值/格,乘 R/Ī 后仍秒级,故取全量。
    """
    n = 0
    for cap, offset, rounds, ibar in itertools.product(
            (5, 9, 10), range(1, OVERFLOW_OFFSET_MAX + 1),
            range(0, ROUNDS_MAX + 1), INCOME_BAND):
        g = saturation_line(cap) + offset
        # spend 全量: 花后仍守线的每一步都在辖域(spend ≤ g − g* = offset)
        for spend in range(1, offset + 1):
            got = loss_exact(g, spend, rounds, ibar, cap=cap)
            assert got == 0, (
                f'溢出段息损非零: cap={cap} g={g} spend={spend} '
                f'R={rounds} I={ibar} -> L={got}')
            n += 1
    print(f'[断言1] 溢出段息损恒零: 全网格 {n} 格 L=0 ✓')
    return n


def check_band_contrast() -> None:
    """断言 2: 出辖对照——带内格息损 > 0,划出 D_ovf 边界。"""
    cap = 5
    g_star = saturation_line(cap)
    # (g=50, spend=10): A₀=40 掉一档,R=1 即有息差
    got = loss_exact(g_star, 10, 1, 7, cap=cap)
    assert got == 1, f'带内对照格预期 L=1, 实得 {got}'
    # 贴辖域边界: g=51 花 1(仍在溢出段)→ 息损 0;花 2(穿线)→ 可能非零
    assert loss_exact(g_star + 1, 1, 1, 7, cap=cap) == 0
    crossing = loss_exact(g_star + 1, 2, 3, 7, cap=cap)
    assert crossing > 0, f'穿线格预期 L>0, 实得 {crossing}'
    # 息帽封顶直觉锚: g* 处 interest 已封顶,溢出段增量零息
    assert interest(g_star, cap) == cap
    assert interest(g_star + 100, cap) == cap
    print(f'[断言2] 出辖对照: 带内 L={got}>0, 穿线 L={crossing}>0,'
          f' 溢出段贴线格 L=0, 息帽封顶 interest(g*)=cap ✓')


def check_registry_anchors() -> None:
    """断言 3: 掉血锚 S(n) 与注册表单一源对账(辖域声明面,禁第二份)。"""
    dmg = DEFAULT_REGISTRY.streak_floor_loss_damage
    assert dmg['encounter'][0] == 24.32, f"encounter 截距漂移: {dmg['encounter'][0]}"
    assert dmg['encounter'][1] == -4.53
    assert dmg['boss'][0] == 26.71
    assert dmg['boss'][1] == 0.0
    assert BOSS_P15V2_LO <= BOSS_P15V2_POINT <= BOSS_P15V2_HI
    # 全锚非负: 侧 3「掉血不变多」单调性的数值面
    for name, (intercept, _slope) in dmg.items():
        assert intercept > 0, f'{name} 掉血锚非正'
    print("[断言3] 掉血锚对账: encounter=(24.32,-4.53) boss=(26.71,0.0) "
          f"registry 一致; boss P15v2 锚 {BOSS_P15V2_POINT} "
          f"∈ [{BOSS_P15V2_LO}, {BOSS_P15V2_HI}] ✓")


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    check_overflow_zero_interest_loss()
    check_band_contrast()
    check_registry_anchors()
    print('\n全部断言通过。')


if __name__ == '__main__':
    main()
