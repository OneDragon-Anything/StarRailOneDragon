
"""货币战争 投资环境 3 选 1 op(从主循环拆出)。

OCR 3 张投资环境卡名 → ``cw_events.decide_event`` 按事件白名单打分 → 点**最优**卡底
+ 确认。替代原"盲点中卡"(无策略)。

环境刷新 = 终结动作(用户裁定 2026-09-14:刷新 = 唯一引入新事实的动作,
须交回外循环重观察;结构语义 = flow/screen_op.md 决策 7 + §8.4 商店/补给
刷新同款——期望态必须在新事实处重建,禁为刷新设计循环内重读机制):
决策返回 ``refresh_slots`` 非空(kernel 侧环境刷新判据经 decide_invest
产出)∧「剩余次数」计数现读授权 → 点刷新圆钮一次(文本锚定偏移)→
动画窗固定等待(机械时序,非判效)→ 零效果缺陷留证 → 本访问即交回
(pending + round_retry 节点重跑,与确认交回同款);新事实的观察与决策归
重入的下一访问(重入裁决后走正常观察链重分类)。计数承载 = 画面计数文本
(屏幕可观察,无 carried 融合载体),取值时机 = 每访问执行闸从当帧现读。
环境屏与策略屏刷新交互不同构(整组重掷单钮单计数 vs 逐卡刷新),落地
形态见 ``_decide_and_act`` 链头注。

卡名按行过滤:标题「投资环境」在顶(y≈98)、卡名在中(y≈392)、描述在下(y≈432)、
「确认」在底(y≈982);取 y≈392 行的短文本(2-6 字)即 3 张卡名,按 center-x 排序
左→右。decide_event 仅用 ``state.board`` 做克制判定,投资环境常在开局/局内 overlay、
board 不可读 → 传空 board stub(dot_punish 为次要细化,白名单主策略不依赖 board)。

卡底 Y + 确认坐标进 screen_info(``currency_war_invest_env``):``区域-卡牌描述行``(给 Y)
+ ``按钮-确认``(给 center),task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,
缺失才用兜底常量。

统一观察架构逐屏迁移(五相位屏;架构设计 §9.1 并存纪律):本类是
CwScreenOpBase 子类,handle 顶部装配点分流(重入裁决**之后**,先例锚 =
cw_screen_encounter.py :241-251 重入裁决 / :252-258 装配点分流,注释原文
「两路径共用(分流前挂,先于五段 lifecycle 的 observe 门)」;总纲契约 6):
cw_game_ports 两端口完整在场 → 五段生命周期新路径;缺省 None = 生产直连
旧路径(原序列,生产行为零变化)。五段形态:observe = 入口门 + 1s 稳定帧
+ 候选读取(实机适配器①封口 = ``_observe_frame``,两路径共享同一读链)+
刷新计数 log 观察通道(遥测保留,与 _decide_and_act 执行闸同源 reader 各司
其职);decide+act 内聚 ``_decide_and_act``(环境刷新终结动作:refresh_slots
非空 → 点刷新交回本访问,链头注 → 选卡时点写 ``active_env``
→ portal 效果登记(active_env 写入同址,invest-env design §2.4,best-effort)
→ 点卡 → 台账变异窗 → 确认 → 台账写点②,两路径共享零转录);reconcile/
on_outcome = 空申报(本屏无独立对账面、无登记件)。本屏 sim 腿 = 不适用
(F11 例外清单:有 sim 事实来源但 sim 端口适配器未建,归 sim 接线批),
等价判据主承重 = 实机在册行为锁 + 写入流对拍(锁面 = sr-od-test
test_cw_obs_arch_phase_screens.py)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_events import decide_event
from sr_od.application.currency_war.kernel.cw_investments import is_known_env
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickInvestParam,
    CwActionRefreshInvestCardsParam,
)
from sr_od.application.currency_war.obs.cw_node_obs import read_invest_refresh_counts
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    emit_overlay_confirm,
    safe_click,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class InvestEnvObservation:
    """投资环境观察 payload(五段之段1产物;实机转录形态)。

    - ``hit``:入口锚「标识-投资环境」命中(误分发防线;miss → observe 段
      round_fail 交回);
    - ``options``:候选卡 ``(名字, center-x)`` 现役读链产物(左→右排序);
    - ``screen``:稳定帧引用(实机识别域载体,不出端口;sim 适配器落位时
      该域 = None 帧语义,F11 例外清单本批不建)。
    """

    hit: bool
    options: list[tuple[str, int]]
    screen: Any = None


class InvestEnvLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口)。

    内部复用现役读链(``CwScreenInvestEnv._observe_frame``:入口门 + 1s
    稳定帧 + 候选读取)——识别机制(OCR/截图)不出端口(§2.1 契约三则);
    重入裁决不进适配器(总纲契约 6)。sim 实现 = T5 后辖域本批不建(F11
    例外清单)。
    """

    def observe(self, op: 'CwScreenInvestEnv') -> InvestEnvObservation:
        return op._observe_payload()


class CwScreenInvestEnv(CwScreenOpBase):
    """投资环境 3 选 1:OCR 卡名 → decide_event 打分 → 点最优卡底 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-投资环境'   # screen_info 画面(currency_war_invest_env.yml)
    # 卡选中点击 Y:screen_info「区域-卡牌描述行」center.y(task#20);常量=screen_info 缺失兜底。
    # 实测(2026-08-04):立绘在卡顶 y≈100-400(点立绘/name y390 开角色详情,非选中);
    # **描述区 y≈450 才选中**(立绘下方);卡底 y700 无效。区别 invest_strategy(描述区 y545)。
    CARD_CLICK_Y: ClassVar[int] = 450   # 兜底;首选 area_center('区域-卡牌描述行')
    # 卡名行 center-y 过滤带(排除标题 y≈98 / 描述 y≈419+ / 确认 y≈982)。
    # 卡名 y 随立绘变(实机见过 375-378 / 392),放宽 [360,410] 容变;原 [378,408] 漏 y<378 的卡名。
    NAME_CY_LO: ClassVar[int] = 360
    NAME_CY_HI: ClassVar[int] = 410
    # 非卡名(同 y 行可能误入或已知 UI 文本)
    _EXCLUDE: ClassVar[set[str]] = {'投资环境', '攻略', '确认', '角色', '装备', '剩余次数：1'}
    # 变异窗宽限(秒):覆盖确认动画 + 节点行刷新重试窗;超时后三票校验恢复落账。
    ENV_GRACE_S: ClassVar[float] = 45.0
    # 确认按钮:screen_info「按钮-确认」center(task#20);常量=兜底。
    CONFIRM: ClassVar[Point] = Point(1082, 982)   # 兜底;首选 area_center('按钮-确认')
    # ---- 环境刷新执行链常量(3.8,design §2.8;执行层时序/几何常量,非策略数值,
    # ADR-0529 先例)----
    # 刷新圆钮 = 「剩余次数」文本中心 + 固定偏移(文本锚定,ADR-0600 §3.4 先例
    # ——单帧证据不足判文本漂移形态,固定 area 不可行;遭遇屏/策略屏同款)。
    # 偏移实测收口(归档帧 sr-od-test/screens/货币战争-投资环境/default.webp
    # 亮像素簇质心:钮心 x≈671、计数文本中心 x≈772,y 同带 ≈983)→ dx ≈ −101。
    # 偏移错 → 刷新未命中(计数不扣、牌不变):零效果只落缺陷台账留证;
    # 重进后计数未扣、预算仍在 → 再次刷新,每圈耗 1 次节点重试预算,
    # 预算耗尽 FAIL bail(能力退化非事故,复测即修)。
    _REFRESH_BTN_DX: ClassVar[int] = -101
    # 刷新后等待(整组重掷动画覆盖;沿策略屏 REFRESH_ANIM_WAIT_S 同值先例)。
    REFRESH_ANIM_WAIT_S: ClassVar[float] = 1.5

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-投资环境')
        # 适配器位缺省装配(先例 = CwScreenPrep/CwScreenEncounter):观察口 =
        # 实机适配器(现役读链封口);动作口 = None = 直连现役确认链(基类
        # 「None = 子类缺省实现自担」)。on_outcome 注册表:本屏无登记件
        # (环境刷新零登记件——计数为画面现读权威,无发射型载体;
        # active_env = 选卡 handler 单次逻辑写入豁免,§3.4 申报豁免面留守
        # _decide_and_act。原 ADR-0600 §2/§4「环境侧刷新执行不启用」规则
        # 已废,现行刷新形态见 _decide_and_act 链头注)。
        self._observation_adapter = InvestEnvLiveObservationAdapter()
        # 确认已发待重入裁决标志(验证废除形态):重入裁决见 handle 顶部。
        self._confirm_pending: bool = False
        # 刷新已发待重入裁决标志(终结动作交回形态):重入裁决见 handle 顶部。
        self._refresh_pending: bool = False
        # 刷新零效果留证证据(批4 比对收口:刷新臂只读不比,读数原样
        # 携带——元组 = (刷前计数, 刷前名集, 刷后计数, 刷后名集);
        # 消费端 = 重入裁决点 ``_reconcile_refresh_no_effect``,消费即清;
        # None = 无待评证据)。
        self._refresh_evidence: tuple[int, list[str],
                                      list, list[tuple[str, int]]] | None = None

    def _read_options(self, screen) -> list[tuple[str, int]]:
        """OCR 3 张卡的 ``(名字, 名字 center-x)``,按卡名行 y 过滤 + 左→右排序。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        opts: list[tuple[str, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (CwScreenInvestEnv.NAME_CY_LO <= cy <= CwScreenInvestEnv.NAME_CY_HI
                    and 2 <= len(text) <= 8 and text not in CwScreenInvestEnv._EXCLUDE):
                opts.append((text, mrl.max.center.x))
        opts.sort(key=lambda t: t[1])
        return opts

    def _observe_frame(self) -> tuple[bool, list[tuple[str, int]], Any]:
        """入口门 + 1s 稳定帧 + 候选读取(实机适配器①封口内容;两路径共用
        读链,总纲 §2.1-1 抽共享方法)。时序口径逐位保留:用户口述口径
        (docs/game/currency_war/research/screen_flow_timing.md「用户口述
        过场动画时序」#3,2026-09-02)「投资环境」标题出现后 1s 内三卡才
        渲染稳定——入口帧可能在稳定期内,立即 OCR 读卡名有读缺/读半字风险
        (空候选 → fallback 盲点屏中)。等 1s 重截稳定帧再读再决策(与简报
        0a0b 修复同型)。Returns: ``(入口锚命中, 候选, 稳定帧)``。"""
        screen = self.last_screenshot
        _hit = self.round_by_find_area(screen, CwScreenInvestEnv.SCREEN_NAME,
                                       '标识-投资环境').is_success
        log.info(f'[cw-env] enter find_area(标识-投资环境)={_hit}')
        if not _hit:
            return False, [], screen
        time.sleep(1.0)
        screen = self.screenshot()
        return True, self._read_options(screen), screen

    def _observe_payload(self) -> InvestEnvObservation:
        """稳定帧观察链 → payload(适配器①与缺省直连共用的装配形态)。"""
        _hit, opts, screen = self._observe_frame()
        return InvestEnvObservation(hit=_hit, options=opts, screen=screen)

    def _log_env_refresh_counts(self, screen) -> None:
        """刷新计数观察写入(ADR-0600 §3.4,G5;零点击零决策——本读数 =
        观察段遥测面,供 V5/V6 实证与 GameState §2.5 写入端;执行闸不消费
        本读数,``_decide_and_act`` 刷新闸独立现读同源 reader)。两路径共用
        (旧 handle 内联位平移)。"""
        _env_counts = read_invest_refresh_counts(self.ctx, screen, 'env')
        log.info(f'[cw-env] 刷新剩余计数读数={_env_counts}(观察通道,V5/V6)')

    def _reconcile_refresh_no_effect(self) -> None:
        """刷新零效果留证对账(观察侧宿主 = 重入裁决点;裁决3 比对收口,
        统一动作工厂批4 自刷新执行臂迁入):携带证据(刷前计数/名集 +
        刷后帧机械重读)在此评「计数未扣 ∧ 名集未变」→ 落缺陷台账
        (零决策零改道);任一侧读缺 = 过渡帧不可判,不猜。判定条件与
        缺陷行内容与迁出前执行臂内联式逐字等价(接收者/局部名归一),
        消费即清(每次刷新恰评一次)。"""
        _ev = self._refresh_evidence
        if _ev is None:
            return
        self._refresh_evidence = None
        _c, _pre_names, _counts2, _opts2 = _ev
        if not (bool(_counts2) and _counts2[0][0] >= _c
                and [n for n, _ in _opts2] == _pre_names):
            return
        try:
            from sr_od.application.currency_war.telemetry import (
                defects as cw_defects,
            )
            cw_defects.record_defect(
                'invest_env', 'refresh_no_effect',
                expected=f'计数<{_c} 或名集变化',
                observed=f'计数={_counts2[0][0]},名集未变',
                verdict='留证-刷新零效果(零决策)',
                reader_source='cw_screen_invest_env',
                note='执行侧判效已拆(判效归一),仅机械留证;'
                     '比对宿主 = 重入观察侧对账点(批4 比对收口)',
                gap_large=False,
                severity=cw_defects.SEVERITY_L2_RECORD)
        except Exception:   # noqa: BLE001  留证不阻塞交回
            pass

    @operation_node(name='投资环境', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        # 重入裁决(观察驱动,验证废除形态):上轮已发确认 → 本轮入口锚不在
        # = overlay 已关(环境选择落地)→ success 交回;锚仍在 = 确认未落地
        # → 清标志重走(计节点预算)。两路径共用(分流前挂,先于五段
        # lifecycle 的 observe 门;总纲契约 6,先例锚 cw_screen_encounter
        # .py :241-251/:252-258)。
        if self._confirm_pending:
            self._confirm_pending = False
            if not self.round_by_find_area(
                    self.last_screenshot, '货币战争-投资环境',
                    '标识-投资环境').is_success:
                return self.round_success('投资环境已确认(重入观察裁决)', wait=2.0)
        # 刷新重入裁决(终结动作交回形态,与确认重入裁决同款结构):上轮
        # 已发刷新 → 本轮入口锚在 = 预期(整组重掷后 overlay 仍在、新牌面
        # 已渲染)→ 穿透到正常观察链(重观察 + 重分类);锚不在 = overlay
        # 意外离开(刷新从不关 overlay,非预期面)→ success 交回外循环按
        # 当前画面重分派(success/retry = 轮次流转语义,非动作成败回执,
        # _overlay_confirm 出口同口径)。两路径共用(分流前挂)。
        if self._refresh_pending:
            # 零效果留证对账(观察侧宿主,批4 比对收口):先于锚分支评,
            # 「锚在(预期穿透)」与「锚不在(意外离开)」两臂同覆盖——与
            # 迁出前「刷新点击当轮即评」的留证覆盖面等价(缺陷的实际触发
            # 形态 = 刷新未生效而 overlay 残留,该形态必经本重入点)。
            self._reconcile_refresh_no_effect()
            self._refresh_pending = False
            if not self.round_by_find_area(
                    self.last_screenshot, '货币战争-投资环境',
                    '标识-投资环境').is_success:
                return self.round_success(
                    '投资环境刷新后画面已离开(重入观察裁决)', wait=2.0)
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run/
        # CwScreenEncounter.handle):两端口完整在场(= 测试 harness 显式装配)
        # → 五段生命周期新路径;缺省 None = 生产直连旧路径(下方原序列,
        # 生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        _hit, opts, screen = self._observe_frame()
        if not _hit:
            return self.round_fail('非投资环境屏')
        self._log_env_refresh_counts(screen)
        return self._decide_and_act(opts, screen)

    def _decide_and_act(self, opts: list[tuple[str, int]],
                        screen: Any = None) -> OperationRoundResult:
        """决策+动作内聚体(五段 decide+act 两路径共享零转录;旧 handle
        :120-201 逐位平移):decide_event/decide_invest 决策(空候选 fallback
        链)→ 环境刷新终结动作(refresh_slots 非空 ∧ 计数授权 → 点刷新后
        本访问即交回,链头注)→ ``active_env`` 选卡时点写(点卡**前**,
        ADR-0598 投资两屏各自实证语义,禁与策略屏重入裁决出口 append 统一)
        → portal 效果登记(active_env 写入同址,best-effort)→ 点最优卡底
        → 台账变异窗 → 确认 → 台账写点②。

        ``screen`` = 观察段稳定帧(刷新计数现读的执行闸输入);缺省 None =
        旧调用形兼容(无帧 = 无授权,刷新链跳过,失败安全)——生产两路径
        均显式传帧。"""

        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _ in opts]
        # 见 od-dev-gameplay-automation 完成判据反馈)。可能是赛季新增 / OCR 误识 / 锁定未命名。
        for _n in names:
            if not is_known_env(_n):
                log.warning(f'[cw-env] 投资环境名不在注册表(数据缺口): {_n!r} → 该项 env_fit 走中性 fallback')
        match = self.ctx.cw_match
        # 写槽 → 零参决策(终态契约 §2.7:写槽以本分支将调用 decide 为前提;
        # 同访问覆盖写,三分语义 details §2.3)。输出 = 单一 CwAction:
        # CwActionRefreshInvestCardsParam(整组刷新建议)/ CwActionPickInvestParam(选卡)互斥单发。
        act = None
        refresh_slots: tuple[int, ...] = ()
        if names:
            if match is not None:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig,
                )
                _gs_env = match.gs
                _gs_env.write_logic(
                    _gs_env.invest_env_opts,
                    list(names),
                    produced_by='CwScreenInvestEnv',
                    sig=ChannelSig(family='logic_action',
                                   actor='CwScreenInvestEnv',
                                   mode='compute'))
                act = match.strategy.decide_invest_env()
            else:
                # 防御:无 match(局外独立跑)——防御空容器直喂(容器签名;
                # 经验分退役后 decide_event 不读 hp/品质惩罚,空容器安全)。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    GameState as _GS_Empty,
                )
                _kpick = decide_event(names, config,
                                      _GS_Empty(schema_version=1))
                act = CwActionPickInvestParam(idx=_kpick.option_idx, reason=_kpick.reason)
        if isinstance(act, CwActionRefreshInvestCardsParam):
            refresh_slots = act.slots
        # ===== 环境刷新 = 终结动作(用户裁定 2026-09-14:刷新 = 唯一引入
        # 新事实的动作,须交回外循环重观察;结构语义 = flow/screen_op.md
        # 决策 7 + §8.4 商店/补给刷新同款——期望态必须在新事实处重建,
        # 禁为刷新设计循环内重读机制)=====
        # 形态:refresh_slots 非空(kernel 侧环境刷新判据经 decide_invest
        # 产出,handler 禁直调 kernel 判据算刷新建议,策略侧锁 13 同款纪律)
        # ∧ 计数现读授权 → 点刷新圆钮一次(环境屏 = 整组重掷:单全局钮 +
        # 单计数,cw_node_obs 归档帧实证,与策略屏逐卡刷新不同构)→ 动画窗
        # 固定等待(机械时序,非判效)→ 零效果缺陷留证 → 本访问即交回
        #(pending + round_retry 节点重跑,确认交回 emit_overlay_confirm
        # 同款机械形态;重入裁决见 handle 顶部,重入后走正常观察链重分类)。
        # 刷新计数授权(计数现读):承载 = 画面「剩余次数」计数文本——屏幕
        # 可观察,每次访问入口重现在当帧,无跨访问承载需求,不引入 session
        # carried 融合载体(screen_op.md §3.1/§8.4 归属判据:非屏幕可观察
        # 字段才归 carried,补给侧 supply_refresh_used 容器计数对照);取值时机 =
        # 每访问执行闸从当访问稳定帧现读,读缺 = 无授权(失败安全)。重进后
        # 再次刷新由既有计数读数自然闸住(每刷一次计数扣一,已耗读 0 → 闸
        # 关),无需跨访问防重入载体;点偏未生效(计数不扣)时重进后
        # 预算仍在 → 再次刷新,每圈耗 1 次节点重试预算,预算耗尽 FAIL bail
        #(有界终止单,emit_overlay_confirm 同款收口)。
        # 零判效(判效归一,统一观察架构画面 op 基类设计 §6.2,环境屏
        # 与策略屏同判):动作只机械执行,「刷没刷成」不判不重试;「点了零
        # 效果」异常面只落缺陷台账留证(零决策零改道,判效权归观察侧
        # reconcile),刷后帧机械重读仅作留证输入,不进决策。
        # 无 match 防御路径显式跳过(局外防御帧零行为增量,策略侧同款);
        # getattr 守卫 = 既有桩 pick(本链落地前的测试替身)无 refresh_slots
        # 字段时按不刷处理,失败安全。
        if refresh_slots and opts and screen is not None:
            _counts = read_invest_refresh_counts(self.ctx, screen, 'env')
            _budget = _counts[0][0] if _counts else 0   # 全局计数至多一条;读缺 = 无授权
            if _budget > 0:
                _c, _tx, _ty = _counts[0]
                # 点钮:「剩余次数」文本中心 + 固定偏移(文本锚定,常量注见
                # _REFRESH_BTN_DX;safe_click 带 bug#1 mouse_move 缓解)。
                safe_click(self,
                           Point(_tx + CwScreenInvestEnv._REFRESH_BTN_DX, _ty),
                           tag='cw-env')
                # 动画窗固定等待(整组重掷动画覆盖;机械执行时序,非判效)。
                time.sleep(CwScreenInvestEnv.REFRESH_ANIM_WAIT_S)
                # 刷后帧机械重读(裁决3 比对收口,统一动作工厂批4:零比对
                # 零判效——读数原样携带进留证证据,「计数未扣 ∧ 名集未变」
                # 的零效果判定迁重入观察侧对账点
                # (``_reconcile_refresh_no_effect``,缺陷台账承接);判效权
                # 归观察侧 reconcile)。
                _after = self.screenshot()
                _counts2 = read_invest_refresh_counts(self.ctx, _after, 'env')
                _opts2 = self._read_options(_after)
                self._refresh_evidence = (
                    _c, [n for n, _ in opts], _counts2, _opts2)
                log.info(f'[cw-env] 环境刷新终结交回:计数 {_c}→'
                         f'{_counts2[0][0] if _counts2 else "读缺"},'
                         f'重入后重观察重分类')
                # 终结交回:pending + round_retry 节点重跑——选卡/确认/
                # active_env 写均不在本访问。
                self._refresh_pending = True
                return self.round_retry(wait=1)
            # 闸全败(建议帧但计数无授权)→ 同访问重调落选卡:策略侧同帧
            # 去重(建议帧首调发建议、紧随重调落选卡)等价旧 CwActionPickEventParam
            # 「idx + refresh_slots 并载、闸败回退选卡」行为,零选卡漂移。
            act = match.strategy.decide_invest_env()
            if isinstance(act, CwActionRefreshInvestCardsParam):   # 防御:策略未实现去重
                act = None
        if isinstance(act, CwActionPickInvestParam) and 0 <= act.idx < len(opts):
            chosen, choose_x = opts[act.idx]
            reason = act.reason
        elif opts:
            chosen, choose_x, reason = opts[0][0], opts[0][1], 'fallback(no-decision)'
        else:
            chosen, choose_x, reason = '?', 960, 'fallback(no-ocr)'
        log.info(f'[cw-env] options={names} chose={chosen!r}@x={choose_x} reason={reason}')
        # 原 bug:chosen 只点不存 → env_fit 全 0.5 → T0 env 绑定静默失效。
        # 终态契约 §B:session 份退役,直写 gs.active_env。
        if match is not None and chosen != '?':
            # GameState 写端(迁移批次二,§3.4.3/§4 投资选择行):已选投资
            # 环境=本屏写入、选完即关整局保留;单次逻辑写入(§3.4 申报豁免:
            # 选择落地无定型帧可核对,后果走观察覆盖)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
            )
            match.gs.write_logic(
                match.gs.active_env, chosen,
                produced_by='CwScreenInvestEnv',
                sig=ChannelSig(family='logic_action',
                               actor='CwScreenInvestEnv', mode='compute'))
            # portal 登记端(invest-env 迭代 design.md §2.4):active_env 写入
            # 同址登记环境效果(source='portal');结构化条目 = 经济环境
            # (cw_effect_inventory.ENV_PORTAL_EFFECTS),其余已知名 UnitBuffRef
            # 占位(效果原文存档,G 组 notes 附 GiftGrant 摘要)。best-effort:
            # 失败不阻塞确认链(effect-domain.md §7.3 登记面纪律,词缀源挂点
            # 同式);幂等在登记体内。本登记零决策消费(经济判据接登记数据
            # 归后续批,design.md §1.3-5)。
            try:
                from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                    register_portal_from_env,
                )
                _portal = register_portal_from_env(match.session, chosen)
                if _portal is not None:
                    log.info(f'[cw-env] portal 效果账本登记: {_portal.name}'
                             f'({_portal.category.value})')
            except Exception as e:   # noqa: BLE001  登记面失败不阻塞
                log.warning(f'[cw-env] portal 效果账本登记失败(不阻塞): {e}')
            # 外部随机授予置闩(观察对账精确吸收的申报消费;申报表 =
            # cw_mismatch_policy.EXTERNAL_BENCH_GRANTS / EXTERNAL_EQUIP_
            # GRANTS;与 CwScreenInvestStrategy 确认挂点同型):投资环境
            # 卡文含「开局时获得…角色/初始简易装备」(概念股族)、「获得
            # 【X】」(契约/邀请/贵族族)等授予效应,随机身份/随机装备不建
            # 逻辑写端(effect-domain §6.3/§6.4),确认后置 pending,下一
            # 干净备战帧 bench/equips 实读对逻辑态纯超集时精确吸收
            #(external_grant_absorbed 行),形状不符照真失配停。置闩收敛
            # kernel 单一源(幂等 + 闩龄上界住 kernel,出处=改动三审
            # 2026-09-18「置闩幂等化」;本挂点零本地逻辑)。best-effort 同登记挂点纪律。
            try:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    latch_external_grants,
                )
                from sr_od.application.currency_war.kernel.cw_investments import (
                    normalize_invest_name,
                )
                latch_external_grants(match.gs, normalize_invest_name(chosen),
                                      actor='CwScreenInvestEnv')
            except Exception as e:   # noqa: BLE001  置闩失败不阻塞确认链
                log.warning(f'[cw-env] 外部授予置闩失败(不阻塞): {e}')
        # 效果原文回流断供为裁定的接受后果,收编归宿 =
        # strategy_offer 画面 payload 域,候其落地批接线。

        # 点最优卡底(task#20:Y 从 screen_info「区域-卡牌描述行」center 读;缺失兜底 CARD_CLICK_Y)。
        # safe_click 带 bug#1 mouse_move 缓解(partner reset 根因同类)。
        _sel = area_center(self.ctx, '区域-卡牌描述行', CwScreenInvestEnv.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else CwScreenInvestEnv.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        safe_click(self, target, tag='cw-env')
        time.sleep(0.7)

        # 台账:确认前开「投资环境变异窗」豁免——环境选择是位面节点序列唯一
        # 变异源(用户口述),确认到节点行重读刷新之间查表与逐帧校验的不一致
        # 是合法变异,三票校验不得落缺陷台账。重读成功后关窗(置 0)。
        try:
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                get_node_ledger,
            )
            _ledger = get_node_ledger(getattr(getattr(self.ctx, 'cw_match', None), 'session', None))
            if _ledger is not None:
                _ledger.env_grace_until = time.monotonic() + CwScreenInvestEnv.ENV_GRACE_S
        except Exception:   # noqa: BLE001  观测面 best-effort
            pass

        # 确认 + 机械交回(验证废除:不读屏判「overlay 关没关」,落地由下一轮
        # 重入入口观察裁决——原「点了就 success」不观察 → bug#1/卡未选中/
        # 隐藏多步 flat-loop 防线由重入裁决 + 预算耗尽 bail 承接)。确认 center
        # 从 screen_info 读,缺失兜底。
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenInvestEnv.SCREEN_NAME) or CwScreenInvestEnv.CONFIRM
        self._confirm_pending = True
        _result = emit_overlay_confirm(self, confirm_point=_confirm, entry_keyword='投资环境',
                                       tag='cw-env')
        # (台账写点②「确认后自截屏重读节点行」已退役——链观察落地批:环境
        #  改型由返回备战后的入口观察链读承接(diff 连续两帧一致才记行),
        #  变异窗开窗保留、关窗迁至备战帧链写端;op 层不再自读屏幕。)
        return _result

    # ---- 五段生命周期(统一观察架构 §5.1,先例 = CwScreenEncounter)----

    def lifecycle_observe(self
                          ) -> tuple[InvestEnvObservation,
                                     OperationRoundResult | None]:
        """段1 observe:入口门 + 实机适配器①稳定帧观察(1s 稳定期 + 候选
        读取)+ 刷新计数 log 观察通道(遥测面,时点 = 旧 handle 读链后逐位;
        执行闸归 _decide_and_act 独立现读,design §2.8)。
        门失败 = round_fail 早退(旧 handle 首闸逐位转录),后续段不执行。
        重入裁决不在本段(总纲契约 6:留守 handle 分流前共享段)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_payload())
        if not obs.hit:
            return obs, self.round_fail('非投资环境屏')
        self._log_env_refresh_counts(obs.screen)
        return obs, None

    def lifecycle_decision_cycle(self, payload: InvestEnvObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作决策循环):decide+act 内聚 ``_decide_and_act``
        (决策/环境刷新终结动作/active_env 选卡时点写/点卡/确认/台账全在
        现役时序,两路径共享零转录);on_outcome = 本屏无登记件(注册表
        缺席 = 零动作,__init__ 申报)。轮次终结出口 = 环境刷新终结交回 +
        确认机械交回(两者的落地/重观察判定均归下一轮重入裁决,验证废除
        形态)。"""
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = self._decide_and_act(payload.options, payload.screen)
        self._lifecycle_mark('on_outcome')
        return rs
