"""虚构叙事完整挑战:编队填充 → 荒腔走板装配 → 进入故事 → 节点战斗循环 → 结算返回。

前置:``GotoTreasuresLightward(TLMode.PURE_FICTION)`` 到虚构叙事选关 → 点目标关卡
纸鹤进编队屏后调用本 op(本 op 不做选关→编队的跳转)。

交互模型(2026-11-05 实机,取象为文期):
- 编队屏(虚构叙事-编队)两行×4 槽;点槽位 = 展开左栏角色列表 + 选中该行(白框);
  点角色卡 = 加入当前选中行的下一个空槽;**点击已在编队中的角色 = 将其移除**(填充
  搜索时必须跳过已落位目标,否则会把已填角色点掉);
- 行右端「+」= 荒腔走板装配(三选一:触技/笑韵/赋格),每行独立装配;弹窗结构
  (效果列表/装配效果按钮)复用 逐光捡金 屏 PF_CACOPHONY_* 旧 area(弹窗帧实测命中);
- 「进入故事」点击生效后会弹关卡简报横幅(本期战意机制说明,「点击空白处关闭」),
  需点画面下部空白关闭后才进节点画面;
- 节点画面为锁光标大世界:前进 → 点击画面正中心发起攻击(不带 Alt,Alt+点击是
  解锁光标的 UI 操作,不会开战)→ 键盘 V 开自动战斗(V 键实测有效,右上自动图标
  点击不可靠;键盘使用原因:自动战斗开关无可靠点击替代);
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
    GridCell,
    grid_cell_center,
    read_character_grid,
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

#: 编队行槽位 1 点击点(展开列表 + 选中该行;来自 screen_info 虚构叙事-编队 行槽位 area)
_ROW_SLOT_POINTS: dict[int, Point] = {
    1: Point(1315, 770),
    2: Point(1315, 885),
}

#: 装配加号点击点(行右端 +;screen_info 虚构叙事-编队 行装配加号 area 中心)
_EQUIP_POINTS: dict[int, Point] = {
    1: Point(1830, 779),
    2: Point(1830, 886),
}

#: 荒腔走板弹窗:第一个效果条目与装配按钮(逐光捡金屏 PF_CACOPHONY_OPT_1/CONFIRM)
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
        self._effect_picked: bool = False #: 荒腔走板弹窗效果已选中待装配

    @operation_node(name='清空编队', is_start_node=True, node_max_retry_times=8)
    def _clear_teams(self) -> OperationRoundResult:
        """确认在编队屏并逐行清空(点行槽位选中 → 点垃圾桶,两行各一次)。

        ⚠️ PF 的垃圾桶只清「当前选中行」,非全清(2026-11-05 实测:仅点一次时
        行 2 残留成员从列表隐藏,填充找不到目标);与忘却之庭编队屏的全清语义
        不同。清空幂等,对空行无副作用;点完直接 success 转入填充循环。"""
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
        """逐行逐角色填充:列表未展开先点该行槽位 → 滚回顶部 → 逐页找目标 → 点卡即推进。

        推进模型 = 实测「点卡即落入当前行下一空槽」;8 人互不相同(构造期校验),
        故无「点卡误移除」风险;落位复核依赖「进入故事」按钮的可点态兜底。"""
        image = self.last_screenshot
        if self._row_idx >= len(self.teams):
            # 全部落位:收起左栏列表,交装配节点
            self.ctx.controller.click(_COLLAPSE_POINT, press_time=0.15)
            return self.round_success('填充完成', wait=1)

        row_no = self._row_idx + 1
        target = self.teams[self._row_idx][self._char_idx]

        # 列表未展开 → 点该行槽位 1(展开 + 选中该行)。
        # 判据 = 页签无任何识别名:未展开时网格 area 也能裁到格子(编队屏背景/
        # 敌人预览),但识别不出角色名,故不能用 len(cells)==0 判展开态。
        cells = read_character_grid(self.ctx, image)
        if not self._page_sig(cells):
            point = _ROW_SLOT_POINTS[row_no]
            self.ctx.controller.click(point, press_time=0.15)
            self._need_top = True
            return self.round_wait(f'选中行 {row_no} 并展开列表', wait=1.5)

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
            return self.round_wait('滚回列表顶部', wait=1.2)

        # 顶部起逐页向下找目标;点卡即推进(游戏落入当前行下一空槽)。
        # 匹配两级:精确名优先;否则取目标名开头的变体名(命途变体形态,脸库名
        # 带后缀如「姬子•启行」;OCR 分隔符在 •/· 间抖动,故只按前缀判,2026-11-05
        # 实测)。精确名同页存在时必优先,变体兜底不会抢精确命中。
        hit: GridCell | None = None
        variant: GridCell | None = None
        for cell in cells:
            name = cell.guess.char
            if name == target:
                hit = cell
                break
            if name is not None and len(name) > len(target) and name.startswith(target):
                variant = variant or cell
        if hit is None:
            hit = variant
        if hit is not None:
            center = grid_cell_center(self.ctx, hit.row, hit.col)
            if center is None:
                return self.round_fail('区域-角色网格缺失')
            self.ctx.controller.click(center, press_time=0.1)
            log.info('PF填充: 行%d 点 %s', row_no, target)
            self._char_idx += 1
            self._need_top = True  # 下一个角色重新回顶
            if self._char_idx >= 4:
                self._char_idx = 0
                self._row_idx += 1
                return self.round_wait(f'行 {row_no - 1} 填充完成', wait=1)
            return self.round_wait(f'点击 {target}', wait=1)

        sig = self._page_sig(cells)
        log.info('PF填充诊断: 找 %s 行%d stagnation=%d 页签=%s',
                 target, row_no, self._down_stagnation, sig[:80])
        # 到底判定用「已见页签集合」:底部翻页在最后两页弹跳,页签交替出现,
        # 单比上一页永远不相等(2026-11-05 实测);页签复现即视为停滞。
        if sig in self._seen_sigs:
            self._down_stagnation += 1
        else:
            self._down_stagnation = 0
            self._seen_sigs.add(sig)
        if self._down_stagnation >= 2:
            return self.round_fail(f'列表到底未找到 {target}')
        self.ctx.controller.drag_to(_SCROLL_TO, start=_SCROLL_FROM, duration=0.6)
        return self.round_wait('向下翻页', wait=1)

    @staticmethod
    def _page_sig(cells: list[GridCell]) -> str:
        """当前页签名(可见格识别名集合,用于翻页/到顶判定)。"""
        return '|'.join(sorted(
            filter(None, (
                c.guess.char or (c.guess.candidates[0][0] if c.guess.candidates else '')
                for c in cells
            ))
        ))

    @node_from(from_name='填充循环')
    @node_from(from_name='填充循环')
    @operation_node(name='装配循环', node_max_retry_times=24)
    def _equip_loop(self) -> OperationRoundResult:
        """两行各装配第一个荒腔走板效果(三选一,自动化默认取首项触技)。

        选效果与点装配拆成两轮:同轮连点时选中动画未完成,装配点击落空、
        弹窗滞留(2026-11-05 实机踩坑);弹窗滞留时兜底再点装配。"""
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
        """关卡简报横幅(本期战意机制说明)→ 点空白关闭;节点画面 → 进入战斗循环。"""
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
            # 节点待命:前进接近敌人 → 点画面中心开战(不带 Alt) → V 开自动战斗
            # (round_retry 计数:开战点击若落空,下轮仍待命会重试;持续失败超限退出)
            self.ctx.controller.move('w', press_time=2)
            self.ctx.controller.click(Point(960, 540), press_time=0.05)
            self.ctx.controller.btn_tap('v')  # V=自动战斗开关;右上图标点击不可靠,确需键盘
            return self.round_retry('发起战斗并开自动', wait=5)

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
