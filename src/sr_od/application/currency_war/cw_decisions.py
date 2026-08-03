"""货币战争 策略决策(评估函数 + 贪心改进;纯逻辑,可测,不碰游戏)。

架构(strategy_design.md / strategy_research.md):
- ``evaluate(state)`` 给局面打分 = 羁绊激活质量(+高 ceiling 阵营潜力)+ 经济健康度 + 角色质量(bench+deployed)。
- ``plan(state)`` 在**硬规则门**(bench-full 必破、gold≥0、level≤10)内,**贪心选 eval 提升
  最大的动作序列**(买+deploy 原子组合/deploy/升/卖/刷新)。

review r1 修正(2026-08-03):board 模型加 deployed 身份/站位 → char_quality 计已上阵;
synergy 加 ceiling 潜力项(避免线性小 tier 阵营虚高);凑整吃息改跨档判定;牌池操纵
暂禁用(无牌池建模=零收益);economy_mode 只调利息项;level 封顶;bench_full 用固定9/OCR;
sell 保留接近推层牌;RefreshShop 候选;event dot 匹配修正。

自适应核心:**贪心加深当前领先 + 高 ceiling 阵营**,config 做方向,boss 克制覆盖切换。
meta 层(阵营/角色/事件)版本依赖,以米游社百科/游戏图鉴为准、实机 OCR 为真值。
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
# 第一位面/低血时经济权重的衰减(保血优先)
EARLY_WEAK_ECON_FACTOR: float = 0.5

# 默认升级金价(粗估,实机校准)
LEVEL_UP_COST_TABLE: dict[int, int] = {2: 4, 3: 10, 4: 18, 5: 30, 6: 36, 7: 48, 8: 60, 9: 70, 10: 84}
SHOP_REFRESH_COST: int = 2  # 刷新商店花费(粗估,实机校准)


def _activated_tiers(faction: str, count: int) -> int:
    """该阵营在 count 人下激活了几个 tier。无信息返回 0。"""
    info = FACTIONS.get(faction)
    if info is None or count <= 0:
        return 0
    return sum(1 for t in info.tiers if t <= count)


def _max_tier(faction: str) -> int:
    """该阵营最高激活 tier(几人);无信息返回 1。"""
    info = FACTIONS.get(faction)
    return max(info.tiers) if info and info.tiers else 1


def _close_to_next(faction: str, count: int) -> bool:
    """再 +1 人是否推到下一激活层。"""
    info = FACTIONS.get(faction)
    if info is None:
        return False
    nxt = next((t for t in info.tiers if t > count), None)
    return nxt is not None and count + 1 >= nxt


def _close_factions(state: GameState) -> set[str]:
    """当前 board 里"差 1 人推下一层"的阵营集合(卖牌时要保留这些拼图)。"""
    return {f for f, c in state.board.items() if _close_to_next(f, c)}


def synergy_score(state: GameState, faction_priority: list[str]) -> float:
    """羁绊质量分:激活 tier × 类别权重 + 接近推层 + 偏好 + **高 ceiling 潜力项**。

    ceiling 潜力项:对 max_tier≥6 的高 ceiling 阵营(仙舟10/击破10/盛会之星6/星间旅人7),
    按 count/max_tier 给进度分,奖励中段投入(避免被线性小 tier 阵营淹没)。
    """
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
        # 高 ceiling 潜力项(避免只看 tier 个数,低估仙舟/击破这类后期起飞阵营)
        mt = _max_tier(faction)
        if mt >= 6:
            score += cat_w * (count / mt) * CEILING_BONUS_FACTOR
        if faction in faction_priority:
            rank = faction_priority.index(faction)
            score += (len(faction_priority) - rank) * FACTION_PRIORITY_BONUS
    return score


def _expected_level(round_num: int, plane: int) -> int:
    """该阶段期望等级(研究节拍:前期 4-5、中期 6-7、后期 8-9)。"""
    if plane == 1:
        return min(4 + round_num // 2, 6)
    if plane == 2:
        return min(6 + (round_num - 1) // 2, 8)
    return min(8 + (round_num - 1) // 3, 10)


def economy_score(state: GameState, economy_mode: str) -> float:
    """经济健康度:利息(存金到 50)+ 等级合适度。

    保血:第一位面 / 低血时,**利息囤积**价值衰减(优先把金花在战力上);
    economy_mode **只调利息项**(rush_level 弱化守息、interest_first 强化守息),等级项不变。
    """
    interest_tiers = min(state.gold // 10, INTEREST_THRESHOLD // 10)  # 最多 5 档
    interest_val = interest_tiers * INTEREST_WEIGHT
    if state.plane == 1 or state.hp < 40:
        interest_val *= EARLY_WEAK_ECON_FACTOR
    if economy_mode == "interest_first":
        interest_val *= 1.5
    elif economy_mode == "rush_level":
        interest_val *= 0.5
    expected = _expected_level(state.round_num, state.plane)
    level_val = (state.level - expected) * LEVEL_WEIGHT
    return interest_val + level_val


def char_quality_score(state: GameState, character_priority: list[str]) -> float:
    """角色质量分:character_priority 角色 × 星级(bench + **已上阵 deployed**)。

    review r1:已上阵优先角色也计分(避免 deploy 后失忆、贪心拒绝上阵核心)。
    """
    score = 0.0
    for bc in (*state.bench, *state.deployed):
        if bc.char_id in character_priority:
            score += CHAR_PRIORITY_BONUS * bc.star
    return score


def evaluate(state: GameState, config, faction_priority: list[str]) -> float:
    """局面总分(越高越好)。config 为 CurrencyWarConfig(getattr 取字段)。"""
    return (
        synergy_score(state, faction_priority)
        + economy_score(state, getattr(config, 'economy_mode', 'adaptive'))
        + char_quality_score(state, getattr(config, 'character_priority', []))
    )


def _bench_sell_value(bc: BenchChar, character_priority: list[str], close_factions: set[str]) -> float:
    """角色"留下价值"(越低越该卖):星级 + 优先角色 + **接近推层阵营**保留。"""
    val = float(bc.star)
    if bc.char_id in character_priority:
        val += 100  # 优先角色不卖
    if bc.faction in close_factions:
        val += 50   # 即将推层的拼图保留(review r1 #36/#44)
    return val


def _weakest_bench_idx(state: GameState, character_priority: list[str]) -> int | None:
    """返回最该卖的 bench 索引(价值最低,且优先卖非接近推层);空返回 None。"""
    if not state.bench:
        return None
    close = _close_factions(state)
    return min(range(len(state.bench)),
               key=lambda i: _bench_sell_value(state.bench[i], character_priority, close))


def plan(state: GameState, config, faction_priority: list[str]) -> list[Action]:
    """一回合动作计划:硬门(必做)+ 贪心改进(买/deploy/升/卖/刷新)。

    config: CurrencyWarConfig。返回按执行顺序的 Action 列表(op 层执行)。
    硬门:bench-full 必破、gold≥0、level≤10。
    """
    character_priority = getattr(config, 'character_priority', [])
    actions: list[Action] = []
    cur = state.copy()

    # —— 硬门:bench-full 阻塞出战 → 必破(优先升等级,无金则卖最弱)——
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

    # —— 贪心:反复选 eval 提升最大的动作序列,直到无正提升或预算尽 ——
    base_eval = evaluate(cur, config, faction_priority)
    for _ in range(15):  # 上限防死循环
        step = _best_improving_action(cur, config, faction_priority, base_eval)
        if not step:
            break
        actions.extend(step)
        for a in step:
            cur = simulate(cur, a)
        base_eval = evaluate(cur, config, faction_priority)

    # —— 凑整吃息:卖出能跨 10 倍数(+1 档息)的非关键 bench 牌(循环)——
    _maybe_sell_for_interest(cur, actions, character_priority, config)

    # 注:牌池操纵(满息买废牌改池)暂禁用 —— 当前无牌池建模,零收益且烧息
    # (review r1 #19);待 simulate 建模牌池刷新概率后再启用(aggression=greedy + 守息)。

    return actions


def _best_improving_action(
    state: GameState, config, faction_priority: list[str], base_eval: float,
) -> list[Action]:
    """返回 eval 提升最大且为正的动作**序列**(买+deploy 原子组合 / 单动作);无则 []。

    候选:买+deploy 组合(原子,避免 deploy 被下一轮抢)、deploy 已有 bench 角色、升等级、
    卖(凑整)、刷新(shop 死牌时)。gold≥0、level≤10 硬约束。
    """
    character_priority = getattr(config, 'character_priority', [])
    best: list[Action] = []
    best_delta = 0.0

    def beat(delta: float, seq: list[Action]) -> None:
        nonlocal best, best_delta
        if delta > best_delta + 1e-6:
            best, best_delta = seq, delta

    # 1) 买 + 上任组合(原子):买后立即 deploy 到对应排,组合 delta
    for card in state.shop:
        cost = card_cost(card)
        if state.gold < cost:
            continue
        after_buy = simulate(state, BuyCard(card=card))
        # 买的牌落 bench 末尾,看能否 deploy
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
        # character_priority 万用核心:出现就抓(强加成,哪怕阵营不推层)
        if card.name and card.name in character_priority:
            delta += CHAR_PRIORITY_BONUS * 2
        beat(delta, seq)

    # 2) 上任已拥有的 bench 角色(免费 deploy;按 position_pref 分流)
    for i, bc in enumerate(state.bench):
        if state.deployed_count() >= state.max_units():
            break
        row, ok = _pick_deploy_row(state, bc)
        if not ok:
            continue
        mv = DeployMove(bench_idx=i, to_row=row, faction=bc.faction)
        if state.gold >= 0:  # deploy 不花金
            delta = evaluate(simulate(state, mv), config, faction_priority) - base_eval
            beat(delta, [mv])

    # 3) 升等级(解锁上阵位;封顶 10)
    if state.level < 10:
        cost = LEVEL_UP_COST_TABLE.get(state.level + 1, 70)
        if state.gold >= cost:
            delta = evaluate(simulate(state, LevelUp(cost=cost)), config, faction_priority) - base_eval
            beat(delta, [LevelUp(cost=cost)])

    # 4) 刷新商店(shop 死牌 + 关键 D 牌期 + 有金):给小额期望 delta
    if state.gold >= SHOP_REFRESH_COST and _shop_is_dead(state, config, faction_priority, base_eval):
        beat(0.5, [RefreshShop(cost=SHOP_REFRESH_COST)])  # 小正 delta:新 shop 可能更好

    return best


def _shop_is_dead(state: GameState, config, faction_priority: list[str], base_eval: float) -> bool:
    """shop 是否"死牌":没有任何买+deploy 能产生正 delta(含 character_priority)。"""
    character_priority = getattr(config, 'character_priority', [])
    for card in state.shop:
        if state.gold < card_cost(card):
            continue
        after = simulate(state, BuyCard(card=card))
        if after.deployed_count() < after.max_units() and after.bench:
            bc = after.bench[-1]
            row, ok = _pick_deploy_row(after, bc)
            if ok:
                after = simulate(after, DeployMove(bench_idx=len(after.bench) - 1, to_row=row, faction=bc.faction))
        delta = evaluate(after, config, faction_priority) - base_eval
        if card.name in character_priority:
            delta += CHAR_PRIORITY_BONUS * 2
        if delta > 0.5:
            return False
    return True


def _pick_deploy_row(state: GameState, bc: BenchChar) -> tuple[str, bool]:
    """按角色 position_pref 选排(偏好排优先,满则另一排);无空位返回 (row, False)。"""
    if state.deployed_count() >= state.max_units():
        return ("front", False)
    pref = bc.position_pref or "back"
    if pref == "front" and state.front_count() < state.front_max:
        return ("front", True)
    if state.back_count() < state.back_max:
        return ("back", True)  # back 偏好 或 front 满溢出到 back
    if state.front_count() < state.front_max:
        return ("front", True)  # back 满溢出到 front
    return ("front", False)


def _maybe_sell_for_interest(state: GameState, actions: list[Action],
                             character_priority: list[str], config) -> None:
    """凑整吃息:卖出能**跨一个 10 倍数**(+1 档息)的非关键 bench 牌(循环,最多 3 张)。

    review r1:旧条件恒真(白卖);改为只在 (gold+refund)//10 > gold//10(真跨档)时卖,
    且不超 50(满息内)。2/3 星(回 3/5 金)也可凑整。
    """
    if state.gold >= INTEREST_THRESHOLD or not state.bench:
        return
    economy_mode = getattr(config, 'economy_mode', 'adaptive')
    if economy_mode == 'rush_level':
        return  # 抢升等级模式不做凑整卖
    cur = state
    for _ in range(3):
        close = _close_factions(cur)
        best_idx = None
        for i, bc in enumerate(cur.bench):
            if bc.char_id in character_priority or bc.faction in close:
                continue
            refund = sell_refund(bc.star)
            # 卖后真能跨一个 10 倍数(多吃一档息)且不超 50
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
    """事件选项打分:白名单优先级(子串)+ 克制环境降权(走 DoT 主派时避)。

    review r1:DoT 判定改"主流派"(count≥2);dot_punish 改子串匹配(与白名单一致);
    惩罚量动态 = max(白名单分)+100(永远压过白名单)。全 0 选第一个。
    """
    whitelist: dict = getattr(config, 'event_whitelist', {}) or {}
    dot_punish = list(getattr(config, 'dot_punish_envs', []) or [])
    # 走 DoT/减益"主流派":count >= 2(而非仅 1 个顺带角色)
    on_dot = sum(state.board.get(f, 0) for f in ('持续伤害', '减益')) >= 2
    penalty = (max(whitelist.values()) + 100) if whitelist else 100

    best_idx, best_score = 0, -1.0
    for i, opt in enumerate(options):
        score = 0.0
        for name, val in whitelist.items():
            if name in opt:  # 子串匹配(容错繁简/前后缀)
                score = max(score, float(val))
        if on_dot and any(p in opt for p in dot_punish):  # 子串匹配(与白名单一致)
            score -= penalty
        if score > best_score:
            best_score, best_idx = score, i
    return PickEvent(option_idx=best_idx, reason=f"score={best_score:.0f}")
