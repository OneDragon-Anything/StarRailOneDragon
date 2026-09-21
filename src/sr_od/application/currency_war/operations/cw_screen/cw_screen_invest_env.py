
"""货币战争 投资环境 3 选 1 op(两 node 直继承 SrOperation)。

观察 node = 入口门(标识-投资环境,miss = round_fail 交回外循环重判)
→ **一次读全**(3 张环境卡名 + 全局刷新剩余次数,零稳定帧等待——用户
裁定 2026-09-21「不要 1s 稳定帧」)→ ``report_screen_invest_env_obs``
落容器(候选 ``invest_env_opts`` + ``env_refresh_left`` 观察写端)→ obs
挂实例属性。决策动作 node = 零参决策(候选自容器槽;空候选/无有效输出
= round_fail 显式失败,零盲发)→ 环境帧刷新判据可发整组重掷(终结交回)
∨ 点**最优**卡底 + 确认链经 ``CwActionPickInvestOp`` 派发(词表 =
CwActionPickInvestEnvParam 屏别独立类)→ **round_success 终结交回**
(选完即交回外循环,用户裁定;确认未生效 = 代码 bug,overlay 残留由
外循环按当前画面重识别重派,修法 = 点击链可靠性——action_ops.md §1
增补 2 即时上报契约)。

环境刷新 = 终结动作(用户裁定 2026-09-14:刷新 = 唯一引入新事实的动作,
须交回外循环重观察;结构语义 = screens/op-layer.md §1.4):决策返回
``refresh_slots`` 非空 ∧ 剩余次数授权(obs 携带 + 容器 ``env_refresh_
left``)→ 点刷新圆钮一次(文本锚定偏移)→ 动画窗固定等待 → 零效果缺陷
留证对账 → 本访问即终结交回。

选择事实(active_env)经动作落地链写:动作 op 确认后立即自上报 →
``gain_invest_env`` 整链(active_env 注册 + portal 登记 + on_env_gained
效果枚举,正本 = game_state/gain-chain.md);画面 op 零选择写点。计数 =
屏上剩余次数观察真值(用户裁定),写端 = 观察 report 摄入。
本屏 sim 腿 = 不适用(sim 端口适配器未建),等价判据主承重 = 实机在册
行为锁。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_events import decide_event
from sr_od.application.currency_war.kernel.cw_investments import (
    is_known_env,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.invest_env import (
    CwScreenInvestEnvObs,
    report_screen_invest_env_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickInvestEnvParam,
    CwActionRefreshInvestCardsParam,
)
from sr_od.application.currency_war.obs.cw_node_obs import read_invest_refresh_counts
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenInvestEnv(SrOperation):
    """投资环境 3 选 1:OCR 卡名 → decide_event 打分 → 点最优卡底 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-投资环境'   # screen_info 画面(currency_war_invest_env.yml)
    # 卡选中点击 Y:screen_info「区域-卡牌描述行」center.y;常量=screen_info 缺失兜底。
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
    # 确认按钮:screen_info「按钮-确认」center;常量=兜底。
    CONFIRM: ClassVar[Point] = Point(1082, 982)   # 兜底;首选 area_center('按钮-确认')
    # ---- 环境刷新执行链常量(3.8;执行层时序/几何常量,非策略数值,
    # ADR-0529 先例)----
    # 刷新圆钮 = 「剩余次数」文本中心 + 固定偏移(文本锚定,ADR-0600 §3.4 先例
    # ——单帧证据不足判文本漂移形态,固定 area 不可行;遭遇屏/策略屏同款)。
    # 偏移实测收口(归档帧 sr-od-test/screens/货币战争-投资环境/default.webp
    # 亮像素簇质心:钮心 x≈671、计数文本中心 x≈772,y 同带 ≈983)→ dx ≈ −101。
    # 偏移错 → 刷新未命中(计数不扣、牌不变):零效果只落缺陷台账留证;
    # 重进后计数未扣、预算仍在 → 再次刷新,每圈耗 1 次外环重进,能力退化
    # 非事故,复测即修。
    _REFRESH_BTN_DX: ClassVar[int] = -101
    # 刷新后等待(整组重掷动画覆盖;沿策略屏 REFRESH_ANIM_WAIT_S 同值先例)。
    REFRESH_ANIM_WAIT_S: ClassVar[float] = 1.5

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资环境')
        # 刷新零效果留证证据(批4 比对收口:刷新臂只读不比,读数原样
        # 携带——元组 = (刷前计数, 刷前名集, 刷后计数, 刷后名集);
        # 消费点 = 刷新臂终结交回出口 ``_reconcile_refresh_no_effect``,
        # 消费即清;None = 无待评证据)。
        self._refresh_evidence: tuple[int, list[str],
                                      list, list[tuple[str, int]]] | None = None
        # 观察结果(观察 node 产物,决策动作 node 消费)。
        self._obs: CwScreenInvestEnvObs | None = None

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

    def _match_gs(self):
        """局容器单例读口(无局/局外兜底路径 = None,调用方零行为跳过)。"""
        _match = getattr(self.ctx, 'cw_match', None)
        return getattr(_match, 'gs', None) if _match is not None else None

    def _reconcile_refresh_no_effect(self) -> None:
        """刷新零效果留证对账(消费点 = 刷新臂终结交回出口):携带证据
        (刷前计数/名集 + 刷后帧机械重读)在此评「计数未扣 ∧ 名集未变」→
        落缺陷台账(零决策零改道);任一侧读缺 = 过渡帧不可判,不猜。
        消费即清(每次刷新恰评一次)。缺陷的实际触发形态 = 刷新未生效而
        overlay 残留——证据为当次刷新的机械重读快照,评点住终结交回出口
        与该形态覆盖面等价(每笔证据恰评一次)。"""
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
                     '比对宿主 = 刷新臂终结交回出口(批4 比对收口)',
                gap_large=False,
                severity=cw_defects.SEVERITY_L2_RECORD)
        except Exception:   # noqa: BLE001  留证不阻塞交回
            pass

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + 一次读全 → report 落容器。

        门 miss = round_fail 早退交回外循环重判(现役首闸同 status)。
        零稳定帧等待(用户裁定 2026-09-21);一次读全 = 环境卡名 + 全局
        刷新剩余计数,同一帧读取。门后 report 摄入(候选 + env_refresh_
        left,match/gs 缺席的局外兜底路径跳过 report)。"""
        screen = self.last_screenshot
        _hit = self.round_by_find_area(screen, CwScreenInvestEnv.SCREEN_NAME,
                                       '标识-投资环境').is_success
        log.info(f'[cw-env] enter find_area(标识-投资环境)={_hit}')
        if not _hit:
            return self.round_fail('非投资环境屏')
        screen = self.screenshot()
        counts = read_invest_refresh_counts(self.ctx, screen, 'env')
        obs = CwScreenInvestEnvObs(
            hit=True,
            options=self._read_options(screen),
            refresh=(counts[0] if counts else None),
            screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_invest_env_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=10)
    def act(self) -> OperationRoundResult:
        """零参决策 → 环境刷新终结交回 / 选卡+确认后立即终结 → round_success。

        选卡链派发后本访问即终结交回外循环(选完即交回,用户裁定
        2026-09-21;确认未生效 = 代码 bug,overlay 残留由外循环按当前
        画面重识别重派,修法 = 点击链可靠性,action_ops.md §1 增补 2)。"""
        obs = self._obs
        return self._decide_and_act(obs)

    def _decide_and_act(self, obs: CwScreenInvestEnvObs) -> OperationRoundResult:
        """决策+动作内聚体(决策面):零参决策(候选自容器槽;空候选 =
        round_fail 显式失败,零盲发)→ 环境刷新终结动作(obs 余量授权 +
        容器 env_refresh_left)→ 点最优卡底 → 确认链派发(动作 op 内
        即时上报)→ round_success 终结交回。"""

        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        opts = obs.options
        names = [n for n, _ in opts]
        if not names:
            # 空候选 = OCR 读缺 = bug 面:显式失败交外循环重观察重派
            #(零盲发,用户裁定 2026-09-21「没有选到就是代码 bug」)。
            return self.round_fail('投资环境候选 OCR 读缺(零盲发,显式失败)')
        for _n in names:
            if not is_known_env(_n):
                log.warning(f'[cw-env] 投资环境名不在注册表(数据缺口): {_n!r} → 该项 env_fit 走中性 fallback')
        match = self.ctx.cw_match
        # 零参决策(写槽已由观察轮 report 落容器 invest_env_opts)。
        # 输出 = 单一 CwAction:CwActionRefreshInvestCardsParam(整组刷新
        # 建议)/ CwActionPickInvestEnvParam(选卡)互斥单发。
        act = None
        refresh_slots: tuple[int, ...] = ()
        if match is not None:
            act = match.strategy.decide_invest_env()
        else:
            # 防御:无 match(局外独立跑)——防御空容器直喂(容器签名)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                GAME_STATE_SCHEMA_VERSION,
                GameState,
            )
            _kpick = decide_event(names, config,
                                  GameState(schema_version=GAME_STATE_SCHEMA_VERSION))
            act = CwActionPickInvestEnvParam(idx=_kpick.option_idx,
                                             reason=_kpick.reason)
        if isinstance(act, CwActionRefreshInvestCardsParam):
            refresh_slots = act.slots
        # ===== 环境刷新 = 终结动作(用户裁定 2026-09-14:刷新 = 唯一引入
        # 新事实的动作,须交回外循环重观察;环境屏 = 整组重掷:单全局钮 +
        # 单计数。闸输入 = obs.refresh(同帧一次读全,决策环零识别)+
        # 容器 env_refresh_left;读缺 = 无授权失败安全)=====
        if refresh_slots and match is not None and obs.refresh is not None:
            _budget, _tx, _ty = obs.refresh
            # 闸:容器剩余口径对照(≤0 = 尽;键缺失由 obs 现值裁决)。
            _mgs = self._match_gs()
            _left = (_mgs.env_refresh_left.value
                     if _mgs is not None else None)
            if _budget > 0 and not (_left is not None and _left <= 0):
                # 点钮:「剩余次数」文本中心 + 固定偏移(safe_click 带
                # bug#1 mouse_move 缓解)。
                safe_click(self,
                           Point(_tx + CwScreenInvestEnv._REFRESH_BTN_DX, _ty),
                           tag='cw-env')
                # 动画窗固定等待(整组重掷动画覆盖;机械执行时序,非判效)。
                time.sleep(CwScreenInvestEnv.REFRESH_ANIM_WAIT_S)
                # 刷后帧机械重读(零比对零判效——读数原样携带进留证证据,
                # 「计数未扣 ∧ 名集未变」的零效果判定经对账评点落缺陷台账;
                # 判效权归对账)。
                _after = self.screenshot()
                _counts2 = read_invest_refresh_counts(self.ctx, _after, 'env')
                _opts2 = self._read_options(_after)
                self._refresh_evidence = (
                    _budget, [n for n, _ in opts], _counts2, _opts2)
                log.info(f'[cw-env] 环境刷新终结交回:计数 {_budget}→'
                         f'{_counts2[0][0] if _counts2 else "读缺"},'
                         f'重进后重观察重分类')
                # 零效果留证对账(消费即清)→ 终结交回:选卡/确认均不在
                # 本访问;外循环重进 = 入口重建。
                self._reconcile_refresh_no_effect()
                return self.round_success('投资环境刷新终结交回(重进重观察重分类)',
                                          wait=1)
            # 闸全败(建议帧但计数无授权)→ 同访问重调落选卡:策略侧同帧
            # 去重(建议帧首调发建议、紧随重调落选卡),零选卡漂移。
            act = match.strategy.decide_invest_env()
            if isinstance(act, CwActionRefreshInvestCardsParam):   # 防御:策略未实现去重
                act = None
        # ===== 选卡确认链(派发即即时上报,本访问终结交回)=====
        if isinstance(act, CwActionPickInvestEnvParam) and 0 <= act.idx < len(opts):
            chosen, choose_x = opts[act.idx]
            reason = act.reason
            pick_idx = act.idx
        else:
            # 决策无有效选卡输出 = bug 面:显式失败(零盲点)。
            return self.round_fail(f'投资环境决策无有效选卡输出: {act!r}')
        log.info(f'[cw-env] options={names} chose={chosen!r}@x={choose_x} reason={reason}')
        # 选择事实零容器写(active_env 注册在动作落地获得链 gain_invest_env,
        # 动作 op 即时上报;正本 = game_state/gain-chain.md)。

        # 点最优卡底(Y 从 screen_info「区域-卡牌描述行」center 读;缺失兜底
        # CARD_CLICK_Y)+ 确认链经工厂派发。
        _sel = area_center(self.ctx, '区域-卡牌描述行', CwScreenInvestEnv.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else CwScreenInvestEnv.CARD_CLICK_Y
        target = Point(choose_x, _click_y)

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

        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenInvestEnv.SCREEN_NAME) or CwScreenInvestEnv.CONFIRM
        _env = OverlayPickExecEnv(op=self, idx=pick_idx, target=target,
                                  confirm=_confirm, entry_keyword='投资环境')
        action_op_for(CwActionPickInvestEnvParam(
            idx=pick_idx, norm_name=normalize_invest_name(chosen)), self.ctx,
            _env).execute()
        # 本访问终结:结果已由动作 op 即时上报写入 game state(active_env
        # 注册 + 赠卡效果;确认未生效 = 代码 bug,见类 docstring)。
        return self.round_success(f'{chosen} 已派发(结果即时上报)', wait=2.0)
