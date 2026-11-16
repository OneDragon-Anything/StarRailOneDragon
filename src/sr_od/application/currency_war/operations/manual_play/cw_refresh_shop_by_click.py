"""刷新商店 op(点击刷新按钮;MCP 手动游玩纯动作)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SHOP_SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext


class CwRefreshShopByClick(CwOperation):
    """刷新商店牌行(花金币重摇五张牌)。
    起点:货币战争-备战-开商店(商店面板展开);终点:点击刷新按钮一次,
    停留原画面(牌行是否重摇归调用方下一帧 analyze_screen 对账,extras.shop_cards)。
    消耗:支付当前刷新价格金币(v4.4 口径 2 金起逐次递增;按钮旁费用读数暂无 area)。

    :param times: 连续刷新次数,1-5(每次间隔 1s;零判效,费用够不够不判断)。
    """

    def __init__(self, ctx: SrContext, times: int = 1):
        CwOperation.__init__(self, ctx, op_name='CW刷新商店',
                             need_check_game_win=False)
        if not 1 <= times <= 5:
            raise ValueError(f'times 越界: {times}(可用值 1-5)')
        self.times: int = times

    @operation_node(name='点击刷新', is_start_node=True)
    def click_refresh(self) -> OperationRoundResult:
        import time
        pt = area_center(self.ctx, '按钮-刷新', screen_name=SHOP_SCREEN_NAME)
        if pt is None:
            return self.round_fail(
                status='area 缺失:按钮-刷新(开商店画面档)')
        for i in range(self.times):
            self.ctx.controller.click(pt)
            if i < self.times - 1:
                time.sleep(1)
        return self.round_success(
            status=f'已点击刷新×{self.times}(机械发出,零判效)',
            data={'times': self.times, 'x': pt.x, 'y': pt.y}, wait=1)
