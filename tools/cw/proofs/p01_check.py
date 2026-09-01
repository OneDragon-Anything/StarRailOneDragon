"""P1/P25 再遇窗口自检(math_proofs P1、P25 锚点数字)。

复算对象:
- P1:「5费@7-8级再遇 60-180 轮」——单张目标卡在一次刷新(5 格)中至少出现
  1 张的概率 P1r,再遇期望轮数(每轮一次自动刷新口径)= 1/P1r。
- P25 v2 勘误锚:「3费@lv7/8 再遇 7.4/9.1 轮」(旧版错标 5 费数据已勘误)。

概率单一源 = cw_shop_odds(REFRESH_PROB / DISTINCT_CARDS_PER_CARD /
POOL_COPIES_PER_CARD),与生产 refresh_prob 同源,非本脚本自建表。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from sr_od.application.currency_war.data.cw_shop_odds import (  # noqa: E402
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    _refresh_dist,
    refresh_prob,
)


def reencounter_rounds(level: int, cost: int) -> float:
    """单张卡再遇期望轮数(每轮 1 刷新;P(本次刷新 ≥1 张目标)的倒数)。"""
    p = refresh_prob(level, cost)
    v = DISTINCT_CARDS_PER_COST.get(cost, 13)
    a = POOL_COPIES_PER_CARD.get(cost, 9)
    p0 = _refresh_dist(p, v, a, c=0, k_need=1, j=0)[0]
    return 1.0 / (1.0 - p0)


def main() -> None:
    # P25 v2 勘误锚:3费@lv7/8 = 7.4/9.1 轮(±0.1 容差,索引关键数字)
    r_3lv7 = reencounter_rounds(7, 3)
    r_3lv8 = reencounter_rounds(8, 3)
    assert abs(r_3lv7 - 7.4) < 0.1, f'3费@lv7 再遇 {r_3lv7:.2f} ≠ 7.4'
    assert abs(r_3lv8 - 9.1) < 0.1, f'3费@lv8 再遇 {r_3lv8:.2f} ≠ 9.1'

    # P1:5费@lv7/lv8 落在 60-180 轮带内(带两端即这两格;180.4 为带端精确值)
    r_5lv7 = reencounter_rounds(7, 5)
    r_5lv8 = reencounter_rounds(8, 5)
    assert 60.0 <= r_5lv8 <= 180.5, f'5费@lv8 {r_5lv8:.2f} 出带'
    assert 60.0 <= r_5lv7 <= 180.5, f'5费@lv7 {r_5lv7:.2f} 出带'
    # 带端核对:lv8 是下端(~60)、lv7 是上端(~180)
    assert abs(r_5lv8 - 60.0) < 2.0, f'5费@lv8 {r_5lv8:.2f} 非 ~60'
    assert abs(r_5lv7 - 180.0) < 2.0, f'5费@lv7 {r_5lv7:.2f} 非 ~180'

    print(f'3费@lv7/lv8 再遇 = {r_3lv7:.2f}/{r_3lv8:.2f} 轮 (P25 锚 7.4/9.1)')
    print(f'5费@lv7/lv8 再遇 = {r_5lv7:.2f}/{r_5lv8:.2f} 轮 (P1 带 60-180)')
    print('P1/P25 再遇窗口锚点全部通过')


if __name__ == '__main__':
    main()
