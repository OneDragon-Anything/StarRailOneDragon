"""决策框架 v2 相位派生(W114/ADR-0346,经济循环总模型步①「影子」)。

设计依据:.debug/temp/currency_war/cw_dev/deep_read/W113_经济循环总模型设计.md §3.1
(2026-08-25 用户裁决版:等级不作为独立门槛、核心须上场、追赶态删除)。

**本批是影子观测**:``derive_phase``/``form_ok``/``form_score`` 每轮在
decide_prep 入口计算一次并写 session/遥测,**不被任何决策逻辑消费**——
为步②(切授权)/步③(切调度)提供对照基线。任何 if-相位-then-改行为
的代码都违反本批的存在理由(零行为变化)。

相位是**派生量**(由可观测变量即时算出,不存跨轮状态,天然免疫
session 丢失):

    FORM  := NOT form_ok                        # 战力不足,凑过渡羁绊
    HOARD := form_ok AND gold < interest_floor  # 战力 OK,攒到 50
    SPEND := form_ok AND gold ≥ interest_floor  # 满息平台,花溢余

form_ok 谓词(裁决后版本,**无等级项**——等级通过上场完整性进入判定:
人口上限不够→羁绊单位/核心上不了场→判据为假→留在 FORM):

    form_ok := intention_locked
               AND bond_tiers_met        # ∀(f,t)∈comp.form_tiers: board[f]≥t
               AND core_deployed_ok      # intention_core 已上场 且 star≥2

意向未锁定(兜底局)时降级用连续量:``form_score ≥ phase_form_score_gate``。
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


def form_ok(state: GameState, session: StrategySession,
            registry: DecisionV2Registry) -> bool:
    """战力 OK 判定(相位切换谓词;与 formed_stop 同谓词族,无轮界/辖域)。

    - 意向 locked 且锁定线可解析:三件套判定(意向锁 × 羁绊凑够 ×
      核心已上场 2★)。「核心须上场」是 2026-08-25 用户裁决——
      ``intention_core(comp)`` 必须在 ``state.deployed``(上场)且
      star≥2;躺 bench 不算(bench 囤件≠战力)。
    - 线不可解析/无 form_tiers(反甲类):保守判 False(与
      formed_stop_active 同保守口径——「羁绊凑够」无定义不辖)。
    - 意向未锁(兜底局):降级 ``form_score ≥ phase_form_score_gate``
      (防止兜底局永远停在 FORM);人口落后自然压低 form_score
      (deployed 上不满 → 引擎数低),承接「人口别落后」的观察。
    """
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState) or ist.phase != 'locked':
        return form_score(state, registry) >= registry.phase_form_score_gate
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
