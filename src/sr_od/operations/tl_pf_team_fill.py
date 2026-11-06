"""虚构叙事编队选人(清空两行 + 按目标填 8 人;落位回验驱动)。

模式与末日幻影填充循环(``tl_as_challenge``)同款 —— 均从同一轮死循环排查沉淀:
锚驱动列表识别 / 跳过已落位目标(**点击已在编队中的角色 = 将其移除**,不移除
会在搜索时把已填角色点掉) / 页签名集合到底判定 / 点卡带 press_time。

前置 = 虚构叙事-编队屏(选关点关卡纸鹤进入,本 op 不做跳转)。
交互模型(当期虚构叙事,游戏内期名「取象为文」):
- 编队屏两行×4 槽,每行对应战斗的一个节点;点槽位 = 展开左栏角色列表 + 选中
  该行(白框);点角色卡 = 加入当前选中行的下一个空槽;
- PF 的垃圾桶只清「当前选中行」,非全清(与忘却之庭编队屏的全清语义不同);
- 行选中守卫:点卡落在「当前选中的行」,点卡前必须显式点目标行槽位确保选中;
  列表展开态下直接点另一行槽位的选中切换不可靠(实测行为) → 收起列表后
  点目标行槽位(一步展开+选中)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.treasures_lightward.obs.tl_team_common import (
    AnchorCell,
    MemberGuess,
)
from sr_od.application.treasures_lightward.obs.tl_team_obs import (
    read_character_cells_by_level,
    read_team_nodes,
)
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

_TEAM_SCREEN: str = '虚构叙事-编队'

#: 角色列表滚动拖动(向下翻页;与忘却之庭编队屏同款列表)
_SCROLL_FROM: Point = Point(300, 760)
_SCROLL_TO: Point = Point(300, 430)

#: 编队行槽位 1 点击点(展开列表 + 选中该行;screen_info 行1/行2-槽位1 中心——
#: 空槽与已填头像同位同尺寸圆框)
_ROW_SLOT_POINTS: dict[int, Point] = {
    1: Point(1317, 772),
    2: Point(1317, 880),
}

#: 行垃圾桶点击点(清空当前选中行;⚠️ 只清选中行非全清)
_TRASH_POINTS: dict[int, Point] = {
    1: Point(1834, 693),
    2: Point(1834, 693),
}

#: 收起左栏角色列表:右上返回箭头
_COLLAPSE_POINT: Point = Point(1862, 68)


class TlPfTeamFillOp(SrOperation):
    """编队选人:清空两行 + 按目标填 8 人。起点 = 虚构叙事-编队屏。"""

    def __init__(self, ctx: SrContext, team_names: list[str]):
        SrOperation.__init__(self, ctx, op_name='虚构叙事 编队选人')
        if len(team_names) != 8:
            raise ValueError(f'虚构叙事需 8 名角色(2 行×4): {len(team_names)}')
        if len(set(team_names)) != 8:
            raise ValueError(
                f'虚构叙事 8 名角色须互不相同(重复角色会触发移除语义): {team_names}')
        self.teams: list[list[str]] = [
            team_names[i:i + 4] for i in range(0, 8, 4)
        ]
        for names in self.teams:
            for name in names:
                if next((c for c in CHARACTER_LIST if c.cn == name), None) is None:
                    raise ValueError(f'未知角色名: {name}')
        self._row_idx: int = 0            #: 当前填充的行(0 基)
        self._char_idx: int = 0           #: 当前行填到第几个(0 基)
        self._need_top: bool = True       #: 下一步需先滚回列表顶部
        self._down_stagnation: int = 0    #: 向下翻页停滞计数
        self._seen_sigs: set[str] = set() #: 本次搜索已见页签集合(到底判定:
        #:   底部翻页会在最后两页弹跳,页签交替出现,单比上一页无法累计停滞)
        self._need_row_select: bool = True #: 点卡前需先点目标行槽位选中(守卫)

    @operation_node(name='清空编队', is_start_node=True, node_max_retry_times=8)
    def _clear_teams(self) -> OperationRoundResult:
        """确认在编队屏并逐行清空(点行槽位选中 → 点垃圾桶,两行各一次)。

        ⚠️ PF 的垃圾桶只清「当前选中行」,非全清——仅点一次时行 2 残留成员从
        列表隐藏,填充将找不到目标;与忘却之庭编队屏的全清语义不同。清空幂等,
        对空行无副作用;点完直接 success 转入填充循环。"""
        screen = self.last_screenshot
        if not (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-虚构叙事行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            return self.round_fail('不在虚构叙事编队屏(前置:选关点关卡纸鹤)')
        for row_no in (1, 2):
            self.ctx.controller.click(_ROW_SLOT_POINTS[row_no], press_time=0.15)
            self.ctx.controller.click(_TRASH_POINTS[row_no], press_time=0.15)
        return self.round_success(wait=2)

    @node_from(from_name='清空编队')
    @operation_node(name='填充循环', node_max_retry_times=160)
    def _fill_loop(self) -> OperationRoundResult:
        """逐行逐角色填充:行选中守卫 → 读行成员回验落位 → 回顶 → 逐页找目标 → 点卡。

        落位回验是推进的唯一依据(点卡可能不落位):目标出现在行成员里才推进
        游标,否则重找重点同一目标。行选中守卫:点卡落在「当前选中的行」,
        点卡前必须显式点目标行槽位确保选中。"""
        image = self.last_screenshot
        if self._row_idx >= len(self.teams):
            # 全部落位:收起左栏列表,交装配环节
            self.ctx.controller.click(_COLLAPSE_POINT, press_time=0.15)
            return self.round_success('填充完成', wait=1)

        row_no = self._row_idx + 1
        target = self.teams[self._row_idx][self._char_idx]

        # 行选中守卫:点卡前目标行必须处于选中态(白框),否则角色会落进
        # 上一次选中的行。可靠操作序列 = 收起列表 → 点目标行槽位(一步展开+选中);
        # ⚠️ 列表展开态下直接点另一行槽位的选中切换不可靠(实测行为)。
        if self._need_row_select:
            cells = read_character_cells_by_level(self.ctx, image)
            if self._page_sig(cells):  # 列表展开 → 先收起
                self.ctx.controller.click(_COLLAPSE_POINT, press_time=0.15)
                return self.round_wait('收起列表以便重选目标行', wait=1)
            self.ctx.controller.click(_ROW_SLOT_POINTS[row_no], press_time=0.15)
            self._need_row_select = False
            self._need_top = True
            return self.round_wait(f'选中行 {row_no}', wait=1.5)

        # 落位回验:目标已在行成员里 → 推进游标(点卡可能被游戏吞掉不落位,
        # 这是推进的唯一依据;行槽位头像 74px 圆裁识别命中率高,成员名含候选表)
        nodes = read_team_nodes(self.ctx, image, screen_name=_TEAM_SCREEN)
        row_members = nodes[row_no - 1].members if len(nodes) >= row_no else []
        if not nodes:
            log.warning('PF填充: read_team_nodes 未读到任何行(PF 屏锚/area 失效?)')
        members_dbg = [f'{m.char or "?"}[{"|".join(n for n, _ in m.candidates)}]'
                       for m in row_members]
        log.info('PF填充回验: 行%d 成员=%s 目标=%s', row_no, members_dbg, target)
        if self._member_has(row_members, target):
            log.info('PF填充: 行%d %s 已落位', row_no, target)
            self._char_idx += 1
            self._need_top = True
            if self._char_idx >= 4:
                self._char_idx = 0
                self._row_idx += 1
                self._need_row_select = True  # 跨行:切换选中目标行
                return self.round_wait(f'行 {row_no} 填充完成', wait=1)
            return self.round_wait(f'{target} 已落位', wait=0.5)

        cells = read_character_cells_by_level(self.ctx, image)

        # 回顶 = 固定大幅快拖 3 次,不验证到位(列表天然止于顶部,拖过头无副作用;
        # 定案与实现同 tl_as_challenge._return_to_top)
        if self._need_top:
            for _ in range(3):
                self.ctx.controller.drag_to(
                    Point(300, 1000), start=Point(300, 200), duration=0.3)
            self._need_top = False
            self._down_stagnation = 0
            self._seen_sigs = set()
            return self.round_wait('回列表顶部', wait=2)

        # 顶部起逐页向下找目标;点卡后下一轮以落位回验推进(点卡落空自然重试)。
        # 名字匹配:guess.char(置信名)与 candidates[0](候选第一名)都参与。
        hit: AnchorCell | None = None
        for cell in cells:
            if target in self._cell_names(cell):
                hit = cell
                break
        if hit is not None:
            self.ctx.controller.click(hit.center, press_time=0.15)
            log.info('PF填充: 行%d 点 %s', row_no, target)
            return self.round_wait(f'点击 {target}', wait=1)

        sig = self._page_sig(cells)
        log.info('PF填充诊断: 找 %s 行%d stagnation=%d 页签=%s',
                 target, row_no, self._down_stagnation, sig[:80])
        # 到底判定用「已见页签集合」+ 弹跳 4 次容错(底部翻页弹跳 + 格子识别名
        # 跨帧随机缺失,复读大概率成功,2 次就放弃会误杀)
        if sig in self._seen_sigs:
            self._down_stagnation += 1
        else:
            self._down_stagnation = 0
            self._seen_sigs.add(sig)
        if self._down_stagnation >= 4:
            return self.round_fail(f'列表到底未找到 {target}')
        # 翻页后等滚动动画完全停止再识别(滚动未停帧脸库识别随机失败)
        self.ctx.controller.drag_to(_SCROLL_TO, start=_SCROLL_FROM, duration=0.6)
        return self.round_wait('向下翻页', wait=3)

    @staticmethod
    def _page_sig(cells: list[AnchorCell]) -> str:
        """当前页签名(可见格识别名集合,用于翻页/到顶判定)。"""
        return '|'.join(sorted(
            filter(None, (
                c.guess.char or (c.guess.candidates[0][0] if c.guess.candidates else '')
                for c in cells
            ))
        ))

    @staticmethod
    def _cell_names(cell: AnchorCell) -> list[str]:
        """格子可判名字列表:置信名在前,候选第一名在后(置信不足帧
        guess.char 为空,但候选第一名仍可信)。"""
        names: list[str] = []
        if cell.guess.char:
            names.append(cell.guess.char)
        if cell.guess.candidates:
            names.append(cell.guess.candidates[0][0])
        return names

    @staticmethod
    def _member_has(members: list[MemberGuess], target: str) -> bool:
        """行成员里是否已有目标(置信名/候选全表任一命中)。

        ⚠️ 不做前缀匹配:变体卡(丹恒•腾荒/姬子•启行)是独立角色,前缀命中会把
        「目标=丹恒」误判成「丹恒•腾荒 已落位」——跳过目标造成漏填。"""
        for m in members:
            names: list[str] = []
            if m.char:
                names.append(m.char)
            names.extend(n for n, _ in m.candidates)
            if target in names:
                return True
        return False
