
"""货币战争 投资策略 3 选 1 op(从主循环拆出)。

OCR 3 张投资策略卡名 → 经 ``match.strategy.decide_invest``(委托 ``cw_events.decide_event``
打分)→ 点**最优**卡 + 确认。替代原"盲点中卡"(无策略)。

逐卡刷新 = 终结动作(用户裁定 2026-09-14,照投资环境屏同款形态):
``decide_event`` 帧级触发(零阈值结构判据:全精确分类 ∧ 无 S1/S2 ∧ max_N≠1,
推导见 ADR-0600 §3.2 + math_proofs P81)→ 返回 ``refresh_slots`` 非空 ∧
逐槽计数现读授权(读缺 = 无授权)∧ 容器逐卡计数闸(发射过的卡不重刷)→
文本锚定点刷新圆钮一次 → 固定等待(机械时序,非判效)→ 本访问即终结交回
(外循环重进 = 入口重建,新事实的观察与决策归重进的下一访问)。投资策略
屏刷新是**逐卡刷新**(每卡独立按钮、独立计数,归档帧对实证)。
验效双通道已拆除(用户裁定 2026-09-10:动作 op 只管机械执行禁止验效,出处 =
验证违规清查报告 H2),2026-09-14 裁定进一步收敛为零比对:访问内刷后
不重读不比对不重决策,「刷没刷成」不判;读缺守卫 = 逐槽计数现读的
读缺按无授予处理(失败安全)。逐卡「已发射」账读端 = 容器
``node_screen_refresh.strategy_refresh_used`` 逐卡计数(局内累计;**计数
写端随画面 op 基类退役**,记账由动作 op 会话承接,本 op 只保留读端闸)。

卡名按行过滤(2026-08-04 snap 实测):标题「请选择投资策略」顶(y≈98)、卡名中(y≈490,
center)、描述下(y≈520+)、「刷新次数1」底(y≈841)、「确认」底(y≈983);取 y≈490 行
短文本(2-8 字)即 3 张卡名,按 center-x 排序左→右。

点击 mechanics(2026-08-04 实测):点卡名(y≈474)**不选中**(疑似开详情,bot 点名 540+ 次从没
选中 → 确认灰 → 卡死 18min)→ 点**描述区**(CARD_CLICK_Y=545)才选中(同 invest_env:name 不
选中、描述区选中)。选中 → 确认。decide_event 仅用 state.board,投资策略 overlay 时 board 不可
读 → 空 board stub。

CARD_CLICK_Y + 确认坐标进 screen_info(``currency_war_invest_strategy``):``区域-卡名行``
+ ``按钮-确认``,task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,缺失才用兜底常量。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node = 入口锚复探窗(ADR-0529 有界自愈:复探窗内
自愈、超窗 round_retry 消耗观察 node 预算,既有 retry 面不属新增帽)→
visit 起点单点复位 → 1s 稳定帧 → 候选一次读(G10 首帧 OCR 存底随 obs)→
``report_screen_invest_strategy_obs`` 落容器 ``invest_strategy_opts``(提名
序列;names 空 = OCR 未读得不写,闸在 report 内)→ obs 挂实例属性进决策
node。决策动作 node = 重入裁决顶部(确认已发 → 入口锚不在 = overlay 已关
= 选卡落地 → 此刻才 append ``active_strategies`` + success 交回;锚在 =
未落地 → 清标志重走)→ 零参决策(候选自容器槽)→ 逐卡刷新终结交回 /
选卡+确认链经 ``CwActionPickInvestOp`` 派发(pick-op-unify 批机械链迁入
动作 op)→ ``round_wait`` 循环推进(不烧节点重试预算;不收敛 =
策略 bug 响亮暴露,无防御上限)。决策面留守写点:``active_strategies``
重入裁决出口 append(ADR-0598 幻影卡收口:确认未落地轮 = 重走重选,不留
幻影)+ 效果账本登记 + 授予置闩(``_append_confirmed_strategy`` 原位)。
本屏 sim 腿 = 不适用(sim 端口适配器未建),等价判据主承重 = 实机在册
行为锁。
"""
import time
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_comps import augment_affinity
from sr_od.application.currency_war.kernel.cw_events import (
    decide_event,
    is_economy_engine,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    get_strategy,
    is_blood_economy,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.invest_strategy import (
    CwScreenInvestStrategyObs,
    report_screen_invest_strategy_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickInvestParam,
    CwActionRefreshInvestCardsParam,
)
from sr_od.application.currency_war.obs.cw_node_obs import (
    pair_refresh_counts_to_slots,
    read_invest_refresh_counts,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


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


class CwScreenInvestStrategy(SrOperation):
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
    #: 重试才自愈但每次触发哨兵报警+退出。修法(复探=短窗+新截图):首探
    #: miss → 短窗后新截图复探,窗口内命中即继续;超窗仍 miss 才 round_retry
    #: (防无限等真非目标屏)。决策记录 = ADR-0529。执行层时序常量,非策略数值。
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
        SrOperation.__init__(self, ctx, op_name='货币战争-投资策略')
        self._ocr_map: dict | None = None   # _read_options 存全图 OCR(ADR-0132 效果采集复用,零额外 OCR)
        # 确认已发待重入裁决的选卡名(验证废除形态,用户裁定 2026-09-10):
        # 确认点击发出后置位,下一轮重入由入口观察裁决——锚不在 = overlay 已关
        # (选卡落地)→ 此刻才 append active_strategies(ADR-0598 幻影卡收口
        # 语义保持:确认未落地轮 = 重走重选,不留幻影;append 时点后移一轮,
        # 由重入观察承载)。None = 无待裁决选卡。
        self._confirm_pending: str | None = None
        # 观察结果(观察 node 产物,决策动作 node 消费;entry_ok False = 复探
        # 超窗,观察轮 round_retry 不装载)。
        self._obs: CwScreenInvestStrategyObs | None = None

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

    def _observe_frame(self) -> CwScreenInvestStrategyObs:
        """入口锚复探窗 + 1s 稳定帧 + 候选读取(观察轮读链)。时序口径逐位
        保留:用户口述口径(docs/game/currency_war/research/
        screen_flow_timing.md #11,2026-09-02)「请选择投资策略」标题出现
        1s 后画面(三卡)才稳定(流转 = 备战 → 金币过场动画 → overlay 自动
        弹出)——入口帧可能在稳定期内,立即读刷新次数/卡名有读缺风险。等
        1s 重截稳定帧再读(与 cw_screen_invest_env 同型)。超窗 =
        entry_ok False(调用方 round_retry 有界自愈,ADR-0529 二次治本)。"""
        if not self._ensure_entry_screen():
            return CwScreenInvestStrategyObs(entry_ok=False, options=[])
        time.sleep(1.0)
        screen = self.screenshot()
        opts = self._read_options(screen)
        return CwScreenInvestStrategyObs(entry_ok=True, options=opts,
                                         first_ocr_map=self._ocr_map, screen=screen)

    @operation_node(name='观察', is_start_node=True, node_max_retry_times=10)
    def observe(self) -> OperationRoundResult:
        """入口锚复探窗(ADR-0529 有界自愈)+ 稳定帧一次读 → report 落容器。

        超窗走 round_retry 而非 round_fail(二次治本,2026-09-06
        04:16:38 实证复探窗 3.2s 仍不够覆盖个别过渡段):retry 消耗
        观察节点 node_max_retry_times 预算有界自愈,且不产生 ERROR 行——
        round_fail 会炸出整 op 并触发哨兵报警退出(20-22 局实证
        每次 fail 一次哨兵退出)。ADR-0529 原「拒 fail→retry」的
        前提(外层重试等价)被实证推翻,重审结论见 ADR 修订。
        在窗 → 候选一次读 → ``report_screen_invest_strategy_obs`` 落容器
        ``invest_strategy_opts``(names 空 = OCR 未读得不写,闸在 report
        内;match/gs 缺席的局外兜底路径跳过 report)→ obs 挂实例属性。"""
        obs = self._observe_frame()
        if not obs.entry_ok:
            return self.round_retry('投资策略屏未稳定,复探超窗重试')
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_invest_strategy_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=10)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 零参决策 → 逐卡刷新终结交回 / 点卡+确认 → round_wait。

        重入裁决(观察驱动,验证废除形态):上轮已发确认 → 本轮入口锚不在
        = overlay 已关(选卡落地)→ 补 append active_strategies + success
        交回;锚在 = 确认未落地 → 清标志重走(重选重确认)。循环推进 =
        round_wait(不烧节点重试预算;不收敛 = 策略 bug 响亮暴露,无防御
        上限)。"""
        if self._confirm_pending is not None:
            _p = self._confirm_pending
            self._confirm_pending = None
            if not self._entry_anchor_hit(self.last_screenshot):
                self._append_confirmed_strategy(_p)
                return self.round_success(f'{_p} 已确认(重入观察裁决)', wait=2.0)
        obs = self._obs
        return self._decide_and_act(
            obs.options if obs is not None else [],
            obs.screen if obs is not None else None,
            obs.first_ocr_map if obs is not None else None)

    def _decide_and_act(self, opts: list[tuple[str, int, int]], screen,
                        first_ocr_map: dict | None) -> OperationRoundResult:
        """决策+动作内聚体(决策面):decide_invest 决策(无 match 防御路径
        显式跳过刷新链)→ 逐卡刷新终结动作(点钮后本访问即终结交回,外循
        环重进重观察重决策)→ 点卡名选中 → 确认置位(落地判定归下一轮
        重入裁决,ADR-0598)。

        ``first_ocr_map`` = 观察段首帧 OCR 存底(G10 域;终结交回形态下
        刷新链零重读,本参保留观察 obs 契约,链内不再消费)。"""

        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _x, _y in opts]
        match = self.ctx.cw_match
        # 零参决策(写槽已由观察轮 report 落容器 invest_strategy_opts;决策
        # 调用形态不变,同访问覆盖写)。输出 = 单一 CwAction:
        # CwActionRefreshInvestCardsParam(逐卡刷新建议)/ CwActionPickInvestParam(选卡)互斥单发。
        act = None
        refresh_slots: tuple[int, ...] = ()
        if names:
            if match is not None:
                act = match.strategy.decide_invest_strategy()
            else:
                # 防御:无 match(局外独立跑)。经验分退役后 decide_event 不读
                # hp/品质惩罚(唯一局面消费 = board.value or {},未观察等价
                # 空表)。**显式跳过刷新链**(ADR-0600 §3.3 防御路径):刷新链
                # 依赖容器读与 match 上下文,局外防御帧零行为增量。
                # 换源(登记集消点):防御视图 = 裸容器(全域未观察空视图)。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    GAME_STATE_SCHEMA_VERSION,
                    GameState,
                )
                _kpick = decide_event(names, config,
                                      GameState(schema_version=GAME_STATE_SCHEMA_VERSION))
                act = CwActionPickInvestParam(idx=_kpick.option_idx, reason=_kpick.reason)
        if isinstance(act, CwActionRefreshInvestCardsParam):
            refresh_slots = act.slots

        # ===== 逐卡刷新 = 终结动作(用户裁定 2026-09-14,照投资环境屏
        # 形态:点钮后本访问即终结交回,外循环重进后重观察重决策;闸门
        # 语义 = ADR-0600 §3.3 逐卡预算)=====
        if refresh_slots and opts and match is not None:
            _counts = read_invest_refresh_counts(self.ctx, screen, 'strategy')
            _slot_hits = (pair_refresh_counts_to_slots(
                _counts, [x for _n, x, _y in opts])
                if _counts else [None] * len(opts))
            # 闸 2 读源 = 容器逐卡计数快照(键 = 注册表规范卡名;**计数写端
            # 随画面 op 基类退役**——记账由动作 op 会话承接,本读端闸原样)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            _used_map = dict(game_state_of(
                match.session).strategy_refresh_used.value or {})
            for _i in refresh_slots:
                if _i >= len(opts):
                    continue
                # 闸 1:逐卡计数现读 >0(权威闸,无缓存无假设口径——读缺按
                # 无授予处理,失败安全;读缺守卫保留 = 2026-09-14 裁定;
                # 预注册锁 10,ADR-0600 §5)。
                _hit = _slot_hits[_i] if _i < len(_slot_hits) else None
                if _hit is None or _hit[0] <= 0:
                    continue
                # 闸 2:防重入 = 容器逐卡计数 >0(与闸 1 现读互为双闸;
                # visit 级复位语义随旧执行侧槽集消亡——闸 1 屏上余量现读 +
                # 本计数下无重入放大面,终结动作化后每访问恰一次决策)。
                if _used_map.get(normalize_invest_name(names[_i]), 0) > 0:
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
                # 动画窗固定等待(机械执行时序,非判效)→ 终结交回:本访问
                # 零比对(刷后不重读不比对不重决策,用户裁定 2026-09-14),
                # 选卡/确认均不在本访问;round_success 交回外循环重进 = 入口
                # 重建,重进后重观察重分类重决策。
                time.sleep(CwScreenInvestStrategy.REFRESH_ANIM_WAIT_S)
                log.info(f'[cw-strat] 槽{_i}刷新终结交回:重进后重观察重决策')
                return self.round_success('投资策略刷新终结交回(重进重观察重决策)',
                                          wait=1)
            # 三闸全败(建议帧但无可执行刷新)→ 同访问重调落选卡:策略侧
            # 同帧去重(建议帧首调发建议、紧随重调落选卡)等价旧 CwActionPickEventParam
            # 「idx + refresh_slots 并载、闸败回退选卡」行为,零选卡漂移。
            act = match.strategy.decide_invest_strategy()
            if isinstance(act, CwActionRefreshInvestCardsParam):   # 防御:策略未实现去重
                act = None

        if isinstance(act, CwActionPickInvestParam) and 0 <= act.idx < len(opts):
            chosen, choose_x, choose_y = opts[act.idx]
            reason = act.reason
        elif opts:
            chosen, choose_x, choose_y, reason = opts[0][0], opts[0][1], opts[0][2], 'fallback(no-decision)'
        else:
            chosen, choose_x, choose_y, reason = '?', 920, 490, 'fallback(no-ocr)'
        log.info(f'[cw-strat] options={names} chose={chosen!r}@({choose_x},{choose_y}) reason={reason}')
        # 持卡注入面(gs.active_strategies)的 append 已移至确认成功后
        #(重入裁决出口 _append_confirmed_strategy;ADR-0598 幻影卡收口)——
        # 旧时序 append 先于点卡确认,确认失败轮(active_strategies
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

        # 点最优卡的**卡名**选中(Y 从 screen_info「区域-卡名行」center 读;
        # 缺失兜底 CARD_CLICK_Y=474)+ 确认链经工厂(pick-op-unify 批:
        # 机械链迁入 ``CwActionPickInvestOp``,本 op 只决策与写端;定位点/
        # 确认钮中心决策半现算经 env 显式传入)。
        _sel = area_center(self.ctx, '区域-卡名行', CwScreenInvestStrategy.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else CwScreenInvestStrategy.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        # 确认 + 机械交回(验证废除:不读屏判「overlay 关没关」,落地由下一轮
        # 重入入口观察裁决——裁决点补 append,见 act 顶部/_append_confirmed_
        # strategy)。确认 center 从 screen_info 读,缺失兜底。
        # 派发实例携真实选中下标(上报 param 即真实选择;fallback/盲点 = 0)。
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenInvestStrategy.SCREEN_NAME) or CwScreenInvestStrategy.CONFIRM
        self._confirm_pending = chosen if chosen != '?' else None
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        _param_idx = (act.idx if isinstance(act, CwActionPickInvestParam)
                      and 0 <= act.idx < len(opts) else 0)
        _env = OverlayPickExecEnv(op=self, idx=_param_idx, target=target,
                                  confirm=_confirm, entry_keyword='投资策略')
        action_op_for(CwActionPickInvestParam(idx=_param_idx), self.ctx,
                      _env).execute()
        return self.round_wait(wait=1)

    def _append_confirmed_strategy(self, chosen: str) -> None:
        """重入裁决出口的持卡登记面(ADR-0598 幻影卡收口语义承载):调用点 =
        act 顶部重入裁决(入口锚不在 = overlay 已关 = 选卡落地)。

        持卡本体追加 + 到账登记(§3.3 #22 ConfirmStrategy;粗粒度 expected,
        效果走台账不进 session 推进);去重防重复入列。原「chosen 只点不存」
        bug 的修复语义由本块承载。"""
        match = self.ctx.cw_match
        if match is None or not chosen or chosen == '?':
            return
        # GameState 写端(§3.4.4/§4 投资选择行):持有投资
        # 策略=本屏写入、局级累计(逐次选择追加);单次逻辑写入
        # (申报豁免)。终态契约 §B:session 份退役,直读直写容器。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
        )
        _gs_inv = (match.gs if getattr(match, 'gs', None) is not None
                   else match.gs)
        _cur = list(_gs_inv.active_strategies.value or [])
        if chosen not in _cur:
            _cur.append(chosen)
        _gs_inv.write_logic(
            _gs_inv.active_strategies,
            _cur,
            produced_by='CwScreenInvestStrategy',
            sig=ChannelSig(family='logic_action',
                           actor='CwScreenInvestStrategy', mode='compute'))
        # 效果账本选卡登记挂点(设计 §5.1「买卡=激活登记」
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
                _gs_reg = match.gs
                _nd = _gs_reg.node.value
                _t = ((_nd.plane - 1) * 9 + _nd.round_num
                      if _nd is not None else None)
                _gs_reg.effects.register_strategy(_spec, _t)
                # 桥·burst 形态(迁移批次三 B1,设计 §3.3.5/§5.1):登记
                # 时点把免费刷新 burst 额度一次性累加进余额(固定理财
                # 即时段 2 等;载体 = payload.free_refresh_burst,零额度
                # no-op)。每节点/容量两形态在 cw_loop tick 挂点,不经此。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    apply_effect_burst_grant,
                )
                apply_effect_burst_grant(
                    _gs_reg, _spec,
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
                    _gs_reg, _spec,
                    frame=f'p{_nd.plane}-r{_nd.round_num}'
                    if _nd is not None else '')
                if _rw is not None:
                    log.info(f'[cw-strat] 板面重写桥:{_rw.rewrite}'
                             f'(退款 {_rw.refund_gold}/清空域 '
                             f'{",".join(_rw.cleared_fields) or "无"})')
                log.info(f'[cw-strat] 效果账本登记:{_spec.name}(t={_t})')
        except Exception as e:   # noqa: BLE001  登记面失败不阻塞
            log.warning(f'[cw-strat] 效果账本登记失败(不阻塞): {e}')
        # 外部随机授予置闩(观察对账精确吸收的申报消费;申报表 =
        # cw_mismatch_policy.EXTERNAL_BENCH_GRANTS / EXTERNAL_EQUIP_GRANTS):
        # 卡文含「获得随机角色/随机装备」的投资卡(效果注册表未逐条确定;
        # 随机身份按 effect-domain §6.3 不建逻辑写端)确认后按申报表置入
        # 待吸收数,下一干净备战帧 bench/equips 观察对逻辑态纯超集时精确
        # 吸收(external_grant_absorbed 行),形状不符照真失配停。置闩收敛
        # kernel 单一源(幂等 + 闩龄上界住 kernel,与 CwScreenInvestEnv
        # 挂点同型同源,出处=改动三审 2026-09-18「置闩幂等化」;
        # 本挂点零本地逻辑)。best-effort 同登记挂点纪律。
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                latch_external_grants,
            )
            from sr_od.application.currency_war.kernel.cw_investments import (
                normalize_invest_name,
            )
            latch_external_grants(match.gs, normalize_invest_name(chosen),
                                  actor='CwScreenInvestStrategy')
        except Exception as e:   # noqa: BLE001  置闩失败不阻塞选卡主链
            log.warning(f'[cw-strat] 外部授予置闩失败(不阻塞): {e}')
        # (原 register_confirm_arrival('ConfirmStrategy') 已随 ADR-0651
        #  两态制废除:active_strategies 本体追加 + write_logic 直写均在
        #  上方确认成功写点,无挂账登记环节。)
