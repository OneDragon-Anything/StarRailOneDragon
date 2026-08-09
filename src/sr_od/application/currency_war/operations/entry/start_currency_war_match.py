# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

import logging
from typing import ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.handlers.handle_briefing import (
    HandleBriefing,
)
from sr_od.application.currency_war.operations.handlers.handle_invest_env import (
    HandleInvestEnv,
)
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

    注:备战阶段的「买牌 + 部署到前台 + 出战」循环由 ``BattlePrepCycle`` 负责;装备识别经
    cw_equip SIFT(D-27/D-28,非 OCR-only —— 旧「视觉大模型 看不到图标位置」判断已破,
    cw_equip 154 模板 SIFT 识别装备区 owned icon)。deploy 需拖拽角色图标(装备拖拽机制 D-18,待 live 验证)。
    """

    # 点空白关闭「点击空白处继续」教程叠层(避开中央内容)
    BLANK_CLICK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)
    # 入口链路 screen_info 画面名;按钮经 round_by_find_and_click_area / area_center 读(替代全屏 ocr)
    DIFFICULTY_SCREEN: ClassVar[str] = '货币战争-难度确认'
    LOBBY_SCREEN: ClassVar[str] = '货币战争-大厅'
    MODE_SELECT_SCREEN: ClassVar[str] = '货币战争-模式选择'
    BRIEFING_SCREEN: ClassVar[str] = '货币战争-简报'
    PREP_SCREEN: ClassVar[str] = '货币战争-备战'

    STATUS_AT_PREP: ClassVar[str] = '到达备战阶段'

    # 推进步数上限(防死循环)
    MAX_ADVANCE_STEPS: ClassVar[int] = 60

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='开始货币战争对局')
        self._advance_steps: int = 0

    def _at_prep(self, screen) -> bool:
        """是否到达备战阶段(备战独有「购买经验」按钮,screen_info area 判定,替代全屏 ocr)。"""
        return self.round_by_find_area(screen, StartCurrencyWarMatch.PREP_SCREEN, '备战标识-购买经验', crop_first=False).is_success

    @operation_node(name='点开始', is_start_node=True)
    def click_start(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self._at_prep(screen):
            return self.round_success(StartCurrencyWarMatch.STATUS_AT_PREP)
        # lobby screen_info area(按钮-开始货币战争)替代全屏 ocr(根治 LCS 误匹配)。
        # crop_first=False:全屏 OCR 后按 area.rect 过滤(小 area crop 易漏字,全屏 OCR 稳)。
        return self.round_by_find_and_click_area(
            screen, StartCurrencyWarMatch.LOBBY_SCREEN, '按钮-开始货币战争',
            retry_wait=1, success_wait=2, crop_first=False,
        )

    @node_from(from_name='点开始')
    @operation_node(name='推进到备战阶段', node_max_retry_times=60)
    def advance_to_prep(self) -> OperationRoundResult:
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
        # 难度确认:用 screen_info area 检测+点击(round_by_find_and_click_area),替代全屏 round_by_ocr。
        # 全屏 ocr 有 LCS 误匹配:「开始对局」与简报 boss 词缀「开局不利」共享「开局」(2/4=0.5=默认阈值)
        # → 简报屏误触发开始对局分支点错(行为测试暴露)。area.rect 限定位置根治。
        # crop_first=False:全屏 OCR 后按 area.rect 过滤(小 area crop 易漏字,全屏 OCR 稳)。
        if self.round_by_find_and_click_area(
                screen, StartCurrencyWarMatch.DIFFICULTY_SCREEN, '按钮-返回最高职级',
                success_wait=2, crop_first=False).is_success:
            return self.round_wait(wait=2)
        if self.round_by_find_and_click_area(
                screen, StartCurrencyWarMatch.DIFFICULTY_SCREEN, '按钮-开始对局',
                success_wait=2, crop_first=False).is_success:
            return self.round_wait(wait=2)
        # 1a) 有 screen_info 的前进按钮 → area 点击(替代全屏 ocr,根治 LCS 误匹配)。
        #     「开始对局」已在上面难度确认段单独处理(因要先判「返回最高职级」切最高难度)。
        if self.round_by_find_and_click_area(
                screen, StartCurrencyWarMatch.MODE_SELECT_SCREEN, '按钮-进入标准博弈',
                success_wait=2, crop_first=False).is_success:
            return self.round_wait(wait=1)
        # 简报屏 → HandleBriefing 独立 op(识别简报 id_mark + 读词缀/boss + 点下一步进投资环境)。
        # 入口大 op 只调度(一屏一 op);词缀/boss 链路在 HandleBriefing 内。
        if self.round_by_find_area(
                screen, StartCurrencyWarMatch.BRIEFING_SCREEN, '标识-本场对局首领',
                crop_first=False).is_success:
            _log.info('[cw-entry] 到达简报屏 → HandleBriefing(读词缀/boss + 下一步)')
            HandleBriefing(self.ctx).execute()
            return self.round_wait(wait=2)
        # 1b) 「继续进度」(恢复保存局弹窗,暂无 screen_info)→ ocr;4 字独有,LCS 风险低
        if self.round_by_ocr_and_click(screen, '继续进度', success_wait=2).is_success:
            return self.round_wait(wait=1)
        # 2) 投资环境 3 选 1 → HandleInvestEnv(OCR 3 卡名 + decide_event 白名单打分 + 点最优卡底
        #    + 确认)。统一开局与主循环的投资环境处理(原 hardcoded
        #    盲点中卡 + 无策略,已下沉到 handler)。handler 内有 round_by_ocr('投资环境') 入口日志。
        if self.round_by_find_area(screen, '货币战争-投资环境', '标识-投资环境').is_success:
            _log.info('[cw-entry] 到达投资环境 → HandleInvestEnv(3 选 1 + 确认)')
            HandleInvestEnv(self.ctx).execute()
            return self.round_wait(wait=2)
        # 3) 位面教程叠层 → 点空白
        if self.round_by_ocr(screen, '点击空白处继续').is_success:
            self.ctx.controller.click(StartCurrencyWarMatch.BLANK_CLICK.center)
            return self.round_wait(wait=1)

        return self.round_retry(wait=1)
