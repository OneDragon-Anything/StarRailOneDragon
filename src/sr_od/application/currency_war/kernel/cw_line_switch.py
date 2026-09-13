"""换线判据:E_rounds 比较 + θ 滞回 + D_min 驻留(DESIGN §③)。

设计=唯一规格:无定型姿态设计件 §③。
核心公式(候选线 c,候选集=过渡引擎池方向):

    distance(c) = need(c) − held(c) − shelf(c)   # 需求张数 − 持有 − 货架可见可买
    E_rounds(c) ≈ distance(c) / per_round(c)
    per_round(c) = (1 + 可负担刷次数) × p̄(c, lv) # 自然刷 1 次/轮 + 买刷;截断到 bench 空位

p̄ 同超几何模型(cw_shop_odds P5 表实值;同 ``ev_proto.p_at_least_one`` 构型:
每格独立,P(格=该费用)=p;给定 m 格该费用,P(至少一张目标)=1−C(同费非
目标,m)/C(同费总,m))。**p̄ 乐观偏差**:理论满池值未扣 NPC 消耗/争夺,
系统性偏乐观 10-20%——判据先修偏再比较:双线 E_rounds 同乘 (1+δ)
(registry.line_switch_debias_delta,默认 0.15),θ(registry.line_switch_theta,
默认 1.0 轮)只承载去偏后的剩余噪声(DESIGN §③)。

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

from sr_od.application.currency_war.kernel.cw_game_state import (
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_slots_of,
    gold_of,
    level_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_comps import Comp
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    StrategySession,
    strategy_state_of,
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
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.data.cw_shop_odds import (
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


def tier_progress(comp: Comp, bs: GameState) -> dict[str, tuple[int, int, int]]:
    """逐档进度 {档: (需求, 已持, 货架)}——线距离口径的分解单一源。

    消费端:``line_distance``(标量和)与 strategies 侧线缺口分解
    (evidence_gate 输入,proof.py)共用本式,禁第二实现漂移。
    口径(原 line_distance 逐字,超档不计):held_t = min(需求, 板面档
    计数);shelf_t = 本回合 shop 中该档阵营可见件数,仅当板面档计数
    仍低于需求时计(买走即 held,不计入刷出期望)。
    """
    tiers = getattr(comp, 'form_tiers', None) or {}
    board = bs.board.value or {}
    out: dict[str, tuple[int, int, int]] = {}
    for f, t in tiers.items():
        held_t = min(t, board.get(f, 0))
        shelf_t = 0
        if held_t < t:
            _payload = bs.shop.value
            for c in shop_payload_content_cards(_payload):
                if (getattr(c, 'faction', '') or '') == f:
                    shelf_t += 1
        out[f] = (t, held_t, shelf_t)
    return out


def line_distance(comp: Comp, bs: GameState) -> int:
    """distance(c) = need − held − shelf(需求张数 − 持有 − 货架可见可买)。

    held 取 board(场上)对阵营档位的占有(超档不计);shelf=本回合 shop
    中「缺档阵营」的可见件数(买走即 held,不计入刷出期望)。逐档进度
    分解单一源 = ``tier_progress``;全局 clamp 是本函数(E_rounds 标量
    距离)的既有意口径——超持仓可跨档抵扣,与逐档 clamp 的缺口分解
    (proof.py)服务不同消费端,两形态并存已申报。
    """
    prog = tier_progress(comp, bs)
    if not prog:
        return 0
    need = sum(p[0] for p in prog.values())
    held = sum(p[1] for p in prog.values())
    shelf = sum(p[2] for p in prog.values())
    return max(0, need - held - shelf)


def e_rounds(comp: Comp, bs: GameState,
             registry: DecisionV2Registry | None = None,
             session: StrategySession | None = None) -> float:
    """E_rounds(c) ≈ distance / per_round(per_round 见模块注释)。

    distance=0 → 0.0(已完成);p̄=0(该等级刷不出)→ inf(静态不可达;
    「实测断供」归 drought bail 旁路,DESIGN §附4)。

    可负担窗的守息线 = session resolved 链单一源
    (``saturation_line(cap_resolved_of_session(session))``,ADR-0598
    随批接线:旧 ``reg.interest_floor()`` 不随持卡语境动——买断制局
    刷新可负担窗被 50 金地板压死,囤金经本车道部分存活);
    ``session=None``(无 session 调用形态/旧测试桩)退注册表派生值,
    与既有调用形状零漂移。
    """
    reg = registry or DEFAULT_REGISTRY
    dist = line_distance(comp, bs)
    if dist <= 0:
        return 0.0
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        BENCH_CAPACITY,
        bench_occupied,
    )
    p = 0.0
    for f in (getattr(comp, 'form_tiers', None) or {}):
        # 标签独立并集:1−∏(1−p_f)(联合概率高估为设计内承认近似,见模块注释)
        p_f = p_bar_faction(f, level_of(bs))
        p = p_f if p <= 0 else 1 - (1 - p) * (1 - p_f)
    if p <= 0:
        return math.inf
    from sr_od.application.currency_war.kernel.cw_economy import (
        cap_resolved_of_session,
        refresh_cost_effective,
        saturation_line,
    )
    # 刷价单一源消费 = refresh_cost_effective(现值→None 退建模基价;
    # economy 接缝注「字段读统一经容器读口单一源,禁各消费点自写兜底」
    # ——禁在本判据内联第二份读式/裸魔数兜底)。
    cost = refresh_cost_effective(None, 0, bs=bs)
    if session is not None:
        floor = saturation_line(cap_resolved_of_session(session))
    else:
        floor = reg.interest_floor()
    affordable = max(0, (gold_of(bs) - floor) // cost)
    bench_free = max(0, BENCH_CAPACITY - bench_occupied(bench_slots_of(bs)))
    rolls = min(affordable, bench_free)    # 买刷截断到 bench 空位
    per_round = (1 + rolls) * p
    return dist / per_round


def switch_allowed(bs: GameState, session: StrategySession) -> bool:
    """辖域门:位面前中段可换;末窗禁换(设计内辖域声明,DESIGN §③)。

    末窗=本位面末 3 轮(9 轮位面即 r≥7;7 轮位面 P2 即 r≥5)——末窗换线
    = 丢弃已成形板面战力追 0-progress 新线,且 D_min=2 驻留在末窗等价于
    禁换;真值源=``cw_plane_table.nodes_of_plane``(位面轮数,ADR-0366)。
    """
    from sr_od.application.currency_war.kernel.cw_plane_table import nodes_of_plane
    return round_num_of(bs) <= nodes_of_plane(session) - 3


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


#: P2 位面节点模板(economy.md §10.2;表缺/位面锚不符时的投影回退):
#: [战斗, 战斗, 遭遇, 奖励, 遭遇, 奖励, 战斗, boss]——实测表第 7 节点为「?」
#: 占位,按保守规则转战斗+normal 档(未知多算一的一场损失=存活估计更
#: 短=门更紧,保守方向显式声明,多局开局帧复核后改)。
_P2_NODE_TEMPLATE: list[str] = ['battle', 'battle', 'encounter', 'reward',
                                'encounter', 'reward', 'battle', 'boss']

_ZERO_LOSS_NODE_KINDS: frozenset[str] = frozenset({'reward', 'supply'})


def node_loss_kind(node_type: str) -> str:
    """节点型 → 损血档归一(单一源;阈值层投影
    cw_first_passage._loss_dist 消费,registry.p2_cond_loss_table 同表分档)。boss/遭遇→同名档;奖励/补给→零损档(投影日历轮照走、
    损血 0);其余(普通战斗/精英/缺读/'?' 占位)→ normal 档——未知
    战斗节点按 normal 档(战斗频率最高档)、未知非战斗节点由调用方
    先归零损档,两类缺读不共用一个兜底。"""
    if node_type == 'boss':
        return 'boss'
    if node_type in ('encounter', 'encounter_v2', '遭遇'):
        return 'encounter'
    if node_type in _ZERO_LOSS_NODE_KINDS:
        return 'reward'
    return 'normal'


# (C4 换线存活轮数门机械已随旧方案清退批删除——开关族
#  line_switch_survival_gate_enabled / rounds_two_state_enabled 出局,
#  清查报告 OLD_MIX_AUDIT §1.3;连同删除 rounds_alive / gate_need /
#  gate_counterfactual / survival_gate / register_gate_block 与
#  cw_intention._switch_gate_open 接线、v3_line_gate_* 决策位/闩、
#  line_gate_blocked/line_gate_cf_blocked 遥测键。损血档归一
#  node_loss_kind 与 p2_cond_loss_table 保留——阈值层
#  cw_first_passage._loss_dist 仍消费;两态 p_win 表 p_win_p2_by_rung
#  保留——cw_plane_table.p_win_p2 阈值层映射仍消费。)


def best_alt_line(bs: GameState, session: StrategySession, config,
                  score_ctx, registry: DecisionV2Registry | None = None
                  ) -> tuple[object, float]:
    """候选集中 E_rounds 最小且有限的备选线((comp, e) ;无候选 → (None, inf))。

    候选集=select_comp_scored top-N(与选线同一来源,防另造排序);排除
    drought_excluded 死线(drought 名单语义保留)与供给为 0 的线(选线
    供给门同口径)。registry 注入(e_rounds 的金/刷价参数)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import (
        select_comp_scored,
        shop_supply,
    )
    reg = registry or DEFAULT_REGISTRY
    # 判据面防御 getattr(strategy_state_of None 契约,ADR-0563 B4 划分线):
    # 异型状态对象字段缺席退 ''(与下行 drought_excluded 防御形态同族)
    _tc = getattr(strategy_state_of(session), 'target_comp', None)
    cur_name = _tc.name if _tc is not None else ''
    excluded = set(getattr(strategy_state_of(session), 'drought_excluded', None) or ())
    best: tuple[object, float] = (None, math.inf)
    for _s, c in select_comp_scored(bs, score_ctx, config, top_n=8):
        if c.name == cur_name or c.name in excluded:
            continue
        if shop_supply(c, bs) <= 0:
            continue
        e = e_rounds(c, bs, reg, session=session)
        if e < best[1]:
            best = (c, e)
    return best
