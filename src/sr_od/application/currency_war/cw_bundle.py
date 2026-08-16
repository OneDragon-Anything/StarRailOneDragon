"""回合内联合行动束优化器 v0(06 号重设计提案;ADR-0156;2026-08-16)。

**诊断(06 号)**:历史头号杀手(board 散 → P2 秒死)与 commit/pivot/prefilter/drought-bail
一族粘性补丁的共因 —— 贪心按「单动作边际」估值,看不见**动作间交互**:第 5/6 张同 trait 的
断点跳变、同商店 2 张同名(要么都买凑星、要么都不买)、连锁买卖净金。补丁是「选择机制看不见
交互」的系统性补偿;在贪心框架内这些参数没有正确答案。

**设计(提案 §2)**:对买牌子集(束)联合估值 V(B) = Σ 单动作 delta(加性部分 = 现贪心
eval,天然上界)+ Σ 交互项(断点跳变/同名升星链)。三条性质:
1. 关交互项 → 束退化为最优单买 ≡ 现贪心(对拍锚点,测试锁定);
2. 束优 ≥ 贪心按构造(同一估值下);
3. off-target 入束仅当其参与交互项(联合价值可见才放行 —— 粘性门退役的雏形)。

纯函数 + 离线可测;影子接缝由 cw_plan 调用(``BUNDLE_SEAM_ACTIVE``,默认 False)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_state import (
    BuyCard,
    GameState,
    card_cost,
    simulate,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_comps import Comp

# 交互项权重(plaza 锚定先验,校准点;防 optimizer's curse:只对 target/skeleton 阵营生效)
BREAK_W: float = 6.0        # 阵营计数跨过一个激活档(tier)的联合 bonus
PAIR_W: float = 2.0         # 同名第 2 张(凑 2★ 进度,1/3)
MERGE_W: float = 8.0        # 同名第 3 张(当场 3合1 → 2★)
BUNDLE_MARGIN: float = 0.5  # 束须超最优单买的最小余量(防平局噪声翻转)

BUNDLE_SEAM_ACTIVE: bool = False   # ADR-0156:影子开关,False = 现贪心生效


def _owned_faction_counts(state: GameState) -> dict[str, int]:
    """bench + deployed 的阵营计数(交互项的「买前」基线)。"""
    counts: dict[str, int] = {}
    for bc in [*state.bench, *state.deployed]:
        if bc.faction and bc.faction != '?':
            counts[bc.faction] = counts.get(bc.faction, 0) + 1
    return counts


def _owned_name_counts(state: GameState) -> dict[str, int]:
    counts: dict[str, int] = {}
    for bc in [*state.bench, *state.deployed]:
        if bc.char_id:
            counts[bc.char_id] = counts.get(bc.char_id, 0) + 1
    return counts


def _interaction_bonus(buys: list, state: GameState, target_comp: Comp | None) -> float:
    """束的交互项:断点跳变 + 同名升星链。只对 target/骨架阵营计分(防凑错组合)。"""
    from sr_od.application.currency_war.cw_comps import skeleton_factions
    bonus = 0.0
    focus = set(target_comp.factions) if target_comp is not None else set()
    focus |= skeleton_factions()
    # 1) 断点跳变:买前计数 → 买后计数跨过的激活档数
    fac_before = _owned_faction_counts(state)
    fac_after = dict(fac_before)
    for c in buys:
        if c.faction and c.faction != '?':
            fac_after[c.faction] = fac_after.get(c.faction, 0) + 1
    for f, after_n in fac_after.items():
        if f not in focus:
            continue
        tiers = FACTIONS[f].tiers if f in FACTIONS else ()
        crossed = sum(1 for t in tiers if fac_before.get(f, 0) < t <= after_n)
        bonus += BREAK_W * crossed
    # 2) 同名升星链:owned + 束内同名数;第 2 张 PAIR_W、第 3 张 MERGE_W(3合1 当场 2★)
    name_before = _owned_name_counts(state)
    name_bundle: dict[str, int] = {}
    for c in buys:
        if c.name:
            name_bundle[c.name] = name_bundle.get(c.name, 0) + 1
    for n, k in name_bundle.items():
        owned = name_before.get(n, 0)
        total = owned + k
        if total >= 3 and owned < 3:
            bonus += MERGE_W          # 凑齐 3 张合并
        elif total == 2:
            bonus += PAIR_W           # 2/3 进度
    return bonus


def bundle_select(state: GameState, config, faction_priority: list[str],
                  target_comp: Comp | None, *, interactions: bool = True):
    """束优化选择:返回 actions 列表;None = 无优于贪心的束(调用方回退贪心)。

    关交互项(interactions=False)→ 返回最优**单买**(与贪心同参对拍锚点)。
    """
    from sr_od.application.currency_war.cw_evaluate import evaluate
    from sr_od.application.currency_war.cw_plan import _concentration_delta
    base = evaluate(state, config, faction_priority, target_comp)
    # 单买 delta(贪心同口径:eval 差 + 集中度项)
    singles: list[tuple[float, object]] = []
    for c in state.shop:
        if state.gold < card_cost(c) or not c.name:
            continue
        d = (evaluate(simulate(state, BuyCard(card=c)), config, faction_priority, target_comp) - base
             + _concentration_delta(c, state, target_comp))
        singles.append((d, c))
    if not singles:
        return None
    best_single_d, best_single = max(singles, key=lambda t: t[0])
    if not interactions:
        return [BuyCard(card=best_single)] if best_single_d > 0 else None
    # 束枚举:2^5 买牌子集(联合可负担);V = Σ delta + 交互项
    import itertools
    cards = [c for _, c in singles]
    deltas = {c.name: d for d, c in singles}   # 同名卡(shop 双开)同 delta
    best_v, best_buys = best_single_d, None
    for r in range(1, len(cards) + 1):
        for combo in itertools.combinations(cards, r):
            cost = sum(card_cost(c) for c in combo)
            if cost > state.gold:
                continue
            v = sum(deltas[c.name] for c in combo)
            v += _interaction_bonus(list(combo), state, target_comp)
            if v > best_v + BUNDLE_MARGIN:
                best_v, best_buys = v, combo
    if best_buys is None:
        return None
    return [BuyCard(card=c) for c in best_buys]
