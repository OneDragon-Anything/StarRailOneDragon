"""P38 ⑤层金位递推(预算 → 付费刷新数;标定批 T-278/ADR-0639)。

正本 = math_proofs P38 §推导⑤层「金位递推(显式定义——逐轮金位模拟
唯一口径)」:

    g_{r+1} = g_r + base(r) + streak(r) + min(g_r, 50)//10 − spend_r
    B = G − floor + Σ_r[base+streak+interest] − Σ_k n_k·cost_k − Σ_ΔL levelup
    B < 0 → P = 0(买不到缺口件,「买到即计数」前提破产);R = max(0, ⌊B/刷价⌋)

本模块是 :func:`p38_budget_recursion` 单一源,消费 kernel 经济原语
(round_base_income/streak_gold/interest/saturation_line/xp_click_cost),
禁在本模块第二份实现。落地形态逐项(P38 声明的简化口径,方向逐条
注明):
- 字面 50 → resolved 息帽链(saturation_line/cap_resolved_of_session,
  ADR-0598 同源泛化;P38 默认守 50 = 缺省 cap 5 的特例);
- base(r) = ``round_base_income``(P1 规划投影,函数自带跨位面近似
  申报——决策数学侧的 sanctioned 形态);
- streak(r) = 当前连胜档 ``streak_gold``(P38 A5/O4「按当前档」);
  无信号(None/连败/0)取表中位(P38「或中位 2」——中位由
  STREAK_GOLD_TABLE 现算,非拍死);当前档持有恒常 = 简化申报;
- 利息按支出前金位计 = 乐观上界(P38 已声明,量级 ≤ 单轮支出×10%
  封顶 cap);
- 购买成本按期望到达摊销 spend_r/T;升级金 v1 辖**下一级**(等级日程
  L(r) 系 P38 A4 调用方输入,生产无日程源 → 单步声明;升级金低估 =
  乐观向,较接线批静态口径〔零升级费〕严格收窄),买牌送 XP 每张
  +4 抵扣(P38「XP_PER_BUY 同源」);
- spend_r 的刷新金 2R/T 均摊使 R 出现在递推自身 → 小型不动点
  (利息 ≤ cap/轮 ⇒ 收敛带每轮 ≤ cap 金),迭代上限内不收敛 =
  2-循环振荡,取两支较小 = 保守端(试验数少 → P 小 → 充分侧保守)。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.kernel.cw_economy import (
    SHOP_REFRESH_COST,
    STREAK_GOLD_TABLE,
    cap_resolved_of_session,
    interest,
    round_base_income,
    saturation_line,
    streak_gold,
    xp_click_cost,
)
from sr_od.application.currency_war.kernel.cw_plane_table import r_remaining
from sr_od.application.currency_war.kernel.cw_state import (
    XP_PER_BUY,
    XP_TO_NEXT_LEVEL,
)

#: 不动点迭代上限(利息 ≤ cap/轮 ⇒ 每轮预算扰动 ≤ cap,B 步长 = 刷价,
#: 4 轮内不收敛即判 2-循环取保守端)
_FIXED_POINT_PASSES: int = 4

#: 无连胜信号时的连胜金规划档(P38 A5/O4「中位 2」:表中位现算,零拍死)
STREAK_PLAN_MEDIAN: int = sorted(STREAK_GOLD_TABLE)[len(STREAK_GOLD_TABLE) // 2]


@dataclass(frozen=True)
class BudgetPlan:
    """P38 ⑤层预算递推输出。

    字段坐标系(写入端 = :func:`p38_budget_recursion`;取值时机 =
    锁线评估帧现算):
    - ``refreshes``:视野内可负担付费刷新数 R(不动点终值;保守端);
    - ``budget``:可支刷新预算 B(期末结清口径;负值 = 缺口件买不起域);
    - ``exhausted``:B < 0(P38「买到即计数前提破产」分支;消费端
      P := 0,e_p_next := 0,门内走 below_nec 诚实锁劣——P76 §5.5.2
      预算解耦不回归:此处耗尽的是**购卡**预算,非刷新预算)。
    """

    refreshes: int
    budget: int
    exhausted: bool


def next_level_xp_cost(state: object, missing_copies: int) -> int:
    """升级金 v1(单步口径;P38 levelup_cost 式 ⌈max(0,need−4·Σn_k)/4⌉×单价)。

    等级日程条件(P38「升级金按日程所在轮扣」——日程不升则不扣):
    日程源 = ``cw_economy.get_node_goal`` 预算收权核(无标量先验路径,
    零 hp 依赖零 seam 日志);target_level ≤ 当前级 ⇒ 视界内无升级
    ⇒ 0。XP 缺口 = xp_progress 现读(缺省权威表兜底,与
    ``cw_economy.clicks_to_next_level`` 同表同兜底)减买牌送 XP
    (XP_PER_BUY × 缺口张数,P38 买牌同源抵扣);单击单价 =
    ``xp_click_cost``(显示价优先/兜底折扣族单一源)。满级 = 0。
    多级日程(P38 A4)生产无逐级源,本函数只辖下一级 = 声明简化。
    """
    level = int(getattr(state, 'level', 1) or 1)
    if level >= 10:
        return 0
    from sr_od.application.currency_war.kernel.cw_economy import (
        get_node_goal,
    )
    goal = get_node_goal(int(getattr(state, 'plane', 1) or 1),
                         int(getattr(state, 'round_num', 1) or 1))
    if goal.target_level <= level:
        return 0
    prog = getattr(state, 'xp_progress', None)
    if isinstance(prog, tuple) and len(prog) == 2:
        cur, need = int(prog[0]), int(prog[1])
    else:
        cur, need = 0, XP_TO_NEXT_LEVEL.get(level, 4)
    remain = max(0, need - cur - XP_PER_BUY * max(0, int(missing_copies)))
    clicks = -(-remain // XP_PER_BUY)
    return clicks * xp_click_cost(state)


def p38_budget_recursion(state: object, session: object,
                         purchase_cost: float,
                         missing_copies: int) -> BudgetPlan:
    """P38 ⑤层金位递推单一源(见模块 docstring 正本式与逐项声明)。

    ``purchase_cost`` = 缺口件期望购买成本 Σ_k m_k·c̄_k(c̄ = 分费档
    命中概率加权期望单价,生产端由 ``proof._missing_items`` 明细派生;
    q≤0 静态不可达件不计——它永不出现,购账不发生而 P=0 已由
    p_complete 承载,入账反会虚增 B<0 域);``missing_copies`` =
    可达缺口张数(买牌送 XP 抵扣分母,同口径)。
    """
    plane = int(getattr(state, 'plane', 1) or 1)
    round_num = int(getattr(state, 'round_num', 1) or 1)
    gold = int(getattr(state, 'gold', 0) or 0)
    cap = cap_resolved_of_session(session)
    floor = saturation_line(cap)
    refresh_cost = (int(getattr(state, 'shop_refresh_cost', 0) or 0)
                    or SHOP_REFRESH_COST)
    t_horizon = max(0, int(r_remaining(session, plane, round_num)))
    lvl_cost = next_level_xp_cost(state, missing_copies)
    streak = getattr(state, 'streak', None)
    streak_term = (streak_gold(int(streak))
                   if isinstance(streak, int) and streak > 0
                   else STREAK_PLAN_MEDIAN)

    def budget_at(r_plan: int) -> float:
        """给定摊销刷新计划 R 的期末预算 B(递推一轮金位路径累计)。"""
        income_total = 0.0
        interest_total = 0.0
        g = float(gold)
        amort_refresh = (refresh_cost * r_plan / t_horizon) if t_horizon else 0.0
        amort_buy = (purchase_cost / t_horizon) if t_horizon else purchase_cost
        for i in range(1, t_horizon + 1):
            base = round_base_income(round_num + i)
            it = interest(g, cap)
            income_total += base + streak_term
            interest_total += it
            # 升级金按日程所在轮扣:v1 单步日程 = 首轮扣(追级压力前置,
            # 早扣少息 = 保守向)
            spend = amort_buy + amort_refresh + (lvl_cost if i == 1 else 0.0)
            g = g + base + streak_term + it - spend
        return gold - floor + income_total + interest_total \
            - purchase_cost - lvl_cost

    def refreshes_of(b: float) -> int:
        if b <= 0:
            return 0
        return int(b) // refresh_cost

    # 不动点:种子 = 接线批静态口径(gold−floor)//刷价(单调收敛起点);
    # 2-循环振荡取两支较小(保守端,见模块 docstring)。
    r_prev = max(0, (gold - floor) // refresh_cost)
    b = budget_at(r_prev)
    r_next = refreshes_of(b)
    for _ in range(_FIXED_POINT_PASSES):
        if r_next == r_prev:
            break
        r_prev, r_next = r_next, refreshes_of(budget_at(r_next))
    r_final = min(r_prev, r_next)
    b_final = budget_at(r_final)
    return BudgetPlan(refreshes=r_final, budget=int(b_final),
                      exhausted=b_final < 0)
