"""末日幻影终焉公理装配:两行右端圆圈 → 弹窗选卡 → 装配效果。

起点 = 编队屏(已填人);终点 = 编队屏(已装配)。增益入口分派:
星启 = 行尾「+」按钮 area(04- 前缀),双节点 = 建档「公理圆圈N」。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

_TEAM_SCREEN: str = '末日幻影-编队'
_AXIOM_SCREEN: str = '末日幻影-终焉公理'

_ARC_AXIOM_AREAS: dict[int, str] = {
    1: '04-增益入口-行1',
    2: '04-增益入口-行2',
    3: '04-增益入口-行3',
}


class TlAsAxiomEquipOp(SrOperation):
    """终焉公理装配:两行右端圆圈 → 弹窗选卡 → 装配效果。起点 = 编队屏(已填人)。"""

    def __init__(self, ctx: SrContext, buff_slots: tuple[int, ...] | list[int] = (1, 1)):
        """
        Args:
            buff_slots: 每行装配的终焉公理增益序号(1 基,每行三选一;
                增益名称随期轮换不可锚定,按卡片位置选择)。
                2 项 = 双节点(01-03);3 项 = 星启三节点。默认 (1, 1)。
                接受 list(MCP JSON 反序列化产物),内部转 tuple。
        """
        SrOperation.__init__(self, ctx, op_name='末日幻影 终焉公理装配')
        buff_slots = tuple(buff_slots)
        if any(not 1 <= s <= 3 for s in buff_slots):
            raise ValueError(f'buff_slots 须为 1-3: {buff_slots}')
        if len(buff_slots) not in (2, 3):
            raise ValueError(f'buff_slots 需 2(双节点)或 3(星启)项: {buff_slots}')
        self._buff_slots: tuple[int, ...] = buff_slots
        # 增益入口分派按布局模式(星启 = 行尾「+」area,双节点 = 建档圆圈);
        # 星启判定 = 3 项增益,与 TlAsTeamFillOp 的 12 人判定同构
        self._arc_mode: bool = len(buff_slots) == 3
        self._row_idx: int = 0              #: 当前装配行(0 基)
        self._phase: str = 'open'           #: 装配子步:open 点圆圈 / select 点卡片 /
                                            # confirm 点装配效果 / closed 等弹窗关

    @operation_node(name='装配循环', is_start_node=True, node_max_retry_times=16)
    def _equip_loop(self) -> OperationRoundResult:
        """逐行装配指定增益进终焉公理(行增益入口 → 弹窗选卡 → 装配效果)。

        行内「敌方特性」条款按钮(坚防守备/阵地转移等)是机制查看入口,点击
        不改变装配(实机验证);增益入口分派:星启 = 行尾「+」按钮(x≈1826,
        y 与行同轴),双节点 = 建档「公理圆圈{row}」;增益名称随期轮换不可
        锚定,按位置 ``buff_slots``(1 基)选卡。装配生效后弹窗自动关闭回
        编队屏,以「装配效果」按钮消失为到达证据。"""
        row = self._row_idx + 1
        screen = self.last_screenshot
        in_axiom = self.round_by_find_area(screen, _AXIOM_SCREEN, '文本-选择增益行').is_success
        in_team = (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-末日幻影行').is_success
                   and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success)

        if self._phase == 'open':
            if in_axiom:
                self._phase = 'select'
                return self.round_wait('公理弹窗已开', wait=0.5)
            if in_team:
                if self._arc_mode:
                    # 星启:行尾「+」即终焉公理入口(编入角色前后形态一致,实测);
                    # 分派必须按布局模式——按行号比较会把 04 的行 2/3 错派到
                    # 01-03 圆圈坐标(该坐标在 04 无效,弹窗开不了死循环)
                    self._click_area_center(_TEAM_SCREEN, _ARC_AXIOM_AREAS[row])
                else:
                    self._click_area_center(_TEAM_SCREEN, f'按钮-公理圆圈{row}')
                self._phase = 'select'
                return self.round_wait(f'打开行{row}公理弹窗', wait=1.5)
            return self.round_retry('不在编队屏也非公理弹窗', wait=1.5)

        if self._phase == 'select':
            if not in_axiom:
                self._phase = 'open'
                return self.round_retry('公理弹窗未开,重开', wait=1.2)
            slot = self._buff_slots[self._row_idx]
            self._click_area_center(_AXIOM_SCREEN, f'卡片-增益{slot}')
            self._phase = 'confirm'
            return self.round_wait(f'行{row}选增益{slot}', wait=0.8)

        if self._phase == 'confirm':
            click = self.round_by_find_and_click_area(
                screen, _AXIOM_SCREEN, '按钮-装配效果', success_wait=1.2)
            if click.is_success:
                self._phase = 'closed'
                return self.round_wait(f'行{row}装配确认', wait=1.5)
            return self.round_retry('装配效果按钮未命中', wait=1)

        # closed:弹窗应已自动关闭,到达编队屏 = 装配生效
        if in_team:
            if self._row_idx < len(self._buff_slots) - 1:
                self._row_idx += 1
                self._phase = 'open'
                return self.round_wait(f'行{row}装配完成', wait=1)
            return self.round_success('装配完成', wait=1)
        if in_axiom:
            self._phase = 'confirm'
            return self.round_retry('弹窗未关,重按装配', wait=1.2)
        return self.round_retry('画面异常(既非编队屏也非公理弹窗)', wait=1.5)

    def _click_area_center(self, screen_name: str, area_name: str) -> None:
        """按建档 rect 中心点击(纯定位区;坐标单一真相源在 screen_info)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        rect = area.rect
        self.ctx.controller.click(
            Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2), press_time=0.15)
