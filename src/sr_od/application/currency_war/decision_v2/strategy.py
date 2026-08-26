"""决策框架 v2 策略具现(ADR-0290/0291/0306 载体批;DecisionV2Strategy)。

**载体批(W35)重建**:不继承旧 ``LineStrategy``(ADR-0336 已删)——独立
``CwStrategy`` 实现(继承 ``DefaultCwStrategy`` 只复用**执行性钩子**:
球/箱/遭遇/补给/巨星/伙伴/prep 步级;战略与备战决策全部自持)。
层1 换源(裁决终版第三选项):

- 信号/锁线 → ``cw_intention``(意向分层状态机;strategy_v4 点0);
- 体系/组合 → ``cw_system_cards``(四体系卡+组合规则;点1/点2);
- 阵容演进 → ``cw_evolution``(``evolution_step`` 进决策循环,显式动作
  发 ``cw_state`` v2 的 CompTransaction/FillSpec;点6/点11);
- 目标件 → ``hoard_target_set``+COMP_LIBRARY v2(定义节 class1-5);
- 插件消费 → ``PLUGIN_LIBRARY``(candidates 层1);
- 纪律族(应急/boss_breaker/carry_gate/保血通道;追赶态已随
  W126/ADR-0349 退场)→
  ``decision_v2.discipline``(移植+语义重接;点4/点7/点12)。

备战计划仍走四层:层1 候选生成 → 层2 硬过滤 → 层3 板面评分 → 层4
预算仲裁;纪律族经 ``assess_discipline`` 产出的注册表**视图**作用于
层2/层4(评分恒用原表——ALL IN 窗不扭曲息 EV 平台语义)。

**唯一策略载体**(ADR-0309;ADR-0336 删除旧臂):config ``strategy_id``
可选 ``decision_v2``/``default``;回退路径=git revert(见 ADR-0336)。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_comps import get_comp
from sr_od.application.currency_war.cw_evolution import (
    EvolutionState,
    evolution_step,
    rollback_weakest,
)
from sr_od.application.currency_war.cw_horizon import NODES_PER_PLANE
from sr_od.application.currency_war.cw_intention import (
    IntentionState,
    hoard_target_set,
    update_intention,
)
from sr_od.application.currency_war.cw_state import (
    BuyCard,
    CompTransaction,
    GameState,
    SellDeployed,
    simulate,
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.arbiter import arbitrate
from sr_od.application.currency_war.decision_v2.candidates import (
    generate_candidates,
)
from sr_od.application.currency_war.decision_v2.discipline import (
    BloodAlarmTracker,
    assess_discipline,
    carry_gate_actions,
    register_round_sold,
)
from sr_od.application.currency_war.decision_v2.filters import (
    filter_candidates,
)
from sr_od.application.currency_war.decision_v2.phase import (
    derive_phase,
    form_ok,
    form_score,
)
from sr_od.application.currency_war.decision_v2.registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.decision_v2.scoring import score_all
from sr_od.application.currency_war.strategies.default_strategy import (
    DefaultCwStrategy,
)

#: 谷底回滚线(点6:转型中遭遇单场掉血 >15 → 回滚一件最弱替换位;
#: 与点4 报警线 20/30 分层并存——15 管转型期单场,20/30 管全局累计)
VALLEY_ROLLBACK_LOSS: int = 15


class DecisionV2Strategy(DefaultCwStrategy):
    """决策框架 v2 唯一策略载体(意向分层×体系卡×演进×纪律族)。

    语义骨架(诚实声明,承 ADR-0291):评分表部分标定(ADR-0293/0295/
    0297/0301/0305),纪律族为 v1 移植语义重接版——本版交付的是**结构与
    可审计性**(每轮候选×分数 log/纪律覆盖态锚点),战力标定归步 5。
    """

    STRATEGY_ID = 'decision_v2'
    STRATEGY_NAME = '决策框架 v2(意向×体系×演进×纪律)'
    AUTHOR = 'OneDragon'
    VERSION = '0.2'
    DESCRIPTION = ('载体批重建:意向分层锁线+体系卡组合+演进引擎+'
                   '纪律族移植(ADR-0309);四层决策骨架不变')

    def __init__(self, registry: DecisionV2Registry | None = None):
        """registry 可注入(A/B:两套注册表各跑一臂);缺省=标定版。"""
        super().__init__()
        self.registry = registry or DEFAULT_REGISTRY

    # ===== 生命周期 =====

    def on_match_start(self, state: GameState, session: StrategySession,
                       config) -> None:
        """扩展态初始化(意向/演进/报警;v2 同轮簿记一并清零)。

        W51:补清 ``v3_intention_key``/``v3_prev_hp``/``v3_last_
        intention_event``——session 跨局复用(续跑/replay 路径)时,
        旧局轮键会让新局 (1,1) 撞键被段级守卫误吞(首轮意向不驱动)、
        旧局终值 HP 会污染三臂首 record 的 hp_before。
        """
        super().on_match_start(state, session, config)
        session.v3_intention = IntentionState()
        session.v3_evolution = EvolutionState()
        session.v3_alarm = BloodAlarmTracker()
        session.v3_hoard = None
        session.v3_core_names = set()
        session.v3_mode = 'economy'
        session.v3_formed_stop = False   # ADR-0343:成型停手标志(层2 写,遥测读)
        session.v3_pending_rollback = None
        session.v3_intention_key = None
        session.v3_prev_hp = None
        session.v3_last_intention_event = ''
        session.v2_round_key = None
        session.v2_round_bought = set()
        session.v2_round_sold = set()
        session.v2_remedy_used = False   # W52(ADR-0326):补偿轮键跨局清零
        session.v2_steady_lv_used = False  # W194/ADR-0378:稳态多击组跨局清零
        session.v3_steady_lv_abandoned = 0  # 稳态组事务性放弃计数(判读)
        session.v3_remedy_abandoned = 0  # 连续放弃轮计数器(检查项数据源)
        session.v2_seed_bought = {}
        session.v2_ever_full_interest = False   # default 栈消费(冻结);v2 已退场(E6)
        session.v2_round_refreshes = 0   # W122 F-01/P8:扑满刷新豁免轮计数
        session.v2_round_p1_early = 0    # W179/ADR-0372:早期买入门轮笔数
        session.v2_round_p2_core = 0     # W194/ADR-0378:P2 核心首件门轮笔数
        # W114/ADR-0346 相位观测(自 W119 起被消费)+ W119/ADR-0347
        # DP 姿态轮缓存载体:初始化(每轮 decide_prep 重算)
        session.v3_phase = 'FORM'
        session.v3_form_ok = False
        session.v3_form_score = 0.0
        session.v3_dp_posture = None

    def on_round_end(self, state: GameState, session: StrategySession,
                     config, obs) -> None:
        """感知质量门(继承 default 实证链)+掉血三臂喂入+谷底回滚判。"""
        super().on_round_end(state, session, config, obs)
        tracker = session.v3_alarm
        if tracker is None:
            tracker = session.v3_alarm = BloodAlarmTracker()
        hp_after = getattr(obs, 'hp_after', None)
        node_type = getattr(obs, 'node_type', None) or ''
        # N2 同源:obs.plane 比 state.plane 权威(结算时位面可能已推进)
        plane = getattr(obs, 'plane', None) or state.plane
        t = (plane - 1) * NODES_PER_PLANE + state.round_num
        hp_before = getattr(session, 'v3_prev_hp', None)
        if hp_before is not None and hp_after:
            tracker.record(node_type, hp_before, hp_after, t, plane=plane)
            # 点6 谷底回滚:转型中(上次替换名单非空)单场掉血 >15
            # → 回滚一件最弱替换位后放缓(显式动作下轮发)
            mem = session.v3_evolution
            if mem is not None and getattr(mem, 'last_deployed', None) \
                    and hp_before - hp_after > VALLEY_ROLLBACK_LOSS \
                    and session.v3_pending_rollback is None:
                act = rollback_weakest(state, mem)
                if act is not None:
                    session.v3_pending_rollback = act
                    log.info('[cw][d2] 谷底回滚登记(单场 -%d > %d)',
                             hp_before - hp_after, VALLEY_ROLLBACK_LOSS)
        session.v3_prev_hp = hp_after if hp_after else hp_before

    # ===== 战略层:意向分层(点0)=====

    def update_target(self, state: GameState, session: StrategySession,
                      config) -> None:
        """v2 战略层:驱动意向状态机(锁线/撤销/强制锁线),写
        ``target_comp``(COMP_LIBRARY v2 真 Comp)+ ``v3_hoard``(囤货
        目标集,层1 唯一消费面)+ ``v3_core_names``(carry 标签裁决)。"""
        ist = session.v3_intention
        if not isinstance(ist, IntentionState):
            ist = session.v3_intention = IntentionState()
        # 段级重入守卫:sim 决策循环每轮最多 8 段重入 update_target,
        # 意向状态机的 miss 计数分母=轮——同轮重入只刷新派生视图
        # (hoard/target_comp),不重复驱动锁线/撤销计数。
        key = (state.plane, state.round_num)
        if session.v3_intention_key != key:
            session.v3_intention_key = key
            # ADR-0366:session 透传(plane_remaining_nodes 读本位面轮数真值)
            update_intention(state, ist, session)
        comp = get_comp(ist.locked_comp) if ist.locked_comp else None
        session.target_comp = comp
        hoard = hoard_target_set(state, ist)
        session.v3_hoard = hoard
        session.v3_core_names = set(comp.core_chars) if comp else set()
        if ist.last_event and ist.last_event not in (
                getattr(session, 'v3_last_intention_event', '')):
            log.info('[cw][d2] 意向 %s mode=%s(%s)',
                     ist.phase, hoard.mode, ist.last_event)
        session.v3_last_intention_event = ist.last_event

    # ===== 备战计划:纪律族 + 演进 + 四层 =====

    def decide_prep(self, state: GameState, session: StrategySession,
                    config) -> list:
        """备战 shop 计划(纪律族视图 × 演进显式动作 × 四层)。"""
        registry = self.registry
        self._ensure_state(session)
        # r408 同轮已买/已卖集维护(轮变更重置;互斥约束的数据源)
        key = (state.plane, state.round_num)
        if session.v2_round_key != key:
            session.v2_round_key = key
            session.v2_round_bought = set()
            session.v2_round_sold = set()
            # W52(ADR-0326):v2_remedy_used 轮键重置——每轮至多一批补偿
            # (防环 §1.5-1);随同轮簿记一并清零。
            session.v2_remedy_used = False
            # W194/ADR-0378:稳态多击组轮键重置(每轮至多一组,
            # 刷后 re-decide 段链不连发)
            session.v2_steady_lv_used = False
            # W122 F-01/W120 P8:扑满节点刷新豁免的轮计数器(轮键重置;
            # arbiter 刷新采纳处递增,scoring 豁免门消费)
            session.v2_round_refreshes = 0
            # W179/ADR-0372:早期买入门单轮笔数(轮键重置;arbiter
            # gold_floor 放行采纳处递增)
            session.v2_round_p1_early = 0
            # W194/ADR-0378 件3:P2 核心首件门单轮笔数(同上)
            session.v2_round_p2_core = 0
        # (W119/ADR-0347:v2_ever_full_interest 采样随 E6 latch 退场删除
        # ——decision_v2 不再消费;default 栈仍读写该字段,冻结不动)
        # W114/ADR-0346 相位观测 + W119 切授权:每轮决策入口计算一次
        # 相位+form_ok+form_score 写 session 供遥测;**自本批起被消费**
        # (arbiter._active_floor 相位地板/filters.formed_stop)。
        _phase = derive_phase(state, session, registry)
        session.v3_phase = _phase.value
        session.v3_form_ok = form_ok(state, session, registry)
        session.v3_form_score = form_score(state, registry)
        # W119/ADR-0347 DP 接线(W113 §8-6 净新增):每轮入口查询一次
        # DP 姿态写 session——仲裁层授权/地板对齐消费(ev.round_posture
        # 同轮读缓存),遥测行带 dp_posture(授权依据 trace)
        from sr_od.application.currency_war.decision_v2.ev import (
            RoundPosture,
            dp_posture,
            reward_node_is_battle,
        )
        session.v3_dp_posture = RoundPosture(
            key, dp_posture(state, session))
        # ADR-0348 ↺:扑满节点识别遥测(识别≠授权;每轮入口采样)
        session.v3_piggy_reward = reward_node_is_battle(state)
        actions: list = []
        # ① 谷底回滚待发动作(上轮结算登记;显式动作优先)
        if session.v3_pending_rollback is not None:
            # ADR-0328:谷底回滚的 SellDeployed 卖出件同样登记同轮已卖集
            # (arbitrate 前;同趟 BUY 同名候选被已卖禁买拒)
            self._register_early_sells([session.v3_pending_rollback],
                                       state, session)
            actions.append(session.v3_pending_rollback)
            session.v3_pending_rollback = None
        # ② 演进引擎进决策循环(点6 统一入口;显式 CompTransaction)
        if session.v3_evolution is not None:
            # W155/ADR-0360 件1:锁定帧 off-lock 演进提案降级分从 registry
            # 注入(总开关关/0 = 回 W150 后行为)
            ev_acts = evolution_step(
                state, session, session.v3_evolution,
                off_lock_penalty=(
                    registry.evolve_off_lock_penalty
                    if registry.evolve_lock_constraint_enabled else 0.0),
                # W160/ADR-0363:S1 型修法两件(引擎下界守卫/末轮演进
                # 冻结)从 registry 注入(A/B 通道,关=回 W155 后行为)
                engine_guard=registry.evolve_engine_guard_enabled,
                final_freeze=registry.evolve_final_freeze_enabled,
                # W174/ADR-0371:引擎补完守卫(own-gap 修法,A/B 通道,
                # 关=回 W170 后行为)
                engine_completion=registry.evolve_engine_completion_enabled,
                # W192/ADR-0375:希儿系贡献件并入守卫/保护集辖域
                # (A/B 通道,关=回 W188 后行为)
                seele_scope=registry.guard_seele_scope_enabled)
            # ADR-0328 第四卖发射点:演进替换事务/谷底回滚的卖出件
            # (CompTransaction.sell / SellDeployed)不经 arbitrate 守卫
            # ——此处(arbitrate 前)登记同轮已卖集,arbitrate 同趟
            # BUY 同名候选被已卖禁买拒(seed 0 r1「COMP 卖桑博 +
            # BUY 桑博」振荡,检查器按账本序报 no_same)。
            self._register_early_sells(ev_acts, state, session)
            actions.extend(ev_acts)
        # ③ 纪律族评估(覆盖态/模式/ALL IN 窗/保血通道)
        disc = assess_discipline(state, session, registry)
        session.v3_mode = disc.mode
        # ④ carry 腾位门(bench 满+意向核心在店;v1 r416 移植)
        actions.extend(carry_gate_actions(
            state, session, registry,
            bought={a.card.name for a in actions
                    if isinstance(a, BuyCard)}))
        # ⑤ 四层(层2/层4 消费纪律视图;层3 评分用原表)
        reg_view = disc.arbiter_registry(registry)
        # ADR-0328 执行域对齐:arbitrate 的 state 参数 = **前置已采纳动作
        # simulate 后**的执行域(演进 COMP/谷底回滚/carry_gate),非决策
        # 入口原始态——arbitrate 内 working 从执行域初始化,index_drift/
        # same_round_mutex 基于「真实执行序」的槽位内容校验(W66 seed
        # 0/6/14 实证:前置 COMP 改变槽位后,SellBench(idx) 决策域与
        # 执行域错位 → 实卖错件[刚买的同名卡] → 账本「BUY X → SELL X」
        # 假象违规,no_same 96/400 的主要来源)。候选生成/过滤/评分仍用
        # 原始 state(候选 idx 语义=原始槽;评分=决策时点)。
        exec_state = state
        if actions:
            _wk = state.copy()
            for _a in actions:
                _wk = simulate(_wk, _a)
            exec_state = _wk
        cands = generate_candidates(state, session, registry)          # 层1
        kept, _flog = filter_candidates(cands, state, session, reg_view)  # 层2
        scored = score_all(kept, state, session, registry)             # 层3
        # (W52/ADR-0326:旧 ⑤b liquidity_actions 已删——金不足变现收编
        # 进层4 末段补偿趟 _compensate_gold,触发源=实际拒绝事件)
        result = arbitrate(scored, exec_state, session, reg_view,
                           disc_view=disc)                    # 层4
        actions.extend(result.actions)
        # 执行 log → session.last_candidate_scores(遥测判读可直接读)
        session.last_candidate_scores = {
            f"r{state.round_num}:{r['tag']}:{r['desc']}": r['score']
            for r in result.log[:10] if r['accepted']}
        session.last_candidate_scores_round = state.round_num
        # ADR-0328:同轮已买/已卖集登记已前移到**动作采纳处**(arbiter
        # 主循环/补偿趟/carry_gate 内部,采纳即登记)——此处不再兜底
        # 回写:守卫在采纳时立即可见(no_same_round_buy_sell 回归根因
        # = 旧登记点延迟到 arbitrate 之后,同趟 BUY X 采纳后 SELL X
        # 旧副本候选的 r408 守卫读的是上一段已买集)。engine_seed
        # 购入轮登记(ADR-0289 §5,seed_age_blocked 数据源)随采纳
        # 处一并完成(arbiter._register_accepted)。
        log.info('[cw][d2] r%d %s/%s 地板%d:演进 %d+采纳 %d/%d 候选(%s)',
                 state.round_num, disc.coverage, disc.mode, result.floor,
                 len([a for a in actions
                      if type(a).__name__ == 'CompTransaction']),
                 len(result.actions), len(cands),
                 '; '.join(r['desc'] for r in result.log
                           if r['accepted']) or '无')
        return actions

    # ===== 内部 =====

    @staticmethod
    def _register_early_sells(acts, state: GameState,
                              session: StrategySession) -> None:
        """ADR-0328 第四卖发射点:arbitrate **之前**已发射的卖动作
        (演进替换事务 ``CompTransaction.sell`` / 谷底回滚
        ``SellDeployed``)登记同轮已卖集。

        这两类卖不经 arbitrate 的 same_round_mutex 守卫(不产生
        SellBench 候选),而 arbitrate 同趟可能采纳 BUY 同名候选——
        seed 0 r1「COMP 卖桑博(旧档解除)+ BUY 桑博(店新副本)」
        振荡,检查器按账本序报 no_same_round_buy_sell。登记后
        arbitrate 的 BUY 候选被已卖禁买拒,同轮同名买卖互斥闭合。
        CompTransaction 被拒(事务校验失败)时登记保守多记,下轮
        重置,不破坏不变量。
        """
        names: list[str] = []
        for a in acts:
            if isinstance(a, CompTransaction):
                for idx, domain in a.sell or []:
                    src = state.deployed if domain == 'deployed' \
                        else state.bench
                    if 0 <= idx < len(src or []) and src[idx] is not None:
                        _n = src[idx].char_id
                        if _n:
                            names.append(_n)
            elif isinstance(a, SellDeployed):
                if 0 <= a.deployed_idx < len(state.deployed or []):
                    _n = state.deployed[a.deployed_idx].char_id
                    if _n:
                        names.append(_n)
        if names:
            register_round_sold(names, state, session)

    @staticmethod
    def _ensure_state(session: StrategySession) -> None:
        """扩展态 None 归一化(续跑/replay 路径未走 on_match_start 的
        守卫——终审 B1 同型:None 崩防御)。"""
        if not isinstance(session.v3_intention, IntentionState):
            session.v3_intention = IntentionState()
        if session.v3_evolution is None:
            from sr_od.application.currency_war.cw_evolution import (
                EvolutionState,
            )
            session.v3_evolution = EvolutionState()
        if session.v3_alarm is None:
            session.v3_alarm = BloodAlarmTracker()
