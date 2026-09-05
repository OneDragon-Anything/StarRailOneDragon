"""货币战争 主流程驱动核(CwFlowStrategy;自 decision_v2/strategy.py 迁入,
策略统一迁移批——底稿 MAP ⓪ A1「迁移白名单」)。

辖域 = mandate_v1 未覆写的域实现:

- 生命周期钩子(create_session/on_match_start/on_round_end/on_match_end
  ——含意向/演进/报警/轮键跨局清零与感知质量门);
- 战略层 ``update_target``(意向状态机驱动 + P1 配方对物化,两臂共用
  的换线权威,R197 症2 裁决);
- pick 族(decide_invest/supply/encounter/megastar/partner/planner/
  star_tome/wish_trial/box_card);
- deprecated 兼容别名 decide_prep_action(W971);
- 商店单动作接口 decide_shop_action(ADR-0517,委托 mandate_v1/shop)。

**旧备战骨架已删(ADR-0517 迁移批,flow/screen_op.md §8.2 裁决)**:
_decide_prep_action_impl/_main_flow_step 相位机/_free_bench_step 腾席链/
_deploy_up_candidates/_bench_junk_idx/_pseudo_state/_fresh_state 及私有
helper(_is_boss_round/_cap_shortfall/_levelup_engine_ok)= 零生产调用死码
簇(测试直调不算;live 备战决策链 = cw_screen_prep → mandate_v1.bridge →
entry.emit 三遍编排);传递性死码 kernel/cw_deploy_seat(_should_deploy
族)与 session 暂存字段(prep_phase/prep_phase_retry/free_bench_gold_wait)
同批清除。

本类 ``_abstract=True``(中间辅助 ABC,StrategyManager 不注册;
decide_prep_screen/decide_shop_screen 保持 abstract——具现 =
``strategies.impl.mandate_v1.bridge.MandateV1Strategy``,生产注册壳 =
``strategies/mandate_v1_strategy.py``)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel import cw_comps, cw_events
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_discipline_rules import (
    BloodAlarmTracker,
)
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
    rollback_weakest,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    IntentionState,
    hoard_target_set,
    p1_early_pair,
    pair_target_comp,
    update_intention,
)
from sr_od.application.currency_war.kernel.cw_performance import (
    HP_CONFIDENCE_THRESHOLD,
    RoundOutcome,
)
from sr_od.application.currency_war.kernel.cw_plane_table import NODES_PER_PLANE
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    Action,
    GameState,
    MatchOutcome,
    PickEvent,
)
from sr_od.application.currency_war.strategies.impl.cw_strategy import (
    CwStrategy,
    StrategySession,
)
from sr_od.application.currency_war.strategies.impl.pick_bias import (
    PICK_BIAS,
    effect_pick_bias,
)

if TYPE_CHECKING:
    pass

# config 属 app 桶,impl 桶禁 import(cw_strategy.py 字符串注解先例);
# 实例由调用方按参注入。
CurrencyWarConfig = 'CurrencyWarConfig'

#: 谷底回滚线(点6:转型中遭遇单场掉血 >15 → 回滚一件最弱替换位;
#: 与点4 报警线 20/30 分层并存——15 管转型期单场,20/30 管全局累计)
VALLEY_ROLLBACK_LOSS: int = 15


class CwFlowStrategy(CwStrategy):
    """主流程驱动核(生命周期 + 战略层意向 + pick 族 + 备战主流程栈)。

    方法体逐字平移自 ``decision_v2/strategy.py`` DecisionV2Strategy
    同名方法(出处见各方法 docstring;行为零变更由 sim 契约锁承载)。
    """

    STRATEGY_ID: str = ''            # 中间辅助 ABC,不注册(_abstract=True)
    STRATEGY_NAME: str = '主流程驱动核(内部基类)'
    _abstract: bool = True

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
        # (v3_hoard 囤货通道已随 v2 退役链删除——A6 裁决:写端活/读端零,
        #  囤货视野通道语义消亡,session 字段保留历史 schema 缺省。)
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
        # DP 姿态轮缓存载体:初始化(每轮 decide_shop_screen 重算)
        session.v3_phase = 'FORM'
        session.v3_form_ok = False
        session.v3_form_score = 0.0
        session.v3_dp_posture = None
        # 镜像族轮键戳(写者=write_shop_mirrors 单一源;None=本轮未写,
        # sim 引擎缺写守卫消费——见 write_shop_mirrors docstring)
        session.v3_mirror_key = None
        # `w224_handoff/`/ADR-0399:P2 承接快照(观测层;None=未进 P2/未计算)
        session.v3_handoff = None
        session.v3_handoff_plane = None
        # `w227_handoff_gate/`/ADR-0400:P1 末窗承接门缺口(filters 每段写;跨局清零)
        session.v3_handoff_gap = 0
        # 迁移审计 w238(git 历史)/ADR-0403:boss 投影 hp 披露(ADR-0411 起投影无条件启用,
        # 末窗 handoff_gate_gap 写;None=非末窗,判读「boss 后投影 hp」面)
        session.v3_handoff_hp_proj = None
        # W332b:release 泄息指令(每轮 decide_shop_screen 重算)与轮内累计花费
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
        if not node_type:
            # supply 失活治本(supply失活升级线 第6/7次复现):空 node_type 轮
            # 被 BloodAlarmTracker 战斗节点门整轮丢弃 → 掉血数据缺失、生死窗
            # 判读缺页。修法 = node_type 空值回落**对局档案装配轮行序**——
            # 档案(match_archive)按局归并轮次、轮行自带序,但其装配是局后
            # assemble_pending 产物,on_round_end 时点不可得 → 同一轮行序的
            # 局内单一源 = 位面节点台账(PlaneNodeLedger:按位面归并、轮行
            # 自带序;位面详情采集/投资环境重读两写点,15 号稿 §1 行 10
            # 「权威表」),按 (plane, round_num) 查同轮 node_type;查不到 =
            # 照旧空串(不猜)+ 分键留证。
            node_type = self._alarm_node_type_fallback(
                session, plane, getattr(obs, 'round_num', None)
                or state.round_num)
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

    def _alarm_node_type_fallback(self, session, plane, round_num) -> str:
        """掉血报警 node_type 空值回落(→ 生产词汇表 token | 空串)。

        命中 = 台账该位次有非空类型 → 映射回生产词表喂
        BloodAlarmTracker(掉血数据恢复);未命中(表缺/越界/该位次 None)
        = 照旧空串不猜 + ``blood_alarm_node_type_fallback`` 分键留证
        (单一源 = kernel.cw_telemetry_exit 常量)。best-effort 不抛。"""
        token: str | None = None
        try:
            from sr_od.application.currency_war.kernel.cw_state import (
                ledger_node_type,
            )
            token = ledger_node_type(session, plane, round_num)
        except Exception:   # noqa: BLE001  台账缺失不阻塞结算喂入
            token = None
        # 词表单一源 = kernel.cw_state.NODE_TOKEN_TO_WORD(落地审 C1:自维护
        # 删减副本漏 elite 致精英轮掉血恢复失效,从源头消掉)。
        try:
            from sr_od.application.currency_war.kernel.cw_state import (
                NODE_TOKEN_TO_WORD,
            )
            nt = NODE_TOKEN_TO_WORD.get(str(token), '') if token else ''
        except Exception:   # noqa: BLE001
            nt = ''
        try:
            from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
                DEFECT_KIND_BLOOD_ALARM_NODE_FALLBACK,
                record_defect,
            )
            record_defect(
                'blood_alarm', DEFECT_KIND_BLOOD_ALARM_NODE_FALLBACK,
                expected=f'node_type 非空(台账={token if token else "缺"})',
                observed=f'回落={nt if nt else "空串(照旧)"}',
                plane=int(plane or 0), round_num=int(round_num or 0),
                gap_large=False, auto_resolved=bool(nt),
                verdict=('台账命中-掉血数据恢复' if nt
                         else '台账未命中-照旧空串(不猜)+分键留证'),
                reader_source='on_round_end_node_type_fallback',
                note='supply 失活治本:空 node_type 轮掉血数据不丢')
        except Exception:   # noqa: BLE001  遥测 best-effort
            pass
        if nt:
            log.info('[cw][d2] node_type 空值回落:台账 %s(%s-%s)→「%s」'
                     '(掉血数据恢复)', token, plane, round_num, nt)
        return nt

    def create_session(self, config) -> StrategySession:
        """空白 session(rng 留默认,由 run loop 按 ``config.strategy_seed`` 覆盖)。

        新局起点顺带复位布局未知态计数(落地审 C4:跨局残留会让新局开局
        ——level 未 observed/CV 高发不可判期——提前吃冻结)。"""
        try:
            from sr_od.application.currency_war.kernel.cw_state import (
                reset_layout_unknown_state,
            )
            reset_layout_unknown_state()
        except Exception:   # noqa: BLE001  复位 best-effort,不阻 session 创建
            pass
        return StrategySession()

    def on_match_end(self, session: StrategySession, config, outcome: MatchOutcome) -> None:
        """P1 no-op(outcome 字段全默认,真实结算屏 OCR 属 P1.5)。"""
        pass

    # ===== 镜像族观察写者(mandate_v1 单臂)=====

    def write_shop_mirrors(self, state: GameState,
                           session: StrategySession) -> None:
        """逐帧恢复 ``v3_form_score`` 写者(纯遥测观测面)。

        背景:该字段自 mandate_v1 换核后仅剩 on_match_start 初始化
        0.0,两批 sim 849 帧零非零(sim57 判读报告 §B5)——仪表缺
        写者,非车没走。口径 = ADR-0346/W114 设计语义的
        **上场(deployed)连续量**:过渡体系达成数(``cw_deploy_logic.
        engines_count`` 四体系单一源)+ 配方档小数(``cw_line_defs.
        recipe_tier``/``RECIPE_BASE`` × ``registry.rung_frac_per_
        recipe_tier``),封顶 2 档除 2 归一到 [0,1];bench 囤件不计入
        (「上场了才算战力」的裁决口径)。

        边界:本方法**只恢复 form_score 一个键**——``v3_phase``/
        ``v3_form_ok`` 的 v2 相位机写端仍属退役语义(测试仓
        test_cw_metric_mirror_fix 锁 phase=''/form_ok=False 保持),
        ``v3_mirror_key`` 轮键戳照常盖章(键语义 =「本轮已写」,sim
        引擎缺写守卫据此不重复触发)。纯遥测恢复:该字段不进任何
        判据(kernel/cw_registry.py「form_score 降级纯遥测观测,不进
        判据」注记),写者本身零行为面。
        """
        from sr_od.application.currency_war.kernel.cw_battle_calib import (
            board_factions_of,
        )
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            engines_count,
        )
        from sr_od.application.currency_war.kernel.cw_line_defs import (
            RECIPE_BASE,
            recipe_tier,
        )
        deployed = [d for d in
                    (getattr(state, 'deployed', None) or [])
                    if d is not None]
        if not deployed:
            # 实机落位补缺(g_20260906_021859/034515 两局全帧 0.0 实证):
            # 商店观察帧(state=shop_state_frame)只播种 bench
            # (cw_op_buy_cards 入口 tracked_bench_chars 播种段),
            # ``deployed`` 列表恒空 → engines/frac 恒 0 → form_score 恒 0,
            # 写者调用点本身已接(decide_shop_action 决策核入口)。回退源 =
            # session.tracked_deployed(执行记录槽位表,单元素带 char_id,
            # 与 assembly/cw_observation 同一消费源),空 = 板面真空的
            # 事实态,照写 0 不虚构。
            deployed = [d for d in
                        (getattr(session, 'tracked_deployed', None) or [])
                        if d is not None]
        bf = board_factions_of(deployed)
        dep_names = frozenset(
            (getattr(d, 'char_id', '') or '') for d in deployed)
        engines = engines_count(bf, dep_names)
        frac = min(recipe_tier(bf) / RECIPE_BASE, 1.0)
        x = min(2.0, float(engines)
                + getattr(self.registry, 'rung_frac_per_recipe_tier', 0.3)
                * frac)
        session.v3_form_score = max(0.0, min(1.0, x / 2.0))
        session.v3_mirror_key = (getattr(state, 'plane', 1) or 1,
                                 getattr(state, 'round_num', 0) or 0)

    # ===== 战略层:意向分层(点0)=====

    def update_target(self, state: GameState, session: StrategySession,
                      config) -> None:
        """战略层:驱动意向状态机(锁线/撤销/强制锁线),写
        ``target_comp``(COMP_LIBRARY v2 真 Comp)+ ``v3_core_names``(carry 标签
        裁决);囤货集仅作意向派生视图与日志读数(A6:v3_hoard 通道随 v2 删)。"""
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
            # (P1→P2 接口机制·①锁线 v2 后处理已随五开关定谳清理删除,
            # ADR-0487:W793 A/B 触发面全开火仍主判据双败。[23] 锚经
            # update_intention 信号驱动锁线,不受影响。)
        comp = get_comp(ist.locked_comp) if ist.locked_comp else None
        # `w578_target_comp_wire/`:P1 配方锁帧物化——ADR-0357 后 locked_comp 在配方锁局恒空,
        # session.target_comp 恒 None → 部署选人/评分管线/投资装备钩子等
        # 既有 target 消费者全盲(实机断链:引擎件躺 bench、散脸占板)。
        # 把已锁配方对物化为伪 comp(单一口径=cw_intention.pair_target_comp
        # docstring);①锁局 locked_comp 优先,本分支不辖;P2+/空对不物化
        # (不越 ADR-0357 辖域)。
        if comp is None and state.plane == 1:
            # P1 目标不空窗(经济冻结批):配方对退场帧(支持度掉出锁门槛/
            # 断供驱逐重派生为空)不落 None——按 p1_early_pair 无门槛 top-2
            # 方向物化(单一源=cw_intention.p1_early_pair,ADR-0372 买入门
            # 同款读法:空窗期同样有方向,不该因为不够锁而没方向)。旧形态
            # None → 消费者(部署/评分/准备域引擎)全盲,0 买 0 刷经济冻结
            # (实机局 g_20260904_042657 p1r7-r9)。P1 外不辖(维持旧辖域:
            # P2+ 终局线走 locked_comp / 强制 assignment 通道)。
            pair = tuple(getattr(ist, 'p1_pair', ()) or ()) \
                or p1_early_pair(state, ist)
            if pair:
                comp = pair_target_comp(pair)
        session.target_comp = comp
        hoard = hoard_target_set(state, ist)
        session.v3_core_names = set(comp.core_chars) if comp else set()
        if ist.last_event and ist.last_event not in (
                getattr(session, 'v3_last_intention_event', '')):
            log.info('[cw][d2] 意向 %s mode=%s(%s)',
                     ist.phase, hoard.mode, ist.last_event)
        session.v3_last_intention_event = ist.last_event

    # ===== pick 族(事件/选卡决策;判据单源 = kernel cw_events/cw_comps)=====

    def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                      state: GameState, session: StrategySession, config) -> PickEvent:
        """投资策略/投资环境 3 选 1。P1 两 kind 同一实现(委托 ``decide_event``);分表现 P2+ 议题。
        ``state.board`` 由调用方传空 stub(overlay 叠备战时 board 不可读,§11.7)。
        ADR-0134:strategy kind 传 session.target_comp(星徽套组/专属强化对齐 target = 成型加速,
        comp 匹配分压倒品质先验)。ADR-0144 修订:env kind 也传 —— 开局环境屏 comp 未定(None,
        行为同旧,阵营定向走 select_comp env_fit);**局中环境屏**(如 联席决策 2-6 节点)comp 已定,
        概念股/邀请/契约阵营匹配定序门(ENV_FACTION_MATCH_FLOOR,ADR-0524 定形:
        三档值=category 定序档位,禁读基数)生效。
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
        ⚠️ OCR 未就绪(char_id 全空 → 匹配恒失败 → idx=0 = 今天盲点左候选,随阶段5)。
        (强化角色维度已随 megastar_enhance_enabled 开关族删除——旧方案
        清退批,清查报告 OLD_MIX_AUDIT §1.3;MegastarPick.enhance_char_id
        字段保留恒 None,兼容既有遥测/执行面读取。)"""
        available = [o.char_id for o in options if o.char_id]
        chosen_name = cw_comps.select_megastar(state, session.target_comp, available)
        if chosen_name:
            for o in options:
                if o.char_id == chosen_name:
                    return MegastarPick(
                        idx=o.idx,
                        reason=f"select_megastar 命中 {chosen_name}")
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
            s = effect_pick_bias(session, obj)
            if '金币' in obj:
                s += PICK_BIAS.wish_gold
            if any(f in obj for f in (_tgt_facs | _fw_facs)):
                s += PICK_BIAS.wish_faction
            if '刷新' in obj or '购买' in obj:
                s += PICK_BIAS.wish_operation
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
            s = effect_pick_bias(session, n)
            if n in _key:
                s += PICK_BIAS.box_key_equip
            if n in _key_mats:
                s += PICK_BIAS.box_key_material
            s += float(_material_value(n))
            if s > best_s:
                best_i, best_s = i, s
        return best_i

    # ===== 备战决策环步级决策(strategy/03(原 doc 15§5.1-5.3) 参考实现;P1)=====

    def decide_prep_action(self, obs, session: StrategySession, config):
        """备战决策环步级决策(deprecated 兼容薄委托,W971 §2 黑板模式)。

        旧签名 → 写 ``session.prep_obs_frame``(黑板写路径)→ 新接口
        :meth:`decide_prep_screen`(同一决策核,行为等价由构造保证)。
        规则序 docstring 见新接口。
        """
        session.prep_obs_frame = obs
        return self.decide_prep_screen(session, config)

    def decide_shop_action(self, session: StrategySession,
                           config: CurrencyWarConfig) -> Action:
        """商店单动作决策接口(ADR-0517 决策 1/2/5)。

        输入 = ``session.shop_state_frame``(黑板:入口观察/单动作投影/
        sim 引擎写);输出 = **恰一个动作**,全函数永不 None——「无动作
        可做」由 ``CloseShop`` 恒可用终结表达(决策 5/6)。决策本体 =
        ``mandate_v1/shop.decide_shop_action``(选择序 = 既有波批优先级
        逐帧取首项)。执行侧单动作循环逐帧调用本接口;sim/兼容路径走
        :meth:`decide_shop_screen` 驱动器(同核循环化)。观察帧缺失 =
        观察层失约,抛错(禁静默按空态决策)。
        """
        from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
            shop,
        )
        state = session.shop_state_frame
        if state is None:
            raise ValueError(
                'decide_shop_action: session.shop_state_frame 缺失'
                '(黑板契约:入口观察段是唯一写者;None=观察层失约,'
                '禁静默按空态决策)')
        # v3_form_score 逐帧镜像写者(纯遥测,零行为面;口径与边界见
        # write_shop_mirrors docstring)。写位 = 决策核入口 = 生产单
        # 动作循环与 sim decide_shop_screen 驱动器共同必经点。
        self.write_shop_mirrors(state, session)
        return shop.decide_shop_action(state, session, config,
                                       registry=self.registry)
