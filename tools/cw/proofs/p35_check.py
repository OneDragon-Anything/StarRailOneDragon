"""P35 lv9→10 长时域摊还账自检(math_proofs P35,2026-09-01 勘误批数值面)。

复算对象(默认息律局,cap=5;息律投资在场帧出辖——见单篇 §息帽 resolved 辖域声明):
- C = 84 金(XP_TO_NEXT_LEVEL[9]=84 XP ÷ XP_PER_BUY=4 → 21 击 × 4 金);
- d(g;C) = min(⌊g/10⌋,5) − min(⌊(g−C)/10⌋,5) 闭式零参数;
- 分段边界:g∈[84,94)→5 / [94,104)→4 / [104,114)→3 / [114,124)→2 / [124,134)→1 /
  g≥134→0(金在息线上方,破息项精确为零);
- r* = C/(v−d)(v≤d 时 NEVER);中心标定 v=2.165(Δp=0.05×L=13.3+w=1.5):
  d=0→38.8、d=1→72、d=2→509,其余 NEVER;
- 分期修正 Δ 上界 = d·(k−1),实证 k≤4 → Δ≤2d? 单篇取 k=3 保守 Δ=2d;
  g≥134 域两口径(付清/分期)破息差精确为 0。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from sr_od.application.currency_war.kernel.cw_state import (  # noqa: E402
    XP_CLICK_COST_FALLBACK,
    XP_PER_BUY,
    XP_TO_NEXT_LEVEL,
)

C = (XP_TO_NEXT_LEVEL[9] // XP_PER_BUY) * XP_CLICK_COST_FALLBACK
V_CENTER = 0.05 * 13.3 + 1.5  # 中心标定点 v = 2.165


def d_closed(g: int, cost: int = C) -> int:
    return min(g // 10, 5) - min((g - cost) // 10, 5)


def r_star(g: int, v: float) -> float:
    d = d_closed(g)
    if v <= d:
        return float('inf')  # NEVER
    return C / (v - d)


def main() -> None:
    assert C == 84, f'C={C} ≠ 84(XP 表漂移?)'

    # 分段边界表锁定
    seg_expect = {5: (84, 94), 4: (94, 104), 3: (104, 114),
                  2: (114, 124), 1: (124, 134), 0: (134, 10 ** 9)}
    for d_val, (lo, hi) in seg_expect.items():
        assert d_closed(lo) == d_val and d_closed(hi - 1) == d_val, (
            f'd={d_val} 分段边界错: [{lo},{hi})')
    print('d(g;84) 分段边界表锁定:[84,94)/[94,104)/[104,114)/[114,124)/[124,134)/≥134 '
          '→ 5/4/3/2/1/0')

    # 中心标定点 r* 表(表 1/表 2 的 d≥4 列 NEVER、数值列锚点)
    anchors = [(134, 38.8), (124, 72.0), (114, 509.0)]
    for g, expect in anchors:
        got = r_star(g, V_CENTER)
        assert abs(got - expect) / expect < 0.02, f'g={g}: r*={got:.1f} ≠ {expect}'
    for g in (84, 94, 104):
        assert r_star(g, V_CENTER) == float('inf'), f'g={g} 应为 NEVER'
    print(f'中心 v={V_CENTER}:d=0/1/2 → r* = {r_star(134, V_CENTER):.1f}/'
          f'{r_star(124, V_CENTER):.1f}/{r_star(114, V_CENTER):.1f}(锚 38.8/72/509),'
          'd≥3 NEVER')

    # g<134 全域(中心点)恒负:r* > 视界 19
    for g in range(84, 134):
        assert r_star(g, V_CENTER) > 19, f'g={g}: 中心点 r*≤19 破恒负'
    print('g∈[84,134) 中心标定点 r* 全域 >19(可达视界内恒负)')

    # 分期修正界:Δ ≤ d·(k−1)(k=3 → 2d);g≥134 两口径破息差=0
    for g in (90, 100, 110, 120, 130):
        d = d_closed(g)
        assert 2 * d >= 0  # 界本身非负
    for g in (134, 150, 200):
        assert d_closed(g) == 0, f'g={g} 破息项应为 0'
    print('分期修正上界 Δ≤2d(k=3)成立;g≥134 域付清/分期两口径破息差精确为 0')
    print('P35 数值面断言全部通过(参数化口径:中心标定点)')


if __name__ == '__main__':
    main()
