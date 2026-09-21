"""货币战争 战斗等待 op(W971 05-battle §1;P4 收编)。

接 「出战 op 交回循环」之后的战斗/结算窗口:等结算画面 → 结算处理(遥测读点 →
点「继续挑战」)→ 完成判据白名单任一出现(备战系/补给/遭遇/投资策略/强敌来袭/
位面过渡锚)→ round_success 交回主循环分发;「前往结算」链的团灭终局(多页 →
返回货币战争 → 大厅)= 第三出口,round_success(status='terminal_lobby') 交整局
退出(主循环 3c 收口)。决策 why 归 git 历史(战斗等待 op 期望态接线;接线语义见下)。


结构判据(od-dev-write-operation「循环驱动玩法」):本 op = node-per-op 的
**逻辑单元生命周期 owner**——战斗+结算是一个单元(开始=出战,结束=白名单锚/
团灭终局),单元内多阶段(等待/页1 动画/结算页/败局链),节点作用域预算 =
未知帧 bail 上界 + 出战宽限(ADR-0250)收编。外循环只回答「在不在战斗窗口」
(驻留闩 + 帧锚双入口),不进单元内部分类。

收编来源(cw_loop 分支随迁;语义逐条保真,遥测写端调用原样平移):
- 分支 1f(失败结算页:进度符号闩/面板延迟门/页1 三项暂存/败局补录/翻页);
- 分支 2(「点击空白加速」页1 动画帧:progress/三项暂存 + 点空白加速);
- 分支 3(挑战成功结算:读点前等 1.5s(#25 用户裁定)/C-1 新帧计数/
  M39 长按兜底/备战相位机复位);
- 分支 3b(前往结算链:前往结算/下一页/下一步/返回货币战争 + 挑战失败
  hp=0 补录);
- 分支 6(战斗/过场屏总伤害/数据统计 → 点空白推进)。

遥测连续性红线(W971 05-battle §1):观察半直写/结算链内存轨迹照旧维持;
判读连续性由 journal 行与冻结档案承载。

自动战斗检测(W971 05-battle §2;已落地):①段(等结算画面)轮询消费
「自动战斗未开启」信号(画面右下角「我方行动中」待操作帧,连续 ~5s
双锚)→ 点「按钮-自动战斗开关」自愈;判据与判效边界随分支实现注释,
语义申报 = screens/battle_wait.md 开放设计注③。

统一观察架构逐屏迁移(五相位屏;用户裁定豁免):本屏 = **驻留状态机**
(内部 while 处理结算帧,round_wait 逐轮分类),「观察 node + 决策动作
node」两段形态不适配——出口判定(大厅终局锚/完成白名单)与分支链在
单 node 内逐轮重判,拆两 node 会把出口判定与分支序的轮次耦合切开。
本批只做:直继承 SrOperation、基类挂接/适配器/五段方法/装配点分流
随基类退役删除;内部结算链(settlement 页循环/_write_settlement_
observation/apply_settlement_cover/SettlementState)逐位零改动。
驻留形态豁免经用户裁定;kernel/cw_screen_report/battle_wait
保持占位(零 op 层观察容器写点)。结构参数:SettlementState 跨局状态机
注入(``__init__(ctx, st, config)``,RunLoop 持有)不变;
``node_max_retry_times=400`` 归节点不变。本屏 sim 腿 = 不适用(F11 例外
清单:sim 事实来源为 coarse 结算产出非画面段),等价判据主承重 = 实机
在册行为锁经 execute()/wait() 单路径全绿。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
    SEVERITY_L1_ALERT,
    journal_refs,
)
from sr_od.application.currency_war.obs.cw_observation import read_phase_round
from sr_od.application.currency_war.obs.cw_settlement_obs import (
    parse_progress_fill_ratio,
    parse_settlement_progress,
    parse_settlement_round,
    read_round_outcome,
    read_settle_damage_breakdown,
    settle_page1_progress_sign,
)
from sr_od.application.currency_war.telemetry import defects
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_performance import (
        RoundOutcome,
    )
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )


def _write_settlement_observation(session: StrategySession,
                                  obs: RoundOutcome) -> None:
    """结算观察半直写(ADR-0583 §2.5:旧 on_round_end 观察段收编的单一写点)。

    现役 = performance.record(streak/hp/gold/level 真值链已由结算覆盖写端
    直入容器 gs:streak_after 带符号;终态契约 §B:last_streak session 份
    退役)。独立成模块级函数:被测面 = 纯写点(观察层产物),单测直调即经
    生产链路(op 回路是唯一调用方)。
    """
    session.performance.record(obs)


#: 战斗窗覆盖度守卫的窗口单元出口集(bail 不计:帧锚可重入续同窗,计则
#: 假阳——同一 battle_ts 的后续窗观测落地后锚即匹配;bail 形态自有
#: op 截图留证(prefix=battle_wait_bail)+ 未知兜底链留证暴露,不依赖本守卫)。
_COVERAGE_EXIT_STATUSES: frozenset[str] = frozenset(
    {'back_to_loop', 'terminal_lobby'})


def count_settlement_obs_coverage_miss(st: SettlementState,
                                       exit_status: str) -> bool:
    """战斗窗 exit 结算观测覆盖度守卫(战斗链收口守卫面)。

    调用方 = cw_loop ``_on_battle_wait`` 出口归一点(旧路径/五段路径共用
    同一收口);本函数只判不抛,异常面由 record_defect 自身 best-effort 承担。

    背景:长战斗形态整窗零「结算观测」行实锤(2026-09-15 局深检
    .debug/currency_war/deep_review/run_20260915_054718.md §8-1:488s
    主战 hp 3→0 扣血链零观测,复盘断节不可知),需求 = 覆盖度可观测防
    复发。形态 = 只计数留证(缺陷台账 L1 行),不新增停机(安灯停线已退役,
    停机处置归框架 stop_running)。

    判定:窗口单元 success 出口(白名单命中 back_to_loop / 团灭终局
    terminal_lobby)+ 出战开窗在(battle_ts 非 None = RunLoop 出战开窗点
    注入)+ 本窗零结算观测行(settled_battle_ts ≠ battle_ts,同源
    monotonic 锚比较)→ 落一行 L1 台账行。

    边界:接管局/残留屏经帧锚入窗无出战锚(battle_ts=None)不计——无窗
    开锚不成窗,该形态由残留屏判据与未知兜底链自证;telemetry-only 败局
    补录行同样刷新窗锚(结算观测行含败局链,覆盖率口径与判读一致)。

    Returns:
        是否落了覆盖度缺失行(测试断言面;生产消费 = 台账行本身)。
    """
    if exit_status not in _COVERAGE_EXIT_STATUSES:
        return False
    if st.battle_ts is None or st.settled_battle_ts == st.battle_ts:
        return False
    defects.record_defect(
        'settlement', 'settle_obs_coverage_miss',
        expected='战斗窗全程 ≥1 条「结算观测」行(胜负/扣血真值链在案)',
        observed='战窗 exit 零结算观测行(胜负与扣血零观测,伤害链断节'
                 '复盘不可知)',
        verdict=('留证-结算观测覆盖度缺失(只计数不停机;处理:按窗锚'
                 ' battle_ts 对 journal/op 行定位漏读窗,结算识别失准走'
                 '识别优化批)'),
        refs=journal_refs(),
        reader_source='battle_wait_exit',
        gap_large=True,
        severity=SEVERITY_L1_ALERT,
        note='覆盖度检测 = 战窗 exit 守卫面;正常结算/败局补录行恒刷新'
             '窗锚,本行 = 真缺失(非识别噪声)')
    return True


@dataclass
class SettlementState:
    """战斗/结算链跨迭代状态机(原 cw_loop 散挂属性收拢;随迁不改语义)。

    [字段定义] 生命周期 = 每局(handle_init 随 RunLoop 新建),不是每场战斗
    ——页间暂存/防重指纹都是「本局内跨场」语义(残留屏判定/败局页防重按局
    记忆)。坐标系:
    - last_outcome_hp = outcomes 内存轨迹末条真 hp(summary final_hp 真值源;
      conf≥0.9 才更新,r3 live 修);
    - saw_defeat_settlement = 败局闩:本局见过任一显式败局结算帧
      (3c 假 win 守卫消费);
    - last_outcome_t = 上一结算真值轮全局节点号(killed hp 对比兜底的轮次
      邻接门);
    - rounds_done = 已完成战斗轮数(C-1 新结算帧计数;轮锚点 = 挑战成功结算);
    - settle_page1_progress / settle_page1_settle = 结算页1 三项遥测暂存
      (页2 记录时合并消费,用后清);
    - settle_p1_ts = 结算页1 面板渲染延迟门计时(SETTLE_PANEL_WAIT_S);
    - last_settle_fp / last_loss_fp = 同屏指纹防重(C-1 计数/败局行防重);
    - auto_off_first_ts = 自动战斗未开检测首见时刻(连续 ~5s 待操作双锚命中
      才判未开并点击开关;防技能演出相似视觉单帧误判);
    - first_settlement_seen / run_start_ts / is_new_match = relaunch 残留
      结算屏判据三件(迁移审计 w28;run_start_ts/is_new_match 由 RunLoop
      handle_init 注入);
    - battle_ts = 出战时刻(RunLoop ADR-0250 战斗窗口开窗点注入;op 据此
      判「战斗进行中合法静止」宽限);
    - saw_settlement = 本窗口已见结算屏(RunLoop 据此关战斗 watch 宽限);
    - settled_battle_ts = 结算观测窗锚:最近一次「结算观测」行落点时点的
      battle_ts 快照(坐标系 = battle_ts 同源 monotonic 时钟;取值时机 =
      _record_round_outcome 行写点写入,含 telemetry-only 败局补录行)。
      战斗窗 exit 覆盖度守卫据此判「本窗(出战开窗)全程零结算观测行」:
      ≠ 当前 battle_ts 即本窗未写过行(battle_ts None 时本字段无比较语义,
      守卫不触发)。
    """
    last_outcome_hp: int | None = None
    saw_defeat_settlement: bool = False
    last_outcome_t: int | None = None
    rounds_done: int = 0
    settle_page1_progress: int | None = None
    settle_page1_settle: dict = field(default_factory=dict)
    settle_p1_ts: float | None = None
    # 页1 暂存所属战斗窗标记(= 填充时点的 battle_ts;消费时同窗才取用——
    # 跨窗滞留即弃,防上一场页1 暂存污染下一场结算行)
    settle_p1_battle_ts: float | None = None
    last_settle_fp: tuple | None = None
    last_loss_fp: tuple | None = None
    auto_off_first_ts: float | None = None   # 自动未开检测首见时刻(见类头字段表)
    first_settlement_seen: bool = False
    run_start_ts: float = 0.0
    is_new_match: bool = True
    battle_ts: float | None = None
    saw_settlement: bool = False
    settled_battle_ts: float | None = None


class CwScreenBattleWait(SrOperation):
    """战斗等待 op:等结算 → 结算处理 → 白名单完成判据 / 团灭终局分叉。"""

    #: 结算页1 掉血说明 tooltip 渲染延迟门(随迁自 cw_loop,注释原文见
    #: 该处 git 历史):面板进页 ~2-4s 才出现;门语义 = 面板 visible 或超时
    #: 才放行推进。超时兜底覆盖胜轮(面板整块不出现,帧实证)。
    SETTLE_PANEL_WAIT_S: ClassVar[float] = 4.0
    #: 败局闩次级证据裁决的轮次下限(二轮审计裁决 5,随迁):
    #: t = (plane-1)*9+round 过中位 + 面板负分量 双证据才置闩。
    SETTLE_DEFEAT_LATCH_MIN_T: ClassVar[int] = 14
    #: relaunch 残留结算屏判据宽限(随迁自 cw_loop RELAUNCH_SETTLE_GRACE_S)。
    RELAUNCH_SETTLE_GRACE_S: ClassVar[float] = 30.0
    #: 出战宽限(ADR-0250 随迁口径):战斗进行中合法静止,不进未知帧计数。
    BATTLE_WATCH_GRACE_S: ClassVar[float] = 600.0
    #: 未知帧 bail 上界(节点作用域预算;超限 = 留证 + bail 交主循环未知
    #: 画面分支,W971 05-battle §1 超时兜底)。战斗特效长帧期宽限已由
    #: BATTLE_WATCH_GRACE_S 挡在计数外,本值只辖「结算后卡死」形态。
    UNKNOWN_BAIL_N: ClassVar[int] = 10
    # 点空白区(加速战斗/关叠层;避开中央内容;随迁自 cw_loop.BLANK)
    BLANK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)
    # (M39 长按兜底专用点/停留阈值与结算点击、证据等待、推进上报一并
    #  迁入 CwOpSettleConfirm,迭代 2026-09-20-node-advance-action-report
    #  landing §3.2;本类仅保留结算链记(读点/_record_round_outcome/
    #  rounds_done 计数,攻击 B2 归属界定)。)

    def __init__(self, ctx: SrContext, st: SettlementState,
                 config: CurrencyWarConfig):
        SrOperation.__init__(self, ctx, op_name='货币战争-战斗等待')
        self._st = st
        self._cw_config = config
        self._unknown_streak: int = 0

    # ===== ①段:等结算画面 =====
    #
    # 自动战斗检测(W971 05-battle §2;已落地):战斗进行中宽限轮询处
    #(下方 _in_battle_grace 分支)是本检测的消费点——「我方行动中」
    # 待操作帧连续 ~5s 双锚命中 → 点「按钮-自动战斗开关」自愈
    #(实现见自动战斗检测段)。

    def _in_battle_grace(self, now: float) -> bool:
        """战斗进行中宽限判定(ADR-0250 随迁):未见过结算屏且出战未超
        宽限 → 合法静止,不进未知帧计数。"""
        return (not self._st.saw_settlement
                and self._st.battle_ts is not None
                and now - self._st.battle_ts < CwScreenBattleWait.BATTLE_WATCH_GRACE_S)

    # ===== ③段:完成判据白名单(W971 05-battle §1 裁决集)=====
    # 白名单语义 = 「已回备战系画面」的到达判定(宽;面板就位判定由循环
    # 判定序承接,不在本 op 承诺内——05-battle §1 架构修正条)。位面简报
    # 不在切换链上(仅入场出现一次,用户裁决 2026-09-02),不列。
    # 判定本体迁出为共用 helper(结算确认 op 转移证据与本品出口同一源,
    # design §2.3 证据集同源条款/攻击 R3;锚表见 cw_op_settle_confirm)。

    def _hit_completion_anchor(self, screen) -> bool:
        """完成判据白名单任一命中(纯判定,单一源委托;语义详见
        :func:`cw_op_settle_confirm.hit_settle_completion_anchor`)。"""
        from sr_od.application.currency_war.operations.cw_op.cw_op_settle_confirm import (
            hit_settle_completion_anchor,
        )
        return hit_settle_completion_anchor(self, screen)

    def _cw_selection_write(self, session: StrategySession,
                            obs: RoundOutcome, plane: int, round_num: int,
                            node_type: str, *, residual: bool) -> str:
        """结算行入环(E-2 观测面单一写端;调用位 = _record_round_outcome 环写位)。

        difficulty_node 装填双态(拨盘 = kernel D_ENC_VARIANT,定谳前 None):
        普战行恒 live 门(observation 态 ∧ 非空);遭遇行 (i) = observation 态、
        (ii) = observation/carried 自证态(简报值无容器入口,自证链封闭)。
        encounter_tier = 遭遇行取 chosen_encounter 落点档(选择落地写入先于
        结算)。残留行不入环(旧局键,跨局污染排除)。归因串返回留痕。"""
        from sr_od.application.currency_war.kernel.cw_encounter_selection import (
            D_ENC_VARIANT,
            record_settlement_row,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            gs_of_ctx,
        )
        gs = gs_of_ctx(None, session)
        _f = gs.enemy_difficulty
        _val, _src = _f.value, _f.source
        diff = None
        tier = None
        if _val is not None and node_type != "遭遇":
            if _src == "observation":
                diff = float(_val)
        elif _val is not None:
            if D_ENC_VARIANT == "i":
                diff = float(_val) if _src == "observation" else None
            elif D_ENC_VARIANT == "ii":
                diff = (float(_val) if _src in ("observation", "carried")
                        else None)
            _chosen = gs.chosen_encounter.value
            if isinstance(_chosen, tuple) and _chosen:
                try:
                    tier = int(_chosen[0])
                except (TypeError, ValueError):
                    tier = None
        return record_settlement_row(gs, obs, plane=plane,
                                     round_num=round_num, node_type=node_type,
                                     difficulty_node=diff,
                                     encounter_tier=tier, residual=residual)

    def _cw_selection_capture(self, session: StrategySession,
                              obs: RoundOutcome, plane: int, round_num: int,
                              node_type: str, *, suppressed: bool = False) -> None:
        """E-3 对账落盘 hook(缺省关;启用点 = E-3 标定采集显式接通)。

        对账数据源 = 环写位同点 hook 全量落盘序列(含 W239 抑制行留痕标记;
        非运行时环 dump——环旋转会制造假缺行)。本批只钉点位,零副作用;
        落盘件格式与启用开关随 E-3 标定批采集协议一并定。"""
        return None

    # ===== 结算链遥测(自 cw_loop 原样平移;写端调用零变更)=====

    def _record_round_outcome(self, screen, telemetry_only: bool = False) -> None:
        """P1.5 观测回路:结算屏 → read_round_outcome → 观察半直写 + 策略半入槽。

        (自 cw_loop._record_round_outcome 平移;方法级注释与判定链逐条
        保真,详见原处 git 历史。差异仅两处载体:循环态挂 SettlementState、
        ADR-0250 窗口关由 saw_settlement 承载。)
        **ADR-0583 拆两半**:策略生命周期钩子 on_round_end 删除后,本回路
        直接承担观察半——结算真值观察(performance.record)在结算点即时
        直写(写点与原 on_round_end 同点同时序,performance.history 无缺行
        窗口);策略半(pending_round_outcomes 入槽)已随终态契约 §B 删
        (消费侧 drain 退役,ADR-0638)。telemetry-only 面(败局页补录)
        不写任何一侧。
        """
        if self.ctx.cw_match is None:
            return
        if not telemetry_only:
            self._st.saw_settlement = True   # ADR-0250:见结算屏 → 窗口关
        _st = self._st
        # 残留判定与 telemetry_only 解耦(两路同源):判定值来自结算处理入口
        # 恰一次调用(首见副作用,环写位禁二次调用),1f/3b/胜局三路的残留行
        # 排除共用本值。
        _residual = self._mark_relaunch_residual()
        # (_source 行来源标记(''/'recovered'/'loss_page')随 outcomes 流写入端
        #  退役删除——删除波 1;_residual 残局判定保留,消费方 = 下方 plane
        #  归属校正分支。)
        try:
            _session = self.ctx.cw_match.session
            _plane, _round = read_phase_round(self.ctx, screen)
            _ocr_texts = [r.data for r in self.ctx.ocr_service.get_ocr_result_list(
                image=screen, rect=None, color_range=None, crop_first=False)]
            # plane 归属修复(W239):结算屏头部「X-Y」屏面真值 + 单调门,
            # 逻辑原样平移(注释详见原处)。
            _scr = parse_settlement_round(_ocr_texts)
            if _scr is not None:
                if _residual:
                    log.warning('[cw][bwait] relaunch 残留结算屏:round 按「%s-%s」校正'
                                '(原兜底 P%s-r%s)', _scr[0], _scr[1], _plane, _round)
                    _plane, _round = _scr
                else:
                    _t_new = (_scr[0] - 1) * 9 + _scr[1]
                    _t_old = (_plane - 1) * 9 + _round if (_plane and _round) else None
                    if _t_old is None or _t_new >= _t_old:
                        if (_scr[0], _scr[1]) != (_plane, _round):
                            log.info('[cw-bwait] plane/round 结算屏真值「%s-%s」覆盖 '
                                     'last-known「%s-%s」(W239)', _scr[0], _scr[1],
                                     _plane, _round)
                            defects.record_defect(
                                'phase_round', 'perception_conflict',
                                expected=f'备战缓存 {_plane}-{_round}',
                                observed=f'结算屏 {_scr[0]}-{_scr[1]}',
                                plane=_plane, round_num=_round,
                                verdict='留证-结算屏真值覆盖 last-known',
                                reader_source='settlement_vs_prep_round',
                                gap_large=False, auto_resolved=True,
                                # refs 旧挂点清理(W7 refs 迁移):outcomes
                                # 流已退役,改指 journal (run_id,v) 锚。
                                refs=journal_refs(),
                                note='观测自检框架设计 §2.7:同轮双读不等留证;'
                                     '残留屏豁免')
                        _plane, _round = _scr
                    else:
                        log.warning('[cw-bwait] 结算屏「%s-%s」落后 last-known「%s-%s」'
                                    '= OCR 假阳 → 拒(W239 单调门)',
                                    _scr[0], _scr[1], _plane, _round)
                        defects.record_defect(
                            'phase_round', 'perception_conflict',
                            expected=f'备战缓存 {_plane}-{_round}',
                            observed=(f'结算屏 {_scr[0]}-{_scr[1]}(落后 last-known'
                                      '=OCR 假阳,单调门拒)'),
                            plane=_plane, round_num=_round,
                            verdict='留证-结算屏读数落后 last-known 判 OCR 假阳拒',
                            reader_source='settlement_vs_prep_round',
                            gap_large=False, auto_resolved=True,
                            # refs 旧挂点清理(W7 refs 迁移):outcomes 流
                            # 已退役,改指 journal (run_id,v) 锚。
                            refs=journal_refs(),
                            note='观测自检框架设计 §2.7;残留屏豁免')
            # 披露面防御 getattr(strategy_state_of None 契约,ADR-0563 B4 划分线):
            # 异型状态对象字段缺席退 '?'(outcomes comp_tag 缺席语义,非行为面)
            _tc = getattr(strategy_state_of(_session), 'target_comp', None)
            _comp_tag = _tc.name if _tc is not None else '?'
            _is_boss = self.round_by_find_area(
                screen, '货币战争-结算', '标识-首领').is_success
            from sr_od.application.currency_war.kernel.cw_game_state import (
                gs_of_ctx,
                node_kind_of,
            )
            # node 优先序:首领识别锚(画面位) > gs 推导(终态契约 §A′,
            # session 识别源退役) > 探针表(§A′ 重锚面,宿主迁移另子件) > 缺省。
            _node = 'boss' if _is_boss else self._normalize_node_type(
                node_kind_of(gs_of_ctx(self.ctx, _session))
                or self._node_type_from_table(_session, _plane, _round)
                or '普通战斗')
            _obs = read_round_outcome(self.ctx, screen, plane=_plane, round_num=_round,
                                      comp_tag=_comp_tag, node_type=_node)
            if telemetry_only and _obs.killed is not False:
                log.info('[cw-bwait] loss_page 行不落:killed=%s 非显式败局(W239)',
                         _obs.killed)
                # 守卫抑制形态:不入环(W239 防毒设计保留);E-3 对账 hook 在
                # 环写位同点上游括守卫两臂,抑制行以留痕标记进落盘序列。
                self._cw_selection_capture(_session, _obs, _plane, _round,
                                           _node, suppressed=True)
                return
            # r68 页1 progress 合并(暂存源 = SettlementState)
            if _obs.progress_delta is None:
                _pg1 = _st.settle_page1_progress
                if _pg1 is not None and _st.settle_p1_battle_ts == _st.battle_ts:
                    _obs.progress_delta = _pg1
                    log.info('[cw-bwait] progress 合并(第一页暂存):%s', _pg1)
                _st.settle_page1_progress = None
            # boss 胜局 win 真值:进度符号先于 hp 对比兜底
            if _obs.killed is None and _obs.progress_delta is not None:
                _obs.killed = _obs.progress_delta > 0
                log.info('[cw-bwait] killed 进度符号判定:progress=%s → %s',
                         _obs.progress_delta, _obs.killed)
            # killed 文本兜底(双侧置信度门 + 轮次邻接门)
            # 时基经 kernel 单一源派生(schedule 前序位面实际长度和)。
            # 上一真值源 = gs.hp(终态契约 §A:session.last_hp 锚退役——
            # 本兜底先行于本轮结算覆盖写,gs.hp 现值 = 上一结算真值,
            # 行为变化登记 design §1.3)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                gs_of_ctx,
            )
            from sr_od.application.currency_war.kernel.cw_plane_table import (
                node_t_of,
            )
            _now_t = node_t_of(_session, _plane, _round)
            if not telemetry_only and _obs.hp_confidence >= 0.9 and _now_t is not None:
                if _obs.killed is None:
                    _prev_hp = gs_of_ctx(self.ctx, _session).hp.value
                    _prev_t = _st.last_outcome_t
                    if (_prev_hp is not None and _prev_t is not None
                            and _now_t - _prev_t == 1):
                        _obs.killed = _obs.hp_after >= _prev_hp
                        log.info('[cw-bwait] killed 兜底(hp 对比):上轮 %s → 本轮 %s → %s',
                                 _prev_hp, _obs.hp_after,
                                 '赢' if _obs.killed else '输')
                _st.last_outcome_t = _now_t
            # 结算三项遥测页1 暂存合并(同 progress 合并法;暂存值优先于页2 同帧读数)
            # heal_longline 同并入(ADR-0609:回血分量,页1 瞬窗才可见)
            _st1 = _st.settle_page1_settle
            if _st1 and _st.settle_p1_battle_ts != _st.battle_ts:
                _st1 = {}   # 异窗滞留即弃(跨场污染排除)
            if _st1:
                for _k in ('progress_fill_ratio', 'damage_base',
                           'damage_unfinished_progress', 'heal_longline'):
                    if _st1.get(_k) is not None:
                        setattr(_obs, _k, _st1[_k])
                if _st1.get('damage_breakdown_visible'):
                    _obs.damage_breakdown_visible = True
            _st.settle_page1_settle = {}
            _st.settle_p1_ts = None
            # —— 遭遇选档观测面(E-2):环写位 = 页1 暂存合并消费之后、观察半
            # 直写之前;过守卫三路均入环,残留行排除,同场去重合并(键 =
            # plane+round)。E-3 对账 hook 同点(缺省关,启用 = E-3 采集接通)。
            self._cw_selection_capture(_session, _obs, _plane, _round, _node)
            self._cw_selection_write(_session, _obs, _plane, _round, _node,
                                     residual=_residual)
            if not telemetry_only:
                # —— 观察半直写(ADR-0583 §2.5;原 on_round_end 观察段逐行平移,
                # 写点与原调用同点同时序;hp 结算锚已随终态契约 §A 退役)——
                _write_settlement_observation(_session, _obs)
                # (策略半入槽 pending_round_outcomes 已随终态契约 §B 删:
                #  消费侧 drain 早在 ADR-0638 退役,结算真值归宿 = gs
                #  settlement 覆盖 + performance.history。)
                # 结算真值现役归宿 = GameState settlement
                # 域 apply_settlement_cover(观察半直写链)。
                if _obs.hp_confidence >= 0.9:
                    _st.last_outcome_hp = _obs.hp_after
                # 结算屏真值覆盖(EXPECTED_STATE §2 原口径的观察半,两态制
                # ADR-0651 后 = 纯观察直写:hp/gold/streak/level 全可信):
                # hp 真值链走结算观察直写→last_hp(上);gold/level/经验经
                # apply_settlement_cover 直写容器(原 last_state 帧写半随
                # last_state 链退役批删除,容器半为唯一宿主)。best-effort,
                # 失败不阻塞。(原「覆盖点 diff 对账」半随 expected_state
                # 条目表一并废除——失配 = 推算 bug,缺陷台账留证,无挂账环节。)
                try:
                    from sr_od.application.currency_war.obs.cw_settlement_obs import (
                        parse_settlement_assets,
                        read_settle_gold_opt,
                    )
                    _assets = parse_settlement_assets(_ocr_texts)
                    if _assets.get('gold') is None:
                        # 旧版「存量 <N>」token 锚在当前版本结算布局不存在
                        #(run_20260918_084010 当日 6/6 胜局解析全失败,证据帧
                        # 见 read_settle_gold_opt docstring)→ 退定点读右上角
                        # 金币存量;仍失败则本局无金真值覆盖(gold=None)。
                        _assets['gold'] = read_settle_gold_opt(self.ctx, screen)
                    if _assets.get('gold') is None \
                            and getattr(_obs, 'killed', None) is True:
                        # 读失败原因定位留证(T-42):胜局结算页必有金面板
                        #(经济知识=economy.md「金币明细面板只在胜局结算屏
                        # 出现」),token 解析与定点读双失败 = 布局再漂移
                        # ——落全帧 token 供解析器加固对账(败局页无面板,
                        # 读失败是预期形态,不刷屏)。
                        log.warning('[cw-bwait] 结算屏金读失败(token+定点双失败,'
                                    '胜局,本局无金真值覆盖): ocr_tokens=%s',
                                    _ocr_texts)
                    # GameState 结算覆盖写端(迁移批次二,任务书件 8/设计
                    # §3.5.1):结算真值组(hp/streak 带方向/gold·level·xp
                    # 仅胜局)覆盖进记录;金/等级/经验缺席(败局页无该面板)
                    # 不写。
                    # settlement 行注记带 battle_done:<节点类型> 语义——旧
                    # exogenous 'node_enter' 外生行的「出节点」半随删除波 1
                    # 退役后,其判读语义由本行承接(R5 迁移规划 W1 ⑤/
                    # ADR-0634;同时点同载荷,行行自足快照更强)。
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        apply_settlement_cover,
                        gs_of_ctx,
                    )
                    from sr_od.application.currency_war.kernel.cw_performance import (
                        HP_CONFIDENCE_THRESHOLD,
                    )
                    apply_settlement_cover(
                        gs_of_ctx(self.ctx, _session),
                        hp_after=(getattr(_obs, 'hp_after', None)
                                  if getattr(_obs, 'hp_confidence', 1.0)
                                  >= HP_CONFIDENCE_THRESHOLD
                                  else None),
                        streak_after=getattr(_obs, 'streak', None),
                        killed=getattr(_obs, 'killed', None),
                        progress_delta=getattr(_obs, 'progress_delta', None),
                        gold=_assets.get('gold'),
                        level=_assets.get('level'),
                        xp=((_assets.get('xp_cur'), _assets.get('xp_next'))
                            if (_assets.get('xp_cur') is not None
                                and _assets.get('xp_next') is not None)
                            else None),
                        note=f'battle_done:{getattr(_obs, "node_type", None)}')
                except Exception as e:  # noqa: BLE001  观测面不阻塞对局
                    log.warning('[cw-bwait] 结算覆盖写失败(不阻塞): %s', e)
                # 效果账本结算挂点(GameState 设计 §5.1 挂点清单「结算挂点
                # (on_battle_end)」生产接线;宿主 = settlement 锚行组成部分,
                # 统一观察架构 §12.7-6:锚为账本既有挂点提供确定性触发时点,
                # 挂点语义零改动)。现役注册表零 BATTLE_END 条目(effect-domain
                # §7.4 零条目 = 零驱动)→ 行为面 = 结算事件标记计数;条目
                # 计数/余量推进待建模批立 BATTLE_END 条目后经同一挂点自动
                # 生效。best-effort 同升级标记挂点纪律(prep_actions 升级标记
                # 先例:观测失败不阻塞结算链)。
                try:
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        gs_of_ctx,
                    )
                    gs_of_ctx(self.ctx, _session).effects.on_battle_end()
                except Exception as e:  # noqa: BLE001  观测面不阻塞对局
                    log.warning('[cw-bwait] effect inventory 结算挂点失败'
                                '(不阻塞): %s', e)
                # 装备写端·拷贝仪参与计数结算(生产接线;载体 =
                # settle_copy_machine_participation,指定挂点 = 战斗结算
                # 覆盖带 on_battle_end 同分支同时序):现值
                # 观察面(前台+后台在册单位)逐件推进参与计数,整除阈值
                # 成熟经入席桥落 1★ 复制;对局无拷贝仪穿戴 = 零扫描命中
                # 零行为差。独立 best-effort try(同 on_battle_end 纪律,
                # 不与结算覆盖写端共享异常域;失败不阻塞结算链)。
                try:
                    from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                        settle_copy_machine_participation,
                    )
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        gs_of_ctx,
                    )
                    for _cm in settle_copy_machine_participation(
                            gs_of_ctx(self.ctx, _session),
                            frame=f'p{_plane}-r{_round}'):
                        log.info('[cw-bwait] 拷贝仪成熟入席(equip=%s wearer='
                                 '%s count=%s placed=%s)', _cm.equip,
                                 _cm.wearer, _cm.count, _cm.placed)
                except Exception as e:  # noqa: BLE001  观测面不阻塞对局
                    log.warning('[cw-bwait] 拷贝仪参与结算挂点失败'
                                '(不阻塞): %s', e)
            # 结算观测窗锚刷新(覆盖度守卫的「本窗已观测」凭据;含
            # telemetry-only 败局补录行——行写点即锚,异常中断路径不刷新,
            # exit 守卫按真缺失计):
            _st.settled_battle_ts = _st.battle_ts
            log.info('[cw-bwait] 结算观测 plane=%s round=%s hp_after=%s conf=%s '
                     'comp=%s node=%s%s',
                     _plane, _round, _obs.hp_after, _obs.hp_confidence, _comp_tag,
                     _obs.node_type,
                     ' [loss_page telemetry-only]' if telemetry_only else '')
        except Exception as e:  # noqa: BLE001  观测回路失败不阻塞对局
            log.warning('[cw-bwait] 结算观测失败(不阻塞): %s', e)

    def _record_loss_page(self, screen, pre_fp: tuple | None = None) -> None:
        """失败结算页 → telemetry-only 补一行 outcome + 同屏指纹防重
        (自 cw_loop._record_loss_page 平移,逻辑零变更)。"""
        try:
            if pre_fp is not None:
                _fp = pre_fp
            else:
                _fp = tuple(sorted((r.data, r.y) for r in
                                   self.ctx.ocr_service.get_ocr_result_list(
                                       image=screen, rect=None, color_range=None,
                                       crop_first=False)))
            if self._st.last_loss_fp == _fp:
                return
            self._st.last_loss_fp = _fp
            self._record_round_outcome(screen, telemetry_only=True)
        except Exception as e:  # noqa: BLE001  补录失败不阻塞对局
            log.warning('[cw-bwait] loss_page 补录失败(不阻塞): %s', e)

    def _defeat_latch_by_secondary(self, pnl: dict) -> None:
        """进度符号漏读帧的败局闩次级证据裁决(二轮审计②,随迁)。"""
        _neg = ((pnl.get('damage_base') is not None and pnl['damage_base'] < 0)
                or (pnl.get('damage_unfinished_progress') is not None
                    and pnl['damage_unfinished_progress'] < 0))
        _t = None
        _match = self.ctx.cw_match
        _sess = getattr(_match, 'session', None) if _match else None
        # 轮键锚 = 容器节点读口(last_state 链退役换源;节点未观察 = 证据
        # 不足不置闩,与旧「last_state 缺失」分支同 fail-closed 方向)。
        if _sess is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                gs_of_ctx,
            )
            _nd = gs_of_ctx(self.ctx, _sess).node.value
            if _nd is not None:
                _t = (_nd.plane - 1) * 9 + _nd.round_num
        _min_t = CwScreenBattleWait.SETTLE_DEFEAT_LATCH_MIN_T
        if _neg and _t is not None and _t >= _min_t:
            self._st.saw_defeat_settlement = True
            log.info('[cw-bwait] 败局闩次级证据:面板负分量 + t=%s≥%s → 置闩'
                     '(二轮审计)', _t, _min_t)
        else:
            log.info('[cw-bwait] 败局闩次级证据不足(负分量=%s, t=%s, 门限=%s)→ '
                     '不置闩留证(二轮审计)', _neg, _t, _min_t)

    def _mark_relaunch_residual(self) -> bool:
        """relaunch 残留结算屏判据(迁移审计 w28,随迁;只标记不改行为)。"""
        _res = (not self._st.first_settlement_seen and self._st.is_new_match
                and time.monotonic() - self._st.run_start_ts
                < CwScreenBattleWait.RELAUNCH_SETTLE_GRACE_S)
        self._st.first_settlement_seen = True
        return _res

    @staticmethod
    def _normalize_node_type(raw: str) -> str:
        """节点类型词汇表统一(r363 审计 P0-1,随迁;表与语义见原处)。"""
        _MAP = {'battle': '普通战斗', 'reward': '奖励', 'encounter': '遭遇',
                'supply': '补给', 'boss': 'boss', 'megastar': '巨星',
                '战斗': '普通战斗', '奖励': '奖励', '遭遇': '遭遇',
                '补给': '补给', '首领': 'boss', '巨星': '巨星',
                '普通战斗': '普通战斗', '精英': '精英'}
        return _MAP.get((raw or '').strip(), raw or '普通战斗')

    @staticmethod
    def _node_type_from_table(_session, plane: int | None,
                              round_num: int | None) -> str | None:
        """首节点冷启动兜底:r362 槽序表查节点类型(随迁,逻辑零变更)。"""
        try:
            # 终态契约 §A′:宿主 = gs.node_books(内嵌函数无 self → 桥取)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of as _gso_nt,
            )
            _table = _gso_nt(_session).node_books.plane_node_table or []
            _r = int(round_num or 0)
            if _table and 1 <= _r <= len(_table):
                return str(_table[_r - 1])
        except Exception:   # noqa: BLE001  best-effort 兜底
            pass
        return None

    # ===== 主节点(flat 分类;单元作用域预算 = UNKNOWN_BAIL_N)=====

    @operation_node(name='战斗等待', is_start_node=True, node_max_retry_times=400)
    def wait(self) -> OperationRoundResult:
        """驻留轮(出口判定先行,分支链随后;逐轮 round_wait 重判)。"""
        screen = self.last_screenshot
        # ③出口 B:团灭终局链终点 = 回到大厅(「返回货币战争」落点)→
        # terminal 交回主循环 3c 收口(runs summary/分配器/存档在彼处,遥测
        # 连续性红线:收口点不随 op 化迁移)。
        if self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南',
                                   crop_first=False).is_success:
            log.info('[cw-bwait] 终局分叉:已回大厅 → terminal_lobby(交整局退出收口)')
            return self.round_success('terminal_lobby')

        # ③出口 A:完成判据白名单任一命中 → 交回循环分发
        if self._hit_completion_anchor(screen):
            log.info('[cw-bwait] 完成判据白名单命中 → 交回循环分发')
            return self.round_success('back_to_loop')
        return self._dispatch_frame(screen)

    def _dispatch_frame(self, screen) -> OperationRoundResult:
        """分支链逐位转录体(旧 wait() 出口判定之后的分支序列平移,
        **分支序禁重排**——挑战成功结算/失败页 1f 全链/点空白加速/前往
        结算链/过场屏/战斗宽限/未知帧 bail 的序位即语义;出口判定
        (终局锚/白名单)归 wait() 原位先行)。"""
        # ②段:挑战成功结算(读点 → 继续挑战;#25 读点前等 1.5s)
        if self.round_by_find_area(screen, '货币战争-结算', '按钮-继续挑战').is_success:
            self._unknown_streak = 0
            log.info('[cw-bwait][battle_end] 结算屏首见(战斗结束锚点)')
            from sr_od.application.currency_war.operations.settle_collect_hooks import (
                settle_frame_collect,
            )
            settle_frame_collect(screen)
            # #25 用户裁定:按钮出现后结算数据 ~1.5s 才渲染完,读点前等 1.5s
            # + 重截(交接文件 REAL_MACHINE_EFFICIENCY_HANDOFF.md damage 0/15
            # 事故时序根因);采集钩子仍抓首见帧(时序价值在动画帧)。
            time.sleep(1.5)
            screen = self.screenshot()
            self._record_round_outcome(screen)
            # C-1:新结算帧才计数(点击不生效循环不虚增 rounds_done)
            _fp = tuple(sorted((r.data, r.y) for r in
                               self.ctx.ocr_service.get_ocr_result_list(
                                   image=screen, rect=None, crop_first=False)))
            if self._st.last_settle_fp != _fp:
                self._st.rounds_done += 1
                self._st.last_settle_fp = _fp
            time.sleep(0.2)
            # ②段改调结算确认动作 op(landing §3.2;随 op 迁移 = 点击/
            # M39 长按兜底/证据等待/推进上报,上方读点与 rounds_done 计数
            # 等结算链记留宿主,攻击 B2 归属界定)。子 op 内闭环到白名单
            # 转移证据命中 + settle_confirm 上报;成功后回 wait() 顶走
            # ③段白名单出口收口(幂等:已命中帧不重复点击)。
            from sr_od.application.currency_war.operations.cw_op.cw_op_settle_confirm import (
                CwOpSettleConfirm,
            )
            _confirm = CwOpSettleConfirm(self.ctx)
            _res = _confirm.execute()
            if _res.success:
                return self.round_wait(wait=1.0)
            log.warning('[cw!][bwait] 结算确认动作 op 失败:%s → bail 交主循环兜底',
                        _res.status)
            return self.round_fail('结算确认转移等待失败,bail 交主循环兜底')

        # ①段:失败结算页(分支 1f 随迁:模板组合门 + 进度符号闩 + 面板延迟门
        # + 页1 三项暂存 + 败局补录 + 翻页/点空白)
        _1f_tpl_hit = (
            self.round_by_find_area(screen, '货币战争-结算-失败', '标识-挑战进度',
                                    crop_first=False).is_success
            and self.round_by_find_area(screen, '货币战争-结算-失败', '标识-挑战结束',
                                        crop_first=False).is_success
            and not self.round_by_find_area(
                screen, '货币战争-结算', '按钮-继续挑战', crop_first=False).is_success)
        _1f_items: list | None = None
        _1f_sign: str | None = None
        if _1f_tpl_hit:
            try:
                _1f_items = self.ctx.ocr_service.get_ocr_result_list(
                    image=screen, rect=None, color_range=None, crop_first=False)
                _1f_sign = settle_page1_progress_sign([r.data for r in _1f_items])
            except Exception as e:  # noqa: BLE001  判定失败按漏读处理(fail-open)
                log.warning('[cw-bwait] 结算页1 进度符号判定失败: %s', e)
                _1f_items = None
        if _1f_tpl_hit and _1f_sign != 'pos':
            self._unknown_streak = 0
            if _1f_sign == 'neg':
                self._st.saw_defeat_settlement = True
            from sr_od.application.currency_war.operations.settle_collect_hooks import (
                settle_frame_collect,
            )
            settle_frame_collect(screen)
            # 面板渲染延迟门(SETTLE_PANEL_WAIT_S;1f 是失败页主通道)
            _pnl = read_settle_damage_breakdown(self.ctx, screen)
            if (self.round_by_ocr(screen, '点击空白加速').is_success
                    and not _pnl['visible']):
                _now = time.monotonic()
                if self._st.settle_p1_ts is None:
                    self._st.settle_p1_ts = _now
                if _now - self._st.settle_p1_ts < CwScreenBattleWait.SETTLE_PANEL_WAIT_S:
                    return self.round_wait(wait=0.5)
            self._st.settle_p1_ts = None
            if _1f_sign is None:
                self._defeat_latch_by_secondary(_pnl)
            # 页1 三项遥测暂存(填充率后帧覆盖语义随迁)
            try:
                _on_p1_1f = _1f_items is not None and any(
                    '点击空白加速' in (r.data or '') for r in _1f_items)
                if _1f_items is not None:
                    _pg1f = parse_settlement_progress([r.data for r in _1f_items])
                    if _pg1f is not None:
                        self._st.settle_page1_progress = _pg1f
                    self._st.settle_p1_battle_ts = self._st.battle_ts
                _fr_1f = parse_progress_fill_ratio(screen) if _on_p1_1f else None
                _st_1f = self._st.settle_page1_settle or {}
                for _k, _v in (('damage_base', _pnl['damage_base']),
                               ('damage_unfinished_progress',
                                _pnl['damage_unfinished_progress']),
                               ('heal_longline', _pnl.get('heal_longline'))):
                    if _st_1f.get(_k) is None and _v is not None:
                        _st_1f[_k] = _v
                if _pnl['visible']:
                    _st_1f['damage_breakdown_visible'] = True
                if _fr_1f is not None:
                    _st_1f['progress_fill_ratio'] = _fr_1f
                self._st.settle_page1_settle = _st_1f
            except Exception as e:  # noqa: BLE001  暂存 best-effort
                log.warning('[cw-bwait] 结算页1(1f)三项暂存失败(不阻塞): %s', e)
            _pre_fp = (tuple(sorted((r.data, r.y) for r in _1f_items))
                       if _1f_items is not None else None)
            self._record_loss_page(screen, pre_fp=_pre_fp)
            for _btn in ('前往结算', '下一页', '下一步', '返回货币战争'):
                if self.round_by_ocr(screen, _btn, lcs_percent=0.8).is_success:
                    # 点 OCR 命中位置(检测/点击同源:点刚判中的按钮文本中心,
                    # 非固定点——四按钮位置不同则固定点落空)。二趟 miss = 无点击
                    # 交下轮重判(失败安全,非静默假推进);pre_delay=0 保持原
                    # 「检测即点」时序。
                    self.round_by_ocr_and_click(screen, _btn, lcs_percent=0.8,
                                                pre_delay=0)
                    self.park_cursor(after_wait=0.1)
                    return self.round_wait(wait=1)
            self.ctx.controller.click(CwScreenBattleWait.BLANK.center)
            self.park_cursor(after_wait=0.1)
            return self.round_wait(wait=1)

        # ②段:点空白加速(结算页1 动画帧/强敌来袭横幅;分支 2 随迁)
        _accel_hit = self.round_by_ocr(screen, '点击空白加速')
        if _accel_hit.is_success:
            self._unknown_streak = 0
            from sr_od.application.currency_war.operations.settle_collect_hooks import (
                settle_frame_collect,
            )
            settle_frame_collect(screen)
            try:
                _texts1 = [r.data for r in self.ctx.ocr_service.get_ocr_result_list(
                    image=screen, rect=None, crop_first=False)]
                _pg1 = parse_settlement_progress(_texts1)
                if _pg1 is not None:
                    self._st.settle_page1_progress = _pg1
                    self._st.settle_p1_battle_ts = self._st.battle_ts
            except Exception as e:   # noqa: BLE001  暂存 best-effort
                log.warning('[cw-bwait] 结算页1 progress 暂存失败(不阻塞): %s', e)
            _panel_now = None
            try:
                _panel_now = read_settle_damage_breakdown(self.ctx, screen)
                _fr = parse_progress_fill_ratio(screen)
                _stash = self._st.settle_page1_settle or {}
                for _k, _v in (('damage_base', _panel_now['damage_base']),
                               ('damage_unfinished_progress',
                                _panel_now['damage_unfinished_progress']),
                               ('heal_longline', _panel_now.get('heal_longline'))):
                    if _stash.get(_k) is None and _v is not None:
                        _stash[_k] = _v
                if _panel_now['visible']:
                    _stash['damage_breakdown_visible'] = True
                if _fr is not None:
                    _stash['progress_fill_ratio'] = _fr
                self._st.settle_page1_settle = _stash
                self._st.settle_p1_battle_ts = self._st.battle_ts
            except Exception as e:   # noqa: BLE001  暂存 best-effort
                log.warning('[cw-bwait] 结算页1 三项暂存失败(不阻塞): %s', e)
            if _accel_hit.is_success and not (
                    _panel_now is not None and _panel_now['visible']):
                _now = time.monotonic()
                if self._st.settle_p1_ts is None:
                    self._st.settle_p1_ts = _now
                if _now - self._st.settle_p1_ts < CwScreenBattleWait.SETTLE_PANEL_WAIT_S:
                    return self.round_wait(wait=0.5)
            self._st.settle_p1_ts = None
            self.ctx.controller.click(CwScreenBattleWait.BLANK.center)
            return self.round_wait(wait=0.8)

        # ②段:前往结算链(分支 3b 随迁:轮败/位面结束/团灭多页 → 逐页点进;
        # 「前往结算」帧补 outcome 行,「挑战失败」帧 hp=0 补录置闩)
        for btn in ('前往结算', '下一页', '下一步', '返回货币战争'):
            if self.round_by_ocr(screen, btn, lcs_percent=0.8).is_success:
                self._unknown_streak = 0
                if btn == '前往结算':
                    _fp = tuple(sorted((r.data, r.y) for r in
                                       self.ctx.ocr_service.get_ocr_result_list(
                                           image=screen, rect=None, crop_first=False)))
                    if self._st.last_loss_fp != _fp:
                        self._st.last_loss_fp = _fp
                        self._record_round_outcome(screen)
                if btn == '下一步' and self.round_by_ocr(screen, '挑战失败').is_success:
                    self._st.last_outcome_hp = 0
                    self._st.saw_defeat_settlement = True
                    log.info('[cw-bwait] 战败结算屏 → hp=0 补录 outcomes 真值源')
                from sr_od.application.currency_war.operations.settle_collect_hooks import (
                    settle_frame_collect,
                )
                settle_frame_collect(screen)
                # 点 OCR 命中位置(检测/点击同源,同 1f 分支注释;二趟 miss =
                # 无点击交下轮重判;pre_delay=0 保持原「检测即点」时序)。
                self.round_by_ocr_and_click(screen, btn, lcs_percent=0.8,
                                            pre_delay=0)
                self.park_cursor(after_wait=0.1)
                return self.round_wait(wait=1)

        # ①段:战斗/过场屏(总伤害/数据统计;分支 6 随迁)→ 点空白推进
        if (self.round_by_ocr(screen, '总伤害').is_success
                or self.round_by_find_area(screen, '货币战争-结算', '标识-数据统计').is_success):
            self._unknown_streak = 0
            self.ctx.controller.click(CwScreenBattleWait.BLANK.center)
            return self.round_wait(wait=1.0)

        # ①段:等待结算画面出现。战斗进行中 = 合法静止(ADR-0250 宽限)。
        if self._in_battle_grace(time.monotonic()):
            # 自动战斗检测(P4 挂账落地;2026-09-03 实机建档):「我方行动
            # 待操作」双锚(单攻+回复技能按钮)**连续 ~5s** 命中 = 自动未开
            # (战斗在我方回合停住等操作)→ 鼠标点击右上自动战斗开关开启
            # (点击而非按键:开关为画面按钮,键盘对窗口焦点敏感)。单帧
            # 命中可能是技能演出相似视觉,故连续计时防误判;开关动作后
            # wait=2 覆盖切换生效窗。锚 rect 建档于 currency_war_battle.yml。
            _auto_pending = (
                self.round_by_find_area(
                    screen, '货币战争-战斗', '标识-我方行动待操作',
                    crop_first=False).is_success
                and self.round_by_find_area(
                    screen, '货币战争-战斗', '标识-回复技能',
                    crop_first=False).is_success)
            _now = time.monotonic()
            if _auto_pending:
                if self._st.auto_off_first_ts is None:
                    self._st.auto_off_first_ts = _now
                    log.info('[cw-bwait] 自动战斗疑似未开(我方行动待操作首见)')
                elif _now - self._st.auto_off_first_ts >= 5.0:
                    log.info('[cw-bwait] 连续 %.0fs 我方行动待操作 → 点击自动战斗开关',
                             _now - self._st.auto_off_first_ts)
                    self._st.auto_off_first_ts = None
                    _toggle = area_center(self.ctx, '按钮-自动战斗开关',
                                          '货币战争-战斗')
                    if _toggle is not None:
                        self.ctx.controller.mouse_move(_toggle)
                        self.ctx.controller.click(_toggle)
                    return self.round_wait(wait=2)
            else:
                self._st.auto_off_first_ts = None
            return self.round_wait(wait=2)
        # 节点作用域预算:宽限外连续未知帧 → 留证 + bail 交主循环未知画面分支
        # (W971 05-battle §1 超时兜底;不停机——兜底链裁决权留外循环)。
        self._unknown_streak += 1
        if self._unknown_streak >= CwScreenBattleWait.UNKNOWN_BAIL_N:
            try:
                _shot = self.save_screenshot(prefix='battle_wait_bail')
            except Exception:  # noqa: BLE001  留证失败不阻塞 bail
                _shot = ''
            log.warning('[cw!][bwait] 连续 %s 轮未识别 → bail 交主循环兜底'
                        '(shot=%s,处理流程归 guards.md §2)',
                        self._unknown_streak, _shot)
            return self.round_fail('战斗等待连续未识别,bail 交主循环兜底')
        return self.round_wait(wait=1.5)

    # (五段生命周期段已随基类退役删除:装配点分流/适配器/段迹一并退;
    #  驻留形态豁免经用户裁定,见模块头——两 node 形态不适配。)
