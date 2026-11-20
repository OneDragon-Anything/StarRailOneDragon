"""货币战争 幕后茶歇交互 op(免战节点奖励交互;迭代 2026-11-20-cw-p0-chain
design §2.1)。

幕后茶歇页两态:首页双卡态(选交互入口卡)与分支选项态(交互内容三选一 +
展开确认)。本 op 按固定规则完成「选卡 → 确认」全链,做完画面已切茶歇
奖励页(判效锚保证),交回主循环(下帧派茶歇奖励 op)。

形态(1+N 无策略段,screen-op.md 通则——处理方式全固定):观察 node =
入口门(标识-茶歇标题)+ 标题词面态判别(首页标题「幕后茶歇」/ 分支标题
「享用茶歇」,text=茶歇为两态共字建档锚故用词面细分)+ 选项一次读
(分支态 = 选项卡带 y 聚合;首页态 = 双卡带 x 聚合)→ report 落
``tea_break_opts``/``tea_break_opts_xy``(读缺跳写)→ obs 即弃零副本
(决策与点击一律按 idx 零参读 game state——白话禁令「画面 op 禁止保存
观察数据」)。首页交互 node = 首页前置段(点回血卡按钮进分支态;出边回
观察重判态,循环有界)。分支选卡 node = 固定规则决策(R1 回血优先 /
R2 负面 HP 词面排除 / R2b 返回类排除 / R3 取首)→ 点选 → 确认钮在场
= 选中生效 → 点确认 until 奖励页标题;确认钮未在场 = 点击未生效脉冲
重试 ≤3(CwScreenPartner CONFIRM_REJECT_MAX 形态);点确认连等封顶
≤3(OPEN_CLICK_MAX 同款——until 点击恒成功锚恒不出现 = 框架
round_wait 无界,节点自设连等封顶,超限 fail 交外环)。

触发链声明:奇遇 → 茶歇由主循环分发自然衔接,本 op 不感知上游;
茶歇 → 奖励页同理由判效锚 + 主循环下帧分发衔接,op 内不跳转。
"""
from __future__ import annotations

import re
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.ocr.ocr_match_result import OcrMatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_screen_report.tea_break import (
    CwScreenTeaBreakObs,
    report_screen_tea_break_obs,
)
from sr_od.application.currency_war.operations.cw_operation_base import (
    CwOperation,
)
from sr_od.context.sr_context import SrContext

#: 状态词(观察 → 两处置 node 的路由键;两处消费逐字同源,常量化防漂移,
#: 机制同 CwScreenPrep.SELECT_HERO_SUBSTATE_STATUS)。
STATUS_BRANCH: str = '分支态选项在场,直达分支选卡'
STATUS_HOME: str = '首页双卡态,直达首页交互'


def pick_option_idx(options: list[str]) -> int | None:
    """茶歇/奇遇选项固定规则(R1/R2/R2b/R3;单一源住本模块,CwScreenAdventureDialog
    卡选择决策复用同函数——两屏规则同文申报于迭代 design §2.1/§2.2)。

    - R1:文本含「回复」∧「生命」的选项优先(摇茶 +20 即时入账实证);
    - R2:含负面 HP 词面的排除——「降低」/「降到」/「失去」或「−N HP」
      「-N HP」形(智慧果咖啡 −10HP、螺丝钉 −4HP 实录);
    - R2b:含「返回」的退出选项排除(点它 = 放弃交互);
    - R3:其余取第一个未排除项;全排除/空 = None(调用方显式失败,禁盲选)。

    只产「点哪个」(idx),不预判数值(判效靠锚)。
    """
    if not options:
        return None
    hp_negative = re.compile(r'[−-]\s*\d+\s*HP')

    def _excluded(text: str) -> bool:
        if '返回' in text:
            return True
        return ('降低' in text or '降到' in text or '失去' in text
                or hp_negative.search(text) is not None)

    candidates = [i for i, t in enumerate(options) if not _excluded(t)]
    if not candidates:
        return None
    for i in candidates:
        if '回复' in options[i] and '生命' in options[i]:
            return i
    return candidates[0]


class CwScreenTeaBreak(CwOperation):
    """幕后茶歇交互:态判别 → 首页选卡(前置段)→ 分支选卡 → 确认 → 切奖励页。
    起点:货币战争-幕后茶歇(首页双卡态或分支选项态);终点:已确认交互,
    画面切货币战争-茶歇奖励(交回主循环)。

    :param ctx: 框架上下文(MCP 反射协议字段)。
    """
    # screen_info area 名(cw_tea_break.yml;坐标单一真相源)。
    A_TITLE: ClassVar[str] = '标识-茶歇标题'
    A_BRANCH_STRIP: ClassVar[str] = '读区-选项卡区'
    A_HOME_STRIP: ClassVar[str] = '读区-首页选项卡带'
    A_CONFIRM: ClassVar[str] = '按钮-确认'
    # 选项卡聚合阈值:分支态纵向列表相邻 item 中心 y 差 ≤ 该值归同卡
    #(卡内选项行距 ~68,卡间隙实测 92-122;取 80 居中——帧证 = 200509
    # 两卡〔478→600 差 122 拆开〕/120053 三卡〔518→610 差 92 拆开〕,
    # 100 会把奇遇两卡塌缩)。
    BRANCH_MERGE_Y: ClassVar[int] = 80
    # 首页双卡横向聚合阈值(卡宽 ~390 间隙;帧证 = 200426 双卡 x 中心 390/1537)。
    HOME_MERGE_X: ClassVar[int] = 400
    # 首页卡上按钮词面集(历史样本在案;无命中回落卡带内 y 最大短词 item)。
    HOME_BUTTON_WORDS: ClassVar[tuple[str, ...]] = ('摇一摇', '聊一聊')
    # 确认钮未在场(点击未生效)脉冲上限(CwScreenPartner CONFIRM_REJECT_MAX
    # 形态;取值 < 节点预算,先于预算耗尽给出精确失败原因)。
    CONFIRM_REJECT_MAX: ClassVar[int] = 3
    # 确认连等封顶(点确认 until 等待在框架里是 round_wait 无界——
    # 点击恒成功锚恒不出现时框架不设限,节点自设连等封顶,同款 =
    # CwScreenTeaBreakReward.OPEN_CLICK_MAX;超限 = 奖励页锚恒不出现
    # 形态,fail 交外环)。
    CONFIRM_WAIT_MAX: ClassVar[int] = 3

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='货币战争-幕后茶歇')
        # 确认未生效脉冲计数(分支选卡 node 自环重入 +1,超限 fail;
        # 实例级,单 op 生命周期)。
        self._confirm_pulses: int = 0
        # 确认连等计数(select_option until 失败分支每轮 +1,超限 fail;
        # 封顶语义见 CONFIRM_WAIT_MAX;实例级,单 op 生命周期)。
        self._confirm_waits: int = 0
        # 确认已发标志(落地复查顶部消费,见 select_option docstring;
        # partner _confirm_pending 同款形态)。
        self._confirm_sent: bool = False
        # 首页点击计数(首页交互 node 每次进入 +1,超限 fail 交外环——
        # 点了进不了分支态 = 按钮未生效形态,禁无界循环)。
        self._home_pulses: int = 0

    def _read_items(self, screen: MatLike, area_name: str) -> list[OcrMatchResult]:
        """读区 OCR 直调(list 形态,item 自带 rect;先例 =
        kernel/cw_obs_core._ocr 同签名,彼处为私有故本地等价实现)。"""
        rect = self._area_rect(area_name)
        if rect is None:
            return []
        return self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=rect, crop_first=False)

    def _area_rect(self, area_name: str, screen_name: str | None = None
                   ) -> Rect | None:
        """档 area rect(缺失 = None,调用方显式处理禁裸坐标)。"""
        si = self.ctx.screen_loader.get_screen(screen_name or '货币战争-幕后茶歇')
        if si is None:
            return None
        area = next((a for a in si.area_list if a.area_name == area_name), None)
        if area is None or area.pc_rect is None:
            return None
        return area.pc_rect

    def _title_kind(self, screen: MatLike) -> str:
        """标题词面态判别:'home'(标题含「幕后」)/'branch'(含「享用」)
        /''(读缺)。标题 text=茶歇为两态共字建档锚,态细分靠词面
        (帧证 = 200426 首页「幕后茶歇」/200509 分支「享用茶歇」)。"""
        title_rect = self._area_rect(CwScreenTeaBreak.A_TITLE)
        if title_rect is None:
            return ''
        texts = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=title_rect, crop_first=False)
        full = ''.join(t.data or '' for t in texts)
        if '享用' in full:
            return 'branch'
        if '幕后' in full:
            return 'home'
        return ''

    def _merge_items(self, items: list[OcrMatchResult], axis: str,
                     threshold: int) -> list[tuple[str, tuple[int, int, int, int]]]:
        """读区 item 聚合为选项单元(选项文本, 点击框)。

        axis='y' = 纵向列表相邻中心 y 差 ≤ threshold 归同卡(分支态);
        axis='x' = 横向双卡中心 x 差 ≤ threshold 归同卡(首页态)。
        单元文本 = 卡内 item 文本依序拼接(R1/R2 词面跨标题与效果行,
        聚合后全文可判);点击框 = 聚合包围盒(分支态,中心落卡体)。
        """
        pts = [it for it in items if (it.data or '').strip()]
        if axis == 'y':
            pts.sort(key=lambda t: t.y + t.h // 2)
        else:
            pts.sort(key=lambda t: t.x + t.w // 2)

        def _center(it: OcrMatchResult, ax: str) -> int:
            return ((it.y + it.h // 2) if ax == 'y' else (it.x + it.w // 2))

        groups: list[list[OcrMatchResult]] = []
        for it in pts:
            if (groups and _center(it, axis) - _center(groups[-1][-1], axis)
                    <= threshold):
                groups[-1].append(it)
            else:
                groups.append([it])
        units: list[tuple[str, tuple[int, int, int, int]]] = []
        for grp in groups:
            text = ''.join(t.data or '' for t in grp)
            x1 = min(t.x for t in grp)
            y1 = min(t.y for t in grp)
            x2 = max(t.x + t.w for t in grp)
            y2 = max(t.y + t.h for t in grp)
            units.append((text, (x1, y1, x2, y2)))
        return units

    def _home_units(self, screen: MatLike
                    ) -> list[tuple[str, tuple[int, int, int, int]]]:
        """首页双卡选项单元:卡聚合(文本 = 卡全文)+ 点击框 = 卡上按钮框
        (首页交互 = 点按钮进分支,卡体点击语义未实测不采用)。
        按钮定位 = 卡 x 带内按钮词面命中 item;无命中回落该带 y 最大短词
        item(≤4 字,按钮词形);全无 = 该卡单元丢弃(不可点击单元不上报,
        防点了没反应)。"""
        items = self._read_items(screen, CwScreenTeaBreak.A_HOME_STRIP)
        cards = self._merge_items(items, axis='x',
                                  threshold=CwScreenTeaBreak.HOME_MERGE_X)
        units: list[tuple[str, tuple[int, int, int, int]]] = []
        for text, _box in cards:
            card_items = [it for it in items
                          if it.x + it.w // 2 >= _box[0]
                          and it.x + it.w // 2 <= _box[2]]
            button = self._locate_home_button(card_items)
            if button is not None:
                b = button
                units.append((text, (b.x, b.y, b.x + b.w, b.y + b.h)))
        return units

    def _locate_home_button(self, card_items: list[OcrMatchResult]
                            ) -> OcrMatchResult | None:
        """首页卡按钮 item:词面集命中优先,回落 y 最大短词 item(≤4 字)。
        None = 卡带无按钮形态(单元不可点击,丢弃申报)。"""
        for it in card_items:
            text = it.data or ''
            if any(w in text for w in CwScreenTeaBreak.HOME_BUTTON_WORDS):
                return it
        words = [it for it in card_items
                 if 0 < len((it.data or '').strip()) <= 4]
        if not words:
            return None
        return max(words, key=lambda t: t.y + t.h // 2)

    def _branch_units(self, screen: MatLike
                      ) -> list[tuple[str, tuple[int, int, int, int]]]:
        """分支态选项单元(y 聚合;点击框 = 选项卡包围盒,中心落卡体——
        非档 area 中心,多选项列表下区域中心会落卡间错卡)。"""
        items = self._read_items(screen, CwScreenTeaBreak.A_BRANCH_STRIP)
        return self._merge_items(items, axis='y',
                                 threshold=CwScreenTeaBreak.BRANCH_MERGE_Y)

    def _report_options(self, units: list[tuple[str, tuple[int, int, int, int]]],
                        screen: MatLike) -> None:
        """上报段:options 经 report 写 game state(读缺跳写闸在 report 内);
        obs 构造即弃零副本(白话禁令)。"""
        obs = CwScreenTeaBreakObs(on_screen=True, options=list(units),
                                  screen=screen)
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_screen_tea_break_obs(gs, obs)

    @node_from(from_name='首页交互')
    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + 标题词面态判别 + 选项一次读 → report → 态路由。

        门 miss = round_fail 交回主循环重判(CwScreenPartner 观察段先例);
        两态读全缺 = 选项读缺 round_fail(禁盲点)。首页交互 node 点完
        经兜底边回本 node 重判态(点完进没进分支态由下一帧观察裁决)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, '货币战争-幕后茶歇',
                CwScreenTeaBreak.A_TITLE).is_success:
            return self.round_fail('非幕后茶歇屏')
        kind = self._title_kind(screen)
        if kind == 'branch':
            units = self._branch_units(screen)
            if not units:
                return self.round_fail('分支态选项读缺(交回主循环重判)')
            self._report_options(units, screen)
            return self.round_success(STATUS_BRANCH, wait=0)
        if kind == 'home':
            units = self._home_units(screen)
            if not units:
                return self.round_fail('首页选项读缺(交回主循环重判)')
            self._report_options(units, screen)
            return self.round_success(STATUS_HOME, wait=0)
        return self.round_fail('茶歇标题词面读缺(态判别失败,交回主循环)')

    @node_from(from_name='观察', status=STATUS_HOME)
    @operation_node(name='首页交互')
    def enter_branch(self) -> OperationRoundResult:
        """首页前置段:固定规则选卡(R1/R2/R2b/R3 复用 pick_option_idx,
        消费 ``tea_break_opts`` 零参读产 idx)→ 点该卡按钮
        (``tea_break_opts_xy[idx]``,首页态上报的点击框 = 按钮框)→
        success 经兜底边回观察重判态(round_wait 会原样重跑本节点,
        永远回不了观察——回判态必须走边);点完进没进分支态由下一帧
        观察裁决,本 node 无陈帧误点面;超限 fail 交外环。"""
        self._home_pulses += 1
        if self._home_pulses > CwScreenTeaBreak.CONFIRM_REJECT_MAX:
            return self.round_fail(
                f'首页选卡连点超限(>{CwScreenTeaBreak.CONFIRM_REJECT_MAX}轮,'
                f'按钮未生效交外环)')
        opts = self._gs_opts()
        idx = pick_option_idx(opts)
        if idx is None:
            return self.round_fail(f'首页选卡无合规项(opts={opts!r})')
        pt = self._gs_point(idx, len(opts))
        log.info('[cw-tea] 首页选卡 idx=%s %s → 点按钮 %s',
                 idx, opts[idx], pt)
        self.ctx.controller.mouse_move(pt)   # 防吞点击(先例 = cw_pick_partner_action)
        self.ctx.controller.click(pt)
        return self.round_success('首页选卡已点,回观察重判态', wait=1.2)

    @node_from(from_name='观察', status=STATUS_BRANCH)
    @operation_node(name='分支选卡', node_max_retry_times=10)
    def select_option(self) -> OperationRoundResult:
        """分支态选卡 → 确认链:零参读决策产 idx → 点选项卡(选中)→
        确认钮在场 = 选中生效 → 点确认 until 奖励页标题;确认钮未在场 =
        点击未生效 → 脉冲重入(round_wait 原样重跑本节点;gs 未变 idx
        恒定,重点同卡幂等),超限 fail 交外环。本 node 无出边——
        success/fail 即访问终态交回主循环(带 status 的 SUCCESS 走自环
        兜底边 = 无限循环,故脉冲重入只用 round_wait 不建自环边)。
        点确认 = area 点击原语 + until 判效锚(奖励页出现 = 交互落地),
        success_wait 显式。until 失败分支 = 确认连等(点击恒成功锚恒
        不出现 = 框架 round_wait 无界面),消费 ``_confirm_waits`` 计数
        封顶 ``CONFIRM_WAIT_MAX``,超限 round_fail 交外环。

        重入顶部落地复查(确认已发 → 奖励页标题在场 = 交互落地 →
        success;CwScreenPartner 落地复查顶部同款):until 验证轮 = 本
        节点函数重跑,不复查会按「点卡」路径重走,在奖励页帧上确认钮
        恒 miss → 脉冲耗尽假失败。"""
        screen = self.last_screenshot
        if self._confirm_sent:
            if self.round_by_find_area(
                    screen, '货币战争-茶歇奖励',
                    '标识-奖励标题').is_success:
                return self.round_success('已确认交互,画面切茶歇奖励'
                                          '(交回主循环)', wait=0.5)
            self._confirm_sent = False   # 确认未落地(罕见),继续脉冲链
        opts = self._gs_opts()
        idx = pick_option_idx(opts)
        if idx is None:
            return self.round_fail(f'分支选卡无合规项(opts={opts!r})')
        pt = self._gs_point(idx, len(opts))
        self.ctx.controller.mouse_move(pt)
        self.ctx.controller.click(pt)
        selected = self.round_by_find_area(
            self.screenshot(), '货币战争-幕后茶歇',
            CwScreenTeaBreak.A_CONFIRM, success_wait=0.8)
        if not selected.is_success:
            self._confirm_pulses += 1
            if self._confirm_pulses > CwScreenTeaBreak.CONFIRM_REJECT_MAX:
                return self.round_fail(
                    f'选项选中未生效(确认钮持续不在场,'
                    f'>{CwScreenTeaBreak.CONFIRM_REJECT_MAX}轮交外环)')
            log.info('[cw-tea] 选中未生效(idx=%s)脉冲 %s/%s',
                     idx, self._confirm_pulses,
                     CwScreenTeaBreak.CONFIRM_REJECT_MAX)
            return self.round_wait('选卡点击未生效,脉冲重试', wait=1.0)
        rr = self.round_by_find_and_click_area(
            self.screenshot(), '货币战争-幕后茶歇', CwScreenTeaBreak.A_CONFIRM,
            until_find_all=[('货币战争-茶歇奖励', '标识-奖励标题')],
            pre_delay=0.3, success_wait=2.0, retry_wait=1.0)
        if rr.is_success:
            return self.round_success('已确认交互,画面切茶歇奖励(交回主循环)',
                                      wait=0.5)
        self._confirm_waits += 1
        if self._confirm_waits > CwScreenTeaBreak.CONFIRM_WAIT_MAX:
            return self.round_fail(
                f'点确认后奖励页锚恒不出现(确认连等超限,'
                f'>{CwScreenTeaBreak.CONFIRM_WAIT_MAX}轮交外环)')
        self._confirm_sent = True
        return rr

    def _gs_opts(self) -> list[str]:
        """game state 选项文本零参读(缺席/空 = 空表,决策产出 None 显式失败;
        禁控制流回退——消费契约 = design §2.8)。"""
        gs = game_state_from_ctx(self.ctx)
        if gs is None:
            return []
        return list(gs.tea_break_opts.value or [])

    def _gs_point(self, idx: int, opts_len: int) -> Point:
        """game state 坐标伴随域按 idx 取点(守卫断言:缺席/越界 = 恒炸
        禁钳位,机制同 CwScreenPartner 守卫③)。"""
        gs = game_state_from_ctx(self.ctx)
        pts = list(gs.tea_break_opts_xy.value or []) if gs is not None else []
        if len(pts) != opts_len or not (0 <= idx < len(pts)):
            raise AssertionError(
                f'[cw-tea] 坐标伴随域失配(禁钳位): idx={idx} '
                f'len(xy)={len(pts)} len(opts)={opts_len}')
        x, y = pts[idx]
        return Point(int(x), int(y))
