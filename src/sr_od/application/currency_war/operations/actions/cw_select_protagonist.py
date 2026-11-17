"""主角光环选择 op(选光环 + 拖角色入主角槽 + 确认;公用底层动作原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

_AURA_SCREEN: str = '货币战争-主角光环选择'
_SLOT_AREA: str = '槽-中央主角槽'
_CONFIRM_AREA: str = '按钮-确认'
_CARD_AREA: dict[str, str] = {'left': '卡-左光环', 'right': '卡-右光环'}


class CwSelectProtagonist(CwOperation):
    """主角光环选择画面三步一体:选光环卡 → 拖角色入中央主角槽 → 确认。
    起点/终点:货币战争-主角光环选择(画面自身;确认后回备战画面,由调用方观察)。
    消耗:确认后本位面主角绑定生效(不可逆;光环随位面重选)。

    交互手法(双局实机沉淀,缺一不可):
    - 光环卡选中 = **静态点击卡面**(白框亮起即选中;先选卡才能拖角色)
    - 放主角 = **拖拽**:角色预览卡 → 中央主角槽;点角色/点槽位/点适配头像
      均无效;拖拽源用坐标参数(预览槽居中排布,数量随部署数变化,无固定槽位
      area——源坐标由调用方从当前帧读出)
    - 确认 = **微距拖拽**(按下→横移→抬起):胶囊按钮,静态点击免疫
    - 非适配角色也可放置(无阻拦);三样缺一确认键置灰

    :param aura_side: 选哪张光环卡,'left' 或 'right'(光环池随机,内容调用方读图决策)。
    :param source_x: 拖拽源横坐标——目标角色预览卡中心(调用方从当前帧读出)。
    :param source_y: 拖拽源纵坐标——目标角色预览卡中心。
    """

    def __init__(self, ctx: SrContext, aura_side: str, source_x: int, source_y: int):
        CwOperation.__init__(self, ctx, op_name='CW选择主角光环',
                             need_check_game_win=False)
        if aura_side not in _CARD_AREA:
            raise ValueError(f"aura_side 只能是 'left'/'right',得到: {aura_side}")
        self.aura_side: str = aura_side
        self.source: Point = Point(source_x, source_y)

    @operation_node(name='点选光环卡', is_start_node=True)
    def select_aura(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, _AURA_SCREEN, _CARD_AREA[self.aura_side],
            success_wait=1)

    @node_from(from_name='点选光环卡')
    @operation_node(name='拖角色入主角槽')
    def drag_protagonist(self) -> OperationRoundResult:
        target = self._area_center(_SLOT_AREA)
        if target is None:
            return self.round_fail(status=f'area 缺失:{_SLOT_AREA}')
        self.ctx.controller.drag_to(end=target, start=self.source, duration=0.8)
        return self.round_success(status='已拖入主角槽(机械发出,零判效)', wait=1.5)

    @node_from(from_name='拖角色入主角槽')
    @operation_node(name='确认')
    def confirm(self) -> OperationRoundResult:
        target = self._area_center(_CONFIRM_AREA)
        if target is None:
            return self.round_fail(status=f'area 缺失:{_CONFIRM_AREA}')
        # 胶囊按钮微距拖拽:按下→横移4px→抬起(静态点击免疫,双局实机实证)
        self.ctx.controller.drag_to(
            end=Point(target.x + 4, target.y), start=target, duration=0.35)
        return self.round_success(
            status='已微距拖拽确认(机械发出,零判效;落位归下一帧观察)', wait=2)

    def _area_center(self, area_name: str) -> Point | None:
        screen_info = self.ctx.screen_loader.get_screen(_AURA_SCREEN)
        if screen_info is None:
            return None
        target = next((a for a in screen_info.area_list
                       if a.area_name == area_name), None)
        if target is None or target.pc_rect is None:
            return None
        return target.pc_rect.center
