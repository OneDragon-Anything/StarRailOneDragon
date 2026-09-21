
"""货币战争 投资策略 3 选 1 op(两 node 直继承 SrOperation)。

观察 node = 入口锚复探窗(ADR-0529 有界自愈:复探窗内自愈、超窗
round_retry 消耗观察 node 预算)→ visit 起点单点复位已随防重入宿主
退役 → **一次读全**(3 张卡名 + 逐卡刷新剩余次数,零稳定帧等待——
用户裁定 2026-09-21「不要 1s 稳定帧」;读缺自愈 = 复探窗/外循环重派)
→ ``report_screen_invest_strategy_obs`` 落容器(候选 ``invest_strategy_
opts`` + 逐卡剩余 ``strategy_refresh_left`` 观察写端)→ obs 挂实例
属性。决策动作 node = 零参决策(候选自容器槽;空候选/无有效输出 =
round_fail 显式失败交外循环重派,fallback 盲发路径废除——裁定「没有
选到就是代码 bug」)→ 逐卡刷新终结交回 ∨ 选卡确认链经
``CwActionPickInvestOp`` 派发(pick-op-unify 批机械链迁入动作 op;
派发实例携归一名,词表 = CwActionPickInvestStrategyParam 屏别独立类)
→ **round_success 终结交回**(选完即交回外循环,用户裁定;确认未生效
= 代码 bug,归点击链可靠性治理,不设防重复/等待——action_ops.md §1
增补 2 即时上报契约)。

逐卡刷新 = 终结动作(用户裁定 2026-09-14,照投资环境屏同款形态):
``decide_event`` 帧级触发(零阈值结构判据,推导见 ADR-0600 §3.2.2 +
math_proofs P81)→ 返回 ``refresh_slots`` 非空 ∧ 逐槽余量闸(obs 携带
+ 容器 ``strategy_refresh_left`` 双闸,剩余 ≤0 = 尽)→ 文本锚定点刷新
圆钮一次 → 固定等待(机械时序,非判效)→ 本访问即终结交回(外循环重进
= 入口重建,新事实的观察与决策归重进的下一访问)。投资策略屏刷新是
**逐卡刷新**(每卡独立按钮、独立计数,归档帧对实证)。验效双通道已拆除
(用户裁定 2026-09-10;2026-09-14 收敛为零比对:访问内刷后不重读不比对
不重决策)。计数 = 屏上剩余次数观察真值(用户裁定:game state 记录画面
可观察的剩余次数),写端 = 观察 report 摄入,本 op 零计数写点。

形态(投资两屏迁移批):观察一次读全 + 即时上报 + 终结交回;选择事实
(active_strategies)经动作落地链写(动作 op 立即自上报 → gain_invest_
strategy 整链:无效载荷拒绝/持卡面按名字去重/效果账本登记腿/on_strategy_
gained 效果分派,正本 = game_state/gain-chain.md),画面 op 零选择写点。
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
    CwActionPickInvestStrategyParam,
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
        self._ocr_map: dict | None = None   # _read_options 存全图 OCR(采集复用,零额外 OCR)
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
        """入口锚复探窗 + 一次读全(观察轮读链)。零稳定帧等待(用户裁定
        2026-09-21);一次读全 = 卡名 OCR + 逐卡刷新剩余计数,同一帧读取,
        计数按 x 就近配对到槽(标准化转换住观察侧)。读缺 = 对应槽 None,
        由复探窗/外循环重派自愈;超窗 = entry_ok False(调用方 round_retry
        有界自愈,ADR-0529)。"""
        if not self._ensure_entry_screen():
            return CwScreenInvestStrategyObs(entry_ok=False, options=[])
        screen = self.screenshot()
        opts = self._read_options(screen)
        # 逐卡刷新剩余计数(与卡名同帧一次读全;x 就近配对到槽,读缺 = None)
        counts = read_invest_refresh_counts(self.ctx, screen, 'strategy')
        refresh_slots = (pair_refresh_counts_to_slots(
            counts, [x for _n, x, _y in opts]) if counts and opts
            else [None] * len(opts))
        return CwScreenInvestStrategyObs(entry_ok=True, options=opts,
                                         refresh_slots=refresh_slots,
                                         first_ocr_map=self._ocr_map,
                                         screen=screen)

    @operation_node(name='观察', is_start_node=True, node_max_retry_times=10)
    def observe(self) -> OperationRoundResult:
        """入口锚复探窗(ADR-0529 有界自愈)+ 一次读全 → report 落容器。

        超窗走 round_retry 而非 round_fail(二次治本,2026-09-06
        04:16:38 实证复探窗 3.2s 仍不够覆盖个别过渡段):retry 消耗
        观察节点 node_max_retry_times 预算有界自愈,且不产生 ERROR 行——
        round_fail 会炸出整 op 并触发哨兵报警退出(20-22 局实证
        每次 fail 一次哨兵退出)。在窗 → 一次读全 → ``report_screen_
        invest_strategy_obs`` 落容器(候选 + 逐卡剩余,match/gs 缺席的
        局外兜底路径跳过 report)→ obs 挂实例属性。"""
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
        """零参决策 → 逐卡刷新终结交回 / 点卡+确认后立即终结 → round_success。

        选卡链派发后本访问即终结交回外循环(选完即交回,用户裁定
        2026-09-21;确认未生效 = 代码 bug,overlay 残留由外循环按当前
        画面重识别重派,修法 = 点击链可靠性,action_ops.md §1 增补 2)。"""
        obs = self._obs
        return self._decide_and_act(obs)

    def _decide_and_act(self, obs: CwScreenInvestStrategyObs) -> OperationRoundResult:
        """决策+动作内聚体(决策面):零参决策(候选自容器槽)→ 逐卡刷新
        终结动作(obs 余量闸 + 容器剩余口径双闸)→ 选卡确认链派发(动作
        op 内即时上报)→ round_success 终结交回。空候选/决策无有效输出 =
        round_fail 显式失败(零盲发,裁定「没有选到就是代码 bug」)。"""

        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        opts = obs.options
        names = [n for n, _x, _y in opts]
        if not names:
            # 空候选 = OCR 读缺 = bug 面:显式失败交外循环重观察重派
            #(原 fallback(no-ocr) 盲点屏中路径废除——用户裁定 2026-09-21
            #「没有选到就是代码 bug,不做无畏补丁」;ADR-0529 复探窗已
            # 自愈过渡帧,此态 = 真读缺)。
            return self.round_fail('投资策略候选 OCR 读缺(零盲发,显式失败)')
        match = self.ctx.cw_match
        # 零参决策(写槽已由观察轮 report 落容器 invest_strategy_opts)。
        # 输出 = 单一 CwAction:CwActionRefreshInvestCardsParam(逐卡刷新
        # 建议)/ CwActionPickInvestStrategyParam(选卡)互斥单发。
        act = None
        refresh_slots: tuple[int, ...] = ()
        if match is not None:
            act = match.strategy.decide_invest_strategy()
        else:
            # 防御:无 match(局外独立跑)。decide_event 不读 hp/品质惩罚
            #(唯一局面消费 = board.value or {},未观察等价空表)。显式跳过
            # 刷新链(ADR-0600 §3.3 防御路径:局外防御帧零行为增量)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                GAME_STATE_SCHEMA_VERSION,
                GameState,
            )
            _kpick = decide_event(names, config,
                                  GameState(schema_version=GAME_STATE_SCHEMA_VERSION))
            act = CwActionPickInvestStrategyParam(idx=_kpick.option_idx,
                                                  reason=_kpick.reason)
        if isinstance(act, CwActionRefreshInvestCardsParam):
            refresh_slots = act.slots

        # ===== 逐卡刷新 = 终结动作(用户裁定 2026-09-14:点钮后本访问即
        # 终结交回,外循环重进后重观察重决策;闸门语义 = ADR-0600 §3.3
        # 逐卡预算;闸输入 = obs 携带 + 容器剩余口径,决策环零识别)=====
        if refresh_slots and match is not None:
            # 闸 2 读源 = 容器逐卡剩余(观察写端;键 = 规范卡名;≤0 = 尽;
            # 键缺失 = 该卡尚未观察过余量,由闸 1 现值裁决)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            _left_map = dict(game_state_of(
                match.session).strategy_refresh_left.value or {})
            for _i in refresh_slots:
                if _i >= len(opts):
                    continue
                # 闸 1:obs 逐槽余量(权威闸;None = 读缺 = 无授权失败安全)。
                _hit = (obs.refresh_slots[_i]
                        if _i < len(obs.refresh_slots) else None)
                if _hit is None or _hit[0] <= 0:
                    continue
                # 闸 2:容器剩余口径对照(≤0 = 尽)。
                _left = _left_map.get(normalize_invest_name(names[_i]))
                if _left is not None and _left <= 0:
                    continue
                # 闸 3:F2 唯一 L1 槽守卫(按当前名集现算,ADR-0600 §5)。
                _l1_now = [j for j, (_ex_flag, _b, _f, _t) in
                           enumerate(_guard_classify(n, config) for n in names)
                           if _ex_flag and not _b and not _f]
                if _l1_now == [_i]:
                    continue
                # 点钮:该槽「刷新次数N」文本中心 + 偏移(safe_click 带
                # bug#1 mouse_move 缓解,遭遇屏同款)。
                _tx, _ty = _hit[1], _hit[2]
                safe_click(self, Point(_tx + CwScreenInvestStrategy._REFRESH_BTN_DX, _ty),
                           tag='cw-strat')
                # 动画窗固定等待(机械时序,非判效)→ 终结交回:本访问
                # 零比对(刷后不重读不比对不重决策),选卡/确认均不在本
                # 访问;round_success 交回外循环重进 = 入口重建。
                time.sleep(CwScreenInvestStrategy.REFRESH_ANIM_WAIT_S)
                log.info(f'[cw-strat] 槽{_i}刷新终结交回:重进后重观察重决策')
                return self.round_success('投资策略刷新终结交回(重进重观察重决策)',
                                          wait=1)
            # 三闸全败(建议帧但无可执行刷新)→ 同访问重调落选卡:策略侧
            # 同帧去重(建议帧首调发建议、紧随重调落选卡),零选卡漂移。
            act = match.strategy.decide_invest_strategy()
            if isinstance(act, CwActionRefreshInvestCardsParam):   # 防御:策略未实现去重
                act = None

        # ===== 选卡确认链(派发即即时上报,本访问终结交回)=====
        if isinstance(act, CwActionPickInvestStrategyParam) and 0 <= act.idx < len(opts):
            chosen, choose_x, choose_y = opts[act.idx]
            reason = act.reason
            pick_idx = act.idx
        else:
            # 决策无有效选卡输出(策略器契约 = 恰一个动作;此态 = bug 面)
            # = 显式失败,禁盲点(原 fallback(no-decision) 盲点首卡路径废除)。
            return self.round_fail(f'投资策略决策无有效选卡输出: {act!r}')
        log.info(f'[cw-strat] options={names} chose={chosen!r}@({choose_x},{choose_y}) reason={reason}')
        # 未注册名告警(注册表只 T0 子集,数据缺口可见化,不阻塞)。
        for _c in opts:
            _n = _c[0]
            if _n not in ('?',) and get_strategy(_n) is None:
                log.warning(f'[cw-strat] 投资策略名不在注册表(数据缺口): {_n!r}')

        # 点最优卡的**卡名**选中(Y 从 screen_info「区域-卡名行」center 读;
        # 缺失兜底 CARD_CLICK_Y)+ 确认链经工厂派发(机械链 + 即时上报在
        # 动作 op 内:定位点/确认钮中心决策半现算经 env 显式传入)。
        _sel = area_center(self.ctx, '区域-卡名行', CwScreenInvestStrategy.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else CwScreenInvestStrategy.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenInvestStrategy.SCREEN_NAME) or CwScreenInvestStrategy.CONFIRM
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, idx=pick_idx, target=target,
                                  confirm=_confirm, entry_keyword='投资策略')
        action_op_for(CwActionPickInvestStrategyParam(
            idx=pick_idx, norm_name=normalize_invest_name(chosen)), self.ctx,
            _env).execute()
        # 本访问终结:结果已由动作 op 即时上报写入 game state(确认未生效
        # = 代码 bug,overlay 残留由外循环重识别重派,见类 docstring)。
        return self.round_success(f'{chosen} 已派发(结果即时上报)', wait=2.0)
