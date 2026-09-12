"""V_opt / V_slot / V_comp / ΔP̂ / ΔV_streak 等派生价值量(含 M6 档匹配/
gap_depth 谓词与 refund_full_star_ok 星级纪律共享谓词,R4-F4)。

档匹配谓词与 V_comp 表生成在本模块单一源——M6(mandate 侧)与
stockpile_buy(criteria 侧)同源消费,防臂①旁路误拆 M6 买入口(R4-F4)。
V_opt 消费处金可行性截断(R28 低3):逐格取值时现检可支金,金不足以执行
该格通道下界(当前刷)的格退 A7 下界(P41 索引原文)——缺截断 ⇒ V_opt
系统性高估 ⇒ E_rev 豁免偏松。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    expected_refreshes,
    refresh_prob,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    LOSS_GOLD_BY_NODE,
    STREAK_GOLD_TABLE,
)
from sr_od.application.currency_war.kernel.cw_economy import sell_refund

#: 凑息/搜牌场景缺省 (k_need, j_owned)(P49 A3 场景声明:目标件差 2 张带
#: 1-4费 (3,1)/5费 (9,7);【注】场景参数,非拟合)
SCEN_KJ: dict[int, tuple[int, int]] = {1: (3, 1), 2: (3, 1), 3: (3, 1),
                                       4: (3, 1), 5: (9, 7)}
#: DP 内连胜数上限(表饱和于 6,12 足够;P43 引擎口径)
_SMAX: int = 12


def p_miss(level: int, cost: int, j: int, taken_c: int,
           slots: int = 5) -> float:
    """P_miss = (1−q)^H(P41 ① 分量;H=需要时距,【拟】注入)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.odds import (
        slot_q,
    )
    return (1.0 - slot_q(level, cost, j, taken_c)) ** slots


def a7_lower_bound(level: int, cost: int, refresh_cost: int, j: int = 0,
                   taken_c: int = 0) -> float:
    """A7 下界 = c_eff/P_shop(单步搜救价值门阈值形态,p49 §7 同式)——
    金可行性截断时 V_opt 的退路格值(P41 索引「消费处金可行性截断」)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.odds import (
        p_shop,
    )
    ps = p_shop(level, cost, j, taken_c)
    if ps <= 0:
        return float('inf')
    return refresh_cost / ps


def v_opt(level: int, cost: int, u: float, h: int, gold: int,
          refresh_cost: int, j: int = 0, taken_c: int = 0) -> float:
    """V_opt(囤件期权)= u·P_miss·C_rescue,P41 ①;消费处金可行性截断
    (R28 低3):gold < refresh_cost(该格通道下界=当前刷)⇒ 退 A7 下界。"""
    if gold < refresh_cost:
        return a7_lower_bound(level, cost, refresh_cost, j, taken_c)
    return u * p_miss(level, cost, j, taken_c) * (
        refresh_cost / max(_p_shop_cached(level, cost, j, taken_c), 1e-12))


def _p_shop_cached(level: int, cost: int, j: int, taken_c: int) -> float:
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.odds import (
        p_shop,
    )
    return p_shop(level, cost, j, taken_c)


def v_slot(bench_free: int, blocked_net_evs: list[float]) -> float:
    """V_slot(bench 槽价,P41 ③):有空槽=0;free≤1 = max 被阻断动作净 EV。

    合成完备购不入阻断集(P41 ③);标定后组装规格=逐阻断动作按该动作目标
    卡落位格取该消费位端点后取 max(R25-低2/§E4.0 χ 条同款聚合语义——
    端点注入随标定批,本函数收净 EV 列表)。"""
    if bench_free > 1:
        return 0.0
    return max(blocked_net_evs, default=0.0)


def v_comp_marginal(cost: int, level: int, taken: int = 0,
                    scen: tuple[int, int] | None = None,
                    refresh_cost: int = 2) -> float:
    """第 taken+1 张同费杂牌的边际压缩价值 Δ金(P49 ①②;R2-11 对拍锚)。

    = (E[refreshes](taken) − E[refreshes](taken+1)) × c_eff(条件值:窗口
    全程付费刷);E 走 expected_refreshes 精确超几何 DP(命题 1 硬要求)。
    线性律失效边界:仿射性在非目标池近耗尽(≳90%)处失效,带外禁外推。"""
    k, j = scen if scen is not None else SCEN_KJ[cost]
    p = refresh_prob(level, cost)
    if p <= 0:
        return 0.0
    e0 = expected_refreshes(p, DISTINCT_CARDS_PER_COST[cost],
                            POOL_COPIES_PER_CARD[cost], taken, k, j)
    e1 = expected_refreshes(p, DISTINCT_CARDS_PER_COST[cost],
                            POOL_COPIES_PER_CARD[cost], taken + 1, k, j)
    return (e0 - e1) * refresh_cost


def v_comp_table(levels: tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10),
                 refresh_cost: int = 2) -> dict[int, dict[int, float]]:
    """V_comp 边际压缩价值二维表(费用档×等级;P49 (2) 文档表=誊录,
    本生成器=单一源)。resolved 池突变(v_c/a_c 变)下整体重生成
    (NMF §3.4 #1 池构成族接线)。"""
    table: dict[int, dict[int, float]] = {}
    for cost in (1, 2, 3, 4, 5):
        row: dict[int, float] = {}
        for level in levels:
            if refresh_prob(level, cost) <= 0:
                continue
            row[level] = v_comp_marginal(cost, level, refresh_cost=refresh_cost)
        table[cost] = row
    return table


def tier_match(card_cost: int, t_search: frozenset[int]) -> bool:
    """M6 档匹配谓词(P49 ③ [34] 数学化:目标档匹配=必要条件,跨档购零
    压缩系模型结构事实)。M6 侧与 stockpile_buy 侧全辖域同源消费(R4-F4)。"""
    return card_cost in t_search


def gap_depth(k_need: int, j_owned: int) -> int:
    """缺口深度 = k_need − j_owned(压库档序/凑息档序的排序分量)。"""
    return max(0, k_need - j_owned)


def refund_full_star_ok(star: int, cost: int) -> bool:
    """星级纪律共享谓词(R12-3):= 1★ ∧ sell_refund 全额可退(注册表直读)。
    档匹配发射谓词 = 档匹配 ∧ 本谓词(M6 侧与 stockpile_buy 侧同源消费,
    禁发射位内联星级判断)。"""
    return star == 1 and sell_refund(star, cost) == cost


def p_complete(missing: list[tuple[int, float]], refreshes: int) -> float:
    """P̂(集齐|H,B) = Π Binomial 尾(P38 闭式带;NMF §2「ΔP̂」行)。

    missing = [(该卡还差张数 m_i, 单格命中概率 q_i)];B(refreshes)=付费
    刷次数。阈值边际 ≥8-10pp 时闭式可用,深缺口走精确 DP(判据层消费时
    按带声明选路;+8pp 乐观偏差已带内声明,NMF §3.2)。"""
    prod = 1.0
    for m, q in missing:
        if q <= 0:
            return 0.0
        # P(命中 ≥ m) = 1 − Σ_{x<m} C(n,x) q^x (1−q)^(n−x)(P38 闭式带的
        # 尾概率式;求和域开区间 [0, m−1]——含 x=m 项即算成 P(≥m+1),
        # 边界系统性左移一档,IMPL_ADV_R200 症1 勘误)。
        # 边界 m>refreshes:B(n) 支撑 [0,n] ⇒ P(≥m)=0(乘零短路)。
        if m > refreshes:
            return 0.0
        tail = 1.0 - sum(
            _comb(refreshes, x) * (q ** x) * ((1.0 - q) ** (refreshes - x))
            for x in range(m))
        prod *= tail
    return prod


def _comb(n: int, k: int) -> float:
    import math
    return math.comb(n, k)


def delta_p_hat(missing: list[tuple[int, float]], new_card_q: float,
                new_card_need: int, refreshes_after_buy: int,
                refreshes_before: int) -> float:
    """ΔP̂ = P̂(集齐|H∪{x}, B−c) − P̂(集齐|H, B)(P38;买入 x 的完成概率
    增量,证据门概率因子)。"""
    after = p_complete(missing + [(new_card_need, new_card_q)],
                       refreshes_after_buy)
    before = p_complete(missing, refreshes_before)
    return after - before


def _sg(s: int) -> int:
    """连胜奖励金(越界取表尾;cw_economy.streak_gold 同构,P43 引擎口径)。"""
    return STREAK_GOLD_TABLE[min(max(s, 0), len(STREAK_GOLD_TABLE) - 1)]


def _streak_v_table(rounds: int, p: float, loss: int) -> list[list[float]]:
    """引擎口径 DP:V[(s,lost)] = 该状态下未来 r 轮期望连胜金+败轮金总和
    (P43 ①;轮首收入:lost∧s==0→loss 补发,否则 table[s];转移:胜→
    (min(s+1,SMAX),0)/败→(0,1)。基础奖励与利息两轨迹同得,差分中消去)。"""
    v = [[0.0] * 2 for _ in range(_SMAX + 1)]
    for _ in range(rounds):
        nv = [[0.0] * 2 for _ in range(_SMAX + 1)]
        for s in range(_SMAX + 1):
            for lost in (0, 1):
                inc = loss if (lost and s == 0) else _sg(s)
                nv[s][lost] = inc + p * v[min(s + 1, _SMAX)][0] \
                    + (1.0 - p) * v[0][1]
        v = nv
    return v


def delta_v_streak(s: int, rounds: int, delta_p: float, p: float,
                   loss: int = LOSS_GOLD_BY_NODE['battle']) -> float:
    """ΔV_streak = 引擎口径 DP 两次求值相减(NMF §2「ΔV_streak」行,P43 ①;
    d_eng(s+1)−d_eng(s) 的胜转移增量 × Δp 换算;换算 Δp 带 CI 系消费方
    职责,NMF §3.3 #10)。"""
    v_win = _streak_v_table(rounds, min(1.0, p + delta_p), loss)
    v_base = _streak_v_table(rounds, p, loss)
    return v_win[min(s + 1, _SMAX)][0] - v_base[min(s + 1, _SMAX)][0]


__all__ = [
    'SCEN_KJ', 'a7_lower_bound', 'delta_p_hat', 'delta_v_streak',
    'gap_depth', 'p_complete', 'p_miss',
    'refund_full_star_ok', 'tier_match', 'v_comp_marginal', 'v_comp_table',
    'v_opt', 'v_slot',
]
