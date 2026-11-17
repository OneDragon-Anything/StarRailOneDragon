"""购买经验 op(点击购买经验按钮 N 次;公用底层动作原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SHOP_SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

#: 购买经验按钮 area 名(画面名口径 = 开商店画面档;备战画面档同名 area 同位,
#: 按钮在两种面板状态下常驻)。
_BUY_EXP_AREA: str = '备战标识-购买经验'


class CwBuyXpRepeat(CwOperation):
    """购买经验(升团队等级)N 次。
    起点:货币战争-备战(商店面板开合均可);终点:连点购买经验按钮 N 次,
    停留原画面(等级/经验/金币变化归调用方下一帧 analyze_screen 对账)。
    消耗:每次支付当前档购买经验价格金币(见 extras.levelup_cost),不可逆。

    金币是否够付不判断(零判效):余额不足时游戏侧无效,
    对账以 extras.gold / xp_progress 为准。
    按钮 area 缺失 → round_fail(建档漂移显式暴露,不兜底坐标)。

    :param times: 购买次数,1-10(每次间隔 1s 等待面板刷新)。
    """

    def __init__(self, ctx: SrContext, times: int = 1):
        CwOperation.__init__(self, ctx, op_name='CW购买经验',
                             need_check_game_win=False)
        if not 1 <= times <= 10:
            raise ValueError(f'times 越界: {times}(可用值 1-10)')
        self.times: int = times

    @operation_node(name='连点购买经验', is_start_node=True)
    def click_buy(self) -> OperationRoundResult:
        pt = area_center(self.ctx, _BUY_EXP_AREA, screen_name=SHOP_SCREEN_NAME)
        if pt is None:
            return self.round_fail(
                status=f'area 缺失:{_BUY_EXP_AREA}({SHOP_SCREEN_NAME})')
        for i in range(self.times):
            self.ctx.controller.click(pt)
            if i < self.times - 1:
                time.sleep(1)
        return self.round_success(
            status=f'已点击购买经验×{self.times}(机械发出,零判效)',
            data={'times': self.times, 'x': pt.x, 'y': pt.y}, wait=1)
