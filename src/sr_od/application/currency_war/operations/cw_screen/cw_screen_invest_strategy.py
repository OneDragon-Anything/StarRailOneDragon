
"""货币战争 投资策略 3 选 1 op(从主循环拆出)。

OCR 3 张投资策略卡名 → 经 ``match.strategy.decide_invest``(委托 ``cw_events.decide_event``
打分)→ 点**最优**卡 + 确认。替代原"盲点中卡"(无策略)。

逐卡刷新 = 终结动作(用户裁定 2026-09-14,照投资环境 T-206 形态):
``decide_event`` 帧级触发(零阈值结构判据:全精确分类 ∧ 无 S1/S2 ∧ max_N≠1,
推导见 ADR-0600 §3.2 + math_proofs P81)→ 返回 ``refresh_slots`` 非空 ∧
逐槽计数现读授权(读缺 = 无授权)→ 文本锚定点刷新圆钮一次 → 固定等待
(机械时序,非判效)→ 本访问即交回(pending + round_retry,与确认交回同款);
新事实的观察与决策归重入的下一访问(重入裁决后走正常观察链重分类重决策)。
投资策略屏刷新是**逐卡刷新**(每卡独立按钮、独立计数,归档帧对实证)。
验效双通道已拆除(用户裁定 2026-09-10:动作 op 只管机械执行禁止验效,出处 =
验证违规清查报告 H2),2026-09-14 裁定进一步收敛为零比对:访问内刷后
不重读不比对不重决策,「刷没刷成」不判;读缺守卫 = 逐槽计数现读的
读缺按无授予处理(失败安全)。已发射槽集挂
``exec_state_of(session)``
(局容器级),复位 = visit 起点单点(实例首帧入口锚验通过后清空)。

卡名按行过滤(2026-08-04 snap 实测):标题「请选择投资策略」顶(y≈98)、卡名中(y≈490,
center)、描述下(y≈520+)、「刷新次数1」底(y≈841)、「确认」底(y≈983);取 y≈490 行
短文本(2-8 字)即 3 张卡名,按 center-x 排序左→右。

点击 mechanics(2026-08-04 实测):点卡名(y≈474)**不选中**(疑似开详情,bot 点名 540+ 次从没
选中 → 确认灰 → 卡死 18min)→ 点**描述区**(CARD_CLICK_Y=545)才选中(同 invest_env:name 不
选中、描述区选中)。选中 → 确认。decide_event 仅用 state.board,投资策略 overlay 时 board 不可
读 → 空 board stub。

CARD_CLICK_Y + 确认坐标进 screen_info(``currency_war_invest_strategy``):``区域-卡名行``
+ ``按钮-确认``,task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,缺失才用兜底常量。

统一观察架构逐屏迁移(账本 T-8 五相位屏;架构设计 §9.1 并存纪律):本类是
CwScreenOpBase 子类,handle 顶部装配点分流(重入裁决**之后**,先例锚 =
cw_screen_encounter.py :241-251 重入裁决 / :252-258 装配点分流;总纲契约 6
——裁决出口写端 ``_append_confirmed_strategy`` 随共享段两路径同承,ADR-0598
幻影卡收口语义原位保留):两端口完整在场 → 五段生命周期新路径;缺省 None =
生产直连旧路径(原序列,生产行为零变化)。五段形态:observe = 入口锚复探窗
(ADR-0529)→ visit 起点单点复位 → 1s 稳定帧 → 候选读取(实机适配器①封口 =
``_observe_frame``,两路径共享同一读链,G10 首帧 OCR 存底随 payload);
decide+act 内聚 ``_decide_and_act``(决策 → 逐卡刷新链 → 点卡 → 确认置位,
两路径共享零转录);on_outcome = **收编 1 件 ``strategy_refresh_used``**(架构
设计 §6.4-R-E 在册两件②「策略屏迁移批其写端入本面接线」):写端自内联位
(:289-309)随迁注册表发射钩子体,触发点 = ``_emit_refresh_click`` 两路径共
用分派面(触发唯一性先例 = 遭遇屏同名面),随刷新点击置位不等验效,值/键
归一/produced_by/evidence 逐位一致。豁免留守(不入注册表收编面):
``active_strategies`` 本体追加 + write_logic(重入裁决出口)、效果账本
``register_strategy`` + ``apply_effect_burst_grant``(``_append_confirmed_
strategy`` 原位)。本屏 sim 腿 = 不适用(F11 例外清单:有 sim 事实来源
``decide_invest`` 注入段但 sim 端口适配器未建,归 sim 接线批),等价判据
主承重 = 实机在册行为锁 + 写入流对拍(锁面 = sr-od-test
test_cw_obs_arch_phase_screens.py)。
"""
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_comps import augment_affinity
from sr_od.application.currency_war.kernel.cw_events import (
    decide_event,
    is_economy_engine,
)
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_investments import (
    get_strategy,
    is_blood_economy,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.obs.cw_node_obs import (
    pair_refresh_counts_to_slots,
    read_invest_refresh_counts,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    emit_overlay_confirm,
    safe_click,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    ActionOutcome,
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


def _guard_classify(name: str, config) -> tuple[bool, bool, bool, bool]:
    """刷新链逐步守卫的单名分类(ADR-0600 §3.3;D*-free,纯函数可单测)。

    返回 ``(exact, blood, forbidden, top)``:
    - exact = 策略注册表归一后精确命中(轴钉死:环境名/形变名 → False = 不可
      分类,消费方停链 fail-closed——与 kernel 帧级闸同一严格轴);
    - blood/forbidden = F2 唯一 L1 守卫输入(L1 = 非血∧非禁);
    - ``top`` = 顶级判定(S1 定义型 ∨ S2 经济引擎档)。返回值随链语义演进:
      现役消费 = 闸 3 的 L1 计算(exact/blood/forbidden);top 输出现在无
      消费方(原「新卡达顶级停链」随 2026-09-14 终结交回裁定退役),保留
      返回形状供闸内联解包,语义 = 帧内单名顶级事实。
    帧级 D*-dependent 判据(对齐档 N/max_N)只在 kernel:handler 禁直调 kernel
    判据算刷新建议(G1——直调会丢 D*① 三参换基),本 helper 只服务执行期守卫
    与中断检查,不产决策。
    """
    st = get_strategy(name)
    forbidden = any(p in name
                    for p in (getattr(config, 'strategy_forbid', None) or []))
    if st is None:
        return False, False, forbidden, False
    blood = is_blood_economy(st.economy)
    top = bool(augment_affinity(name)) or is_economy_engine(st.economy)
    return True, blood, forbidden, top


@dataclass
class StrategyRefreshClick:
    """逐卡刷新点击意图(on_outcome 登记件 ``strategy_refresh_used`` 的触发
    载荷;发射型单一发射口,T-8 收编)。

    - ``slot``:策略屏画面槽位下标左→右 0-2(与 PickEvent.refresh_slots
      同源,ExecState._invest_refresh_used_slots 注释坐标系);值 = 发射期
      快照(点击时点现值)。
    - ``name``:该槽发射时点的候选卡名(登记件键归一输入 = 现读名集该槽位)。
    """

    slot: int
    name: str


@dataclass
class InvestStrategyObservation:
    """投资策略观察 payload(五段之段1产物;T-8 实机转录形态)。

    - ``entry_ok``:入口锚复探窗判定(ADR-0529;False = 超窗,observe 段
      round_retry 有界自愈);
    - ``options``:候选卡 ``(名字, center-x, center-y)`` 现役读链产物;
    - ``first_ocr_map``:首帧全图 OCR 存底(G10 观察采集域;刷新链读缺回退
      消费已随 2026-09-14 终结交回裁定退役,域保留);
    - ``screen``:稳定帧引用(逐卡计数读同帧同源;sim 适配器落位时该域 =
      None 帧语义,F11 例外清单本批不建)。
    """

    entry_ok: bool
    options: list[tuple[str, int, int]]
    first_ocr_map: dict | None = None
    screen: Any = None


class InvestStrategyLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,T-8)。

    内部复用现役读链(``CwScreenInvestStrategy._observe_frame``:入口锚复探
    窗 + visit 复位 + 1s 稳定帧 + 候选读取)——识别机制不出端口(§2.1 契约
    三则);重入裁决不进适配器(总纲契约 6)。sim 实现 = T5 后辖域本批不建
    (F11 例外清单)。
    """

    def observe(self, op: 'CwScreenInvestStrategy') -> InvestStrategyObservation:
        return op._observe_payload()


class CwScreenInvestStrategy(CwScreenOpBase):
    """投资策略 3 选 1:OCR 卡名 → decide_invest 决策 → (按需逐卡刷新)→ 点最优卡 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-投资策略'   # screen_info 画面(currency_war_invest_strategy.yml)
    # 卡选中点击 Y:screen_info「区域-卡名行」center.y(=卡名选中行);常量=兜底。
    # V4.4 实测(2026-08-05,↺ 推翻 I16「卡底 820 选中」):**点卡名(y≈474)选中**(白边 + 确认亮)。
    # 实机点验:点中产阶级卡名(461,474) → 白边选中 → 点确认 → 推进备战 1-3(链路通)。
    # I16「卡底 820 才选中」错 —— 820 是刷新区/卡底,点没选中 → handle 点 820 不选中 → loop 反复卡死投资策略
    # (整局阻塞,实跑暴露)。旧 doc(2026-08-04「描述区 545 选中」/ I16「卡底 820」)均过时。
    CARD_CLICK_Y: ClassVar[int] = 474   # 兜底(卡名选中);首选 area_center('区域-卡名行')
    # 卡名行 center-y 过滤带(标题 y≈98 / 描述 y≈520+ / 刷新次数 y≈841 / 确认 y≈983)
    NAME_CY_LO: ClassVar[int] = 465
    NAME_CY_HI: ClassVar[int] = 505
    _EXCLUDE: ClassVar[set[str]] = {'请选择投资策略', '攻略', '返回备战界面', '图例', '确认', '刷新次数1'}
    # 确认按钮:screen_info「按钮-确认」center(task#20);常量=兜底。
    CONFIRM: ClassVar[Point] = Point(978, 983)   # 兜底;首选 area_center('按钮-确认')
    #: 入口锚复探窗(动画帧容忍,治本 20/21 局同型失败 2026-09-06 01:41:30 /
    #: 02:22:28「返回状态 非投资策略屏」):投资策略节点首访时派发帧 → 本 op
    #: 首帧之间落在「备战 → 金币过场动画 → overlay 淡入」过渡段(screen_flow_timing.md
    #: #11),首帧采样可 miss「标识-请选择投资策略」;旧实现单探测 miss 即
    #: round_fail(round_fail 不吃 node_max_retry_times,直接炸出整 op),外层
    #: 重试才自愈但每次触发哨兵报警+退出。修法与 cw_loop._invest_overlay_dispatch
    #: 同族(复探=短窗+新截图):首探 miss → 短窗后新截图复探,窗口内命中即
    #: 继续;超窗仍 miss 才 round_fail(防无限等真非目标屏)。决策记录 =
    #: ADR-0529。执行层时序常量(沿 CwLoop.INVEST_REPROBE_WAIT 先例),非策略数值。
    ENTRY_REPROBE_TIMES: ClassVar[int] = 4
    ENTRY_REPROBE_WAIT_S: ClassVar[float] = 0.8
    # 逐卡刷新圆钮 = 「刷新次数N」文本中心 + 固定偏移(ADR-0600 §3.4 文本锚定;
    # 单帧证据不足判文本漂移形态,固定 area 不可行——遭遇屏 _REFRESH_BTN_DX
    # 先例)。偏移实测收口(V7,归档帧 sr-od-test/screens/货币战争-投资策略/
    # default.webp CV 环亮像素质心):钮心 x≈{388,887,1386}、计数文本中心
    # x≈{477,975,1474}(y 同带 ≈855)→ dx ≈ −88。偏移错 → 刷新未命中,
    # 重读=原卡名集,重决策结果天然等价(能力退化非事故,复测即修)。
    _REFRESH_BTN_DX: ClassVar[int] = -88
    # 刷新后等待(执行层时序常量,非策略数值,沿 ADR-0529 先例;screen_flow_timing
    # #13:刷新动画 ~1s,旧实现 1.5s 覆盖)。
    REFRESH_ANIM_WAIT_S: ClassVar[float] = 1.5

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-投资策略')
        # 适配器位缺省装配(先例 = CwScreenPrep/CwScreenEncounter):观察口 =
        # 实机适配器(现役读链封口);动作口 = None = 直连现役动作体(基类
        # 「None = 子类缺省实现自担」)。
        self._observation_adapter = InvestStrategyLiveObservationAdapter()
        # on_outcome 落地登记注册表(架构设计 §6.4;单一发射口,发射即触发
        # ——T-223):收编 1 件 strategy_refresh_used(逐件申报面
        # EMIT_TRIGGERED_DECLARED 在册两件②「策略屏迁移批其写端入本面接线」)。
        # 写端自 handle 刷新链内联位随迁钩子体(位置迁移语义不变):随刷新
        # 点击置位、不等验效(选择落地不置位;发射证据 refresh_click@slot{i}),
        # 逐卡 dict[str,int] write_logic,键 = normalize_invest_name 归一。
        # active_strategies 本体追加 + 效果账本登记 = 豁免留守(重入裁决出口
        # _append_confirmed_strategy 原位,§3.4 申报豁免面不入收编面)。
        self.register_outcome_hook(
            StrategyRefreshClick, self._on_refresh_emitted,
            name='strategy_refresh_used')
        self._ocr_map: dict | None = None   # _read_options 存全图 OCR(ADR-0132 效果采集复用,零额外 OCR)
        # visit 起点单点复位旗标(实例级;ADR-0600 §3.3 复位语义/G6):实例首帧(入口锚验
        # 通过后)清一次 exec_state 已发射槽集,同 visit 重入(round_retry 同
        # 实例)不再清——防重入保留,跨 visit(新实例)必清。
        self._visit_reset_done: bool = False
        # 确认已发待重入裁决的选卡名(验证废除形态,用户裁定 2026-09-10):
        # 确认点击发出后置位,下一轮重入由入口观察裁决——锚不在 = overlay 已关
        # (选卡落地)→ 此刻才 append active_strategies(ADR-0598 幻影卡收口
        # 语义保持:确认未落地轮 = 重走重选,不留幻影;append 时点后移一轮,
        # 由重入观察承载)。None = 无待裁决选卡。
        self._confirm_pending: str | None = None
        # 刷新已发待重入裁决标志(终结动作交回形态,用户裁定 2026-09-14,
        # 投资环境 _refresh_pending 同款):重入裁决见 handle 顶部。
        self._refresh_pending: bool = False

    def _read_options(self, screen) -> list[tuple[str, int, int]]:
        """OCR 3 张卡的 ``(名字, center-x, center-y)``,按卡名行 y 过滤 + 左→右排序。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        self._ocr_map = ocr_map   # ADR-0132:采集复用(同一帧 OCR,不重跑)
        opts: list[tuple[str, int, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (CwScreenInvestStrategy.NAME_CY_LO <= cy <= CwScreenInvestStrategy.NAME_CY_HI
                    and 2 <= len(text) <= 8 and text not in CwScreenInvestStrategy._EXCLUDE):
                opts.append((text, mrl.max.center.x, cy))
        opts.sort(key=lambda t: t[1])
        return opts

    def _entry_anchor_hit(self, screen: MatLike) -> bool:
        """入口锚探测:screen_info id_mark「标识-请选择投资策略」命中(与
        cw_loop 0e 分发 / cw_entry 2b 分支同锚同源)。"""
        return self.round_by_find_area(
            screen, CwScreenInvestStrategy.SCREEN_NAME, '标识-请选择投资策略',
        ).is_success

    def _ensure_entry_screen(self) -> bool:
        """入口锚判定 + 动画帧复探(语义见 ENTRY_REPROBE_* 注):首帧 miss →
        短窗后新截图复探,窗口内命中即 True;超窗仍 miss 返回 False(调用方
        才报失败,防无限等真非目标屏)。"""
        screen = self.last_screenshot
        hit = self._entry_anchor_hit(screen)
        for _ in range(CwScreenInvestStrategy.ENTRY_REPROBE_TIMES):
            if hit:
                return True
            # 复探等待走可中断睡眠:裸 time.sleep 最坏 3.2s 不可停机中断,
            # 绕过框架停机加固(operation.py 停机延迟实证)。
            self._interruptible_sleep(CwScreenInvestStrategy.ENTRY_REPROBE_WAIT_S)
            screen = self.screenshot()
            hit = self._entry_anchor_hit(screen)
        # 末次复探结果必须消费:循环内 if 只判上一轮采样,最后一次采样的
        # 命中若不在此返回,会被整体丢弃(三审 off-by-one:锚恰在窗口末拍
        # 出现仍误报失败——恰是本复探窗要容忍的形态边缘)。
        return hit

    def _visit_reset_once(self) -> None:
        """visit 起点单点复位(ADR-0600 §3.3 复位语义/G6;两路径共用):实例
        首帧(入口锚验通过后)清空 exec_state 已发射槽集——三车道全覆盖:
        ①同 visit 重入(round_retry 同实例,本旗标已置位)不清 → 防重入保留;
        ②失败终止 → 预算耗尽 op 终止 → 下一 visit 新实例天然清,陈旧集不泄入;
        ③确认成功 → 本 visit 终结,下 visit 必清。旗标唯一职责 = 同 visit
        防重入;「可否再刷」权威判定 = 逐卡计数现读(双保险不同源,观察赢
        规则照常辖)。"""
        if self._visit_reset_done:
            return
        self._visit_reset_done = True
        _m0 = self.ctx.cw_match
        if _m0 is not None:
            exec_state_of(_m0.session)._invest_refresh_used_slots.clear()

    def _observe_frame(self) -> InvestStrategyObservation:
        """入口锚复探窗 + visit 复位 + 1s 稳定帧 + 候选读取(实机适配器①
        封口内容;两路径共用读链,总纲 §2.1-1 抽共享方法)。时序口径逐位
        保留:用户口述口径(docs/game/currency_war/research/
        screen_flow_timing.md #11,2026-09-02)「请选择投资策略」标题出现
        1s 后画面(三卡)才稳定(流转 = 备战 → 金币过场动画 → overlay 自动
        弹出)——入口帧可能在稳定期内,立即读刷新次数/卡名有读缺风险。等
        1s 重截稳定帧再读(与 cw_screen_invest_env #3 修复同型)。超窗 =
        entry_ok False(调用方 round_retry 有界自愈,ADR-0529 二次治本)。"""
        if not self._ensure_entry_screen():
            return InvestStrategyObservation(entry_ok=False, options=[])
        self._visit_reset_once()
        # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
        # #11,2026-09-02):「请选择投资策略」标题出现 1s 后画面(三卡)才稳定
        # (流转 = 备战 → 金币过场动画 → overlay 自动弹出)——入口帧可能在
        # 稳定期内,立即读刷新次数/卡名有读缺风险。等 1s 重截稳定帧再读
        # (与 cw_screen_invest_env #3 修复同型)。
        time.sleep(1.0)
        screen = self.screenshot()
        opts = self._read_options(screen)
        return InvestStrategyObservation(entry_ok=True, options=opts,
                                         first_ocr_map=self._ocr_map, screen=screen)

    def _observe_payload(self) -> InvestStrategyObservation:
        """稳定帧观察链 → payload(适配器①与缺省直连共用的装配形态)。"""
        return self._observe_frame()

    def _emit_refresh_click(self, session: 'StrategySession',
                            slot: int, name: str) -> None:
        """刷新点击发射时点(单一发射口,发射即触发;§6.5-4 随点击置位不等
        验效)。防重入旗标 = 执行侧载体留守(非登记件;发射即记不等验效,
        位置迁移语义不变);登记件写端经 on_outcome 注册表触发——本方法 =
        两路径(旧 handle / 五段循环)共用分派面,触发唯一性先例 =
        CwScreenEncounter._emit_refresh_click。"""
        exec_state_of(session)._invest_refresh_used_slots.add(slot)
        self.fire_outcome_hooks(
            StrategyRefreshClick(slot=slot, name=name),
            evidence=f'refresh_click@slot{slot}')

    def _on_refresh_emitted(self, outcome: ActionOutcome) -> None:
        """strategy_refresh_used 写端(on_outcome 注册表·发射型钩子体;
        §6.4 收编行「策略屏逐卡刷新计数」,T-8 自 handle 刷新链内联位随迁)。
        策略屏刷新已用**随刷新点击置位、不等验效**,选择落地不置位;逐卡键
        = 注册表规范卡名(normalize_invest_name 归一后入键,与
        STRATEGY_EFFECTS 同键空间,§3.4.4 键口径)。单次逻辑写入(§3.4 申报
        豁免:自身动作事实,无可核对的后续定型帧;之后仍受观察覆盖辖)。
        best-effort 记录面:失败不阻塞刷新链(与升级挂点同纪律)。"""
        _click = outcome.action
        match = self.ctx.cw_match
        if match is None:
            return
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                board_state_of,
            )
            from sr_od.application.currency_war.kernel.cw_investments import (
                normalize_invest_name,
            )
            _bs_rc = board_state_of(match.session)
            _used = dict(_bs_rc.strategy_refresh_used.value or {})
            _k = normalize_invest_name(_click.name)
            _used[_k] = int(_used.get(_k, 0)) + 1
            _bs_rc.write_logic(
                _bs_rc.strategy_refresh_used, _used,
                produced_by='CwScreenInvestStrategy',
                evidence=outcome.evidence,
                sig=ChannelSig(family='logic_action',
                               actor='CwScreenInvestStrategy',
                               mode='compute'))
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞
            log.warning(f'[cw-strat] 刷新计数记录失败(不阻塞): {e}')

    @operation_node(name='投资策略', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        # 重入裁决(观察驱动,验证废除形态):上轮已发确认 → 本轮入口锚不在
        # = overlay 已关(选卡落地)→ 补 append + success 交回;锚仍在 = 确认
        # 未落地 → 清标志重走(计节点预算,重读重选)。两路径共用(分流前挂,
        # 先于五段 lifecycle 的 observe 门;总纲契约 6,先例锚
        # cw_screen_encounter.py :241-251/:252-258;裁决出口写端
        # _append_confirmed_strategy 随共享段)。
        if self._confirm_pending is not None:
            _p = self._confirm_pending
            self._confirm_pending = None
            if not self._entry_anchor_hit(self.last_screenshot):
                self._append_confirmed_strategy(_p)
                return self.round_success(f'{_p} 已确认(重入观察裁决)', wait=2.0)
        # 刷新重入裁决(终结动作交回形态,与确认重入裁决同款结构,投资环境
        # T-206 先例):上轮已发刷新 → 本轮入口锚在 = 预期(逐卡重掷后
        # overlay 仍在、新卡已渲染)→ 穿透到正常观察链(重观察 + 重分类
        # 重决策);锚不在 = overlay 意外离开(刷新从不关 overlay,非预期面)
        # → success 交回外循环按当前画面重分派。两路径共用(分流前挂)。
        if self._refresh_pending:
            self._refresh_pending = False
            if not self._entry_anchor_hit(self.last_screenshot):
                return self.round_success(
                    '投资策略刷新后画面已离开(重入观察裁决)', wait=2.0)
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run/
        # CwScreenEncounter.handle):两端口完整在场 → 五段生命周期新路径;
        # 缺省 None = 生产直连旧路径(下方原序列,生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        obs = self._observe_frame()
        if not obs.entry_ok:
            # 超窗走 round_retry 而非 round_fail(二次治本,2026-09-06
            # 04:16:38 实证复探窗 3.2s 仍不够覆盖个别过渡段):retry 消耗
            # node_max_retry_times 预算有界自愈,且不产生 ERROR 行——
            # round_fail 会炸出整 op 并触发哨兵报警退出(20-22 局实证
            # 每次 fail 一次哨兵退出)。ADR-0529 原「拒 fail→retry」的
            # 前提(外层重试等价)被实证推翻,重审结论见 ADR 修订。
            return self.round_retry('投资策略屏未稳定,复探超窗重试')
        return self._decide_and_act(obs.options, obs.screen, obs.first_ocr_map)

    def _decide_and_act(self, opts: list[tuple[str, int, int]], screen,
                        first_ocr_map: dict | None) -> OperationRoundResult:
        """决策+动作内聚体(五段 decide+act 两路径共享零转录;旧 handle
        :226-389 逐位平移):decide_invest 决策(无 match 防御路径显式跳过
        刷新链)→ 逐卡刷新终结动作(发射点 = ``_emit_refresh_click``;点钮
        后本访问即交回,链内注)→ 点卡名选中 → 确认置位(落地判定归下一轮
        重入裁决,ADR-0598)。

        ``first_ocr_map`` = 观察段首帧 OCR 存底(G10 域;终结交回形态下
        刷新链零重读,本参保留观察 payload 契约,链内不再消费)。"""
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _x, _y in opts]
        # 不可读 → 传空 CwSimFrame(decide_event 只用 board 判 DoT 克制,空 board = 不惩罚,安全)。
        match = self.ctx.cw_match
        if names:
            if match is not None:
                # ADR-0144:真状态替空 stub。决策输入消费切换(迁移批次二):
                # 值源 = GameState 视图(cw_bs_view.strategy_input_state)。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    board_state_of,
                )
                pick = match.strategy.decide_invest('strategy', names, board_state_of(match.session), match.session, config)
            else:
                # 防御:无 match(局外独立跑)。经验分退役后 decide_event 不读
                # hp/品质惩罚(唯一局面消费 = board.value or {},未观察等价
                # 空表)。**显式跳过刷新链**(ADR-0600 §3.3 防御路径):刷新链
                # 依赖 exec_state_of(match.session) 与 match 上下文,局外防御
                # 帧零行为增量(refresh_slots 不消费)。
                # 换源 T-146(登记集消点):防御视图 = 裸容器(全域未观察空
                # 视图);旧合成 CwSimFrame + 过渡桥装箱退役。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    BS_SCHEMA_VERSION,
                    GameState,
                )
                pick = decide_event(names, config,
                                    GameState(schema_version=BS_SCHEMA_VERSION))
        else:
            pick = None

        # ===== 逐卡刷新 = 终结动作(用户裁定 2026-09-14,照投资环境 T-206
        # 形态:点钮后本访问即交回,重入后重观察重决策;闸门语义 = ADR-0600
        # §3.3 逐卡预算)=====
        if (match is not None and pick is not None and pick.refresh_slots
                and opts):
            _ex = exec_state_of(match.session)
            _counts = read_invest_refresh_counts(self.ctx, screen, 'strategy')
            _slot_hits = (pair_refresh_counts_to_slots(
                _counts, [x for _n, x, _y in opts])
                if _counts else [None] * len(opts))
            for _i in pick.refresh_slots:
                if _i >= len(opts):
                    continue
                # 闸 1:逐卡计数现读 >0(权威闸,无缓存无假设口径——读缺按
                # 无授予处理,失败安全;读缺守卫保留 = 2026-09-14 裁定;
                # 预注册锁 10,ADR-0600 §5)。
                _hit = _slot_hits[_i] if _i < len(_slot_hits) else None
                if _hit is None or _hit[0] <= 0:
                    continue
                # 闸 2:防重入(发射即记;复位 = visit 起点单点)。
                if _i in _ex._invest_refresh_used_slots:
                    continue
                # 闸 3:F2 唯一 L1 槽守卫(按当前名集现算,预注册锁 14,
                # ADR-0600 §5)。
                _l1_now = [j for j, (_ex_flag, _b, _f, _t) in
                           enumerate(_guard_classify(n, config) for n in names)
                           if _ex_flag and not _b and not _f]
                if _l1_now == [_i]:
                    continue
                # 点钮:该槽「刷新次数N」文本中心 + 偏移(safe_click 带 bug#1
                # mouse_move 缓解,遭遇屏同款)。
                _tx, _ty = _hit[1], _hit[2]
                safe_click(self, Point(_tx + CwScreenInvestStrategy._REFRESH_BTN_DX, _ty),
                           tag='cw-strat')
                # 发射即记(防重入优先,不等验效)+ 登记件经 on_outcome 注册表
                #(发射型触发点单一分派面 _emit_refresh_click,T-8 收编;值/
                # 键归一/produced_by/evidence 逐位随迁钩子体,对拍锁面)。
                self._emit_refresh_click(match.session, _i, names[_i])
                # 动画窗固定等待(机械执行时序,非判效)→ 终结交回:本访问
                # 零比对(刷后不重读不比对不重决策,用户裁定 2026-09-14),
                # 选卡/确认均不在本访问;pending + round_retry 节点重跑,
                # 重入裁决(handle 顶部)后走正常观察链重分类重决策。
                time.sleep(CwScreenInvestStrategy.REFRESH_ANIM_WAIT_S)
                log.info(f'[cw-strat] 槽{_i}刷新终结交回:重入后重观察重决策')
                self._refresh_pending = True
                return self.round_retry(wait=1)

        if pick is not None and 0 <= pick.option_idx < len(opts):
            chosen, choose_x, choose_y = opts[pick.option_idx]
            reason = pick.reason
        elif opts:
            chosen, choose_x, choose_y, reason = opts[0][0], opts[0][1], opts[0][2], 'fallback(no-decision)'
        else:
            chosen, choose_x, choose_y, reason = '?', 920, 490, 'fallback(no-ocr)'
        log.info(f'[cw-strat] options={names} chose={chosen!r}@({choose_x},{choose_y}) reason={reason}')
        # 持卡注入面(session.active_strategies)的 append 已移至确认成功后
        #(重入裁决出口 _append_confirmed_strategy;ADR-0598 幻影卡收口)——
        # 旧时序 append 先于点卡确认,确认失败轮(session.active_strategies
        # 是息帽 resolved 链的输入源)留下幻影卡:幻影买断制 = 息线全关,
        # 比幻影 9/10 更烈。
        # ADR-0132 采集(候选卡面+效果原文按卡分桶)已随 invest_cards 流写入端
        # 退役删除(删除波 1;效果原文回流断供为裁定的接受后果,收编归宿 =
        # strategy_offer 画面 payload 域,候其落地批接线);未注册名告警
        # (注册表只 T0 子集)保留,数据源 = 当前确认轮候选名。
        for _c in (opts or []):
            _n = _c[0] if isinstance(_c, tuple) else _c
            if _n not in ('?',) and get_strategy(_n) is None:
                log.warning(f'[cw-strat] 投资策略名不在注册表(数据缺口): {_n!r}')

        # 点最优卡的**卡名**选中(Y 从 screen_info「区域-卡名行」center 读;缺失兜底 CARD_CLICK_Y=474)。
        # safe_click 带 bug#1 mouse_move 缓解(partner reset 根因同类)。
        _sel = area_center(self.ctx, '区域-卡名行', CwScreenInvestStrategy.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else CwScreenInvestStrategy.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        safe_click(self, target, tag='cw-strat')
        time.sleep(0.7)
        # 确认 + 机械交回(验证废除:不读屏判「overlay 关没关」,落地由下一轮
        # 重入入口观察裁决——裁决点补 append,见 handle 顶部/_append_confirmed_strategy)。
        # 确认 center 从 screen_info 读,缺失兜底。
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenInvestStrategy.SCREEN_NAME) or CwScreenInvestStrategy.CONFIRM
        self._confirm_pending = chosen if chosen != '?' else None
        _rr = emit_overlay_confirm(self, confirm_point=_confirm, entry_keyword='投资策略',
                                   tag='cw-strat')
        return _rr

    def _append_confirmed_strategy(self, chosen: str) -> None:
        """重入裁决出口的持卡登记面(ADR-0598 幻影卡收口语义承载):调用点 =
        handle 顶部重入裁决(入口锚不在 = overlay 已关 = 选卡落地)。两路径
        共用(总纲契约 6:裁决出口写端随共享段;豁免留守 = 本体追加 + 到账
        登记不入 on_outcome 注册表收编面)。

        持卡本体追加 + 到账登记(§3.3 #22 ConfirmStrategy;粗粒度 expected,
        效果走台账不进 session 推进);去重防重复入列。原「chosen 只点不存」
        bug 的修复语义由本块承载。"""
        match = self.ctx.cw_match
        if match is None or not chosen or chosen == '?':
            return
        if chosen not in match.session.active_strategies:
            match.session.active_strategies.append(chosen)
        # GameState 写端(迁移批次二,§3.4.4/§4 投资选择行):持有投资
        # 策略=本屏写入、局级累计(逐次选择追加);单次逻辑写入
        # (§3.4 申报豁免)。品质锚挂建模批(设计 §3.4.4)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
            board_state_of,
        )
        board_state_of(match.session).write_logic(
            board_state_of(match.session).active_strategies,
            list(match.session.active_strategies),
            produced_by='CwScreenInvestStrategy',
            sig=ChannelSig(family='logic_action',
                           actor='CwScreenInvestStrategy', mode='compute'))
        # 效果账本选卡登记挂点(迁移批次三,设计 §5.1「买卡=激活登记」
        # /§8.7 批次三件 4;免战牌同点自动登记——件 5「§3.2.19 载体归一
        # 的另一半,禁只做一半」)。chosen 命中效果注册表(规范名归一
        # 后)才登记;acquired_t = 登记时点节点序快照((plane-1)*9+round,
        # 基 1,ActiveEffect 坐标系;GameState 节点单例,节点未观察
        # (引导窗)= None 缺位,last_state 帧回退随链退役批删除)。
        # 登记面 best-effort:失败不阻塞
        # 选卡主链(与升级挂点同纪律);账本当前零决策消费(§5.1 过渡
        # 口径:挂点接线未完成面一律观察覆盖兜底)。
        try:
            from sr_od.application.currency_war.kernel.cw_investments import (
                STRATEGY_EFFECTS,
                normalize_invest_name,
            )
            _spec = STRATEGY_EFFECTS.get(normalize_invest_name(chosen))
            if _spec is not None:
                _bs_reg = board_state_of(match.session)
                _nd = _bs_reg.node.value
                _t = ((_nd.plane - 1) * 9 + _nd.round_num
                      if _nd is not None else None)
                _bs_reg.effects.register_strategy(_spec, _t)
                # 桥·burst 形态(迁移批次三 B1,设计 §3.3.5/§5.1):登记
                # 时点把免费刷新 burst 额度一次性累加进余额(固定理财
                # 即时段 2 等;载体 = payload.free_refresh_burst,零额度
                # no-op)。每节点/容量两形态在 cw_loop tick 挂点,不经此。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    apply_effect_burst_grant,
                )
                apply_effect_burst_grant(
                    _bs_reg, _spec,
                    frame=f'p{_nd.plane}-r{_nd.round_num}'
                    if _nd is not None else '')
                # 桥·板面重写形态(设计 §5 全员晋升/人力重组两行;生产接线 =
                # 选卡确认落地登记点,与 register_strategy/burst 桥同点):board_
                # rewrite 声明经桥落写端归属——出售面=逻辑写(清场+退款按卖价
                # 公式)、整场替换面=零写端观察收口,报告留证;非重写条目返回
                # None 零动作。归属判据单一源 = GameState 设计 §5.3,桥内申报。
                from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                    apply_board_rewrite,
                )
                _rw = apply_board_rewrite(
                    _bs_reg, _spec,
                    frame=f'p{_nd.plane}-r{_nd.round_num}'
                    if _nd is not None else '')
                if _rw is not None:
                    log.info(f'[cw-strat] 板面重写桥:{_rw.rewrite}'
                             f'(退款 {_rw.refund_gold}/清空域 '
                             f'{",".join(_rw.cleared_fields) or "无"})')
                log.info(f'[cw-strat] 效果账本登记:{_spec.name}(t={_t})')
        except Exception as e:   # noqa: BLE001  登记面失败不阻塞
            log.warning(f'[cw-strat] 效果账本登记失败(不阻塞): {e}')
        # (原 register_confirm_arrival('ConfirmStrategy') 已随 ADR-0651
        #  两态制废除:active_strategies 本体追加 + write_logic 直写均在
        #  上方确认成功写点,无挂账登记环节。)

    # ---- 五段生命周期(统一观察架构 §5.1;T-8,先例 = CwScreenEncounter)----

    def lifecycle_observe(self
                          ) -> tuple[InvestStrategyObservation,
                                     OperationRoundResult | None]:
        """段1 observe:入口锚复探窗(ADR-0529,超窗 round_retry 早退有界
        自愈)→ visit 起点单点复位 → 实机适配器①稳定帧观察(1s 稳定期 +
        候选读取,G10 首帧 OCR 存底随 payload)。重入裁决不在本段(总纲
        契约 6:留守 handle 分流前共享段,裁决出口写端随段共享)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_payload())
        if not obs.entry_ok:
            # 超窗走 round_retry 而非 round_fail(二次治本;语义与旧 handle
            # 逐位一致,出处注 = handle 旧路径同位注释/ADR-0529 修订)。
            return obs, self.round_retry('投资策略屏未稳定,复探超窗重试')
        return obs, None

    def lifecycle_decision_cycle(self, payload: InvestStrategyObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作决策循环):decide+act 内聚 ``_decide_and_act``
        (决策/逐卡刷新终结动作/点卡/确认置位全在现役时序,两路径共享零转录;
        刷新登记件发射点 = ``_emit_refresh_click`` 共用分派面);on_outcome
        = 注册表触发随发射点(本屏唯一收编件 strategy_refresh_used)。
        轮次终结出口 = 逐卡刷新终结交回 + 确认机械交回(两者的落地/重观察
        判定均归下一轮重入裁决,ADR-0598/用户裁定 2026-09-14)。"""
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = self._decide_and_act(payload.options, payload.screen,
                                  payload.first_ocr_map)
        self._lifecycle_mark('on_outcome')
        return rs
