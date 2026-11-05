"""末日幻影完整挑战:编队填充 → 终焉公理装配 → 前往挑战 → 首领简报 →
节点一战斗 → 节点结算 → 节点二战斗 → 最终结算 → 返回选关。

前置:``GotoTreasuresLightward(TLMode.APOCALYPTIC_SHADOW)`` 到末日幻影选关屏;
难度选择不在本 op 内(选关屏点难度标签后进入;当期自动化默认打当前可打
的最高难度即可——3 星通关最高难度视同通关全部前置难度,奖励由「快速通关」
弹窗补发)。

交互模型(末日幻影-编队屏,与虚构叙事编队屏的差异见各节点注释):
- 两行各 4 槽对应两个节点;点槽位语义按列表展开态分三种:
  收起态点槽位 = 展开列表 + 选中该行;展开态点**当前选中行**的已入队槽位 =
  移除该角色;展开态点**非选中行**槽位 = 不改编队、仅收起列表;
- 清空编队不靠垃圾桶(顶部垃圾桶在此屏无清空功能),按上述语义用
  「点已入队槽位」逐个移除,由落位回验(行成员实读)驱动收敛;
- 行 boss 卡内的「坚防守备/阵地转移」等按钮 = **敌方特性条款查看入口**,
  点击仅弹说明、不改变任何装配(实机验证);真正的增益装配入口 = 行右端
  圆形按钮(编入角色后出现)→「终焉公理」弹窗(增益三选一,名称随期轮换,
  按位置选择后点「装配效果」,弹窗自动关闭);敌方特性首条「坚防守备」
  与弹窗内的增益装配是两回事;
- 「通关阵容」按钮弹出推荐阵容弹窗,「一键上阵」+ 确认可整体套用推荐队伍
  (成员不可控,自动化用指定队伍填充时不用此路径);
- 「前往挑战」在校验不通过(编队不满 / 含不可用角色)时点击无反应,不做
  点击侧重试外的兜底——填充与装配节点保证到达时编队合法;
- 「前往挑战」点击生效后先弹**首领简报横幅**(首领特性说明,「点击空白处
  关闭」,不点也会自动消失)→ 节点画面(大世界,左栏锚与忘却之庭节点画面
  同构,复用其 area);
- 两节点**逐个开战**:节点一战斗结束出节点结算页(积分明细 + 「前往节点二」)
  → 节点二简报横幅 → 节点二战斗 → 最终结算页(通关奖励 + 「返回末日幻影」);
- 自动战斗由游戏继承上一次设置(战斗内沙漏图标已验证高亮),op 不接管;
- 战斗以「剩余行动值」计分,行动值耗尽 = 低分结算,不视为失败流程。
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
    read_team_waves,
)
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_SELECT_SCREEN: str = '末日幻影-选关'
_TEAM_SCREEN: str = '末日幻影-编队'
_BANNER_SCREEN: str = '末日幻影-首领简报'
_RESULT_SCREEN: str = '末日幻影-节点结算'
_AXIOM_SCREEN: str = '末日幻影-终焉公理'
_NODE_SCREEN: str = '忘却之庭-节点画面'  # 节点画面左栏锚(查看详情)与 FH 同构,复用其 area

#: 角色列表滚动拖动(向下翻页;与忘却之庭编队屏同款列表,一次约移 2 行)
_SCROLL_FROM: Point = Point(300, 760)
_SCROLL_TO: Point = Point(300, 430)

#: 编队行槽位 1 点击点(展开列表 + 选中该行;放大标定实测填充态头像圆心——
#: 空槽菱形与填充头像同位,行 1 (1025,396) / 行 2 (1025,678))
_ROW_SLOT_POINTS: dict[int, Point] = {
    1: Point(1025, 396),
    2: Point(1025, 678),
}

#: 全部槽位点击点(清空用,行内左→右;圆心距约 82px)
_SLOT_POINTS: list[list[Point]] = [
    [Point(1025, 396), Point(1108, 396), Point(1190, 396), Point(1273, 396)],
    [Point(1025, 678), Point(1108, 678), Point(1190, 678), Point(1273, 678)],
]


class TlApocalypticShadowChallengeOp(SrOperation):

    STATUS_SUCCESS: ClassVar[str] = '挑战成功'

    def __init__(self, ctx: SrContext, team_names: list[str],
                 buff_slots: tuple[int, int] = (1, 1)):
        """
        Args:
            team_names: 按行(节点)顺序拼接的角色中文名列表,8 人(2 行×4);
                与脸库识别名一致,行 1 = 节点一队伍,行 2 = 节点二队伍。
                队伍须避开带警告标记的角色(命途/养成警告,如当期试用角色)——
                此类角色可落位,但「前往挑战」校验不通过(点击无反应)。
            buff_slots: 每行装配的终焉公理增益序号(1 基,每行三选一;
                增益名称随期轮换不可锚定,按卡片位置选择)。
                默认 (1, 1) = 各装第一项(游戏默认项,保守)。
        """
        SrOperation.__init__(self, ctx, op_name='末日幻影 挑战')
        if len(team_names) != 8:
            raise ValueError(f'末日幻影需 8 名角色(2 行×4): {len(team_names)}')
        if len(set(team_names)) != 8:
            raise ValueError(f'末日幻影 8 名角色须互不相同: {team_names}')
        if any(not 1 <= s <= 3 for s in buff_slots):
            raise ValueError(f'buff_slots 须为 1-3: {buff_slots}')
        self.teams: list[list[str]] = [
            team_names[i:i + 4] for i in range(0, 8, 4)
        ]
        for names in self.teams:
            for name in names:
                if next((c for c in CHARACTER_LIST if c.cn == name), None) is None:
                    raise ValueError(f'未知角色名: {name}')
        self._buff_slots: tuple[int, int] = buff_slots
        self._row_idx: int = 0            #: 当前填充的行(0 基)
        self._char_idx: int = 0           #: 当前行填到第几个(0 基)
        self._row_selected: bool = False  #: 目标行已选中(点卡前置守卫)
        self._awaiting_expand: bool = False  #: 已点槽位等待列表展开复验
        self._equip_row2_done: bool = False  #: 行 2 装配未做(装配顺序游标)
        self._equip_phase: str = 'open'   #: 装配子步:open 点圆圈 / select 点卡片 /
                                          # confirm 点装配效果 / closed 等弹窗关
        self._need_top: bool = True       #: 下一步需先滚回列表顶部
        self._down_stagnation: int = 0    #: 向下翻页停滞计数
        self._seen_sigs: set[str] = set() #: 本次搜索已见页签集合(到底判定)
        self._last_page_sig: str = ''     #: 上一页签名(回顶判定用)
        self._clear_slot: tuple[int, int] | None = None  #: 清空游标(行 0 基,槽 0 基)
        # 命名避开框架 Operation._current_node(执行期被赋为当前节点对象,撞名
        # 会让本记录被覆盖,日志打出对象 repr)
        self._brief_node_no: int = 0     #: 简报标题实读的当前节点号(1/2;简报外为 0)
        self._brief_pending: bool = False  #: 简报已确认待进节点画面(首战开战守卫)

    @operation_node(name='进入编队屏', is_start_node=True, node_max_retry_times=10)
    def _enter_team(self) -> OperationRoundResult:
        """从选关屏进编队屏;已在编队屏则直接通过。

        选关屏入口按钮随难度状态变形:未通关难度 = 中央「前往挑战」大按钮;
        已通关难度 = 节点分数卡下的「重新挑战」(两态同屏,前者消失)。
        首领简报横幅可见 = 挑战已发起(编队满员态进编队屏游戏会自动弹简报),
        返回 BANNER_UP 直连简报处理,跳过填充/装配。节点画面(左栏「查看详情」)
        可见 = 挑战进行中,返回 BATTLE_ONGOING 直连战斗循环。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-末日幻影行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            # 难度徽章校验:三节点难度(04,星启模式)布局不同,本 op 未适配
            if self.round_by_find_area(screen, _TEAM_SCREEN, '徽章-难度04').is_success:
                return self.round_fail(
                    '编队屏为难度04(三节点),本 op 仅适配双节点难度(01-03);'
                    '请在选关屏选择 01-03 难度后重试')
            return self.round_success()
        if self.round_by_find_area(screen, _BANNER_SCREEN, '提示-点击空白处关闭').is_success:
            return self.round_success('BANNER_UP')
        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            return self.round_success('BATTLE_ONGOING')
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, '按钮-更换编队确认').is_success:
            self.ctx.controller.click(Point(1165, 672), press_time=0.15)
            return self.round_retry('确认更换编队弹窗', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, '按钮-更换编队').is_success:
            self.ctx.controller.click(Point(1748, 737), press_time=0.15)
            return self.round_retry('选关屏点更换编队', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, '按钮-重新挑战').is_success:
            self.ctx.controller.click(Point(928, 890), press_time=0.15)
            return self.round_retry('选关屏点重新挑战', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, '按钮-前往挑战').is_success:
            self.ctx.controller.click(Point(960, 841), press_time=0.15)
            return self.round_retry('选关屏点前往挑战', wait=2.5)
        return self.round_retry('画面异常(既非选关屏也非编队屏)', wait=1.5)

    @node_from(from_name='进入编队屏')
    @operation_node(name='清空编队', node_max_retry_times=24)
    def _clear_teams(self) -> OperationRoundResult:
        """确认在编队屏并清空两行(点已入队槽位逐个移除)。

        AS 垃圾桶无清空功能;移除语义依赖列表展开态(见模块 docstring),
        本节点按实读行成员驱动,每轮点一个目标槽位,由回验收敛。"""
        screen = self.last_screenshot
        if not (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-末日幻影行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            return self.round_fail('不在末日幻影编队屏(前置:选关点前往挑战)')
        waves = read_team_waves(self.ctx, screen, screen_name=_TEAM_SCREEN)
        if not waves:
            # 锚未读到 = 降级空列表,不等于编队已空(弹窗遮挡锚行会走到这);
            # 误判已空会跳过清队,行满导致填充死循环(实机故障形态)
            return self.round_retry('波次锚未读到(画面遮挡?),重读', wait=1.5)
        list_open = self.round_by_find_area(
            screen, _TEAM_SCREEN, '列表-角色列表页签').is_success

        # 找第一个有成员的槽位(行 0 基、槽 0 基)
        target: tuple[int, int] | None = None
        for r, wave in enumerate(waves):
            for s, member in enumerate(wave.members):
                if member.char or member.candidates:
                    target = (r, s)
                    break
            if target is not None:
                break
        if target is None:
            return self.round_success('编队已空', wait=1)

        r, s = target
        point = _SLOT_POINTS[r][s]
        self.ctx.controller.click(point, press_time=0.15)
        log.info('AS清空: 点行%d槽%d (列表展开=%s)', r + 1, s + 1, list_open)
        # 展开态且该行为选中行 = 移除;否则本点击只做展开/收起,下一轮实读继续
        return self.round_wait(f'点行{r + 1}槽{s + 1}', wait=1.2)

    @node_from(from_name='清空编队')
    @operation_node(name='填充循环', node_max_retry_times=160)
    def _fill_loop(self) -> OperationRoundResult:
        """逐行逐角色填充:行选中守卫 → 读行成员回验落位 → 回顶 → 逐页找目标 → 点卡。

        落位回验是推进的唯一依据。名字匹配含置信名与候选表第一名。
        行选中守卫:收起态点目标行槽位 = 展开+选中,一步到位;跨行切换时
        先点收起箭头(展开态点他行槽位只会收起列表,不切换选中)。"""
        image = self.last_screenshot
        if self._row_idx >= len(self.teams):
            return self.round_success('填充完成', wait=1)

        # 难度布局防御:本 op 的槽位/效果/交互常量按双节点难度(01-03)标定;
        # 最高难度(04,星启模式)为三节点区块布局,锚行数实读不符即显式失败。
        waves_probe = read_team_waves(self.ctx, image, screen_name=_TEAM_SCREEN)
        if not waves_probe:
            return self.round_retry('波次锚未读到(画面遮挡?),重读', wait=1.5)
        if len(waves_probe) != len(self.teams):
            return self.round_fail(
                f'编队屏节点数 {len(waves_probe)} 与队伍数 {len(self.teams)} 不符:'
                f'三节点难度(星启模式)未适配,请在选关屏选择双节点难度(01-03)')

        row_no = self._row_idx + 1
        target = self.teams[self._row_idx][self._char_idx]

        # 列表展开态判定用「角色列表」页签(展开态独有锚;锚文本须与收起态同
        # 区域的「首领攻略」零公共子序列,短锚「等级」与其 LCS 达 0.5 会假命中):
        # 角色卡识别(read_character_cells_by_level)在展开动画帧会整帧空识别,
        # 据此判收起态会误点收起箭头(该坐标在收起态 = 关闭编队屏),流程发散。
        list_open = self.round_by_find_area(
            image, _TEAM_SCREEN, '列表-角色列表页签').is_success

        # 行选中守卫:点卡落在「当前选中的行」,清空节点末尾留下的选中行不一定是
        # 目标行——每行第一个角色填充前必须重新选中目标行。状态机三步:
        # 遗留展开(非本行)→ 点收起箭头;收起态 → 点目标行槽位 1(展开+选中
        # 一步到位);点了槽位后以页签复验展开是否生效,未生效则重试。
        if not self._row_selected:
            if self._awaiting_expand:
                if list_open:
                    self._row_selected = True
                    self._need_top = True
                    self._awaiting_expand = False
                    return self.round_wait(f'行 {row_no} 展开复验通过', wait=0.5)
                self.ctx.controller.click(_ROW_SLOT_POINTS[row_no], press_time=0.15)
                return self.round_wait(f'选中行 {row_no}(重试)', wait=1.5)
            if list_open:
                self.ctx.controller.click(Point(1862, 68), press_time=0.15)
                return self.round_wait('收起遗留展开的列表', wait=1.2)
            self.ctx.controller.click(_ROW_SLOT_POINTS[row_no], press_time=0.15)
            self._awaiting_expand = True
            return self.round_wait(f'选中行 {row_no}(待展开复验)', wait=1.5)

        # 落位回验:目标已在行成员里 → 推进游标
        waves = read_team_waves(self.ctx, image, screen_name=_TEAM_SCREEN)
        if not waves:
            # 锚未读到的降级空列表不可当「成员为空」用(会误判落位失败死循环点卡)
            return self.round_retry('落位回验锚未读到,重读', wait=1.5)
        row_members = waves[row_no - 1].members if len(waves) >= row_no else []
        members_dbg = [f'{m.char or "?"}[{"|".join(n for n, _ in m.candidates)}]'
                       for m in row_members]
        log.info('AS填充回验: 行%d 成员=%s 目标=%s', row_no, members_dbg, target)
        if self._member_has(row_members, target):
            log.info('AS填充: 行%d %s 已落位', row_no, target)
            self._char_idx += 1
            self._need_top = True
            if self._char_idx >= 4:
                self._char_idx = 0
                self._row_idx += 1
                self._row_selected = False
                if self._row_idx < len(self.teams):
                    # 跨行:收起列表,下一轮由行选中守卫重新展开目标行
                    self.ctx.controller.click(Point(1862, 68), press_time=0.15)
                    return self.round_wait(f'行 {row_no} 填充完成,收起列表', wait=1.2)
                return self.round_success('填充完成', wait=1)
            return self.round_wait(f'{target} 已落位', wait=0.8)

        cells = read_character_cells_by_level(self.ctx, image)

        # 每个角色搜索前先回列表顶部(页签连续两次相同 = 到顶);
        # 空识别帧(展开动画/OCR 抖动)不参与判定,视为未就绪重试
        if self._need_top:
            sig = self._page_sig(cells)
            if not sig:
                return self.round_wait('列表识别未就绪,重试', wait=1.5)
            if sig == self._last_page_sig:
                self._need_top = False
                self._down_stagnation = 0
                self._seen_sigs = set()
                self._last_page_sig = ''
                return self.round_wait('已回到列表顶部', wait=0.5)
            self._last_page_sig = sig
            for _ in range(3):
                self.ctx.controller.drag_to(
                    Point(300, 760), start=Point(300, 430), duration=0.4)
            return self.round_wait('滚回列表顶部', wait=3)

        # 顶部起逐页向下找目标;点卡后下一轮以落位回验推进。
        # 名字精确匹配:变体卡(丹恒•腾荒/姬子•启行)是独立角色,前缀/分隔符
        # 模糊匹配会把不同角色误当目标——队伍名必须给列表卡的全名。
        hit: AnchorCell | None = None
        for cell in cells:
            if target in self._cell_names(cell):
                hit = cell
                break
        if hit is not None:
            self.ctx.controller.click(hit.center, press_time=0.15)
            log.info('AS填充: 行%d 点 %s', row_no, target)
            return self.round_wait(f'点击 {target}', wait=1)

        sig = self._page_sig(cells)
        log.info('AS填充诊断: 找 %s 行%d stagnation=%d 页签=%s',
                 target, row_no, self._down_stagnation, sig[:80])
        if sig in self._seen_sigs:
            self._down_stagnation += 1
        else:
            self._down_stagnation = 0
            self._seen_sigs.add(sig)
        if self._down_stagnation >= 4:
            return self.round_fail(f'列表到底未找到 {target}')
        # 翻页后等滚动动画完全停止再识别(滚动未停帧识别名随机缺失)
        self.ctx.controller.drag_to(_SCROLL_TO, start=_SCROLL_FROM, duration=0.6)
        return self.round_wait('向下翻页', wait=3)

    @node_from(from_name='填充循环')
    @operation_node(name='终焉公理装配', node_max_retry_times=16)
    def _equip_loop(self) -> OperationRoundResult:
        """两行各装配指定增益进终焉公理(行右端圆圈 → 弹窗选卡 → 装配效果)。

        行内「敌方特性」条款按钮(坚防守备/阵地转移等)是机制查看入口,点击
        不改变装配(实机验证),真正的增益选择在行右端圆圈弹窗内;增益名称
        随期轮换不可锚定,按位置 ``buff_slots``(1 基)选卡。装配生效后弹窗
        自动关闭回编队屏,以「装配效果」按钮消失为到达证据。"""
        row = 2 if self._equip_row2_done else 1
        screen = self.last_screenshot
        in_axiom = self.round_by_find_area(screen, _AXIOM_SCREEN, '文本-选择增益行').is_success
        in_team = (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-末日幻影行').is_success
                   and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success)

        if self._equip_phase == 'open':
            if in_axiom:
                self._equip_phase = 'select'
                return self.round_wait('公理弹窗已开', wait=0.5)
            if in_team:
                self._click_area_center(_TEAM_SCREEN, f'按钮-公理圆圈{row}')
                self._equip_phase = 'select'
                return self.round_wait(f'打开行{row}公理弹窗', wait=1.5)
            return self.round_retry('不在编队屏也非公理弹窗', wait=1.5)

        if self._equip_phase == 'select':
            if not in_axiom:
                self._equip_phase = 'open'
                return self.round_retry('公理弹窗未开,重开', wait=1.2)
            slot = self._buff_slots[row - 1]
            self._click_area_center(_AXIOM_SCREEN, f'卡片-增益{slot}')
            self._equip_phase = 'confirm'
            return self.round_wait(f'行{row}选增益{slot}', wait=0.8)

        if self._equip_phase == 'confirm':
            click = self.round_by_find_and_click_area(
                screen, _AXIOM_SCREEN, '按钮-装配效果', success_wait=1.2)
            if click.is_success:
                self._equip_phase = 'closed'
                return self.round_wait(f'行{row}装配确认', wait=1.5)
            return self.round_retry('装配效果按钮未命中', wait=1)

        # closed:弹窗应已自动关闭,到达编队屏 = 装配生效
        if in_team:
            if row == 1:
                self._equip_row2_done = True
                self._equip_phase = 'open'
                return self.round_wait('行1装配完成', wait=1)
            return self.round_success('装配完成', wait=1)
        if in_axiom:
            self._equip_phase = 'confirm'
            return self.round_retry('弹窗未关,重按装配', wait=1.2)
        return self.round_retry('画面异常(既非编队屏也非公理弹窗)', wait=1.5)

    def _click_area_center(self, screen_name: str, area_name: str) -> None:
        """按建档 rect 中心点击(纯定位区;坐标单一真相源在 screen_info)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        x1, y1, x2, y2 = area.pc_rect
        self.ctx.controller.click(
            Point((x1 + x2) // 2, (y1 + y2) // 2), press_time=0.15)

    @node_from(from_name='终焉公理装配')
    @operation_node(name='前往挑战', node_max_retry_times=10)
    def _start(self) -> OperationRoundResult:
        """点「前往挑战」→ 到达验证:首领简报横幅或节点画面出现。

        简报横幅不点击会在数秒内自动关闭进入节点画面,两种到达态都认。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _BANNER_SCREEN, '文本-首领特性').is_success:
            return self.round_success()
        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            return self.round_success()
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, '按钮-更换编队确认').is_success:
            # 已挑战过的编队被修改后,点前往挑战先弹「更换编队将清空当前队伍和
            # 对应节点积分」确认(与选关屏的同名弹窗同构,复用其 area)
            self.ctx.controller.click(Point(1165, 672), press_time=0.15)
            return self.round_retry('确认更换编队弹窗', wait=2.5)
        if self.round_by_find_area(screen, _TEAM_SCREEN, '按钮-前往挑战').is_success:
            self.ctx.controller.click(Point(1577, 985), press_time=0.15)
            return self.round_retry('点击前往挑战', wait=2.5)
        return self.round_retry('画面异常(不在编队屏也未见简报)', wait=1.5)

    @node_from(from_name='前往挑战')
    @node_from(from_name='进入编队屏', status='BANNER_UP')
    @operation_node(name='首领简报处理', node_max_retry_times=8)
    def _brief(self) -> OperationRoundResult:
        """首领简报横幅 → 点空白关闭;节点画面 → 进入战斗循环。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _BANNER_SCREEN, '提示-点击空白处关闭').is_success:
            self.ctx.controller.click(Point(960, 950), press_time=0.15)
            return self.round_wait('关闭首领简报', wait=2.5)
        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            return self.round_success()
        return self.round_retry('等待节点画面', wait=2)

    @node_from(from_name='首领简报处理')
    @node_from(from_name='进入编队屏', status='BATTLE_ONGOING')
    @operation_node(name='节点战斗循环', node_max_retry_times=720)
    def _battle_loop(self) -> OperationRoundResult:
        """按画面特征分流:结算 → 逐节点推进;简报 → 关闭;待命 → 开战;其余 → 战斗中等待。

        AS 逐节点开战:节点一结算点「前往节点二」回简报处理,最终结算点
        「返回末日幻影」收尾。节点画面待命判据 = 左栏「查看详情」(战斗中
        左栏被战斗 UI 替换故不误判);开战 = 前进接近敌人后点击画面中心
        (框架标准 initiate_attack 手法)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _RESULT_SCREEN, '标题-挑战结束').is_success:
            if self.round_by_find_area(screen, _RESULT_SCREEN, '按钮-返回末日幻影').is_success:
                self.ctx.controller.click(Point(1240, 949), press_time=0.15)
                return self.round_success(TlApocalypticShadowChallengeOp.STATUS_SUCCESS, wait=2.5)
            if self.round_by_find_area(screen, _RESULT_SCREEN, '按钮-前往节点二').is_success:
                self.ctx.controller.click(Point(1243, 949), press_time=0.15)
                return self.round_retry('前往节点二', wait=3)

        if self.round_by_find_area(screen, _BANNER_SCREEN, '提示-点击空白处关闭').is_success:
            # 简报标题区的「节点一/节点二」位置恒定(说明行数只影响下方区域),
            # 实读记入状态——节点流转的判定锚比结算页按钮文本更稳
            if self.round_by_find_area(screen, _BANNER_SCREEN, '标题-节点二行').is_success:
                self._brief_node_no = 2
                self._brief_pending = True
            elif self.round_by_find_area(screen, _BANNER_SCREEN, '标题-节点一行').is_success:
                self._brief_node_no = 1
                self._brief_pending = True
            self.ctx.controller.click(Point(960, 950), press_time=0.15)
            return self.round_retry(f'关闭首领简报(节点{self._brief_node_no})', wait=2.5)

        if self._brief_pending and self.round_by_find_area(
                screen, _NODE_SCREEN, '面板-查看详情').is_success:
            self._brief_pending = False
            self.ctx.controller.move('w', press_time=2)
            self.ctx.controller.initiate_attack()
            return self.round_retry(f'节点{self._brief_node_no} 发起战斗', wait=5)

        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            self.ctx.controller.move('w', press_time=2)
            self.ctx.controller.initiate_attack()
            return self.round_retry('发起战斗', wait=5)

        # 战斗中等待用 round_retry 计数(每 5s 一轮;单节点战斗正常 ~2 分钟,
        # 720 轮 = 1 小时兜底退出,防战斗异常卡死时 round_wait 永不超限)
        return self.round_retry('战斗进行中', wait=5)

    @node_from(from_name='节点战斗循环', status=STATUS_SUCCESS)
    @operation_node(name='返回选关', node_max_retry_times=12)
    def _click_back(self) -> OperationRoundResult:
        """结算点「返回末日幻影」→ 处理快速通关奖励弹窗 → 选关屏。

        3 星通关最高难度时游戏弹「快速通关」补发前置难度奖励(确认 + 一层
        「点击空白处关闭」提示),两步都处理后到达选关屏。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, '标题-末日幻影行').is_success:
            return self.round_success()
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, 'AFTER_BATTLE_QUICK_PASS_CONFIRM').is_success:
            self.ctx.controller.click(Point(960, 988), press_time=0.15)
            return self.round_wait('领取快速通关奖励', wait=2)
        click = self.round_by_find_and_click_area(
            screen, _RESULT_SCREEN, '按钮-返回末日幻影', success_wait=2)
        if click.is_success:
            return self.round_wait('返回末日幻影中', wait=2)
        return self.round_retry('等待返回按钮', wait=1.5)

    @staticmethod
    def _page_sig(cells: list) -> str:
        """当前页签名(可见格识别名集合,用于翻页/到顶判定)。

        cells 元素为带 .guess 的识别单元(AnchorCell 鸭子兼容)。"""
        return '|'.join(sorted(
            filter(None, (
                c.guess.char or (c.guess.candidates[0][0] if c.guess.candidates else '')
                for c in cells
            ))
        ))

    @staticmethod
    def _cell_names(cell) -> list[str]:
        """格子可判名字列表:置信名在前,候选第一名在后。"""
        names: list[str] = []
        if cell.guess.char:
            names.append(cell.guess.char)
        if cell.guess.candidates:
            names.append(cell.guess.candidates[0][0])
        return names

    @staticmethod
    def _member_has(members, target: str) -> bool:
        """行成员里是否已有目标(置信名/候选全表精确相等;变体卡是独立角色,
        前缀模糊匹配会把丹恒•腾荒误判为丹恒已落位)。"""
        for m in members:
            names: list[str] = []
            if m.char:
                names.append(m.char)
            names.extend(n for n, _ in m.candidates)
            if target in names:
                return True
        return False
