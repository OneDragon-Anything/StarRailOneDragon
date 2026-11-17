"""出战 op(收店前置 + 出战微距拖拽 + 未达上限弹窗条件确认;公用底层动作原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

_PREP_SCREEN: str = '货币战争-备战'
_SHOP_SCREEN: str = '货币战争-备战-开商店'
_WARN_SCREEN: str = '货币战争-未达上限警告'


class CwStartBattleByClick(CwOperation):
    """点击出战开始本节点战斗(商店展开自动收起 + 未达上限弹窗确定性处理)。
    起点:货币战争-备战(商店面板开合均可);终点:战斗转场(弹窗出现时先点掉),
    离开备战画面(战斗是否实际开启归调用方对局画面观察)。
    消耗:进入战斗(败局扣小队生命值;战斗本身无直接货币消耗)。

    出战按钮为胶囊形,对静态点击免疫(双局实机交叉实证),本 op 用
    **微距拖拽手势**(按下→横移4px→抬起)循环施放,直到离开备战画面。
    商店展开态第一下拖拽只收商店不触发战斗(实机两次验证),故先收店再出战。
    弹窗处理 = 确定性分支(出现即点确认),非决策闸门;「本局不再提示」
    勾选框不代点(留调用方自行决定是否勾选,勾选属玩家偏好)。
    部署是否满员不判断(零判效):未满员时弹窗由本 op 内分支点掉。

    :param none: 无参数。
    """

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='CW出战',
                             need_check_game_win=False)

    @operation_node(name='收起商店(若展开)', is_start_node=True)
    def collapse_shop(self) -> OperationRoundResult:
        found = self.round_by_find_area(
            self.last_screenshot, _SHOP_SCREEN, '按钮-收起')
        if not found.is_success:
            return self.round_success(status='商店未展开(无需收起)')
        return self.round_by_find_and_click_area(
            self.last_screenshot, _SHOP_SCREEN, '按钮-商店开关',
            until_not_find_all=[(_SHOP_SCREEN, '按钮-收起')],
            pre_delay=0.3, success_wait=1.5, retry_wait=1)

    @node_from(from_name='收起商店(若展开)')
    @operation_node(name='微距拖拽出战', node_max_retry_times=8)
    def drag_start(self) -> OperationRoundResult:
        screen = self.last_screenshot
        still = self.round_by_find_area(screen, _PREP_SCREEN, '按钮-出战')
        if not still.is_success:
            return self.round_success(status='已离开备战(出战生效)')
        screen_info = self.ctx.screen_loader.get_screen(_PREP_SCREEN)
        target = None
        if screen_info is not None:
            target = next((a for a in screen_info.area_list
                           if a.area_name == '按钮-出战'), None)
        if target is None or target.pc_rect is None:
            return self.round_fail(status='area 缺失:按钮-出战(货币战争-备战)')
        center = target.pc_rect.center
        self.ctx.controller.drag_to(
            end=Point(center.x + 4, center.y),
            start=center,
            duration=0.35)
        return self.round_retry(status='已微距拖拽出战,等待画面响应', wait=4)

    @node_from(from_name='微距拖拽出战')
    @operation_node(name='处理未达上限弹窗')
    def handle_warn_dialog(self) -> OperationRoundResult:
        found = self.round_by_find_area(
            self.last_screenshot, _WARN_SCREEN, '标识-未达上限警告')
        if not found.is_success:
            return self.round_success(status='无未达上限弹窗(直接进战斗)')
        return self.round_by_find_and_click_area(
            self.last_screenshot, _WARN_SCREEN, '按钮-确认',
            until_not_find_all=[(_WARN_SCREEN, '标识-未达上限警告')],
            pre_delay=0.3, success_wait=2, retry_wait=1)
