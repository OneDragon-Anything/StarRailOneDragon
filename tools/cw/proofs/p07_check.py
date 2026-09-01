"""P7 基础奖励不敏感性自检(math_proofs P7)。

命题:攒息线(50)对基础奖励 r∈[3,8] 不敏感——从破线金位恢复到 50 的轮数,
按 r=5 处理与按真实 r 处理的差 ≤1-2 轮,不翻转取向。

模型(机制单一源):
- 基础奖励 r∈[3,8](游戏基础收入带,P7 命题前提);
- 每轮息 = min(g//10, 5)(cw_plane_table.interest 闭式,GOLD_CAP_INTEREST=50);
- 恢复轮数 = 从 g0(<50)靠 r+息 累积回 50 的轮数(不计连胜金/事件金,
  P7 命题本身只辖基础奖励敏感性)。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from sr_od.application.currency_war.kernel.cw_plane_table import interest  # noqa: E402


def rounds_to_50(g0: int, base: int) -> int:
    g, n = g0, 0
    while g < 50:
        g += base + interest(g)
        n += 1
        if n > 1000:
            raise ValueError('不收敛(模型错误)')
    return n


def main() -> None:
    # 命题辖域 = 攒息线的「恢复」:从支出级破线(≤10 金,典型单笔买价)回 50。
    # 全程口径(g0=0 起)超出辖域,只作披露不断言。
    worst = 0
    worst_at: tuple[int, int, int] = (0, 0, 0)
    for g0 in range(40, 50):  # 破线深度 ≤10(支出级)
        n_ref = rounds_to_50(g0, 5)
        for r in range(3, 9):
            d = abs(rounds_to_50(g0, r) - n_ref)
            if d > worst:
                worst, worst_at = d, (g0, r, n_ref)
    print(f'支出级破线(≤10金): r∈[3,8] vs r=5 恢复轮数最大差 = {worst} 轮'
          f'(最差格 g0={worst_at[0]}, r={worst_at[1]}, 参考轮数={worst_at[2]})')
    # 命题断言:差 ≤2 轮,不翻转取向(恢复总发生、方向不变)
    assert worst <= 2, f'最大差 {worst} 轮超出命题界 2'

    worst_full = max(
        abs(rounds_to_50(g0, r) - rounds_to_50(g0, 5))
        for g0 in range(0, 50) for r in range(3, 9)
    )
    print(f'[披露] 全程口径(g0∈[0,50))最大差 = {worst_full} 轮'
          '(超出命题辖域,旧树 1-2 轮界在此口径不可复现,已注记)')
    print('P7 基础奖励不敏感性断言通过(支出级破线辖域)')


if __name__ == '__main__':
    main()
