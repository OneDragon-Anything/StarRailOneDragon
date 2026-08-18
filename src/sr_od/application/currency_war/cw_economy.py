# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)
"""货币战争 经济 / 等级 / 节奏骨架模型(纯函数:金 / 经验 / 息 / 刷新成本,ADR-0131 EconomyEffect 消费 + 0129 单击经验模型 + 0142 重复性效果折算;node_plan 节点×等级节奏骨架,14 §2 —— 三层共享底层,economy/evaluate/plan 均消费)。

自 cw_decisions.py 一次性拆分而来(ADR-0145;纯移动零行为变化,函数名/签名不变)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_comps import (
    LevelGoal,
)
from sr_od.application.currency_war.cw_factions import (
    INTEREST_THRESHOLD,
)
from sr_od.application.currency_war.cw_investments import (
    EconomyEffect,
    aggregate_economy,
)
from sr_od.application.currency_war.cw_state import (
    XP_CLICK_COST_FALLBACK,
    XP_PER_BUY,
    XP_TO_NEXT_LEVEL,
    GameState,
    effective_hp_threshold,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_comps import Comp

INTEREST_WEIGHT: float = 4.0          # 每档(10金)利息的分。2026-08-04 提权(2→4):bot 不攒金 → 升不起级

# (gold 0-15 < 升级 cost 36-48)→ 卡低 level → 弱 comp。原 2.0:息 delta(50vs0)=10 = 牌 synergy 10 → bot
# 无差别→买不攒。提 4.0:息 delta=20 > 牌 synergy 10 → bot 攒到 50(息引擎)+ 花超额买/升级 = 经济统一论。
# streak 经济(C 杠杆 2;fixture 核实 2026-08-11 结算「连胜×N」前缀=方向 → streak 接线):auto-chess
# 连胜/连败都给档位金(对称,取 magnitude;方向用于 plan 行为 —— 保连胜 vs fold,留 R2-4b)。
STREAK_WEIGHT: float = 2.0            # 每档 streak 的经济分(占位,阶段 6 实玩校准)

STREAK_CAP: int = 5                   # streak 经济封顶档(连胜/连败金一般 ≤5 档)

# C 杠杆 3 winning half(R2-4b;14 §连胜中「2 胜+」):连胜 ≥ 此 → 破息花钱提质量维持连胜(断连胜亏 > 利息亏)。
# streak 带符号(连胜 + / 连败 −,结算源 session.last_streak 方向可靠);连败 fold 半已由 HP-gating 覆盖(02 R2-4b)。
WIN_STREAK_BREAK_INTEREST: int = 2    # auto-chess 连胜金 2 连起档(2 连=1 金、3 连=2 金…),故阈值=2

LEVEL_WEIGHT: float = 6.0             # 每级(相对期望)的分。2026-08-04 提权(3→6):bot 不升等级


# —— 购买经验决策 helper(ADR-0129;机制常量 XP_TO_NEXT_LEVEL/XP_PER_BUY 在 cw_state 单一源)——
def _strategy_economy(state: GameState) -> EconomyEffect:
    """当前持有投资策略的聚合经济效果(ADR-0131;active_strategies → 数值效果,策略层算账)。"""
    return aggregate_economy(state.active_strategies)



def _refresh_cost(state: GameState, refresh_used: int) -> int:
    """第 refresh_used+1 次刷新的真实花金(ADR-0131):策略免费额度(如 加油站 每节点 1 次)内 = 0。"""
    if refresh_used < _strategy_economy(state).free_refresh_per_node:
        return 0
    return SHOP_REFRESH_COST



def xp_click_cost(state: GameState) -> int:
    """一次「购买经验」单击花金(state.level_up_cost OCR 实读优先;缺 → XP_CLICK_COST_FALLBACK;
    商业间谍类 xp_buy_cost_discount 再减;ADR-0131)。"""
    base = state.level_up_cost if state.level_up_cost else XP_CLICK_COST_FALLBACK
    return max(0, base - _strategy_economy(state).xp_buy_cost_discount)



def clicks_to_next_level(state: GameState) -> int:
    """从当前 XP 到升 1 级还需的单击次数(xp 未知按 0 进度向上取整;满级返 0)。"""
    if state.level >= 10:
        return 0
    if state.xp_progress:
        cur, need = state.xp_progress
    else:
        cur, need = 0, XP_TO_NEXT_LEVEL.get(state.level, 4)
    return max(0, -(-(need - cur) // XP_PER_BUY))



def _want_level_up(state: GameState, target_comp: Comp | None) -> bool:
    """是否处于「该买经验」期:comp level_goal 说 level_up,或落后 NodeGoal.target_level 地板。

    ADR-0128(用户节奏 §7-7「不无脑停概率最高级,也不无脑推级」):comp 对**当前级**显式给了
    roll/stable(= 停留本级 D 核心)→ comp 停留意图压过 node 地板 —— 钱该花在 D 牌不是经验;
    未给(走通用曲线)才按 node 地板推。例:列车同行 lv7 roll 3星姬子(攻略 列车:53)→ 不推 8。
    ADR-0149 评审R3(用户 §7-12「连50金都没凑到,为什么要急着升级?」):P1 金 < INTEREST_THRESHOLD
    非boss/非锁血 → 不追级 —— 息引擎未立时追级 = 挤占买牌本金(M22 r7-r9 实证金≤35 全程追级
    零息)。boss/锁血节点豁免(节奏窗口 > 息纪律)。
    """
    if state.level >= 10:
        return False
    # ADR-0149 P1 追级抑制(评审R3):息引擎未立**不追级**(金<INTEREST_THRESHOLD 时不再攒金
    # 买经验 —— M22 r7-r9 金≤35 全程追级零息病理)。⚠️ 语义边界(M31 实证修正):只拦「攒金
    # 追级」(金 < 单击价+10 = 连一次有效点击都做不了还想攒),**金够单击+保命地板(10)放行** ——
    # 升级本身是人口投资,金 12-14 点一次 XP 是正确节奏非泄金(M31 死因:旧 +20 地板把 lv4
    # 卡到 P2)。lv<5 不拦(开场人口等级);boss/锁血豁免。
    if (state.plane == 1 and state.level >= 5
            and state.gold < INTEREST_THRESHOLD
            and state.node_type not in ('boss',) and state.hp >= 30):
        _click_cost = 4 + state.level   # xp_click_cost 简算(lv5=9/格)
        if state.gold < _click_cost + 10:
            return False
    if target_comp is not None:
        _own = target_comp.level_plan.get(state.level)
        if _own is not None:
            if _own.action == 'level_up':
                return True
            if _own.action in ('roll', 'stable'):
                # r11 review #3:P2+ node 地板是**硬下限**(P2 敌强度跳升,人口不升=硬吃两仗,
                # M55 P2 冻 lv6 实证)——comp 停留意图只在 P1 压地板;P2+ 落后地板即追级
                # (停留 roll 可在追上地板后继续)。
                return bool(state.plane >= 2 and state.level < get_node_goal(
                    state.plane, state.round_num,
                    gold=state.gold, level=state.level, hp=state.hp).target_level)
    goal = _resolve_level_goal(state, target_comp)
    if goal is not None and goal.action == 'level_up':
        return True
    return state.level < get_node_goal(state.plane, state.round_num,
                                       gold=state.gold, level=state.level,
                                       hp=state.hp).target_level



def _xp_gold_floor(state: GameState, want_level: bool) -> int:
    """买经验时的存金地板(用户节奏 economy_research §7;**玩法理解**: gameplay/currency_war.md 策略模型 S1)。

    非追级期(已到核心概率等级、goal 说 roll/stable)→ 50(攒息,零花才点经验);
    追级期 → 20(「偶尔掉到 40/30」精神,保守取 20);HP 危险 → 10(保血优先)。
    r24 位面末修正:A8 下 P1-r9 血量恒在危险带(六局实证 15-49<阈值)→ 地板恒 10
    → boss 前花光 → P2 进场赤贫(gold 5-28,零搜牌窗口,成型无从谈起)。位面末
    回合(round_num≥8,P1/P2 过半位面)保 **20**(P2 首回合一级利息档 + 搜牌本钱);
    hp<30 真濒死仍 10(保命绝对优先)。
    """
    if state.hp < 30:
        return 10
    if state.round_num >= 8:
        return 20   # r24:位面末保本钱进下一位面(非 hp 危险分支的 10)
    if state.hp < effective_hp_threshold(state):
        return 10
    return 20 if want_level else INTEREST_THRESHOLD

SHOP_REFRESH_COST: int = 2   # 刷新商店花费(粗估,实机校准)


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
    # 2026-08-15 live 校准(ADR-0126):M8(lv9 aggressive)唯一破 2-7 进位面 3;lv6@1-9 boss 稳定 -34~-40 HP,
    # 进位面 2 即死(M9/M10/M11 全灭于 2-1/2-2)。A8 敌难度 108 要求更高人口 —— P1 后期也推 7,P2 提前上 8。
    (1, 1, 3, NodeGoal(4, "saving", "rush_level")),    # P1 早期:冲 Lv4,纯升级 + 尽快向 50 金
    (1, 4, 6, NodeGoal(6, "interest", "d_search")),    # P1 中期:Lv6,攒 50 吃满息(息引擎)
    (1, 7, 9, NodeGoal(7, "hold", "rush_level")),      # P1 后期/首领:lv7 保血过 P1 首领(live:-34HP@lv6 → 升人口)
    (2, 1, 4, NodeGoal(8, "level", "d_search")),       # P2 早期:直接推 Lv8(live:lv7 进 P2 仍 2-1/2-2 死)
    (2, 5, 9, NodeGoal(8, "level", "d_search")),       # P2 中后期:lv8(review H4 软化:M8 lv9 锚点疑幽灵,收入模型不支持 9)
    (3, 1, 3, NodeGoal(9, "allin", "chase_star")),     # P3 早期:上 9 找 5 费
    (3, 4, 9, NodeGoal(10, "allin", "chase_star")),    # P3 后期/boss:上 10 + 关键卡追 3 星
]



def get_node_goal(plane: int, round_num: int, *,
                  gold: int | None = None, level: int | None = None, hp: int | None = None,
                  committed: bool = True) -> NodeGoal:
    """查 (plane, round) → NodeGoal(先匹配 _DEFAULT_NODE_PLAN 区间 → fallback;14 §2.0)。

    fallback(未匹配):target_level=_expected_level(round, plane)、spend_mode="adaptive"、
    action_focus="rush_level"。位面长度变(首领轮次不定)→ 区间兜;plane>3 / round>9 → fallback。

    **影子模式(ADR-0155,日程 DP 接缝)**:``HORIZON_SEAM_ACTIVE=True`` 且传全 (gold, level, hp)
    → 姿态查 ``cw_horizon`` 解(满息/追级/D 预算从剩余日程 DP 涌现,03 号重设计);表 = 回退。
    默认 False(表生效)—— 切流待实机 A/B(V5);消费端签名零改(全关键字参)。
    ADR-0209(接线 2/6):committed=False(双轨期)→ DP 升级姿态被压(P1 攒息过渡)。
    """
    if HORIZON_SEAM_ACTIVE:
        _partial = (gold, level, hp)
        if any(v is not None for v in _partial) and None in _partial:
            log.debug('[cw-seam] get_node_goal 部分传参(%s)→ 走表;迁移漏点排查',
                      ('g' if gold is not None else '-') + ('l' if level is not None else '-')
                      + ('h' if hp is not None else '-'))
        if None not in (gold, level, hp):
            from sr_od.application.currency_war.cw_horizon import _horizon_node_goal
            _goal = _horizon_node_goal(plane, round_num, gold, level, hp, committed=committed)   # type: ignore[arg-type]
            if _goal is not None:
                return _goal
    for p, rmin, rmax, goal in _DEFAULT_NODE_PLAN:
        if p == plane and rmin <= round_num <= rmax:
            return goal
    return NodeGoal(_expected_level(round_num, plane), "adaptive", "rush_level")


# ADR-0155:日程 DP(cw_horizon)→ NodeGoal 接缝开关。False = 区间表(现状栈)生效;
# True 且调用方传全状态 → DP 姿态。
# ✅ **切流执行(2026-08-18 r16,ADR-0208)**:六连败证据链完备——①160 局对拍
# 「表 hold→DP level」在 P1 高金段系统性分歧(节奏慢一档);②六局 P1 boss 稳定损
# 20-36 血→P2 残血开局即崩;③r8 经济投入已尽力(强度差距根子在 P1 全程积累);
# ④DP 姿态语义逐段核验(早升/先成型后冲 8)。目标授权自主推进。回滚 = 本行改 False。
HORIZON_SEAM_ACTIVE: bool = True



def economy_score(state: GameState, economy_mode: str) -> float:
    """经济健康度:利息(存金到 50)+ 等级合适度 + streak 档位金(C 杠杆 2)。

    economy_mode 只调利息项(rush_level 弱化守息、interest_first 强化守息),等级项不变。
    阶段保血(前期/低血 → 经济降权)由 evaluate 的 _phase_weights 统一处理(A3)。
    streak 取 magnitude(连胜/连败都给档位金,对称);fold(连败保息)已由 HP-gating 实现(02 R2-4b,用户 2026-08-12 确认:血量安全→fold/不安全→急救,经 _phase_weights/_refresh_cap HP gate);方向驱动「保连胜」半(连胜维持>吃息)已接 plan:``_should_save_for_interest`` 连胜≥``WIN_STREAK_BREAK_INTEREST`` 破息(C 杠杆 3,R2-4b)。
    """
    # ADR-0131(投资策略效果进经济分):利息上限覆写(开源节流 9 档/利息上调 10 档/买断制 0)+
    # 每节点固定给金(定期福利 2/节点 ≈ 白拿 0.2 档息)+ 连胜奖励倍率(伟大征服 ×3 → streak 更值)。
    _se = _strategy_economy(state)
    _icap = _se.interest_cap_override if _se.interest_cap_override is not None else INTEREST_THRESHOLD // 10
    interest_tiers = min(state.gold // 10, _icap)
    interest_val = interest_tiers * INTEREST_WEIGHT
    interest_val += _se.gold_per_node * INTEREST_WEIGHT / 10.0
    # ADR-0142(重复性经济效果折算进经济分;一次性 instant_gold 在选卡时点已体现,不在此):
    # - 分期节点金(长期主义系):amount*count 总额摊 20 节点 ≈ 每节点等效金
    # - boss 节点金(特战资金系):boss 占节点 ~1/9(1-9/2-7 结构)折算每节点等效
    # - 升级金(节节高升):P1+P2 剩余期望 ~5 次升级,摊 20 节点
    # - gold_per_20hp_lost(保险)故意不折算:损血换钱是反向激励,选卡评分不应鼓励损血
    _equiv = (_se.gold_next_nodes_amount * _se.gold_next_nodes_count / 20.0
              + _se.gold_per_boss_node / 9.0
              + _se.gold_per_level_up * 5.0 / 20.0)
    interest_val += _equiv * INTEREST_WEIGHT / 10.0
    level_val = (state.level - _expected_level(state.round_num, state.plane)) * LEVEL_WEIGHT
    if economy_mode == "interest_first":
        interest_val *= 1.5
    elif economy_mode == "rush_level":
        interest_val *= 0.5
        level_val *= 1.5   # rush_level:等级项加权(抢升语义 —— 落后等级更痛、领先更值),不只弱化守息
    # streak 档位金(C 杠杆 2;fixture 核实后接线 2026-08-11)。ADR-0128(攻略复查 #5):货币战争
    # **无连败补偿**(核心机制:27,vs TFT)→ 只计连胜方向,连败 0 分(旧 magnitude 对称计 = 把
    # 不存在的连败金也计入经济分 → 连败中虚高,误导「连败也值钱」)。
    streak_val = min(max(state.streak or 0, 0), STREAK_CAP) * STREAK_WEIGHT * _se.win_reward_mult
    return interest_val + level_val + streak_val




# P2+ 穷金重建门限(ADR-0148,评审 f3ab d1):低于此金 → rush_level 降档 interest_first(息引擎重建)。
# 与 roll_affordable 门(ADR-0147,放行边界 35)同族 —— 用户基准「P2 稳定≥50」的邻域;重建门限略低(30):
# 升 8 需 ~40 金级投入(多击 XP + 板件),30 以下 rush 无意义;息引擎(50 封顶)可渐进重建,自愈式
# (金回升 ≥ floor 自动回 rush_level,非进场粘滞)。
P2_REBUILD_GOLD_FLOOR: int = 30


def roll_affordable(state: GameState, config, target_comp) -> bool:
    """roll 可负担性门(ADR-0147,评审 f3ab d2):E[刷到 2星核心]×单价 vs 预算金。

    M20 死亡窗实证:roll 分支满血也放宽 cap=4 × 5 轮 plan,散板下 MC 期望恒正(任何牌都算
    reinforce+4、金币边际成本≈0)→ 连刷烧光金 18→0 全买散件。本门用**金计价**替 MC 符号:
    期望刷次(expected_refreshes_for_card,超几何精确;已实现未接线——本次接上)× 2 金
    > 预算金(gold − xp_floor)→ roll 让位 node plan(P2 推 8),不放宽。用户基准「P2 少刷吃息」。
    2星(3张)为目标档;3星 9 张期望太贵不进 D 决策。
    """
    goal = target_comp.level_plan.get(state.level)
    if goal is None or goal.action != 'roll':
        return False
    cost = goal.target_cost or 3
    # k=1「D 到下一张核心」:roll 分支实际行为 = 刷→见核心→买(增量凑件),非从 0 凑 2星
    # (2星 3 张期望 22 刷/44 金,门会永不放行)。expected_refreshes_for_card 的
    # target_star 只映射 2星/3星 → 直调底层 expected_refreshes(k=1)。
    from sr_od.application.currency_war.cw_shop_odds import (
        DISTINCT_CARDS_PER_COST,
        POOL_COPIES_PER_CARD,
        expected_refreshes,
        refresh_prob,
    )
    _p = refresh_prob(state.level, cost)
    _v = DISTINCT_CARDS_PER_COST.get(cost, 13)
    _a = POOL_COPIES_PER_CARD.get(cost, 9)
    e_refreshes = expected_refreshes(_p, _v, _a, c=0, k=1)
    # ADR-0202/53 号点消费:期望边际刷价按台账(免费额度余量折抵期望;v0 以额度摊销近似
    # ——每节点 N 次免费 → 期望刷次中前 N 次零成本)。无 active_strategies = 旧行为(零漂移)。
    _econ = getattr(state, 'active_strategies', None) or []
    _free_per_node = 0
    for _s in _econ:
        from sr_od.application.currency_war.cw_investments import get_strategy
        _se = get_strategy(_s)
        if _se is not None and _se.economy is not None:
            _free_per_node += _se.economy.free_refresh_per_node
    if _free_per_node > 0 and e_refreshes > _free_per_node:
        e_gold = (e_refreshes - _free_per_node) * SHOP_REFRESH_COST
    else:
        e_gold = e_refreshes * SHOP_REFRESH_COST if _free_per_node == 0 else 0.0
    budget = state.gold - _xp_gold_floor(state, True)
    return budget > e_gold and (e_gold == 0 or state.gold >= 2 * SHOP_REFRESH_COST)


def _char_synergies(name: str) -> set[str]:
    """角色全部羁绊(阵营 + 流派 + 独立),查 ``CHARACTERS`` 注册表(游戏数据单一真相源)。

    流派(持续伤害/击破/燃血/…)与阵营同为羁绊,``comp.factions`` 可含两者 → target 匹配须用全羁绊,
    非单 ``card.faction``(= ``Character.factions[0]``,丢流派)。流派主派 comp(DOT/击破/燃血)的流派
    角色(如艾丝妲=银河学者+持续伤害)据此识别为 target,不被误判 off-target → commit 后仍可买凑过渡。
    未识别 / 不在注册表 → 空集(card.faction 兜底由 ``_card_hits_target`` 加)。
    """
    ch = CHARACTERS.get(name)
    if ch is None:
        return set()
    syn = set(ch.factions) | set(ch.flows)
    if ch.independent:
        syn.add(ch.independent)
    return syn
