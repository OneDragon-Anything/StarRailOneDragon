"""货币战争 主流程驱动核(CwFlowStrategy;自 decision_v2/strategy.py 迁入,
策略统一迁移批——底稿 MAP ⓪ A1「迁移白名单」)。

方法体自 ``decision_v2/strategy.py`` **原样平移,零行为变更**(活路径
行为零变更红线;sim 契约锁重指向后全绿即为证)。辖域 = mandate_v1
未覆写的域实现:

- 生命周期钩子(create_session/on_match_start/on_round_end/on_match_end
  ——含意向/演进/报警/轮键跨局清零与感知质量门);
- 战略层 ``update_target``(意向状态机驱动 + P1 配方对物化,两臂共用
  的换线权威,R197 症2 裁决);
- pick 族(decide_invest/supply/encounter/megastar/partner/planner/
  star_tome/wish_trial/box_card);
- 备战主流程栈(_main_flow_step 相位机 + dd-037 部署发射门 +
  腾席链 a/a2/b/c/d + _pseudo_state 决策态组装);
- deprecated 兼容别名 decide_prep_action(W971)。

**不迁**(v2 专属,随退役批删除):decide_shop_screen 旧实现/
write_shop_mirrors/_decide_shop_plan 四层管线。

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
from sr_od.application.currency_war.kernel.cw_deploy_seat import (
    _bench_sell_value,
    _card_supports_target,
    _close_factions,
    _pick_deploy_row,
    _should_deploy,
    _weakest_bench_idx,
    deploy_legal,
    deployed_name_set,
    level_up_gate,
)
from sr_od.application.currency_war.kernel.cw_discipline_rules import (
    BloodAlarmTracker,
)
from sr_od.application.currency_war.kernel.cw_economy import xp_click_cost
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
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    ClickSpheres,
    DeferSpheres,
    DeployMove,
    LevelUp,
    OpenBox,
    OpenShop,
    OpenTome,
    PickBoxCard,
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
    GameState,
    MatchOutcome,
    PickEvent,
)
from sr_od.application.currency_war.strategies.impl.cw_strategy import (
    CwStrategy,
    StrategySession,
    gated_hp,
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
            # W970 批 C:EnsureShopClosed 退役 → OpenShop(read_only) 编排
            # (幂等开店[已开不点]→观察刷新→不调商店决策→CwOpCloseShop→回备战,同收
            # 「清洁面板」效果)。
            if obs.shop_open:
                return OpenShop(read_only=True)
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
                 if bc.char_id and _should_deploy(bc, st, target)]
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
        total = clicks_to_next_level(st) * xp_click_cost(st)
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
        close = _close_factions(st)
        best_i, best_v = None, None
        for i, bc in enumerate(st.bench):
            if bc is None or not bc.char_id or counts[(bc.char_id, bc.star)] >= 2:
                continue
            if _card_supports_target(bc.char_id, bc.faction, st, target):
                continue
            v = _bench_sell_value(bc, character_priority, close, target)
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
        # ⚖️ r94:同名在场守卫收口 kernel.cw_deploy_seat.deploy_legal(全局不变量单一源;5.1.7)。
        # 第14局 r9 实证:藿藿已在场,腾席链a把 bench 藿藿拖向空位 5 次全被游戏拒
        # → director 屏蔽 → 爻光滞留 bench 到局末。_should_deploy 顶部同守卫,
        # 此处显式跳过是为了「失败记忆」计数不污染(被拦的不再进候选循环)。
        _dep_names = deployed_name_set(st)
        # a. deploy 空位(零成本最优):bench 有过 _should_deploy 的角色 → DeployMove
        if obs.deploy_vacancy > 0:
            for bc in list(obs.bench_chars):
                if not deploy_legal(bc, _dep_names):
                    continue   # 同名已在场(游戏拒),留 bench 待 3合1 合并
                # r93 失败记忆:同角色拖拽已被游戏拒过 → 跳过(重试同目标=白烧环步,
                # 藿藿 5 连败实证;下一候选继续)。备战后对账刷新会自然重置状态。
                if session.deploy_fail_counts.get(bc.char_id, 0) >= 1:
                    continue
                if _should_deploy(bc, st, target):
                    row, ok = _pick_deploy_row(st, bc, target)
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
            from sr_od.application.currency_war.kernel.cw_intention import (
                committed_from,
            )
            _lk = getattr(session, 'free_bench_gold_wait', 0)
            if getattr(obs, 'state_gold_trusted', False) and obs.state is not None:
                session.free_bench_gold_wait = 0
                fresh = self._fresh_state(obs, session)
                if (level_up_gate(
                        fresh, target, committed=committed_from(session, fresh))
                        and self._levelup_engine_ok(fresh, session)):
                    log.info(f'[cw][prep] 腾席链b:升级 lv{fresh.level} gold={fresh.gold}(cap+1 → 回 a)')
                    return LevelUp()
            else:
                _lk2 = getattr(session, 'free_bench_gold_wait', 0) + 1
                session.free_bench_gold_wait = _lk2
                if _lk2 <= 1:
                    # W970 批 C(§4.3.6 腾席链 b 读数性开店):EnsureShopOpen 退役 →
                    # OpenShop(read_only)——开店成功 = 本轮有进展(r364 进展保证语义
                    # 由 CwOpOpenShop 成功承担)。
                    log.info('[cw][prep] 腾席链b:需 gold 真值 → OpenShop(read_only) 开态重读')
                    return OpenShop(read_only=True)
                # r366b(review A3 修,补齐注释宣称的中间态):第 2 次仍无
                # 真值 = 无进展环 → **先用 stale gold 试算 level_up_gate**
                # (level_up_cost 缺省 4;金够就升——升级破满席是最优解,
                # 卡 50min 代价 >> 一次可能失败的 LevelUp);gate 拒才落
                # 链 c 卖牌。零下行:LevelUp 失败被框架 fail 链兜住。
                _stale = self._pseudo_state(obs, session)
                _stale.level_up_cost = getattr(_stale, 'level_up_cost', None) or 4
                if (level_up_gate(
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
        idx = _weakest_bench_idx(st, config.character_priority, target)
        if idx is not None and idx < len(st.bench):
            bc = st.bench[idx]
            log.info(f'[cw][prep] 腾席链c:卖最弱 槽{bc.slot}({bc.char_id})')
            return SellBench(slot=bc.slot)
        if getattr(session, 'free_bench_gold_wait', 0) > 1:
            _dep_all = deployed_name_set(st)
            for bc in st.bench:
                if bc is not None and bc.char_id and bc.char_id not in _dep_all:
                    log.info(f'[cw][prep] 腾席链c(r364 强制):全保护死锁 → 卖 槽{bc.slot}'
                             f'({bc.char_id})')
                    return SellBench(slot=bc.slot)
        # d. 全是有用角色 → 留置(DeferSpheres;框架计 defer_count,门=2)
        log.info('[cw][prep] 腾席链d:无可卖/不可升 → DeferSpheres(球留置)')
        return DeferSpheres()

    def _deploy_up_candidates(self, obs, session: StrategySession) -> list[int]:
        """部署段发射门(dd-037):用与执行方同源的 kernel 纯函数算「谁该上场」。

        单一源 = ``cw_deploy_logic.select_deployments``(围栏/成对/cap/去重/
        配方底线/板空保底全在其内);本方法只做输入装配,不自持任何判据。
        输入源 = 观察帧 obs 的 SIFT bench/deployed 身份 + session tracking
        板面(与 _pseudo_state 同源);cap 用 level 链(cap≈level,D-19;宝钻/
        诅咒加成的偏差方向 = 发射门可能保守留 bench——留 bench 是合法稳态,
        比误判「有部署可做」再进死循环便宜)。SIFT 未识别的 bench 件走纯函数
        的 fail-open(照旧上)→ 门只在「身份可判且全被规则留 bench」时收口。
        返回 up 下标列表(对 obs.bench_chars 紧凑序);空 = 计划空,不发射。
        """
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            select_deployments as _sel,
        )
        bench = [bc for bc in (obs.bench_chars or []) if bc is not None]
        if not bench:
            return []
        deployed = [d for d in (obs.deployed_chars or []) if d is not None]
        deployed_cids = {d.char_id for d in deployed if getattr(d, 'char_id', '')}
        deployed_fac: dict[str, int] = {}
        from sr_od.application.currency_war.data.cw_chars import CHARACTERS
        for _d in deployed:
            _ch = CHARACTERS.get(getattr(_d, 'char_id', ''))
            if _ch is None:
                continue
            for _f in ((_ch.factions or ()) + (_ch.flows or ())):
                deployed_fac[_f] = deployed_fac.get(_f, 0) + 1
        st = self._pseudo_state(obs, session)
        board = dict(st.board)
        cap = min(10, st.level or 1)
        target_factions: set[str] = set()
        target_cores: set[str] = set()
        fw_carry: set[str] = set()
        locked_factions: frozenset[str] = frozenset()
        from sr_od.application.currency_war.kernel.cw_recipe import (
            decision_target as _dt_fn,
        )
        try:
            _tgt = _dt_fn(session, st)
            if _tgt is not None:
                target_factions = set(_tgt.all_factions)
                target_cores = set(_tgt.core_chars)
        except Exception:   # noqa: BLE001  目标读失败 → 空集(fail-open 同身份未判)
            pass
        _fw = getattr(session, 'transition_framework', '')
        if _fw:
            from sr_od.application.currency_war.kernel.cw_transition import (
                FRAMEWORK_FACTIONS,
                TRANSITION_PACK,
            )
            target_factions |= set(FRAMEWORK_FACTIONS.get(_fw, ()))
            fw_carry = {n for n, (f, t) in TRANSITION_PACK.items()
                        if (f == _fw or f == '通用') and t != 'drop'}
        try:
            from sr_od.application.currency_war.kernel.cw_intention import (
                locked_faction_scope as _lfs,
            )
            locked_factions = _lfs(getattr(session, 'v3_intention', None)) \
                or frozenset()
        except Exception:   # noqa: BLE001  锁定帧读失败 → 空集=回旧行为
            locked_factions = frozenset()
        up, _held = _sel(
            bench, deployed_cids=deployed_cids, deployed_fac=deployed_fac,
            board=board, cap=cap,
            target_factions=target_factions, target_cores=target_cores,
            fw_carry=fw_carry, locked_factions=locked_factions)
        return up

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
            # W970 批 C(RunBuyPhase 解体):主流程买牌段改发显式开店意图,
            # 流程层(cw_screen_prep._open_shop_phase)编排 开店→商店动作循环→
            # CwOpCloseShop→节点探针;组合壳 BuyShopCards 已随退役批删除(决策核只发显式开店意图)。
            return OpenShop()
        if session.prep_phase == 1:
            session.prep_phase = 2
            # dd-037 单一源谓词门:发射前用与执行方(CwOpDeploy)同源的
            # ``cw_deploy_logic.has_deployable`` 判「还有没有部署可做」——
            # 计划为空(全部候选被配方底线/去重/cap 等规则留 bench)时不发射
            # RunDeploy(bench=1 是合法稳态,交后续段推进),消除「发射方谓词
            # 与执行方不同源 → 空计划 RunDeploy → 执行方 skip → 环级零推进」
            # 的死循环形态(run 20260904_28xx 局11,G3 守卫停机实证)。
            _up = self._deploy_up_candidates(obs, session)
            if not _up:
                log.info('[cw][prep] 部署段计划空(候选全被规则留 bench,'
                         'dd-037)→ bench 稳态,跳 RunDeploy 直入装备段')
                session.prep_phase = 3
                return RunEquip()
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
        # 现读基准 = last_state.hp 框架末次读值;无真值时 None(W823 None 化,不兜底)。
        _t = (st.plane - 1) * 9 + st.round_num if (st.plane and st.round_num) else None
        _cur_hp = session.last_state.hp if session.last_state is not None else None
        st.hp = gated_hp(_cur_hp, session, _t)
        # r101 审计必修①(5ba9b0a6 T6 实证):漏拷 dual_track_phase → 腾席链的
        # decision_target 恒走非双轨分支退终局 comp,r100 必修①(步级路径迁移)
        # 空转——r≥8 终局件提前上场+配方 carry 可被卖。迁移批 2(方向层接管)起
        # committed 语义 = cw_intention 权威派生(读端 committed_from 单点换源,
        # P1 同 commit 面),此处传 state 供 plane 判定。
        from sr_od.application.currency_war.kernel.cw_intention import (
            committed_from,
        )
        st.dual_track_phase = not committed_from(session, st)
        # 迁移审计 w148(git 历史)(ADR-0358,迁移审计 w92(git 历史) 修法 A):owned 穿戴池搬运链读端——CwOpEquipAll 写的
        # session 快照拷入决策 state.equips(decisions 遥测携带,win_model 持有
        # 面特征可见;空快照=默认 [] 语义不变)。
        st.equips = list(session.last_owned_equips)
        # r412(ADR-0274):node_type 补拷——腾席链 b 的 boss 轮禁升判定需要;
        # 权威源 = 备战节点行(cw_screen_prep 存 session.node_type_current),
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
