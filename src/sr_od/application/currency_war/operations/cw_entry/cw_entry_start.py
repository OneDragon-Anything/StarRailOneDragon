
import time
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation import Operation
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult

# 迁移审计 w222(git 历史) 遥测缺口②同源:裸模块 logger 无 handler(框架日志走 'OneDragon',
# propagate=False),本文件日志从未落地 → 改挂框架 logger。
from one_dragon.utils.log_utils import log as _log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.operations.cw_screen.cw_screen_briefing import (
    CwScreenBriefing,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_invest_env import (
    CwScreenInvestEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def try_handle_train_supply_popup(
        op: Operation, screen: MatLike) -> OperationRoundResult | None:
    """列车补给每日弹窗处理(入局链共享助手,app/enter/start 三层挂点)。

    游戏语义(2026-08-31 建档实锤):全屏领取弹窗,「点击领取今日补给」= 点任意处/
    中央徽章即领取,**无 X 关闭钮**——补贴为免费领取无消耗,领取优先;
    领取点击未落地时弹窗仍在,重跑本分支再点同点位(自愈重试)。
    弹窗盖在**大世界之上**,早于 CW 入口首段导航(match2 实锤 2026-08-31:弹窗帧在
    app 首节点即被误判,执行流到不了 start op 内层挂点),故挂点前移到 app
    `_enter_lobby` 首节点;内层 start op 两挂点保留作纵深(识别到弹窗的任何一步
    都接得住)。离线建档声明:点击落地后的画面回落未实机验证(现场保活禁点击)。

    返回 round_retry 而非 round_wait(ADR-0574 交替循环上界闭合):框架只对 RETRY
    计节点 retry 计数,WAIT 不计且把计数归零——WAIT 下「领取点击永不生效」会无限
    空转,且与星琼详情守卫构成「关详情↔领取再开详情」的无界交替循环;RETRY 后两
    分支都计入节点预算,任何组合都有界具名 FAIL。

    op:Operation 基类(SrOperation/SrApplication 共同祖先,round_by_* 同源)。
    未命中=一次全屏 OCR 后按 id_mark area 过滤(crop_first=False,非零开销),
    返回 None;命中返回 round_retry(计入节点预算,等领取动画回落)。
    """
    if not op.round_by_find_area(
            screen, CwEntryStart.TRAIN_SUPPLY_SCREEN, '标识-列车补给',
            crop_first=False).is_success:
        return None
    _log.info('[cw-entry] 列车补给每日弹窗 → 领取今日补贴(点中央徽章)')
    op.round_by_find_and_click_area(
        screen, CwEntryStart.TRAIN_SUPPLY_SCREEN, '按钮-领取补贴',
        success_wait=2, crop_first=False)
    return op.round_retry(status='列车补给领取中', wait=3)


def try_handle_jade_detail_popup(
        op: Operation, screen: MatLike) -> OperationRoundResult | None:
    """星琼(稀有货币)详情弹窗守卫(入局链共享助手,与列车补给助手同构;ADR-0574)。

    事故(2026-09-07 实机):列车补给领取点击落在弹窗中央徽章区,命中其中的星琼
    图标 → 游戏打开货币详情弹窗(「点货币图标→开详情」为游戏全局统一行为,已两次
    活体复现实锤,采样结论见 ADR-0574 §5)。该弹窗模态压暗+模糊背景,入口链全部
    背景锚点(备战
    标识/创业指南/前进按钮)同时失明,推进循环无分支命中空烧 60 步超时。守卫识别
    弹窗 → 点右上角 X 关闭;若弹窗底下压着未领取的列车补给弹窗,下一轮由补给
    分支接住,两守卫接力收敛。

    识别用双锚 AND:「星琼」标题 @0.5 管召回(2 字 @0.5 = 含任一字符即命中,是
    全家族最弱配置,单锚触发误配面过大),「稀有货币」@0.75 管精度(4 字容 1 字
    形变);双 id_mark 全中才算画面精准匹配,守卫触发同判据。同帧 OCR 有缓存,
    第二锚近零增量成本。不用「当前持有」(数字变动);关闭不用 ESC(禁键令),
    点空白关闭未采样,不作默认手段。

    返回 round_retry(非 round_wait):RETRY 计入节点预算,X 点击始终不落地时以
    具名状态有界 FAIL;与列车补给分支(同为 round_retry)两两计预算,「关详情↔
    领取再开详情」交替循环每圈耗 2 次,任何节点预算内必具名退出,上界闭合。

    op:Operation 基类(SrOperation/SrApplication 共同祖先,round_by_* 同源)。
    未命中返回 None(双锚同帧 OCR 缓存下近零开销);命中返回 round_retry(等关闭动画)。
    """
    if not (op.round_by_find_area(
            screen, CwEntryStart.JADE_DETAIL_SCREEN, '标识-星琼标题',
            crop_first=False).is_success
            and op.round_by_find_area(
            screen, CwEntryStart.JADE_DETAIL_SCREEN, '标识-稀有货币',
            crop_first=False).is_success):
        return None
    _log.info('[cw-entry] 星琼详情弹窗 → 点 X 关闭')
    op.round_by_find_and_click_area(
        screen, CwEntryStart.JADE_DETAIL_SCREEN, '按钮-关闭X',
        success_wait=2, crop_first=False)
    return op.round_retry(status='星琼详情弹窗关闭中', wait=1.5)


class CwEntryStart(SrOperation):
    """从货币战争大厅开始/恢复一局,推进到「备战阶段」。

    统一用「点前进按钮直到备战」循环,兼容两条路径的所有中间画面:
    - 有保存局:开始 → 继续进度 → (位面教程叠层)→ 备战。
    - 无保存局:开始 → 进入标准博弈 → 开始对局(职级难度确认)→ 简报(下一步)
      → 投资环境(3 选 1 + 确认)→ 备战。
    - 残留大厅:上局结束「回大厅」的死按钮态 → 点「按钮-关闭」退出到朝露公馆
      世界入口 → F 交互重进新鲜大厅 → 正常开始。

    前置:已在货币战争大厅(CwEntryEnter 之后)。到达备战后返回 STATUS_AT_PREP。

    注:备战阶段的「买牌 + 部署到前台 + 出战」循环由 ``CwScreenPrep 备战单轮`` 负责;装备识别经
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
    # 列车补给每日弹窗(建档 2026-08-31,launch_dead 停机后实锤:全屏弹窗挡死入局链
    # → 推进到备战阶段超时)。建档案:assets/game_data/screen_info/currency_war_train_supply.yml
    TRAIN_SUPPLY_SCREEN: ClassVar[str] = '货币战争-列车补给弹窗'
    # 星琼(稀有货币)详情弹窗(建档 2026-09-07,模态弹窗卡死入局链事故;ADR-0574)。
    # 建档案:assets/game_data/screen_info/currency_war_stellar_jade_detail.yml
    JADE_DETAIL_SCREEN: ClassVar[str] = '货币战争-星琼详情'

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
        """新局确凿信号处弃置上一局残留 match 容器(迁移审计 w289(git 历史)/ADR-0419)。

        难度确认/模式选择/简报三屏只在**无保存局的新局路径**出现(有保存局走
        「继续进度」直达,恢复的是同一物理对局 —— 此时旧容器合法续用,不弃)。
        见 ``cw_strategy.discard_stale_match_container`` docstring。
        """
        if self._stale_discarded:
            return
        from sr_od.application.currency_war.strategies.impl.cw_strategy import (
            discard_stale_match_container,
        )
        self._stale_discarded = discard_stale_match_container(self.ctx, reason)

    def _establish_match_once(self) -> None:
        """新局确凿信号处建立本局 match 容器(W971 §2.1 match 生命周期前置)。

        与 ``_discard_stale_once`` 同址衔接(先弃置残留,再建立本局):
        session 建立时机从 run 首帧 handle_init 前移到进对局——简报观察
        (P3 起 CwScreenBriefing 直写 session)先于 run loop 出现,session 不存在
        = 观察无写目标。已有容器(继续进度恢复)幂等直过。
        """
        from sr_od.application.currency_war.strategies.impl.cw_strategy_manager import (
            establish_new_match,
        )
        establish_new_match(
            self.ctx,
            CurrencyWarConfig(self.ctx.current_instance_idx))

    def _at_prep(self, screen: MatLike) -> bool:
        """是否到达备战阶段(备战独有「购买经验」按钮,screen_info area 判定,替代全屏 ocr)。"""
        return self.round_by_find_area(screen, CwEntryStart.PREP_SCREEN, '备战标识-购买经验', crop_first=False).is_success

    def _handle_train_supply_popup(self, screen: MatLike) -> OperationRoundResult | None:
        """列车补给每日弹窗处理(本 op 两节点挂点,共享助手见模块级函数)。"""
        return try_handle_train_supply_popup(self, screen)

    def _handle_jade_detail_popup(self, screen: MatLike) -> OperationRoundResult | None:
        """星琼详情弹窗守卫(本 op 两节点挂点,共享助手见模块级函数;ADR-0574)。"""
        return try_handle_jade_detail_popup(self, screen)

    @operation_node(name='点开始', is_start_node=True)
    def click_start(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self._at_prep(screen):
            return self.round_success(CwEntryStart.STATUS_AT_PREP)
        popup = self._handle_train_supply_popup(screen)
        if popup is not None:
            return popup
        # 星琼详情弹窗守卫(ADR-0574):模态弹窗盖住一切时开始按钮同样失明。
        popup = self._handle_jade_detail_popup(screen)
        if popup is not None:
            return popup
        # lobby screen_info area(按钮-开始货币战争)替代全屏 ocr(根治 LCS 误匹配)。
        # crop_first=False:全屏 OCR 后按 area.rect 过滤(小 area crop 易漏字,全屏 OCR 稳)。
        return self.round_by_find_and_click_area(
            screen, CwEntryStart.LOBBY_SCREEN, '按钮-开始货币战争',
            retry_wait=1, success_wait=2, crop_first=False,
        )

    @node_from(from_name='点开始')
    @operation_node(name='推进到备战阶段', node_max_retry_times=60)
    def advance_to_prep(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self._at_prep(screen):
            return self.round_success(CwEntryStart.STATUS_AT_PREP)
        # 列车补给每日弹窗优先于一切推进分支(全屏遮罩挡死下面全部前进按钮)。
        popup = self._handle_train_supply_popup(screen)
        if popup is not None:
            return popup
        # 星琼详情弹窗守卫同样先于一切状态分支(ADR-0574:模态压暗+模糊背景下
        # 大厅锚/前进按钮/教程提示全部失明,不接住则走兜底空烧预算;守既有
        # 「列车补给优先于一切推进分支」的排序约定,守卫插在其后)。
        popup = self._handle_jade_detail_popup(screen)
        if popup is not None:
            return popup

        # 残留大厅态(2026-08-27 实机事故:上局结束「回大厅」后大厅 UI 层残留,
        # app 层 _enter_lobby 见大厅锚即跳过 enter op → 死按钮态直达本 op)。
        # 该态「开始」按钮不响应任何点击(死按钮仍 OCR 可见,故判据用大厅锚
        # 「标识-创业指南」而非开始按钮文字),右上角「按钮-关闭」才是真退出:
        # 关闭后露朝露公馆世界入口,F 交互重进的大厅恢复可点。走到本节点仍见
        # 大厅锚 = 「点开始」未产生画面转移 → 残留态;连续多轮锚命中才判定
        # (防转场动画帧误判)。若 BackToNormalWorldPlus 已处理残留,本分支不触发。
        if self.round_by_find_area(
                screen, CwEntryStart.LOBBY_SCREEN, '标识-创业指南',
                crop_first=False).is_success:
            self._lobby_anchor_rounds += 1
            if self._lobby_anchor_rounds < CwEntryStart.LOBBY_RESIDUAL_CONFIRM_ROUNDS:
                return self.round_retry(wait=1)
            if not self._residual_closed:
                _log.info('[cw-entry] 大厅残留态(点开始无转移)→ 点「按钮-关闭」退出到世界入口')
                self._residual_closed = True
                self.round_by_find_and_click_area(
                    screen, CwEntryStart.LOBBY_SCREEN, '按钮-关闭',
                    success_wait=2, crop_first=False)
                return self.round_wait(wait=2)
            if not self._residual_reentered:
                # 关闭点击未落地 / 转场未完成(大厅层还在)→ 继续点关闭
                return self.round_by_find_and_click_area(
                    screen, CwEntryStart.LOBBY_SCREEN, '按钮-关闭',
                    retry_wait=1, crop_first=False)
            # 关闭 + F 重进后的大厅 = 新鲜大厅,开始按钮可点 → 重新点开始。
            # 本节点无 success 出边,必须 round_wait 自环续推(返回 helper 的
            # round_success 会让 op 在模式选择前假成功结束)。
            _log.info('[cw-entry] 残留逃逸后重回大厅 → 重新点「按钮-开始货币战争」')
            self.round_by_find_and_click_area(
                screen, CwEntryStart.LOBBY_SCREEN, '按钮-开始货币战争',
                success_wait=2, crop_first=False)
            return self.round_wait(wait=2)

        # 逃逸中途落在大世界朝露公馆入口(关闭后露出的场景):按 F 重进大厅
        # (与 CwEntryEnter.wait_lobby 的 F 分支同手势;带 lcs 0.7 防任务
        # 追踪文本「请前往…」与「前往参与」的子序列假阳性饿死本分支)。
        if (self._residual_closed and not self._residual_reentered
                and self.round_by_ocr(screen, '货币战争', lcs_percent=0.7).is_success
                and not self.round_by_ocr(screen, '前往参与', lcs_percent=0.7).is_success):
            _log.info('[cw-entry] 残留逃逸:世界入口(朝露公馆)→ 按 F 重进货币战争大厅')
            self._residual_reentered = True
            self.ctx.controller.btn_tap(self.ctx.controller.game_config.key_interact)
            return self.round_wait(wait=2)

        self._advance_steps += 1
        if self._advance_steps > CwEntryStart.MAX_ADVANCE_STEPS:
            return self.round_fail(status='推进到备战阶段超时')

        # 0) 详情弹窗(点卡触发的"可合成列表")→ ESC(同 cw_loop)
        if self.round_by_ocr(screen, '可合成列表').is_success:
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=1.5)

        # 1) 前进按钮(恢复/新局两路的明确推进)
        # 难度确认屏:默认开"当前选择"难度(本号 = A5 紫金);"返回最高职级"按钮在 = 未在最高 → 先点它
        # 切到玩家最高职级(本号 = A8 财富造物主,即目标最高难度),再"开始对局"。
        # (2026-08-03 入口画面建档发现:此前 op 直接点"开始对局" → 一直打 A5 而非目标的最高难度。)
        # 难度确认:用 screen_info area 检测+点击(round_by_find_and_click_area),替代全屏 round_by_ocr。
        # crop_first=False:全屏 OCR 后按 area.rect 过滤(小 area crop 易漏字,全屏 OCR 稳)。
        # 读本局职级(难度确认屏「标识-当前难度职级」→ ctx.cw_selected_difficulty 中转;切最高后 = A8)
        # → loop __init__ copy session → 策略层填 state → effective_hp_threshold D-32(3.5.1 接线)。
        # 迁移审计 w289(git 历史)/ADR-0419:难度确认屏 = 新局确凿信号(不受 cw_selected_difficulty 门限),
        # 见屏即弃置上一局残留 match 容器。
        if self.round_by_find_area(
                screen, CwEntryStart.DIFFICULTY_SCREEN, '标识-当前职级难度效果',
                crop_first=False).is_success:
            self._discard_stale_once('到达难度确认屏=新局开始')
            self._establish_match_once()
        if self.ctx.cw_selected_difficulty is None and self.round_by_find_area(
                screen, CwEntryStart.DIFFICULTY_SCREEN, '标识-当前职级难度效果',
                crop_first=False).is_success:
            from sr_od.application.currency_war.obs.cw_observation import (
                read_selected_difficulty,
            )
            _diff = read_selected_difficulty(self.ctx, screen)
            if _diff:
                self.ctx.cw_selected_difficulty = _diff
                _log.info('[cw-entry] 本局职级: %s', _diff)
        if self.round_by_find_and_click_area(
                screen, CwEntryStart.DIFFICULTY_SCREEN, '按钮-返回最高职级',
                success_wait=2, crop_first=False).is_success:
            return self.round_wait(wait=2)
        if self.round_by_find_and_click_area(
                screen, CwEntryStart.DIFFICULTY_SCREEN, '按钮-开始对局',
                success_wait=2, crop_first=False).is_success:
            return self.round_wait(wait=2)
        # 1a) 有 screen_info 的前进按钮 → area 点击(替代全屏 ocr,根治 LCS 误匹配)。
        #     「开始对局」已在上面难度确认段单独处理(因要先判「返回最高职级」切最高难度)。
        if self.round_by_find_and_click_area(
                screen, CwEntryStart.MODE_SELECT_SCREEN, '按钮-进入标准博弈',
                success_wait=2, crop_first=False).is_success:
            return self.round_wait(wait=1)
        # 模式选择屏可见 = 新局确凿信号(迁移审计 w289(git 历史)/ADR-0419;点击未中也不丢信号)
        if self.round_by_find_area(
                screen, CwEntryStart.MODE_SELECT_SCREEN, '按钮-进入标准博弈',
                crop_first=False).is_success:
            self._discard_stale_once('到达模式选择屏=新局开始')
            self._establish_match_once()
        # 简报屏 → CwScreenBriefing(W971 P3b:观察直写 session,HandleBriefing 已退役;
        # 一屏一 op 调度不变)。
        if self.round_by_find_area(
                screen, CwEntryStart.BRIEFING_SCREEN, '标识-本场对局首领',
                crop_first=False).is_success:
            self._discard_stale_once('到达简报屏=新局开始')
            self._establish_match_once()
            _log.info('[cw-entry] 到达简报屏 → CwScreenBriefing(读词缀/boss 写 session + 下一步)')
            CwScreenBriefing(self.ctx).execute()
            return self.round_wait(wait=2)
        # 1b) 「继续进度」(恢复保存局弹窗,暂无 screen_info)→ ocr;4 字独有,LCS 风险低
        if self.round_by_ocr_and_click(screen, '继续进度', success_wait=2).is_success:
            return self.round_wait(wait=1)
        # 2) 投资环境 3 选 1 → CwScreenInvestEnv(OCR 3 卡名 + decide_event 白名单打分 + 点最优卡底
        #    + 确认)。统一开局与主循环的投资环境处理(原 hardcoded
        #    盲点中卡 + 无策略,已下沉到 handler)。handler 内有 round_by_ocr('投资环境') 入口日志。
        if self.round_by_find_area(screen, '货币战争-投资环境', '标识-投资环境').is_success:
            _log.info('[cw-entry] 到达投资环境 → CwScreenInvestEnv(3 选 1 + 确认)')
            CwScreenInvestEnv(self.ctx).execute()
            return self.round_wait(wait=2)
        # 2b) 投资策略 3 选 1 → CwScreenInvestStrategy(M41 实机修复 2026-08-16:开局流程
        #     「简报→投资环境→投资策略→备战」,本屏在推进窗口出现但无分支 → 干等超时 196s
        #     [日志实锤:OCR 反复读到「请选择投资策略」+三卡名,advance 无命中]。handler
        #     内含打分(STRATEGY_BINDINGS)+确认;此前只在 prep 主循环内被调度。
        if self.round_by_find_area(screen, '货币战争-投资策略', '标识-请选择投资策略').is_success:
            _log.info('[cw-entry] 到达投资策略屏 → CwScreenInvestStrategy(3 选 1 + 确认)')
            from sr_od.application.currency_war.operations.cw_screen.cw_screen_invest_strategy import (
                CwScreenInvestStrategy,
            )
            CwScreenInvestStrategy(self.ctx).execute()
            return self.round_wait(wait=2)
        # 3) 位面教程叠层 → 点空白
        if self.round_by_ocr(screen, '点击空白处继续').is_success:
            self.ctx.controller.click(CwEntryStart.BLANK_CLICK.center)
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
