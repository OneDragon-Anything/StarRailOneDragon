
import time
from dataclasses import dataclass
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
from sr_od.application.currency_war.kernel.cw_entry_policy import (
    DifficultyEntryIntent,
    difficulty_entry_intent,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen.cw_screen_briefing import (
    CwScreenBriefing,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_invest_env import (
    CwScreenInvestEnv,
)
from sr_od.application.currency_war.telemetry import state
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


@dataclass(frozen=True)
class EntryPopupGuardSpec:
    """入口链弹窗守卫参数行(一行 = 一个已建档弹窗的处置语义;ADR-0607)。

    识别契约与画面档精准匹配同判据:identify 全锚同帧命中 = is_precise 同义,
    守卫不发明第二套识别语义(ADR-0574 §2.1)。动作只用该弹窗自己建档的控件,
    零画面坐标进代码(坐标单一真相源在 screen_info)。循环语义统一 round_retry
    (具名状态),禁 round_wait——框架对 WAIT 不计 retry 且归零计数(ADR-0574
    §2.2 实证),会无界空转。
    """

    # 画面档 screen_name(单一真相源;字段序即数据表列序,值来自各建档 yml)
    screen_name: str
    # 识别锚 area 名全集,全命中才触发(AND;锚强度分层见各 spec 注释)
    identify_area_names: tuple[str, ...]
    # 点击目标 area 名(领取区或关闭钮,按弹窗动作语义选)
    action_area_name: str
    # 具名状态(失败出口的报警名,哨兵按「执行失败」消费)
    retry_status: str
    # 关闭/领取动画等待秒数
    wait_seconds: float


# 列车补给每日弹窗(建档 assets/game_data/screen_info/currency_war_train_supply.yml):
# 领取类动作,无 X 关闭钮。点击目标 = 底部「文本-领取提示」——中央徽章区点击
# 会命中徽章内下缘的星琼图标,「只开详情不领取」(S1 两次活体复现,S2 实证点
# 提示区 (960,910) 一次领取成功且不开详情,ADR-0574 §5)。中央徽章 rect 以
# 「区域-中央徽章危险区」留档,仅供测试负向断言取坐标,生产代码永不点击。
# 单锚 4 字 @0.75 强锚,天然满足锚强度分层(ADR-0574 §2.1)。
_TRAIN_SUPPLY_GUARD = EntryPopupGuardSpec(
    screen_name='货币战争-列车补给弹窗',
    identify_area_names=('标识-列车补给',),
    action_area_name='文本-领取提示',
    retry_status='列车补给领取中',
    wait_seconds=3,
)

# 星琼(稀有货币)详情弹窗(建档 assets/game_data/screen_info/currency_war_stellar_jade_detail.yml;
# 2026-09-07 实机卡死事故,ADR-0574):模态压暗+模糊背景下入口链全部背景锚失明。
# 双锚 AND:「星琼」@0.5 管召回(2 字 @0.5 = 含任一字符即命中,全家族最弱配置,
# 不可单锚触发)+「稀有货币」@0.75 管精度(4 字容 1 字形变);锚避开动态值
# (「当前持有」数字变动不入锚)。关闭 = 弹窗右上角 X;禁键令,点空白关闭未
# 采样不作默认手段。
_JADE_DETAIL_GUARD = EntryPopupGuardSpec(
    screen_name='货币战争-星琼详情',
    identify_area_names=('标识-星琼标题', '标识-稀有货币'),
    action_area_name='按钮-关闭X',
    retry_status='星琼详情弹窗关闭中',
    wait_seconds=1.5,
)

# 星徽详情弹窗(建档 assets/game_data/screen_info/currency_war_star_badge_detail.yml):
# 全屏遮罩层,关闭 X 在屏幕右上角(非弹窗卡角——与星琼的布局差异 = 同族泛化
# 必须逐弹窗从画面档取坐标的实证)。双锚 AND @0.9 系建档 id_mark 原值(M53),
# 4 字近乎全等误配面趋零;变体帧(类型行非「流派星徽」)上 AND 漏接 = 有界具名
# FAIL,不预建变体分支——星徽详情已知触发场景全在对局内,入口链无已知触发
# 路径,本守卫本质是防御面;对局内分发(阶段一身份)同为建档组合 AND,与
# 本入口同向;OR 接管面只剩 op 内 entry_ok(变体帧兜底重判后的自愈面)。
# 原与「对局内 OR」的有意分叉声明已随分发收编建档组合 AND 失效
# (调和声明见 ADR-0607,历史读法以本注为准)。
_STAR_BADGE_GUARD = EntryPopupGuardSpec(
    screen_name='货币战争-星徽详情',
    identify_area_names=('标识-流派星徽', '标识-套组标题'),
    action_area_name='按钮-关闭',
    retry_status='星徽详情弹窗关闭中',
    wait_seconds=1.5,
)

# 注册表元组顺序 = 挂点执行序:supply 在 detail 族之前(领取优先,ADR-0574
# §2.1 挂点约定;叠层语义:supply 弹窗被 detail 盖住时其背景锚 OCR 不命中,
# 自然让位给 detail,序位无害)。序位知识只住这一处数据;机械防线 = 测试仓
# test_cw_screens_entry.py 的守卫序位锁(元组重排即红)。升级依据 = ADR-0574
# §2.1 预约「第三个同族弹窗出现时升级为注册表」,由星徽落位触发(ADR-0607)。
ENTRY_POPUP_GUARDS: tuple[EntryPopupGuardSpec, ...] = (
    _TRAIN_SUPPLY_GUARD,
    _JADE_DETAIL_GUARD,
    _STAR_BADGE_GUARD,
)


def _handle_entry_popup_spec(
        op: Operation, screen: MatLike,
        spec: EntryPopupGuardSpec) -> OperationRoundResult | None:
    """单条守卫语义:全锚同帧命中才动作(识别不过就是不过,守卫没有盲点击)。

    点击后不原地断言成功——返回具名 round_retry,靠下一轮重观察裁决出口
    (「点了≠成了」在循环层兑现):下一轮弹窗锚不命中 = 关闭/领取落地,交下游
    既有分支;点击始终不落地 = 每圈耗 1 次节点预算,预算耗尽以 spec.retry_status
    具名 FAIL(ADR-0574 §2.2 改形)。

    op:Operation 基类(SrOperation/SrApplication 共同祖先,round_by_* 同源)。
    未命中返回 None;命中返回 round_retry(等关闭/领取动画回落)。
    """
    if not all(op.round_by_find_area(
            screen, spec.screen_name, name,
            crop_first=False).is_success
            for name in spec.identify_area_names):
        return None
    _log.info('[cw-entry] 入口链弹窗 %s 命中 → 点 %s',
              spec.screen_name, spec.action_area_name)
    op.round_by_find_and_click_area(
        screen, spec.screen_name, spec.action_area_name,
        success_wait=2, crop_first=False)
    return op.round_retry(status=spec.retry_status, wait=spec.wait_seconds)


def try_handle_entry_popups(
        op: Operation, screen: MatLike) -> OperationRoundResult | None:
    """入口链弹窗守卫统一入口:按注册表序逐个识别,首个命中者执行动作。

    四挂点(app ``_enter_lobby`` 首节点 / ``cw_entry_enter.wait_lobby`` 纵深 /
    ``cw_entry_start.click_start`` / ``advance_to_prep`` 一切状态分支之前)收敛为
    对本函数的单行调用;新成员 = 画面建档 + 注册表加一行,挂点零改动(ADR-0607;
    升级依据 = ADR-0574 §2.1 预约的第三个同族弹窗)。模态弹窗盖场时背景锚全部
    失明,守卫列于各节点一切既有分支之前(挂点契约,ADR-0574 §2.1)。

    op:Operation 基类(SrOperation/SrApplication 共同祖先,round_by_* 同源)。
    未命中返回 None(同帧 OCR 缓存下逐 spec 近零增量);命中返回具名 round_retry
    (计入节点预算)。
    """
    for spec in ENTRY_POPUP_GUARDS:
        result = _handle_entry_popup_spec(op, screen, spec)
        if result is not None:
            return result
    return None


def try_handle_train_supply_popup(
        op: Operation, screen: MatLike) -> OperationRoundResult | None:
    """列车补给每日弹窗守卫薄包装(委托注册表 supply 项,签名/语义原样)。

    唯一保留理由 = CW 之外的真实消费方 ``back_to_normal_world_plus``(通用
    「返回大世界」op 只管 supply;要不要也接 detail 族弹窗是独立决策,不入守卫
    注册表批,ADR-0607 非目标)。CW 入口链挂点一律走 ``try_handle_entry_popups``;
    jade/badge 无 CW 外消费方,不设薄包装(零调用死代码兼第二测试面,会遮蔽
    序位/收敛行为,ADR-0607)。
    """
    return _handle_entry_popup_spec(op, screen, _TRAIN_SUPPLY_GUARD)


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
    # 弹窗守卫族的画面名已收拢进模块级 ENTRY_POPUP_GUARDS 注册表(单一数据源,
    # 本类不再重复持名)。

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
        """新局确凿信号处弃置上一局残留 match 容器(ADR-0419)。

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

    @operation_node(name='点开始', is_start_node=True)
    def click_start(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self._at_prep(screen):
            return self.round_success(CwEntryStart.STATUS_AT_PREP)
        # 入口链弹窗守卫(注册表统一入口,supply→jade→badge 序位见
        # ENTRY_POPUP_GUARDS;ADR-0574/ADR-0607):模态弹窗盖住一切时
        # 开始按钮同样失明,守卫先于本节点既有分支。
        popup = try_handle_entry_popups(self, screen)
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
        # 入口链弹窗守卫(注册表统一入口;ADR-0574)先于一切状态分支:模态压暗+
        # 模糊背景下大厅锚/前进按钮/教程提示全部失明,不接住则走兜底空烧预算。
        # 守卫轮在弹窗分支返回,不落入下方 _advance_steps 自增(弹窗消化不烧
        # 60 步推进预算,序位约定,ADR-0574 §2.1)。
        popup = try_handle_entry_popups(self, screen)
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

        # 0) 详情弹窗(点卡触发的"可合成列表")→ 点面板外空白关(与外循环 1b 的
        #    CwScreenRoleDetailOverlay 同弹窗同修;旧按 ESC:浮窗已自关时 ESC 落
        #    备战会误弹「中断挑战」bug#2,空白点在弹窗未开时是无害空点)。
        #    ⚠️ 待实机核:该 overlay 帧上「区域-空白关闭」坐标未实机复点
        #    (关闭机制经建档 live 验,见 CwScreenRoleDetailOverlay 模块头)。
        # ⚠️ lcs 默认 0.5 风险提示(清点定级提示级,不改值):「可合成列表」
        # 5 字全屏 OCR 低阈值有子序列误匹配面;此处靠入口链序位保护(本分支
        # 在弹窗守卫/残留大厅分支之后的推进段尾)独占消费。收紧留待触碰本分支。
        if self.round_by_ocr(screen, '可合成列表').is_success:
            _blank = area_center(self.ctx, '区域-空白关闭', CwEntryStart.PREP_SCREEN)
            if _blank is not None:
                self.ctx.controller.click(_blank)
            return self.round_wait(wait=1.5)

        # 1) 前进按钮(恢复/新局两路的明确推进)
        # 难度确认屏:选难度判据单一源 = kernel/cw_entry_policy「恒选最高」缺省纯函数
        # (行为保持契约 = 同输入同动作):「按钮-返回最高职级」在场 = 未在
        # 最高职级 → 先点它切到玩家最高职级(本号 = A8 财富造物主,即目标最高难度),
        # 再「开始对局」;本 op 只做观察(按钮在场 + 职级读数)→ 按意图机械点击。
        # (2026-08-03 入口画面建档发现:此前 op 直接点"开始对局" → 一直打 A5 而非目标的最高难度。)
        # 难度确认:用 screen_info area 检测+点击(round_by_find_and_click_area),替代全屏 round_by_ocr。
        # crop_first=False:全屏 OCR 后按 area.rect 过滤(小 area crop 易漏字,全屏 OCR 稳)。
        # 读本局职级(难度确认屏「标识-当前难度职级」→ ctx.cw_selected_difficulty 中转;切最高后 = A8)
        # → loop __init__ copy session → 策略层填 state → effective_hp_threshold D-32(3.5.1 接线)。
        # ADR-0419:难度确认屏 = 新局确凿信号(不受 cw_selected_difficulty 门限),
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
        _go_highest_seen = self.round_by_find_area(
            screen, CwEntryStart.DIFFICULTY_SCREEN, '按钮-返回最高职级',
            crop_first=False).is_success
        _start_seen = self.round_by_find_area(
            screen, CwEntryStart.DIFFICULTY_SCREEN, '按钮-开始对局',
            crop_first=False).is_success
        _intent = difficulty_entry_intent(
            _go_highest_seen, _start_seen, self.ctx.cw_selected_difficulty)
        if _intent is DifficultyEntryIntent.SWITCH_TO_HIGHEST:
            self.round_by_find_and_click_area(
                screen, CwEntryStart.DIFFICULTY_SCREEN, '按钮-返回最高职级',
                success_wait=2, crop_first=False)
            return self.round_wait(wait=2)
        if _intent is DifficultyEntryIntent.START_MATCH:
            self.round_by_find_and_click_area(
                screen, CwEntryStart.DIFFICULTY_SCREEN, '按钮-开始对局',
                success_wait=2, crop_first=False)
            return self.round_wait(wait=2)
        # 1a) 有 screen_info 的前进按钮 → area 点击(替代全屏 ocr,根治 LCS 误匹配)。
        #     「开始对局」已在上面难度确认段单独处理(因要先判「返回最高职级」切最高难度)。
        if self.round_by_find_and_click_area(
                screen, CwEntryStart.MODE_SELECT_SCREEN, '按钮-进入标准博弈',
                success_wait=2, crop_first=False).is_success:
            return self.round_wait(wait=1)
        # 模式选择屏可见 = 新局确凿信号(ADR-0419;点击未中也不丢信号)
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
            # ADR-0588:简报锚 = 新局路径上第一个遥测生产分支,简报/开局选卡行
            # 落盘前先铸造本局 run(行生而归本局;治冷启动首局零行 + 行盖上局
            # 戳)。难度已在前序难度确认回合读存。幂等;loop 侧同容器认领。
            state.ensure_run_started(self.ctx.cw_match,
                                     self.ctx.cw_selected_difficulty or '')
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
            # ADR-0588:「选卡前铸造」硬保证——即使简报屏因转场被跳过,env 行
            # 落盘前必有归属本局的 open run(幂等,重复调用零成本)。
            state.ensure_run_started(self.ctx.cw_match,
                                     self.ctx.cw_selected_difficulty or '')
            _log.info('[cw-entry] 到达投资环境 → CwScreenInvestEnv(3 选 1 + 确认)')
            CwScreenInvestEnv(self.ctx).execute()
            return self.round_wait(wait=2)
        # 2b) 投资策略 3 选 1 → CwScreenInvestStrategy(M41 实机修复 2026-08-16:开局流程
        #     「简报→投资环境→投资策略→备战」,本屏在推进窗口出现但无分支 → 干等超时 196s
        #     [日志实锤:OCR 反复读到「请选择投资策略」+三卡名,advance 无命中]。handler
        #     内含打分(STRATEGY_BINDINGS)+确认;此前只在 prep 主循环内被调度。
        if self.round_by_find_area(screen, '货币战争-投资策略', '标识-请选择投资策略').is_success:
            _log.info('[cw-entry] 到达投资策略屏 → CwScreenInvestStrategy(3 选 1 + 确认)')
            # ADR-0588:策略 kind 与 env 同一写端漏斗同一时序缺陷,环境屏被
            # 跳过而策略屏直达时的兜底铸造(幂等)。
            state.ensure_run_started(self.ctx.cw_match,
                                     self.ctx.cw_selected_difficulty or '')
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
