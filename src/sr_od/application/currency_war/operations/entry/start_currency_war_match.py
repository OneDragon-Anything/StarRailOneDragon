import logging
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_log = logging.getLogger(__name__)


class StartCurrencyWarMatch(SrOperation):
    """从货币战争大厅开始/恢复一局,推进到「备战阶段」。

    统一用「点前进按钮直到备战」循环,兼容两条路径的所有中间画面:
    - 有保存局:开始 → 继续进度 → (位面教程叠层)→ 备战。
    - 无保存局:开始 → 进入标准博弈 → 开始对局(职级难度确认)→ 简报(下一步)
      → 投资环境(3 选 1 + 确认)→ 备战。

    前置:已在货币战争大厅(EnterCurrencyWar 之后)。到达备战后返回 STATUS_AT_PREP。

    注:备战阶段的「买牌 + 部署到前台 + 出战」循环(deploy 需拖拽角色图标)受本环境
    OCR-only 限制(vision 看不到图标位置),由上层 app 决定是否继续。
    """

    # 点空白关闭「点击空白处继续」教程叠层(避开中央内容)
    BLANK_CLICK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)

    STATUS_AT_PREP: ClassVar[str] = '到达备战阶段'

    # 前进按钮(按优先级;投资环境/弹窗的「确认」单独处理,避免误点备战内的确认)
    FORWARD_BUTTONS: ClassVar[list[str]] = ['继续进度', '进入标准博弈', '开始对局', '下一步']
    # 推进步数上限(防死循环)
    MAX_ADVANCE_STEPS: ClassVar[int] = 60

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='开始货币战争对局')
        self._advance_steps: int = 0

    def _at_prep(self, screen) -> bool:
        """是否到达备战阶段(用备战独有的「购买经验」按钮判定)。"""
        return self.round_by_ocr(screen, '购买经验').is_success

    @operation_node(name='点开始', is_start_node=True)
    def click_start(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self._at_prep(screen):
            return self.round_success(StartCurrencyWarMatch.STATUS_AT_PREP)
        return self.round_by_ocr_and_click(screen, '开始「货币战争」', retry_wait=1, success_wait=2)

    @node_from(from_name='点开始')
    @operation_node(name='推进到备战阶段', node_max_retry_times=60)
    def advance_to_prep(self) -> OperationRoundResult:
        self.ctx.controller.active_window()  # 防失焦点空(开始对局/继续进度等;同 click_game)
        screen = self.last_screenshot
        if self._at_prep(screen):
            return self.round_success(StartCurrencyWarMatch.STATUS_AT_PREP)

        self._advance_steps += 1
        if self._advance_steps > StartCurrencyWarMatch.MAX_ADVANCE_STEPS:
            return self.round_fail(status='推进到备战阶段超时')

        # 0) 详情弹窗(点卡触发的"可合成列表")→ ESC(同 battle_loop)
        if self.round_by_ocr(screen, '可合成列表').is_success:
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=1.5)

        # 1) 前进按钮(恢复/新局两路的明确推进)
        # 难度确认屏:默认开"当前选择"难度(本号 = A5 紫金);"返回最高职级"按钮在 = 未在最高 → 先点它
        # 切到玩家最高职级(本号 = A8 财富造物主,即目标最高难度),再"开始对局"。
        # (2026-08-03 入口画面建档发现:此前 op 直接点"开始对局" → 一直打 A5 而非目标的最高难度。)
        if self.round_by_ocr(screen, '返回最高职级').is_success:
            self.ctx.controller.active_window()
            self.ctx.controller.click(Point(1392, 965))   # 返回最高职级 按钮(底部,开始对局左侧)
            return self.round_wait(wait=2)
        # ⚠️ 开始对局单独处理:round_by_ocr_and_click 有 0.3s pre_delay,active_window(节点起手)到
        # click 间游戏可能失焦 → 点空(bug #1,手动 click_game 无此间隙所以有效)。
        # 改:OCR 检测 + active_window 紧贴直接 controller.click(无 pre_delay 间隙,同 click_game)。
        if self.round_by_ocr(screen, '开始对局').is_success:
            self.ctx.controller.active_window()
            self.ctx.controller.click(Point(1691, 965))
            return self.round_wait(wait=2)
        for btn in StartCurrencyWarMatch.FORWARD_BUTTONS:
            r = self.round_by_ocr_and_click(screen, btn, success_wait=2)
            if r.is_success:
                return self.round_wait(wait=1)
        # 2) 投资环境:卡底 (900,700) 选中 + 确认 (1082,982)。
        #    bug#1(实测):bot 的 controller.click 紧跟 last_screenshot(移鼠标到角落)→ 判 drag 不落地。
        #    手动 click_game 行(无前置截图)。缓解:active_window + sleep(1.0) 让鼠标彻底 settle 再 click。
        #    坐标 (900,700) = 卡底(画面建档实测);select+confirm 间 sleep(0.5) 让 select 注册。
        if self.round_by_ocr(screen, '投资环境').is_success:
            self.ctx.controller.active_window()
            time.sleep(0.5)
            c1 = self.ctx.controller.click(Point(900, 700))
            log.info('[投资环境] select (900,700) -> %s', c1)
            time.sleep(0.5)
            c2 = self.ctx.controller.click(Point(1082, 982))
            log.info('[投资环境] confirm (1082,982) -> %s', c2)
            return self.round_wait(wait=1.5)
        # 3) 位面教程叠层 → 点空白
        if self.round_by_ocr(screen, '点击空白处继续').is_success:
            self.ctx.controller.click(StartCurrencyWarMatch.BLANK_CLICK.center)
            return self.round_wait(wait=1)

        return self.round_retry(wait=1)
