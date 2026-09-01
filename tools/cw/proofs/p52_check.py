"""P52 贪心 ε-最优性定理·数值例证脚本。

定理: 安全域 D_ε 上 |V(π_greedy) − V(π*)| ≤ ε = T·δ̄ + λ̄·E·H_eff。
本脚本只做算术例证,全部输入值逐一注明来源(无 sim/数据文件依赖):
- λ3 分层值与 CI: P51 v3 §4-B-2 表(pooled 口径,直测 3 轮累积危险率);
- 敞口 E = g + Φ: P51 v3 §4-B 表(pooled p≤7: g=74.4, Φ=+147.3);
- W_floor 参照值: P51 v3 §4-B 表(pooled p≤7 = 13.5 [9.2, 18.4])——
  用作恒等式对账(λ̄·E 应逐位复现该列);
- 局终销毁中位: P51 v3 §4-C 表(cw3 s0/r2/r3 = 236.5/210/197);
- 桶构成(距终≤6 占比): P51 v3 §4-B-3(cw3 8.2% / legacy 0.0%);
- δ̄(每期贪心缺口保守带): W_flow 二阶小项 0-0.5 金/轮,P51 v3 §4-A;
- 息差 cap: p47 域 min(g//10,5) 封顶 5 金/轮(P48 §③(a) 同源引用);
- 濒死带 W_floor: P51 v3 §4-B(pooled p8-12 = 59.3 [48.5, 71.7])。

重跑: $env:PYTHONPATH='src'; uv run python tools/cw/proofs/p52_check.py
"""
from dataclasses import dataclass

# ---------- 输入常量(全部【注】P51/p47 表值直录,禁改) ----------
WINDOW = 3                    # 危险率视界(P51 声明参数,3 轮累积)
DELTA_BAR = 0.5               # δ̄ 金/轮(判据残差保守带 = W_flow 带上端,P51 §4-A)
MATCH_COST_BAND = 12.0        # 升档器转化错配上界(金,P39 5费单张边界带带宽量级)
INTEREST_CAP = 5.0            # 息差 cap 金/轮(p47)
DEATH_MEDIAN = {'cw3_s0': 236.5, 'cw3_r2': 210.0, 'cw3_r3': 197.0}  # 局终销毁中位(P51 §4-C)


@dataclass
class Cell:
    """p≤7 桶×节点分层格(P51 §4-B-2,pooled)。"""
    name: str
    lam_point: float
    lam_lo: float
    lam_hi: float
    n: int


CELLS_P7 = [
    Cell('battle', 0.065, 0.046, 0.086, 835),
    Cell('encounter', 0.042, 0.000, 0.091, 71),
    Cell('boss', 0.021, 0.000, 0.067, 48),
]

# pooled p≤7 混合格(P51 §4-B): λ3=0.061, g=74.4, Φ=+147.3, W_floor=13.5 [9.2,18.4]
LAM_MIXED_P7 = 0.061
G_P7, PHI_P7 = 74.4, 147.3
WFLOOR_P7_PT, WFLOOR_P7_LO, WFLOOR_P7_HI = 13.5, 9.2, 18.4
# 桶构成: p≤7 桶轮次中距终≤6 占比(P51 §4-B-3)
NEAR_DEATH_SHARE = {'cw3': 0.082, 'legacy': 0.0}
# 濒死带(P51 §4-B pooled p8-12)
WFLOOR_DYING_PT, WFLOOR_DYING_LO, WFLOOR_DYING_HI = 59.3, 48.5, 71.7
# 默认局长(P51 §4-C: 死亡轮序/局长中位 102-105)
T_DEFAULT = 105


def exposure_p7() -> float:
    """E = g + Φ(P51 W_floor 同一量: 存量金 + 未来纯金流)。"""
    return G_P7 + PHI_P7


def check_identity() -> None:
    """对账 1: λ̄·E 逐位复现 P51 §4-B 的 W_floor 列(同一乘积的两种出处)。"""
    e = exposure_p7()
    got = LAM_MIXED_P7 * e
    assert abs(got - WFLOOR_P7_PT) < 0.1, f'恒等式失配: {LAM_MIXED_P7}*{e}={got} vs {WFLOOR_P7_PT}'
    print(f'[对账1] λ3·E = {LAM_MIXED_P7} × {e:.1f} = {got:.2f} ≈ P51 W_floor(pooled p≤7) {WFLOOR_P7_PT} ✓')


def window_epsilon_table() -> None:
    """对账 2: 单窗 ε 表(逐分层格)。ε_w = λ̄·E + WINDOW·δ̄。"""
    e = exposure_p7()
    flow_term = WINDOW * DELTA_BAR
    print(f'\n[对账2] 单窗 ε(p≤7 桶,E={e:.1f} 金,流差项 {flow_term:.1f} 金/窗):')
    print(f'{"节点":>10} {"λ3点":>6} {"CI上界":>7} {"死亡通道项 点/上界":>18} {"ε_w 点/上界":>14} {"ε_w/销毁中位197 上界":>20}')
    for c in CELLS_P7:
        d_pt, d_hi = c.lam_point * e, c.lam_hi * e
        eps_pt, eps_hi = d_pt + flow_term, d_hi + flow_term
        # ε 随 λ 单调(定理结构性事实)
        assert eps_pt <= eps_hi
        print(f'{c.name:>10} {c.lam_point:>6.3f} {c.lam_hi:>7.3f} {d_pt:>9.1f}/{d_hi:<7.1f} {eps_pt:>6.1f}/{eps_hi:<6.1f} {eps_hi / DEATH_MEDIAN["cw3_r3"] * 100:>10.1f}%')


def path_epsilon() -> None:
    """对账 3: 全路径累计口径(两个 band,如实披露 union bound 的松紧)。"""
    e = exposure_p7()
    flow_term = WINDOW * DELTA_BAR
    eps_w_hi = CELLS_P7[0].lam_hi * e + flow_term  # 取 battle CI 上界作最保守单窗
    # band A(可用形态): 危险窗数按桶构成限定——距终≤6(≤2 窗)× 桶内占比
    for side, share in NEAR_DEATH_SHARE.items():
        danger_windows = share * T_DEFAULT / WINDOW
        eps_path = danger_windows * eps_w_hi
        print(f'\n[对账3-{side}] 桶构成修正危险窗数 = {share:.3f}×{T_DEFAULT}/{WINDOW} = {danger_windows:.2f} 窗'
              f' → 全局死亡通道项 ≤ {danger_windows:.2f} × {eps_w_hi:.1f} = {eps_path:.1f} 金'
              f'({eps_path / DEATH_MEDIAN["cw3_r3"] * 100:.1f}% of 销毁中位 197)')
    # band B(披露形态): 朴素 union bound 全窗累计
    naive = (T_DEFAULT / WINDOW) * eps_w_hi
    print(f'[对账3-披露] 朴素 union bound(全部 {T_DEFAULT // WINDOW} 窗按最保守格累计)= {naive:.0f} 金 —— vacuous,'
          '证明定理可用形态=窗口局部 ε-最优(域条件 H_eff 的实证内容即危险窗稀少)')


def belt_corollary() -> None:
    """对账 4: 升档器安全带——c_σ 有界且小于濒死带单窗敞口(截断读法)。"""
    shift_rounds = WINDOW  # 提前量上界 = 1 个视界窗
    c_sigma = INTEREST_CAP * shift_rounds + MATCH_COST_BAND
    print(f'\n[对账4] c_σ = 息差 cap {INTEREST_CAP:.0f}×{shift_rounds} + 错配上界 {MATCH_COST_BAND:.0f} = {c_sigma:.0f} 金')
    assert c_sigma < WFLOOR_DYING_LO, '安全带常数应小于濒死带单窗敞口 CI 下界'
    print(f'  濒死带单窗敞口(P51 pooled p8-12)= {WFLOOR_DYING_PT} [{WFLOOR_DYING_LO}, {WFLOOR_DYING_HI}] 金'
          f' → c_σ={c_sigma:.0f} < CI 下界 {WFLOOR_DYING_LO} ✓'
          f'(无界敞口被替换为有界常数,截断比 ≈ {WFLOOR_DYING_PT / c_sigma:.1f}:1)')


def main() -> None:
    # Windows 控制台默认 GBK,输出含 ✓/λ 等字符会 UnicodeEncodeError——强制 UTF-8 输出
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    check_identity()
    window_epsilon_table()
    path_epsilon()
    belt_corollary()
    print('\n全部断言通过。')


if __name__ == '__main__':
    main()
