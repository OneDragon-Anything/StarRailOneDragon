"""投资策略三选一 op(点图标区选卡 + 确认微距拖拽;公用底层动作原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

_STRATEGY_SCREEN: str = '货币战争-投资策略'
_ICON_AREA: dict[int, str] = {1: '图标-策略卡1', 2: '图标-策略卡2', 3: '图标-策略卡3'}
_CONFIRM_AREA: str = '按钮-确认'


class CwPickInvestStrategy(CwOperation):
    """投资策略三选一两步一体:点卡片图标区选中 → 确认微距拖拽。
    起点/终点:货币战争-投资策略(画面自身;确认后回备战画面,由调用方观察)。
    消耗:确认后本节点投资策略绑定生效(不可逆;刷新次数随画面走)。

    交互手法(实机沉淀):
    - 选卡 = **点卡片六边形图标区**(画面档 图标-策略卡N;点卡片标题/文字区
      不选中——实机踩坑,勿改回点卡心)
    - 确认 = **微距拖拽**(按下→横移→抬起):胶囊按钮,静态点击免疫;
      未选中时确认置灰,op 不判效,置灰态拖拽 = 无操作,调用方下一帧对账
    - 「返回备战界面」按钮 = 跳过本次选择,本 op 不含(需要跳过时调用方自点)

    :param card_index: 选第几张卡,1..3 从左到右(内容决策归调用方读图)。

    前提(用户质询核实):现行版本恒为三选一——实机 4 例(两局 4 时点)恒 3 张,
    flow 层口径一致;extras.strategies 的读取器是动态行 OCR(数量变化会如实反映)。
    **护栏:调用方先确认 len(extras.strategies)==3 再用本 op**;≠3 说明卡数变了,
    退回坐标点击并反馈更新本 op 的图标区。
    """

    def __init__(self, ctx: SrContext, card_index: int):
        CwOperation.__init__(self, ctx, op_name='CW选投资策略',
                             need_check_game_win=False)
        if card_index not in _ICON_AREA:
            raise ValueError(f'card_index 只能是 1/2/3,得到: {card_index}')
        self.card_index: int = card_index

    @operation_node(name='点图标区选中', is_start_node=True)
    def pick_card(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, _STRATEGY_SCREEN, _ICON_AREA[self.card_index],
            success_wait=1)

    @node_from(from_name='点图标区选中')
    @operation_node(name='确认')
    def confirm(self) -> OperationRoundResult:
        screen_info = self.ctx.screen_loader.get_screen(_STRATEGY_SCREEN)
        target = None
        if screen_info is not None:
            target = next((a for a in screen_info.area_list
                           if a.area_name == _CONFIRM_AREA), None)
        if target is None or target.pc_rect is None:
            return self.round_fail(status=f'area 缺失:{_CONFIRM_AREA}')
        center = target.pc_rect.center
        self.ctx.controller.drag_to(
            end=Point(center.x + 5, center.y), start=center, duration=0.35)
        return self.round_success(
            status='已微距拖拽确认(机械发出,零判效;落位归下一帧观察)', wait=2)
