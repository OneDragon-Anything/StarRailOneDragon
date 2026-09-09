"""P89 换血持续预算的离散锚·复算脚本。

命题(docs/develop/currency_war/proofs/p89.md;math_proofs.md P89 行):
带源 = 真人尺保留率带 [0.59, 0.74](stage_transitions Q2)⟹
- 正典式(卖出率): n_swap/9 ∈ [0.26, 0.41] ⟹ n_swap = {3}(整数唯一解);
- 等价形(保留率): (9−n_swap)/9 ∈ [0.59, 0.74] ⟹ n_swap = {3}(互补恒等);
- 交叉核(过渡件分母): n_swap/8 ∈ [0.26, 0.41] ⟹ n_swap = {3};
- 折算: 3 件 / 4 轮 = 0.75 次/轮(A/B 预注册线,禁入代码闸门);
- 锚④反例自检: n=3 两正形式皆过;n=6 两正形式皆拒;v1 已废错误式
  |9−n|/9 ∈ [0.26,0.41] 的整数解恰为 {6}(与结论自斥,勘误注在册)。

零自由参数;算术用 Fraction 精确有理数,无浮点边差。带源文件 live-read
(仓库持久文件,防带值漂移);三批 sim 报告住 .debug/temp/(易失),实测数字
只作对账不进推导。

重跑: $env:PYTHONPATH='src'; uv run python tools/cw/proofs/p89_check.py
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

from sr_od.application.currency_war.kernel.cw_state import BENCH_CAPACITY

BOARD_N = 9        # 板分母(单一源断言在断言 8:BENCH_CAPACITY == 9)
TRANSITION_N = 8   # 过渡件分母(线外 8 件,探针双读法)
SELL_LO, SELL_HI = Fraction(26, 100), Fraction(41, 100)      # 卖出率带 [0.26, 0.41]
KEEP_LO, KEEP_HI = Fraction(59, 100), Fraction(74, 100)      # 保留率带 [0.59, 0.74]
BAND_SOURCE = Path(__file__).resolve().parents[3] / (
    'docs/game/currency_war/research/stage_transitions.md')


def in_band(x: Fraction, lo: Fraction, hi: Fraction) -> bool:
    return lo <= x <= hi


def check_canonical_form() -> None:
    """断言 1: 正典式(卖出率)对 n∈0..9 逐个判定,唯一解 n=3。"""
    solutions = [n for n in range(BOARD_N + 1)
                 if in_band(Fraction(n, BOARD_N), SELL_LO, SELL_HI)]
    assert solutions == [3], f'正典式解集 {solutions} ≠ [3]'
    detail = {n: str(Fraction(n, BOARD_N)) for n in (2, 3, 4)}
    print(f'[断言1] 正典式 n/9∈[0.26,0.41]: n∈0..9 逐个判定,解集 {{3}} 唯一 '
          f'(n=2: {detail[2]} 出带 / n=3: {detail[3]} 带内 / n=4: {detail[4]} 出带) PASS')


def check_equivalent_form() -> None:
    """断言 2: 等价形(保留率)对 n∈0..9 逐个判定,唯一解 n=3。"""
    solutions = [n for n in range(BOARD_N + 1)
                 if in_band(Fraction(BOARD_N - n, BOARD_N), KEEP_LO, KEEP_HI)]
    assert solutions == [3], f'等价形解集 {solutions} ≠ [3]'
    detail = {n: str(Fraction(BOARD_N - n, BOARD_N)) for n in (2, 3, 4)}
    print(f'[断言2] 等价形 (9−n)/9∈[0.59,0.74]: n∈0..9 逐个判定,解集 {{3}} 唯一 '
          f'(n=2: 留 {detail[2]} 超上限 / n=3: 留 {detail[3]} 带内 / n=4: 留 {detail[4]} 破下缘) PASS')


def check_cross_denominator() -> None:
    """断言 3: 交叉核(过渡件分母 8)对 n∈0..9 逐个判定,唯一解 n=3。"""
    solutions = [n for n in range(BOARD_N + 1)
                 if in_band(Fraction(n, TRANSITION_N), SELL_LO, SELL_HI)]
    assert solutions == [3], f'交叉核解集 {solutions} ≠ [3]'
    assert Fraction(3, TRANSITION_N) == Fraction(3, 8)
    lo, hi = SELL_LO * TRANSITION_N, SELL_HI * TRANSITION_N
    assert lo == Fraction(52, 25) and hi == Fraction(164, 50), '带端点×8 算术漂移'
    assert Fraction(104, 50) <= 3 <= Fraction(164, 50)
    print('[断言3] 交叉核 n/8∈[0.26,0.41]: 解集 {3} 唯一;n∈[2.08, 3.28];'
          '3/8 = 0.375 与探针实测 37.5% 一致(两分母读法收敛) PASS')


def check_complement_identity() -> None:
    """断言 4: 两带互补恒等 1−[0.26,0.41] = [0.59,0.74](正典式 ⟺ 等价形)。"""
    assert Fraction(1, 1) - SELL_HI == KEEP_LO, '1−0.41 ≠ 0.59'
    assert Fraction(1, 1) - SELL_LO == KEEP_HI, '1−0.26 ≠ 0.74'
    # 区间减法逐端点 ⟹ 两式同解集(断言 1/2 解集一致即其数值面)
    print('[断言4] 互补恒等: 1−[0.26,0.41] = [0.59,0.74] 逐端点成立,'
          '正典式与等价形同解集 PASS')


def check_worked_fractions() -> None:
    """断言 5: 逐例分数写准(勘误注面:禁把保留率分数写成卖出率分数)。"""
    assert in_band(Fraction(3, 9), SELL_LO, SELL_HI), '卖 3/9 应带内'
    assert in_band(Fraction(6, 9), KEEP_LO, KEEP_HI), '留 6/9 应带内'
    assert Fraction(7, 9) > KEEP_HI, '留 7/9 应超 0.74 上限'
    assert Fraction(5, 9) < KEEP_LO, '留 5/9 应破 0.59 下缘'
    assert Fraction(3, 9) == Fraction(1, 3) and Fraction(6, 9) == Fraction(2, 3)
    print('[断言5] 逐例分数: 换3=卖3/9≈0.33 带内+留6/9≈0.67 带内;'
          '换2=留7/9≈0.78 超上限;换4=留5/9≈0.56 破下缘 PASS')


def check_counterexample_n6() -> None:
    """断言 6(批 A 验收锚④): n=3 满足两正形式;n=6 两正形式皆拒。"""
    for n, want in ((3, True), (6, False)):
        sell_ok = in_band(Fraction(n, BOARD_N), SELL_LO, SELL_HI)
        keep_ok = in_band(Fraction(BOARD_N - n, BOARD_N), KEEP_LO, KEEP_HI)
        assert sell_ok == want and keep_ok == want, (
            f'锚④失败: n={n} 正典式={sell_ok} 等价形={keep_ok} 预期 {want}')
    # n=6 拒斥数值: 卖 6/9≈0.67 ∉ 卖出率带;留 3/9≈0.33 ∉ 保留率带
    assert Fraction(6, 9) > SELL_HI and Fraction(3, 9) < KEEP_LO
    print('[断言6] 锚④反例自检: n=3 两正形式皆过;n=6 两正形式皆拒 '
          '(卖 6/9≈0.67 ∉ [0.26,0.41],留 3/9≈0.33 ∉ [0.59,0.74]) PASS')


def check_v1_deprecated_form_self_refutes() -> None:
    """断言 7: v1 已废错误式 |9−n|/9 ∈ [0.26,0.41] 的整数解恰为 {6}(自斥演示)。"""
    solutions = [n for n in range(BOARD_N + 1)
                 if in_band(Fraction(abs(BOARD_N - n), BOARD_N), SELL_LO, SELL_HI)]
    assert solutions == [6], f'v1 废式解集 {solutions} ≠ [6]'
    lo, hi = SELL_LO * BOARD_N, SELL_HI * BOARD_N
    assert Fraction(117, 50) <= BOARD_N - 6 <= Fraction(333, 50)
    assert abs((9 - float(hi)) - 5.31) < 1e-9 and abs((9 - float(lo)) - 6.66) < 1e-9
    # 废式(保留率公式配卖出率带)唯一解 6 ≠ 结论 3 = 自斥,已废(勘误注在册)
    print(f'[断言7] v1 废式自斥演示: |9−n|/9∈[0.26,0.41] ⟹ |9−n|∈[{float(lo)}, {float(hi)}] '
          f'⟹ n∈[{round(9 - float(hi), 2)}, {round(9 - float(lo), 2)}] ⟹ 解集 {{6}} ≠ 结论 {{3}}'
          f'——保留率式配卖出率带,照式即自斥,已废 PASS')


def check_conversion_and_endpoints() -> None:
    """断言 8: 折算 0.75 次/轮与带端点算术 + 板分母单一源(F8-1 处置,
    与 p88_check 断言 7 同标:BENCH_CAPACITY 直调断言)。"""
    assert BENCH_CAPACITY == BOARD_N, \
        f'板分母单一源漂移: BENCH_CAPACITY={BENCH_CAPACITY} ≠ {BOARD_N}'
    assert Fraction(3, 4) == Fraction(75, 100), '3 件/4 轮 = 0.75'
    assert Fraction(75, 100) * 4 == 3, '0.75×4 轮 = 3 件'
    assert Fraction(117, 50) == SELL_LO * BOARD_N and Fraction(369, 100) == SELL_HI * BOARD_N
    assert Fraction(52, 25) == SELL_LO * TRANSITION_N, '0.26×8 ≠ 2.08'
    assert Fraction(41, 25) * 2 == SELL_HI * TRANSITION_N, '0.41×8 ≠ 3.28'
    print('[断言8] 折算与端点: 3/4=0.75 次/轮(预注册线,禁入代码闸门);'
          '0.26×9=2.34、0.41×9=3.69、0.26×8=2.08、0.41×8=3.28;'
          'BENCH_CAPACITY=9(单一源断言) PASS')


def check_band_source_live() -> None:
    """断言 9: 带源 live-read——stage_transitions.md 在册带值防漂移。"""
    text = BAND_SOURCE.read_text(encoding='utf-8')
    assert '保留率 0.59-0.74' in text, '带源 :195 保留率带漂移或缺失'
    assert '保留率才是「卖没卖过渡」的正确读数' in text, '带源 :92-93 读数口径缺失'
    assert '|E|均值 4.7' in text, '带源 |E|≈4.7 板数据缺失'
    rel = BAND_SOURCE.relative_to(Path(__file__).resolve().parents[3])
    print(f'[断言9] 带源 live-read: {rel} 含「保留率 0.59-0.74」(:195)、'
          f'「保留率才是正确读数」(:92-93)、|E|≈4.7 —— 带值与仓库单一源一致 PASS')


_CHECKS = (
    ('正典式', check_canonical_form),
    ('等价形', check_equivalent_form),
    ('交叉核', check_cross_denominator),
    ('互补恒等', check_complement_identity),
    ('逐例分数', check_worked_fractions),
    ('锚④反例', check_counterexample_n6),
    ('v1废式自斥', check_v1_deprecated_form_self_refutes),
    ('折算与端点', check_conversion_and_endpoints),
    ('带源live-read', check_band_source_live),
)


def main() -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print('P89 复算:换血持续预算的离散锚(A/B 预注册线的推导载体)')
    print('=' * 72)
    for name, fn in _CHECKS:
        try:
            fn()
        except AssertionError as exc:
            print(f'[FAIL] {name}: {exc}')
            return 1
    print('=' * 72)
    print('P89 复算:全部断言通过(9/9 PASS)。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
