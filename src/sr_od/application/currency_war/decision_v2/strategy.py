"""决策框架 v2 策略具现(ADR-0290/0291/0306 载体批;DecisionV2Strategy)。

**载体批(迁移审计 w35(git 历史))重建**:不继承旧 ``LineStrategy``(ADR-0336 已删)——独立
``CwStrategy`` 全具现(执行性钩子:球/箱/遭遇/补给/巨星/伙伴/prep 步级,
自 ``DefaultCwStrategy`` 本体删除批平移自持,判据/表库仍消费
``cw_plan/cw_economy/cw_recipe/cw_comps`` 共享函数;战略与备战决策自持)。
层1 换源(裁决终版第三选项):

- 信号/锁线 → ``cw_intention``(意向分层状态机;strategy_v4 点0);
- 体系/组合 → ``cw_system_cards``(四体系卡+组合规则;点1/点2);
- 阵容演进 → ``cw_evolution``(``evolution_step`` 进决策循环,显式动作
  发 ``cw_state`` v2 的 CompTransaction/FillSpec;点6/点11);
- 目标件 → ``hoard_target_set``+COMP_LIBRARY v2(定义节 class1-5);
- 插件消费 → ``PLUGIN_LIBRARY``(candidates 层1);
- 纪律族(应急/boss_breaker/carry_gate/保血通道;追赶态已随
  `w126_b_arm/`/ADR-0349 退场)→
  ``decision_v2.discipline``(移植+语义重接;点4/点7/点12)。

备战计划仍走四层:层1 候选生成 → 层2 硬过滤 → 层3 板面评分 → 层4
预算仲裁;纪律族经 ``assess_discipline`` 产出的注册表**视图**作用于
层2/层4(评分恒用原表——ALL IN 窗不扭曲息 EV 平台语义)。

**唯一策略载体**(ADR-0309;ADR-0336 删除旧臂):config ``strategy_id``
可选 ``decision_v2``/``default``;回退路径=git revert(见 ADR-0336)。
"""
from __future__ import annotations

from typing import Literal

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_plan
from sr_od.application.currency_war.cw_strategy import CwStrategy, StrategySession
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
from sr_od.application.currency_war.decision_v2.scoring import score_all
from sr_od.application.currency_war.kernel import cw_comps, cw_events
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    EncounterPick,
    MegastarOption,
    MegastarPick,
    PartnerOption,
    PartnerPick,
    PlannerOption,
    PlannerPick,
    SupplyOption,
    SupplyPick,
)
from sr_od.application.currency_war.kernel.cw_evolution import (
    EvolutionState,
    evolution_step,
    rollback_weakest,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    IntentionState,
    hoard_target_set,
    pair_target_comp,
    update_intention,
)
from sr_od.application.currency_war.kernel.cw_performance import (
    HP_CONFIDENCE_THRESHOLD,
    RoundOutcome,
)
from sr_od.application.currency_war.kernel.cw_plane_table import NODES_PER_PLANE
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    ClickSpheres,
    DeferSpheres,
    DeployMove,
    EnsureShopClosed,
    EnsureShopOpen,
    LevelUp,
    OpenBox,
    OpenTome,
    PickBoxCard,
    RunBuyPhase,
    RunDeploy,
    RunEquip,
    SellBench,
    StartBattle,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BuyCard,
    CompTransaction,
    GameState,
    MatchOutcome,
    PickEvent,
    RefreshShop,
    SellDeployed,
    simulate,
)

#: 谷底回滚线(点6:转型中遭遇单场掉血 >15 → 回滚一件最弱替换位;
#: 与点4 报警线 20/30 分层并存——15 管转型期单场,20/30 管全局累计)
VALLEY_ROLLBACK_LOSS: int = 15


class DecisionV2Strategy(CwStrategy):
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

        迁移审计 w51(git 历史):补清 ``v3_intention_key``/``v3_prev_hp``/``v3_last_
        intention_event``——session 跨局复用(续跑/replay 路径)时,
        旧局轮键会让新局 (1,1) 撞键被段级守卫误吞(首轮意向不驱动)、
        旧局终值 HP 会污染三臂首 record 的 hp_before。
        """
        # (基类 on_match_start 原为 P1 no-op;default 本体删除批后无基类体可调)
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
        session.v2_remedy_used = False   # 迁移审计 w52(git 历史)(ADR-0326):补偿轮键跨局清零
        session.v2_steady_lv_used = False  # `w194_p2line/`/ADR-0378:稳态多击组跨局清零
        session.v3_steady_lv_abandoned = 0  # 稳态组事务性放弃计数(判读)
        session.v3_remedy_abandoned = 0  # 连续放弃轮计数器(检查项数据源)
        # 血预算停手·停升级拒付计数(设计件 12;ADR-0448):决策层拒付
        # 披露(判读「停手线拦了多少次追级」;sim 逐轮差分进账本)
        session.v3_blood_budget_rejects = 0
        # 血预算停手·搜索型刷新停付拒付计数(设计件 12 §2.3-P1-c/§3.2;
        # ADR-0449):refresh 收尾拒付披露,sim 逐轮差分同式
        session.v3_blood_budget_refresh_rejects = 0
        session.v2_seed_bought = {}
        session.v2_ever_full_interest = False   # default 栈消费(冻结);v2 已退场(E6)
        session.v2_round_refreshes = 0   # 迁移审计 w122(git 历史) F-01/P8:扑满刷新豁免轮计数
        session.v2_round_p1_early = 0    # `w179_gate/`/ADR-0372:早期买入门轮笔数
        session.v2_round_p2_core = 0     # `w194_p2line/`/ADR-0378:P2 核心首件门轮笔数
        session.v2_round_press_exempt = 0   # `w300_dup_ruling/`/V-B8:[11] 豁免臂轮笔数
        session.v2_round_press_copy = 0     # `w300_dup_ruling/`/V-B8:press 候选轮笔数
        # 迁移审计 w114(git 历史)/ADR-0346 相位观测(自 迁移审计 w119(git 历史) 起被消费)+ 迁移审计 w119(git 历史)/ADR-0347
        # DP 姿态轮缓存载体:初始化(每轮 decide_prep 重算)
        session.v3_phase = 'FORM'
        session.v3_form_ok = False
        session.v3_form_score = 0.0
        session.v3_dp_posture = None
        # `w224_handoff/`/ADR-0399:P2 承接快照(观测层;None=未进 P2/未计算)
        session.v3_handoff = None
        session.v3_handoff_plane = None
        # `w227_handoff_gate/`/ADR-0400:P1 末窗承接门缺口(filters 每段写;跨局清零)
        session.v3_handoff_gap = 0
        # 迁移审计 w238(git 历史)/ADR-0403:boss 投影 hp 披露(ADR-0411 起投影无条件启用,
        # 末窗 handoff_gate_gap 写;None=非末窗,判读「boss 后投影 hp」面)
        session.v3_handoff_hp_proj = None
        # W332b:release 泄息指令(每轮 decide_prep 重算)与轮内累计花费
        session.v3_release = None
        session.v3_release_round = None
        session.v3_release_spent = 0

    def on_round_end(self, state: GameState, session: StrategySession,
                     config, obs: RoundOutcome) -> None:
        """感知质量门(观测段自 default 本体删除批平移自持,逐字)+
        掉血三臂喂入+谷底回滚判。"""
        session.performance.record(obs)
        # 结算「连胜×N」前缀=方向 → session.last_streak(给下回合 economy C 杠杆:连胜保连胜/连败 fold)。
        session.last_streak = obs.streak
        # 结算屏「小队生命值NN」可靠 → 用它给下回合 prep(HP 结算→下回合 prep 不变)。保血/maybe_pivot 信号地基。
        if obs.hp_confidence >= HP_CONFIDENCE_THRESHOLD:
            session.last_hp = obs.hp_after
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

    def create_session(self, config) -> StrategySession:
        """空白 session(rng 留默认,由 run loop 按 ``config.strategy_seed`` 覆盖)。"""
        return StrategySession()

    def on_match_end(self, session: StrategySession, config, outcome: MatchOutcome) -> None:
        """P1 no-op(outcome 字段全默认,真实结算屏 OCR 属 P1.5)。"""
        pass

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
            # ADR-0366:session 透传(plane_remaining_nodes 读本位面轮数真值);
            # registry 透传(C4 存活轮数门在 v2 换线通道的判据注入,A/B 臂
            # 经构造参替换 registry 即可达;cw_intention 缺省 None=缺省表)
            update_intention(state, ist, session, registry=self.registry)
        comp = get_comp(ist.locked_comp) if ist.locked_comp else None
        # `w578_target_comp_wire/`:P1 配方锁帧物化——ADR-0357 后 locked_comp 在配方锁局恒空,
        # session.target_comp 恒 None → 部署选人/评分管线/投资装备钩子等
        # 既有 target 消费者全盲(实机断链:引擎件躺 bench、散脸占板)。
        # 把已锁配方对物化为伪 comp(单一口径=cw_intention.pair_target_comp
        # docstring);①锁局 locked_comp 优先,本分支不辖;P2+/空对不物化
        # (不越 ADR-0357 辖域)。
        if comp is None and state.plane == 1 and ist.p1_pair:
            comp = pair_target_comp(tuple(ist.p1_pair))
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
            # 迁移审计 w52(git 历史)(ADR-0326):v2_remedy_used 轮键重置——每轮至多一批补偿
            # (防环 §1.5-1);随同轮簿记一并清零。
            session.v2_remedy_used = False
            # `w194_p2line/`/ADR-0378:稳态多击组轮键重置(每轮至多一组,
            # 刷后 re-decide 段链不连发)
            session.v2_steady_lv_used = False
            # 迁移审计 w122(git 历史) F-01/迁移审计 w120(git 历史) P8:扑满节点刷新豁免的轮计数器(轮键重置;
            # arbiter 刷新采纳处递增,scoring 豁免门消费)
            session.v2_round_refreshes = 0
            # `w179_gate/`/ADR-0372:早期买入门单轮笔数(轮键重置;arbiter
            # gold_floor 放行采纳处递增)
            session.v2_round_p1_early = 0
            # `w194_p2line/`/ADR-0378 件3:P2 核心首件门单轮笔数(同上)
            session.v2_round_p2_core = 0
            # `w300_dup_ruling/`/V-B8:press 通道两臂单轮笔数([11] 豁免臂/press 候选
            # 采纳;arbiter 采纳处递增)
            session.v2_round_press_exempt = 0
            session.v2_round_press_copy = 0
            # W332b:release 泄息预算的轮内累计花费(预算逐轮清零;boss 窗
            # 单轮 latch 单位,无跨轮语义)
            session.v3_release_spent = 0
        # (迁移审计 w119(git 历史)/ADR-0347:v2_ever_full_interest 采样随 E6 latch 退场删除
        # ——decision_v2 不再消费;default 栈仍读写该字段,冻结不动)
        # 迁移审计 w114(git 历史)/ADR-0346 相位观测 + 迁移审计 w119(git 历史) 切授权:每轮决策入口计算一次
        # 相位+form_ok+form_score 写 session 供遥测;**自本批起被消费**
        # (arbiter._active_floor 相位地板/filters.formed_stop)。
        _phase = derive_phase(state, session, registry)
        session.v3_phase = _phase.value
        session.v3_form_ok = form_ok(state, session, registry)
        session.v3_form_score = form_score(state, registry)
        # 迁移审计 w119(git 历史)/ADR-0347 接线(预算收权批(ADR-0465)):每轮入口核算一次轮姿态写
        # session——仲裁层授权/地板对齐消费(ev.round_posture 同轮读缓存),
        # 遥测行带 dp_posture(标签 trace)。生产者 = 确定性预算核
        # (build_round_posture:schedule/refresh_ev_budget 两接缝,R4
        # 单一址);release 包装(FLIP/存息准入门)紧随其后。
        from sr_od.application.currency_war.decision_v2.ev import (
            RoundPosture,
            build_round_posture,
            reward_node_is_battle,
        )
        _raw_posture = build_round_posture(state, session, registry)
        # W332b 未成型期姿态:泄息通道(release)——FLIP 谓词命中/末窗
        # slot 守卫压 level 时包装姿态(预算三方合并 + spend_mode 新档,
        # 单一源=decision_v2.posture_release;下流 scoring/arbiter 读同一
        # 包装后姿态,义务预算走 session.v3_release)。
        from sr_od.application.currency_war.decision_v2.posture_release import (
            evaluate_release,
        )
        _wrapped, _directive = evaluate_release(
            state, session, registry, _phase.value, _raw_posture)
        session.v3_dp_posture = RoundPosture(key, _wrapped)
        if _directive is None:
            session.v3_release = None
        # `w611_econ_cycle/` 储备/义务披露字段(每轮入口写,幂等;判读「义务帧兑现率」
        # 与 ADR-0445 实机验证队列 §2.3 的数据源)。遥测经 recorder 汇点
        # 统一接出(`w603_telemetry_wiring/` 同款通道,shop.py extra 通道不触)。
        from sr_od.application.currency_war.kernel.cw_economy import (
            reserve_cap as _reserve_cap,
        )
        _rcap = _reserve_cap(state, session, registry)
        session.v3_reserve_cap = _rcap
        session.v3_reserve_overflow = max(0, (state.gold or 0) - _rcap)
        session.v3_release_budget = int(
            getattr(_directive, 'budget_gold', 0) or 0)
        session.v3_release_reason = str(
            getattr(_directive, 'reason', '') or '')
        # ADR-0348 ↺:扑满节点识别遥测(识别≠授权;每轮入口采样)
        session.v3_piggy_reward = reward_node_is_battle(state)
        # `w224_handoff/`/ADR-0399:P2 承接快照(纯观测,零行为;设计件 08 §4.2
        # Phase 0)——plane>=2 本位面首帧算一次写 session.v3_handoff
        # (派生量模式,同 v3_phase;session 丢→下轮入口现算,天然免疫)。
        # 挂载在相位派生同址、任何 P2 决策/动作之前 = 「进场继承完成后」
        # 的承接态;sim/生产同点(sim 侧 SimResult.p2_handoff 由此采样)。
        if state.plane >= 2 and getattr(session, 'v3_handoff_plane', None) \
                != state.plane:
            from sr_od.application.currency_war.decision_v2.handoff import (
                handoff_snapshot,
            )
            session.v3_handoff_plane = state.plane
            session.v3_handoff = handoff_snapshot(state, session, registry)
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
            # `w155_evolve_lock/`/ADR-0360 件1:锁定帧 off-lock 演进提案降级分从 registry
            # 注入(总开关关/0 = 回 `w150_buy_lock/` 后行为)
            ev_acts = evolution_step(
                state, session, session.v3_evolution,
                off_lock_penalty=(
                    registry.evolve_off_lock_penalty
                    if registry.evolve_lock_constraint_enabled else 0.0),
                # 迁移审计 w160(git 历史)/ADR-0363:S1 型修法两件(引擎下界守卫/末轮演进
                # 冻结)从 registry 注入(A/B 通道,关=回 `w155_evolve_lock/` 后行为)
                engine_guard=registry.evolve_engine_guard_enabled,
                final_freeze=registry.evolve_final_freeze_enabled,
                # `w174_deploy/`/ADR-0371:引擎补完守卫(own-gap 修法,A/B 通道,
                # 关=回 `w170_p1_vd/` 后行为)
                engine_completion=registry.evolve_engine_completion_enabled,
                # `w201_strand/`/ADR-0381:补完缺口 owned 口径 distinct(A/B 通道,
                # 关=回 `w174_deploy/` 后全羁绊逐件计数)
                complete_distinct=registry.engine_complete_distinct_owned,
                # `w192_seelex/`/ADR-0375:希儿系贡献件并入守卫/保护集辖域
                # (A/B 通道,关=回 `w188_threestack/` 后行为)
                seele_scope=registry.guard_seele_scope_enabled,
                # `w197_comptx/`/ADR-0380:溢出卖出下界守卫(execute_replacement
                # 溢出卖出对 TT 体系件改留场;A/B 通道,关=回 `w195_intent/` 后
                # 行为——arbiter 采纳点复检同 flag,见 arbiter.py)
                sell_floor=registry.sell_floor_exec_guard_enabled,
                # `w202_grade/`/ADR-0382:补完保护集分级(undeploy 候选枯竭且
                # 缺口持续 ≥2 轮时降级换血;A/B 通道,关=回 0371/0381
                # 后「不硬拆」语义)
                grade_down=registry.engine_complete_grade_down)
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
        # same_round_mutex 基于「真实执行序」的槽位内容校验(迁移审计 w66(git 历史) seed
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
        # (迁移审计 w52(git 历史)/ADR-0326:旧 ⑤b liquidity_actions 已删——金不足变现收编
        # 进层4 末段补偿趟 _compensate_gold,触发源=实际拒绝事件)
        result = arbitrate(scored, exec_state, session, reg_view,
                           disc_view=disc)                    # 层4
        actions.extend(result.actions)
        # v6 死亡窗支出分配器(W684 v6 设计落码,决策 why 见 ADR-0474):
        # 管线动作落地后的执行域上,若本帧管线未支出(坐息/攥金帧)且
        # 落入分配器辖域(停手窗∨死亡域,辖域谓词现值直用),剩余支出
        # 由分配器按 P_t=⟨Π_t,R_t,O,D⟩ 出清;管线已支出帧分配器不接管
        # (同帧双花结构性排除)。记账扩展=分配器帧位(各渠道获配金,
        # v6 §6)每帧披露写 session.v3_alloc_frame。
        from sr_od.application.currency_war.decision_v2.allocator import (
            allocator_run,
        )
        from sr_od.application.currency_war.decision_v2.discipline import (
            register_round_bought,
        )
        _pipeline_spent = any(isinstance(a, (BuyCard, LevelUp, RefreshShop))
                              for a in result.actions)
        _alloc_base = exec_state
        if result.actions:
            _wk = exec_state.copy()
            for _a in result.actions:
                _wk = simulate(_wk, _a)
            _alloc_base = _wk
        _alloc = allocator_run(_alloc_base, session, registry,
                               pipeline_spent=_pipeline_spent)
        session.v3_alloc_frame = _alloc.frame
        if _alloc.active and _alloc.actions:
            actions.extend(_alloc.actions)
            for _a in _alloc.actions:
                if isinstance(_a, BuyCard) and _a.card.name:
                    register_round_bought([_a.card.name], state, session)
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

    def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                      state: GameState, session: StrategySession, config) -> PickEvent:
        """投资策略/投资环境 3 选 1。P1 两 kind 同一实现(委托 ``decide_event``);分表现 P2+ 议题。
        ``state.board`` 由调用方传空 stub(overlay 叠备战时 board 不可读,§11.7)。
        ADR-0134:strategy kind 传 session.target_comp(星徽套组/专属强化对齐 target = 成型加速,
        comp 匹配分压倒品质先验)。ADR-0144 修订:env kind 也传 —— 开局环境屏 comp 未定(None,
        行为同旧,阵营定向走 select_comp env_fit);**局中环境屏**(如 联席决策 2-6 节点)comp 已定,
        概念股/邀请/契约阵营条件分(ENV_FACTION_MATCH_FLOOR)生效。
        ADR-0209(接线 1/6):选卡结果喂 CommitSignals(策略 2.0/环境 1.0 权重;
        affinity 表把所选卡映射到 comp 分贡献)。"""
        _tgt = session.target_comp
        pick = cw_events.decide_event(options, config, state, target_comp=_tgt)
        # 信号喂入:所选卡对各线的 affinity → comp 分贡献
        try:
            from sr_od.application.currency_war.kernel.cw_comps import augment_affinity
            src = 'invest_strategy' if kind == 'strategy' else 'invest_env'
            scores: dict[str, float] = {}
            for opt in options:
                aff = augment_affinity(opt)
                for comp_name, v in aff.items():
                    scores[comp_name] = max(scores.get(comp_name, 0.0), v)
            if scores:
                session.commit_signals.add(src, scores)
        except Exception:   # noqa: BLE001  信号喂入 best-effort
            pass
        return pick

    def decide_supply(self, options: list[SupplyOption], state: GameState,
                      session: StrategySession, config, refresh_used: bool = False) -> SupplyPick:
        """补给选装备/出钻。⚠️ OCR 未就绪(P1 钩子 + 默认委托,handler 不 rewire,随阶段5)。"""
        return cw_events.decide_supply(options, state, session.target_comp, config, refresh_used)

    def decide_encounter(self, options: list[EncounterOption], state: GameState,
                         session: StrategySession, config, refresh_used: bool = False) -> EncounterPick:
        """遭遇难度/词缀避开。⚠️ 后 dormant(遭遇=普通战斗无选项 UI);纯逻辑+测试暂留。"""
        return cw_events.decide_encounter(options, state, session.target_comp, config, refresh_used)

    def decide_megastar(self, options: list[MegastarOption], state: GameState,
                        session: StrategySession, config) -> MegastarPick:
        """巨星选候选:委托 ``cw_comps.select_megastar`` 拿角色名 → 名在 options 命中该 idx;否则 idx=0。
        ⚠️ OCR 未就绪(char_id 全空 → 匹配恒失败 → idx=0 = 今天盲点左候选,随阶段5)。"""
        available = [o.char_id for o in options if o.char_id]
        chosen_name = cw_comps.select_megastar(state, session.target_comp, available)
        if chosen_name:
            for o in options:
                if o.char_id == chosen_name:
                    return MegastarPick(idx=o.idx, reason=f"select_megastar 命中 {chosen_name}")
        return MegastarPick(idx=0, reason="fallback 左候选(OCR 未就绪,char_id 空)")

    def decide_partner(self, options: list[PartnerOption], state: GameState,
                       session: StrategySession, config) -> PartnerPick:
        """选择伙伴:优先 ``config.character_build_around`` / ``target.core_chars`` 命中;否则 idx=0。
        ⚠️ OCR 未就绪(char_id 全空 → 命中恒失败 → idx=0 = 今天盲点 stage 立绘,随阶段5)。"""
        wants: list[str] = list(getattr(config, 'character_build_around', []) or [])
        if session.target_comp is not None:
            wants += list(session.target_comp.core_chars)
        for o in options:
            if o.char_id and o.char_id in wants:
                return PartnerPick(idx=o.idx, reason=f"命中偏好/核心 {o.char_id}")
        return PartnerPick(idx=0, reason="fallback(OCR 未就绪,char_id 空)")

    def decide_planner(self, options: list[PlannerOption], state: GameState,
                       session: StrategySession, config) -> PlannerPick:
        """银狼策划事件(r104 用户定调:接入策略模块由它定;委托 cw_events.decide_planner)。

        升费卡打分含银狼线/在场判定(state.bench+deployed 的 char_id),
        session.target_comp 决定银狼线加成。"""
        return cw_events.decide_planner(options, state, session.target_comp)

    def decide_star_tome(self, options: list[str], state: GameState,
                         session: StrategySession, config) -> int:
        """星徽秘典四选一(r104 接入策略模块;原 loop 内联 board 匹配迁此)。

        打分:①target_comp.all_factions 命中(终局线需要的阵营星徽 = +40);
        ②board 已有该阵营(板上已有=边际价值高,board 计数 ×8);
        ③当前配方框架阵营命中(双轨期过渡配方需要,+15)。无命中 fallback idx=0。
        返回 options 索引。"""
        if not options:
            return 0
        fw = getattr(session, 'transition_framework', '')
        _fw_facs: set[str] = set()
        if fw:
            from sr_od.application.currency_war.kernel.cw_transition import (
                FRAMEWORK_FACTIONS,
            )
            _fw_facs = set(FRAMEWORK_FACTIONS.get(fw, ()) or ())
        _tgt_facs: set[str] = set()
        if session.target_comp is not None:
            _tgt_facs = set(session.target_comp.all_factions or [])
        best_i, best_s = 0, -1.0
        for i, name in enumerate(options):
            s = 0.0
            from one_dragon.utils import str_utils
            from sr_od.application.currency_war.decision_v2.scoring import PICK_BIAS
            if name in _tgt_facs:
                s += PICK_BIAS.tome_target_faction
            hit = next((b for b, n in (state.board or {}).items()
                        if n > 0 and str_utils.find_by_lcs(b, name, percent=0.8)), None)
            if hit is not None:
                s += PICK_BIAS.tome_board_hit * (state.board or {})[hit]
            if name in _fw_facs:
                s += PICK_BIAS.tome_framework_faction
            if s > best_s:
                best_i, best_s = i, s
        return best_i

    def decide_wish_trial(self, options: list[str], state: GameState,
                          session: StrategySession, config) -> int:
        """祈愿试炼选卡(r104 接入策略模块;原固定第1张)。

        options = 各卡 objective 文字(OCR)。打分:①金币类(直接经济,阵容无关
        稳妥)+25;②target/框架阵营相关词命中 +20;③「刷新/购买」类操作向
        (与 DP 攒息协同)+10;无信息 fallback idx=0。返回索引。"""
        if not options:
            return 0
        _tgt_facs: set[str] = set()
        if session.target_comp is not None:
            _tgt_facs = set(session.target_comp.all_factions or [])
        fw = getattr(session, 'transition_framework', '')
        _fw_facs: set[str] = set()
        if fw:
            from sr_od.application.currency_war.kernel.cw_transition import (
                FRAMEWORK_FACTIONS,
            )
            _fw_facs = set(FRAMEWORK_FACTIONS.get(fw, ()) or ())
        best_i, best_s = 0, -1.0
        for i, obj in enumerate(options):
            from sr_od.application.currency_war.decision_v2.scoring import (
                PICK_BIAS as _PB,
            )
            from sr_od.application.currency_war.decision_v2.scoring import (
                effect_pick_bias,
            )
            s = effect_pick_bias(session, obj)
            if '金币' in obj:
                s += _PB.wish_gold
            if any(f in obj for f in (_tgt_facs | _fw_facs)):
                s += _PB.wish_faction
            if '刷新' in obj or '购买' in obj:
                s += _PB.wish_operation
            if s > best_s:
                best_i, best_s = i, s
        return best_i

    def decide_box_card(self, names: list[str], state: GameState,
                        session: StrategySession, config) -> int:
        """武装箱/节点弹窗 4 选 1 装备卡(r104 接入策略模块;原 pick_box_card 内联迁此)。

        打分:①target.key_equips 命中 +100(成型加速压倒一切);
        ②合成材料通用性(_material_value 配方数;生命之花 7/轮滑鞋 6/光能电池 6);
        ③target.key_equips 的合成材料(两跳:该材料能合出 key_equip)命中 +30。
        无信息 fallback idx=0。返回索引(调用方点卡)。"""
        if not names:
            return 0
        from sr_od.application.currency_war.kernel.cw_prep_expect import (
            material_value as _material_value,
        )
        _key: set[str] = set()
        if session.target_comp is not None:
            _key = set(session.target_comp.key_equips or [])
        # key_equip 的合成材料(两跳)
        _key_mats: set[str] = set()
        if _key:
            try:
                # r130 修正:注册表字段是 **recipes**(cw_equipment_data._eq
                # recipes=(('量产型装甲','幸运星'),))——旧代码读 .materials
                # (不存在的属性)→ exception 被 swallow → 材料分静默失效,
                # 幸运星/量产型装甲从拿不到 key_equip 材料加分(局33b 箱仅开
                # 2 次的获取侧根因之一)。recipes 是「配方元组的元组」
                # (每条=(材料a,材料b)),逐条展开。
                from sr_od.application.currency_war.data.cw_equipment_data import (
                    EQUIPMENTS,
                )
                for ke in _key:
                    eq = EQUIPMENTS.get(ke)
                    for recipe in getattr(eq, 'recipes', ()) or ():
                        for m in recipe:
                            if m:
                                _key_mats.add(m)
            except Exception:   # noqa: BLE001  材料表缺失不加分
                pass
        best_i, best_s = 0, -1.0
        for i, n in enumerate(names):
            from sr_od.application.currency_war.decision_v2.scoring import (
                PICK_BIAS as _PB,
            )
            from sr_od.application.currency_war.decision_v2.scoring import (
                effect_pick_bias,
            )
            s = effect_pick_bias(session, n)
            if n in _key:
                s += _PB.box_key_equip
            if n in _key_mats:
                s += _PB.box_key_material
            s += float(_material_value(n))
            if s > best_s:
                best_i, best_s = i, s
        return best_i
    # ===== 备战决策环步级决策(strategy/03(原 doc 15§5.1-5.3) 参考实现;P1)=====

    def decide_prep_action(self, obs, session: StrategySession, config):
        """备战决策环步级决策 = strategy/03(原 doc 15§5.1-5.3) 参考实现(奖励收取 → 腾席链 → 主流程)。

        规则序(每步全量重判,先命中先出):
        1. 武装箱 overlay 开 → PickBoxCard(执行器默认选卡,v7 M-3;OpenBox 两步链第二步);
        2. 有箱 → OpenBox(箱白占席,先开=腾席+得装备;两步非一步,F1/L-5);
        3. 有球且有空席 → ClickSpheres(k=min(free, n);掉箱由规则 1/2 下步统筹);
        4. 有球无空席且 defer<2 → 腾席链一步(deploy 空位 > 卖杂件 > 升级 > 卖最弱 > DeferSpheres;
           ADR-0274 口述[32]:卖件优先于升级,boss 轮禁升级);
        5. 球箱皆无 或 defer≥2 → 主流程(买→部署→装备→出战,Run* 组合;P1 过渡)。

        obs P1 恒空字段(overlay_state/overlay_options/shop_cards/owned_equips)不依赖(§13.4);
        gold 仅 shop_open 且 obs.state fresh 时可信(关态读空,§5.2b M2)。
        """
        step = self._decide_prep_action_impl(obs, session, config)
        # r412(ADR-0274):息引擎 latch 采样(后置,ADR-0266 同款语义)——本笔
        # 决策读「此前」是否曾达满息,决策后置位(首达当轮自家不解锁);
        # default 栈此前无采样端 → 腾席链 b 的引擎门只剩花完≥50 单臂。
        try:
            if (getattr(obs, 'state_gold_trusted', False) and obs.state is not None
                    and obs.state.gold >= 50):
                session.v2_ever_full_interest = True
        except Exception:   # noqa: BLE001  采样 best-effort
            pass
        return step

    def _decide_prep_action_impl(self, obs, session: StrategySession, config):
        """decide_prep_action 的实现体(入口 docstring 见上层;拆分只为 latch 后置采样)。"""
        if obs.box_overlay_open:
            return PickBoxCard(card_idx=None)   # 执行器默认选卡(P1 住执行器;P5 上移策略)
        # r11 review P0:defer 门(对照收球规则 4)——OpenTome 失败反复重试时(执行器连败置
        # defer),无门活锁:M55 P2 全部 365 条决策全是 OpenTome 重试,71→84 金全程闲置、板面
        # 冻结硬吃两仗。典籍疑似误检/开不动 → 放弃走主流程;下轮环入口 defer 清零重判自愈。
        if getattr(obs, 'tomes', None) and session.defer_count < 2:
            return OpenTome()                   # 开典籍即腾席+触发星徽四选一(2026-08-16;选卡 loop 0i)
        if obs.boxes:
            return OpenBox()                     # 开箱即腾席 + 得装备
        if obs.spheres and obs.free_bench_slots > 0:
            # live 2026-08-14(1-2 实锤):商店开态奖励面板 [1257,140,1662,493] 与「刷新概率表」
            # 按钮 [945,360,1415,410] 重叠(x1257-1415∩y360-410)——HoughCircles 把按钮图形误检成
            # 假球,点击即开概率表弹窗(遮挡 → bail → 乒乓)。商店开 → 先关店,清洁面板上再收球。
            if obs.shop_open:
                return EnsureShopClosed()
            # live 2026-08-15(M12 1-9 实锤):owned 装备栏溢出到奖励区 → 道具图标被误检成假球,
            # 点击无效 → 验证失败循环 → bail×3 停机。defer 门扩到收球:反复失败(框架置 defer)后
            # 放弃收球走主流程;下轮环入口 defer 清零重判(真球可再收,自愈)。
            if session.defer_count >= 2:
                log.info('[cw][prep] 球疑假检(owned 溢出,点击反复失败)→ defer 跳过收球,走主流程')
                return self._main_flow_step(obs, session, config)
            return ClickSpheres(max_k=min(obs.free_bench_slots, len(obs.spheres)))
        if obs.spheres and obs.free_bench_slots <= 0 and session.defer_count < 2:
            return self._free_bench_step(obs, session, config)
        return self._main_flow_step(obs, session, config)

    @staticmethod
    def _is_boss_round(st: GameState) -> bool:
        """boss 轮判定(位面末节点;ADR-0274 口述[32])。

        判定源同 update_target 的 `_boss_window` 前两支:node_type=='boss'
        (权威源=备战节点行 read_node_sequence)或 round_num≥9 先验(supply
        节点例外——r9 补给不是 boss)。位面切换首战(plane≥2 r1)不含:那是
        pivot 冻结窗语义,不是「位面末节点」。
        """
        nt = st.node_type or ''
        return nt == 'boss' or (st.round_num >= 9 and nt != 'supply')

    @staticmethod
    def _cap_shortfall(st: GameState, target) -> int:
        """真缺人口缺口(ADR-0274 口述[32]「cap-deployed≥1 才可能考虑升级」):
        想上场(``_should_deploy`` 同链 a 判据)而 cap 装不下的 bench 件数——
        现有空位可吸纳的先扣,剩余即被 cap 卡住的真实缺口。缺口 0(板没满 /
        空位够装)→ 升级不产生可兑现的人口收益,不升。
        """
        cap = min(10, st.level or 1)
        dep = sum(1 for d in (st.deployed or []) if getattr(d, 'char_id', ''))
        vacancy = max(0, cap - dep)
        worth = [bc for bc in (st.bench or []) if bc is not None
                 if bc.char_id and cw_plan._should_deploy(bc, st, target)]
        return max(0, len(worth) - vacancy)

    @staticmethod
    def _levelup_engine_ok(st: GameState, session: StrategySession) -> bool:
        """息引擎门(ADR-0266 同款,ADR-0274 堵腾席链 b 这第三条升级通道):
        lv<5 豁免(过渡成型基线,r263);否则 = 本局曾达满息 latch
        (``v2_ever_full_interest``;default 栈采样端 r412 补)∨ 升级总成本
        花完后金仍 ≥50(``_INTEREST_FLOOR`` 满息结余)。"""
        if st.level < 5:
            return True
        if getattr(session, 'v2_ever_full_interest', False):
            return True
        from sr_od.application.currency_war.kernel.cw_economy import (
            clicks_to_next_level,
        )
        total = clicks_to_next_level(st) * cw_plan.xp_click_cost(st)
        return st.gold - total >= 50

    @staticmethod
    def _bench_junk_idx(st: GameState, character_priority: list[str],
                        target) -> int | None:
        """bench 杂件下标(off-target 且最低价值;腾席链 a2,ADR-0274)。

        判据 = ``_card_supports_target`` False(off-target;deploy 卖
        off-target 腾位的同一判源)+ 3合1 重复件保护(同 ``_weakest_bench_idx``)
        + ``_bench_sell_value`` 最低价值排序。无可卖杂件 → None(升级前置
        「杂件卖无可卖」即 a2 返 None)。
        """
        from collections import Counter
        if not st.bench:
            return None
        counts = Counter((bc.char_id, bc.star) for bc in st.bench
                       if bc is not None and bc.char_id)
        close = cw_plan._close_factions(st)
        best_i, best_v = None, None
        for i, bc in enumerate(st.bench):
            if bc is None or not bc.char_id or counts[(bc.char_id, bc.star)] >= 2:
                continue
            if cw_plan._card_supports_target(bc.char_id, bc.faction, st, target):
                continue
            v = cw_plan._bench_sell_value(bc, character_priority, close, target)
            if best_v is None or v < best_v:
                best_i, best_v = i, v
        return best_i

    def _free_bench_step(self, obs, session: StrategySession, config):
        """腾席链一步(§5.2;优先级是默认策略的选择,非框架强制;继承者可只覆盖本方法)。

        r100 审计必修①:target 改走 decision_target 单一入口——双轨期腾席链的上/卖
        判据同 plan 路径(配方驱动),消除双路径语义分叉(旧:步级读终局 target →
        r≥8 终局件上场 + 腾席链 c 无框架 keep 集可卖掉配方 carry)。
        """
        st = self._pseudo_state(obs, session)
        from sr_od.application.currency_war.kernel.cw_recipe import decision_target
        target = decision_target(session, st)
        # ⚖️ r94:同名在场守卫收口 cw_plan.deploy_legal(全局不变量单一源;5.1.7)。
        # 第14局 r9 实证:藿藿已在场,腾席链a把 bench 藿藿拖向空位 5 次全被游戏拒
        # → director 屏蔽 → 爻光滞留 bench 到局末。_should_deploy 顶部同守卫,
        # 此处显式跳过是为了「失败记忆」计数不污染(被拦的不再进候选循环)。
        _dep_names = cw_plan.deployed_name_set(st)
        # a. deploy 空位(零成本最优):bench 有过 _should_deploy 的角色 → DeployMove
        if obs.deploy_vacancy > 0:
            for bc in list(obs.bench_chars):
                if not cw_plan.deploy_legal(bc, _dep_names):
                    continue   # 同名已在场(游戏拒),留 bench 待 3合1 合并
                # r93 失败记忆:同角色拖拽已被游戏拒过 → 跳过(重试同目标=白烧环步,
                # 藿藿 5 连败实证;下一候选继续)。备战后对账刷新会自然重置状态。
                if session.deploy_fail_counts.get(bc.char_id, 0) >= 1:
                    continue
                if cw_plan._should_deploy(bc, st, target):
                    row, ok = cw_plan._pick_deploy_row(st, bc, target)
                    if not ok:
                        continue
                    occupied = obs.front_occupied if row == 'front' else obs.back_occupied
                    size = obs.front_size if row == 'front' else obs.back_size
                    empty = next((n for n in range(1, size + 1) if n not in occupied), None)
                    if empty is not None:
                        log.info(f'[cw][prep] 腾席链a:deploy空位 → 槽{bc.slot}({bc.char_id})'
                                 f' → {row}{empty}')
                        return DeployMove(from_slot=bc.slot, to_row=row, to_slot=empty)
        # a2. 卖杂件(ADR-0274,口述[32]「腾席需求优先用卖件解决」):bench 满
        # 先卖 off-target 杂件,再考虑升级。判据复用 deploy/_concentration 的
        # ``_card_supports_target``(off-target 判定单一源);价值排序复用
        # ``_bench_sell_value``(最低价值先卖);3合1 重复件保护同链 c。
        # target=None(reactive 早段)跳过——无 off-target 语义,防全卖。
        if target is not None:
            _j = self._bench_junk_idx(st, config.character_priority, target)
            if _j is not None and _j < len(st.bench):
                bc = st.bench[_j]
                log.info(f'[cw][prep] 腾席链a2:卖杂件 槽{bc.slot}({bc.char_id})'
                         '(ADR-0274 卖件优先于升级)')
                return SellBench(slot=bc.slot)
        # b. 升级扩容(cap+1 → 回 a):**三前置**(ADR-0274,口述[32],局72 r9
        # 腾席链连升 5→6→7 进 boss 剩 4 金实证):①boss 轮(位面末节点)一律
        # 禁升级腾席(升级的 cap 收益下轮才兑现,boss 当轮不上场);②真缺人口
        # (cap 缺口≥1——现有空位可吸纳的应上场件扣完后仍有富余,「cap-deployed
        # ≥1」即不缺);③息引擎门(ADR-0266 同款,堵这条第三升级通道的漏网)。
        # 前置不过直接落链 c(卖件/Defer),不再为 gold 真值空等(等待只为升级,
        # 不升就不必开店)。gold 需可信(framework F2 state_gold_trusted,MED-1 接线;
        # shop 开态 + fresh state 才信 —— 关态读空/缓存过期都会误判无金 → 链 c 误卖)
        # r364(局47 死循环修:50min 卡「警告→M-6→链b 要真值→EnsureShopOpen
        # →警告」40 次):**进展保证**——EnsureShopOpen 成功 ≠ 下一轮
        # state_gold_trusted 就 True(obs 快照刷新时机在环外),前提永不
        # 满足 = 无进展环。修:同环第 2 次进链 b 仍无真值 → 不再等,
        # 直接试 LevelUp(state.level_up_cost OCR 真值优先,缺省 4;
        # 金不够 gate 拒 → 自然落链 c,比死等好)。计数在环入口清
        # (director 环=同轮;跨轮重置)。
        if (st.level < 10 and not self._is_boss_round(st)
                and self._cap_shortfall(st, target) >= 1):
            # 退役批(ADR-0466/0467/0469) C5 换源(蓝图 §4.3-R1):升级门 committed 从 committed_from
            # 权威派生显式传入——fresh 帧不再依赖装配边界回填双轨标志
            # (漏回填=恒按已定型激进化放升级的病理修复;方向=门收紧)。
            from sr_od.application.currency_war.decision_v2.prep_brain import (
                committed_from,
            )
            _lk = getattr(session, 'free_bench_gold_wait', 0)
            if getattr(obs, 'state_gold_trusted', False) and obs.state is not None:
                session.free_bench_gold_wait = 0
                fresh = self._fresh_state(obs, session)
                if (cw_plan.level_up_gate(
                        fresh, target, committed=committed_from(session, fresh))
                        and self._levelup_engine_ok(fresh, session)):
                    log.info(f'[cw][prep] 腾席链b:升级 lv{fresh.level} gold={fresh.gold}(cap+1 → 回 a)')
                    return LevelUp()
            else:
                _lk2 = getattr(session, 'free_bench_gold_wait', 0) + 1
                session.free_bench_gold_wait = _lk2
                if _lk2 <= 1:
                    log.info('[cw][prep] 腾席链b:需 gold 真值 → EnsureShopOpen(开态重读)')
                    return EnsureShopOpen()
                # r366b(review A3 修,补齐注释宣称的中间态):第 2 次仍无
                # 真值 = 无进展环 → **先用 stale gold 试算 level_up_gate**
                # (level_up_cost 缺省 4;金够就升——升级破满席是最优解,
                # 卡 50min 代价 >> 一次可能失败的 LevelUp);gate 拒才落
                # 链 c 卖牌。零下行:LevelUp 失败被框架 fail 链兜住。
                _stale = self._pseudo_state(obs, session)
                _stale.level_up_cost = getattr(_stale, 'level_up_cost', None) or 4
                if (cw_plan.level_up_gate(
                        _stale, target, committed=committed_from(session, _stale))
                        and self._levelup_engine_ok(_stale, session)):
                    log.info('[cw][prep] 腾席链b:等待 %d 次无真值 → stale gold=%s 试升级'
                             '(cap+1 破满席;失败自然落链 c)',
                             _lk2, _stale.gold)
                    return LevelUp()
                log.info('[cw][prep] 腾席链b:gold 真值等待 %d 次无进展且 stale 试算不过 → 落链 c(局47 死循环修)',
                         _lk2)
        # c. 卖最弱(_weakest_bench_idx 含 3合1 重复件保护;全保护 → None)
        # r364 兜底:全保护(None)且 b 等待超限 → **强制卖 bench 首
        # 个非在场件**(保护是优化不是死锁理由;卡 50min 实证全保护
        # 也是死循环形态之一)。正常路径(未超限)不受影响。
        idx = cw_plan._weakest_bench_idx(st, config.character_priority, target)
        if idx is not None and idx < len(st.bench):
            bc = st.bench[idx]
            log.info(f'[cw][prep] 腾席链c:卖最弱 槽{bc.slot}({bc.char_id})')
            return SellBench(slot=bc.slot)
        if getattr(session, 'free_bench_gold_wait', 0) > 1:
            _dep_all = cw_plan.deployed_name_set(st)
            for bc in st.bench:
                if bc is not None and bc.char_id and bc.char_id not in _dep_all:
                    log.info(f'[cw][prep] 腾席链c(r364 强制):全保护死锁 → 卖 槽{bc.slot}'
                             f'({bc.char_id})')
                    return SellBench(slot=bc.slot)
        # d. 全是有用角色 → 留置(DeferSpheres;框架计 defer_count,门=2)
        log.info('[cw][prep] 腾席链d:无可卖/不可升 → DeferSpheres(球留置)')
        return DeferSpheres()

    def _main_flow_step(self, obs, session: StrategySession, config):
        """主流程推进(§5.3;Run* 组合 P1 过渡,阶段位 prep_phase 由 Director 环入口清零)。

        阶段位在**出动作时**前移(策略看不到执行结果;失败由框架 fail/屏蔽/恢复链兜住,
        失败动作不无限重提案)。M-6 门:进 RunBuyPhase 前保证 free>0,否则跳过买牌直奔部署
        (防 shop.py 内 _handle_bench_full 位置式卖,strategy/03(原 doc 15§8) P1 残留风险)。
        """
        if session.prep_phase <= 0:
            session.prep_phase = 1
            if obs.free_bench_slots <= 0:
                # M-6 门:free=0 跳过买牌(防 shop.py 内 _handle_bench_full 位置式卖)。
                # M24 卡死修(2026-08-16):满席且**无球**时旧逻辑直奔 RunDeploy → deploy-swap 卖
                # 拖拽失败(bug#1 变体)→ 警告不消 → 死循环;金不够升级时链 b 也不通。修:满席
                # 一律先过腾席链 a/b/c(deploy 空位/升级扩容/卖最弱 —— _weakest_bench_idx 是保护式
                # 卖,非位置式卖,与 M-6 门防的不冲突);链 d(DeferSpheres)不入 —— 无球时 defer 无意义,
                # 落回部署段保持原行为。
                log.info('[cw][prep] M-6 门:free=0 → 腾席链 a/b/c 破满席(买牌跳过)')
                step = self._free_bench_step(obs, session, config)
                if not isinstance(step, DeferSpheres):
                    return step
                return self._main_flow_step(obs, session, config)   # 链全空 → 部署段
            return RunBuyPhase()
        if session.prep_phase == 1:
            session.prep_phase = 2
            return RunDeploy()
        if session.prep_phase == 2:
            session.prep_phase = 3
            return RunEquip()
        # ⚖️ r23(强度表消费,p1-1 掉 25.5 实证):空板/严重缺员出战守卫——54 局 5 次空板出战
        # (lv4,dep=0),p1-1/p1-7 高强度节点掉 24-29 血。deployed 有 tracking(bench/deployed chars)
        # 且板上 0 人 → 不出战,回部署段(RunDeploy 会拖 bench 上场);bench 也空(真无牌)才放行
        # (开局首轮无牌是正常态,游戏会给保底板?不——p1-1 开局必能买到牌,空板=部署失败,重试)。
        _dep_n = len(obs.deployed_chars or [])
        _bench_n = len(obs.bench_chars or [])
        if _dep_n == 0 and _bench_n > 0 and session.prep_phase_retry < 2:
            session.prep_phase_retry += 1
            session.prep_phase = 1   # 回部署段重试(bench 有人没上去)
            log.info('[cw][prep] 空板出战守卫:板上 0 人 bench %d 人 → 回部署段(p1-1 类节点掉 24+ 血)',
                     _bench_n)
            return RunDeploy()
        return StartBattle()

    def _pseudo_state(self, obs, session: StrategySession) -> GameState:
        """从 session tracking 组装决策用 GameState(环内轻量,SIFT 重读只在环入口)。"""
        st = GameState()
        st.board = {}
        for bc in session.tracked_deployed:
            if bc is None:   # ADR-0392 槽位表空槽
                continue
            if bc.faction and bc.faction != '?':
                st.board[bc.faction] = st.board.get(bc.faction, 0) + 1
        st.bench = list(session.tracked_bench_chars)
        st.deployed = list(session.tracked_deployed)
        st.level = session.last_level_obs or (
            session.last_state.level if session.last_state is not None else 1)
        if obs is not None and getattr(obs, 'state_gold_trusted', False) and obs.state is not None:
            st.gold = obs.state.gold   # 仅 F2 可信标记时采用(gold 关态读空,MED-1)
            st.plane = obs.state.plane
            st.round_num = obs.state.round_num
        elif session.last_state is not None:
            st.plane = session.last_state.plane
            st.round_num = session.last_state.round_num
        # r69 review:hp 过新鲜度门(陈旧 last_hp 不进 pseudo state;门单源 cw_strategy.gated_hp,
        # 现读基准 = last_state.hp 框架末次读值,None 时 100 默认)。
        from sr_od.application.currency_war.cw_strategy import gated_hp
        _t = (st.plane - 1) * 9 + st.round_num if (st.plane and st.round_num) else None
        _cur_hp = session.last_state.hp if session.last_state is not None else 100
        st.hp = gated_hp(_cur_hp, session, _t)
        # r101 审计必修①(5ba9b0a6 T6 实证):漏拷 dual_track_phase → 腾席链的
        # decision_target 恒走非双轨分支退终局 comp,r100 必修①(步级路径迁移)
        # 空转——r≥8 终局件提前上场+配方 carry 可被卖。迁移迁移批 2(方向层接管)(方向层接管) 起 committed 语义
        # = cw_intention 权威派生(读端 committed_from 单点换源,P1 同
        # commit 面),此处传 state 供 plane 判定。
        from sr_od.application.currency_war.decision_v2.prep_brain import (
            committed_from,
        )
        st.dual_track_phase = not committed_from(session, st)
        # 迁移审计 w148(git 历史)(ADR-0358,迁移审计 w92(git 历史) 修法 A):owned 穿戴池搬运链读端——EquipAll 写的
        # session 快照拷入决策 state.equips(decisions 遥测携带,win_model 持有
        # 面特征可见;空快照=默认 [] 语义不变)。
        st.equips = list(session.last_owned_equips)
        # r412(ADR-0274):node_type 补拷——腾席链 b 的 boss 轮禁升判定需要;
        # 权威源 = 备战节点行(prep_director 存 session.node_type_current),
        # 退化 last_state.node_type。
        st.node_type = (getattr(session, 'node_type_current', None)
                        or (session.last_state.node_type if session.last_state is not None else '')
                        or '')
        return st

    def _fresh_state(self, obs, session: StrategySession) -> GameState:
        """shop 开态 fresh state(obs.state)+ bench tracking seed(gold 可信,腾席链 b 用)。"""
        st = obs.state if obs.state is not None else GameState()
        fresh = st.copy()
        if session.tracked_bench_chars:
            fresh.bench = list(session.tracked_bench_chars)
        return fresh


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
                if 0 <= a.deployed_idx < len(state.deployed or []) \
                        and state.deployed[a.deployed_idx] is not None:   # ADR-0392 空槽
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
            from sr_od.application.currency_war.kernel.cw_evolution import (
                EvolutionState,
            )
            session.v3_evolution = EvolutionState()
        if session.v3_alarm is None:
            session.v3_alarm = BloodAlarmTracker()
