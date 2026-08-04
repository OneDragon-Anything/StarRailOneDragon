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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.cw_factions import FACTIONS, INTEREST_THRESHOLD

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_comps import Comp
from sr_od.application.currency_war.cw_comps import (
    AFFIX_MECHANIC_MAP,
    COMP_LIBRARY,
    LevelGoal,
    clamp,
    form_progress,
    make_score_context,
    mechanics_fit,
    select_comp,
)
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

# —— eval 权重 ——
# 以下为 **V4.4 research meta 先验,冻结**(版本更新才改,不进用户调参面;review r5/r6 权重纪律)。
# 开发者阶段 6 手调的最敏感 3-5 维(均内部,非用户 GUI;用户配置走 README A 的 4 轴优先/禁止/build_around+handoff):hp_safe_threshold(由 difficulty 派生)/ obs schedule / MAX_REFRESH_PER_ROUND / α(t) r_open·r_close / fold 阈值。
CATEGORY_WEIGHT: dict[str, float] = {"combat": 10.0, "economy": 6.0, "support": 4.0, "independent": 2.0}
INTEREST_WEIGHT: float = 4.0          # 每档(10金)利息的分。2026-08-04 提权(2→4):bot 不攒金 → 升不起级
# (gold 0-15 < 升级 cost 36-48)→ 卡低 level → 弱 comp。原 2.0:息 delta(50vs0)=10 = 牌 synergy 10 → bot
# 无差别→买不攒。提 4.0:息 delta=20 > 牌 synergy 10 → bot 攒到 50(息引擎)+ 花超额买/升级 = 经济统一论。
LEVEL_WEIGHT: float = 6.0             # 每级(相对期望)的分。2026-08-04 提权(3→6):bot 不升等级
# (level benefit+3 < interest loss-6 → 不升)→ 卡 lv5-6 → 弱 comp → plane2 死。提权让升级战胜息损 → 升7-8
# → 高费 unit → comp value↑ → 攻坚 plane2。
CHAR_PRIORITY_BONUS: float = 8.0      # character_priority 角色分(每星)
FACTION_PRIORITY_BONUS: float = 1.0   # faction_priority rank 分
CLOSE_TO_NEXT_TIER_BONUS: float = 0.5  # 差 1 人推层的加成系数
SYNERGY_TIER_EXPONENT: float = 1.5     # 激活 tier 的超线性指数(收敛,task#16):深堆(高 tier)超线性奖励。
# 2026-08-04 实跑:bot 散阵(买每阵营 1 张)因 买新 tier-1 = 深化 tier1→2 同 delta(线性)→ 无偏好→散。
# 超线性(×1.5):深化 delta(2^1.5-1=1.83)> 散新(1^1.5=1)→ bot 偏好深化已有阵营 → 收敛(深堆>散)。
OFF_TARGET_DISCOUNT: float = 1.0       # 2026-08-04 revert(原 0.3):实跑发现 0.3 打折 board synergy 致 bot
# 卖成型 off-target 深堆(churn)= regression(vs 4-fix 无 commitment 清 plane1)。改 1.0(不打折)= 恢复
# 4-fix(super-linear synergy 单独)行为。commitment 正确实现 = prefilter(只 discount 新 off-target **buys**,
# 不动已有堆的 board eval)—— 待后续 task#16 续。target_comp 参数保留(prefilter 复用),effect 暂关。
CEILING_BONUS_FACTOR: float = 0.3      # 高 ceiling 阵营(count/max_tier)潜力项系数

# 默认升级金价(粗估,实机校准)
LEVEL_UP_COST_TABLE: dict[int, int] = {2: 4, 3: 10, 4: 18, 5: 30, 6: 36, 7: 48, 8: 60, 9: 70, 10: 84}
SHOP_REFRESH_COST: int = 2   # 刷新商店花费(粗估,实机校准)
REFRESH_SAMPLES: int = 8     # 蒙特卡洛 D 牌采样数(越大越准越慢)
MAX_REFRESH_PER_ROUND: int = 2   # 每回合最多主动刷新(D 牌)次数(防无限刷;review r5 修死代码)

# 通用升级曲线(task#18 经济统一论):COMP_LIBRARY 未填 level_plan 时用。
# auto-chess meta:前期(2-4)roll 找低费核心 → 中期(5-7)level_up 推等级(解锁高费刷新率 + 出战位)
# → lv8 roll 找 5 费核心 → lv9+ stable。comp 自带 level_plan(如列车同行)优先于此(见 _resolve_level_goal)。
_DEFAULT_LEVEL_GOAL: dict[int, LevelGoal] = {
    2: LevelGoal("roll", target_cost=2),
    3: LevelGoal("roll", target_cost=3),
    4: LevelGoal("roll", target_cost=3),
    5: LevelGoal("level_up"),
    6: LevelGoal("level_up"),
    7: LevelGoal("level_up"),
    8: LevelGoal("roll", target_cost=5),
    9: LevelGoal("stable"),
}


def _resolve_level_goal(state: GameState, target: Comp | None) -> LevelGoal | None:
    """当前等级该做什么(comp 自带 level_plan 优先;无则通用曲线 _DEFAULT_LEVEL_GOAL)。

    level_plan 是**花费指令**(经济统一论):说 ``level_up`` → plan() 硬 gate 升级;
    ``roll`` → D 找核心;``stable`` → 吃息。comp 未填 level_plan(多数 comp)时退回通用曲线,
    保证所有 comp 都有合理经济行为(不再依赖每 comp 手填曲线)。
    """
    if target is not None:
        g = target.level_plan.get(state.level)
        if g is not None:
            return g
    return _DEFAULT_LEVEL_GOAL.get(state.level)


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


def synergy_score(state: GameState, faction_priority: list[str],
                  target_comp: Comp | None = None) -> float:
    """羁绊质量分:激活 tier × 类别 + 接近推层 + 偏好 + 高 ceiling 潜力项。

    target_comp 给定时(commitment,task#16):off-target 阵营 synergy × OFF_TARGET_DISCOUNT,
    聚焦深化 target 阵营 → target comp 更高 tier 更强。target_comp=None(reactive/测试)→ 不打折。
    """
    target_factions: set[str] = set(target_comp.form_tiers.keys()) if target_comp is not None else set()
    score = 0.0
    for faction, count in state.board.items():
        if count <= 0:
            continue
        info = FACTIONS.get(faction)
        cat_w = CATEGORY_WEIGHT[info.category] if info and info.category in CATEGORY_WEIGHT else 3.0
        tier_score = cat_w * _activated_tiers(faction, count) ** SYNERGY_TIER_EXPONENT
        if _close_to_next(faction, count):
            tier_score += cat_w * CLOSE_TO_NEXT_TIER_BONUS
        mt = _max_tier(faction)
        if mt >= 6:
            tier_score += cat_w * (count / mt) * CEILING_BONUS_FACTOR
        # commitment:off-target 阵营打折(target 设定时),聚焦深化 target(用户 priority bonus 不打折)
        if target_factions and faction not in target_factions:
            tier_score *= OFF_TARGET_DISCOUNT
        score += tier_score
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
    level_val = (state.level - _expected_level(state.round_num, state.plane)) * LEVEL_WEIGHT
    if economy_mode == "interest_first":
        interest_val *= 1.5
    elif economy_mode == "rush_level":
        interest_val *= 0.5
        level_val *= 1.5   # rush_level:等级项加权(抢升语义 —— 落后等级更痛、领先更值),不只弱化守息
    return interest_val + level_val


def char_quality_score(state: GameState, character_priority: list[str]) -> float:
    """角色质量分:character_priority 角色 × 星级(bench + 已上阵 deployed)。"""
    score = 0.0
    for bc in (*state.bench, *state.deployed):
        if bc.char_id in character_priority:
            score += CHAR_PRIORITY_BONUS * bc.star
    return score


HP_DANGER: int = 40   # 保血触发阈值(hp 低于此 → 弃息保血;A8 高难可调高,待 difficulty 字段)


def _phase_weights(plane: int, hp: int) -> tuple[float, float, float]:
    """阶段键控权重 (synergy, economy, char)。A3 + review agent 经济学校准。

    **2026-08-03 修正(review agent + 用户)**:前期 economy **不该压低** —— 利息越早到 5 档(50 金)
    越好,经济滚雪球。原 "plane1 → economy 0.4" 把"前期"和"保血"混淆了。修正:
    - **HP 危险(hp<HP_DANGER):保血** —— 任何位面,弃息提质量(战力/角色加权、经济降权)。
    - **plane3(后期):锁血** —— 全力战力/星级(打 boss)。
    - **其余(健康):平衡 (1,1,1)** —— economy 不压低,可 snowball 到 50。

    待补:A8 difficulty 信号(高难 HP_DANGER 调高)+ win_streak(连胜中保连胜>吃息,需 read_streak)。
    """
    if hp < HP_DANGER:
        return (1.2, 0.4, 1.2)   # 保血:战力/角色优先,经济降权(任何位面 HP 危险)
    if plane == 3:
        return (1.3, 0.3, 1.3)   # 锁血:全力战力/星级(plane3 boss 战)
    return (1.0, 1.0, 1.0)       # 健康:平衡(economy 不压低,snowball 到 50)


def _refresh_cap(state: GameState) -> int:
    """本回合 D 牌(刷新)上限(动态;review agent + 用户:固定 2 太死)。

    关键回合放宽:升 8 后 / plane3 搜核心、HP 危险锁血急救。
    待补:拿刷新减费策略(砂里淘金/加油站)→ 6;需 GameState.active_strategies 字段(电表倒转)。
    """
    cap = MAX_REFRESH_PER_ROUND          # 基线 2
    if state.plane == 3 or state.level >= 8:
        cap = max(cap, 4)                # 升 8 后 / plane3:搜核心多刷
    if state.hp < HP_DANGER:
        cap = max(cap, 4)                # 锁血急救:多刷找质量
    return cap


def evaluate(state: GameState, config, faction_priority: list[str],
             target_comp: Comp | None = None) -> float:
    """局面总分(越高越好)= 阶段键控加权的(羁绊 + 经济 + 角色质量)+ target_progress(若有 target)。

    target_comp 给定时加 **战略层导向**:接近 target 成型(form_tiers)的局面加分
    (− TARGET_PROGRESS_WEIGHT × 剩余进度)。target_comp=None(reactive)→ 行为不变(A3)。
    **接法第一步**(03):evaluate 支持 target;plan 自动 select_comp 传 target 是下一步。
    core_chars 持有不在此重复计分(char_quality 已覆盖用户 character_priority)。
    """
    ws, we, wc = _phase_weights(state.plane, state.hp)
    score = (
        ws * synergy_score(state, faction_priority, target_comp)
        + we * economy_score(state, getattr(config, 'economy_mode', 'adaptive'))
        + wc * char_quality_score(state, getattr(config, 'character_priority', []))
    )
    if target_comp is not None:
        score -= TARGET_PROGRESS_WEIGHT * _target_progress_remaining(state, target_comp)
    return score


# target 成型剩余进度权重(战略层导向;占位,待实玩校准)。越大 → 越 commit 到 target。
TARGET_PROGRESS_WEIGHT: float = 15.0


def _target_progress_remaining(state: GameState, target_comp: Comp) -> float:
    """target comp 剩余成型进度 0..1(0=已成型 form_tiers,1=完全没起步)。

    只看阵营 form_tiers(core_chars 持有由 char_quality 覆盖,不重复计分,03 去三重)。
    """
    if not target_comp.form_tiers:
        return 0.0
    tot = sum(max(0, t - state.board.get(f, 0)) / t for f, t in target_comp.form_tiers.items())
    return tot / len(target_comp.form_tiers)


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


def _best_buy_deploy_eval(state: GameState, config, faction_priority: list[str],
                          target_comp: Comp | None = None) -> float:
    """给定 shop,取最优 buy+deploy 的 eval(用于蒙特卡洛 D 牌:新 shop 下能拿到的最高分)。

    target_comp: 战略层目标(A2),传给 evaluate 使 D 牌期望导向 target 成型。None=reactive。
    """
    character_priority = getattr(config, 'character_priority', [])
    best = evaluate(state, config, faction_priority, target_comp)
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
        ev = evaluate(after, config, faction_priority, target_comp)
        if card.name in character_priority:
            ev += CHAR_PRIORITY_BONUS * 2
        best = max(best, ev)
    return best


def _refresh_expected_delta(state: GameState, config, faction_priority: list[str],
                            base_eval: float, rng: random.Random, k: int = REFRESH_SAMPLES,
                            target_comp: Comp | None = None) -> float:
    """刷新商店的**期望 delta**(蒙特卡洛,A1):扣刷新金后,采样 k 个 shop,各取最优 buy+deploy
    eval,均值 − base_eval。这把"何时 D 牌"从无法建模变成可计算 —— D 牌当期望新 shop 收益 >
    刷新成本(economy 降)时发生。simulate 已扣 refresh cost,故期望含成本惩罚。

    target_comp: 战略层目标(A2),透传给 _best_buy_deploy_eval。None=reactive。
    """
    if state.gold < SHOP_REFRESH_COST:
        return -1e9
    after_cost = simulate(state, RefreshShop(SHOP_REFRESH_COST))  # 已扣 2 金
    deltas = []
    for _ in range(k):
        s = after_cost.copy()
        s.shop = _sample_shop(after_cost, faction_priority, rng)
        deltas.append(_best_buy_deploy_eval(s, config, faction_priority, target_comp) - base_eval)
    return sum(deltas) / len(deltas) if deltas else 0.0


def plan(state: GameState, config, faction_priority: list[str],
         rng: random.Random | None = None,
         target_comp: Comp | None = None) -> list[Action]:
    """一回合动作计划:硬门(必做)+ 贪心改进(买/deploy/升/卖/**D 牌蒙特卡洛**)。

    config: CurrencyWarConfig。rng: 蒙特卡洛 D 牌用(默认新建;测试传 seeded 保确定)。
    target_comp: 战略层目标阵容(稳定,由上层 shop op 跨回合管理 + maybe_pivot 切换)。
        传入 → 用它(不每轮重选,防 select_comp 振荡致 churn);None → 内部 select_comp
        (向后兼容 / 测试 / reactive 退化)。硬门:bench-full 必破、gold≥0、level≤10。
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

    # —— A2 战略层:target 由上层传入(稳定,防每轮 select_comp 振荡 → churn);未传则 select_comp ——
    # 2026-08-04 实跑:每轮 select_comp 随 board 微变翻转 target(列车同行↔DOT队)→ _maybe_sell_for_interest
    # 按振荡 target 卖牌 → 破坏性 churn(每轮换牌)+ 零收敛 → 比 reactive 更弱。故 target 须跨回合稳定
    # (上层 shop op 持久化 + maybe_pivot 才切),plan 只消费。详 task#16 + strategy/02 F-3。
    target = target_comp
    if target is None:
        _candidates = select_comp(cur, make_score_context(cur), config)
        if _candidates:
            target = _candidates[0]

    # —— level_plan 硬 gate(task#18 经济统一论核心):level_plan 说 level_up + 够钱 → 升级(1 级/轮)——
    # 根因(replay 32 局「升 0 次」):贪心 eval 对「花大金升级」的利息损失短视 —— LevelUp 候选 delta 永负
    # (花 48 金 → 利息档 5→0 损 -20,level_val 仅 +6)→ 永不选中 → bot 卡 lv5-6 → 弱 comp → plane2 死。
    # level_plan 是**花费指令**非建议:说 level_up + afford → 执行,信任计划而非短视 eval。tempo 破息在所
    # 不惜(升级解锁高费刷新率 + 出战位 = 关键长期投资)。每轮最多 1 级(自然节流,防一轮烧光金)。
    _goal = _resolve_level_goal(cur, target)
    if _goal is not None and _goal.action == "level_up" and cur.level < 10:
        _lv_cost = LEVEL_UP_COST_TABLE.get(cur.level + 1, 70)
        if cur.gold >= _lv_cost:
            actions.append(LevelUp(cost=_lv_cost))
            cur = simulate(cur, actions[-1])

    # —— 贪心:反复选 eval 提升最大的动作序列(含 D 牌蒙特卡洛),直到无正提升 ——
    base_eval = evaluate(cur, config, faction_priority, target)
    for _ in range(15):
        refresh_used = sum(1 for a in actions if isinstance(a, RefreshShop))
        step = _best_improving_action(cur, config, faction_priority, base_eval, rng,
                                      refresh_budget=_refresh_cap(cur) - refresh_used,
                                      target_comp=target)
        if not step:
            break
        actions.extend(step)
        for a in step:
            cur = simulate(cur, a)
        base_eval = evaluate(cur, config, faction_priority, target)

    # —— 凑整吃息:卖出能跨 10 倍数(+1 档息)的非关键 bench 牌(循环)——
    _maybe_sell_for_interest(cur, actions, character_priority, config)
    return actions


def _best_improving_action(
    state: GameState, config, faction_priority: list[str], base_eval: float,
    rng: random.Random, refresh_budget: int = 0, target_comp: Comp | None = None,
) -> list[Action]:
    """返回 eval 提升最大且为正的动作序列;无则 []。

    候选:买+deploy 原子组合、deploy 已有角色、**D 牌(蒙特卡洛期望)**。升等级不由这里候选 ——
    plan() 硬 gate 按 level_plan 执行(task#18;根因:eval 对花大金升级短视)。gold≥0/level≤10。
    refresh_budget: 本回合剩余可刷新次数(≤0 则不再生成 RefreshShop;防无限刷,review r5)。
    target_comp: 战略层目标阵容(A2);传给 evaluate,使动作导向 target 成型。None=reactive。
    """
    character_priority = getattr(config, 'character_priority', [])
    best: list[Action] = []
    best_delta = 0.0

    def beat(delta: float, seq: list[Action]) -> None:
        nonlocal best, best_delta
        if delta > best_delta + 1e-6:
            best, best_delta = seq, delta

    # 花费指令(level_plan / 通用曲线):驱动下面 buying gate + refresh gate(task#18)。
    _goal = _resolve_level_goal(state, target_comp)
    _lv_cost = LEVEL_UP_COST_TABLE.get(state.level + 1, 70)         # 升下一级金价
    _saving_for_level = (_goal is not None and _goal.action == "level_up"
                         and state.gold < _lv_cost)                  # 攒金升级中 → 抑制散牌买/刷

    # 1) 买 + 上任组合(原子)
    for card in state.shop:
        cost = card_cost(card)
        if state.gold < cost:
            continue
        # level_plan buying gate(task#18):攒金升级期间(_saving_for_level)抑制散牌,但仍允许 target
        # 阵营/core/优先角色牌(深化 target 值得花,且不该被攒金阻塞)。升级本身由 plan() 硬 gate 执行,
        # 这里只管"攒金期间别把金泄到散牌上"(解 replay 32 局金堆 50+ 不花/花在散牌上不升级)。
        if _saving_for_level:
            _is_target_card = (target_comp is not None and (
                card.faction in target_comp.factions
                or card.name in target_comp.core_chars
                or card.name in character_priority))
            if not _is_target_card:
                continue   # 散牌:攒金给升级,跳过
        # commitment prefilter(task#16):target 设定时,若 shop 有 target 卡(阵营∈target.factions 或
        # ∈core_chars)可买,跳过纯 off-target 散牌(阵营∉target 且非 core_char/优先角色)→ 聚焦深化 target,
        # 防"买一切"致 board 散、comp 永不深堆(plane2 comp-strength 墙根因)。shop 无 target 卡时不跳(防
        # hold-forever 饿死)。区别旧 OFF_TARGET_DISCOUNT 打折 board 的 churn(d87b2a68 revert):只 gate 新 buys。
        if target_comp is not None:
            _is_offtarget = (card.faction not in target_comp.factions
                             and card.name not in target_comp.core_chars
                             and card.name not in character_priority)
            if _is_offtarget and any(
                    c.faction in target_comp.factions or c.name in target_comp.core_chars
                    for c in state.shop if state.gold >= card_cost(c)):
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
        delta = evaluate(after, config, faction_priority, target_comp) - base_eval
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
        beat(evaluate(simulate(state, mv), config, faction_priority, target_comp) - base_eval, [mv])

    # 3) D 牌/刷新商店(蒙特卡洛期望 delta;A1):受 refresh_budget 上限约束(防无限刷,review r5)。
    # 升等级不由这里候选 —— plan() 硬 gate 按 level_plan 执行(task#18;根因:eval 对「花大金升级」
    # 的利息损失短视 → LevelUp 候选 delta 永负 → 永不选 → 32 局升 0 次)。buying gate 同源:攒金升级期间
    # (_saving_for_level)不 D 牌(refresh 泄金,与散牌买同理)。
    if state.gold >= SHOP_REFRESH_COST and refresh_budget > 0 and not _saving_for_level:
        beat(_refresh_expected_delta(state, config, faction_priority, base_eval, rng,
                                     target_comp=target_comp),
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


# ===== 遭遇节点(decide_encounter,design 08;纯逻辑骨架,handler 接线待阶段5 OCR)=====

@dataclass
class EncounterOption:
    """一个遭遇分支:难度档 + 敌人词缀 + 奖励(OCR 读,``read_encounter_options`` 阶段5)。

    difficulty:难度档 1=易/2=中/3=难(越高奖励越好但敌人越凶)。
    affixes:敌人词缀 OCR 原名(经 ``AFFIX_MECHANIC_MAP`` → 机制 tag,再 ``mechanics_fit`` 判 comp 克/利)。
    rewards:奖励(钻/装备/金币;带钻最优,详 design 08 / cw_comps MECHANIC 表)。
    """
    idx: int
    difficulty: int = 1
    affixes: list[str] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)


@dataclass
class EncounterPick:
    """decide_encounter 返回:选哪个分支 + 是否刷新避开。"""
    idx: int
    refresh: bool = False
    reason: str = ""


def _option_mechanics(option: EncounterOption, target_comp: Comp | None) -> float:
    """该分支词缀对 target_comp 的契合(``mechanics_fit`` 0..1;<0.4 克、>0.5 利 debuff=buff)。

    无 target_comp → 中性 0.5(纯按难度选)。
    """
    if target_comp is None:
        return 0.5
    mechs = {AFFIX_MECHANIC_MAP.get(a, a) for a in option.affixes}
    return mechanics_fit(target_comp, mechs)


def decide_encounter(options: list[EncounterOption], state: GameState,
                     target_comp: Comp | None, config, refresh_used: bool = False) -> EncounterPick:
    """遭遇节点选难度档 + 是否刷新(纯逻辑,design 08;handler 待阶段5 ``read_encounter_options`` 接)。

    决策(观测驱动 + comp 相关,debuff=buff):
    1. **未成型**(deployed 不足 / target 成型度低)→ 偏低难度(生存优先)。
    2. **词缀按 comp 判**(``mechanics_fit``):全分支都克 comp + 刷新未用 → **刷新换批**避开;
       存在不克的分支 → 选最利 comp 的。
    3. **成型 + 词缀利 comp**(debuff=buff)→ 挑高难度拿奖励(奖励权重随成型度)。
    4. 刷新已用 → 不再刷,按 1-3 选最优分支。

    config 预留(未来对策装备映射 / 偏好;当前未用)。
    """
    if not options:
        return EncounterPick(idx=0, reason="no-options")
    mechs = [_option_mechanics(o, target_comp) for o in options]
    form = form_progress(target_comp, state) if target_comp is not None else 0.5
    formed = form >= 0.4 and state.deployed_count() >= max(2, state.max_units() // 2)

    # 全分支词缀都克 comp(mechanics_fit < 0.4)+ 刷新未用 → 刷新换批(避开高危)
    if not refresh_used and target_comp is not None and all(m < 0.4 for m in mechs):
        return EncounterPick(idx=options[0].idx, refresh=True,
                             reason=f"全分支词缀克 comp(mech_max={max(mechs):.2f}),刷新换批")

    # 评分:词缀契合(利 comp 加分)+ 成型→高难度值(奖励)/ 未成型→低难度安全
    def _score(o: EncounterOption, m: float) -> float:
        s = m
        diff_norm = (o.difficulty - 1) / 2.0   # 0..1(难度 1→0、3→1)
        s += (0.3 * diff_norm) if formed else (-0.3 * diff_norm)
        return s

    scored = sorted(zip(options, mechs, strict=True), key=lambda om: _score(om[0], om[1]), reverse=True)
    best_o, best_m = scored[0]
    return EncounterPick(idx=best_o.idx, refresh=False,
                         reason=f"mech={best_m:.2f} formed={formed} diff={best_o.difficulty}")


# ===== 补给节点(decide_supply,design 07/08;纯逻辑骨架,handler 接线待阶段5 OCR)=====

# 通用装备价值(V4.4 meta 先验;**值在代码单一源,不进 strategy doc**;实玩校准)。
# 设计原则:带钻 > 鞋(找鞋战争;速度 comp 命脉)> 电池 > 花/通用。具体值随版本。
_EQUIP_VALUE: dict[str, int] = {
    "反重力皮靴": 5, "轮滑鞋": 4,
    "永动机": 4, "光能电池": 3, "超级电池": 3,
    "物质分解液": 3, "能量饮料": 2, "绝对热量": 2,
}


@dataclass
class SupplyOption:
    """一个补给选项:角色 + 装备 + 是否带钻(OCR/视觉读,``read_supply_options`` 阶段5)。

    has_diamond:带红/蓝钻(视觉判定;钻 = 拿到基本赢,碾压一切)。
    equip:装备名(OCR;``key_equips`` 契合 + 通用价值排序用)。
    """
    idx: int
    char: str = ""
    equip: str = ""
    has_diamond: bool = False


@dataclass
class SupplyPick:
    """decide_supply 返回:选哪个 + 是否刷新找钻。"""
    idx: int
    refresh: bool = False
    reason: str = ""


def _equip_value(equip: str) -> int:
    """装备通用价值(0=未知/无;V4.4 先验,见 ``_EQUIP_VALUE``)。"""
    return _EQUIP_VALUE.get(equip, 0)


def decide_supply(options: list[SupplyOption], state: GameState,
                  target_comp: Comp | None, config, refresh_used: bool = False) -> SupplyPick:
    """补给节点选装备 + 是否刷新(纯逻辑,design 07/08;handler 待阶段5 ``read_supply_options`` 接)。

    决策(comp 相关 + 钻优先):
    1. **带钻**(红/蓝)→ 选它(拿到基本赢,碾压)。
    2. **全无钻 + 刷新未用** → **刷新找钻**(钻价值远超装备)。
    3. **刷新已用 / 有钻** → 按 ``target_comp.key_equips`` 契合(命脉级,+10 碾压)+ 通用装备价值
       (鞋>电池>花)选。
    """
    if not options:
        return SupplyPick(idx=0, reason="no-options")
    # 1) 带钻 → 选第一个带钻的(基本赢)
    diamond = [o for o in options if o.has_diamond]
    if diamond:
        return SupplyPick(idx=diamond[0].idx, reason="带钻(基本赢)")
    # 2) 全无钻 + 刷新未用 → 刷新找钻
    if not refresh_used:
        return SupplyPick(idx=options[0].idx, refresh=True, reason="无钻,刷新找钻")
    # 3) 刷新已用 → key_equips 契合(命脉,+10)+ 通用装备价值
    key_equips = set(target_comp.key_equips) if target_comp is not None else set()

    def _score(o: SupplyOption) -> int:
        s = _equip_value(o.equip)
        if o.equip in key_equips:
            s += 10   # 契合 target_comp 命脉装备(碾压通用价值)
        return s

    scored = sorted(options, key=_score, reverse=True)
    best = scored[0]
    return SupplyPick(idx=best.idx, reason=f"equip={best.equip or '?'} key_fit={best.equip in key_equips}")


# ===== optionality_score + α(t) 承诺-期权(design 02/03 P1-1 + F-3;纯逻辑,evaluate 集成待 P0 验证)=====
# A8 是方差生存战:过早 commit 单一高 ceiling comp,遇克/缺关键牌即死。optionality 奖励 bench 角色
# 同时属 ≥2 可行 comp(保期权/容错);α(t) 早灵活(保期权)→ 晚承诺(深化 target)。
# ⚠️ **evaluate 集成延后**:改核心 eval 行为需游戏(P0)验证才稳;先纯函数 + 测试(零件)。

# α(t) 总回合阈值(R_OPEN 前 α=0 纯期权 / R_CLOSE 后 α=1 纯承诺);**值在代码**(阶段6实玩校准)。
R_OPEN: int = 2
R_CLOSE: int = 12
OPTIONALITY_WEIGHT: float = 8.0      # optionality 项权重(eval 集成时用;V4.4 先验,代码,实玩校准)
OPTIONALITY_PER_CHAR: float = 1.0    # 每个属 ≥2 comp 的 bench 角色加分


def _elapsed_rounds(state: GameState) -> int:
    """总回合数(``round_num + (plane-1)*6``;3 位面 × 6 关 = 18)。α(t) 用。"""
    return state.round_num + (state.plane - 1) * 6


def alpha_t(state: GameState) -> float:
    """承诺-期权时间衰减 α(t)(design F-3):总回合 < R_OPEN → 0(纯期权/灵活)、
    > R_CLOSE → 1(纯承诺/commit),之间线性。eval 集成时:``α·target_progress + (1-α)·optionality``。
    """
    if R_CLOSE <= R_OPEN:
        return 1.0
    return clamp((_elapsed_rounds(state) - R_OPEN) / (R_CLOSE - R_OPEN), 0.0, 1.0)


def optionality_score(state: GameState) -> float:
    """灵活性分:bench 角色属 **≥2 个 COMP_LIBRARY comp**(``shared_chars ∪ core_chars``)→ 加分(保期权)。

    设计 P1-1:保 ≥2 comp 可行的 bench 角色 → 遇克/缺牌可转型,容错;过早卖 shared_chars 扣分(未实现,
    集成时在 _bench_sell_value 加)。**未含 transition_chars**(需 comp 上下文,集成时补)。
    """
    if not state.bench:
        return 0.0
    # 预算每个角色属几个 comp(shared + core 合并)
    char_comps: dict[str, int] = {}
    for comp in COMP_LIBRARY:
        for c in set(comp.shared_chars) | set(comp.core_chars):
            char_comps[c] = char_comps.get(c, 0) + 1
    score = 0.0
    for bc in state.bench:
        if bc.char_id and char_comps.get(bc.char_id, 0) >= 2:
            score += OPTIONALITY_PER_CHAR
    return score
