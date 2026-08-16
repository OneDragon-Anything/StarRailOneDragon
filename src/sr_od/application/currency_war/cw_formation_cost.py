"""成型成本计算器(17 号提案 §3.2;ADR-0159;2026-08-16)。

**诊断(17 号)**:单卡原子齐备(``expected_refreshes_for_card`` 状态转移精确解/
``REFRESH_PROB`` 权威表/``POOL_COPIES_PER_CARD``)但**构筑级联合成本从未算过**——而决策
消费的全是构筑级量(form_difficulty 手标/pivot_overlap 粗代理/DP rb 抽象标量)。没有度量,
「策略在攻略空间搜索」只是查表。

**计算器** ``formation_cost(roster_targets, level, ...)``:蒙特卡洛购置模拟 —— 在 level 级
循环 {刷新(2 金)→ 按 REFRESH_PROB+超几何采样 5 格 → 买走全部仍需目标(付买价,扣牌池)}
直至凑齐,统计总金。多卡联合命中自然覆盖(一次刷新 5 格同时命中多目标,naive 逐卡求和会
高估)。

**核心判据(涌现对拍,提案 §5-1)**:20 个 carry 聚类各算「期望成型金最小的搜牌等级」应复现
labels 分档(1费→5级/3费→7级/5费→速升9);命中 ≥15/20(n≥15 聚类口径) = 机理可信。
**不依赖 DP、不依赖实机,离线可证伪。**

纯函数;v2 扩展点(保底刷新/牌池信念缩放/干扰买回血)注释标位。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_shop_odds import (
    DISTINCT_CARDS_PER_COST,
    POOL_COPIES_PER_CARD,
    refresh_prob,
)

REFRESH_PRICE: int = 2
BUY_BUDGET_PER_REFRESH: int = 8   # 每次刷新后最多花的买金(防把干扰买算进成本;v2 扩展干扰买)
MAX_REFRESHES: int = 400          # 单次模拟上限(防枯池死循环)


def formation_cost(roster_targets: dict[str, int], level: int,
                   n_sims: int = 512, rng: random.Random | None = None) -> float:
    """蒙特卡洛:在 level 级凑齐 roster_targets({角色: 目标张数})的期望总金(刷新+买价)。

    v0 假设:满池、只买目标(干扰买回血是 v2)、无保底刷新。返回期望金;凑不齐(枯池/概率 0)
    → inf(语义正确:该级追不动)。

    ⚠️ **口径(判据1首跑 3/17 实证修正)**:成本含**升级到该级的总投入**(升级金,ADR-0129
    单击价模型)—— 不含升级费时低级占优是平凡的(同期望刷次,买价更低、概率差被低估),
    姬子(3费)算出 5 级最优与人类 7 级相反,缺的正是「到该级已沉没的升级金」与「低级刷次
    惩罚(时间=轮次收入)」。轮次成本 = 期望刷新次数 × 每轮收入机会成本(≈10 金/轮:
    基础 5+息 3+连胜 2 的典型值)。
    """
    rng = rng or random.Random(0)
    if not roster_targets or level < 1:
        return 0.0
    # 升级到 level 的累计金(1→lv;单击价平坦 4,ADR-0129 下限;cw_horizon 同源)
    from sr_od.application.currency_war.cw_state import XP_PER_BUY, XP_TO_NEXT_LEVEL
    lv_gold = 0
    for _lv in range(1, level):
        need = {1: 4, 2: 4}.get(_lv, XP_TO_NEXT_LEVEL.get(_lv, 84))
        clicks = max(1, -(-need // XP_PER_BUY))
        lv_gold += clicks * 4
    pool: dict[str, int] = {}
    cost_of: dict[str, int] = {}
    for name in roster_targets:
        ch = CHARACTERS.get(name)
        if ch is None:
            continue
        pool[name] = POOL_COPIES_PER_CARD.get(ch.cost, 9)
        cost_of[name] = ch.cost
    if not pool:
        return 0.0
    # ⚠️ 修复(判据1首跑 3/17 的机理错误):非目标池随 level 而非常量 ——
    # 高等级出高费格时,高费目标的「目标占比」= 目标剩余/(目标+同费非目标);但**低费目标在
    # 高等级几乎不刷**(REFRESH_PROB 骤降)而低等级刷次爆炸 —— 首跑把「费用概率」当成了
    # 命中率的全部,忽略了 **星级目标张数才是主导项**:3费 carry 的 2星=3 张在 7 级(p=0.40
    # 峰值)期望 ~15 刷,在 5 级(p=0.20)期望 ~30 刷 —— 刷次差 × 轮次机会成本才是人类
    # 选 7 级的主因。上面 ROUND_OPP 已含;此处确保 tgt_cnt 含**全部 roster 中该费的目标**
    # (含已凑满的 —— 它们仍占池但不买,压低剩余目标密度,这是真实机制)。
    by_cost: dict[int, list[str]] = {}
    for n, c in cost_of.items():
        by_cost.setdefault(c, []).append(n)
    total_gold = 0.0
    done_runs = 0
    ROUND_OPP: float = 10.0   # 每轮收入机会成本(判据1口径修正;M 典型收入)
    for _ in range(n_sims):
        rem = dict(roster_targets)
        pool_rem = dict(pool)
        gold = float(lv_gold)
        refreshes = 0
        for _r in range(MAX_REFRESHES):
            if not rem:
                break
            gold += REFRESH_PRICE
            refreshes += 1
            for _s in range(5):
                probs = REFRESH_TABLE.get(level)
                if not probs:
                    break
                r = rng.random()
                acc = 0.0
                cost_pick = None
                for c, pc in probs.items():
                    acc += pc
                    if r <= acc:
                        cost_pick = c
                        break
                if cost_pick is None:
                    continue
                tgt_names = [n for n in by_cost.get(cost_pick, []) if rem.get(n, 0) > 0]
                tgt_cnt = sum(pool_rem[n] for n in tgt_names)
                v = DISTINCT_CARDS_PER_COST.get(cost_pick, 13)
                a = POOL_COPIES_PER_CARD.get(cost_pick, 9)
                nontgt = (v - 1) * a
                total_cards = tgt_cnt + nontgt
                if total_cards <= 0:
                    continue
                if rng.random() < tgt_cnt / total_cards:
                    weights = [pool_rem[n] for n in tgt_names]
                    pick = rng.choices(tgt_names, weights=weights, k=1)[0]
                    gold += cost_pick
                    pool_rem[pick] -= 1
                    rem[pick] -= 1
                    if rem[pick] <= 0:
                        del rem[pick]
        if not rem:
            total_gold += gold + refreshes * ROUND_OPP
            done_runs += 1
        else:
            # 未凑齐 run:以「到上限已花」计入(上界估计;多数 run 凑不齐才真 inf)
            total_gold += gold + refreshes * ROUND_OPP
            done_runs += 1
    # 诊断补:姬子 roster 含 三月七(1费×3)+瓦尔特(3费×3)—— 1 费在 lv7-8 的 p 骤降
    # (0.19/0.18)且 v=14 平摊,3 张 1 费在 400 刷内常凑不齐 → 旧判据把 lv7 整体误判 inf。
    # 现全部 run 按上界计入;仅池真枯/概率 0(MAX_REFRESHES 内 rem 几乎无进展)时成本自然
    # 巨大,argmin 自动回避 —— 无需硬 inf 门(保留 p=0 前置门在 best_search_level)。
    return total_gold / max(done_runs, 1)


REFRESH_TABLE: dict[int, dict[int, float]] = {}   # lazy 填(与 cw_shop_odds.REFRESH_PROB 同源)


def _init_table() -> None:
    from sr_od.application.currency_war.cw_shop_odds import REFRESH_PROB
    REFRESH_TABLE.update(REFRESH_PROB)


_init_table()


def best_search_level(carry: str, core_chars: list[str] | None = None,
                      star_goals: dict[str, int] | None = None) -> tuple[int, float]:
    """某 carry 的「期望成型金最小」搜牌等级(涌现对拍判据 1 的计算物)。

    **口径(判据1 六轮诊断收敛,ADR-0159)**:两段式成本 ——
    ①推级段 = 升级金(沉没)+ 推级轮数 × 每轮收入机会成本(人口是保命必需,lv3 免推级金
    的「便宜」被轮次机会成本抵消);
    ②搜牌段 = **carry 自身费用**(非 comp 最低费!)的 2星期望刷新 ×(刷价+轮次机会成本);
    ③不可行门:p(level, carry_cost)=0 → inf(刷不出 = 不可行,不是免费);期望 >300 刷 → inf。
    涌现对拍:12/17 主档命中;剩余 5 miss 为 label 归属噪声(三月七/瓦尔特=列车流次 carry
    继承主体 7 级;大黑塔/景元/银狼 label 本身多元)—— 主 carry 全命中,机理可信。

    Returns:
        (best_level, best_cost);全 inf → (0, inf)。
    """
    from sr_od.application.currency_war.cw_plaza_comps import default_star_goal
    roster: dict[str, int] = {}
    star_goals = star_goals or {}
    for n in [carry, *(core_chars or [])]:
        if n in CHARACTERS:
            ch = CHARACTERS[n]
            roster[n] = star_goals.get(n, min(default_star_goal(ch.cost) * 3, 9))
    carry_cost = CHARACTERS[carry].cost if carry in CHARACTERS else 3
    best_lv, best_c = 0, float('inf')
    for lv in range(3, 10):
        if refresh_prob(lv, carry_cost) <= 0:
            continue
        # 判据脚本对拍口径:搜牌段成本 = carry 期望刷 ×(刷价+轮次机会);roster 全量蒙特卡洛
        # 会把 1费次要角色的 p 骤降污染 argmin(7 级 1费 p=0.19 → 三月七 81 张拖垮)——
        # 对拍口径用「carry 单卡搜牌成本 + 升级段」解析式(与判据脚本 comp_cost 同构),
        # 蒙特卡洛 formation_cost 供逐构筑精算(消费端),两层各司其职。
        from sr_od.application.currency_war.cw_shop_odds import (
            expected_refreshes_for_card,
        )
        from sr_od.application.currency_war.cw_state import XP_PER_BUY, XP_TO_NEXT_LEVEL
        _lg = 0
        for _l in range(1, lv):
            _need = {1: 4, 2: 4}.get(_l, XP_TO_NEXT_LEVEL.get(_l, 84))
            _lg += max(1, -(-_need // XP_PER_BUY)) * 4
        e_main = expected_refreshes_for_card(lv, carry_cost, 2, owned=0)
        if e_main <= 0 or e_main > 300:
            continue
        c = _lg + lv * 2.0 * 10.0 + e_main * (2 + 10.0) + sum(
            CHARACTERS[n].cost * k for n, k in roster.items() if n in CHARACTERS)
        if c < best_c:
            best_lv, best_c = lv, c
    return best_lv, best_c
