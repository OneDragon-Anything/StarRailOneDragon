"""胶囊按钮微距拖拽点击 op(MCP 手动游玩通用动作)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext


class CwCapsuleDragClick(CwOperation):
    """对指定画面上的指定胶囊按钮执行「按下→横移数px→抬起」的微距拖拽点击。
    起点/终点:目标画面自身(本 op 只做手势,不负责画面导航)。
    消耗:随目标按钮而定(调用方读 extras 后自行决策,本 op 零判效)。

    为什么存在(双局实机交叉实证):出战/投资确认/补给确认/放弃并结算等
    **胶囊形按钮对静态点击免疫**(点击无响应或偶发生效),微距拖拽手势
    一次生效;普通文字卡/页签/商店牌/购买经验不受影响,仍用静态点击。
    出战按钮在商店展开态第一下拖拽只收商店——**先收商店再调本 op**
    (用 CwToggleShopPanel 先收)。

    :param screen_name: 按钮所在画面档名(如 货币战争-备战 / 货币战争-补给)。
        须为已建档画面,否则构造期拒绝。
    :param area_name: 按钮 area 名(含「按钮-」前缀,如 按钮-出战 / 按钮-确认)。
    :param move_px: 按下后的横移像素数(正=向右),缺省 4,可用值 2-12。
    """

    def __init__(self, ctx: SrContext, screen_name: str, area_name: str,
                 move_px: int = 4):
        CwOperation.__init__(self, ctx, op_name='CW胶囊按钮微距拖拽',
                             need_check_game_win=False)
        if move_px < 2 or move_px > 12:
            raise ValueError(f'move_px 越界: {move_px}(可用值 2-12)')
        self.screen_name: str = screen_name
        self.area_name: str = area_name
        self.move_px: int = move_px

    @operation_node(name='定位并微距拖拽', is_start_node=True)
    def capsule_click(self) -> OperationRoundResult:
        screen_info = self.ctx.screen_loader.get_screen(self.screen_name)
        target = None
        if screen_info is not None:
            target = next((a for a in screen_info.area_list
                           if a.area_name == self.area_name), None)
        if target is None or target.pc_rect is None:
            return self.round_fail(
                status=f'area 缺失:{self.area_name}({self.screen_name})')
        center = target.pc_rect.center
        self.ctx.controller.drag_to(
            end=Point(center.x + self.move_px, center.y),
            start=center,
            duration=0.35)
        return self.round_success(
            status=(f'已微距拖拽 {self.area_name}'
                    f'({center.x},{center.y}→+{self.move_px}px;机械发出,零判效)'),
            data={'x': center.x, 'y': center.y, 'move_px': self.move_px},
            wait=1)
