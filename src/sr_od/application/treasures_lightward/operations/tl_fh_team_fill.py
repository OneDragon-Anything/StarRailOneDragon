"""忘却之庭(混沌回忆)编队屏:清空编队并按角色名填充两节点队伍。

⚠️ 适用范围:仅忘却之庭的编队屏(screen = 忘却之庭-编队,槽位/建议属性/预设卡
area 均按混沌回忆布局标定)。虚构叙事/末日幻影各有自己的填充 op
(``tl_pf_team_fill.TlPfTeamFillOp`` / ``tl_as_challenge`` 内嵌填充循环)。

前置:已在本画面(``GotoTreasuresLightward`` 到选关 → 点关卡水晶 → 编队屏)。
交互模型(2026-11-04 实机实测):
- 点左栏角色卡 = 加入「当前选中行」的下一个空槽(行选中态 = 白框);
- 点队伍行敌人预览区 = 选中该行;右端垃圾桶(按钮-清空编队)= 全清,无确认弹窗;
- 左列表拖动滚动,每屏 16 格。

填充目标按角色中文名给出(与脸库识别名一致)。模式与末日幻影填充循环
(``tl_as_challenge``)同款 —— 均从同一轮死循环排查沉淀:
- 列表识别用**等级锚驱动**(``read_character_cells_by_level``,滚动停驻位置无关),
  不用固定网格(要求停驻与标定帧一致,拖动误差累积会整页错位);
- 回验锚未读到 ≠ 成员为空(降级空列表会误判「已落位/已清空」死循环点卡)→ 重读;
- 找卡命中 = 置信名或候选第一名(与回验同口径,减少「识别得出但找不到」的分叉);
- 点卡带 press_time(短点击偶发不落地,重试会再点同一张);
- 回顶 = 固定大幅快拖 3 次,不验证到位(列表天然止于顶部,拖过头无副作用);
- 翻页停滞用见过的页签名集合判(同页反复出现 = 到底),空识别帧不计停滞。
"""
from __future__ import annotations

from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.treasures_lightward.obs.tl_team_obs import (
    SCREEN_NAME,
    AnchorCell,
    MemberGuess,
    node_row_select_point,
    read_character_cells_by_level,
    read_left_tab,
    read_team_nodes,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class TlFhTeamFillOp(SrOperation):

    STATUS_ALL_FILLED: ClassVar[str] = '编队填充完成'

    #: 向下翻页(慢拖;列表几何与末日幻影编队屏同构,标定沿用其实测值:
    #: 400px/0.5s = 精准 3 行无过冲,落定即识别清晰)
    _SCROLL_FROM: Point = Point(300, 850)
    _SCROLL_TO: Point = Point(300, 450)
    _SCROLL_DURATION: float = 0.5
    #: 回顶(固定大幅快拖 3 次,任何起点都到顶;不验证到位 —— 定案见
    #: tl_as_challenge._return_to_top 注释)
    _TOP_FROM: Point = Point(300, 200)
    _TOP_TO: Point = Point(300, 1000)
    _TOP_DURATION: float = 0.3
    _TOP_DRAG_COUNT: int = 3

    def __init__(self, ctx: SrContext, team_names: list[str]):
        """
        Args:
            team_names: 按节点顺序拼接的角色中文名列表(与脸库识别名一致),
                每 4 人切分为一节点(当前混忆 2 节点 = 8 人)。
        """
        SrOperation.__init__(self, ctx, op_name='逐光捡金 清空并填充编队')
        if len(team_names) % 4 != 0 or not 1 <= len(team_names) // 4 <= 4:
            raise ValueError(f'角色数须为 4 的倍数且节点数 1-4: {len(team_names)}')
        self.teams: list[list[str]] = [
            team_names[i:i + 4] for i in range(0, len(team_names), 4)
        ]
        self._team_idx: int = 0            #: 当前填充到第几节点(0 基)
        self._char_idx: int = 0            #: 当前节点填到第几个(0 基)
        self._selected_node: int = -1      #: 已选中行(1 基;-1 = 未选)
        self._need_top: bool = True        #: 下一步需要先滚回列表顶部
        self._down_stagnation: int = 0     #: 向下翻页停滞计数(见过的页签名再现 = 停滞)
        self._seen_sigs: set[str] = set()  #: 已见过的页签名集合(到底判定)

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
        """点垃圾桶全清(无确认弹窗,实测);清空对空队伍无副作用。

        节点识别锚未读到 = 降级空列表,**不可当「已清空」用**(会假绿跳过清空,
        残留成员把后续填充的全量校验打穿)→ 重读。"""
        click = self.round_by_find_and_click_area(
            self.last_screenshot, SCREEN_NAME, '按钮-清空编队', success_wait=1)
        if not click.is_success:
            return self.round_fail('未找到清空按钮')
        nodes = read_team_nodes(self.ctx, self.last_screenshot)
        if not nodes:
            return self.round_retry('节点识别锚未读到,不可确认清空,重读', wait=1)
        for node in nodes:
            for member in node.members:
                if not member.empty:
                    return self.round_wait('清空确认中', wait=1)
        return self.round_success()

    @node_from(from_name='清空编队')
    # 填充循环的节点内重跑由 round_wait/round_retry 机制自动完成,不声明自环
    # (自环出边会让成功结果也沿边回到本节点,操作永不结束 —— 2026-11-04 实测)
    @operation_node(name='填充循环', node_max_retry_times=140)
    def _fill_loop(self) -> OperationRoundResult:
        """逐节点逐角色填充主循环:每轮做一个原子动作,用节点识别回验落位。

        每个角色的搜索都先滚回列表顶部再逐页向下(人类老莫 2026-11-04 要求):
        滚动中途直接搜会因列表页序漂移丢失目标。"""
        image = self.last_screenshot
        tab = read_left_tab(self.ctx, image)
        if tab != '角色列表':
            return self.round_by_find_and_click_area(
                image, SCREEN_NAME, 'tab-角色列表', success_wait=1)

        nodes = read_team_nodes(self.ctx, image)
        if len(nodes) < len(self.teams):
            # 锚未读到 = 降级空列表 ≠ 行数不足;但两者处理一致(读不出就重读),
            # 只有读得到且行数确实少才是配置错误
            return self.round_retry(
                f'节点识别未就绪或行数不足: 读到 {len(nodes)} 行,需 {len(self.teams)} 行',
                wait=1.5)
        if self._team_idx >= len(self.teams):
            return self.round_success(TlFhTeamFillOp.STATUS_ALL_FILLED)

        node = nodes[self._team_idx]
        team = self.teams[self._team_idx]

        # 本节点已全部落位 → 下一节点
        if all(self._member_has(node.members, name) for name in team):
            self._team_idx += 1
            self._char_idx = 0
            self._selected_node = -1
            self._need_top = True
            return self.round_wait(f'节点 {self._team_idx} 填充完成', wait=0.5)

        if self._char_idx >= len(team):
            self._char_idx = 0
            return self.round_wait('重扫当前节点', wait=0.3)

        target = team[self._char_idx]
        if self._member_has(node.members, target):
            self._char_idx += 1
            self._need_top = True
            return self.round_wait(f'{target} 已落位', wait=0.3)

        # 行选中:每节点开工先点该行敌人预览区(非控件),后续点卡才落本行
        if self._selected_node != self._team_idx + 1:
            point = node_row_select_point(self.ctx, self._team_idx + 1)
            if point is None:
                return self.round_fail(f'节点 {self._team_idx + 1} 槽位 area 缺失')
            self.ctx.controller.click(point)
            self._selected_node = self._team_idx + 1
            self._need_top = True
            return self.round_wait(f'选中节点 {self._team_idx + 1} 行', wait=0.5)

        if self._need_top:
            return self._return_to_top()

        cells = read_character_cells_by_level(self.ctx, image)
        if not cells:
            # 空识别帧(滚动余动/展开动画)不参与停滞判定,直接重读
            return self.round_wait('列表识别未就绪,重读', wait=1)

        # 找目标:置信名或候选第一名命中(与槽位回验同口径)
        hit: AnchorCell | None = None
        for cell in cells:
            names = {cell.guess.char, *(n for n, _ in cell.guess.candidates)}
            if target in names:
                hit = cell
                break
        if hit is not None:
            self.ctx.controller.click(hit.center, press_time=0.15)
            self._need_top = True   # 下一个角色重新回顶
            return self.round_wait(f'点击 {target}', wait=0.8)

        return self._page_down(cells, target)

    def _return_to_top(self) -> OperationRoundResult:
        """固定大幅快拖回顶,不验证到位(拖过头无副作用,定案见常量注释)。"""
        for _ in range(self._TOP_DRAG_COUNT):
            self.ctx.controller.drag_to(
                self._TOP_TO, start=self._TOP_FROM, duration=self._TOP_DURATION)
        self._need_top = False
        self._down_stagnation = 0
        self._seen_sigs = set()
        return self.round_wait('回列表顶部', wait=2)

    def _page_down(self, cells: list[AnchorCell], target: str) -> OperationRoundResult:
        """当前页无目标:页签停滞判定 + 向下翻页(见过的签名再现 = 到底 = fail)。"""
        sig = self._page_sig(cells)
        if not sig:
            return self.round_wait('列表识别未就绪,不计停滞', wait=1.5)
        log.info(f'填充诊断: 找 {target} stagnation={self._down_stagnation} '
                 f'页签名={sig[:80]}')
        if sig in self._seen_sigs:
            self._down_stagnation += 1
        else:
            self._down_stagnation = 0
            self._seen_sigs.add(sig)
        if self._down_stagnation >= 4:
            return self.round_fail(
                f'列表到底未找到 {target}(不点歧义格);已扫页签名数={len(self._seen_sigs)}')
        self.ctx.controller.drag_to(
            self._SCROLL_TO, start=self._SCROLL_FROM,
            duration=self._SCROLL_DURATION)
        return self.round_wait('向下翻页', wait=2)

    @staticmethod
    def _page_sig(cells: list[AnchorCell]) -> str:
        """当前页签名(可见格识别名集合,用于翻页/到底判定)。"""
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
