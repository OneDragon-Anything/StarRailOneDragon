"""换线判据:E_rounds 比较 + θ 滞回 + D_min 驻留(DESIGN §③)。

设计=唯一规格:`.debug/temp/currency_war/w328_unformed_posture/DESIGN.md` §③。
核心公式(候选线 c,候选集=过渡引擎池方向):

    distance(c) = need(c) − held(c) − shelf(c)   # 需求张数 − 持有 − 货架可见可买
    E_rounds(c) ≈ distance(c) / per_round(c)
    per_round(c) = (1 + 可负担刷次数) × p̄(c, lv) # 自然刷 1 次/轮 + 买刷;截断到 bench 空位

p̄ 同超几何模型(cw_shop_odds P5 表实值;同 ``ev_proto.p_at_least_one`` 构型:
每格独立,P(格=该费用)=p;给定 m 格该费用,P(至少一张目标)=1−C(同费非
目标,m)/C(同费总,m))。**p̄ 乐观偏差**:理论满池值未扣 NPC 消耗/争夺,
系统性偏乐观 10-20%——判据先修偏再比较:双线 E_rounds 同乘 (1+δ)
(registry.line_switch_debias_delta,默认 0.15),θ(registry.line_switch_theta,
默认 1.0 轮)只承载去偏后的剩余噪声(DESIGN §③修订 1-2)。

切换条件(滞回 + 驻留):

    E_rounds(alt)×(1+δ) + θ < E_rounds(cur)×(1+δ)  且 当前线驻留 ≥ D_min=2

(D_min 压振荡频率硬上限至 1/(2·D_min);退化情形双 inf → 维持原线。)

与 drought bail 的关系(DESIGN §附4):**或-并存**——E_rounds 比较为主判据,
N=5 连续 shop_supply<1.0 的经验观测保留为独立旁路(drought_excluded 死线
名单语义不变):E_rounds=inf 是静态池数学,检测不了「理论可达、实测断供」
的线,后者只有经验观测能测;两路任一触发即弃线。

切换成本:1★ 卖出全额退成本(cw_state.sell_refund)→ 凑齐羁绊前换线近乎
零成本,唯一真实成本=2★ 已合成件折价(−1 金)与 bench 机会成本;D_min 之外
无需额外切换税(DESIGN §③)。辖域=位面前中段;末窗禁换是设计内辖域声明
(末窗的线选择由投影血量判据下的找件 EV 接管)。
"""
from __future__ import annotations

import math

from sr_od.application.currency_war.cw_comps import Comp
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)


def char_has_tag(ch, tag: str) -> bool:
    """板面标签 = 阵营(factions)∪ 流派(flows)的并集(outcomes board 口径)。"""
    return tag in (getattr(ch, 'factions', None) or ()) \
        or tag in (getattr(ch, 'flows', None) or ())


def p_bar_faction(tag: str, level: int) -> float:
    """p̄:单次刷新至少出 1 张「该标签(阵营∪流派)」件的概率(超几何)。

    多标签联合分布按标签独立取(DESIGN §附5 诚实列表:联合概率高估,
    设计内承认的近似)。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    from sr_od.application.currency_war.cw_shop_odds import (
        DISTINCT_CARDS_PER_COST,
        POOL_COPIES_PER_CARD,
        REFRESH_PROB,
    )
    names = [n for n, ch in CHARACTERS.items()
             if getattr(ch, 'cost', 0) and char_has_tag(ch, tag)]
    if not names:
        return 0.0
    costs = sorted({ch.cost for ch in CHARACTERS.values()
                    if char_has_tag(ch, tag)})
    p_hit_once = 0.0
    shop_slots = 5    # cw_shop_odds.SHOP_SLOTS
    for cost in costs:    # 费用档互斥,可加
        p_cost = REFRESH_PROB.get(level, {}).get(cost, 0.0)
        if p_cost <= 0:
            continue
        a = POOL_COPIES_PER_CARD.get(cost, 9)
        v = DISTINCT_CARDS_PER_COST.get(cost, 13)
        total = v * a
        a_tgt = len([n for n in names
                     if CHARACTERS[n].cost == cost]) * a
        if a_tgt <= 0:
            continue
        for m in range(1, shop_slots + 1):
            if m > total:
                continue
            p_m = math.comb(shop_slots, m) * p_cost ** m \
                * (1 - p_cost) ** (shop_slots - m)
            p_none = (math.comb(total - a_tgt, m) / math.comb(total, m)
                      if total - a_tgt >= m else 0.0)
            p_hit_once += p_m * (1 - p_none)
    return min(1.0, p_hit_once)


def line_distance(comp: Comp, state: GameState) -> int:
    """distance(c) = need − held − shelf(需求张数 − 持有 − 货架可见可买)。

    held 取 board(场上)对阵营档位的占有(超档不计);shelf=本回合 shop
    中「缺档阵营」的可见件数(买走即 held,不计入刷出期望)。
    """
    tiers = getattr(comp, 'form_tiers', None) or {}
    if not tiers:
        return 0
    board = state.board or {}
    need = sum(tiers.values())
    held = sum(min(t, board.get(f, 0)) for f, t in tiers.items())
    shelf = 0
    for c in (state.shop or []):
        f = getattr(c, 'faction', '') or ''
        if f in tiers and board.get(f, 0) < tiers[f]:
            shelf += 1
    return max(0, need - held - shelf)


def e_rounds(comp: Comp, state: GameState,
             registry: DecisionV2Registry | None = None) -> float:
    """E_rounds(c) ≈ distance / per_round(per_round 见模块注释)。

    distance=0 → 0.0(已完成);p̄=0(该等级刷不出)→ inf(静态不可达;
    「实测断供」归 drought bail 旁路,DESIGN §附4)。"""
    reg = registry or DEFAULT_REGISTRY
    dist = line_distance(comp, state)
    if dist <= 0:
        return 0.0
    from sr_od.application.currency_war.cw_state import (
        BENCH_CAPACITY,
        bench_occupied,
    )
    p = 0.0
    for f in (getattr(comp, 'form_tiers', None) or {}):
        # 标签独立并集:1−∏(1−p_f)(联合概率高估为设计内承认近似,见模块注释)
        p_f = p_bar_faction(f, state.level)
        p = p_f if p <= 0 else 1 - (1 - p) * (1 - p_f)
    if p <= 0:
        return math.inf
    cost = state.shop_refresh_cost or 2
    affordable = max(0, ((state.gold or 0) - reg.interest_floor) // cost)
    bench_free = max(0, BENCH_CAPACITY - bench_occupied(state.bench or []))
    rolls = min(affordable, bench_free)    # 买刷截断到 bench 空位
    per_round = (1 + rolls) * p
    return dist / per_round


def switch_allowed(state: GameState, session: StrategySession) -> bool:
    """辖域门:位面前中段可换;末窗禁换(设计内辖域声明,DESIGN §③)。

    末窗=本位面末 3 轮(9 轮位面即 r≥7;7 轮位面 P2 即 r≥5)——末窗换线
    = 丢弃已成形板面战力追 0-progress 新线,且 D_min=2 驻留在末窗等价于
    禁换;真值源=``cw_horizon.nodes_of_plane``(位面轮数,ADR-0366)。
    """
    from sr_od.application.currency_war.cw_horizon import nodes_of_plane
    return state.round_num <= nodes_of_plane(session) - 3


def should_switch_e(e_cur: float, e_alt: float, dwell_rounds: int,
                    registry: DecisionV2Registry | None = None) -> tuple[bool, str]:
    """切换裁决(纯数):输入双线 E_rounds 与当前驻留轮数。

    返回 (是否切换, 理由串)。条件:E(alt)×(1+δ)+θ < E(cur)×(1+δ)
    且 dwell≥D_min;退化情形双 inf → 维持原线(理由 'both_inf');
    e_cur=inf 且 e_alt 有限 = 原线静态不可达,不等式恒真(仍受 D_min 辖)。
    """
    reg = registry or DEFAULT_REGISTRY
    if not math.isfinite(e_alt):
        return False, 'alt_inf'
    if math.isfinite(e_cur) and math.isfinite(e_alt):
        if e_cur <= 0:
            return False, 'cur_done'
    k = 1.0 + reg.line_switch_debias_delta
    lhs = e_alt * k + reg.line_switch_theta
    rhs = e_cur * k if math.isfinite(e_cur) else math.inf
    if not lhs < rhs:
        return False, 'theta'
    if dwell_rounds < reg.line_switch_min_dwell:
        return False, f'dwell({dwell_rounds}<{reg.line_switch_min_dwell})'
    return True, 'ok'


def rounds_alive(state: GameState,
                 registry: DecisionV2Registry | None = None) -> int:
    """存活轮数估计:ceil(hp / E[每轮期望损血])(纯数,设计
    `.debug/temp/currency_war/w353_p2_survival/DESIGN.md` §2 C4)。

    E[每轮损血] = registry.line_switch_round_loss 三档(普通/遭遇/boss)
    等权均值——粗档谱(P2 损血标定,来源见 registry 注释);等权含 boss
    高损档 → 估计偏小 → 门更紧,方向保守。hp≤0 → 0。
    """
    reg = registry or DEFAULT_REGISTRY
    vals = [v for v in reg.line_switch_round_loss.values() if v > 0]
    if not vals or not state.hp or state.hp <= 0:
        return 0
    e_per_round = sum(vals) / len(vals)
    return int(-(-state.hp // e_per_round))   # ceil


def survival_gate(state: GameState, session: StrategySession,
                  e_alt: float,
                  registry: DecisionV2Registry | None = None
                  ) -> tuple[bool, str]:
    """换线存活轮数门(第三道门;registry.line_switch_survival_gate_enabled)。

    判据:rounds_alive ≥ E_rounds(新线) + 兑现余量(设计 §2 C4:换线
    价值兑现在新线成型之后;存活轮数不足=新线永远到不了兑现点,换线
    期望 0<驻留旧线)。与既有 θ 滞回/δ 先修偏/D_min 驻留同族串联,不是
    第二换线机制;drought bail 旁路不辖(或-并存结构不变)。

    辖域 plane≥2(损血谱为 P2 标定,P1 不适用);开关关/辖域外 → 放行
    (零漂移)。e_alt=inf 时数学上恒不满足,但该情形在 should_switch_e
    已被 'alt_inf' 拦,此处保守放行(门不重复裁决)。
    """
    reg = registry or DEFAULT_REGISTRY
    if not reg.line_switch_survival_gate_enabled:
        return True, 'gate_off'
    if state.plane < 2 or not math.isfinite(e_alt):
        return True, 'gate_off'
    ra = rounds_alive(state, reg)
    need = e_alt + reg.line_switch_survival_margin
    if ra >= need:
        return True, 'ok'
    return False, f'survival({ra:.0f}<{need:.2f})'


def best_alt_line(state: GameState, session: StrategySession, config,
                  score_ctx, registry: DecisionV2Registry | None = None
                  ) -> tuple[object, float]:
    """候选集中 E_rounds 最小且有限的备选线((comp, e) ;无候选 → (None, inf))。

    候选集=select_comp_scored top-N(与选线同一来源,防另造排序);排除
    drought_excluded 死线(drought 名单语义保留)与供给为 0 的线(选线
    供给门同口径)。registry 注入(e_rounds 的金/刷价参数)。
    """
    from sr_od.application.currency_war.cw_comps import (
        select_comp_scored,
        shop_supply,
    )
    reg = registry or DEFAULT_REGISTRY
    cur_name = session.target_comp.name if session.target_comp else ''
    excluded = set(getattr(session, 'drought_excluded', None) or ())
    best: tuple[object, float] = (None, math.inf)
    for _s, c in select_comp_scored(state, score_ctx, config, top_n=8):
        if c.name == cur_name or c.name in excluded:
            continue
        if shop_supply(c, state) <= 0:
            continue
        e = e_rounds(c, state, reg)
        if e < best[1]:
            best = (c, e)
    return best
