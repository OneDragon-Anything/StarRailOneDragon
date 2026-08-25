"""决策框架 v2 相位派生(W114/ADR-0346 影子;W119/ADR-0347 起被消费)。

设计依据:.debug/temp/currency_war/cw_dev/deep_read/W113_经济循环总模型设计.md §3.1
(2026-08-25 用户裁决版:等级不作为独立门槛、核心须上场;**追赶态已随
步③(W126/ADR-0349)删除**——覆盖序只剩 应急>报警>boss>模式,相位域
与覆盖态不再双 gate 并存)。

**W114 影子期已结束(步② 切授权)**:相位/form_ok/form_score 仍是每轮
decide_prep 入口计算一次的派生量(不落跨轮存储),但自 W119 起被决策
消费——地板族(``arbiter._active_floor`` 相位驱动)与成型停手
(``filters.formed_stop_active`` 消费 form_ok)读它。

相位是**派生量**(由可观测变量即时算出,不存跨轮状态,天然免疫
session 丢失):

    FORM  := NOT form_ok                        # 战力不足,凑过渡羁绊
    HOARD := form_ok AND gold < interest_floor  # 战力 OK,攒到 50
    SPEND := form_ok AND gold ≥ interest_floor  # 满息平台,花溢余

form_ok 谓词(裁决后版本,**无等级项**——等级通过上场完整性进入判定:

    form_ok(锁定) := intention_locked
                      AND bond_tiers_met        # ∀(f,t)∈comp.form_tiers: board[f]≥t
                      AND core_deployed_ok      # intention_core 已上场 且 star≥2
    form_ok(兜底) := r≥phase_fallback_min_round
                      AND 有效体系数≥phase_fallback_min_engines   # ADR-0353

人口上限不够→羁绊单位/核心上不了场→判据为假→留在 FORM(等级经上场完整性
进入判定,兜底局同理:deployed 上不满→体系凑不齐→FORM)。form_score 自
W132/ADR-0353 起为纯遥测观测,不进任何判据。
"""
from __future__ import annotations

from enum import StrEnum

from sr_od.application.currency_war.cw_intention import (
    IntentionState,
    intention_core,
)
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)


class Phase(StrEnum):
    """经济循环相位(内生状态机;派生量,不落跨轮存储)。"""

    FORM = 'FORM'    # 凑过渡羁绊(战力不足)
    HOARD = 'HOARD'  # 凑息(战力 OK,金未达满息地板)
    SPEND = 'SPEND'  # 花钱(满息平台,花溢余)


def form_score(state: GameState,
               registry: DecisionV2Registry) -> float:
    """战力连续量副指标(归一化 [0,1];设计稿 §3.1「板面 rung 副指标」)。

    口径 = **按上场阵容**(deployed only,与 form_ok 的「上场完整性」
    裁决同向):过渡体系达成数(``cw_sim._engines_count`` 单一源,deployed
    阵营计数)+ 配方档小数(与 ``scoring.board_rung_x`` 同式的
    ``rung_frac_per_recipe_tier × recipe_tier/RECIPE_BASE``),封顶 2 档后
    除以 2 归一。

    **W132/ADR-0353 起为纯遥测观测**(sim 账本/生产 decisions.jsonl 字段
    保留),不进任何判据——旧兜底门(score≥gate)被 run15 型散板(单体系
    +配方档小数=0.65)绕过两证,判据改结构化(见 ``fallback_engines_count``)。

    与 ``scoring.board_rung_x``(混合域:bench 星级×bench_form_weight 折减
    计入)的差异是**刻意的**:form_score 是纯观测口径(不进评分/决策,
    无双源互斥风险);bench 囤件不计入——「上场了才算战力」。
    """
    from sr_od.application.currency_war.cw_line_defs import (
        RECIPE_BASE,
        recipe_tier,
    )
    from sr_od.application.currency_war.cw_sim import (
        _board_factions_of,
        _engines_count,
    )
    deployed = state.deployed or []
    fac = _board_factions_of(deployed)
    dep_names = frozenset(
        getattr(d, 'char_id', '') or '' for d in deployed)
    engines = _engines_count(fac, dep_names)
    frac = min(recipe_tier(fac) / RECIPE_BASE, 1.0)
    x = min(2.0, float(engines)
            + registry.rung_frac_per_recipe_tier * frac)
    return max(0.0, min(1.0, x / 2.0))


def fallback_engines_count(state: GameState) -> int:
    """兜底门有效体系数(W132/ADR-0353;结构判据,deployed 口径)。

    = 四过渡体系达成数(``_engines_count`` 单一源:仙舟3/列车2/DOT2/希儿系)
      + hp_charge_stack 型全局累积角色豁免(上场 2★ 各计 1;万敌——
      ``cw_comps.hp_charge_stack_chars`` W127 字段派生;``cost_escalation``
      型不豁免:累积由购买驱动,不构成上场战力)。

    判据基准 = transition_combos 定稿「两两组合=过渡成型」;「核心 2★」
    豁免门槛与 form_ok 三件套路径的裁决同向(保守)。
    """
    from sr_od.application.currency_war.cw_comps import hp_charge_stack_chars
    from sr_od.application.currency_war.cw_sim import (
        _board_factions_of,
        _engines_count,
    )
    deployed = [d for d in (state.deployed or []) if d is not None]
    fac = _board_factions_of(deployed)
    dep_names = frozenset(
        getattr(d, 'char_id', '') or '' for d in deployed)
    n = _engines_count(fac, dep_names)
    exempt = hp_charge_stack_chars()
    n += sum(1 for d in deployed
             if (getattr(d, 'char_id', '') or '') in exempt
             and (getattr(d, 'star', 1) or 1) >= 2)
    return n


def form_ok(state: GameState, session: StrategySession,
            registry: DecisionV2Registry) -> bool:
    """战力 OK 判定(相位切换谓词;与 formed_stop 同谓词族,无轮界/辖域)。

    - 意向 locked 且锁定线可解析:三件套判定(意向锁 × 羁绊凑够 ×
      核心已上场 2★)。「核心须上场」是 2026-08-25 用户裁决——
      ``intention_core(comp)`` 必须在 ``state.deployed``(上场)且
      star≥2;躺 bench 不算(bench 囤件≠战力)。**W132/ADR-0353:此
      路径语义零改动**。
    - 线不可解析/无 form_tiers(反甲类):保守判 False(与
      formed_stop_active 同保守口径——「羁绊凑够」无定义不辖)。
    - 意向未锁(兜底局):降级**结构判据**(W132/ADR-0353):
      ``round_num ≥ phase_fallback_min_round`` **且**
      ``fallback_engines_count(state) ≥ phase_fallback_min_engines``——
      板面真收敛到 ≥2 过渡体系(或 1 体系+万敌 2★ 豁免)才判「战力 OK」。
      旧 score≥gate 门被 run15 型散板(单体系+配方档小数)绕过,已删;
      form_score 保留为纯遥测观测。人口落后自然压低体系达成数(deployed
      上不满 → 引擎凑不齐),承接「人口别落后」的观察。
    """
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState) or ist.phase != 'locked':
        if state.round_num < registry.phase_fallback_min_round:
            return False
        return fallback_engines_count(state) \
            >= registry.phase_fallback_min_engines
    from sr_od.application.currency_war.cw_comps import get_comp
    comp = get_comp(ist.locked_comp)
    if comp is None or not comp.form_tiers:
        return False   # 线不可解析/无羁绊线:保守不辖(同 formed_stop)
    board = state.board or {}
    if any((board.get(f) or 0) < t for f, t in comp.form_tiers.items()):
        return False
    core = intention_core(comp)
    if not core:
        return False
    for d in state.deployed or []:
        if d is not None and getattr(d, 'char_id', '') == core \
                and (getattr(d, 'star', 1) or 1) >= 2:
            return True
    return False


def derive_phase(state: GameState, session: StrategySession,
                 registry: DecisionV2Registry) -> Phase:
    """相位派生(每轮决策入口计算一次;纯函数,无副作用)。

    切换判据(W113 §3.1 表,全部可观测):
    - ``NOT form_ok`` → FORM(默认相位,开局/换阵/失件回落);
    - ``form_ok AND gold < interest_floor``(=50,registry 单一源)→ HOARD;
    - ``form_ok AND gold ≥ interest_floor`` → SPEND([17] 满息即花溢余)。
    """
    if not form_ok(state, session, registry):
        return Phase.FORM
    if (state.gold or 0) >= registry.interest_floor:
        return Phase.SPEND
    return Phase.HOARD
