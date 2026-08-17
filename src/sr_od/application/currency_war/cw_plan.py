# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)
"""货币战争 备战动作规划:plan 硬门贪心(bench-full/gold≥0/level≤10)+ 蒙特卡洛 D 牌(A1)+ 部署/卖牌/腾席链。

自 cw_decisions.py 一次性拆分而来(ADR-0145;纯移动零行为变化,函数名/签名不变)。
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_comps import (
    COMMIT_FRAC,
    EARLY_CORE_POOL,
    TEMPO_POOL,
    form_progress,
    make_score_context,
    select_comp,
    skeleton_factions,
    target_committed,
)
from sr_od.application.currency_war.cw_economy import (
    SHOP_REFRESH_COST,
    _refresh_cost,
    _want_level_up,
    _xp_gold_floor,
    clicks_to_next_level,
    get_node_goal,
    roll_affordable,
    xp_click_cost,
)
from sr_od.application.currency_war.cw_evaluate import (
    _card_hits_target,
    _close_factions,
    _refresh_cap,
    _should_save_for_interest,
    evaluate,
)
from sr_od.application.currency_war.cw_factions import (
    FACTIONS,
    INTEREST_THRESHOLD,
)
from sr_od.application.currency_war.cw_shop_odds import (
    REFRESH_PROB,
)
from sr_od.application.currency_war.cw_state import (
    BENCH_CAPACITY,
    Action,
    BenchChar,
    BuyCard,
    DeployMove,
    GameState,
    LevelUp,
    RefreshShop,
    SellBench,
    ShopCard,
    _bench_char_cost,
    card_cost,
    effective_hp_threshold,
    sell_refund,
    simulate,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_comps import Comp

REFRESH_SAMPLES: int = 8     # 蒙特卡洛 D 牌采样数(越大越准越慢)

# (ADR-0131 已删 REFRESH_DISCOUNT_STRATEGIES 名单 —— 旧名单语义全错(高效决策=45秒免费刷爆发,
# 采购专员=变同费5张卡非返现,加油站=每节点1次免费刷新+8金);刷新放宽改由 EconomyEffect 效果驱动,
# 见 _refresh_cap + _refresh_cost。)

# 人玩 auto-chess:跟 shop 走、concentrate(强化已 collect 阵营)、comp emerge。bot 旧「pre-select target→force」
# 在 deployed-lock + shop 随机下失败(target-buy 错配 → spread → 锁板 → 永不成型)。
REINFORCE_BONUS: float = 4.0      # 买 card.faction 已在 bench+deployed → 加分(深化集中阵营,~1 synergy 激活档)

SPREAD_PENALTY: float = 8.0       # 买新阵营 且 已 ≥DEPLOY_FACTION_CAP 阵营 → 重罚(防 spread-lock 永久占槽;>单卡 synergy 收益)

DEPLOY_FACTION_CAP: int = 3       # board 阵营数上限(L2 deploy cap 共用;deployed-lock 下超 = 永久 spread)



def _bench_sell_value(bc: BenchChar, character_priority: list[str], close_factions: set[str],
                     target_comp: Comp | None = None) -> float:
    """角色"留下价值"(越低越该卖):星级 + 优先角色 + 接近推层阵营 + target 核心保护。

    review 🔴:加 target_comp —— target 核心卡(core_chars / 全羁绊命中)高额保护分,
    防 plan 卖掉 target 核心凑息(承诺须贯穿卖路径,非只买/部署;否则一边承诺一边卖 target)。
    """
    val = float(bc.star)
    if bc.char_id in character_priority:
        val += 100
    if bc.faction in close_factions:
        val += 50
    if target_comp is not None and _card_hits_target(bc.char_id, bc.faction, target_comp):
        val += 100   # target 核心保护(同 priority 量级);commit 后绝不卖 target 凑息
    return val



def _weakest_bench_idx(state: GameState, character_priority: list[str],
                       target_comp: Comp | None = None) -> int | None:
    """最弱可卖 bench 下标(腾席链 c 步 / plan 硬门共用;doc 15 §5.2c)。

    **3合1 重复件保护**(doc 15 §4.1 待加项,2026-08-14 P1 落地):bench 内同名 ≥2 张 =
    3合1 进行中(再买 1 张即自动升星,价值远超残值)→ 保护不卖;全被保护 → 返回 None
    (无可卖,调用方走 DeferSpheres/留置)。
    """
    if not state.bench:
        return None
    from collections import Counter
    # 按 (char_id, star) 计数(review L-5):3合1 只合并同名同星,同名不同星不构成进度 → 不保护
    _counts = Counter((bc.char_id, bc.star) for bc in state.bench if bc.char_id)
    _protected = {i for i, bc in enumerate(state.bench)
                  if bc.char_id and _counts[(bc.char_id, bc.star)] >= 2}
    _candidates = [i for i in range(len(state.bench)) if i not in _protected]
    if not _candidates:
        return None   # 全是 3合1 进行件:无可卖(调用方 DeferSpheres/留置)
    close = _close_factions(state)
    return min(_candidates,
               key=lambda i: _bench_sell_value(state.bench[i], character_priority, close, target_comp))




def _distinct_factions(state: GameState) -> set[str]:
    """已 collect 的阵营集合 = board(deployed ground truth)+ bench(不含 '?'/空)。"""
    factions = set(state.board.keys())
    factions.update(bc.faction for bc in state.bench if bc.faction and bc.faction != '?')
    return factions
def _concentration_delta(card: ShopCard, state: GameState,
                         target_comp: Comp | None = None) -> float:
    """买这张牌对 concentration 的影响(加到 buy delta,L1)。

    - card.faction 已在 bench+deployed → +REINFORCE_BONUS(深化集中阵营,人玩「强化已 collect」)。
    - **target 阵营卡**(faction∈target.factions 或 name∈core_chars)→ 永不 spread 罚(,2026-08-08
      实跑 round3:DOT 队 target 卡 减益/椒丘 因 board 已 4 阵营≥cap 被旧逻辑 -8 罚 → target 卡 buy delta
      负 → 不买 → comp 永不深成型 → buy0)。target 阵营是想要的,新 target 阵营**深化 comp 非 spread**。
    - off-target 新阵营 且 已 ≥DEPLOY_FACTION_CAP 阵营 → −SPREAD_PENALTY(防 spread-lock 永久占槽)。
    - 否则 0(早期开第 1-3 阵营中性 / target 阵营新进 中性)。
    """
    factions = _distinct_factions(state)
    if card.faction and card.faction in factions:
        return REINFORCE_BONUS
    if target_comp is not None and _card_hits_target(card.name, card.faction, target_comp):
        return 0.0
    if len(factions) >= DEPLOY_FACTION_CAP:
        return -SPREAD_PENALTY
    return 0.0



def _card_supports_target(name: str, faction: str, state, target) -> bool:
    """买牌/deploy 的 off-target 判定(**配对纪律版**,M25 实证修正)。

    M4 方法论:骨架是「成对凑羁绊」非散买。规则:
    - 核心(core_chars 或核心阵营羁绊)→ 恒 True;
    - **枢纽早期核心**(EARLY_CORE_POOL,千冶·刃/姬子·启行等存活≥0.8)→ 单买 True
      (跨路线复用,买了就是开局,plaza M3);
    - flex 弹性羁绊 → 仅当该羁绊在 board+bench 已有 ≥1(深化成对)才 True;
      散买 flex 单张 = spread 合法化(M25 实锤:8 阵营各 1,列车:1 卡死,hp10 死 2-4)。
    """
    if target is None:
        return False
    if _card_hits_target(name, faction, target):   # 严格档(核心)
        return True
    if name in EARLY_CORE_POOL:
        return True
    from sr_od.application.currency_war.cw_economy import _char_synergies
    syn = _char_synergies(name)
    if faction and faction != '?':
        syn = syn | {faction}
    flex = target.all_factions - set(target.factions)
    if not flex:
        return False
    counts = _bench_faction_counts(state)
    return any(f in flex and counts.get(f, 0) >= 1 for f in syn)


# ADR-0149:通用填充件(用户 §7-14「星期日是通用辅助,阵容有缺口暂时用着也没所谓」——
# 低星低价不挑阵容的第三类,target/off-target 之外;成型后自然替换)。
GENERIC_FILLERS: list[str] = ['星期日']

# ADR-0149:无损购买窗口(用户 §7-11「金<20(1息档)买过渡件不损息还压缩牌库」)。
NO_LOSS_GOLD_CEILING: int = 20


def _no_loss_affordable(gold: int, cost: int) -> bool:
    """ADR-0149 评审R1:**档位保留**式无损可负担(用户原话「金13可以买到10金的」)。

    花后仍 ≥ 当前息档地板(gold//10 × 10)才放行 —— 金14 买 2费(14→12,息档1保留)✓;
    金14 买 4费(14→10,仍档1)✓;金14 买 5费(14→9,档1→0)✗。这同时是天然量控:
    单轮最多花掉「零头」,本金(整十部分)永不动 —— 无需显式「每轮 N 张」。
    """
    return gold - cost >= (gold // 10) * 10


def _skeleton_buy_ok(name: str, faction: str, state: GameState) -> bool:
    """P1 过渡骨架合法买(ADR-0149;与 flex 配对纪律同构,**不依赖 target**)。

    M4 方法论:过渡 = 骨架拼装(便宜低档羁绊成对),不是攒金也不是散买。三类合法:
    ① 枢纽池:EARLY_CORE_POOL(单买=开局,M3)/ TEMPO_POOL(打工,1星买卖近无损);
    ② 骨架羁绊配对:card 的羁绊 ∩ 骨架集,且 board+bench 已有 ≥1(凑**能激活档**的成对;
      评审Y1 收窄:买后 counts+1 ≥ 该羁绊最低激活档 —— 仙舟(3/5/7/10)已有 1 买第 2 张
      不激活任何效果=白占位,不深化到 2 不买);
    ③ 通用填充件:板未满时的 GENERIC_FILLERS(星期日;第三类语义)。
    散买骨架单张(羁绊无存量)仍拒 —— 防spread 回归(M25 教训)。
    """
    if name in EARLY_CORE_POOL or name in TEMPO_POOL:
        return True
    if name in GENERIC_FILLERS:
        return state.deployed_count() < state.max_units()
    from sr_od.application.currency_war.cw_economy import _char_synergies
    from sr_od.application.currency_war.cw_factions import FACTIONS
    syn = _char_synergies(name)
    if faction and faction != '?':
        syn = syn | {faction}
    sk = skeleton_factions() | {'持续伤害', '治疗'}   # 同 TRANSITION_FACTIONS 口径(cw_evaluate)
    counts = _bench_faction_counts(state)
    for f in syn:
        if f not in sk:
            continue
        _info = FACTIONS.get(f)
        _min_tier = min(_info.tiers) if (_info is not None and _info.tiers) else 2
        if counts.get(f, 0) + 1 >= _min_tier:   # 买后达到激活档(评审Y1)
            return True
    return False



def _bench_faction_counts(state: GameState) -> dict[str, int]:
    """已 collect 各阵营计数 = board(deployed ground truth)+ bench(_should_deploy 用)。"""
    counts: dict[str, int] = dict(state.board)
    for c in state.bench:
        if c.faction and c.faction != '?':
            counts[c.faction] = counts.get(c.faction, 0) + 1
    return counts



def _should_deploy(bc: BenchChar, state: GameState, target: Comp | None) -> bool:
    """是否 deploy 该角色(L2 deploy cap,防 spread-lock)。

    deploy 条件(任一):
    - target 阵营角色(target.factions 含 bc.faction 或 bc.char_id ∈ core_chars)。
    - bc.faction 在 bench+deployed 已 count≥2(集中阵营深化)。
    否则留 bench(off-target 单张可 sell,防 deployed-lock 永久占槽)。
    """
    if target is not None and _card_supports_target(bc.char_id, bc.faction, state, target):
        return True
    return _bench_faction_counts(state).get(bc.faction, 0) >= 2



# ===== A1:蒙特卡洛 D 牌(刷新商店期望值)=====

def _sample_cost(level: int, rng: random.Random) -> int:
    """按等级采费用(REFRESH_PROB 权威刷新概率表,D-91 实机 OCR;替旧手估 pool,A4.3)。

    D 牌蒙特卡洛用:采样 cost 必须贴合真实刷新概率(低级不出 5 费),否则 D 牌估值偏差。
    无数据(Lv<4 纯 1 费 / 越界)→ 1 费。
    """
    probs = REFRESH_PROB.get(level)
    if not probs:
        return 1
    costs = list(probs.keys())
    weights = list(probs.values())
    return rng.choices(costs, weights=weights, k=1)[0]



def _sample_shop(state: GameState, faction_priority: list[str], rng: random.Random,
                 n: int = 5, target_comp: Comp | None = None) -> list[ShopCard]:
    """采样 n 张可能的刷新牌(近似牌池模型)。阵营从 FACTIONS 采样(faction_priority + target_comp
    阵营加权),费用按等级。近似(无真实牌池计数);D 牌决策用其期望值。

    /F2:target 阵营加权 —— 蒙特卡洛 D 牌估值该考虑「roll 出 target 卡」的价值,否则 target 阵营
    不在 user priority 时 roll 估值偏低 → bot 不 roll → shop 无 target 卡时纯攒金/买 off-target →
    target 永不深成型(plane2 弱死)。加权 2×(同 priority)让 roll-for-target 进决策。
    """
    factions = list(FACTIONS.keys())
    target_factions = set(target_comp.factions) if target_comp is not None and target_comp.factions else set()
    weights = [2.0 if (f in faction_priority or f in target_factions) else 1.0 for f in factions]
    return [ShopCard(x=0, faction=rng.choices(factions, weights=weights, k=1)[0],
                     cost=_sample_cost(state.level, rng)) for _ in range(n)]



def _best_buy_deploy_eval(state: GameState, config, faction_priority: list[str],
                          target_comp: Comp | None = None) -> float:
    """给定 shop,取最优 buy+deploy 的 eval(用于蒙特卡洛 D 牌:新 shop 下能拿到的最高分)。

    target_comp: 战略层目标(A2),传给 evaluate 使 D 牌期望导向 target 成型。None=reactive。
    """
    best = evaluate(state, config, faction_priority, target_comp)
    _dep_names = {bc.char_id for bc in state.deployed if bc.char_id}
    _bench_cnt: dict[str, int] = {}
    for _bc in state.bench:
        if _bc.char_id:
            _bench_cnt[_bc.char_id] = _bench_cnt.get(_bc.char_id, 0) + 1
    for card in state.shop:
        if state.gold < card_cost(card):
            continue
        # review H3 修正:MC 候选与真实买同约束 —— 场上同名散牌不集(死钱)、副本≥3 不买。
        # 旧 MC 对真实买家会拒绝的牌照估分 → 刷新期望系统性乐观 → 每轮刷满 cap 烧金(M10 25刷6买)。
        _copies = (1 if card.name in _dep_names else 0) + _bench_cnt.get(card.name, 0)
        if _copies >= 3:
            continue
        if (card.name in _dep_names
                and not (target_comp is not None
                         and _card_hits_target(card.name, card.faction, target_comp))):
            continue
        after = simulate(state, BuyCard(card=card))
        if after.deployed_count() < after.max_units() and after.bench:
            bc = after.bench[-1]
            row, ok = _pick_deploy_row(after, bc, target_comp)
            if ok:
                after = simulate(after, DeployMove(bench_idx=len(after.bench) - 1,
                                                   to_row=row, faction=bc.faction))
        # 口径与真实买(_best_improving_action)一致:eval + concentration(char_quality 已计 priority)
        # review🔴 补 concentration(原漏→D牌估值偏);review🟡 去 priority*2(char_quality 一处计,原三重过度偏置)
        ev = (evaluate(after, config, faction_priority, target_comp)
              + _concentration_delta(card, state, target_comp))
        best = max(best, ev)
    return best



def _refresh_expected_delta(state: GameState, config, faction_priority: list[str],
                            base_eval: float, rng: random.Random, k: int = REFRESH_SAMPLES,
                            target_comp: Comp | None = None,
                            refresh_cost: int = SHOP_REFRESH_COST) -> float:
    """刷新商店的**期望 delta**(蒙特卡洛,A1):扣刷新金后,采样 k 个 shop,各取最优 buy+deploy
    eval,均值 − base_eval。这把"何时 D 牌"从无法建模变成可计算 —— D 牌当期望新 shop 收益 >
    刷新成本(economy 降)时发生。simulate 已扣 refresh cost,故期望含成本惩罚。

    refresh_cost(ADR-0131):本次刷新真实花金(策略免费额度内 = 0 → 免费刷新期望恒更优)。
    target_comp: 战略层目标(A2),透传给 _best_buy_deploy_eval。None=reactive。
    """
    if state.gold < refresh_cost:
        return -1e9
    after_cost = simulate(state, RefreshShop(refresh_cost))
    deltas = []
    for _ in range(k):
        s = after_cost.copy()
        s.shop = _sample_shop(after_cost, faction_priority, rng, target_comp=target_comp)
        deltas.append(_best_buy_deploy_eval(s, config, faction_priority, target_comp) - base_eval)
    return sum(deltas) / len(deltas) if deltas else 0.0



def level_up_gate(state: GameState, target_comp: Comp | None = None) -> bool:
    """买经验硬门(plan()/PrepDirector 腾席链 b 步共用单一源;doc 15 §5.2b / §4.1;ADR-0129)。

    条件 = level<10 + 该买经验(_want_level_up)+ 存金允许(扣单击价后不破 _xp_gold_floor)。
    旧门要求 gold≥整级大金(36-60)→ 实际每击仅 4-8 金 → 过度保守 → 升级滞后(M15 live 实锤)。
    ⚠️ gold 前置:shop 关态 gold 读空 —— 调用方须在 shop 开态的 fresh state 上判
    (PrepDirector: EnsureShopOpen 后重读;doc 15 §5.2b M2)。
    """
    if state.level >= 10:
        return False
    want = _want_level_up(state, target_comp)
    if not want:
        return False
    return state.gold - xp_click_cost(state) >= _xp_gold_floor(state, want)


def plan(state: GameState, config, faction_priority: list[str],
         rng: random.Random | None = None,
         target_comp: Comp | None = None,
         reactive: bool = False) -> list[Action]:
    """一回合动作计划:硬门(必做)+ 贪心改进(买/deploy/升/卖/**D 牌蒙特卡洛**)。

    config: CurrencyWarConfig。rng: 蒙特卡洛 D 牌用(默认新建;测试传 seeded 保确定)。
    target_comp: 战略层目标阵容(稳定,由上层 shop op 跨回合管理 + maybe_pivot 切换)。
        传入 → 用它(不每轮重选,防 select_comp 振荡致 churn);None → 内部 select_comp
        (向后兼容 / 测试 / reactive 退化)。硬门:bench-full 必破、gold≥0、level≤10。
    reactive: emergent —— True=授权 target=None(上层 update_target 阵营 count≥2 前不选 target),
        plan 不内部 select_comp(纯 L1 集中化驱动 buy/deploy);False(默认)= 向后兼容(None→内部 select_comp)。
    """
    rng = rng or random.Random()
    character_priority = getattr(config, 'character_priority', [])
    actions: list[Action] = []
    cur = state.copy()

    # —— 硬门:bench-full → 必破(优先升等级,无金则卖最弱)——
    if cur.bench_is_full():
        # bench-full 是阻塞态:点够「真升 1 级」的单击次数解锁(ADR-0129;点不起整套 → 卖最弱。
        # 旧按整级大金判可负担性 → 高估成本 → 不必要卖牌)。
        _clicks = clicks_to_next_level(cur)
        _one = xp_click_cost(cur)
        if cur.level < 10 and _clicks > 0 and cur.gold >= _clicks * _one:
            for _ in range(_clicks):
                actions.append(LevelUp(cost=_one))
                cur = simulate(cur, actions[-1])
        else:
            idx = _weakest_bench_idx(cur, character_priority, target_comp)
            if idx is not None:
                actions.append(SellBench(bench_idx=idx))
                cur = simulate(cur, actions[-1])

    # —— A2 战略层:target 由上层传入(稳定,防每轮 select_comp 振荡 → churn);未传则 select_comp ——
    # 2026-08-04 实跑:每轮 select_comp 随 board 微变翻转 target(列车同行↔DOT队)→ _maybe_sell_for_interest
    # 按振荡 target 卖牌 → 破坏性 churn(每轮换牌)+ 零收敛 → 比 reactive 更弱。故 target 须跨回合稳定
    # (上层 shop op 持久化 + maybe_pivot 才切),plan 只消费。详 task#16 + strategy/02 F-3。
    target = target_comp
    if target is None and not reactive:
        _candidates = select_comp(cur, make_score_context(cur), config)
        if _candidates:
            target = _candidates[0]

    # —— level_plan 硬 gate(task#18 经济统一论核心):level_plan 说 level_up + 够钱 → 升级(1 级/轮)——
    # 根因(replay 32 局「升 0 次」):贪心 eval 对「花大金升级」的利息损失短视 —— LevelUp 候选 delta 永负
    # (花 48 金 → 利息档 5→0 损 -20,level_val 仅 +6)→ 永不选中 → bot 卡 lv5-6 → 弱 comp → plane2 死。
    # level_plan 是**花费指令**非建议:说 level_up + afford → 执行,信任计划而非短视 eval。tempo 破息在所
    # 不惜(升级解锁高费刷新率 + 出战位 = 关键长期投资)。每轮最多 1 级(自然节流,防一轮烧光金)。
    # 升级条件单一源抽 level_up_gate(PrepDirector 腾席链 b 步共用,防两处漂移;P1 2026-08-14):
    # 够钱 + (level_plan 说 level_up **或** 落后 NodeGoal.target_level)。每轮 ≤1 级(自然节流)。
    if level_up_gate(cur, target):
        # ADR-0129:买经验 = 单击 +4 XP;点满「到下一级」所需次数为一段(每轮 ≤1 级自然节流),
        # 预算受 _xp_gold_floor 约束(追级期保 20 / 攒息期保 50 / 血危 10)。
        _one = xp_click_cost(cur)
        _budget = cur.gold - _xp_gold_floor(cur, True)
        for _ in range(min(clicks_to_next_level(cur), max(0, _budget // _one))):
            actions.append(LevelUp(cost=_one))
            cur = simulate(cur, actions[-1])

    # —— 贪心:反复选 eval 提升最大的动作序列(含 D 牌蒙特卡洛),直到无正提升 ——
    base_eval = evaluate(cur, config, faction_priority, target)
    for _ in range(15):
        refresh_used = sum(1 for a in actions if isinstance(a, RefreshShop))
        step = _best_improving_action(cur, config, faction_priority, base_eval, rng,
                                      refresh_budget=_refresh_cap(cur, effective_hp_threshold(cur),
                                                                  target_comp=target, config=config) - refresh_used,
                                      target_comp=target, rf_used=refresh_used)
        if not step:
            break
        actions.extend(step)
        for a in step:
            cur = simulate(cur, a)
        base_eval = evaluate(cur, config, faction_priority, target)

    # —— 凑整吃息:卖出能跨 10 倍数(+1 档息)的非关键 bench 牌(循环)——
    _maybe_sell_for_interest(cur, actions, character_priority, config, target_comp)
    # —— 集中卖散(r28 核心治法):散板根因——早期无 target 散买累计,无回收机制。
    # target 定后:bench 上 off-line(off-target 阵营 + 非优先角色 + 非过渡件)散牌
    # 卖出回收,金投核心;玩家「集中一条线时卖 off-line 换核心」的自然操作。
    # 场上(deployed)散牌**不卖**(上场战力 > 卖价;只清 bench 死库存)。
    _sell_offline_for_focus(cur, actions, character_priority, target)
    return actions


def _sell_offline_for_focus(state: GameState, actions: list,
                            character_priority: list[str], target: Comp | None) -> None:
    """集中卖散:target 定后清 bench 的 off-line 死库存(回收金投核心)。

    判据(off-line,全部满足才卖):非 target 阵营/角色/过渡件 + 非用户 priority
    + 非紧急战力(场上人数 < 上限时 bench 是死库存,卖出不损战力)。
    每回合最多清 2 张(渐进,防一次性清空误伤过渡期)。
    """
    if target is None or not state.bench:
        return
    from sr_od.application.currency_war.cw_state import simulate as _sim
    sold = 0
    _transition_chars = set(getattr(target, 'transition_chars', ()) or ())   # r9 review#1:角色级(transition_factions_hint 不存在,曾恒空→卖掉打工牌)
    for bc in list(state.bench):
        if sold >= 2:
            break
        if not bc.char_id:
            continue
        _is_target = _card_hits_target(bc.char_id, bc.faction, target)
        _is_priority = bc.char_id in character_priority
        _is_transition = bc.char_id in _transition_chars or \
            bc.faction in (getattr(target, 'flex_factions', ()) or ())
        if _is_target or _is_priority or _is_transition:
            continue
        # 场上**满员**时新牌上不了场,bench off-line 才是死库存(该卖);
        # 场上未满时 bench 牌可 deploy 换战力(暂留)。r32 修正:原判据方向写反
        # (deployed<max 才卖),live 快照 deployed 常含超编识别(14/6)→ 恒 False →
        # 集中卖散实际从未触发(局13 r6-r8 零 SellBench 实证)。
        if state.deployed_count() >= state.max_units():
            try:
                _idx = state.bench.index(bc)   # r9 review#3:值相等命中(同值卡分类同,语义等价)
            except ValueError:
                continue   # 已被前序卖掉(值不等幸存者)→ 跳过
            actions.append(SellBench(bench_idx=_idx))
            state = _sim(state, actions[-1])
            sold += 1



def _best_improving_action(
    state: GameState, config, faction_priority: list[str], base_eval: float,
    rng: random.Random, refresh_budget: int = 0, target_comp: Comp | None = None,
    rf_used: int = 0,
) -> list[Action]:
    """返回 eval 提升最大且为正的动作序列;无则 []。

    候选:买+deploy 原子组合、deploy 已有角色、**D 牌(蒙特卡洛期望)**。升等级不由这里候选 ——
    plan() 硬 gate 按 level_plan 执行(task#18;根因:eval 对花大金升级短视)。gold≥0/level≤10。
    refresh_budget: 本回合剩余可刷新次数(≤0 则不再生成 RefreshShop;防无限刷,review r5)。
    rf_used: 本回合已刷新次数(ADR-0131;决定第 next 次刷新花金 —— 策略免费额度内 = 0)。
    target_comp: 战略层目标阵容(A2);传给 evaluate,使动作导向 target 成型。None=reactive。
    """
    _rf_used = rf_used
    character_priority = getattr(config, 'character_priority', [])
    best: list[Action] = []
    best_delta = 0.0

    def beat(delta: float, seq: list[Action]) -> None:
        nonlocal best, best_delta
        if delta > best_delta + 1e-6:
            best, best_delta = seq, delta

    # 想升 + 存金不敷「单击价 + 地板」→ 抑制散牌买/刷,攒金(ADR-0129:单击价小,此抑制远弱于旧
    # 整级大金版,对齐用户「不影响吃息基础上多买牌」;只在真攒不出单击钱时才锁)。
    _want_level = _want_level_up(state, target_comp)
    _saving_for_level = (_want_level and state.gold
                         < xp_click_cost(state) + _xp_gold_floor(state, _want_level))
    # D-14(2026-08-09,4th 自审 + 经济诊断):_saving_for_level **不再**被 _board_strong 门控。
    # 旧门控(板弱 form_progress<COMMIT_FRAC → 不攒级 → 花买/刷)致 chicken-egg:tier-2 弱板→不攒级→永不升→
    # 卡 lv6 cap→上不了更多单位→永 tier-2→p2 死。**升级是 tempo 投资**(提 cap + shop 高费刷新率),任何板都该追。
    # _saving_for_level 抑制 off-target 买 + refresh(浪费金),留 target 买(建 comp)+ 攒金 → 够 cost 下轮 plan
    # level gate(优先执行)升级。**_saving_for_interest 仍由 _board_strong 门控**(息是经济,板强才囤,弱板不囤息)。
    # → 攒息。「维持≥50 金,超出才花;tempo(HP 危险/战力断档/连胜中)破息」(战力断档=板弱,非仅板位不满)。
    _saving_for_interest = _should_save_for_interest(state, config, target_comp)
    _saving = _saving_for_level or _saving_for_interest

    # 影子接缝(ADR-0156,06 号束优化):开关开 → 联合行动束优先(断点跳变/同名升星链的联合
    # 价值在束内可见,贪心单动作边际天然看不见);None/异常 → 落回下方贪心(现状栈,零改)。
    from sr_od.application.currency_war.cw_bundle import BUNDLE_SEAM_ACTIVE
    if BUNDLE_SEAM_ACTIVE:
        try:
            from sr_od.application.currency_war.cw_bundle import bundle_select
            _bundle = bundle_select(state, config, faction_priority, target_comp)
            if _bundle:
                log.info('[cw][bundle] 束选择:%s(交互项联合价值)',
                         [getattr(getattr(a, 'card', None), 'name', '?') for a in _bundle])
                return _bundle
        except Exception as _be:   # noqa: BLE001  影子 best-effort:任何异常回退贪心
            log.info(f'[cw][bundle] 影子跳过:{_be}')

    # 1) 买 + 上任组合(原子)
    # 同角色副本买入门(live M8 死钱实锤 + review H1 修正:游戏 3合1 = 全场合并(deployed+bench),
    # 旧 bench>=2 窗口从 shop 不可达 —— 第 1/2 张也被拦,计数永远起不来,已上阵单位锁死 1★)。
    # 修正语义:总副本(场上+bench)≥3 不买(纯浪费);场上已有同名时,仅 target/core 角色继续集
    # 第 2/3 张(集星意图),散牌不集(那才是 M8 死钱根因)。
    _deployed_name_counts: dict[str, int] = {}
    for _bc in state.deployed:
        if _bc.char_id:
            _deployed_name_counts[_bc.char_id] = _deployed_name_counts.get(_bc.char_id, 0) + 1
    _bench_name_counts: dict[str, int] = {}
    for _bc in state.bench:
        if _bc.char_id:
            _bench_name_counts[_bc.char_id] = _bench_name_counts.get(_bc.char_id, 0) + 1
    # review L2:星敏感计数 —— 商店牌恒 1★,3合1 材料须同名**同星**;deployed/bench 的 2★+ 不算材料。
    def _star1(coll, name: str) -> int:
        return sum(1 for b in coll if b.char_id == name and b.star == 1)
    def _copies(name: str) -> int:
        return _star1(state.deployed, name) + _star1(state.bench, name)
    for card in state.shop:
        cost = card_cost(card)
        if state.gold < cost:
            continue
        if card.name and _copies(card.name) >= 3:
            continue   # 已 3 张(自动合并中)/超 3 = 纯浪费(未知名不判)
        if (card.name and card.name in _deployed_name_counts
                and card_cost(card) > 1
                and not (target_comp is not None
                         and _card_hits_target(card.name, card.faction, target_comp))):
            # 场上已有同名散牌 → 不集(死钱);target/core 继续集;未知名不判(无法识别重复)。
            # ADR-0128(攻略复查 #11,前期过渡:29):**1费例外** —— 1星买卖净 0(ADR-0121),场上
            # 同名 1费买第 2/3 张集 2★ = 免费战力(合完还能原价卖),不属死钱。
            continue
        # 备战席)。买+deploy 原子:deploy 有位则买的牌上任(bench 不增);deploy 满则落 bench → bench 满才 skip。
        if state.deployed_count() >= state.max_units() and len(state.bench) >= BENCH_CAPACITY:
            continue
        # level_plan buying gate(task#18):攒金升级期间(_saving)抑制散牌,但仍允许 target
        # 阵营/core/优先角色牌(深化 target 值得花,且不该被攒金阻塞)。升级本身由 plan() 硬 gate 执行,
        # 这里只管"攒金期间别把金泄到散牌上"(解 replay 32 局金堆 50+ 不花/花在散牌上不升级)。
        if _saving:
            _is_target = (target_comp is not None
                          and (_card_hits_target(card.name, card.faction, target_comp)
                               or card.name in character_priority))
            # ADR-0149 无损购买窗口:金<20(1息档)买过渡件不损息还压牌池(用户 §7-11)——
            # 骨架纪律买放行,且 `_no_loss_affordable` 档位保留(评审R1:花后仍 ≥ 息档地板);
            # M22 实证 r4 金21 有货空手即此病。
            if (not _is_target and state.gold < NO_LOSS_GOLD_CEILING
                    and _no_loss_affordable(state.gold, card_cost(card))
                    and _skeleton_buy_ok(card.name, card.faction, state)):
                pass   # 落到下方正常估值(passthrough;非 continue)
            else:
                # tempo 例外(ADR-0124):板直接增强散牌不属「泄金」—— 板上 ≥2 同阵营深化 或 强卡
                # (cost≥3)且板不满员 → 放行(板饿死每场掉 HP,攒的金最后买不回血)。
                # review MED 修正:同 prefilter 收紧(board-only 计数 + 去 cost>=3 分支 + fp 守卫)
                if target_comp is not None and form_progress(target_comp, state) >= COMMIT_FRAC:
                    _strengthens_s = False   # 已成型:例外关(原 ADR-0124 语义)
                else:
                    _strengthens_s = (state.board.get(card.faction, 0) >= 2
                                      or card.name in character_priority)
                _room_s = (state.deployed_count() < state.max_units()
                           or len(state.bench) < BENCH_CAPACITY)
                if not _is_target and not (_strengthens_s and _room_s):
                    continue   # 散牌:攒金给升级,跳过
        # commitment prefilter(task#16 + ADR-0124 tempo 修订):target 设定时,若 shop 有 target 卡
        # (阵营∈target.factions 或 ∈core_chars)可买,跳过纯 off-target 散牌 → 聚焦深化 target。
        # **tempo 例外(2026-08-15 live 7 局实锤:commit 过早/过死饿死板)**:form_progress <
        # PREFILTER_STRICT_FRAC(0.4 = 未成型)时放行「板直接增强」散牌 —— 板上已有 ≥2 同阵营计数
        # (深化现有羁绊)或强卡(cost≥3)且板不满员。人类打法:前期买强散卡保 tempo,成型后纯堆 target。
        # 板饿死代价(每场 -10~-36 HP) > spread 代价(散卡仍可 deploy 保战力)。
        if target_comp is not None:
            # ADR-0152 M25 实证修正:flex 买牌**配对纪律**(_card_supports_target)—— flex 羁绊
            # 仅在已有 ≥1 时深化(骨架=成对,M4);枢纽早期核心单买放行(M3);散买 flex=spread 合法化。
            _is_offtarget = not _card_supports_target(card.name, card.faction, state, target_comp)
            if _is_offtarget:
                _shop_has_buyable_tgt = any(
                    _card_supports_target(c.name, c.faction, state, target_comp)
                    for c in state.shop if state.gold >= card_cost(c))
                if _shop_has_buyable_tgt:
                    continue   # shop 有 target 可买 → 聚焦
                # ADR-0149 骨架例外:shop 无 target 可买 + 未成型(fp<COMMIT_FRAC)→ 骨架纪律买
                # 放行(板饿死代价>spread,M15-M28 实证);已成型仍严格聚焦。与 tempo 例外并立。
                if (target_comp is not None
                        and form_progress(target_comp, state) < COMMIT_FRAC
                        and _skeleton_buy_ok(card.name, card.faction, state)):
                    _is_offtarget = False
            if _is_offtarget:
                if target_committed(target_comp, state):
                    # 已成型 commit:严格拒散牌(原 T#97 语义)。未成型(form_progress<0.4)commit:
                    # 放行板直接增强散牌(tempo 例外,防饿死)。
                    _fp = form_progress(target_comp, state)
                    # review H2 修正:阵营计数只用 board(deployed 真值;旧含 bench → 买进的单张反向
                    # 维持例外开启,fp 冻结 <0.4 例外永不关 = spread 吸引子);去 cost>=3 无阵营约束分支
                    # (OCR 失败 cost 默认 3 自动放行加剧 spread)。例外 = 深化**板上**已有 ≥2 的阵营
                    # 或 priority 角色(用户偏好);converge 导向。
                    _board_only = dict(state.board)
                    _strengthens = (_board_only.get(card.faction, 0) >= 2
                                    or card.name in character_priority)
                    _room = (state.deployed_count() < state.max_units()
                             or len(state.bench) < BENCH_CAPACITY)
                    if not (_fp < COMMIT_FRAC and _strengthens and _room):
                        continue
        after_buy = simulate(state, BuyCard(card=card))
        seq = [BuyCard(card=card)]
        # review M3:deploy 去重对齐游戏 5.1.7(场上同名禁双)—— 旧模拟把 2★ 与场上 1★ 双上阵,
        # 估值虚高 + 运行时滞留 bench。同名已 deployed → 不 deploy(留 bench 待 3合1 合并)。
        _dep_ids = {b.char_id for b in state.deployed if b.char_id}
        if (after_buy.deployed_count() < after_buy.max_units() and after_buy.bench
                and after_buy.bench[-1].char_id not in _dep_ids
                and _should_deploy(after_buy.bench[-1], after_buy, target_comp)):
            bc = after_buy.bench[-1]
            row, ok = _pick_deploy_row(after_buy, bc, target_comp)
            if ok:
                seq.append(DeployMove(bench_idx=len(after_buy.bench) - 1, to_row=row, faction=bc.faction))
        after = after_buy
        for a in seq[1:]:
            after = simulate(after, a)
        delta = evaluate(after, config, faction_priority, target_comp) - base_eval
        delta += _concentration_delta(card, state, target_comp)
        # review🟡 去 CHAR_PRIORITY_BONUS*2 flat(char_quality_score 已计 priority×star,原三重过度偏置)
        beat(delta, seq)

    # 2) 上任已拥有的 bench 角色(按 position_pref 分流;M3:同名去重同 1))
    _dep_ids2 = {b.char_id for b in state.deployed if b.char_id}
    for i, bc in enumerate(state.bench):
        if state.deployed_count() >= state.max_units():
            break
        if bc.char_id and bc.char_id in _dep_ids2:
            continue   # 场上已有同名(游戏禁双,5.1.7;留 bench 待合并)
        if not _should_deploy(bc, state, target_comp):
            continue
        row, ok = _pick_deploy_row(state, bc, target_comp)
        if not ok:
            continue
        mv = DeployMove(bench_idx=i, to_row=row, faction=bc.faction)
        beat(evaluate(simulate(state, mv), config, faction_priority, target_comp) - base_eval, [mv])

    # 3) D 牌/刷新商店(蒙特卡洛期望 delta;A1):受 refresh_budget 上限约束(防无限刷,review r5)。
    # 升等级不由这里候选 —— plan() 硬 gate 按 level_plan 执行(task#18;根因:eval 对「花大金升级」
    # 的利息损失短视 → LevelUp 候选 delta 永负 → 永不选 → 32 局升 0 次)。buying gate 同源:攒金升级期间
    # (_saving_for_level)不 D 牌(refresh 泄金,与散牌买同理)。
    # target 永不深成型 → plane2 弱秒死,2026-08-06 实跑)。_refresh_expected_delta 已加 target 阵营采样权重。
    # 的 hp 判定排除)。
    _shop_has_target = (target_comp is not None and any(
        _card_hits_target(c.name, c.faction, target_comp)
        for c in state.shop))
    # simulate(RefreshShop) 不建模换 shop(只扣金、shop 不变)→ 贪心误以为「Refresh 后还能买当前 shop 的 target」,
    # 故 plan 选 Refresh 作第一动作;但实跑 Refresh 换 shop → target 卡(追击×3)全没 → 只能买 off-target → spread。
    # 规则:auto-chess 基本功 —— target 卡在场且买得起 = 确定收益,Refresh 找 target 是赌注(蒙特卡洛乐观);
    # 取确定不取赌。买完所有买得起的 target(本字段转 False)才 Refresh 找更多。
    _shop_has_buyable_target = (target_comp is not None and any(
        _card_hits_target(c.name, c.faction, target_comp)
        for c in state.shop if state.gold >= card_cost(c)))
    # (3/3 局 survive plane1 但 comp count=1 不深 → plane2 秒死;策略子agent P3)。
    # M36 实证修正(2026-08-16):旧语义「无 faction≥2 才 roll」在 列车 2/4(fp 0.5)时翻 False →
    # 攒息期 refresh 恒被拦 → **P2 冻金**(M29-M36 金 15-23 攒着不转化的机制根因;半成型恰是最该
    # D 的时点,plaza M5「P2 全 D 凑成型」)。新语义:committed 且未成型(form_progress<1)→ roll 解锁。
    # 评审🟡1:叠加 ADR-0147 可负担性门(金计价:E[刷到核心]×2金 ≤ 预算金)—— 防 drought 长尾
    # 连刷烧光金(M20 病理;基础刷路径原来不查此门)。
    _roll_for_target = (target_comp is not None
                        and target_committed(target_comp, state)
                        and form_progress(target_comp, state) < 1.0
                        and roll_affordable(state, config, target_comp))
    # ADR-0149 骨架买兜底(评审R1/R2/Y1/Y2/Y3 修订后语义):
    # - 触发:金<20(1息档) **且** 候选最优为空/纯 Refresh(gold 花在赌刷新不如确定过渡件;Y3 不抢占
    #   eval 已选出的更优买,含 flex 配对买);
    # - 量控(R1):`_no_loss_affordable` 档位保留式(花后仍 ≥ 当前息档地板)—— 单轮只花零头,
    #   本金永不动,无需显式每轮 N 张;
    # - 原子 deploy(R2):买+立即 deploy(同 candidate-1 模式)—— 过渡件价值在场上保血,
    #   买而囤 bench = 白买(optionality 只数 bench 反向钉死枢纽件);
    # - plane 门(Y2):P2+ 息引擎重建期(ADR-0148)不吃骨架买;
    # - spread 守卫(Y1):板已 ≥DEPLOY_FACTION_CAP 阵营 → 只许深化已有阵营,不开新骨架对。
    # ⚖️ boss 前花尽(2026-08-17 M46/M48 同病根因修复:3/3 局 P1-9 boss 濒死)——boss 节点
    # gold 60-70 闲置 + 刷 10 次架无 target → **一张不买**就出战(骨架兜底的 plane/gold 两门
    # 全拦住)。boss 是 P 末硬节点,板强 = 保 HP(ADR-0128 同源):boss + form<成型 → 解锁
    # 骨架买(免 gold 上限/免 P1 门),把刷出来的确定战力买上;金花在板上 > 闲置挨打。
    _boss_spend = (state.node_type == 'boss'
                   and target_comp is not None
                   and form_progress(target_comp, state) < 1.0)
    if ((state.plane == 1 or _boss_spend)
            and (state.gold < NO_LOSS_GOLD_CEILING or _boss_spend)
            and target_comp is not None
            and not _shop_has_buyable_target
            and (form_progress(target_comp, state) < COMMIT_FRAC or _boss_spend)   # r7 ③:外层 fp 门在 boss 场豁免(fp 0.4-1.0 半成型恰是最需要兜底的域,M46/M48 实证 fp=0.5 被吞)
            and (not best or all(type(a).__name__ in ('RefreshShop', 'DeployMove') for a in best))):   # r9:DeployMove-only best 同样放行骨架买(shop.py 两阶段不执行 deploy 就 break → boss 帧饿死;奖励关掉角色入席正是触发态)
        _sk_candidates = [c for c in state.shop
                          if state.gold >= card_cost(c)   # r9:金硬门(boss 豁免息档地板≠免金;cost>gold 幽灵购买进 tracking)
                          and (_boss_spend or _no_loss_affordable(state.gold, card_cost(c)))   # r7 ②:boss 场免息档地板(ADR-0128 boss 前花尽;保息无意义)
                          and _skeleton_buy_ok(c.name, c.faction, state)]
        if len(_distinct_factions(state)) >= DEPLOY_FACTION_CAP:
            # spread 守卫:只留「深化已有阵营」候选(新阵营 = 第 N+1 个 spread)
            _counts = _bench_faction_counts(state)
            from sr_od.application.currency_war.cw_economy import (
                _char_synergies as _syn,
            )
            _sk_candidates = [c for c in _sk_candidates
                              if any(_counts.get(f, 0) >= 1 for f in
                                     (_syn(c.name) | ({c.faction} if c.faction and c.faction != '?' else set())))]
        if _sk_candidates:
            # 评审Y1③:排序 key 补「立即可激活档」优先(买后即达 min_tier 的骨架对 > 纯枢纽单买)
            from sr_od.application.currency_war.cw_factions import FACTIONS as _FAC
            def _activates_now(c) -> int:
                from sr_od.application.currency_war.cw_economy import (
                    _char_synergies as _syn2,
                )
                _s = _syn2(c.name) | ({c.faction} if c.faction and c.faction != '?' else set())
                _cnt = _bench_faction_counts(state)
                for f in _s:
                    _i = _FAC.get(f)
                    if f in (skeleton_factions() | {'持续伤害', '治疗'}) and _i is not None and _i.tiers:
                        if _cnt.get(f, 0) + 1 >= min(_i.tiers):
                            return 0
                return 1
            _sk_candidates.sort(key=lambda c: (
                _activates_now(c),
                0 if c.name in TEMPO_POOL or c.name in EARLY_CORE_POOL else 1,
                card_cost(c)))
            card = _sk_candidates[0]
            seq: list[Action] = [BuyCard(card=card)]
            after_buy = simulate(state, seq[0])
            _dep_ids = {b.char_id for b in state.deployed if b.char_id}
            if (after_buy.deployed_count() < after_buy.max_units() and after_buy.bench
                    and after_buy.bench[-1].char_id not in _dep_ids):
                bc = after_buy.bench[-1]
                row, ok = _pick_deploy_row(after_buy, bc, target_comp)
                if ok:
                    seq.append(DeployMove(bench_idx=len(after_buy.bench) - 1, to_row=row, faction=bc.faction))
            log.info('[cw-plan] ADR-0149 骨架买(1息档,档位保留):%s(cost%s,gold%s,deploy=%s)',
                     card.name, card.cost, state.gold, len(seq) > 1)
            return seq
    _rf_cost = _refresh_cost(state, _rf_used)
    if (state.gold >= _rf_cost and refresh_budget > 0
            and not _shop_has_buyable_target
            and (not _saving_for_level or not _shop_has_target)
            and not (_saving_for_interest and not _roll_for_target)):
        # 评审R3 连带守卫:①攒级期(ADR-0129)+ drought(无 target 在场)→ 刷金与攒级矛盾
        # (M22 r6/r8 病理:XP×3+Refresh×2 把金 33→17);②金<20(1息档)禁刷 —— 零头是骨架买
        # 的弹药,刷一次 -2 直接破档(评审实证 19→5);骨架兜底已处理此场景。
        _drought_no_target = (target_comp is not None and not _shop_has_target)
        if not (_saving_for_level and _drought_no_target) and state.gold >= NO_LOSS_GOLD_CEILING:
            beat(_refresh_expected_delta(state, config, faction_priority, base_eval, rng,
                                         target_comp=target_comp, refresh_cost=_rf_cost),
                 [RefreshShop(cost=_rf_cost)])

    return best



def _pick_deploy_row(state: GameState, bc: BenchChar,
                    target_comp: Comp | None = None) -> tuple[str, bool]:
    """按角色 position_pref 选排(偏好排优先,满则另一排);无空位返回 (row, False)。

    ADR-0139:target_comp.char_positions(角色→front/back)覆盖命途默认 —— comp 特定站位是攻略实证
    (爻光必后台/万敌独前排),比命途 position_pref 更准;无条目按默认。
    """
    if state.deployed_count() >= state.max_units():
        return ("front", False)
    pref = bc.position_pref or "back"
    if target_comp is not None and bc.char_id in target_comp.char_positions:
        pref = target_comp.char_positions[bc.char_id]
    if pref == "front" and state.front_count() < state.front_max:
        return ("front", True)
    if state.back_count() < state.back_max:
        return ("back", True)
    if state.front_count() < state.front_max:
        return ("front", True)
    return ("front", False)



def _maybe_sell_for_interest(state: GameState, actions: list[Action],
                             character_priority: list[str], config,
                             target_comp: Comp | None = None) -> None:
    """凑整吃息:卖出能跨一个 10 倍数(+1 档息)的非关键 bench 牌(循环,最多 3 张)。"""
    if state.gold >= INTEREST_THRESHOLD or not state.bench:
        return
    # node_plan(14 §2.2):节点 spend_mode 花光成型(allin,P3)/ 升人口(level,P2)/ 抢升(rush_level)
    # 档位不囤息(卖息与节奏相悖)。⚠️ 本函数是 spend_mode 的**动作消费者**(allin/level → 跳卖息动作);
    # 另一消费者 ``_economy_mode_for``(ADR-0102)是**评分消费者**(spend_mode → economy_mode 映射,调
    # economy_score 利息/等级相对权重)。两者刻意不同映射:本函数挡「卖息凑档」动作(allin/level 不该囤息),
    # _economy_mode_for 调经济评分相对权重(level→rush_level / allin→adaptive neutral,economy-low 由
    # _phase_weights plane3 we=0.3 处理)—— 语义不同,勿强行统一(审计 round-17 borderline#2)。
    # r14 切流预备:传全状态(47 号语义——HORIZON_SEAM_ACTIVE 开启时 DP 姿态生效;
    # 关时 gold/level/hp 参数被忽略走表,行为零变化)。
    _spend = get_node_goal(state.plane, state.round_num,
                           gold=state.gold, level=state.level, hp=state.hp).spend_mode
    if _spend in ("allin", "level"):
        return
    cur = state
    # r9 review#2:keep 集对齐 focus 卖版——transition_chars(打工牌)不卖凑息
    # (两卖函数保护集不一致会互相打架:focus 保的弹性件被 interest 跨档卖掉)
    _tc = set(getattr(target_comp, 'transition_chars', ()) or ()) if target_comp is not None else set()
    for _ in range(3):
        close = _close_factions(cur)
        best_idx = None
        for i, bc in enumerate(cur.bench):
            if bc.char_id in character_priority or bc.char_id in _tc or bc.faction in close:
                continue
            # review 🔴:target 核心不卖凑息(承诺贯穿卖路径;防卖刚买的 target 核心凑息)
            if target_comp is not None and _card_hits_target(bc.char_id, bc.faction, target_comp):
                continue
            refund = sell_refund(bc.star, _bench_char_cost(bc))
            if (cur.gold + refund) // 10 > cur.gold // 10 and cur.gold + refund <= INTEREST_THRESHOLD:
                best_idx = i
                break
        if best_idx is None:
            break
        actions.append(SellBench(bench_idx=best_idx))
        cur = simulate(cur, actions[-1])
