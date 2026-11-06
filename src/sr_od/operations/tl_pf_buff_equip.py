"""虚构叙事增益装配:左栏战意效果单选 + 两行荒腔走板弹窗三选一。

起点 = 虚构叙事-编队屏(已填人);终点 = 编队屏(已装配)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.treasures_lightward.obs.tl_team_common import (
    get_area_center_point,
)
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

_TEAM_SCREEN: str = '虚构叙事-编队'
_CACOPHONY_SCREEN: str = '虚构叙事-荒腔走板'

#: 装配加号(行右端圆形按钮,已入队后出现;screen_info 行1/行2-装配加号 中心)
_EQUIP_POINTS: dict[int, Point] = {
    1: Point(1830, 780),
    2: Point(1830, 888),
}


class TlPfBuffEquipOp(SrOperation):
    """增益装配:左栏战意效果单选 + 两行荒腔走板弹窗三选一装配。

    起点 = 虚构叙事-编队屏(已填人);终点 = 编队屏(已装配)。"""

    def __init__(self, ctx: SrContext, buff_slot: int = 1,
                 buff_slots: list[int] | None = None):
        """
        Args:
            buff_slot: 左栏战意效果序号(1 基,按编队屏左栏可见列表上下序;
                效果名称随期轮换不可锚定,按位置选择;效果多于 2 个时需先滚动,
                当前仅支持可见两槽)。
            buff_slots: 每行荒腔走板增益序号(1 基,每行三选一;增益名称随期
                轮换不可锚定,按卡片位置选择)。默认 [1, 1] = 各装第一项。
                list 注解而非 tuple:op 经 MCP JSON 参数发起,tuple 不可反序列化。
        """
        SrOperation.__init__(self, ctx, op_name='虚构叙事 增益装配')
        if buff_slots is None:
            buff_slots = [1, 1]
        if len(buff_slots) != 2:
            raise ValueError(f'buff_slots 须为 2 行各一个: {buff_slots}')
        if not 1 <= buff_slot <= 2:
            raise ValueError(f'buff_slot 须为 1-2(可见两槽): {buff_slot}')
        if any(not 1 <= s <= 3 for s in buff_slots):
            raise ValueError(f'buff_slots 须为 1-3: {buff_slots}')
        self._buff_slot: int = buff_slot
        self._buff_slots: tuple[int, int] = (buff_slots[0], buff_slots[1])
        self._phase: str = 'war_effect'   #: 装配子步:war_effect 战意效果 →
                                          # open 点行加号 / select 选卡 / confirm 装配
        self._row_idx: int = 0            #: 当前装配的行(0 基)

    @operation_node(name='装配循环', is_start_node=True, node_max_retry_times=24)
    def _equip_loop(self) -> OperationRoundResult:
        """装配主循环:战意效果单选 → 逐行荒腔走板装配(弹窗选卡→装配效果)。

        荒腔走板装配生效后弹窗自动关闭回编队屏(实机验证),以「装配效果」
        按钮消失为到达证据。"""
        screen = self.last_screenshot
        in_team = (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-虚构叙事行').is_success
                   and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success)
        in_popup = self.round_by_find_area(
            screen, _CACOPHONY_SCREEN, '文本-选择增益行').is_success

        if self._phase == 'war_effect':
            if not in_team:
                return self.round_retry('不在编队屏(战意效果选择前置)', wait=1.5)
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _TEAM_SCREEN,
                                      f'战意效果-槽{self._buff_slot}'), press_time=0.15)
            self._phase = 'open'
            return self.round_wait('战意效果已点选', wait=1)

        row_no = self._row_idx + 1
        if self._phase == 'open':
            if in_popup:
                self._phase = 'select'
                return self.round_wait(f'行{row_no}弹窗已开', wait=0.5)
            if in_team:
                self.ctx.controller.click(_EQUIP_POINTS[row_no], press_time=0.15)
                self._phase = 'select'
                return self.round_wait(f'点行{row_no}装配加号', wait=1.5)
            return self.round_retry('不在编队屏也非弹窗', wait=1.5)

        if self._phase == 'select':
            if not in_popup:
                self._phase = 'open'
                return self.round_retry('弹窗未开,重开', wait=1.2)
            slot = self._buff_slots[row_no - 1]
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _CACOPHONY_SCREEN,
                                      f'卡片-增益{slot}'), press_time=0.15)
            self._phase = 'confirm'
            return self.round_wait(f'行{row_no}选增益{slot}', wait=1)

        # confirm:点装配效果 → 弹窗自动关闭回编队屏 = 装配生效
        click = self.round_by_find_and_click_area(
            screen, _CACOPHONY_SCREEN, '按钮-装配效果', success_wait=1.5)
        if click.is_success:
            self._row_idx += 1
            if self._row_idx >= len(self._buff_slots):
                if in_team:
                    return self.round_success('装配完成', wait=1)
                self._phase = 'closed'
                return self.round_wait('装配点击完成,等弹窗关闭', wait=1.5)
            self._phase = 'open'
            return self.round_wait(f'行{row_no}装配完成', wait=1.5)
        # 弹窗已关(装配成功但本轮没抓到按钮)或弹窗仍在
        if in_team:
            self._row_idx += 1
            if self._row_idx >= len(self._buff_slots):
                return self.round_success('装配完成', wait=1)
            self._phase = 'open'
            return self.round_wait(f'行{row_no}装配完成', wait=1.5)
        return self.round_retry('装配效果未生效,重按', wait=1.2)
