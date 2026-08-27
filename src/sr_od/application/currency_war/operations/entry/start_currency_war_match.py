
import time
from typing import ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult

# W222 遥测缺口②同源:裸模块 logger 无 handler(框架日志走 'OneDragon',
# propagate=False),本文件日志从未落地 → 改挂框架 logger。
from one_dragon.utils.log_utils import log as _log
from sr_od.application.currency_war.operations.handlers.handle_briefing import (
    HandleBriefing,
)
from sr_od.application.currency_war.operations.handlers.handle_invest_env import (
    HandleInvestEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class StartCurrencyWarMatch(SrOperation):
    """从货币战争大厅开始/恢复一局,推进到「备战阶段」。

    统一用「点前进按钮直到备战」循环,兼容两条路径的所有中间画面:
    - 有保存局:开始 → 继续进度 → (位面教程叠层)→ 备战。
    - 无保存局:开始 → 进入标准博弈 → 开始对局(职级难度确认)→ 简报(下一步)
      → 投资环境(3 选 1 + 确认)→ 备战。
    - 残留大厅:上局结束「回大厅」的死按钮态 → 点「按钮-关闭」退出到朝露公馆
      世界入口 → F 交互重进新鲜大厅 → 正常开始。

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
    # 残留大厅判定所需的连续锚命中轮数(防点开始后的转场动画帧被误判残留态)
    LOBBY_RESIDUAL_CONFIRM_ROUNDS: ClassVar[int] = 2

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='开始货币战争对局')
        self._advance_steps: int = 0
        # 残留容器弃置去重(同一次入口链只报一次;ADR-0419)
        self._stale_discarded: bool = False
        # 大厅锚(「标识-创业指南」)连续命中轮数(残留大厅判定计数,执行期现读)
        self._lobby_anchor_rounds: int = 0
        # 残留大厅逃逸进度:已点「按钮-关闭」露世界 / 已按 F 重进新鲜大厅
        self._residual_closed: bool = False
        self._residual_reentered: bool = False

    def _discard_stale_once(self, reason: str) -> None:
        """新局确凿信号处弃置上一局残留 match 容器(W289/ADR-0419)。

        难度确认/模式选择/简报三屏只在**无保存局的新局路径**出现(有保存局走
        「继续进度」直达,恢复的是同一物理对局 —— 此时旧容器合法续用,不弃)。
        见 ``cw_strategy.discard_stale_match_container`` docstring。
        """
        if self._stale_discarded:
            return
        from sr_od.application.currency_war.cw_strategy import (
            discard_stale_match_container,
        )
        self._stale_discarded = discard_stale_match_container(self.ctx, reason)

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

        # 残留大厅态(2026-08-27 实机事故:上局结束「回大厅」后大厅 UI 层残留,
        # app 层 _enter_lobby 见大厅锚即跳过 enter op → 死按钮态直达本 op)。
        # 该态「开始」按钮不响应任何点击(死按钮仍 OCR 可见,故判据用大厅锚
        # 「标识-创业指南」而非开始按钮文字),右上角「按钮-关闭」才是真退出:
        # 关闭后露朝露公馆世界入口,F 交互重进的大厅恢复可点。走到本节点仍见
        # 大厅锚 = 「点开始」未产生画面转移 → 残留态;连续多轮锚命中才判定
        # (防转场动画帧误判)。若 BackToNormalWorldPlus 已处理残留,本分支不触发。
        if self.round_by_find_area(
                screen, StartCurrencyWarMatch.LOBBY_SCREEN, '标识-创业指南',
                crop_first=False).is_success:
            self._lobby_anchor_rounds += 1
            if self._lobby_anchor_rounds < StartCurrencyWarMatch.LOBBY_RESIDUAL_CONFIRM_ROUNDS:
                return self.round_retry(wait=1)
            if not self._residual_closed:
                _log.info('[cw-entry] 大厅残留态(点开始无转移)→ 点「按钮-关闭」退出到世界入口')
                self._residual_closed = True
                self.round_by_find_and_click_area(
                    screen, StartCurrencyWarMatch.LOBBY_SCREEN, '按钮-关闭',
                    success_wait=2, crop_first=False)
                return self.round_wait(wait=2)
            if not self._residual_reentered:
                # 关闭点击未落地 / 转场未完成(大厅层还在)→ 继续点关闭
                return self.round_by_find_and_click_area(
                    screen, StartCurrencyWarMatch.LOBBY_SCREEN, '按钮-关闭',
                    retry_wait=1, crop_first=False)
            # 关闭 + F 重进后的大厅 = 新鲜大厅,开始按钮可点 → 重新点开始。
            # 本节点无 success 出边,必须 round_wait 自环续推(返回 helper 的
            # round_success 会让 op 在模式选择前假成功结束)。
            _log.info('[cw-entry] 残留逃逸后重回大厅 → 重新点「按钮-开始货币战争」')
            self.round_by_find_and_click_area(
                screen, StartCurrencyWarMatch.LOBBY_SCREEN, '按钮-开始货币战争',
                success_wait=2, crop_first=False)
            return self.round_wait(wait=2)

        # 逃逸中途落在大世界朝露公馆入口(关闭后露出的场景):按 F 重进大厅
        # (与 EnterCurrencyWar.wait_lobby 的 F 分支同手势;带 lcs 0.7 防任务
        # 追踪文本「请前往…」与「前往参与」的子序列假阳性饿死本分支)。
        if (self._residual_closed and not self._residual_reentered
                and self.round_by_ocr(screen, '货币战争', lcs_percent=0.7).is_success
                and not self.round_by_ocr(screen, '前往参与', lcs_percent=0.7).is_success):
            _log.info('[cw-entry] 残留逃逸:世界入口(朝露公馆)→ 按 F 重进货币战争大厅')
            self._residual_reentered = True
            self.ctx.controller.btn_tap(self.ctx.controller.game_config.key_interact)
            return self.round_wait(wait=2)

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
        # 读本局职级(难度确认屏「标识-当前难度职级」→ ctx.cw_selected_difficulty 中转;切最高后 = A8)
        # → loop __init__ copy session → default_strategy 填 state → effective_hp_threshold D-32(3.5.1 接线)。
        # W289/ADR-0419:难度确认屏 = 新局确凿信号(不受 cw_selected_difficulty 门限),
        # 见屏即弃置上一局残留 match 容器。
        if self.round_by_find_area(
                screen, StartCurrencyWarMatch.DIFFICULTY_SCREEN, '标识-当前职级难度效果',
                crop_first=False).is_success:
            self._discard_stale_once('到达难度确认屏=新局开始')
        if self.ctx.cw_selected_difficulty is None and self.round_by_find_area(
                screen, StartCurrencyWarMatch.DIFFICULTY_SCREEN, '标识-当前职级难度效果',
                crop_first=False).is_success:
            from sr_od.application.currency_war.cw_observation import (
                read_selected_difficulty,
            )
            _diff = read_selected_difficulty(self.ctx, screen)
            if _diff:
                self.ctx.cw_selected_difficulty = _diff
                _log.info('[cw-entry] 本局职级: %s', _diff)
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
        # 模式选择屏可见 = 新局确凿信号(W289/ADR-0419;点击未中也不丢信号)
        if self.round_by_find_area(
                screen, StartCurrencyWarMatch.MODE_SELECT_SCREEN, '按钮-进入标准博弈',
                crop_first=False).is_success:
            self._discard_stale_once('到达模式选择屏=新局开始')
        # 简报屏 → HandleBriefing 独立 op(识别简报 id_mark + 读词缀/boss + 点下一步进投资环境)。
        # 入口大 op 只调度(一屏一 op);词缀/boss 链路在 HandleBriefing 内。
        if self.round_by_find_area(
                screen, StartCurrencyWarMatch.BRIEFING_SCREEN, '标识-本场对局首领',
                crop_first=False).is_success:
            self._discard_stale_once('到达简报屏=新局开始')
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
        # 2b) 投资策略 3 选 1 → HandleInvestStrategy(M41 实机修复 2026-08-16:开局流程
        #     「简报→投资环境→投资策略→备战」,本屏在推进窗口出现但无分支 → 干等超时 196s
        #     [日志实锤:OCR 反复读到「请选择投资策略」+三卡名,advance 无命中]。handler
        #     内含打分(STRATEGY_BINDINGS)+确认;此前只在 prep 主循环内被调度。
        if self.round_by_find_area(screen, '货币战争-投资策略', '标识-请选择投资策略').is_success:
            _log.info('[cw-entry] 到达投资策略屏 → HandleInvestStrategy(3 选 1 + 确认)')
            from sr_od.application.currency_war.operations.handlers.handle_invest_strategy import (
                HandleInvestStrategy,
            )
            HandleInvestStrategy(self.ctx).execute()
            return self.round_wait(wait=2)
        # 3) 位面教程叠层 → 点空白
        if self.round_by_ocr(screen, '点击空白处继续').is_success:
            self.ctx.controller.click(StartCurrencyWarMatch.BLANK_CLICK.center)
            return self.round_wait(wait=1)
        # 3b) 积分奖励页(2026-08-17 M58 停机建档:局末积分达标自动弹的活动奖励;bot 推进
        #     到备战不认识此屏 → 干等超时 196s)。处理:一键领取(有达标奖励)→ 等结算动画 →
        #     点 X 关回大厅,下轮 entry 重新推进(领完弹窗自关或留 X)。
        if self.round_by_find_area(screen, '货币战争-积分奖励', '标识-积分奖励',
                                   crop_first=False).is_success:
            _ok = self.round_by_find_and_click_area(
                screen, '货币战争-积分奖励', '按钮-一键领取', success_wait=1)
            _log.info('[cw-entry] 积分奖励页 → 一键领取(%s)后关闭', '点' if _ok.is_success else '按钮未读到')
            time.sleep(1.5)   # 领取动画
            self.round_by_find_and_click_area(
                self.screenshot(), '货币战争-积分奖励', '按钮-关闭', success_wait=1)
            return self.round_wait(wait=2)

        return self.round_retry(wait=1)
