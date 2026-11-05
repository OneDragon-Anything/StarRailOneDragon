"""虚构叙事完整挑战:编队填充 → 增益效果装配 → 进入故事 → 节点战斗循环 → 结算返回。

前置:``GotoTreasuresLightward(TLMode.PURE_FICTION)`` 到虚构叙事选关 → 点目标关卡
纸鹤进编队屏后调用本 op(本 op 不做选关→编队的跳转)。

交互模型(当期虚构叙事,游戏内期名「取象为文」):
- 编队屏(虚构叙事-编队)两行×4 槽,每行对应战斗的一个节点;点槽位 = 展开左栏
  角色列表 + 选中该行(白框);点角色卡 = 加入当前选中行的下一个空槽;
  **点击已在编队中的角色 = 将其移除**(填充搜索时必须跳过已落位目标,否则会把
  已填角色点掉);
- 行右端「+」= 增益效果装配——游戏内系统名「荒腔走板」,每行从三个增益效果
  (触技/笑韵/赋格)中选一个装配;弹窗结构(效果列表/装配效果按钮)复用 逐光捡金
  屏 PF_CACOPHONY_* 旧 area(弹窗帧实测命中);
- 「进入故事」点击生效后会弹关卡简报横幅(本期战斗机制说明,「点击空白处关闭」),
  需点画面下部空白关闭后才进节点画面;
- 节点画面为锁光标大世界:前进接近敌人 → ``controller.initiate_attack()`` 发起
  战斗(框架标准开战手法,准星对准敌人后点击画面中心;Alt+点击是解锁光标的
  UI 操作,不会开战);
- 自动战斗不主动开启:游戏设置会继承上一次的自动战斗状态(玩家上次开着,
  本次战斗自动生效)——op 不接管;若未来需要兜底,参考
  ``cw_screen_battle_wait`` 的自愈模式(识别战斗待操作帧连续 5s → 点击画面
  自动战斗开关),待 PF 战斗画面待操作标志建档后补;
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
    read_team_waves,
)
from sr_od.config.character_const import CHARACTER_LIST
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_SELECT_SCREEN: str = '逐光捡金'
_TEAM_SCREEN: str = '虚构叙事-编队'
_NODE_SCREEN: str = '忘却之庭-节点画面'  # 节点画面左栏锚(查看详情)与 FH 同构,复用其 area

#: 角色列表滚动拖动(向下翻页;与忘却之庭编队屏同款列表,一次约移 2 行)
_SCROLL_FROM: Point = Point(300, 760)
_SCROLL_TO: Point = Point(300, 430)

#: 编队行槽位 1 点击点(展开列表 + 选中该行;霍夫圆检测实测槽位圆心——
#: 空槽与已填头像同位同尺寸圆框,中心行 1 (1296,774) / 行 2 (1296,886))
_ROW_SLOT_POINTS: dict[int, Point] = {
    1: Point(1296, 774),
    2: Point(1296, 886),
}

#: 装配加号点击点(行右端 +;screen_info 虚构叙事-编队 行装配加号 area 中心)
_EQUIP_POINTS: dict[int, Point] = {
    1: Point(1830, 779),
    2: Point(1830, 886),
}

#: 增益装配弹窗(游戏内系统名「荒腔走板」):第一个效果条目与装配按钮
#: (逐光捡金屏 PF_CACOPHONY_OPT_1/CONFIRM)
_EFFECT_1_POINT: Point = Point(720, 240)
_EQUIP_CONFIRM_POINT: Point = Point(1690, 985)

#: 关卡简报空白关闭点(横幅下半部无元素区)
_BRIEF_CLOSE_POINT: Point = Point(960, 950)

#: 收起左栏角色列表:右上返回箭头
_COLLAPSE_POINT: Point = Point(1862, 68)


class TlPureFictionChallengeOp(SrOperation):

    STATUS_SUCCESS: ClassVar[str] = '挑战成功'

    def __init__(self, ctx: SrContext, team_names: list[str]):
        """
        Args:
            team_names: 按行(节点)顺序拼接的角色中文名列表,8 人(2 行×4);
                与脸库识别名一致,行 1 = 节点一队伍,行 2 = 节点二队伍。
        """
        SrOperation.__init__(self, ctx, op_name='虚构叙事 挑战')
        if len(team_names) != 8:
            raise ValueError(f'虚构叙事需 8 名角色(2 行×4): {len(team_names)}')
        if len(set(team_names)) != 8:
            raise ValueError(f'虚构叙事 8 名角色须互不相同(重复角色会触发移除语义): {team_names}')
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
        self._last_page_sig: str = ''     #: 上一页签名(回顶判定用)
        self._equip_row: int = 0          #: 当前装配的行(0 基)
        self._effect_picked: bool = False #: 增益装配弹窗效果已选中待装配
        self._need_row_select: bool = True #: 点卡前需先点目标行槽位选中(守卫)

    @operation_node(name='清空编队', is_start_node=True, node_max_retry_times=8)
    def _clear_teams(self) -> OperationRoundResult:
        """确认在编队屏并逐行清空(点行槽位选中 → 点垃圾桶,两行各一次)。

        ⚠️ PF 的垃圾桶只清「当前选中行」,非全清——仅点一次时行 2 残留成员从
        列表隐藏,填充将找不到目标;与忘却之庭编队屏的全清语义不同。清空幂等,对空行无副作用;点完直接 success 转入填充循环。"""
        screen = self.last_screenshot
        if not (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-虚构叙事行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            return self.round_fail('不在虚构叙事编队屏(前置:选关点关卡纸鹤)')
        for row_no in (1, 2):
            self.ctx.controller.click(_ROW_SLOT_POINTS[row_no], press_time=0.15)
            self.ctx.controller.click(Point(1834, 693), press_time=0.15)
        return self.round_success(wait=2)

    @node_from(from_name='清空编队')
    @operation_node(name='填充循环', node_max_retry_times=160)
    def _fill_loop(self) -> OperationRoundResult:
        """逐行逐角色填充:行选中守卫 → 读行成员回验落位 → 回顶 → 逐页找目标 → 点卡。

        落位回验是推进的唯一依据(点卡可能不落位):目标出现在行成员里才推进
        游标,否则重找重点同一目标。名字匹配含置信名与候选表第一名——置信不足
        帧 guess.char 为空,但候选第一名仍是脸库最近似判定,可信。
        行选中守卫:点卡落在「当前选中的行」,清空节点末尾留下的选中行不一定是
        目标行——点卡前必须显式点目标行槽位确保选中。"""
        image = self.last_screenshot
        if self._row_idx >= len(self.teams):
            # 全部落位:收起左栏列表,交装配节点
            self.ctx.controller.click(_COLLAPSE_POINT, press_time=0.15)
            return self.round_success('填充完成', wait=1)

        row_no = self._row_idx + 1
        target = self.teams[self._row_idx][self._char_idx]

        # 行选中守卫:点卡前目标行必须处于选中态(白框),否则角色会落进
        # 上一次选中的行。可靠操作序列 = 收起列表 → 点目标行槽位(一步展开+选中);
        # ⚠️ 列表展开态下直接点另一行槽位的选中切换不可靠(实测行为);
        # 收起态点槽位 = 展开 + 选中一步到位,实测可靠。
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
        waves = read_team_waves(self.ctx, image, screen_name=_TEAM_SCREEN)
        row_members = waves[row_no - 1].members if len(waves) >= row_no else []
        if not waves:
            log.warning('PF填充: read_team_waves 未读到任何行(PF 屏锚/area 失效?)')
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

        # 列表展开态判定已由 行选中守卫 取代:守卫保证点卡前目标行必被选中
        # (列表未展开时点槽位 = 展开+选中,已展开时点槽位 = 仅切换选中行,
        # 两种状态点槽位都安全收敛到「展开 + 目标行选中」)。
        # 识别用 等级文本锚驱动(滚动停驻位置无关;固定网格几何在半格停驻时
        # 行列偏移裁错位——列表滚动任意停驻的常见形态)。
        cells = read_character_cells_by_level(self.ctx, image)

        # 每个角色搜索前先回列表顶部(页签连续两次相同 = 到顶)
        if self._need_top:
            sig = self._page_sig(cells)
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

        # 顶部起逐页向下找目标;点卡后下一轮以落位回验推进(点卡落空自然重试)。
        # 名字匹配:guess.char(置信名)与 candidates[0](候选第一名)都参与,
        # 精确相等优先于前缀变体(命途变体形态如「姬子•启行」,OCR 分隔符在
        # •/· 间抖动)。同帧仅候选命中 = 置信差一口气,同样可信(候选第一名
        # 即脸库最近似判定),点(候选第一名与页签名同源,页签可见即可信);
        exact: AnchorCell | None = None
        fuzzy: AnchorCell | None = None
        for cell in cells:
            names = self._cell_names(cell)
            if target in names:
                exact = cell
                break
            if fuzzy is None and any(
                    len(n) > len(target) and n.startswith(target) for n in names):
                fuzzy = cell
        hit = exact or fuzzy
        if hit is not None:
            self.ctx.controller.click(hit.center, press_time=0.15)
            log.info('PF填充: 行%d 点 %s', row_no, target)
            return self.round_wait(f'点击 {target}', wait=1)

        sig = self._page_sig(cells)
        log.info('PF填充诊断: 找 %s 行%d stagnation=%d 页签=%s',
                 target, row_no, self._down_stagnation, sig[:80])
        # 到底判定用「已见页签集合」+ 弹跳 4 次容错:底部翻页在最后两页弹跳,
        # 且格子识别名跨帧随机缺失(某页经过时目标格识别失败即错过,复读大概率
        # 成功——识别名存在帧间缺失,底部复读可补救),故
        # 底部多弹跳几轮给识别补救机会,2 次就放弃会误杀。
        if sig in self._seen_sigs:
            self._down_stagnation += 1
        else:
            self._down_stagnation = 0
            self._seen_sigs.add(sig)
        if self._down_stagnation >= 4:
            return self.round_fail(f'列表到底未找到 {target}')
        # 翻页后等滚动动画完全停止再识别:拖动 0.6s + 惯性滚动,等太短截到
        # 滚动中间帧会让脸库识别随机失败(静止帧识别稳定,滚动未停时
        # 目标会整页缺名,静止后重读即恢复)。
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
        """行成员里是否已有目标(置信名/候选全表任一命中,前缀变体也算)。"""
        for m in members:
            names: list[str] = []
            if m.char:
                names.append(m.char)
            names.extend(n for n, _ in m.candidates)
            if target in names:
                return True
            if any(len(n) > len(target) and n.startswith(target) for n in names):
                return True
        return False

    @node_from(from_name='填充循环')
    @node_from(from_name='填充循环')
    @operation_node(name='装配循环', node_max_retry_times=24)
    def _equip_loop(self) -> OperationRoundResult:
        """两行各装配第一个增益效果(三选一,自动化默认取第一项「触技」)。

        选效果与点装配拆成两轮:同轮连点时选中动画未完成,装配点击落空、
        弹窗滞留(连点时选中动画未完成,装配点击无效);弹窗滞留时兜底再点装配。"""
        screen = self.last_screenshot
        popup = self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_CACOPHONY_CONFIRM').is_success

        if popup and not self._effect_picked:
            self.ctx.controller.click(_EFFECT_1_POINT, press_time=0.15)
            self._effect_picked = True
            return self.round_wait('选择效果', wait=1)
        if popup:
            self.ctx.controller.click(_EQUIP_CONFIRM_POINT, press_time=0.15)
            self._effect_picked = False
            self._equip_row += 1
            return self.round_wait(f'行 {self._equip_row} 装配效果', wait=2)

        if self._equip_row >= len(self.teams):
            return self.round_success('装配完成')
        row_no = self._equip_row + 1
        point = _EQUIP_POINTS[row_no]
        self.ctx.controller.click(point, press_time=0.15)
        return self.round_wait(f'点行 {row_no} 装配加号', wait=1.5)

    @node_from(from_name='装配循环')
    @operation_node(name='进入故事', node_max_retry_times=10)
    def _start(self) -> OperationRoundResult:
        """点「进入故事」→ 到达验证:关卡简报横幅或节点画面出现。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY').is_success
                or self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success):
            return self.round_success()
        if self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success:
            self.ctx.controller.click(Point(1680, 984), press_time=0.2)
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
        """按画面特征分流:结算 → 收尾;待命 → 开战;其余 → 战斗中等待。

        待命态判据 = 节点画面左栏「查看详情」(PF 与 FH 节点画面同构);
        战斗中左栏被战斗 UI 替换故不误判。节点间自动衔接,无需操作。"""
        screen = self.last_screenshot

        if (self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_SUCCESS_1').is_success
                or self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_SUCCESS_2').is_success):
            return self.round_success(TlPureFictionChallengeOp.STATUS_SUCCESS)
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_FAIL').is_success:
            return self.round_fail('战斗失败')

        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            # 节点待命:前进接近敌人 → 框架标准开战(initiate_attack = 准星对准
            # 敌人后点击画面中心发起攻击,与 start_fight_for_elite 等生产调用一致)。
            # (round_retry 计数:开战点击若落空,下轮仍待命会重试;持续失败超限退出)
            self.ctx.controller.move('w', press_time=2)
            self.ctx.controller.initiate_attack()
            # 自动战斗不主动开启:游戏设置继承上一次的自动战斗状态;兜底待
            # PF 战斗画面待操作标志建档后参考 cw_screen_battle_wait 自愈模式补
            return self.round_retry('发起战斗', wait=5)

        # 战斗中等待用 round_retry 计数(每 5s 一轮;一局 2 节点 6 波正常 ~60 轮内,
        # 360 轮 = 30 分钟兜底退出,防战斗异常卡死时 round_wait 永不超限)
        return self.round_retry('战斗进行中', wait=5)

    @node_from(from_name='节点战斗循环', status=STATUS_SUCCESS)
    @operation_node(name='返回虚构叙事', node_max_retry_times=12)
    def _click_back(self) -> OperationRoundResult:
        """结算画面点「返回虚构叙事」→ 虚构叙事选关。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_TITLE').is_success:
            return self.round_success()
        click = self.round_by_find_and_click_area(
            screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_BACK_BTN', success_wait=2)
        if click.is_success:
            return self.round_wait('返回虚构叙事中', wait=1.5)
        return self.round_retry('未找到返回按钮', wait=1)
