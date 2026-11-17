"""开/收商店面板 op(点击右下角面板开关;公用底层动作原语)。
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

#: 面板开关按钮 area(v4.7 实测可点击面 = 面板主体;旧「按钮-商店/按钮-收起」
#: 文本区中心点击实测偶发不生效,实锤点 = 面板中部 (1622,945)。两画面档
#: (备战/开商店)各建同名 area,矩形一致,op 按当前画面档取用)。
_TOGGLE_AREA: str = '按钮-商店开关'


class CwToggleShopPanel(CwOperation):
    """切换商店面板开/收状态(点右下角面板开关一次)。
    起点:货币战争-备战(面板收起态,点击展开)或 货币战争-备战-开商店
    (面板展开态,点击收起);终点:面板状态翻转,停留备战族画面
    (翻转结果归调用方下一帧 analyze_screen 对账:画面命中在哪个 screen_name)。
    消耗:零(纯界面开关)。

    零消耗承诺(高消耗风险画面纪律):本 op 只点面板开关,永不触碰
    商店牌 / 刷新 / 购买经验等扣费控件。

    :param screen_name: 当前所在画面档:「货币战争-备战」(收起态)或
        「货币战争-备战-开商店」(展开态);决定从哪个画面档读开关 area。
        传其它值构造期拒绝(带可用值 ValueError)。
    """

    def __init__(self, ctx: SrContext, screen_name: str):
        CwOperation.__init__(self, ctx, op_name='CW开关商店面板',
                             need_check_game_win=False)
        if screen_name not in ('货币战争-备战', SHOP_SCREEN_NAME):
            raise ValueError(
                f'screen_name 非法: {screen_name}'
                f'(可用值: 货币战争-备战 | {SHOP_SCREEN_NAME})')
        self.screen_name: str = screen_name

    @operation_node(name='点击面板开关', is_start_node=True)
    def click_toggle(self) -> OperationRoundResult:
        pt = area_center(self.ctx, _TOGGLE_AREA, screen_name=self.screen_name)
        if pt is None:
            return self.round_fail(
                status=f'area 缺失:{_TOGGLE_AREA}({self.screen_name})')
        self.ctx.controller.click(pt)
        return self.round_success(
            status='已点击商店面板开关(机械发出,零判效)',
            data={'x': pt.x, 'y': pt.y}, wait=1.5)
