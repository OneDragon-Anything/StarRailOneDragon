"""P22 淘金客刷新 XP 占优定理自检(math_proofs P22)。

命题(占优定理,零自由参数):
- r_refresh = xp_per_refresh / refresh_cost(每金 XP,走刷新通道);
- r_buy = XP_PER_BUY / xp_click_cost(每金 XP,走购买经验通道);
- r_refresh ≥ r_buy ⟺ xp_click_cost ≥ refresh_cost·XP_PER_BUY / xp_per_refresh;
  基价语境(refresh_cost=2, xp_per_refresh=2, XP_PER_BUY=4)退化为
  xp_click_cost ≥ 4;唯一例外域 = 商业间谍折扣(xp_click_cost<4)。
- flat-4 裁决下(xp_click_cost=4)两汇率恒等 1.00(全等级,等级只是中介量)。

常量单一源:cw_state(XP_PER_BUY / XP_CLICK_COST_FALLBACK / REFRESH_COST_BASE)、
cw_investments(淘金客 EconomyEffect.xp_per_refresh)。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from sr_od.application.currency_war.kernel.cw_investments import (
    STRATEGY_EFFECTS,  # noqa: E402
)
from sr_od.application.currency_war.kernel.cw_state import (  # noqa: E402
    REFRESH_COST_BASE,
    XP_CLICK_COST_FALLBACK,
    XP_PER_BUY,
)


def main() -> None:
    gd = STRATEGY_EFFECTS['淘金客']
    xp_per_refresh = gd.payload.xp_per_refresh
    assert xp_per_refresh == 2, f'淘金客 xp_per_refresh={xp_per_refresh} ≠ 注册表 2'

    r_refresh = xp_per_refresh / REFRESH_COST_BASE

    # 平汇率断言:flat-4 下两通道汇率恒等
    r_buy_flat = XP_PER_BUY / XP_CLICK_COST_FALLBACK
    assert abs(r_refresh - r_buy_flat) < 1e-12, (
        f'flat-4 平汇率破坏: {r_refresh} vs {r_buy_flat}')
    print(f'flat-4 裁决: r_refresh = r_buy = {r_buy_flat:.2f} XP/金(恒等 1.00)')

    # 占优方向断言:xp_click_cost 网格上符号翻转点恰在 4(基价语境)
    for cc in range(1, 9):
        r_buy = XP_PER_BUY / cc
        holds = r_refresh >= r_buy
        expect = cc >= 4
        assert holds == expect, f'cc={cc}: 占优 {holds} ≠ 命题 {expect}'
        if cc != 4:
            assert (r_refresh > r_buy) == (cc > 4), f'cc={cc}: 严格性方向错'
    print('xp_click_cost∈[1,8] 网格:占优翻转点=4,严格优在 cc>4,'
          '例外域=商业间谍折扣 cc<4 —— 与命题一致')

    # 「免费刷新不计 XP」仅注册表文本证据(P22 挂实采复核项),此处不复算
    print('P22 占优定理断言全部通过')


if __name__ == '__main__':
    main()
