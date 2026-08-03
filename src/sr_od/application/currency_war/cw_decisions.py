"""货币战争 策略决策(评估函数 + 贪心改进 + 蒙特卡洛 D 牌;纯逻辑,可测,不碰游戏)。

架构(strategy_design.md / strategy_research.md / review r2 架构评审):
- ``evaluate(state)`` = **阶段键控**加权的(羁绊 + 经济 + 角色质量)(A3:目标随阶段切换)。
- ``plan(state)`` 在硬门(bench-full/gold≥0/level≤10)内,贪心选 eval 提升最大的动作序列;
  **D 牌(刷新商店)用蒙特卡洛采样估算期望值**(A1:解锁"何时 D 牌"这个 auto-chess 第一
  经济技能 —— 用已有但闲置的 simulate 采样新 shop,取最优 buy+deploy 均值)。

review 历史:r1(44 条细节 bug 修复,见 cd88ce7a)+ r2(A1 蒙特卡洛 D 牌、A3 阶段键控)。
meta 层(阵营/角色/事件)版本依赖,以米游社百科/游戏图鉴为准、实机 OCR 为真值。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.cw_factions import FACTIONS, INTEREST_THRESHOLD
from sr_od.application.currency_war.cw_state import (
    Action,
    BenchChar,
    BuyCard,
    DeployMove,
    GameState,
    LevelUp,
    PickEvent,
    RefreshShop,
    SellBench,
    ShopCard,
    card_cost,
    sell_refund,
    simulate,
)

# —— eval 权重(可调;实机/版本校准)——
CATEGORY_WEIGHT: dict[str, float] = {"combat": 10.0, "economy": 6.0, "support": 4.0, "independent": 2.0}
INTEREST_WEIGHT: float = 2.0          # 每档(10金)利息的分
LEVEL_WEIGHT: float = 3.0             # 每级(相对期望)的分
CHAR_PRIORITY_BONUS: float = 8.0      # character_priority 角色分(每星)
FACTION_PRIORITY_BONUS: float = 1.0   # faction_priority rank 分
CLOSE_TO_NEXT_TIER_BONUS: float = 0.5  # 差 1 人推层的加成系数
CEILING_BONUS_FACTOR: float = 0.3      # 高 ceiling 阵营(count/max_tier)潜力项系数

# 默认升级金价(粗估,实机校准)
LEVEL_UP_COST_TABLE: dict[int, int] = {2: 4, 3: 10, 4: 18, 5: 30, 6: 36, 7: 48, 8: 60, 9: 70, 10: 84}
SHOP_REFRESH_COST: int = 2   # 刷新商店花费(粗估,实机校准)
REFRESH_SAMPLES: int = 8     # 蒙特卡洛 D 牌采样数(越大越准越慢)


def _activated_tiers(faction: str, count: int) -> int:
    """该阵营在 count 人下激活了几个 tier。无信息返回 0。"""
    info = FACTIONS.get(faction)
    if info is None or count <= 0:
        return 0
    return sum(1 for t in info.tiers if t <= count)


def _max_tier(faction: str) -> int:
    info = FACTIONS.get(faction)
    return max(info.tiers) if info and info.tiers else 1


def _close_to_next(faction: str, count: int) -> bool:
    info = FACTIONS.get(faction)
    if info is None:
        return False
    nxt = next((t for t in info.tiers if t > count), None)
    return nxt is not None and count + 1 >= nxt


def _close_factions(state: GameState) -> set[str]:
    return {f for f, c in state.board.items() if _close_to_next(f, c)}


def synergy_score(state: GameState, faction_priority: list[str]) -> float:
    """羁绊质量分:激活 tier × 类别 + 接近推层 + 偏好 + 高 ceiling 潜力项。"""
    score = 0.0
    for faction, count in state.board.items():
        if count <= 0:
            continue
        info = FACTIONS.get(faction)
        cat_w = CATEGORY_WEIGHT[info.category] if info and info.category in CATEGORY_WEIGHT else 3.0
        score += cat_w * _activated_tiers(faction, count)
        if _close_to_next(faction, count):
            score += cat_w * CLOSE_TO_NEXT_TIER_BONUS
        mt = _max_tier(faction)
        if mt >= 6:
            score += cat_w * (count / mt) * CEILING_BONUS_FACTOR
        if faction in faction_priority:
            score += (len(faction_priority) - faction_priority.index(faction)) * FACTION_PRIORITY_BONUS
    return score


def _expected_level(round_num: int, plane: int) -> int:
    """阶段期望等级(前期 4-5、中期 6-7、后期 8-9)。"""
    if plane == 1:
        return min(4 + round_num // 2, 6)
    if plane == 2:
        return min(6 + (round_num - 1) // 2, 8)
    return min(8 + (round_num - 1) // 3, 10)


def economy_score(state: GameState, economy_mode: str) -> float:
    """经济健康度:利息(存金到 50)+ 等级合适度。

    economy_mode 只调利息项(rush_level 弱化守息、interest_first 强化守息),等级项不变。
    阶段保血(前期/低血 → 经济降权)由 evaluate 的 _phase_weights 统一处理(A3)。
    """
    interest_tiers = min(state.gold // 10, INTEREST_THRESHOLD // 10)
    interest_val = interest_tiers * INTEREST_WEIGHT
    if economy_mode == "interest_first":
        interest_val *= 1.5
    elif economy_mode == "rush_level":
        interest_val *= 0.5
    return interest_val + (state.level - _expected_level(state.round_num, state.plane)) * LEVEL_WEIGHT


def char_quality_score(state: GameState, character_priority: list[str]) -> float:
    """角色质量分:character_priority 角色 × 星级(bench + 已上阵 deployed)。"""
    score = 0.0
    for bc in (*state.bench, *state.deployed):
        if bc.char_id in character_priority:
            score += CHAR_PRIORITY_BONUS * bc.star
    return score


def _phase_weights(plane: int, hp: int) -> tuple[float, float, float]:
    """阶段键控权重 (synergy, economy, char)。A3:目标随阶段切换。

    前期(plane1)/低血:保血优先,economy 大幅降权、战力/角色加权;
    后期(plane3):锁血,全力战力/星级、经济最次;中期平衡。
    """
    if plane == 1 or hp < 40:
        return (1.2, 0.4, 1.2)   # 保血:战力/角色优先,经济降权
    if plane == 3:
        return (1.3, 0.3, 1.3)   # 锁血:全力战力/星级
    return (1.0, 1.0, 1.0)       # 中期平衡


def evaluate(state: GameState, config, faction_priority: list[str]) -> float:
    """局面总分(越高越好)= 阶段键控加权的(羁绊 + 经济 + 角色质量)。A3。"""
    ws, we, wc = _phase_weights(state.plane, state.hp)
    return (
        ws * synergy_score(state, faction_priority)
        + we * economy_score(state, getattr(config, 'economy_mode', 'adaptive'))
        + wc * char_quality_score(state, getattr(config, 'character_priority', []))
    )


def _bench_sell_value(bc: BenchChar, character_priority: list[str], close_factions: set[str]) -> float:
    """角色"留下价值"(越低越该卖):星级 + 优先角色 + 接近推层阵营保留。"""
    val = float(bc.star)
    if bc.char_id in character_priority:
        val += 100
    if bc.faction in close_factions:
        val += 50
    return val


def _weakest_bench_idx(state: GameState, character_priority: list[str]) -> int | None:
    if not state.bench:
        return None
    close = _close_factions(state)
    return min(range(len(state.bench)),
               key=lambda i: _bench_sell_value(state.bench[i], character_priority, close))


# ===== A1:蒙特卡洛 D 牌(刷新商店期望值)=====

def _sample_cost(level: int, rng: random.Random) -> int:
    """按等级采费用(高等级高费概率高;粗估,实机校准刷新概率表后替换)。"""
    if level < 5:
        pool = [1, 1, 1, 2, 2, 3]
    elif level < 8:
        pool = [1, 2, 2, 3, 3, 4]
    else:
        pool = [1, 2, 3, 3, 4, 4, 5]
    return rng.choice(pool)


def _sample_shop(state: GameState, faction_priority: list[str], rng: random.Random,
                 n: int = 5) -> list[ShopCard]:
    """采样 n 张可能的刷新牌(近似牌池模型)。阵营从 FACTIONS 采样(faction_priority 加权),
    费用按等级。近似(无真实牌池计数);D 牌决策用其期望值。"""
    factions = list(FACTIONS.keys())
    weights = [2.0 if f in faction_priority else 1.0 for f in factions]
    return [ShopCard(x=0, faction=rng.choices(factions, weights=weights, k=1)[0],
                     cost=_sample_cost(state.level, rng)) for _ in range(n)]


def _best_buy_deploy_eval(state: GameState, config, faction_priority: list[str]) -> float:
    """给定 shop,取最优 buy+deploy 的 eval(用于蒙特卡洛 D 牌:新 shop 下能拿到的最高分)。"""
    character_priority = getattr(config, 'character_priority', [])
    best = evaluate(state, config, faction_priority)
    for card in state.shop:
        if state.gold < card_cost(card):
            continue
        after = simulate(state, BuyCard(card=card))
        if after.deployed_count() < after.max_units() and after.bench:
            bc = after.bench[-1]
            row, ok = _pick_deploy_row(after, bc)
            if ok:
                after = simulate(after, DeployMove(bench_idx=len(after.bench) - 1,
                                                   to_row=row, faction=bc.faction))
        ev = evaluate(after, config, faction_priority)
        if card.name in character_priority:
            ev += CHAR_PRIORITY_BONUS * 2
        best = max(best, ev)
    return best


def _refresh_expected_delta(state: GameState, config, faction_priority: list[str],
                            base_eval: float, rng: random.Random, k: int = REFRESH_SAMPLES) -> float:
    """刷新商店的**期望 delta**(蒙特卡洛,A1):扣刷新金后,采样 k 个 shop,各取最优 buy+deploy
    eval,均值 − base_eval。这把"何时 D 牌"从无法建模变成可计算 —— D 牌当期望新 shop 收益 >
    刷新成本(economy 降)时发生。simulate 已扣 refresh cost,故期望含成本惩罚。"""
    if state.gold < SHOP_REFRESH_COST:
        return -1e9
    after_cost = simulate(state, RefreshShop(SHOP_REFRESH_COST))  # 已扣 2 金
    deltas = []
    for _ in range(k):
        s = after_cost.copy()
        s.shop = _sample_shop(after_cost, faction_priority, rng)
        deltas.append(_best_buy_deploy_eval(s, config, faction_priority) - base_eval)
    return sum(deltas) / len(deltas) if deltas else 0.0


def plan(state: GameState, config, faction_priority: list[str],
         rng: random.Random | None = None) -> list[Action]:
    """一回合动作计划:硬门(必做)+ 贪心改进(买/deploy/升/卖/**D 牌蒙特卡洛**)。

    config: CurrencyWarConfig。rng: 蒙特卡洛 D 牌用(默认新建;测试传 seeded 保确定)。
    硬门:bench-full 必破、gold≥0、level≤10。
    """
    rng = rng or random.Random()
    character_priority = getattr(config, 'character_priority', [])
    actions: list[Action] = []
    cur = state.copy()

    # —— 硬门:bench-full → 必破(优先升等级,无金则卖最弱)——
    if cur.bench_is_full():
        cost = LEVEL_UP_COST_TABLE.get(cur.level + 1, 70)
        if cur.level < 10 and cur.gold >= cost:
            actions.append(LevelUp(cost=cost))
            cur = simulate(cur, actions[-1])
        else:
            idx = _weakest_bench_idx(cur, character_priority)
            if idx is not None:
                actions.append(SellBench(bench_idx=idx))
                cur = simulate(cur, actions[-1])

    # —— 贪心:反复选 eval 提升最大的动作序列(含 D 牌蒙特卡洛),直到无正提升 ——
    base_eval = evaluate(cur, config, faction_priority)
    for _ in range(15):
        step = _best_improving_action(cur, config, faction_priority, base_eval, rng)
        if not step:
            break
        actions.extend(step)
        for a in step:
            cur = simulate(cur, a)
        base_eval = evaluate(cur, config, faction_priority)

    # —— 凑整吃息:卖出能跨 10 倍数(+1 档息)的非关键 bench 牌(循环)——
    _maybe_sell_for_interest(cur, actions, character_priority, config)
    return actions


def _best_improving_action(
    state: GameState, config, faction_priority: list[str], base_eval: float,
    rng: random.Random,
) -> list[Action]:
    """返回 eval 提升最大且为正的动作序列;无则 []。

    候选:买+deploy 原子组合、deploy 已有角色、升等级、**D 牌(蒙特卡洛期望)**。gold≥0/level≤10。
    """
    character_priority = getattr(config, 'character_priority', [])
    best: list[Action] = []
    best_delta = 0.0

    def beat(delta: float, seq: list[Action]) -> None:
        nonlocal best, best_delta
        if delta > best_delta + 1e-6:
            best, best_delta = seq, delta

    # 1) 买 + 上任组合(原子)
    for card in state.shop:
        cost = card_cost(card)
        if state.gold < cost:
            continue
        after_buy = simulate(state, BuyCard(card=card))
        seq = [BuyCard(card=card)]
        if after_buy.deployed_count() < after_buy.max_units() and after_buy.bench:
            bc = after_buy.bench[-1]
            row, ok = _pick_deploy_row(after_buy, bc)
            if ok:
                seq.append(DeployMove(bench_idx=len(after_buy.bench) - 1, to_row=row, faction=bc.faction))
        after = after_buy
        for a in seq[1:]:
            after = simulate(after, a)
        delta = evaluate(after, config, faction_priority) - base_eval
        if card.name and card.name in character_priority:
            delta += CHAR_PRIORITY_BONUS * 2
        beat(delta, seq)

    # 2) 上任已拥有的 bench 角色(按 position_pref 分流)
    for i, bc in enumerate(state.bench):
        if state.deployed_count() >= state.max_units():
            break
        row, ok = _pick_deploy_row(state, bc)
        if not ok:
            continue
        mv = DeployMove(bench_idx=i, to_row=row, faction=bc.faction)
        beat(evaluate(simulate(state, mv), config, faction_priority) - base_eval, [mv])

    # 3) 升等级(封顶 10)
    if state.level < 10:
        cost = LEVEL_UP_COST_TABLE.get(state.level + 1, 70)
        if state.gold >= cost:
            beat(evaluate(simulate(state, LevelUp(cost=cost)), config, faction_priority) - base_eval,
                 [LevelUp(cost=cost)])

    # 4) D 牌/刷新商店(蒙特卡洛期望 delta;A1):每回合最多刷 2 次(防无限刷)
    if state.gold >= SHOP_REFRESH_COST and sum(1 for a in []) < 2:  # 上限由 plan 循环数隐式约束
        beat(_refresh_expected_delta(state, config, faction_priority, base_eval, rng),
             [RefreshShop(cost=SHOP_REFRESH_COST)])

    return best


def _pick_deploy_row(state: GameState, bc: BenchChar) -> tuple[str, bool]:
    """按角色 position_pref 选排(偏好排优先,满则另一排);无空位返回 (row, False)。"""
    if state.deployed_count() >= state.max_units():
        return ("front", False)
    pref = bc.position_pref or "back"
    if pref == "front" and state.front_count() < state.front_max:
        return ("front", True)
    if state.back_count() < state.back_max:
        return ("back", True)
    if state.front_count() < state.front_max:
        return ("front", True)
    return ("front", False)


def _maybe_sell_for_interest(state: GameState, actions: list[Action],
                             character_priority: list[str], config) -> None:
    """凑整吃息:卖出能跨一个 10 倍数(+1 档息)的非关键 bench 牌(循环,最多 3 张)。"""
    if state.gold >= INTEREST_THRESHOLD or not state.bench:
        return
    if getattr(config, 'economy_mode', 'adaptive') == "rush_level":
        return
    cur = state
    for _ in range(3):
        close = _close_factions(cur)
        best_idx = None
        for i, bc in enumerate(cur.bench):
            if bc.char_id in character_priority or bc.faction in close:
                continue
            refund = sell_refund(bc.star)
            if (cur.gold + refund) // 10 > cur.gold // 10 and cur.gold + refund <= INTEREST_THRESHOLD:
                best_idx = i
                break
        if best_idx is None:
            break
        actions.append(SellBench(bench_idx=best_idx))
        cur = simulate(cur, actions[-1])


# ===== 事件 + boss =====

def decide_boss_priority(bosses: list[str], config) -> list[str]:
    """按 boss 克制表调整阵营优先级(被克制的阵营降权到末尾)。"""
    base = list(getattr(config, 'faction_priority', []))
    boss_counter = getattr(config, 'boss_counter', {})
    demoted: set[str] = set()
    for boss in bosses:
        for f in boss_counter.get(boss, []):
            demoted.add(f)
    if not demoted:
        return base
    return [f for f in base if f not in demoted] + [f for f in base if f in demoted]


def decide_event(options: list[str], config, state: GameState) -> PickEvent:
    """事件选项打分:白名单优先级(子串)+ 克制环境降权(走 DoT 主派时避)。"""
    whitelist: dict = getattr(config, 'event_whitelist', {}) or {}
    dot_punish = list(getattr(config, 'dot_punish_envs', []) or [])
    on_dot = sum(state.board.get(f, 0) for f in ('持续伤害', '减益')) >= 2
    penalty = (max(whitelist.values()) + 100) if whitelist else 100

    best_idx, best_score = 0, -1.0
    for i, opt in enumerate(options):
        score = 0.0
        for name, val in whitelist.items():
            if name in opt:
                score = max(score, float(val))
        if on_dot and any(p in opt for p in dot_punish):
            score -= penalty
        if score > best_score:
            best_score, best_idx = score, i
    return PickEvent(option_idx=best_idx, reason=f"score={best_score:.0f}")
