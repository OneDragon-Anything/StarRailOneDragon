"""买商店牌 op(按物理槽位点击;公用底层动作原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import (
    A_SHOP_CARD_PREFIX,
    SHOP_SCREEN_NAME,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext


class CwBuyShopCardBySlot(CwOperation):
    """买入商店指定槽位的一张牌。
    起点:货币战争-备战-开商店(商店面板展开);终点:点击买入一张牌,
    停留原画面(买入是否生效归调用方下一帧 analyze_screen 对账)。
    消耗:支付牌面费用金币,不可逆。

    牌面身份/费用读数 = analyze_screen 对「货币战争-备战-开商店」的 extras
    ``shop_cards``(SIFT 识别,含槽位与费用);本 op 只负责机械点击,不判断牌面。

    :param slot: 商店牌物理槽位号,1-5(= screen_info「商店牌-N」序号;
        extras.shop_cards 数组下标 + 1)。越界构造期拒绝(带可用值 ValueError)。
    """

    def __init__(self, ctx: SrContext, slot: int):
        CwOperation.__init__(self, ctx, op_name='CW买商店牌',
                             need_check_game_win=False)
        if not 1 <= slot <= 5:
            raise ValueError(f'slot 越界: {slot}(可用值 1-5,商店牌物理槽位)')
        self.slot: int = slot

    @operation_node(name='点击商店牌', is_start_node=True)
    def click_card(self) -> OperationRoundResult:
        # 按槽号直取 area(禁压缩列表按序取:任一牌 area 缺失会让后续槽位
        # 整体错位一格,误购不可逆——审计修正建议 5)。
        si = self.ctx.screen_loader.get_screen(SHOP_SCREEN_NAME)
        area = None
        if si is not None:
            area = next((a for a in si.area_list
                         if a.area_name == f'{A_SHOP_CARD_PREFIX}{self.slot}'), None)
        if area is None or area.pc_rect is None:
            return self.round_fail(
                status=f'商店牌-{self.slot} area 缺失(screen_info 建档漂移)')
        pt = area.pc_rect.center
        self.ctx.controller.click(pt)
        return self.round_success(status=f'已点击商店牌{self.slot}槽(机械发出,零判效)',
                                  data={'slot': self.slot,
                                        'x': pt.x, 'y': pt.y},
                                  wait=1)
