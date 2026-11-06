"""虚构叙事完整挑战(组合 op):编队选人 → 战意效果与荒腔走板装配 → 进入故事 →
节点战斗推进 → 结算返回。

拆分为多个可独立 ``run_operation`` 的 op(与末日幻影同构的组合模式):

- :class:`TlPfTeamFillOp` 编队选人:清空两行 + 按目标填 8 人;
  起点 = 虚构叙事-编队,终点 = 编队屏(已填满)。
- :class:`TlPfBuffEquipOp` 增益装配:左栏战意效果单选 + 两行荒腔走板弹窗
  三选一装配;起点 = 编队屏(已填人),终点 = 编队屏(已装配)。
- :class:`TlPfBattleOp` 节点战斗推进:进入故事 → 关卡简报关闭 → 前进+秘技+
  开战 → 战斗等待 → 结算返回;起点 = 编队屏(已装配),终点 = 虚构叙事选关。
- :class:`TlPureFictionChallengeOp` 组合(类名保持兼容):入口多态 → 选人 →
  装配 → 战斗推进。

前置:``GotoTreasuresLightward(TLMode.PURE_FICTION)`` 到虚构叙事选关 → 点目标
关卡纸鹤进编队屏后调用本 op(本 op 不做选关→编队的跳转)。

交互模型(当期虚构叙事,游戏内期名「取象为文」):

- 编队屏两行×4 槽,每行对应战斗的一个节点;点槽位 = 展开左栏角色列表 + 选中
  该行(白框);点角色卡 = 加入当前选中行的下一个空槽;**点击已在编队中的角色
  = 将其移除**(填充搜索时必须跳过已落位目标,否则会把已填角色点掉);
- **增益系统双层**(2026-11-06 实机建档):
  ① 左栏「战意效果」列表(编队屏内,全局单选——两节点共用):点效果名称条
     选中(金色名称条 = 当前装配),可滚动,本期可见 2 个;
  ② 行右端圆形加号(已入队后出现)→「荒腔走板」弹窗(per 行三选一:触技/
     笑韵/赋格,名称随期轮换):点效果卡 → 点「装配效果」→ 弹窗自动关闭;
- 「进入故事」点击生效后弹关卡简报横幅(「点击空白处关闭」),点画面下部
  空白关闭后才进节点画面;
- 节点画面为锁光标大世界:前进接近敌人 → 施放秘技(复用框架 UseTechnique,
  攻击型秘技施放即入战斗)→ 点击画面中心开战;自动战斗由游戏继承上一次
  设置,op 不接管;
- 每关 2 节点 × 3 波,节点间自动衔接(自动切队伍到下一节点出生点),无需操作;
- 结算「挑战成功」→「返回虚构叙事」→ 虚构叙事选关。
"""

from __future__ import annotations

from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.treasures_lightward.obs.tl_team_obs import (
    AnchorCell,
    read_character_cells_by_level,
    read_team_nodes,
)
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.technique import UseTechnique

_SELECT_SCREEN: str = '逐光捡金'
_TEAM_SCREEN: str = '虚构叙事-编队'
_CACOPHONY_SCREEN: str = '虚构叙事-荒腔走板'
_NODE_SCREEN: str = '忘却之庭-节点画面'  # 节点画面左栏锚(查看详情)与 FH 同构,复用其 area

#: 角色列表滚动拖动(向下翻页;与忘却之庭编队屏同款列表,一次约移 2 行)
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

#: 装配加号(行右端圆形按钮,已入队后出现;screen_info 行1/行2-装配加号 中心)
_EQUIP_POINTS: dict[int, Point] = {
    1: Point(1830, 780),
    2: Point(1830, 888),
}

#: 收起左栏角色列表:右上返回箭头
_COLLAPSE_POINT: Point = Point(1862, 68)

#: 关卡简报空白关闭点(横幅下半部无元素区)
_BRIEF_CLOSE_POINT: Point = Point(960, 950)

#: 节点画面开战点击点(画面中心,initiate_attack 等价)
_ATTACK_POINT: Point = Point(960, 540)


def _area_center_point(ctx: SrContext, screen_name: str, area_name: str) -> Point:
    """按建档 rect 算中心点(坐标单一真相源在 screen_info)。"""
    area = ctx.screen_loader.get_area(screen_name, area_name)
    rect = area.rect
    return Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2)


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
    def _page_sig(cells: list) -> str:
        """当前页签名(可见格识别名集合,用于翻页/到顶判定)。

        cells 元素为带 .guess 的识别单元(GridCell/AnchorCell 鸭子兼容)。"""
        return '|'.join(sorted(
            filter(None, (
                c.guess.char or (c.guess.candidates[0][0] if c.guess.candidates else '')
                for c in cells
            ))
        ))

    @staticmethod
    def _cell_names(cell) -> list[str]:
        """格子可判名字列表:置信名在前,候选第一名在后(置信不足帧
        guess.char 为空,但候选第一名仍可信)。"""
        names: list[str] = []
        if cell.guess.char:
            names.append(cell.guess.char)
        if cell.guess.candidates:
            names.append(cell.guess.candidates[0][0])
        return names

    @staticmethod
    def _member_has(members, target: str) -> bool:
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
                _area_center_point(self.ctx, _TEAM_SCREEN,
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
                _area_center_point(self.ctx, _CACOPHONY_SCREEN,
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


class TlPfBattleOp(SrOperation):
    """节点战斗推进:进入故事 → 简报关闭 → 前进+秘技+开战 → 战斗等待 → 结算返回。

    起点 = 虚构叙事-编队屏(已装配);终点 = 结算「返回虚构叙事」后到达选关。"""

    STATUS_DONE: ClassVar[str] = '挑战完成'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='虚构叙事 节点战斗')
        self._tech_used: bool = False  #: 当前节点秘技已施放(节点自动衔接共 2 节点
                                       #  一场连续战斗,全程只需一次)

    @operation_node(name='进入故事', is_start_node=True, node_max_retry_times=10)
    def _start(self) -> OperationRoundResult:
        """点「进入故事」→ 到达验证:关卡简报横幅或节点画面出现。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY').is_success
                or self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success):
            return self.round_success()
        if self.round_by_find_area(screen, _TEAM_SCREEN, '按钮-进入故事').is_success:
            self.ctx.controller.click(
                _area_center_point(self.ctx, _TEAM_SCREEN, '按钮-进入故事'),
                press_time=0.2)
            return self.round_retry('点击进入故事', wait=2)
        return self.round_retry('画面异常(既非编队屏也未见简报/节点)', wait=1.5)

    @node_from(from_name='进入故事')
    @operation_node(name='关卡简报处理', node_max_retry_times=8)
    def _brief(self) -> OperationRoundResult:
        """关卡简报横幅(本期战斗机制说明页)→ 点空白关闭;节点画面 → 进入战斗循环。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY').is_success:
            self.ctx.controller.click(_BRIEF_CLOSE_POINT, press_time=0.15)
            return self.round_wait('关闭关卡简报', wait=2)
        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            return self.round_success()
        return self.round_retry('等待节点画面', wait=1.5)

    @node_from(from_name='关卡简报处理')
    @operation_node(name='节点战斗循环', node_max_retry_times=360)
    def _battle_loop(self) -> OperationRoundResult:
        """单循环按画面特征每轮分流:结算 → 收尾;待命 → 秘技开战;其余 → 战斗中等待。

        待命态判据 = 节点画面左栏「查看详情」(PF 与 FH 节点画面同构);
        战斗中左栏被战斗 UI 替换故不误判。节点间自动衔接(游戏自动切队伍到
        下一节点出生点),一场连续战斗,秘技全程施放一次。"""
        screen = self.last_screenshot

        if (self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_SUCCESS_1').is_success
                or self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_SUCCESS_2').is_success):
            return self.round_success(TlPfBattleOp.STATUS_DONE)
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_FAIL').is_success:
            return self.round_fail('战斗失败')

        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            if not self._tech_used:
                # 未施秘技:前进接近后施放(攻击型秘技施放即入战斗,本轮结束
                # 重新分流走战斗等待;增益型下一轮走到点击开战分支)
                self.ctx.controller.move('w', press_time=2)
                tech_op = UseTechnique(self.ctx)
                tech_op.execute()
                self._tech_used = True
                return self.round_retry('施放秘技', wait=3)
            # 秘技已施放:前进 + 框架标准开战(initiate_attack = 点击画面中心)
            self.ctx.controller.move('w', press_time=2)
            self.ctx.controller.initiate_attack()
            return self.round_retry('发起战斗', wait=5)

        # 战斗中等待(一局 2 节点 6 波正常 ~60 轮内,360 轮 = 30 分钟兜底退出)
        return self.round_retry('战斗进行中', wait=5)

    @node_from(from_name='节点战斗循环', status=STATUS_DONE)
    @operation_node(name='返回虚构叙事', node_max_retry_times=12)
    def _click_back(self) -> OperationRoundResult:
        """结算画面点「返回虚构叙事」→ 虚构叙事选关。

        首次 3 星通关会弹「快速通关」确认(视同通关所有前置难度,点确认领取),
        先处理再判定到达选关。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_TITLE').is_success:
            return self.round_success()
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, '按钮-快速通关确认').is_success:
            self.ctx.controller.click(Point(960, 611), press_time=0.15)
            return self.round_wait('领取快速通关奖励', wait=2)
        click = self.round_by_find_and_click_area(
            screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_BACK_BTN', success_wait=2)
        if click.is_success:
            return self.round_wait('返回虚构叙事中', wait=1.5)
        return self.round_retry('未找到返回按钮', wait=1)


class TlPureFictionChallengeOp(SrOperation):
    """虚构叙事完整挑战(组合 op):选人 → 增益装配 → 战斗推进 → 返回选关。"""

    STATUS_SUCCESS: ClassVar[str] = '挑战成功'

    def __init__(self, ctx: SrContext, team_names: list[str],
                 buff_slot: int = 1, buff_slots: list[int] | None = None):
        """
        Args:
            team_names: 按行(节点)顺序拼接的角色中文名列表,8 人(2 行×4);
                与脸库识别名一致,行 1 = 节点一队伍,行 2 = 节点二队伍。
            buff_slot: 左栏战意效果序号(1 基,按编队屏左栏可见列表上下序)。
            buff_slots: 每行荒腔走板增益序号(1 基,每行三选一,按卡片位置选择)。
        """
        SrOperation.__init__(self, ctx, op_name='虚构叙事 挑战')
        self.fill_op = TlPfTeamFillOp(ctx, team_names)
        self.equip_op = TlPfBuffEquipOp(ctx, buff_slot, buff_slots)
        self.battle_op = TlPfBattleOp(ctx)

    @operation_node(name='进入编队屏', is_start_node=True, node_max_retry_times=10)
    def _enter_team(self) -> OperationRoundResult:
        """确认在虚构叙事编队屏(前置:选关点关卡纸鹤,本 op 不做该跳转)。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-虚构叙事行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            return self.round_success()
        return self.round_fail('不在虚构叙事编队屏(前置:选关点关卡纸鹤)')

    @node_from(from_name='进入编队屏')
    @operation_node(name='编队选人', node_max_retry_times=8)
    def _fill(self) -> OperationRoundResult:
        """组合 :class:`TlPfTeamFillOp`(清空 + 填 8 人,落位回验驱动)。"""
        op_result = self.fill_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='编队选人')
    @operation_node(name='增益装配', node_max_retry_times=8)
    def _equip(self) -> OperationRoundResult:
        """组合 :class:`TlPfBuffEquipOp`(战意效果单选 + 荒腔走板装配)。"""
        op_result = self.equip_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='增益装配')
    @operation_node(name='战斗推进', node_max_retry_times=8)
    def _battle(self) -> OperationRoundResult:
        """组合 :class:`TlPfBattleOp`(进入故事 → 秘技开战 → 战斗 → 结算返回)。"""
        op_result = self.battle_op.execute()
        return self.round_by_op_result(op_result)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.start_running()
    op = TlPureFictionChallengeOp(
        ctx,
        ['姬子•启行', '瓦尔特', '知更鸟', '丹恒•腾荒', '黄泉', '卡芙卡', '黑天鹅', '灵砂'],
    )
    op.execute()


if __name__ == '__main__':
    __debug()
