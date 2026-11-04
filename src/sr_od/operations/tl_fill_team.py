"""忘却之庭(混沌回忆)编队屏:清空编队并按角色名填充两波队伍。

⚠️ 适用范围:仅忘却之庭的编队屏(screen = 忘却之庭-编队,槽位/建议属性/预设卡
area 均按混沌回忆布局标定)。逐光捡金其余玩法(虚构叙事/末日幻影/异相仲裁)的
编队屏布局与交互机制未探明,不可直接套用本 op —— 需另行建档后再写各自的填充 op
(人类老莫 2026-11-04 明确:其他类型的填充可能不一样)。

前置:已在本画面(``GotoTreasuresLightward`` 到选关 → 点关卡水晶 → 编队屏)。
交互模型(2026-11-04 实机实测):
- 点左栏角色卡 = 加入「当前选中行」的下一个空槽(行选中态 = 白框);
- 点队伍行敌人预览区 = 选中该行;右端垃圾桶(按钮-清空编队)= 全清,无确认弹窗;
- 左列表拖动滚动,每屏 16 格,拖一次约移 2 行。

填充目标按角色中文名给出(与脸库识别名一致);只点置信命中的格子(歧义格可能点错人,
错过就继续滚动找);每步点击后用波次识别回验成员落位,没落上会自然重试。
"""

from __future__ import annotations

from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.treasures_lightward.obs.tl_team_obs import (
    SCREEN_NAME,
    GridCell,
    MemberGuess,
    grid_cell_center,
    read_character_grid,
    read_left_tab,
    read_team_waves,
    wave_row_select_point,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class TlFillTeamsOp(SrOperation):

    STATUS_ALL_FILLED: ClassVar[str] = '编队填充完成'

    #: 左列表滚动拖动(向下翻页;2026-11-04 实测一次约移 2 行)
    _SCROLL_FROM: Point = Point(300, 760)
    _SCROLL_TO: Point = Point(300, 430)

    def __init__(self, ctx: SrContext, team_names: list[str]):
        """
        Args:
            team_names: 按波次顺序拼接的角色中文名列表(与脸库识别名一致),
                每 4 人切分为一波(当前混忆 2 波 = 8 人)。
        """
        SrOperation.__init__(self, ctx, op_name='逐光捡金 清空并填充编队')
        if len(team_names) % 4 != 0 or not 1 <= len(team_names) // 4 <= 4:
            raise ValueError(f'角色数须为 4 的倍数且波数 1-4: {len(team_names)}')
        self.teams: list[list[str]] = [
            team_names[i:i + 4] for i in range(0, len(team_names), 4)
        ]
        self._team_idx: int = 0            #: 当前填充到第几波(0 基)
        self._char_idx: int = 0            #: 当前波填到第几个(0 基)
        self._selected_wave: int = -1      #: 已选中行(1 基;-1 = 未选)
        self._need_top: bool = True        #: 下一步需要先滚回列表顶部
        self._down_stagnation: int = 0     #: 向下翻页停滞计数(连续两次同页 = 到底)
        self._last_page_sig: str = ''      #: 上一页签名(翻页/到顶判定)

    @operation_node(name='切换角色列表', is_start_node=True)
    def _switch_tab(self) -> OperationRoundResult:
        """确保左栏在角色列表 tab(从预设编队等状态切入)。"""
        tab = read_left_tab(self.ctx, self.last_screenshot)
        if tab == '角色列表':
            return self.round_success()
        click = self.round_by_find_and_click_area(
            self.last_screenshot, SCREEN_NAME, 'tab-角色列表', success_wait=1)
        if click.is_success:
            return self.round_wait('切换角色列表中', wait=0.5)
        return self.round_fail('未找到角色列表 tab')

    @node_from(from_name='切换角色列表')
    @operation_node(name='清空编队')
    def _clear_teams(self) -> OperationRoundResult:
        """点垃圾桶全清(无确认弹窗,实测);清空对空队伍无副作用。"""
        click = self.round_by_find_and_click_area(
            self.last_screenshot, SCREEN_NAME, '按钮-清空编队', success_wait=1)
        if not click.is_success:
            return self.round_fail('未找到清空按钮')
        waves = read_team_waves(self.ctx, self.last_screenshot)
        for wave in waves:
            for member in wave.members:
                if not member.empty:
                    return self.round_wait('清空确认中', wait=1)
        return self.round_success()

    @node_from(from_name='清空编队')
    # 填充循环的节点内重跑由 round_wait/round_retry 机制自动完成,不声明自环
    # (自环出边会让成功结果也沿边回到本节点,操作永不结束 —— 2026-11-04 实测)
    @operation_node(name='填充循环', node_max_retry_times=140)
    def _fill_loop(self) -> OperationRoundResult:
        """逐波逐角色填充主循环:每轮做一个原子动作,用波次识别回验落位。

        每个角色的搜索都先滚回列表顶部再逐页向下(人类老莫 2026-11-04 要求):
        滚动中途直接搜会因列表页序漂移丢失目标。
        """
        image = self.last_screenshot
        tab = read_left_tab(self.ctx, image)
        if tab != '角色列表':
            return self.round_by_find_and_click_area(
                image, SCREEN_NAME, 'tab-角色列表', success_wait=1)

        waves = read_team_waves(self.ctx, image)
        if len(waves) < len(self.teams):
            return self.round_fail(f'编队行数不足: {len(waves)} < {len(self.teams)}')
        if self._team_idx >= len(self.teams):
            return self.round_success(TlFillTeamsOp.STATUS_ALL_FILLED)

        wave = waves[self._team_idx]
        team = self.teams[self._team_idx]

        # 本波已全部落位 → 下一波
        if all(self._member_has(wave.members, name) for name in team):
            self._team_idx += 1
            self._char_idx = 0
            self._selected_wave = -1
            self._need_top = True
            return self.round_wait(f'波 {self._team_idx} 填充完成', wait=0.5)

        if self._char_idx >= len(team):
            self._char_idx = 0
            return self.round_wait('重扫当前波', wait=0.3)

        target = team[self._char_idx]
        if self._member_has(wave.members, target):
            self._char_idx += 1
            self._need_top = True
            return self.round_wait(f'{target} 已落位', wait=0.3)

        # 行选中:每波开工先点该行敌人预览区(非控件),后续点卡才落本行
        if self._selected_wave != self._team_idx + 1:
            point = wave_row_select_point(self.ctx, self._team_idx + 1)
            if point is None:
                return self.round_fail(f'波 {self._team_idx + 1} 槽位 area 缺失')
            self.ctx.controller.click(point)
            self._selected_wave = self._team_idx + 1
            self._need_top = True
            return self.round_wait(f'选中波 {self._team_idx + 1} 行', wait=0.5)

        # 每个角色搜索前先回列表顶部(页签连续两次相同 = 到顶)
        if self._need_top:
            cells = read_character_grid(self.ctx, image)
            sig = TlFillTeamsOp._page_sig(cells)
            if sig == self._last_page_sig:
                self._need_top = False
                self._down_stagnation = 0
                self._last_page_sig = ''
                return self.round_wait('已回到列表顶部', wait=0.3)
            self._last_page_sig = sig
            self.ctx.controller.drag_to(
                Point(300, 760), start=Point(300, 430), duration=0.5)
            return self.round_wait('滚回列表顶部', wait=0.7)

        # 顶部起逐页向下找目标(只点置信命中;歧义格可能点错人,跳过继续)
        cells = read_character_grid(self.ctx, image)
        hit: GridCell | None = None
        for cell in cells:
            if cell.guess.char == target:
                hit = cell
                break
        if hit is not None:
            center = grid_cell_center(self.ctx, hit.row, hit.col)
            if center is None:
                return self.round_fail('区域-角色网格缺失')
            self.ctx.controller.click(center)
            self._need_top = True   # 下一个角色重新回顶
            return self.round_wait(f'点击 {target}', wait=0.8)

        # 未命中 → 向下翻页;连续停滞 = 到底
        sig = TlFillTeamsOp._page_sig(cells)
        if sig == self._last_page_sig:
            self._down_stagnation += 1
        else:
            self._down_stagnation = 0
        self._last_page_sig = sig
        if self._down_stagnation >= 2:
            return self.round_fail(f'列表到底未找到 {target}(不点歧义格)')
        self.ctx.controller.drag_to(
            TlFillTeamsOp._SCROLL_TO, start=TlFillTeamsOp._SCROLL_FROM, duration=0.6)
        return self.round_wait('向下翻页', wait=0.8)

    @staticmethod
    def _page_sig(cells: list[GridCell]) -> str:
        """当前页签名(可见格识别名集合,用于翻页/到顶判定)。"""
        return '|'.join(sorted(
            filter(None, (
                c.guess.char or (c.guess.candidates[0][0] if c.guess.candidates else '')
                for c in cells
            ))
        ))

    @staticmethod
    def _member_has(members: list[MemberGuess], name: str) -> bool:
        """成员里是否已有该角色(置信名或候选集任一命中)。"""
        for member in members:
            names = {member.char, *(c for c, _ in member.candidates)}
            if name in names:
                return True
        return False
