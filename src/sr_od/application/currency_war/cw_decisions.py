# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

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
from sr_od.application.currency_war.cw_shop_odds import REFRESH_PROB

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_comps import Comp
from sr_od.application.currency_war.cw_comps import (
    AFFIX_MECHANIC_MAP,
    COMMIT_FRAC,
    COMP_LIBRARY,
    LevelGoal,
    clamp,
    form_progress,
    make_score_context,
    mechanics_fit,
    select_comp,
    target_committed,
)
from sr_od.application.currency_war.cw_state import (
    BENCH_CAPACITY,
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
    effective_hp_threshold,
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
# streak 经济(C 杠杆 2;fixture 核实 2026-08-11 结算「连胜×N」前缀=方向 → streak 接线):auto-chess
# 连胜/连败都给档位金(对称,取 magnitude;方向用于 plan 行为 —— 保连胜 vs fold,留 R2-4b)。
STREAK_WEIGHT: float = 2.0            # 每档 streak 的经济分(占位,阶段 6 实玩校准)
STREAK_CAP: int = 5                   # streak 经济封顶档(连胜/连败金一般 ≤5 档)
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
# T#97 step-2(tuned):target bonus **只加在 tier 部分**(_base_tier,不含 close-to-next),避免 over-rush 弱-early。
# 2026-08-07 live:1.5× on whole tier_score(含 close-to-next)→ over-rush 弱-early 追击(count 2 冲 tier 3)→ HP 掉快
TARGET_FACTION_BONUS: float = 1.5      # target 阵营 tier 部分 ×1.5(tier-only,close-to-next 不加;见 synergy_score)
CEILING_BONUS_FACTOR: float = 0.3      # 高 ceiling 阵营(count/max_tier)潜力项系数

# 默认升级金价(粗估,实机校准)
LEVEL_UP_COST_TABLE: dict[int, int] = {2: 4, 3: 10, 4: 18, 5: 30, 6: 36, 7: 48, 8: 60, 9: 70, 10: 84}
SHOP_REFRESH_COST: int = 2   # 刷新商店花费(粗估,实机校准)
REFRESH_SAMPLES: int = 8     # 蒙特卡洛 D 牌采样数(越大越准越慢)
MAX_REFRESH_PER_ROUND: int = 2   # 每回合最多主动刷新(D 牌)次数(防无限刷;review r5 修死代码)

# 人玩 auto-chess:跟 shop 走、concentrate(强化已 collect 阵营)、comp emerge。bot 旧「pre-select target→force」
# 在 deployed-lock + shop 随机下失败(target-buy 错配 → spread → 锁板 → 永不成型)。
REINFORCE_BONUS: float = 4.0      # 买 card.faction 已在 bench+deployed → 加分(深化集中阵营,~1 synergy 激活档)
SPREAD_PENALTY: float = 8.0       # 买新阵营 且 已 ≥DEPLOY_FACTION_CAP 阵营 → 重罚(防 spread-lock 永久占槽;>单卡 synergy 收益)
DEPLOY_FACTION_CAP: int = 3       # board 阵营数上限(L2 deploy cap 共用;deployed-lock 下超 = 永久 spread)

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
        # T#97 step-2(tuned):target bonus **只加在 _base_tier(tier 部分)**,不含 close-to-next —— 避免 over-rush
        _base_tier = cat_w * _activated_tiers(faction, count) ** SYNERGY_TIER_EXPONENT
        if target_factions:
            _base_tier *= TARGET_FACTION_BONUS if faction in target_factions else OFF_TARGET_DISCOUNT
        tier_score = _base_tier
        if _close_to_next(faction, count):
            tier_score += cat_w * CLOSE_TO_NEXT_TIER_BONUS   # close-to-next 不加 bonus(避免 rush 弱-early)
        mt = _max_tier(faction)
        if mt >= 6:
            tier_score += cat_w * (count / mt) * CEILING_BONUS_FACTOR
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


# ===== node_plan:节点×等级×动作节奏骨架(阵容无关;14 §2) =====
# plan() 读 NodeGoal.target_level 作等级 gate 地板(显式,胜 _expected_level 平滑曲线 —— 关键 inflection
# 更果断:P2 早推 7、2-5 推 8 搜核心、P3 推 9-10)。spend_mode 驱经济档位(allin 跳卖息 等)。danger_d 占位(卡 node_type 下节点识别,3.5.5;非 difficulty/hp_trend —— 二者已就绪)。
@dataclass
class NodeGoal:
    """某节点(位面-轮)的节奏目标(阵容无关骨架;comp 只换 level_plan/core_chars 参数;14 §2.0)。"""
    target_level: int           # 该节点目标等级(地板);plan level gate 显式 gate
    spend_mode: str             # saving/interest/level/hold/spend/allin/adaptive(§2.2 经济档位)
    action_focus: str = ""      # 描述辅(d_search/chase_star/rush_level;指导动作偏好,不直接驱评分)
    danger_d: bool = False      # A8 遭遇前战力不足 → 弃息 D 保血(🔴 前置 = 下节点 node_type 预判,3.5.5 blocked;difficulty/hp_trend 已就绪 —— effective_hp_threshold + PerformanceTracker。占位从未被读)


# 节点×等级×动作骨架表(14 §2.1;人玩节奏:前期攒息→中期升人口→后期 allin)。(plane, rmin, rmax) → NodeGoal。
# 目标等级比 _expected_level 平滑曲线**更果断**(关键 inflection 提前),驱动 bot 像人一样按节奏升。
# 值为 V4.4 先验(占位,阶段 6 实玩校准)。位面长度变(首领 1-7/1-8/1-9)用区间(rmax=9)兜。
_DEFAULT_NODE_PLAN: list[tuple[int, int, int, NodeGoal]] = [
    (1, 1, 3, NodeGoal(4, "saving", "rush_level")),    # P1 早期:冲 Lv4,纯升级 + 尽快向 50 金
    (1, 4, 6, NodeGoal(6, "interest", "d_search")),    # P1 中期:Lv6,攒 50 吃满息(息引擎)
    (1, 7, 9, NodeGoal(6, "hold")),                     # P1 后期/首领:锁血过 P1 首领
    (2, 1, 4, NodeGoal(7, "level", "d_search")),       # P2 早期:推 Lv7(升人口)
    (2, 5, 9, NodeGoal(8, "level", "d_search")),       # P2 中后期:2-5~2-7 升 8 搜核心
    (3, 1, 3, NodeGoal(9, "allin", "chase_star")),     # P3 早期:上 9 找 5 费
    (3, 4, 9, NodeGoal(10, "allin", "chase_star")),    # P3 后期/boss:上 10 + 关键卡追 3 星
]


def get_node_goal(plane: int, round_num: int) -> NodeGoal:
    """查 (plane, round) → NodeGoal(先匹配 _DEFAULT_NODE_PLAN 区间 → fallback;14 §2.0)。

    fallback(未匹配):target_level=_expected_level(round, plane)、spend_mode="adaptive"、
    action_focus="rush_level"。位面长度变(首领轮次不定)→ 区间兜;plane>3 / round>9 → fallback。
    """
    for p, rmin, rmax, goal in _DEFAULT_NODE_PLAN:
        if p == plane and rmin <= round_num <= rmax:
            return goal
    return NodeGoal(_expected_level(round_num, plane), "adaptive", "rush_level")


def economy_score(state: GameState, economy_mode: str) -> float:
    """经济健康度:利息(存金到 50)+ 等级合适度 + streak 档位金(C 杠杆 2)。

    economy_mode 只调利息项(rush_level 弱化守息、interest_first 强化守息),等级项不变。
    阶段保血(前期/低血 → 经济降权)由 evaluate 的 _phase_weights 统一处理(A3)。
    streak 取 magnitude(连胜/连败都给档位金,对称);fold(连败保息)已由 HP-gating 实现(02 R2-4b,用户 2026-08-12 确认:血量安全→fold/不安全→急救,经 _phase_weights/_refresh_cap HP gate);方向驱动剩「保连胜」半(连胜维持>吃息)待。
    """
    interest_tiers = min(state.gold // 10, INTEREST_THRESHOLD // 10)
    interest_val = interest_tiers * INTEREST_WEIGHT
    level_val = (state.level - _expected_level(state.round_num, state.plane)) * LEVEL_WEIGHT
    if economy_mode == "interest_first":
        interest_val *= 1.5
    elif economy_mode == "rush_level":
        interest_val *= 0.5
        level_val *= 1.5   # rush_level:等级项加权(抢升语义 —— 落后等级更痛、领先更值),不只弱化守息
    # streak 档位金(C 杠杆 2;fixture 核实后接线 2026-08-11):state.streak 带符号,magnitude 对称计。
    streak_val = min(abs(state.streak or 0), STREAK_CAP) * STREAK_WEIGHT
    return interest_val + level_val + streak_val


def char_quality_score(state: GameState, character_priority: list[str]) -> float:
    """角色质量分:character_priority 角色 × 星级(bench + 已上阵 deployed)。"""
    score = 0.0
    for bc in (*state.bench, *state.deployed):
        if bc.char_id in character_priority:
            score += CHAR_PRIORITY_BONUS * bc.star
    return score


HP_DANGER: int = 40   # 保血触发阈值默认(hp 低于此 → 弃息保血)。A8 高难调高经 effective_hp_threshold(state,config)(D-32/3.5.1 已接,live-verified)。


def _phase_weights(plane: int, hp: int, hp_threshold: int = HP_DANGER) -> tuple[float, float, float]:
    """阶段键控权重 (synergy, economy, char)。A3 + review agent 经济学校准。

    **2026-08-03 修正(review agent + 用户)**:前期 economy **不该压低** —— 利息越早到 5 档(50 金)
    越好,经济滚雪球。原 "plane1 → economy 0.4" 把"前期"和"保血"混淆了。修正:
    - **HP 危险(hp<HP_DANGER):保血** —— 任何位面,弃息提质量(战力/角色加权、经济降权)。
    - **plane3(后期):锁血** —— 全力战力/星级(打 boss)。
    - **其余(健康):平衡 (1,1,1)** —— economy 不压低,可 snowball 到 50。

    A8 difficulty 已接(effective_hp_threshold,3.5.1/D-32 live-verified);win_streak 待补(连胜中保连胜>吃息,需 read_streak 方向 —— 结算源已接 session.last_streak,plan 消费端待 R2-4b)。
    """
    if hp < hp_threshold:
        return (1.2, 0.4, 1.2)   # 保血:战力/角色优先,经济降权(任何位面 HP 危险)
    if plane == 3:
        return (1.3, 0.3, 1.3)   # 锁血:全力战力/星级(plane3 boss 战)
    return (1.0, 1.0, 1.0)       # 健康:平衡(economy 不压低,snowball 到 50)


def _refresh_cap(state: GameState, hp_threshold: int = HP_DANGER) -> int:
    """本回合 D 牌(刷新)上限(动态;review agent + 用户:固定 2 太死)。

    关键回合放宽:升 8 后 / plane3 搜核心、HP 危险锁血急救。
    待补:拿刷新减费策略(砂里淘金/加油站)→ 6;需 GameState.active_strategies 字段(电表倒转)。
    """
    cap = MAX_REFRESH_PER_ROUND          # 基线 2
    if state.plane == 3 or state.level >= 8:
        cap = max(cap, 4)                # 升 8 后 / plane3:搜核心多刷
    if state.hp < hp_threshold:
        cap = max(cap, 4)                # 锁血急救:多刷找质量
    return cap


def _economy_mode_for(state: GameState, config) -> str:
    """node spend_mode → economy_score 档位(14 §2.2;NodeGoal.spend_mode 主,config.economy_mode 辅)。

    spend_mode 是节点节奏 gate,驱动 economy_score 利息/等级相对权重:
    - saving/interest → interest_first(攒息 snowball;P1 早期主目标尽快 50 金)
    - level → rush_level(弱化守息 + 强化等级;P2 升人口)
    - hold/allin/spend → adaptive(economy-low 由 _phase_weights plane3 we=0.3 处理,非此处)
    - adaptive → config.economy_mode 用户偏好辅

    与 _phase_weights 正交:本函数调 economy_score 内部(利息/等级相对权重),
    _phase_weights 调 economy_score 的 outer 乘子 we(HP/plane)。两者复合不双计。
    """
    _spend = get_node_goal(state.plane, state.round_num).spend_mode
    if _spend in ("saving", "interest"):
        return "interest_first"
    if _spend == "level":
        return "rush_level"
    if _spend == "adaptive":
        return getattr(config, 'economy_mode', 'adaptive')
    return "adaptive"   # hold/allin/spend → neutral


def evaluate(state: GameState, config, faction_priority: list[str],
             target_comp: Comp | None = None) -> float:
    """局面总分(越高越好)= 阶段键控加权的(羁绊 + 经济 + 角色质量)+ 承诺-期权混合项。

    承诺-期权(F-3 / ADR 0096,2026-08-11 接线 ``α·commit + (1−α)·optionality``):
    - **commit 项**(target_comp 给定):``BENCH_TARGET``(持有 target 牌,**始终奖励** —— 早期也要攒核心件)
      + ``α·target_progress``(成型压力,早弱晚强:早期未成型是正常的,不该重罚;晚期必须成型 → 罚强)。
    - **optionality 项**(灵活期权):``(1−α)·optionality_score`` —— 早(α 小)保期权(bench 上属 ≥2 comp
      的通用角色),晚(α 大)让位 commit。optionality 与 commit 正交(ADR 0096:不同决策,不矛盾)。
    target_comp=None(reactive)→ commit 项归零,只剩 optionality(早期灵活)+ 基础分(A3 向后兼容)。
    core_chars 持有不在此重复计分(char_quality 已覆盖用户 character_priority)。
    """
    ws, we, wc = _phase_weights(state.plane, state.hp,
                                effective_hp_threshold(state, config))
    score = (
        ws * synergy_score(state, faction_priority, target_comp)
        + we * economy_score(state, _economy_mode_for(state, config))   # spend_mode→economy(§2.2;ADR-0102)
        + wc * char_quality_score(state, getattr(config, 'character_priority', []))
    )
    alpha = alpha_t(state)
    if target_comp is not None:
        # 成型压力(剩余进度罚)随 α:早期未成型不该重罚,晚期必须成型 → 罚强(F-3 commit 项)。
        score -= alpha * TARGET_PROGRESS_WEIGHT * _target_progress_remaining(state, target_comp)
        # BENCH_TARGET 不随 α 缩:持有 target 牌始终奖励(早期也要攒核心件;board 满→买 target 到 bench→
        # delta>0→bot 买→level up 后 deploy→target 深堆)。delta 中 phantom bench 抵消(plan greedy 消,净 delta 正确)。
        _bench_tgt = sum(1 for bc in state.bench
                         if bc.faction in target_comp.factions or bc.char_id in target_comp.core_chars)
        score += BENCH_TARGET_WEIGHT * _bench_tgt
    # optionality(灵活期权,F-3):早期(α 小)保 ≥2 comp 通用角色,晚期(α→1)让位 commit。
    # 即使 reactive(target=None)也奖 —— 未 commit 时更该保灵活(通用角色随时可并入将来 target)。
    score += (1.0 - alpha) * OPTIONALITY_WEIGHT * optionality_score(state)
    # 过渡羁绊(P1 保血基础设施,review round-4 HIGH-2):早期凑能打伤害的羁绊(仙舟/狼狩/dot/列车/贝洛伯格)
    # 稳血到成型(限时 AV 下前期有输出不超时);fades as commit(α→1)。board 阵营数 OCR → 真信号现成。
    score += (1.0 - alpha) * transition_tempo_score(state)
    return score


# target 成型剩余进度权重(战略层导向;占位,待实玩校准)。越大 → 越 commit 到 target。
TARGET_PROGRESS_WEIGHT: float = 15.0
BENCH_TARGET_WEIGHT: float = 3.0   # D-11 二次回退(2026-08-09 A/B 负):=8 局板更散(无 tier-2)、p2 hp3 < baseline hp16。
# 结论:buy hoard(BENCH_TARGET_WEIGHT)单杠杆不治 p2 死 —— bot 能激进买(7 张/轮),非 buy-quantity 限;
# 板散是 comp 选择/pivot + deploy 集中度问题,非 buy 权重。p2 死需更深工作(holistic 板强 / 接受 tier-2 靠星级装备)。
# =3 为 D-6 时期值,保留。D-11 两次试(=8)两次回退,确认非杠杆。


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
    if target_comp is not None and (
            card.faction in target_comp.factions or card.name in target_comp.core_chars):
        return 0.0
    if len(factions) >= DEPLOY_FACTION_CAP:
        return -SPREAD_PENALTY
    return 0.0


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
    if target is not None and (bc.faction in target.factions or bc.char_id in target.core_chars):
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
        s.shop = _sample_shop(after_cost, faction_priority, rng, target_comp=target_comp)
        deltas.append(_best_buy_deploy_eval(s, config, faction_priority, target_comp) - base_eval)
    return sum(deltas) / len(deltas) if deltas else 0.0


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
    if target is None and not reactive:
        _candidates = select_comp(cur, make_score_context(cur), config)
        if _candidates:
            target = _candidates[0]

    # —— level_plan 硬 gate(task#18 经济统一论核心):level_plan 说 level_up + 够钱 → 升级(1 级/轮)——
    # 根因(replay 32 局「升 0 次」):贪心 eval 对「花大金升级」的利息损失短视 —— LevelUp 候选 delta 永负
    # (花 48 金 → 利息档 5→0 损 -20,level_val 仅 +6)→ 永不选中 → bot 卡 lv5-6 → 弱 comp → plane2 死。
    # level_plan 是**花费指令**非建议:说 level_up + afford → 执行,信任计划而非短视 eval。tempo 破息在所
    # 不惜(升级解锁高费刷新率 + 出战位 = 关键长期投资)。每轮最多 1 级(自然节流,防一轮烧光金)。
    _goal = _resolve_level_goal(cur, target)
    _lv_cost = LEVEL_UP_COST_TABLE.get(cur.level + 1, 70)
    # 升级条件:够钱 + (level_plan 说 level_up **或** 落后期望等级 `_expected_level`)。
    # → 永远到不了 5+(level_up 等级)→ 卡低等级 → telemetry 6 局全「升0次」(gold 到 74 也不升)。
    # 「落后期望等级」兜底:不管 goal,等级跟不上节奏 + 够钱 → 升(经济统一论:落后该升)。每轮 ≤1 级。
    # node_plan(14 §2):目标等级用 NodeGoal.target_level(节点级,关键 inflection 更果断)替 _expected_level 曲线。
    _target_lv = get_node_goal(cur.plane, cur.round_num).target_level
    if (cur.level < 10 and cur.gold >= _lv_cost
            and ((_goal is not None and _goal.action == "level_up") or cur.level < _target_lv)):
        actions.append(LevelUp(cost=_lv_cost))
        cur = simulate(cur, actions[-1])

    # —— 贪心:反复选 eval 提升最大的动作序列(含 D 牌蒙特卡洛),直到无正提升 ——
    base_eval = evaluate(cur, config, faction_priority, target)
    for _ in range(15):
        refresh_used = sum(1 for a in actions if isinstance(a, RefreshShop))
        step = _best_improving_action(cur, config, faction_priority, base_eval, rng,
                                      refresh_budget=_refresh_cap(cur, effective_hp_threshold(cur, config)) - refresh_used,
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

    _goal = _resolve_level_goal(state, target_comp)
    _lv_cost = LEVEL_UP_COST_TABLE.get(state.level + 1, 70)         # 升下一级金价
    # 想升 + 还没够钱 → 抑制散牌买/刷,攒金。否则 gate 永远付不起(bot 花光金不攒,lv4 gold12 实测)。
    # node_plan(14 §2):目标等级用 NodeGoal.target_level(节点级)替 _expected_level 曲线。
    _want_level = (state.level < 10 and (
        (_goal is not None and _goal.action == "level_up")
        or state.level < get_node_goal(state.plane, state.round_num).target_level))
    _saving_for_level = _want_level and state.gold < _lv_cost
    # D-14(2026-08-09,4th 自审 + 经济诊断):_saving_for_level **不再**被 _board_strong 门控。
    # 旧门控(板弱 form_progress<COMMIT_FRAC → 不攒级 → 花买/刷)致 chicken-egg:tier-2 弱板→不攒级→永不升→
    # 卡 lv6 cap→上不了更多单位→永 tier-2→p2 死。**升级是 tempo 投资**(提 cap + shop 高费刷新率),任何板都该追。
    # _saving_for_level 抑制 off-target 买 + refresh(浪费金),留 target 买(建 comp)+ 攒金 → 够 cost 下轮 plan
    # level gate(优先执行)升级。**_saving_for_interest 仍由 _board_strong 门控**(息是经济,板强才囤,弱板不囤息)。
    _board_strong = (target_comp is not None and form_progress(target_comp, state) >= COMMIT_FRAC)
    # → 攒息。CLAUDE.md「维持≥50 金,超出才花;tempo(HP 危险/战力断档)破息」(战力断档=板弱,非仅板位不满)。
    _saving_for_interest = (state.gold < INTEREST_THRESHOLD
                            and state.deployed_count() >= state.max_units()
                            and state.hp >= effective_hp_threshold(state, config)
                            and _board_strong)
    _saving = _saving_for_level or _saving_for_interest

    # 1) 买 + 上任组合(原子)
    for card in state.shop:
        cost = card_cost(card)
        if state.gold < cost:
            continue
        # 备战席)。买+deploy 原子:deploy 有位则买的牌上任(bench 不增);deploy 满则落 bench → bench 满才 skip。
        if state.deployed_count() >= state.max_units() and len(state.bench) >= BENCH_CAPACITY:
            continue
        # level_plan buying gate(task#18):攒金升级期间(_saving)抑制散牌,但仍允许 target
        # 阵营/core/优先角色牌(深化 target 值得花,且不该被攒金阻塞)。升级本身由 plan() 硬 gate 执行,
        # 这里只管"攒金期间别把金泄到散牌上"(解 replay 32 局金堆 50+ 不花/花在散牌上不升级)。
        if _saving:
            _is_target_card = (target_comp is not None and (
                card.faction in target_comp.factions
                or card.name in target_comp.core_chars
                or card.name in character_priority))
            if not _is_target_card:
                continue   # 散牌:攒金给升级,跳过
        # commitment prefilter(task#16):target 设定时,若 shop 有 target 卡(阵营∈target.factions 或
        # ∈core_chars)可买,跳过纯 off-target 散牌(阵营∉target 且非 core_char)→ 聚焦深化 target,
        # 防"买一切"致 board 散、comp 永不深堆(plane2 comp-strength 墙根因)。shop 无 target 卡时不跳(防
        # hold-forever 饿死)。区别旧 OFF_TARGET_DISCOUNT 打折 board 的 churn(d87b2a68 revert):只 gate 新 buys。
        # → 藿藿/阿格莱雅 等 priority 列里的 off-target 角色被放行 → board spread;plane1-9 实采 7 阵营零成型、
        # gold=8 买 能量 藿藿/阿格莱雅 填 off-target)。违反「一切评分 comp 相关」(CLAUDE.md):priority 不该
        # 绝对豁免 commitment。priority 仍享 eval 加成(CHAR_PRIORITY_BONUS,下文)+ 未 commit 时(target=None)
        # 本 prefilter 不跑 → 早期 stopgap 保留。
        if target_comp is not None:
            _is_offtarget = (card.faction not in target_comp.factions
                             and card.name not in target_comp.core_chars)
            if _is_offtarget:
                # shop 有买得起的 target 卡 → 跳 off-target(聚焦深化 target;task#16)。
                # T#97:**已 commit** 也跳(commit 后买散牌 = spread 根因 → 该 Refresh 找 target / 攒金;
                # drought bail 处理真不可达 target)。仅「非 commit + shop 无 target」放行 = 早期 tempo。
                _shop_has_buyable_tgt = any(
                    c.faction in target_comp.factions or c.name in target_comp.core_chars
                    for c in state.shop if state.gold >= card_cost(c))
                if _shop_has_buyable_tgt or target_committed(target_comp, state):
                    continue
        after_buy = simulate(state, BuyCard(card=card))
        seq = [BuyCard(card=card)]
        if (after_buy.deployed_count() < after_buy.max_units() and after_buy.bench
                and _should_deploy(after_buy.bench[-1], after_buy, target_comp)):
            bc = after_buy.bench[-1]
            row, ok = _pick_deploy_row(after_buy, bc)
            if ok:
                seq.append(DeployMove(bench_idx=len(after_buy.bench) - 1, to_row=row, faction=bc.faction))
        after = after_buy
        for a in seq[1:]:
            after = simulate(after, a)
        delta = evaluate(after, config, faction_priority, target_comp) - base_eval
        delta += _concentration_delta(card, state, target_comp)
        if card.name and card.name in character_priority:
            delta += CHAR_PRIORITY_BONUS * 2
        beat(delta, seq)

    # 2) 上任已拥有的 bench 角色(按 position_pref 分流)
    for i, bc in enumerate(state.bench):
        if state.deployed_count() >= state.max_units():
            break
        if not _should_deploy(bc, state, target_comp):
            continue
        row, ok = _pick_deploy_row(state, bc)
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
        c.faction in target_comp.factions or c.name in target_comp.core_chars
        for c in state.shop))
    # simulate(RefreshShop) 不建模换 shop(只扣金、shop 不变)→ 贪心误以为「Refresh 后还能买当前 shop 的 target」,
    # 故 plan 选 Refresh 作第一动作;但实跑 Refresh 换 shop → target 卡(追击×3)全没 → 只能买 off-target → spread。
    # 规则:auto-chess 基本功 —— target 卡在场且买得起 = 确定收益,Refresh 找 target 是赌注(蒙特卡洛乐观);
    # 取确定不取赌。买完所有买得起的 target(本字段转 False)才 Refresh 找更多。
    _shop_has_buyable_target = (target_comp is not None and any(
        c.faction in target_comp.factions or c.name in target_comp.core_chars
        for c in state.shop if state.gold >= card_cost(c)))
    # (3/3 局 survive plane1 但 comp count=1 不深 → plane2 秒死;策略子agent P3)。
    _roll_for_target = (target_comp is not None
                        and target_committed(target_comp, state)
                        and not any(state.board.get(f, 0) >= 2 for f in target_comp.factions))
    if (state.gold >= SHOP_REFRESH_COST and refresh_budget > 0
            and not _shop_has_buyable_target
            and (not _saving_for_level or not _shop_has_target)
            and not (_saving_for_interest and not _roll_for_target)):
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
    # node_plan(14 §2.2):节点 spend_mode 花光成型(allin,P3)/ 升人口(level,P2)/ 抢升(rush_level)
    # 档位不囤息(卖息与节奏相悖)。⚠️ 本函数是 spend_mode 的**动作消费者**(allin/level → 跳卖息动作);
    # 另一消费者 ``_economy_mode_for``(ADR-0102)是**评分消费者**(spend_mode → economy_mode 映射,调
    # economy_score 利息/等级相对权重)。两者刻意不同映射:本函数挡「卖息凑档」动作(allin/level 不该囤息),
    # _economy_mode_for 调经济评分相对权重(level→rush_level / allin→adaptive neutral,economy-low 由
    # _phase_weights plane3 we=0.3 处理)—— 语义不同,勿强行统一(审计 round-17 borderline#2)。
    _econ = getattr(config, 'economy_mode', 'adaptive')
    _spend = get_node_goal(state.plane, state.round_num).spend_mode
    if _econ == "rush_level" or _spend in ("allin", "level"):
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


# ===== 事件 =====
# decide_boss_priority(阵营降权)已删(2026-08-12):boss 克制是 comp-vs-boss 机制级(走 boss_fit/
# comp.countered_by_bosses + task#73 机制建模),非阵营级。原 faction 降权是错模型 + 从不派发的死代码。

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


# ===== 遭遇节点(decide_encounter,design 08;✅ 已接 HandleEncounter:55 + read_encounter_options)=====

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
    """遭遇节点选难度档 + 是否刷新(纯逻辑,design 08)。✅ 已接:``HandleEncounter``(L55 调本函数)+
    ``read_encounter_options``(cw_node_obs,OCR 卡标题「遭遇其X」→ difficulty)。affix 分支 N/A
    (选项 UI 不显词缀,战后才显)。原 docstring「handler 待阶段5 接」过期(2026-08-12 代码核实已接)。

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


# ===== 补给节点(decide_supply,design 07/08;✅ 已接 run_supply_node:56 + read_supply_options)=====

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
    """补给节点选装备 + 是否刷新(纯逻辑,design 07/08)。✅ 已接:``run_supply_node``:56 调本函数 +
    ``read_supply_options``(cw_node_obs,OCR 每列角色+装备)。原「handler 待阶段5 接」过期(2026-08-12 核实)。

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


# ===== 巨星节点(decide_megastar;✅ 已派发 run_megastar_node:75,按 target.core_chars 选;⚠️ 候选 char_id OCR 限时 fallback idx0)=====

@dataclass
class MegastarOption:
    """一个巨星候选(OCR/SIFT 读角色名,``read_megastar`` 阶段5;/§11.3.4⑥)。

    char_id:候选角色名(空 = OCR 未就绪,匹配恒失败 → 默认 idx=0 = 今天盲点左候选)。
    """
    idx: int
    char_id: str = ""


@dataclass
class MegastarPick:
    """decide_megastar 返回:选第几个候选 + 原因。"""
    idx: int
    reason: str = ""


# ===== 选择伙伴节点(decide_partner;✅ 已派发 handle_select_partner:96,T#99;⚠️ 候选只立绘 char_id=label→多 idx0,真接需 SIFT 立绘)=====

@dataclass
class PartnerOption:
    """一个伙伴候选(OCR/SIFT 读角色名,``read_partner`` 阶段5;/§11.3.4⑦)。

    char_id:候选角色名(空 = OCR 未就绪 → 默认 idx=0 = 今天盲点 stage 立绘)。
    """
    idx: int
    char_id: str = ""


@dataclass
class PartnerPick:
    """decide_partner 返回:选第几个候选 + 原因。"""
    idx: int
    reason: str = ""


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


# 过渡羁绊(P1 能打伤害的羁绊,前期凑出保血;review round-4 HIGH-2;comps/README「开局过渡分级」人上人级)。
# 限时 AV 下前期靠这些羁绊组合稳血到成型(DOT 慢热 P1 弱死根因之一 = 无过渡羁绊支撑)。
# 全局过渡基础设施(非 per-comp):任何 comp 的 P1 都可拿这些羁绊 tempo。
TRANSITION_FACTIONS: set[str] = {'仙舟', '狼狩', '持续伤害', '列车同行', '贝洛伯格'}
TRANSITION_TEMPO_BONUS: float = 3.0   # 每凑出(≥2)的过渡羁绊的早期保血分(占位,阶段 6 校准)


def transition_tempo_score(state: GameState) -> float:
    """P1 过渡羁绊分(review round-4 HIGH-2):board 凑出(≥2)能打伤害的过渡羁绊 → 早期保血(限时 AV 不超时)。

    人上人级 = 2 个能打伤害羁绊组合(仙舟/狼狩/dot/列车/贝洛伯格),稳血到成型。最多奖 2 个(更多边际
    递减);与 optionality 同(1−α)早期强调 —— 早期保期权/过渡,fades as commit(α→1)让位 target。
    board 阵营数 OCR 读 → 真信号现成。**非与 synergy 双重堆**:只奖过渡羁绊(早期 tempo),flat-per-羁绊。
    """
    n = sum(1 for f in TRANSITION_FACTIONS if state.board.get(f, 0) >= 2)
    return min(n, 2) * TRANSITION_TEMPO_BONUS
