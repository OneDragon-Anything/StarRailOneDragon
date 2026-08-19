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


def _skeleton_buy_ok(name: str, faction: str, state: GameState,
                     framework: str = '') -> bool:
    """P1 过渡骨架合法买(ADR-0149;与 flex 配对纪律同构,**不依赖 target**)。

    M4 方法论:过渡 = 骨架拼装(便宜低档羁绊成对),不是攒金也不是散买。三类合法:
    ① 枢纽池:EARLY_CORE_POOL(单买=开局,M3)/ TEMPO_POOL(打工,1星买卖近无损);
    ② 骨架羁绊配对:card 的羁绊 ∩ 骨架集,且 board+bench 已有 ≥1(凑**能激活档**的成对;
      评审Y1 收窄:买后 counts+1 ≥ 该羁绊最低激活档 —— 仙舟(3/5/7/10)已有 1 买第 2 张
      不激活任何效果=白占位,不深化到 2 不买);
    ③ 通用填充件:板未满时的 GENERIC_FILLERS(星期日;第三类语义)。
    散买骨架单张(羁绊无存量)仍拒 —— 防spread 回归(M25 教训)。

    ⚖️ r95 审计必修③(配方自举豁免):旧 ② 的「不激活不买」把**过渡配方主体阵营**锁死在
    1 副本(仙舟最低档 3:已有 1 买第 2 张被拒 → 第 3 张也永远凑不齐)——run16 实证
    target=景元仙舟、shop 有仙舟牌、金 62-94 却一张不买。配方是**渐进拼装**(第16局
    审计定论),豁免:**当先过渡框架的目标阵营**(TRANSITION_PACK 里框架主体阵营,如
    仙舟对仙舟框架/列车对列车框架)从第 2 张起放行(它们是配方向 3 档推进的必经中间态,
    非"白占位")。非框架阵营维持评审Y1 原语义。
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
    # r95 配方自举豁免:当先框架的目标阵营(已有 ≥1 即在配方向上)→ 放行
    from sr_od.application.currency_war.cw_transition import FRAMEWORK_FACTIONS
    _fw_fac = set(FRAMEWORK_FACTIONS.get(framework, ()) or ()) if framework else set()
    for f in syn:
        if f in _fw_fac and counts.get(f, 0) >= 1:
            return True
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



def _dep_activates_tier(bc: BenchChar, state: GameState) -> bool:
    """r90 C1 上场即激活档:该牌上场后 board 阵营计数命中**此前未达**的激活档。

    攻略 #245「手上有 4击破 才让白厄上场」的判据形式化:final 件的上场窗口之一 =
    上场本身产生确定羁绊增量(新档激活)。deepen 已达最高档不算(那是深化,归框架件管)。
    ⚠️ 口径:只数场上(board),bench 囤牌不计入激活(游戏正确口径;并入 bench 会误判
    「囤 2 张后第 1 张即激活」提前散上)。本函数只评估**候选卡本身**;「bench 囤的第
    2/3 张同阵营齐档后整组上场」的组合窗口不在此判(靠窗口①定型/②位面末兜底,
    单卡永不触发③——r90 审计 A.a 记录,接受该简化)。
    """
    from sr_od.application.currency_war.cw_economy import _char_synergies
    from sr_od.application.currency_war.cw_factions import FACTIONS
    syn = _char_synergies(bc.char_id) if bc.char_id else set()
    if bc.faction and bc.faction != '?':
        syn = syn | {bc.faction}
    for f in syn:
        _i = FACTIONS.get(f)
        if _i is None or not _i.tiers:
            continue
        cur = state.board.get(f, 0)
        new = cur + 1
        hits_new = any(new >= t for t in _i.tiers)
        hits_old = any(cur >= t for t in _i.tiers)
        if hits_new and not hits_old:
            return True
    return False


def deploy_legal(bc: BenchChar, deployed_names: set[str]) -> bool:
    """⚖️ 全局不变量守卫(单一源,r94):**场上同名禁双**(游戏规则 5.1.7 实测,ADR-0125)。

    **一切「把角色放上场」的路径必须过本守卫**——买后 deploy / 腾席链 / 换位 /
    任何新 deploy 路径。历史上散在三处内联(cw_plan 主循环/deploy_bench/cw_state
    注释),第 4 处新路径(腾席链 a,r93)漏写 → 藿藿被拖 5 次全拒实证。收口单一
    函数后新路径只需调用,不再依赖"记得写"。
    同名在场 → False(留 bench 待 3合1 合并,合并域=全场)。
    """
    return not (bc.char_id and bc.char_id in deployed_names)


def deployed_name_set(state: GameState) -> set[str]:
    """场上角色名集(deploy_legal 的配套取数;单一源防各处自算漂移)。"""
    return {b.char_id for b in state.deployed if b.char_id}


def _should_deploy(bc: BenchChar, state: GameState, target: Comp | None) -> bool:
    """是否 deploy 该角色(L2 deploy cap,防 spread-lock)。

    r90 C1 **final 件条件窗口**(663 帖攻略精读 #243/#245/#249:final 件买而囤 bench,
    等窗口才上场 —— 用户定性「凑 final 不是问题,让它上场却取不了胜利才是」):
    双轨期(P1 未定型)target 件**不再即买即上**(旧 L251 直 True = P1 板长成 final
    散件打不过过渡阵容,第9局四线散板实证)。P1 的板 = 过渡框架;final 件囤 bench,
    上场窗口(任一):
    - ①非双轨(定型信号 ready / 进 P2)→ 无条件上;
    - ②位面末变阵窗(round ≥ 8;#243「1-8 奖励关后 d,1-9 变阵」)→ 换 final 上;
    - ③上场即激活阵营档(见 ``_dep_activates_tier``;#245 白厄=4击破齐)→ 即刻兑现;
    - ④框架在册件(TRANSITION_PACK 非 drop,仙舟/列车/通用)→ 双轨期临时 target 照上(r70)。
    窗口外落回集中判据(阵营 count≥2 深化)。

    ⚖️ r94:本函数顶部统一执行 ``deploy_legal``(场上同名禁双,全局不变量)——
    所有调用方(主循环/腾席链/任何新路径)经此即受保护,内联守卫不再各写。
    deploy 条件(任一,窗口外):
    - target 阵营角色(窗口内,见上)。
    - bc.faction 在 bench+deployed 已 count≥2(集中阵营深化)。
    否则留 bench(off-target 单张可 sell,防 deployed-lock 永久占槽)。
    """
    if not deploy_legal(bc, deployed_name_set(state)):
        return False   # 场上同名禁双(5.1.7,全局不变量;留 bench 待 3合1)
    if target is not None and _card_supports_target(bc.char_id, bc.faction, state, target):
        if not state.dual_track_phase:
            return True   # ①已定型/进 P2:final 即主力
        if state.round_num >= 8:
            return True   # ②位面末变阵窗(P1 r8 奖励关起 → r9 boss 前换 final)
        if _dep_activates_tier(bc, state):
            return True   # ③上场即激活档(确定战力即刻兑现)
        # 双轨期窗口外:final 件囤 bench(stash),落到下方框架/集中判据
    if state.dual_track_phase and bc.char_id:
        # r72 口径对齐(review #3):三侧统一「当先框架非 drop + 通用件」——
        # 散件 drop(艾丝妲/佩拉)不自动上(应急件,op 侧同口径);通用 carry
        # (千冶·刃 29%→64%)三侧都认。框架由 plan(framework=)/session 单一源。
        from sr_od.application.currency_war.cw_transition import TRANSITION_PACK as _TP
        _e = _TP.get(bc.char_id)
        if _e is not None and _e[0] in ('仙舟', '列车', '通用') and _e[1] != 'drop':
            return True
    return _bench_faction_counts(state).get(bc.faction, 0) >= 2



# ===== A1:蒙特卡洛 D 牌(刷新商店期望值)=====

def _sample_cost(level: int, rng: random.Random,
                 probs_override: dict[int, float] | None = None) -> int:
    """按等级采费用(REFRESH_PROB 权威刷新概率表,D-91 实机 OCR;替旧手估 pool,A4.3)。

    D 牌蒙特卡洛用:采样 cost 必须贴合真实刷新概率(低级不出 5 费),否则 D 牌估值偏差。
    probs_override(r77 轮岗接线):实读概率条(state.refresh_probs,投资环境轮岗每备战
    阶段随机翻倍一档)优先;None → 基线表。无数据(Lv<4 纯 1 费 / 越界)→ 1 费。
    """
    probs = probs_override or REFRESH_PROB.get(level)
    if not probs:
        return 1
    costs = list(probs.keys())
    weights = list(probs.values())
    if sum(weights) <= 0:
        return 1
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
                     cost=_sample_cost(state.level, rng,
                                       probs_override=getattr(state, 'refresh_probs', None))
                     ) for _ in range(n)]



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

    **溢出金 XP 放行(r85,用户 50 金息律「>50 的每一分都无存钱意义,该升级就升级」)**:
    金 ≥ INTEREST_THRESHOLD + 单击价 时(息满溢出区),_want_level_up 的 False
    (DP 攒息姿态压 target_level)不再拦 —— 溢出部分买经验不损息档地板 50,
    白嫖人口进度;姿态的「攒息」目的此时已达成,不矛盾。P1 末 60-70 金闲置
    实证(用户演示局对照)即此缺口。地板仍守(花后 ≥50)。
    """
    if state.level >= 10:
        return False
    want = _want_level_up(state, target_comp)
    if not want:
        # r85 溢出区放行:息满 + 够单击 + 花后不破 50 地板 → 姿态压制不拦溢出金
        return (state.gold >= INTEREST_THRESHOLD + xp_click_cost(state)
                and state.gold - xp_click_cost(state) >= INTEREST_THRESHOLD)
    return state.gold - xp_click_cost(state) >= _xp_gold_floor(state, want)


def plan(state: GameState, config, faction_priority: list[str],
         rng: random.Random | None = None,
         target_comp: Comp | None = None,
         reactive: bool = False,
         stash_comp: Comp | None = None,
         focus_sell_cap: int = 2,
         framework: str = '') -> list[Action]:
    """一回合动作计划:硬门(必做)+ 贪心改进(买/deploy/升/卖/**D 牌蒙特卡洛**)。

    config: CurrencyWarConfig。rng: 蒙特卡洛 D 牌用(默认新建;测试传 seeded 保确定)。
    target_comp: 战略层目标阵容(稳定,由上层 shop op 跨回合管理 + maybe_pivot 切换)。
        传入 → 用它(不每轮重选,防 select_comp 振荡致 churn);None → 内部 select_comp
        (向后兼容 / 测试 / reactive 退化)。硬门:bench-full 必破、gold≥0、level≤10。
    reactive: emergent —— True=授权 target=None(上层 update_target 阵营 count≥2 前不选 target),
        plan 不内部 select_comp(纯 L1 集中化驱动 buy/deploy);False(默认)= 向后兼容(None→内部 select_comp)。
    stash_comp: ADR-0209 双轨期信号领先线(囤牌方向;None=未起)。双轨期放行
        过渡包牌+此线的 core/阵营牌(囤 bench),其他散牌不买。
    framework: r70 过渡框架(仙舟/列车;''=未定)——双轨期买牌 delta 加 transition_score
        同框架加成、deploy 认框架牌、卖出 keep 集保护框架 carry/partial。三侧单一源自
        cw_transition.pick_framework(session 持有);治「买了→不上场→被当散牌卖掉」循环。
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
    # (上层 shop op 持久化 + maybe_pivot 才切),plan 只消费。详 task#16 + ADR-0096(α(t))。
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
                                      target_comp=target, rf_used=refresh_used,
                                      stash_comp=stash_comp, framework=framework)
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
    _sell_offline_for_focus(cur, actions, character_priority, target,
                            sell_cap=focus_sell_cap, framework=framework)
    return actions


def _sell_offline_for_focus(state: GameState, actions: list,
                            character_priority: list[str], target: Comp | None,
                            sell_cap: int = 2, framework: str = '') -> None:
    """集中卖散:target 定后清 bench 的 off-line 死库存(回收金投核心)。

    判据(off-line,全部满足才卖):非 target 阵营/角色/过渡件 + 非用户 priority
    + 非紧急战力(场上人数 < 上限时 bench 是死库存,卖出不损战力)。
    每回合最多清 sell_cap 张(默认 2 渐进;ADR-0209 定型边沿放宽加急)。
    framework(r72 review:session 单一源透传,替旧 bench-only 重推导——混持/散件场景
    旧法 `_fw=''` → keep 集恒空,「买→不上→卖」循环只修了半边)。
    """
    if target is None or not state.bench:
        return
    from sr_od.application.currency_war.cw_state import simulate as _sim
    sold = 0
    _transition_chars = set(getattr(target, 'transition_chars', ()) or ())   # r9 review#1:角色级(transition_factions_hint 不存在,曾恒空→卖掉打工牌)
    # r70 框架保护集(keep = 当先框架的 carry/partial + 通用件;framework 来自 session,
    # 与买侧/deploy 侧同源)。''=未定框架 → 仅散件 drop 无保护。
    from sr_od.application.currency_war.cw_transition import TRANSITION_PACK
    _fw_keep = ({n for n, (f, t) in TRANSITION_PACK.items()
                 if (f == framework or f == '通用') and t != 'drop'} if framework else set())
    for bc in list(state.bench):
        if sold >= sell_cap:
            break
        if not bc.char_id:
            continue
        _is_target = _card_hits_target(bc.char_id, bc.faction, target)
        _is_priority = bc.char_id in character_priority
        _is_transition = bc.char_id in _transition_chars or \
            bc.faction in (getattr(target, 'flex_factions', ()) or ())
        if _is_target or _is_priority or _is_transition or bc.char_id in _fw_keep:
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



def _compress_release(cost: int, gold: int, hunt_tiers: set[int]) -> bool:
    """牌池压缩买放行判定(纯函数;r61/r62 用户节奏 §7-1/§7-15)。

    「买便宜 1/2 星 = 追求过渡阵容的牌库压缩」——全局供给策略:抽走噪声牌升
    目标卡后续出现率,不问费级归属。**统一保息门**(r64 review P1 修:1 费「净 0」
    只对买卖往返成立,持有跨轮末在金=10 边界损 1 金息 —— 用户原则「保息前提下
    多买」统一适用):买后利息档不降才放行(含 1 费)。
    """
    if cost <= 2 or cost in hunt_tiers:
        return (gold - cost) // 10 == gold // 10
    return False


def _hunt_tier_set(state: GameState, comps: tuple) -> set[int]:
    """追猎费级(ADR-0209 r52 用户指导;**玩法理解**:gameplay/currency_war.md 策略模型 S3)。

    目标牌是动态的,非静态 core 列表——改本函数前先对表该文档:
    ①缺谁追谁——target/stash 的 core 未到 2★ → 在追(过渡与最终两边的 core 都算);
    ②基本目标 2★——核心输出 3★ 难凑,2★ 为主目标;辅助 2★ 也能快速完成;
    ③牌运追猎——场上/bench 已 2★ 的角色,其费级入集(「3费辅助已 2★×2 →
      有几率追 3★」;当前商店等级该费级概率最高时收益最大)。

    返回费级集;供牌池压缩买判定(同费非目标卡保息买入,降分母提命中率;
    压缩语义见同文档 S1 牌库操纵)。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    tiers: set[int] = set()

    def _equiv_copies(name: str) -> int:
        # 3合1 等价副本数(2026-08-18 修,项目权威口径:2★=3张1★、3★=9张,
        # 见 cw_state._SELL_MULT/cw_comps/cw_shop_odds 同源语义):star 折 3**(star-1)。
        # 旧 sum(bc.star)(2★=2/3★=3)配 <2 阈值 → 持 2 张 1★ 即被判「已到 2★ 不在追」,
        # 实际差 1 张才能合并 → 该费级被移出追猎集,压缩买少覆盖一类该买的费级。
        return sum(3 ** max(bc.star - 1, 0) for bc in (*state.deployed, *state.bench)
                   if bc.char_id == name)

    for comp in comps:
        if comp is None:
            continue
        for name in comp.core_chars:
            ch = CHARACTERS.get(name)
            _cost = getattr(ch, 'cost', None)
            if ch is None or not _cost:
                continue
            if _equiv_copies(name) < 3:   # ①+②:core 未到 2★(=3 张 1★ 等价)→ 在追
                tiers.add(int(_cost))
    for bc in (*state.deployed, *state.bench):
        if bc.star >= 2 and bc.char_id:   # ③:已 2★ → 3★ 机会追猎
            ch = CHARACTERS.get(bc.char_id)
            _cost = getattr(ch, 'cost', None)
            if ch is not None and _cost:
                tiers.add(int(_cost))
    return tiers


def _best_improving_action(
    state: GameState, config, faction_priority: list[str], base_eval: float,
    rng: random.Random, refresh_budget: int = 0, target_comp: Comp | None = None,
    rf_used: int = 0, stash_comp: Comp | None = None, framework: str = '',
) -> list[Action]:
    """返回 eval 提升最大且为正的动作序列;无则 []。

    候选:买+deploy 原子组合、deploy 已有角色、**D 牌(蒙特卡洛期望)**。升等级不由这里候选 ——
    plan() 硬 gate 按 level_plan 执行(task#18;根因:eval 对花大金升级短视)。gold≥0/level≤10。
    refresh_budget: 本回合剩余可刷新次数(≤0 则不再生成 RefreshShop;防无限刷,review r5)。
    rf_used: 本回合已刷新次数(ADR-0131;决定第 next 次刷新花金 —— 策略免费额度内 = 0)。
    target_comp: 战略层目标阵容(A2);传给 evaluate,使动作导向 target 成型。None=reactive。
    stash_comp: ADR-0209 双轨期信号领先线(囤牌放行面;None=非双轨/信号未起)。
    framework: r70 过渡框架(买分加 transition_score 同框架加成;''=未定不加)。
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
    # ADR-0209(接线 3/6):双轨买牌——双轨期(dual_track_phase)放行面收窄为:
    # ①过渡包牌(TRANSITION_PACK 在册:上场保血);②信号领先线的 core/阵营牌
    # (stash_comp 传入,囤 bench 不上场,1/2费买卖净 0 兼操纵牌池);③其他 skip(防散板)。
    # 非双轨期不走此门(原逻辑)。stash_comp=None = 信号未起 → 只买过渡包。
    # r52 牌池压缩例外(用户指导):追猎费级同费的非目标卡,保息前提下买入压池
    # (降分母提命中率),后续卖出净损 0-1(1星买卖净 0,economy §2 实证);
    # 压缩持有由集中卖散自然回收(off-line 牌)。
    _dual = state.dual_track_phase
    _hunt_tiers: set[int] = set()   # 双轨期填充(r62:_saving 门压缩放行也消费,提前初始化)
    if _dual:
        from sr_od.application.currency_war.cw_transition import TRANSITION_PACK
        # 常数削减(r51 用户效率提醒):双轨放行面预计算——stash/target 的
        # core+faction 名集一次建好,循环内纯 set 查(免逐卡×逐 comp 的
        # _card_hits_target 函数调用)
        _allow_names: set[str] = set()
        _allow_factions: set[str] = set()
        for _sc in (stash_comp, target_comp):
            if _sc is not None:
                _allow_names.update(_sc.core_chars)
                _allow_factions.update(_sc.factions)
        _hunt_tiers = _hunt_tier_set(state, (stash_comp, target_comp))
    for card in state.shop:
        cost = card_cost(card)
        if state.gold < cost:
            continue
        if _dual and card.name:
            _ent = TRANSITION_PACK.get(card.name)
            if (_ent is None and card.name not in _allow_names
                    and card.faction not in _allow_factions):
                # 牌池压缩例外(用户节奏 §7-1/§7-15,判定 = _compress_release 纯函数)
                if not _compress_release(card_cost(card), state.gold, _hunt_tiers):
                    continue   # 双轨期:非过渡包/非领先线/非压缩件 → 散牌不买
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
                    and _skeleton_buy_ok(card.name, card.faction, state, framework=framework)):
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
                # r62 压缩放行(用户 §7-15:压缩=全局供给策略,非泄金;判定纯函数同上)
                # ——攒金期照买(「保息前提下多买」语义,攒金门只该拦真泄金散牌)。
                _compress_ok = _compress_release(card_cost(card), state.gold, _hunt_tiers)
                if not _is_target and not _compress_ok and not (_strengthens_s and _room_s):
                    continue   # 散牌:攒金给升级,跳过(压缩/板增强例外放行)
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
                    # r64 review P2 修:压缩放行例外(§7-15 压缩=全局供给策略,与聚焦不冲突
                    # —— 便宜噪声牌抽走直接提 target 卡后续出现率;判定同 _compress_release)。
                    if not _compress_release(card_cost(card), state.gold, _hunt_tiers):
                        continue   # shop 有 target 可买 → 聚焦(压缩件照买)
                # ADR-0149 骨架例外:shop 无 target 可买 + 未成型(fp<COMMIT_FRAC)→ 骨架纪律买
                # 放行(板饿死代价>spread,M15-M28 实证);已成型仍严格聚焦。与 tempo 例外并立。
                if (target_comp is not None
                        and form_progress(target_comp, state) < COMMIT_FRAC
                        and _skeleton_buy_ok(card.name, card.faction, state, framework=framework)):
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
        # r70 框架买分:双轨期同框架牌加 transition_score(carry 1.3/partial 0.9+集中加成;
        # 旧 framework 恒 '' → 框架集中评分空转,买出来是 13 人名单散混合)。×0.8 缩放 =
        # 与 synergy delta 同量纲但不盖过成型分(经验缩放,待对拍校准)。
        if _dual and framework:
            from sr_od.application.currency_war.cw_transition import transition_score
            delta += 0.8 * transition_score(card.name, card.faction, framework)
        # review🟡 去 CHAR_PRIORITY_BONUS*2 flat(char_quality_score 已计 priority×star,原三重过度偏置)
        beat(delta, seq)

    # 2) 上任已拥有的 bench 角色(按 position_pref 分流;M3:同名去重同 1))
    # r94:内联同名守卫删(_should_deploy 顶部统一执行 deploy_legal 不变量)
    for i, bc in enumerate(state.bench):
        if state.deployed_count() >= state.max_units():
            break
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
    # ⚖️ 花光域(r89 息律通用化,用户定调「满息即花,节点无关」):**金高位(gold≥INTEREST_THRESHOLD
    # 即满息溢出)+ form<成型** 即解锁骨架买 —— 金>50 的每一分都无存的意义,花的通道节点无关
    # 恒开;boss/P2 首战(旧 _boss_spend 特例)只是「到时自然满息 + 边际价值高」的高频场景,
    # 由本通用条件自然覆盖,不再单列(2026-08-17 M46/M48 病根因的通用修:P1 末 60-70 金闲置
    # 正是旧特例把通道锁在 boss 才发生;#145 攻略「资金超50时用多余金币升级」佐证)。
    # 候选排序:r73 RC5 语义保留(target core 优先,防 r9 boss 前 61 金全买过渡件)。
    _spill_spend = (state.gold >= INTEREST_THRESHOLD and target_comp is not None
                    and form_progress(target_comp, state) < 1.0)
    if ((state.plane == 1 or _spill_spend)
            and (state.gold < NO_LOSS_GOLD_CEILING or _spill_spend)
            and target_comp is not None
            and not _shop_has_buyable_target
            and (form_progress(target_comp, state) < COMMIT_FRAC or _spill_spend)   # r7 ③:外层 fp 门在高位金场豁免(fp 0.4-1.0 半成型恰是最需要兜底的域,M46/M48 实证 fp=0.5 被吞)
            and (not best or all(type(a).__name__ in ('RefreshShop', 'DeployMove') for a in best))):   # r9:DeployMove-only best 同样放行骨架买(shop.py 两阶段不执行 deploy 就 break → boss 帧饿死;奖励关掉角色入席正是触发态)
        _sk_candidates = [c for c in state.shop
                          if state.gold >= card_cost(c)   # r9:金硬门(高位金豁免息档地板≠免金;cost>gold 幽灵购买进 tracking)
                          and (_spill_spend or _no_loss_affordable(state.gold, card_cost(c)))   # r7 ②:高位金场免息档地板(满息溢出花掉不损息档)
                          and _skeleton_buy_ok(c.name, c.faction, state, framework=framework)]
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
                # r73 RC5/r89:高位金花光候选 **target core 优先**(旧排序只看 TEMPO/EARLY 池
                # → r9 boss 前 61 金全买过渡件,进 P2 全是待弃资产);平时骨架买仍按池序。
                (0 if (target_comp is not None and c.name in target_comp.core_chars) else
                 (0 if c.name in TEMPO_POOL or c.name in EARLY_CORE_POOL else 1))
                if _spill_spend else
                (0 if c.name in TEMPO_POOL or c.name in EARLY_CORE_POOL else 1),
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

    # r66 压缩扫尾(用户 §7-1/§7-15「保息前提下多买 1/2 星压缩牌库」的序列面落地):
    # best 是**单序列贪心**(买+deploy 原子对竞争),deploy 配对的 delta 常年压过纯 bench 囤牌
    # → 放行面虽在(_compress_release),量进不了序列 —— r1 live 实证:5 张 1 费只买 2 张。
    # 修:best 确定后追加**纯 BuyCard 扫尾**(不参与 beat 竞争),逐张判息门+金+副本+容量,
    # 模拟递推保证金约束;骨架买分支(上方 return)是同类语义的强化版,不叠加。
    # ⚖️ 适用域 = **双轨期**(r1/r2 压缩是过渡阵容的牌库浓缩,§7-1);已 commit(定型)后
    # off-target 便宜牌属 spread,不扫(t97 语义:commit+shop 无 target → 不买,等 Refresh)。
    if _dual:
        try:
            _sim = state
            for _a in best:
                _sim = simulate(_sim, _a)
            for c in state.shop:
                _cost = card_cost(c)
                if c.name and c.name in {getattr(getattr(a, 'card', None), 'name', None) for a in best}:
                    continue   # best 已含的牌不重复买
                if _sim.gold < _cost:
                    continue
                if c.name:
                    # r68 review:扫尾副本计数分星 —— 商店牌恒 1★,3合1 材料须同名同星(主循环
                    # _star1 同口径);旧裸数名把 2★+ 也计入 → 假满副本误拦真材料(62 轮同族病复发)。
                    _copies = sum(1 for b in (*_sim.deployed, *_sim.bench)
                                  if b.char_id == c.name and b.star == 1)
                    if _copies >= 3:
                        continue   # 3合1 满副本(与主循环同门)
                    if c.name in {b.char_id for b in _sim.deployed if b.char_id} and _cost > 1:
                        continue   # 场上同名散牌不集(同主循环;1费例外集 2★)
                if _sim.deployed_count() >= _sim.max_units() and len(_sim.bench) >= BENCH_CAPACITY:
                    break   # 板+席满,买无所居
                if not _compress_release(_cost, _sim.gold, _hunt_tiers):
                    continue
                best.append(BuyCard(card=c))
                _sim = simulate(_sim, best[-1])
                log.info('[cw-plan] 压缩扫尾:+%s(cost%s,gold%s→%s,§7-15 牌库压缩)',
                         c.name, _cost, _sim.gold + _cost, _sim.gold)
        except Exception as _e:   # noqa: BLE001 扫尾 best-effort,失败保 best 原样
            log.info('[cw-plan] 压缩扫尾跳过:%s', _e)

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
    # 关时 gold/level/hp 参数被忽略走表,行为零变化)。ADR-0209 接线 2/6:
    # dual_track_phase=True(P1 双轨期)压 DP 升级姿态 → 攒息过渡。
    # intake #6:strategies 透传台账解(持卡 effect-aware DP)。
    _spend = get_node_goal(state.plane, state.round_num,
                           gold=state.gold, level=state.level, hp=state.hp,
                           committed=not state.dual_track_phase,
                           strategies=state.active_strategies or None).spend_mode
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
