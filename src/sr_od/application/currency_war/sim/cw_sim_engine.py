"""sim 重做·主引擎(§2.5 步进协议:候选 B 定稿 + 候选 A 薄包装)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.5:

- **reset(seed, run_config) → 观测帧 / step(action) → {LogicOutcome,
  新观测帧 | 局结果}**——相位在观测帧里,策略器是外层驱动者
  (``while not done: act = decide(frame); frame = eng.step(act)``);
- 候选 A 薄包装 :func:`simulate_run`(单函数策略逐相位驱动,兼容
  「一次跑完一局」的调用习惯;策略接口 = ``(观测帧) → 动作``,
  测试桩零成本,§2.5 候选 B 优点④);
- 局结果 = ``{final_hp, plane_reached, rounds, hp_trail, unmodeled
  披露面}``(纯结果,无评判);记录经容器统一 state 流水,不自建
  第二账本(§2.0.3)。

相位状态机(§2.0.1 枚举,流转 = 各模块规格挂钩的落点):
- reset:开局(M01)→ boss 名单(M20)→ 环境屏(RunConfig.env_present
  为真;OPENING_ENV)→ 进 P1r1;
- 进节点:写 NodeKey → 轮首收入(M04,U04 败补挂账按 kernel 分支序
  消费)→ 位面开局环境金(M02 结构化通道)→ 商店全刷(M05,整店锁
  跳过——裁定②:锁 = 引擎自有状态,动作词表无锁通道,首版恒解锁
  +披露)→ offer 日程检查(M11/U07:打完 1-2/2-1/3-1 生效于下一轮
  备战窗口,联席决策挂 2-6)→ PREP;
- PREP:装备/工具四路(CwActionWearEquipParam/CwActionWrenchUseParam/CwActionPrecisionWrenchUseParam/
  CwActionFurnaceUseParam,M10)= sim 侧游戏规则腿(cw_sim_equips 分派;炉走
  ``M10/炉/{uses}`` 流);其余玩家动作经单一转移函数(M07/M08/M09),
  动作后消费银狼升 2 星触发判据(M21,planner_overlay_due + 全域
  星级快照);CwActionOpenBoxParam → 箱候选 →
  BOX_PICK(M17);CwActionStartBattleParam = 备战终结动作(补给 → 选卡面/
  遭遇 → 选档面/其余 → M13 结算);
- 结算(M12→M14→M15→M08 序):随机输出面(M13;扑满不掉血豁免,
  M17)→ HP 折算与保底(M14,dead → 局终)→ 连胜双账(M15)→ 节点
  经验(M08)→ 败态挂账(M04)→ 奖励节点胜 → REWARD_BALL;
- 收尾检查序:overlay 队列(M22)→ offer(M11)→ 下一节点;
- 局终:再次归零(M14)/ P3 进场即 game_over 并披露 ``p3_unobserved``
  (M03/U19)/ P2 boss 结算完成 = 全程走完(第一期限 P1+P2 段);
- SETTLEMENT 相位第一期不呈现:结算 = 引擎内部转移 + hp_trail 记录
  (结算屏语义属 live 画面,相位枚举保留作枚举完备)。

裁定②/③落地:整店锁 = 引擎自有状态 + ``shop_lock_sim_engine_state``
披露;lv10 满级零累计 = 容器 xp 不写(语义等价 None 分母,披露
``level_cap_xp_denominator_none``)。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from sr_od.application.currency_war.data.cw_chars import CHARACTER_ROSTER
from sr_od.application.currency_war.kernel.cw_economy import LostNodeRef
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    SupplyOption,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GAME_STATE_SCHEMA_VERSION,
    GameState,
    LogicOutcome,
    NodeKey,
    _row_unit_tags,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    INVESTMENT_ENVS,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionFurnaceUseParam,
    CwActionOpenBoxParam,
    CwActionPickEventParam,
    CwActionPrecisionWrenchUseParam,
    CwActionStartBattleParam,
    CwActionWearEquipParam,
    CwActionWrenchUseParam,
)
from sr_od.application.currency_war.sim.cw_sim_actions import (
    apply_node_xp,
    apply_player_action,
)
from sr_od.application.currency_war.sim.cw_sim_base import obs_sig, sim_evidence
from sr_od.application.currency_war.sim.cw_sim_battle import (
    SIM_BATTLE_FACE,
    apply_hp_outcome,
    settle_battle,
)
from sr_od.application.currency_war.sim.cw_sim_enemy import (
    BOSS_DEDUP_PENDING,
    DIFFICULTY_BASE_PENDING_U25,
    HOLY_GRAIL_PENDING,
    resolve_plane_bosses,
)
from sr_od.application.currency_war.sim.cw_sim_equips import (
    FURNACE_CHAR_MODE_PENDING,
    TOOL_EFFECTS_PENDING,
    UNMODELED_GRANTS,
    apply_furnace_equip_mode,
    apply_precision_wrench,
    apply_wear_equip,
    apply_wrench,
)
from sr_od.application.currency_war.sim.cw_sim_income import (
    apply_round_start_income,
    streak_income_after,
    streak_signed_after,
)
from sr_od.application.currency_war.sim.cw_sim_nodes import (
    ENCOUNTER_PARAMS_PENDING_U22,
    apply_ball_pick,
    apply_box_pick,
    apply_encounter_pick,
    apply_supply_pick,
    box_options,
    encounter_options,
    is_piggy_node,
    reward_ball_panel,
    supply_options,
)
from sr_od.application.currency_war.sim.cw_sim_offer import (
    ENV_QUALITY_DISCLOSURE,
    OFFER_OUTLIER_DISCLOSURE,
    QUALITY_DISTRIBUTION_DISCLOSURE,
    QUALITY_REWRITE_ENVS_PENDING,
    apply_env_pick,
    apply_strategy_pick,
    offer_slots,
    quality_rewrite_hit,
    sample_env_offer,
    sample_strategy_offer,
)
from sr_od.application.currency_war.sim.cw_sim_opening import apply_opening
from sr_od.application.currency_war.sim.cw_sim_overlay import (
    OVERLAY_PARAM_PENDING,
    OverlayQueue,
    apply_disclosed_pick,
    sample_options,
)
from sr_od.application.currency_war.sim.cw_sim_phase import (
    CwSimObservation,
    CwSimPhase,
    RewardBall,
)
from sr_od.application.currency_war.sim.cw_sim_plane_schedule import (
    node_sequence_of,
)
from sr_od.application.currency_war.sim.cw_sim_run_config import RunConfig
from sr_od.application.currency_war.sim.cw_sim_shop import (
    ROTATION_ASSUMPTION_DISCLOSURE,
    deal_shop,
    effective_deal_probs,
)
from sr_od.application.currency_war.sim.cw_sim_special import (
    SILVER_WOLF_ID,
    planner_overlay_due,
)
from sr_od.application.currency_war.sim.cw_sim_streams import stream_rng

#: 轮岗环境在册名(M02 挂钩:每备战阶段重掷翻倍档;M05 流)。
_ROTATION_ENV_NAME: str = '轮岗'

#: 引擎自有状态披露键群(裁定②/③与占位面;随局结果.unmodeled 输出)。
DISCLOSURE_SHOP_LOCK: str = 'shop_lock_sim_engine_state'
DISCLOSURE_LV10_XP: str = 'level_cap_xp_denominator_none'
DISCLOSURE_P3_UNOBSERVED: str = 'p3_unobserved'
DISCLOSURE_ENV_CHANNELS: str = 'env_economy_channels_pending_m02'
DISCLOSURE_BOX_TRIGGER: str = 'box_spawn_trigger_pending_u23'
#: planner 选卡效果披露(M22 选卡只记账不应用)。机制本身已定谳(升费腿 =
#: 变为下一个费用档的 1 星银狼LV.999 [口述·权威 2026-09-18],
#: research/equipment_mechanics.md §7)——pending 指效果应用未建模,非机制未知。
DISCLOSURE_PLANNER_EFFECT: str = 'planner_pick_effect_pending_u26'

#: 单局步数上限(防策略器死循环;正常局 < 2000 步)。
MAX_STEPS: int = 5000

#: 全程披露常量表(恒在册,与采样值无关的声明面)。
_BASE_DISCLOSURES: dict[str, object] = {
    SIM_BATTLE_FACE: 'random_win_p0.5_hp_loss_uniform_[23,70]',
    QUALITY_DISTRIBUTION_DISCLOSURE: 'uniform_1/3_each_placeholder',
    ENV_QUALITY_DISCLOSURE: 'env_pool_uniform_no_quality_axis',
    OFFER_OUTLIER_DISCLOSURE: 'u07_outlier_1-2pct_not_modeled',
    ENCOUNTER_PARAMS_PENDING_U22: 'count4_gold20_equip0_fixed_set',
    DIFFICULTY_BASE_PENDING_U25: 'base_curve_none_no_interpolation',
    HOLY_GRAIL_PENDING: 'activation_pending_u14',
    BOSS_DEDUP_PENDING: 'with_replacement_per_plane',
    ROTATION_ASSUMPTION_DISCLOSURE: 'tier_uniform_1of5_assumed',
    DISCLOSURE_SHOP_LOCK: 'engine_state_no_action_channel',
    DISCLOSURE_LV10_XP: 'cap10_zero_accumulate_u18',
    DISCLOSURE_ENV_CHANNELS: 'structured_two_of_env_economy',
    DISCLOSURE_BOX_TRIGGER: 'no_spontaneous_box_first_phase',
    # M10 装备三键并表(r2 验收 §7-1③:U24「发放空表随局披露」的交付
    # 面——键定义于 cw_sim_equips,恒在册声明,与采样值无关)
    UNMODELED_GRANTS: 'u24_grant_table_empty_first_phase',
    TOOL_EFFECTS_PENDING: 'privilege_projector_token_unmodeled',
    FURNACE_CHAR_MODE_PENDING: 'furnace_drag_char_mode_unmodeled',
}


def _silver_wolf_max_star(gs: GameState) -> int:
    """全板面银狼最高星级(备战席+前台+后台;M21 触发判据的动作前
    快照输入;无银狼 → 0 = 判据「跨越 2★」的合法起点)。

    kernel 合成产物落点 = 场上同名位(M07),备战席与前后排都是合成
    载体域,扫描必须全域;域未写(None)= 该域无单位。
    """
    stars: list[int] = []
    bench_view = gs.bench.value
    if bench_view is not None:
        stars += [int(s.unit.star) for s in bench_view.slots
                  if s is not None and s.kind == 'unit'
                  and s.unit is not None
                  and s.unit.char_id == SILVER_WOLF_ID]
    for row in (gs.front_row.value, gs.back_row.value):
        stars += [int(u.star) for u in (row or [])
                  if u is not None and u.char_id == SILVER_WOLF_ID]
    return max(stars, default=0)


def _board_truth_of(gs: GameState) -> dict[str, int]:
    """板面羁绊计数引擎真值(容器行全量重算)。

    标签单一源 = kernel ``_row_unit_tags``(:meth:`GameState._resync_board_delta`
    派生增量消费的同一 shim:角色 factions+flows+independent 全集 +
    星徽/卡带装备贡献,开拓者按排归一)——保证 sim 观察真值与 kernel
    行写端派生值位位同源,等值观察零写、不与派生增量双计。
    """
    counts: dict[str, int] = {}
    for row_field, row_name in ((gs.front_row, 'front_row'),
                                (gs.back_row, 'back_row')):
        for unit in (row_field.value or []):
            if unit is None:
                continue
            for tag in _row_unit_tags(unit, row_name):
                counts[tag] = counts.get(tag, 0) + 1
    return counts


@dataclass(frozen=True)
class RunResult:
    """局结果(§2.5 定稿形态;纯结果无评判)。"""

    final_hp: int
    plane_reached: int
    rounds: int
    hp_trail: tuple[int, ...]
    unmodeled: dict[str, object]


@dataclass(frozen=True)
class StepResult:
    """step 回声:动作应用 + 下一观测帧/局结果(三态:终局帧 None)。"""

    outcome: LogicOutcome | None
    observation: CwSimObservation | None
    result: RunResult | None


@dataclass
class _Eng:
    """引擎自有状态(容器不可表达的推进器内账;§2.0.1 sim 是唯一
    状态推进者)。"""

    seed: int
    cfg: RunConfig
    gs: GameState
    phase: CwSimPhase = CwSimPhase.GAME_OVER
    plane: int = 1
    round_num: int = 1
    #: 收入侧无符号连胜计数(M15 双账引擎半)
    streak_unsigned: int = 0
    #: 上一败掉的战斗类节点(单挂账,M04 败补消费)
    pending_loss: LostNodeRef | None = None
    #: 策略/环境 offer 全程去重集(U07③)
    excluded_invest: set[str] = field(default_factory=set)
    excluded_env: set[str] = field(default_factory=set)
    overlay_queue: OverlayQueue = field(default_factory=OverlayQueue)
    #: 「我来当策划」已触发位(首次语义,M21)
    planner_fired: bool = False
    #: 整店锁(裁定②:引擎自有状态;词表无动作通道,首版恒 False)
    shop_locked: bool = False
    #: 宝钻计数(M09 获取通道 = M18 带钻选项;引擎自有状态)
    diamond_count: int = 0
    furnace_uses: int = 0
    hp_trail: list[int] = field(default_factory=list)
    done: bool = False
    #: 相位载荷(逐相位填充,随帧呈现)
    options: tuple[str, ...] = ()
    supply_opts: tuple[SupplyOption, ...] = ()
    encounter_opts: tuple[EncounterOption, ...] = ()
    box_cands: tuple[str, ...] = ()
    balls: tuple[RewardBall, ...] = ()
    balls_left: list[int] = field(default_factory=list)
    encounter_tier: int | None = None
    disclosures: dict[str, object] = field(default_factory=dict)


class CwSimEngine:
    """单局 sim 引擎(§2.5 候选 B:reset/step 原语;一实例一局)。"""

    def __init__(self) -> None:
        self._eng: _Eng | None = None

    # ---------------------------------------------------------- 外层接口

    def reset(self, seed: int, run_config: RunConfig) -> CwSimObservation:
        """开局(局级输入 + 开局真值写入;返回首观测帧)。"""
        if run_config.game_mode != '标准博弈':
            raise ValueError(
                f'对局类型 {run_config.game_mode!r} 不在首版辖域'
                '(U27:sim 首版 = 标准博弈;非标准值显式拒,不猜差异)')
        gs = GameState(schema_version=GAME_STATE_SCHEMA_VERSION)
        eng = _Eng(seed=int(seed), cfg=run_config, gs=gs)
        eng.disclosures.update(_BASE_DISCLOSURES)
        self._eng = eng
        apply_opening(gs, run_config,
                      stream_rng(seed, 'M01/opening_hand'))
        bosses = resolve_plane_bosses(run_config.boss_roster_override,
                                      stream_rng(seed, 'M20/boss'))
        gs.observe(gs.plane_bosses, list(bosses),
                   evidence=sim_evidence('boss:roster'),
                   sig=obs_sig(group_id='sim:boss'))
        self._hp_trail_append(eng)
        if run_config.env_present:
            rng = stream_rng(seed, 'M02/env-offer')
            eng.options = sample_env_offer(rng, eng.excluded_env)
            eng.phase = CwSimPhase.OPENING_ENV
        else:
            self._enter_node(eng, 1, 1)
        return self._observe(eng)

    def step(self, action: CwAction) -> StepResult:
        """单动作推进(相位分派;局终后调用 = RuntimeError)。"""
        eng = self._eng
        if eng is None:
            raise RuntimeError('先 reset 再 step')
        if eng.done:
            raise RuntimeError('局已结束(reset 开新局)')
        outcome: LogicOutcome | None = None
        if eng.phase is CwSimPhase.PREP:
            outcome = self._step_prep(eng, action)
        elif eng.phase in (CwSimPhase.OPENING_ENV, CwSimPhase.INVEST_OFFER):
            self._step_card_pick(eng, action)
        elif eng.phase is CwSimPhase.ENCOUNTER_OFFER:
            self._step_encounter(eng, action)
        elif eng.phase is CwSimPhase.SUPPLY_PICK:
            self._step_supply(eng, action)
        elif eng.phase is CwSimPhase.REWARD_BALL:
            self._step_ball(eng, action)
        elif eng.phase is CwSimPhase.BOX_PICK:
            self._step_box(eng, action)
        elif eng.phase is CwSimPhase.EVENT_OVERLAY:
            self._step_overlay(eng, action)
        elif eng.phase is CwSimPhase.PLANE_TRANSITION:
            self._step_plane_confirm(eng, action)
        else:
            raise RuntimeError(f'相位 {eng.phase} 无动作通道')
        self._refresh_board(eng)
        if eng.done:
            return StepResult(outcome=outcome, observation=None,
                              result=self._result(eng))
        return StepResult(outcome=outcome, observation=self._observe(eng),
                          result=None)

    # ---------------------------------------------------------- PREP

    def _step_prep(self, eng: _Eng, action: CwAction) -> LogicOutcome | None:
        if isinstance(action, CwActionStartBattleParam):
            self._settle_or_dispatch(eng)
            return None
        if isinstance(action, CwActionOpenBoxParam):
            # 箱落席 → 开箱 → 武装箱 4 选 1(cw_vocab CwActionOpenBoxParam 执行语义;
            # 候选 = 占位固定集,U24 箱内容池候实机,占位不消费随机)
            eng.box_cands = box_options()
            eng.phase = CwSimPhase.BOX_PICK
            return None
        equip_outcome = self._apply_equip_action(eng, action)
        if equip_outcome is not None:
            return equip_outcome
        star_before = _silver_wolf_max_star(eng.gs)
        outcome = apply_player_action(
            eng.gs, action, node_tag=f'p{eng.plane}r{eng.round_num}')
        self._check_planner_trigger(eng, star_before)
        return outcome

    def _apply_equip_action(self, eng: _Eng,
                            action: CwAction) -> LogicOutcome | None:
        """装备/工具动作四路分派(M10;设计 §2.2 M10「装备动作腿 = sim
        侧游戏规则建模」——kernel 商店转移口对装备族恒
        ``unsupported_action_type`` 零写拒,必须在此分派;非装备动作返
        None 落回主转移函数)。

        腿语义单一源 = ``cw_sim_equips``(穿着即合成/扳手回区/炉同类型
        重掷),本方法只做分派与 ``LogicOutcome`` 回声包装,禁重写腿
        语义;拒因 = 腿布尔契约的统一回声(细则在腿 docstring)。
        """
        if isinstance(action, CwActionWearEquipParam):
            ok = apply_wear_equip(eng.gs, action)
            return LogicOutcome(applied=ok,
                                reason='' if ok else 'wear_equip_rejected')
        if isinstance(action, CwActionWrenchUseParam):
            ok = apply_wrench(eng.gs, action)
            return LogicOutcome(applied=ok,
                                reason='' if ok else 'wrench_rejected')
        if isinstance(action, CwActionPrecisionWrenchUseParam):
            ok = apply_precision_wrench(eng.gs, action)
            return LogicOutcome(
                applied=ok,
                reason='' if ok else 'precision_wrench_rejected')
        if isinstance(action, CwActionFurnaceUseParam):
            return self._apply_furnace(eng, action)
        return None

    def _apply_furnace(self, eng: _Eng, action: CwActionFurnaceUseParam) -> LogicOutcome:
        """冶金炉分派(M10 双模式):equip 模式 = 同类型随机重掷腿,流键
        ``M10/炉/{uses}`` 按实际重掷序装配;char 模式(拖角色全拆+逐件
        变异)首版不建模,显式拒(披露键恒在册 = _BASE_DISCLOSURES)。"""
        if action.target_kind == 'char':
            return LogicOutcome(applied=False,
                                reason='furnace_char_mode_unmodeled')
        uses = eng.furnace_uses + 1
        new_name = apply_furnace_equip_mode(
            eng.gs, action.item_name,
            rng=stream_rng(eng.seed, f'M10/炉/{uses}'))
        if new_name is None:
            return LogicOutcome(applied=False,
                                reason='furnace_target_not_owned')
        eng.furnace_uses = uses
        return LogicOutcome(applied=True)

    def _check_planner_trigger(self, eng: _Eng, star_before: int) -> None:
        """银狼首次升达 2 星 → planner overlay 入队(M21 有档触发)。

        判据单一源 = ``cw_sim_special.planner_overlay_due``(1→2 星
        合成事件);star_before/after = 全板面(备战席+部署位)银狼最高
        星级动作前后快照——kernel 合成产物落点 = 场上同名位(M07),
        仅扫备战席会漏部署位合成(旧近似判据的缺陷)。聚合口径 = 最高
        星(触发判据只关心「是否跨越 2★」,与载体位置无关)。「首次」
        语义 = 引擎一次性标志去重。
        """
        if eng.planner_fired:
            return
        star_after = _silver_wolf_max_star(eng.gs)
        if planner_overlay_due(SILVER_WOLF_ID, star_before, star_after):
            eng.planner_fired = True
            eng.overlay_queue.push_planner()

    # ---------------------------------------------------------- 节点推进

    def _enter_node(self, eng: _Eng, plane: int, round_num: int) -> None:
        seq = node_sequence_of(plane)
        if round_num > len(seq):
            # 位面走完 → 位面推进/局终
            if plane >= 2:
                # P2 末 = 第一期辖域尽头;P3 进场即 game_over(p3_unobserved)
                eng.disclosures[DISCLOSURE_P3_UNOBSERVED] = \
                    'enter_p3_game_over_u19'
                self._game_over(eng)
                return
            self._to_plane(eng, plane + 1)
            return
        eng.plane, eng.round_num = plane, round_num
        eng.gs.observe(eng.gs.node,
                       NodeKey(plane=plane, round_num=round_num,
                               kind=seq[round_num - 1]),
                       evidence=sim_evidence(f'node:p{plane}r{round_num}'),
                       sig=obs_sig(group_id='sim:node'))
        if plane > 1 and round_num == 1:
            eng.phase = CwSimPhase.PLANE_TRANSITION
            return
        self._begin_prep(eng)

    def _step_plane_confirm(self, eng: _Eng, action: CwAction) -> None:
        """位面过渡确认(任意动作;U20:全继承无重置,披露过渡语义)。"""
        self._begin_prep(eng)

    def _begin_prep(self, eng: _Eng) -> None:
        plane, r = eng.plane, eng.round_num
        kind = node_sequence_of(plane)[r - 1]
        # 轮首收入(M04;败补挂账按 kernel 分支序消费——supply/reward
        # 轮不消费,败态跨轮保留至下一战斗轮)
        apply_round_start_income(eng.gs, plane=plane, round_num=r,
                                 node_type=kind,
                                 streak=eng.streak_unsigned,
                                 pending_loss=eng.pending_loss)
        if kind not in ('supply', 'reward'):
            eng.pending_loss = None
        # 位面开局环境金(M02 结构化通道:gold_per_plane_start)
        self._apply_env_plane_gold(eng, plane)
        # 商店全刷(M05:节点切换自动全刷;整店锁跳过——裁定②)
        if not eng.shop_locked:
            rotation_on = (str(eng.gs.active_env.value or '')
                           == _ROTATION_ENV_NAME)
            rng = stream_rng(eng.seed, f'M05/deal/p{plane}/r{r}')
            probs = effective_deal_probs(
                int(eng.gs.level.value or 3),
                stream_rng(eng.seed, f'M05/rotation/p{plane}/r{r}'),
                rotation_on=rotation_on)
            deal_shop(eng.gs, rng, level=int(eng.gs.level.value or 3),
                      probs=probs, tag=f'shop:deal:p{plane}r{r}')
        # offer 日程(M11/U07:固定轮次生效于本节点备战窗口前)
        active_env = eng.gs.active_env.value
        if offer_slots(plane, r, active_env):
            if quality_rewrite_hit(str(active_env or '')):
                eng.disclosures[QUALITY_REWRITE_ENVS_PENDING] = \
                    str(active_env)
            rng = stream_rng(eng.seed, f'M11/offer/p{plane}/r{r}')
            eng.options = sample_strategy_offer(rng, eng.excluded_invest)
            eng.phase = CwSimPhase.INVEST_OFFER
            return
        eng.phase = CwSimPhase.PREP

    def _apply_env_plane_gold(self, eng: _Eng, plane: int) -> None:
        """环境结构化经济通道(M02:已结构化子集直接生效——位面开局
        金通道;其余通道挂披露,效果批建模)。"""
        env_name = normalize_invest_name(str(eng.gs.active_env.value or ''))
        env = INVESTMENT_ENVS.get(env_name)
        eff = env.economy if env is not None else None
        if eff is None:
            return
        golds = eff.gold_per_plane_start
        if plane_entry_gold := (golds[plane - 1] if 0 < plane <= len(golds)
                                else 0):
            after = int(eng.gs.gold.value or 0) + plane_entry_gold
            eng.gs.observe(eng.gs.gold, after,
                           evidence=sim_evidence(f'env:plane_gold:p{plane}'),
                           sig=obs_sig(group_id='sim:env'))

    # ---------------------------------------------------------- 结算

    def _settle_or_dispatch(self, eng: _Eng) -> None:
        """CwActionStartBattleParam:按节点类型分派(补给 → 选卡/遭遇 → 选档/
        其余 → M13 结算)。"""
        kind = node_sequence_of(eng.plane)[eng.round_num - 1]
        if kind == 'supply':
            rng = stream_rng(eng.seed,
                             f'M18/opts/p{eng.plane}/r{eng.round_num}')
            eng.supply_opts = supply_options(rng)
            eng.phase = CwSimPhase.SUPPLY_PICK
            return
        if kind == 'encounter':
            rng = stream_rng(eng.seed, f'M16/offer/p{eng.plane}')
            eng.encounter_opts = encounter_options()
            eng.phase = CwSimPhase.ENCOUNTER_OFFER
            return
        self._settle_combat(eng, encounter_tier=None)

    def _step_encounter(self, eng: _Eng, action: CwAction) -> None:
        if not isinstance(action, CwActionPickEventParam):
            return
        tier, _reward = apply_encounter_pick(eng.gs, action.option_idx)
        eng.encounter_tier = tier
        self._settle_combat(eng, encounter_tier=tier)

    def _settle_combat(self, eng: _Eng, *, encounter_tier: int | None
                       ) -> None:
        """M12→M14→M15→M08 结算序(战斗类节点含奖励型)。"""
        plane, r = eng.plane, eng.round_num
        kind = node_sequence_of(plane)[r - 1]
        rng = stream_rng(eng.seed, f'M13/{plane}/{r}')
        outcome = settle_battle(rng, plane=plane, round_num=r)
        piggy = is_piggy_node(eng.gs)
        if piggy and outcome.hp_delta < 0:
            # 扑满不掉血豁免(M17:扑满关有战力要求、不掉血)
            from dataclasses import replace
            outcome = replace(outcome, hp_delta=0)
        floor_now, dead = apply_hp_outcome(eng.gs, outcome)
        self._hp_trail_append(eng)
        if dead:
            self._game_over(eng)
            return
        apply_node_xp(eng.gs, node_type=kind)
        eng.streak_unsigned = streak_income_after(
            eng.streak_unsigned, node_type=kind, won=outcome.won)
        signed = streak_signed_after(
            int(eng.gs.streak.value or 0), node_type=kind,
            won=outcome.won)
        eng.gs.observe(eng.gs.streak, signed,
                       evidence=sim_evidence(f'streak:p{plane}r{r}'),
                       sig=obs_sig(group_id='sim:streak'))
        if not outcome.won and kind in ('battle', 'encounter', 'boss'):
            eng.pending_loss = LostNodeRef(plane=plane, round_num=r,
                                           node_type=kind)
        if outcome.won and kind == 'reward':
            eng.balls = reward_ball_panel()
            eng.balls_left = list(range(len(eng.balls)))
            eng.phase = CwSimPhase.REWARD_BALL
            return
        self._after_settlement(eng)

    def _step_supply(self, eng: _Eng, action: CwAction) -> None:
        if not isinstance(action, CwActionPickEventParam):
            return
        if action.refresh:
            # 免费刷新一次(实机两步 decide_supply 语义;一次性)
            used = int(eng.gs.supply_refresh_used.value or 0)
            if used < 1:
                eng.gs.observe(eng.gs.supply_refresh_used, used + 1,
                               evidence=sim_evidence('supply:refresh'),
                               sig=obs_sig(group_id='sim:supply'))
                rng = stream_rng(eng.seed,
                                 f'M18/opts/p{eng.plane}/r{eng.round_num}'
                                 f'/refresh{used + 1}')
                eng.supply_opts = supply_options(rng)
                return
        if action.option_idx < 0 or action.option_idx >= len(eng.supply_opts):
            return
        opt = eng.supply_opts[action.option_idx]
        if apply_supply_pick(eng.gs, opt):
            eng.diamond_count += 1
        eng.disclosures.setdefault(
            'supply_diamond_slot_pending_u24', 'uniform_slot')
        self._after_settlement(eng)

    def _step_ball(self, eng: _Eng, action: CwAction) -> None:
        if not isinstance(action, CwActionPickEventParam):
            return
        # option_idx 坐标系 = 帧内剩余球列表下标(0 基;面板按剩余序
        # 收缩呈现,策略器逐球点,已点球不可再点)
        if not (0 <= action.option_idx < len(eng.balls_left)):
            return
        eng.disclosures.setdefault('reward_ball_content_pending_u23',
                                   'gold30_equip1_gold5_placeholder')
        rng = stream_rng(eng.seed,
                         f'M17/balls/p{eng.plane}/r{eng.round_num}')
        panel_idx = eng.balls_left.pop(action.option_idx)
        apply_ball_pick(eng.gs, panel_idx, rng=rng)
        if not eng.balls_left:
            self._after_settlement(eng)

    def _step_box(self, eng: _Eng, action: CwAction) -> None:
        if not isinstance(action, CwActionPickEventParam):
            return
        if 0 <= action.option_idx < len(eng.box_cands):
            eng.disclosures.setdefault('box_pool_pending_u24', 'bases4')
            apply_box_pick(eng.gs, eng.box_cands[action.option_idx])
        eng.phase = CwSimPhase.PREP

    def _step_overlay(self, eng: _Eng, action: CwAction) -> None:
        if not isinstance(action, CwActionPickEventParam):
            return
        kind = eng.overlay_queue.pop()
        eng.disclosures.setdefault(OVERLAY_PARAM_PENDING,
                                   'm22_placeholder_options')
        pick = (eng.options[action.option_idx]
                if 0 <= action.option_idx < len(eng.options) else '')
        if kind == 'planner':
            eng.disclosures[DISCLOSURE_PLANNER_EFFECT] = f'picked:{pick}'
        else:
            apply_disclosed_pick(eng.gs, kind, pick)
        self._after_settlement(eng)

    # ---------------------------------------------------------- 收尾

    def _after_settlement(self, eng: _Eng) -> None:
        """结算完成检查序:overlay → 下一节点。"""
        if len(eng.overlay_queue):
            kind = eng.overlay_queue.peek()
            # 占位角色池(注册表序;U14 选项池候实机补档,披露面覆盖)
            roster = tuple(sorted(CHARACTER_ROSTER)[:16])
            eng.options = sample_options(
                stream_rng(eng.seed, f'M22/{kind}'), kind, roster)
            eng.phase = CwSimPhase.EVENT_OVERLAY
            return
        self._enter_node(eng, eng.plane, eng.round_num + 1)

    def _to_plane(self, eng: _Eng, plane: int) -> None:
        eng.plane = plane
        eng.round_num = 0
        self._enter_node(eng, plane, 1)

    def _step_card_pick(self, eng: _Eng, action: CwAction) -> None:
        """选卡族相位(环境/策略)共用:CwActionPickEventParam(option_idx) 选 1。"""
        if not isinstance(action, CwActionPickEventParam):
            return
        idx = action.option_idx
        if not (0 <= idx < len(eng.options)):
            return
        name = eng.options[idx]
        if eng.phase is CwSimPhase.OPENING_ENV:
            apply_env_pick(eng.gs, name)
            eng.excluded_env.update(eng.options)
            env = INVESTMENT_ENVS.get(normalize_invest_name(name))
            eff = env.economy if env is not None else None
            if eff is not None and eff.gold_instant:
                after = int(eng.gs.gold.value or 0) + eff.gold_instant
                eng.gs.observe(eng.gs.gold, after,
                               evidence=sim_evidence('env:instant_gold'),
                               sig=obs_sig(group_id='sim:env'))
            self._enter_node(eng, 1, 1)
        else:
            apply_strategy_pick(eng.gs, name)
            eng.excluded_invest.update(eng.options)
            # 商店/收入已在 _begin_prep 前段完成,选卡后直接进备战
            eng.phase = CwSimPhase.PREP

    # ---------------------------------------------------------- 板面观察基座

    def _refresh_board(self, eng: _Eng) -> None:
        """步末板面真值观察(与实机「每备战帧面板观察」同契约)。

        为什么需要:sim 是板面真值唯一持有者,而 kernel 侧 board 为派生
        量(2026-09-18 commit 2995d33e1),派生增量挂钩
        ``_resync_board_delta`` 只活在 write_logic 行写,且基座未读
        (board 为 None)时跳过等观察首读——sim 不补观察写入端则 board
        恒 None,策略器成型度 fp/armed 发射门/部署收益判定的输入恒空
        (实证 = 20260918_0618_findiss 问题 1,998 局 form_ok 全 0)。
        本口每步末以 :func:`_board_truth_of` 全量重算真值观察 board
        (等值零写):一次承担实机面板观察的两重职责——派生基座首读
        (首步即立,后续行写走 kernel 增量派生)+ obs 通道行写
        (cw_sim_equips 装备腿等 sim 真值写,不经 write_logic 挂钩)后
        的漂移覆盖。实机等值语义 = 面板欠计/派生漂移由下一备战帧观察
        覆盖收敛;sim 真值与派生失配经容器 board 吸收面
        (``_absorb_board_derived``,辖域 = ``proj_board_resync`` 派生写端)
        观察赢采新,不停机;吸收落 ``board_derived_adopt`` 台账行时
        observed_evidence 带 ``sim:engine:`` 前缀,命中容器
        ``_MISMATCH_SUPPRESS_PREFIXES`` 抑制面(缺陷发射口兜底),不落
        生产缺陷台账。
        """
        gs = eng.gs
        truth = _board_truth_of(gs)
        if gs.board.value is not None and gs.board.value == truth:
            return
        gs.observe(gs.board, truth,
                   evidence=sim_evidence(
                       f'board:p{eng.plane}r{eng.round_num}'),
                   sig=obs_sig(group_id='sim:board'))

    # ---------------------------------------------------------- 终局

    def _game_over(self, eng: _Eng) -> None:
        eng.done = True
        eng.phase = CwSimPhase.GAME_OVER

    def _hp_trail_append(self, eng: _Eng) -> None:
        hp = eng.gs.hp.value
        if hp is not None:
            eng.hp_trail.append(int(hp))

    def _result(self, eng: _Eng) -> RunResult:
        return RunResult(
            final_hp=int(eng.gs.hp.value or 0),
            plane_reached=eng.plane,
            rounds=(eng.plane, eng.round_num),
            hp_trail=tuple(eng.hp_trail),
            unmodeled=dict(eng.disclosures))

    def _observe(self, eng: _Eng) -> CwSimObservation:
        return CwSimObservation(
            phase=eng.phase,
            gs=eng.gs,
            node=NodeKey(plane=eng.plane, round_num=eng.round_num,
                         kind=node_sequence_of(eng.plane)[eng.round_num - 1]
                         if not eng.done and eng.round_num >= 1 else 'prep'),
            options=eng.options,
            supply_options=eng.supply_opts,
            encounter_options=eng.encounter_opts,
            box_options=eng.box_cands,
            balls=tuple(eng.balls[i] for i in eng.balls_left),
            overlay_kind=(eng.overlay_queue.peek() or ''
                          if eng.phase is CwSimPhase.EVENT_OVERLAY else ''),
            overlay_options=eng.options if eng.phase is CwSimPhase.EVENT_OVERLAY else (),
            disclosures=dict(eng.disclosures))


def simulate_run(seed: int, run_config: RunConfig,
                 decide: Callable[[CwSimObservation], CwAction]) -> RunResult:
    """候选 A 薄包装(§2.5:候选 B 之上的兼容入口;单函数策略逐相位
    驱动一局,返回局结果)。"""
    eng = CwSimEngine()
    frame = eng.reset(seed, run_config)
    for _ in range(MAX_STEPS):
        if frame.phase is CwSimPhase.GAME_OVER:
            break
        action = decide(frame)
        ret = eng.step(action)
        if ret.result is not None:
            return ret.result
        frame = ret.observation
    raise RuntimeError(f'超过单局步数上限 {MAX_STEPS}(策略器疑似死循环)')
