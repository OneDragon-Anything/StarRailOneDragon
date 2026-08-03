"""货币战争 策略决策(评估函数 + 贪心改进;纯逻辑,可测,不碰游戏)。

架构(见 strategy_design.md / strategy_research.md):
- ``evaluate(state)`` 给局面打分 = 羁绊激活质量 + 经济健康度 + 角色质量。
- ``plan(state)`` 在**硬规则门**(bench-full 必破、gold 不为负)内,**贪心选 eval 提升最大
  的动作**(买/卖/升/deploy);研究战术(牌池操纵、第一位面保血、凑整吃息)作权重/注入。
- ``decide_event`` 事件白名单打分;``decide_boss_priority`` boss 克制调整阵营优先级。

自适应核心:**贪心加深当前激活最高的阵营**(eval 天然奖励高 tier),config.faction_priority
做 tiebreaker/方向,boss 克制做覆盖切换 —— 不死追单一阵容。meta 层(阵营/角色/事件优先级)
版本依赖,以米游社百科/游戏图鉴为准、实机 OCR 为真值。
"""
from __future__ import annotations

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
    simulate,
)

# —— eval 权重(可调;实机/版本校准)——
CATEGORY_WEIGHT: dict[str, float] = {"combat": 10.0, "economy": 6.0, "support": 4.0}
INTEREST_WEIGHT: float = 2.0          # 每档(10金)利息的分
LEVEL_WEIGHT: float = 3.0             # 每级(相对期望)的分
CHAR_PRIORITY_BONUS: float = 8.0      # character_priority 角色分(每星)
FACTION_PRIORITY_BONUS: float = 1.0   # faction_priority rank 分
CLOSE_TO_NEXT_TIER_BONUS: float = 0.5  # 差 1 人推层的加成系数
# 第一位面/低血时经济权重的衰减(保血优先)
EARLY_WEAK_ECON_FACTOR: float = 0.5

# 默认升级金价(粗估,实机校准;LEVEL_UP_GOLD_COST 的扩展)
LEVEL_UP_COST_TABLE: dict[int, int] = {2: 4, 3: 10, 4: 18, 5: 30, 6: 36, 7: 48, 8: 60, 9: 70, 10: 84}
SHOP_REFRESH_COST: int = 2  # 刷新商店花费(粗估,实机校准)


def _activated_tiers(faction: str, count: int) -> int:
    """该阵营在 count 人下激活了几个 tier(含 1 人第 1 层)。无信息返回 0。"""
    info = FACTIONS.get(faction)
    if info is None or count <= 0:
        return 0
    return sum(1 for t in info.tiers if t <= count)


def _close_to_next(faction: str, count: int) -> bool:
    """再 +1 人是否推到下一激活层。"""
    info = FACTIONS.get(faction)
    if info is None:
        return False
    nxt = next((t for t in info.tiers if t > count), None)
    return nxt is not None and count + 1 >= nxt


def synergy_score(state: GameState, faction_priority: list[str]) -> float:
    """羁绊激活质量分(核心):高 tier + 即将推层 + 偏好阵营 加分。"""
    score = 0.0
    for faction, count in state.board.items():
        if count <= 0:
            continue
        info = FACTIONS.get(faction)
        cat_w = CATEGORY_WEIGHT[info.category] if info and info.category in CATEGORY_WEIGHT else 3.0
        activated = _activated_tiers(faction, count)
        score += cat_w * activated
        if _close_to_next(faction, count):
            score += cat_w * CLOSE_TO_NEXT_TIER_BONUS
        if faction in faction_priority:
            rank = faction_priority.index(faction)
            score += (len(faction_priority) - rank) * FACTION_PRIORITY_BONUS
    return score


def economy_score(state: GameState, economy_mode: str) -> float:
    """经济健康度:利息(存金到 50)+ 等级合适度。

    保血:第一位面 / 低血时,**利息囤积**价值衰减(优先把金花在战力上,研究:第一位面保血 > 利息);
    等级合适度不衰减(早升等级仍好)。
    """
    interest_tiers = min(state.gold // 10, INTEREST_THRESHOLD // 10)  # 最多 5 档
    interest_val = interest_tiers * INTEREST_WEIGHT
    if state.plane == 1 or state.hp < 40:
        interest_val *= EARLY_WEAK_ECON_FACTOR
    expected = _expected_level(state.round_num, state.plane)
    level_val = (state.level - expected) * LEVEL_WEIGHT
    score = interest_val + level_val
    if economy_mode == "interest_first":
        score *= 1.3
    elif economy_mode == "rush_level":
        score *= 0.7
    return score


def _expected_level(round_num: int, plane: int) -> int:
    """该阶段期望等级(研究节拍:前期 4-5、中期 6-7、后期 8-9)。"""
    if plane == 1:
        return min(4 + round_num // 2, 6)
    if plane == 2:
        return min(6 + (round_num - 1) // 2, 8)
    return min(8 + (round_num - 1) // 3, 10)


def char_quality_score(state: GameState, character_priority: list[str]) -> float:
    """角色质量分:character_priority 角色 + 高星级 加分(已上阵 + bench)。"""
    score = 0.0
    for bc in state.bench:
        if bc.char_id in character_priority:
            score += CHAR_PRIORITY_BONUS * bc.star
    return score


def evaluate(state: GameState, config, faction_priority: list[str]) -> float:
    """局面总分(越高越好)。config 为 CurrencyWarConfig(取 economy_mode/character_priority)。"""
    return (
        synergy_score(state, faction_priority)
        + economy_score(state, getattr(config, 'economy_mode', 'adaptive'))
        + char_quality_score(state, getattr(config, 'character_priority', []))
    )


# ===== 决策:plan(贪心改进) =====

def _bench_sell_value(bc: BenchChar, character_priority: list[str]) -> float:
    """角色"留下价值"(越低越该卖):非优先 + 低星 + 非接近推层阵营 → 低。"""
    val = bc.star
    if bc.char_id in character_priority:
        val += 100  # 优先角色不卖
    return val


def _weakest_bench_idx(state: GameState, character_priority: list[str]) -> int | None:
    """返回最该卖的 bench 索引(价值最低);空返回 None。"""
    if not state.bench:
        return None
    return min(range(len(state.bench)),
               key=lambda i: _bench_sell_value(state.bench[i], character_priority))


def plan(state: GameState, config, faction_priority: list[str]) -> list[Action]:
    """一回合动作计划:硬门(必做)+ 贪心改进(买/deploy/升/卖)+ 战术注入。

    config: CurrencyWarConfig。返回按执行顺序的 Action 列表(op 层执行)。
    gold 永不为负;bench-full 必破(卖/升)。
    """
    character_priority = getattr(config, 'character_priority', [])
    aggression = getattr(config, 'aggression', 'balanced')
    actions: list[Action] = []
    cur = state.copy()
    base_eval = evaluate(cur, config, faction_priority)

    # —— 硬门 1:bench-full 阻塞出战 → 必破(优先升等级,无金则卖最弱)——
    # bench 满定义:备战栏(拥有数)达到上限。简化:bench 数 >= level(可上阵)且已超容量。
    # 这里用 bench 条数 vs 一个软上限(等级+2);实机由"备战席已满"OCR 警告触发更准。
    bench_capacity = max(state.level + 2, 5)
    if len(cur.bench) >= bench_capacity:
        cost = LEVEL_UP_COST_TABLE.get(cur.level + 1, 70)
        if cur.gold >= cost:
            actions.append(LevelUp(cost=cost))
            cur = simulate(cur, actions[-1])
        else:
            idx = _weakest_bench_idx(cur, character_priority)
            if idx is not None:
                actions.append(SellBench(bench_idx=idx))
                cur = simulate(cur, actions[-1])
        base_eval = evaluate(cur, config, faction_priority)

    # —— 贪心:反复选 eval 提升最大的动作,直到无正提升或预算尽 ——
    for _ in range(12):  # 上限防死循环
        best = _best_improving_action(cur, config, faction_priority, base_eval)
        if best is None:
            break
        actions.append(best)
        cur = simulate(cur, best)
        base_eval = evaluate(cur, config, faction_priority)

    # —— 战术注入:牌池操纵(NGA)—— 满息且有 bench 空间 + 余金 → 买非优先牌改牌池 ——
    if cur.gold >= INTEREST_THRESHOLD and len(cur.bench) < bench_capacity:
        for card in cur.shop:
            if cur.gold < (card.cost or 3):
                continue
            if card.name in character_priority or card.faction in faction_priority[:3]:
                continue  # 优先牌已在贪心阶段买;这里只买"不想要但改池"的
            if aggression == "conservative":
                break  # 保守模式不做牌池操纵
            actions.append(BuyCard(card=card))
            cur = simulate(cur, actions[-1])

    # —— 凑整吃息:余金卡在 10 倍数上方且 bench 有低价值牌 → 卖到临界下 ——
    _maybe_sell_for_interest(cur, actions, character_priority)

    return actions


def _best_improving_action(
    state: GameState, config, faction_priority: list[str], base_eval: float,
) -> Action | None:
    """在所有合法动作里,返回 eval 提升最大且为正的;无则 None。买按"买+deploy"组合评估。"""
    character_priority = getattr(config, 'character_priority', [])
    best: Action | None = None
    best_delta = 0.0

    def consider(candidate: Action) -> None:
        nonlocal best, best_delta
        if not _affordable(state, candidate):
            return
        delta = evaluate(simulate(state, candidate), config, faction_priority) - base_eval
        if delta > best_delta + 1e-6:
            best, best_delta = candidate, delta

    # 1) 买 + 上任组合:买后立即 deploy 到最佳空槽,看 board eval 提升
    for card in state.shop:
        if state.gold < (card.cost or 3):
            continue
        after_buy = simulate(state, BuyCard(card=card))
        # deploy 到能让该阵营推层/加深的排(有空槽时)
        row, ok = _pick_deploy_row(after_buy, card.faction)
        if ok:
            after = simulate(after_buy, DeployMove(bench_idx=len(after_buy.bench) - 1,
                                                   to_row=row, faction=card.faction))
        else:
            after = after_buy  # 无空槽:只评估"买落 bench"(角色质量分)
        delta = evaluate(after, config, faction_priority) - base_eval
        # character_priority 万用核心:出现就抓(研究),给强加成(哪怕阵营不推层)
        if card.name and card.name in character_priority:
            delta += CHAR_PRIORITY_BONUS * 2
        if delta > best_delta + 1e-6:
            best, best_delta = BuyCard(card=card), delta

    # 2) 上任已拥有的 bench 角色(免费 deploy)
    deployed = state.deployed_count()
    for i, bc in enumerate(state.bench):
        if deployed >= state.max_units():
            break
        row, ok = _pick_deploy_row(state, bc.faction)
        if not ok:
            continue
        consider(DeployMove(bench_idx=i, to_row=row, faction=bc.faction))

    # 3) 升等级(解锁上阵位 + 后续高费率;这里主要看是否解锁槽位提升)
    cost = LEVEL_UP_COST_TABLE.get(state.level + 1, 70)
    if state.gold >= cost:
        consider(LevelUp(cost=cost))

    # 4) 卖(凑整吃息/腾位)——单独卖通常降 eval,除非换息;放低优先,由 _maybe_sell_for_interest 兜底
    return best


def _pick_deploy_row(state: GameState, faction: str) -> tuple[str, bool]:
    """选 deploy 到哪排(前排优先坦克,但简化:有空位即可)。返回 (row, ok)。"""
    deployed = state.deployed_count()
    if deployed >= state.max_units():
        return ("back", False)
    # 简化:前排优先(坦克/近战);实机按角色命途细化
    return ("front", True)


def _affordable(state: GameState, action: Action) -> bool:
    """gold 不为负门。"""
    if isinstance(action, (BuyCard,)):
        return state.gold >= (action.card.cost or 3)
    if isinstance(action, LevelUp):
        return state.gold >= action.cost
    if isinstance(action, RefreshShop):
        return state.gold >= action.cost
    return True  # SellBench / DeployMove 不花金


def _maybe_sell_for_interest(state: GameState, actions: list[Action], character_priority: list[str]) -> None:
    """凑整吃息:gold 在 10 倍数上方(且未到 50 上限)且有低价值 bench → 卖到临界下。"""
    if state.gold >= INTEREST_THRESHOLD:
        return  # 已满息,不卖
    remainder = state.gold % 10
    if remainder == 0 or not state.bench:
        return
    # 只在余金较少(卖一张 1 星回 1 金正好凑整)时考虑
    idx = _weakest_bench_idx(state, character_priority)
    if idx is None:
        return
    bc = state.bench[idx]
    if bc.char_id in character_priority:
        return
    if bc.star == 1 and state.gold + 1 - (state.gold % 10) >= 0:
        # 卖 1 星回 1 金可能凑整(粗估);避免过度卖出
        actions.append(SellBench(bench_idx=idx))


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
    """事件选项打分:白名单优先级 + 克制环境降权(走 DoT 时避 净化身心)。全 0 选第一个。"""
    whitelist: dict = getattr(config, 'event_whitelist', {}) or {}
    dot_punish = set(getattr(config, 'dot_punish_envs', []) or [])
    # 当前是否走 DoT/减益(看 board)
    on_dot = any(f in state.board for f in ("持续伤害", "减益"))

    best_idx, best_score = 0, -1.0
    for i, opt in enumerate(options):
        score = 0.0
        for name, val in whitelist.items():
            if name in opt:  # 子串匹配(容错繁简/前后缀)
                score = max(score, float(val))
        if opt in dot_punish and on_dot:
            score -= 200  # 走 DoT 时避克制环境
        if score > best_score:
            best_score, best_idx = score, i
    return PickEvent(option_idx=best_idx, reason=f"score={best_score:.0f}")
