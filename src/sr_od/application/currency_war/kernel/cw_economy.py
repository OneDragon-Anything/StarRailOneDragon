"""货币战争 经济 / 等级 / 节奏骨架模型(纯函数:金 / 经验 / 息 / 刷新成本,ADR-0131 EconomyEffect 消费 + 0129 单击经验模型 + 0142 重复性效果折算;node_plan 节点×等级节奏骨架,14 §2 —— 三层共享底层,economy/evaluate/plan 均消费)。

自 cw_decisions.py 一次性拆分而来(ADR-0145;纯移动零行为变化,函数名/签名不变)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_factions import (
    INTEREST_THRESHOLD,
)
from sr_od.application.currency_war.kernel.cw_comps import (
    LevelGoal,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    EconomyEffect,
    aggregate_economy,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    XP_CLICK_COST_FALLBACK,
    XP_PER_BUY,
    XP_TO_NEXT_LEVEL,
    GameState,
    effective_hp_threshold,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )

INTEREST_WEIGHT: float = 4.0          # 每档(10金)利息的分。2026-08-04 提权(2→4):bot 不攒金 → 升不起级


STREAK_GOLD_TABLE: tuple[int, ...] = (1, 1, 2, 2, 2, 3, 4)
"""连胜金实测真值表(索引=连胜数,越界取末值;49/49 样本,economy.md §10.1;ADR-0262)。

弹窗底部固定规则表,与对局状态无关:0-1→1 / 2-4→2 / 5→3 / 6+→4(末位即 6+ 档)。"""


def streak_gold(streak: int) -> int:
    """连胜奖励金(真值源=奖励弹窗 VLM 判读 2026-08-23,r305;表化 ADR-0262)。

    查 STREAK_GOLD_TABLE,越界(连胜 6+)取表尾。
    单一源:sim 收入模型(cw_sim)与决策 EV(旧 line_strategy r307,
    ADR-0336 已删;现 decision_v2 经 sim/plan 共用)
    都 import 此函数,防双表漂移。"""
    idx = max(0, min(streak, len(STREAK_GOLD_TABLE) - 1))
    return STREAK_GOLD_TABLE[idx]


#: 每节点基础收入的近似常量(单一源:cw_sim 收入模型消费;原 DP 日程收入消费面已随 DP 退役删除,防双源漂移条款保留)。
#: 边界:基础奖励实际随节点变(VLM 判读 1-1=3/1-2=4,见 docs/game/currency_war/research/economy.md
#: 「基础奖励」行;守卫测试 sr-od-test test_cw_r305_reward_data)——5 是统一近似值,奖励采集成表后替换为查表。
BASE_INCOME: int = 5

#: 败轮收入(节点级固定金;实机 gold 差分实证 2026-08-28,108 局/767 轮:
#: 普通败轮残差众数 2(24/39)、遭遇 4(18/24)、boss 4(8/22,散布大置信中);
#: 见 docs/develop/currency_war/decisions/0439-sim-economy-income-caliber.md)。
#: 独立常量、**不动 STREAK_GOLD_TABLE**:表是胜轮弹窗真值(streak≥1 域,
#: ADR-0262 锁零触碰);败轮弹窗预期 1 与实发不符,走本表分支。
LOSS_GOLD_BY_NODE: dict[str, int] = {'battle': 2, 'encounter': 4, 'boss': 4}

#: 奖励节点基础收入查表(P1 实测:1-1=3 / 1-2=4,弹窗 VLM 判读 85/85 零散布;
#: 其余轮与全部非奖励节点仍 BASE_INCOME 统一近似)。**与奖励轮 streak 分量成对**:
#: BASE_INCOME=5 恰好盖住奖励轮照发的连胜金 table[0]=1——单独改 streak 不改本表
#: 会让奖励轮多发 1(ADR-0439 成对约束)。
REWARD_BASE_GOLD_BY_ROUND: dict[int, int] = {1: 3, 2: 4}

#: sim 收入口径版本(独立披露,不占 cw_coarse_battle.COARSE_CALIB_VERSION——
#: 那是粗模型战斗引擎校准的版本,收入口径在 cw_economy/cw_sim 收入段,另一子系统)。
#: 跨批次对比先核 manifest.economy_calib_version(局终指纹核对锚,与
#: 既有粗模型版本披露同机制)。
ECONOMY_CALIB_VERSION: int = 2
#: v2(ADR-0447):事件金表按实机逐轮金轨迹反馈整定(状态分布校准总闸),
#: 数值见 cw_sim.EVENT_GOLD_BY_ROUND 注释;v1 旧表(奖励球残差近似)
#: 批次与本版不可比,跨批对照须 economy_calib_version 一致。

# (gold 0-15 < 升级 cost 36-48)→ 卡低 level → 弱 comp。原 2.0:息 delta(50vs0)=10 = 牌 synergy 10 → bot
# 无差别→买不攒。提 4.0:息 delta=20 > 牌 synergy 10 → bot 攒到 50(息引擎)+ 花超额买/升级 = 经济统一论。
# streak 经济(C 杠杆 2;fixture 核实 2026-08-11 结算「连胜×N」前缀=方向 → streak 接线):
# ⚖️ **单边**(ADR-0128 #1,2026-08-15:货币战争无连败补偿,vs TFT)——只计连胜方向,
# 连败 0 分(旧「对称取 magnitude」描述已废,行为自 0128 起就是单边;economy_score:306 同源)。
STREAK_WEIGHT: float = 2.0            # 每档 streak 的经济分(占位,阶段 6 实玩校准)

STREAK_CAP: int = 5                   # streak 经济封顶档(连胜金一般 ≤5 档)

# C 杠杆 3 winning half(R2-4b;14 §连胜中「2 胜+」):连胜 ≥ 此 → 破息花钱提质量维持连胜(断连胜亏 > 利息亏)。
# streak 带符号(连胜 + / 连败 −,结算源 session.last_streak 方向可靠);连败 fold 半已由 HP-gating 覆盖(02 R2-4b)。
WIN_STREAK_BREAK_INTEREST: int = 2    # 连胜 ≥2 破息(阈值历史源 auto-chess 常识,货币战争档金真值未核——见 _refresh_cap r63 注)

# r89b 连胜-保息抉择(攻略专题「连胜与卖血抉择」三变量模型,663 帖精读实证):
# 攻略明文两分支 —— 已连胜→破息保连(#205「如果连胜就多D几个,利息保3」息档降到 30;
# #46「小搜争取连胜,不顺果断存钱」);未连胜+血安全→保息(#151「卡满50利息,大不了先输着先」;
# #145「优先留着吃利息,前期掉点血没事」)。「来牌顺」= 商店有可买战力件(shop_supply,无牌破息也无处花)。
# ⚠️ r90 用户修正(定性,2026-08-20):**攻略的「卖血不低于40」不是急救触发线,是运营质量的
# 报警线** —— 血低于它 = 前面破息决策已经错了;此时花光挺节点是「给前面的策略失败擦屁股」,
# 断息后经济可能永远撑不起整局(死亡螺旋:血低→花光→息断→板半成型→又掉血→又花光)。
# **目标是长期通关,不是苟住多少个节点**。故血低的正确响应 = 最小必要支出止损 + 息引擎
# 尽量保住,真 ALL IN 只留给「位面末最后一战」(赢了带血/板进下位面,不存在后续经济问题)。
# 该常量语义 = 运营质量报警线(策略层诊断/复盘用),不是 spending 触发器。
HP_QUALITY_ALARM: int = 40            # 运营质量报警线(血低于此 = 前面破息决策错;诊断用)
#: 攒息门 hp 急救分位(r90 审计:×0.5 匿名魔法数提成具名常量)——血低于 职级阈值×此分位
#: = 真活不下去(急救通道 _phase_weights 接管);中危带(此线与阈值之间)按用户定调
#: 「血低是报警非触发」维持攒息,不在此门破息(观察点:中危带持续漏买的场景留回放核)。
HP_DISTRESS_FRAC: float = 0.5

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



def _want_level_up(state: GameState, target_comp: Comp | None,
                   committed: bool | None = None) -> bool:
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
    # 退役批(ADR-0466/0467/0469) C5 换源(蓝图 §4.3-R1):committed 显式传参——None=挂账层旧口径
    # (读 GameState 双轨标志,cw_plan.plan 内部消费面暂留,删除点=买层接管批);
    # step 级调用方(level_up_gate 经 cw_plan.level_up_gate 透传)从
    # prep_brain.committed_from 取权威值传入,堵「装配边界漏回填双轨标志 →
    # 缺省 False → committed 恒 True → fresh 帧按已定型激进化放升级」的病理。
    if committed is None:
        committed = not getattr(state, 'dual_track_phase', False)
    # ADR-0149 P1 追级抑制(评审R3):息引擎未立**不追级**(金<INTEREST_THRESHOLD 时不再攒金
    # 买经验 —— M22 r7-r9 金≤35 全程追级零息病理)。⚠️ 语义边界(M31 实证修正):只拦「攒金
    # 追级」(金 < 单击价+10 = 连一次有效点击都做不了还想攒),**金够单击+保命地板(10)放行** ——
    # 升级本身是人口投资,金 12-14 点一次 XP 是正确节奏非泄金(M31 死因:旧 +20 地板把 lv4
    # 卡到 P2)。lv<5 不拦(开场人口等级);boss/锁血豁免。
    if (state.plane == 1 and state.level >= 5
            and state.gold < INTEREST_THRESHOLD
            and state.node_type not in ('boss',) and state.hp >= 30):
        # ADR-0275:旧「4+level」简算与生产 flat-4(XP_CLICK_COST_FALLBACK,OCR 实读
        # 优先)互相矛盾;实机对拍(VLM 三帧 lv4/lv7 均 4 金/击)裁决 flat-4 →
        # 统一走 xp_click_cost(单一源;商业间谍折扣同享)。
        _click_cost = xp_click_cost(state)
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
                # 75-A2 修:committed 全调用点一致(双轨期 xp 门与 spend 门同姿态,
                # 防「spend 攒息/xp 追级」门间对拉)。
                # r73 RC1-③:hp 门(HP_LOSS_FULL=30)——hp<30 濒死时买牌/合星是急救,
                # 追级是远水(RC1 实证:P2r2 hp=1 金 35 被 P2 硬地板吸走 24g 买经验,死)。
                # r87 H1 修正(审计 cc119c14,第3局实锤):hp<30 **进位面首 2 轮不拦** ——
                # hp1 进 P2 → 全量拦 → 升 8 永解锁不了 → 6 人应战到死(r4 团灭实证)。
                # 保命要靠升 7/8 填人口(carry 位),不是永远 6 人;RC1 案例的病理是
                # 「金 35 全烧经验」,由 XP 单击量控(花后地板)兜,非全量禁。
                if state.hp < 30 and not (state.plane >= 2 and state.round_num <= 2):
                    return False
                return bool(state.plane >= 2 and state.level < get_node_goal(
                    state.plane, state.round_num,
                    gold=state.gold, level=state.level, hp=state.hp,
                    committed=not state.dual_track_phase,
                    strategies=state.active_strategies or None).target_level)
    goal = _resolve_level_goal(state, target_comp)
    if goal is not None and goal.action == 'level_up':
        return True
    return state.level < get_node_goal(state.plane, state.round_num,
                                       gold=state.gold, level=state.level,
                                       hp=state.hp,
                                       committed=not state.dual_track_phase,
                                       strategies=state.active_strategies or None).target_level



def _xp_gold_floor(state: GameState, want_level: bool) -> int:
    """买经验时的存金地板(用户节奏 user_playstyle §7(docs/game/currency_war/research/;**玩法理解**: gameplay/currency_war.md 策略模型 S1)。

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
    """阶段期望等级(r90 C4 里程碑刻度,663 帖攻略精读实证)。

    P1:1-3 上5 / 1-7 遭遇前6 / boss 前 6-7(7 是 3费C comp 的 level_plan 域,通用曲线取 6)。
    P2:**2-1 即 7**(升7找主C;H1 修复后 bot 进 P2 应带 7)/ 2-5 前留 7 慢D主C三星 /
    2-6 升 8 搜5费 / 2-7 遭遇前阵容齐。
    P3:3-1 升 8 / 3-3+ 冲 9(3-7 boss 前瓦尔特[5费]需 9)。
    """
    if plane == 1:
        return min(4 + round_num // 2, 6)
    if plane == 2:
        return 7 if round_num <= 5 else 8    # 2-1→7(找主C);2-5 前留7慢D;2-6→8(搜5费)
    return 8 if round_num <= 2 else 9        # 3-1→8;3-3+→9(3-7 前瓦尔特)


# ===== node_plan:节点×等级×动作节奏骨架(阵容无关;14 §2) =====
# plan() 读 NodeGoal.target_level 作等级 gate 地板。spend_mode 驱经济档位(allin 跳卖息 等)。
# danger_d 占位(卡 node_type 下节点识别,3.5.5;非 difficulty/hp_trend —— 二者已就绪)。占位从未被读
@dataclass

class NodeGoal:
    """某节点(位面-轮)的节奏目标(阵容无关骨架;comp 只换 level_plan/core_chars 参数;14 §2.0)。"""
    target_level: int           # 该节点目标等级(地板);plan level gate 显式 gate
    spend_mode: str             # saving/interest/level/hold/spend/allin/adaptive(§2.2 经济档位)
                                # 'release' 不经本投影(帧级态):生产单一源=
                                # decision_v2.posture_release 经 session 通道;
                                # 本函数只产 level/adaptive/interest(迁移迁移批 3(ADR-0465)(ADR-0465))
    action_focus: str = ""      # 描述辅(d_search/chase_star/rush_level;指导动作偏好,不直接驱评分)
    #: DP 授权的可刷次数上界(W332b 三方预算合并:随 NodeGoal 下传,消费侧与
    #: plan 层 _refresh_cap 合并——合并语义单一源=decision_v2.posture_release
    #: 模块注释:release 是义务(下界),DP/plan 是许可(上界),义务激活时
    #: 义务优先,未激活时许可取交)。None=无 DP 信息(先验 fallback;不参与
    #: 合并,许可侧原值)。
    refresh_budget: int | None = None
    danger_d: bool = False      # 占位从未被读(见上)


# ⚖️ r69(2026-08-18 用户定夺):旧 _DEFAULT_NODE_PLAN 区间表**已删**。
# 历史:V4.4 先验表 → ADR-0126 用 11 局 bot live「校准」(P1末7/P2早8)→ 0126 被三重降级
# (0127 H4 疑幽灵锚点/0129 等级观测污染/2026-08-18 单局相关≠基准)。ADR-0155 DP 影子接缝
# 切流(0208)后 live 全部走 DP,该表只剩异常回退一条活路;失败面穷举(r69 对话)仅剩
# MemoryError + 开发期注册表手误(运行时游戏数据不进台账链;未注册策略名静默跳过)→
# **保留脏表回退比停机更危险**(静默掉回 0126 节奏 = 看着在跑实际在错)。删除;
# DP 失败/越界 → _expected_level 平滑先验 + adaptive(V4.4 干净先验,非 0126 数值)。
# 等级基准权威 = 用户口述 §7(economy_research;息引擎优先/§7-13 过渡 lv5-6)+ XP 反推真值。


def get_node_goal(plane: int, round_num: int, *,
                  gold: int | None = None, level: int | None = None, hp: int | None = None,
                  committed: bool = True,
                  strategies: list[str] | None = None) -> NodeGoal:
    """查 (plane, round) → NodeGoal(预算收权批(ADR-0465):确定性预算核单一供给)。

    姿态从预算收权核涌现(原 DP 解供给已退役,BLUEPRINT §3
    裁决;git 历史为 prior art):排程升级 → level/rush_level;刷新预算
    >0 → adaptive/d_search;两者皆无 → interest/hold。供给在任意帧恒有
    定义(`w623_batch3_pre-mortem/` D0:None 级联面消灭),仅传参不全(迁移漏点)时退
    ``_expected_level`` 平滑先验 + adaptive(记 [cw-seam] debug 证据)。

    三档 spend_mode 与决策核同源:level/adaptive/interest 的判据单一址
    = 本模块两接缝(schedule_upgrade/refresh_ev_budget,期 0b 自
    decision_v2.economy_cycle 下沉,R4)——本函数是其标量投影(原 DP
    接缝形状,消费方 cw_evaluate/cw_plan 接口零改动);'release' 档
    不经本函数(帧级态,单一源=decision_v2.posture_release 经 session
    通道)。
    """
    _partial = (gold, level, hp)
    if any(v is not None for v in _partial) and None in _partial:
        log.debug('[cw-seam] get_node_goal 部分传参(%s)→ 走先验 fallback;迁移漏点排查',
                  ('g' if gold is not None else '-') + ('l' if level is not None else '-')
                  + ('h' if hp is not None else '-'))
    if None not in (gold, level, hp):
        from sr_od.application.currency_war.kernel.cw_state import GameState as _GS
        # 标量投影帧:用入参重建最小决策帧(供给核只读经济/板面字段;
        # v1 栈调用面无现成 GameState——旧 DP 接缝同样只收标量)。
        # session=None:nodes_of_plane 走缺表回退先验 9(一次性告警即记档)
        # → h=9−r 常 >0,R* 窗口分量在投影帧**照常储蓄**(`w635_batch3_attack/` F6b 纠偏:
        # 原注释「投影帧不储蓄」与实现不符;方向保守无害)。
        _st = _GS(gold=gold, level=level, plane=plane, round_num=round_num,
                  hp=hp)
        _st.active_strategies = list(strategies or [])
        _rolls = min(6, refresh_ev_budget(_st, None))
        if schedule_upgrade(_st, None):
            return NodeGoal(min(10, level + 1), 'level', 'rush_level',
                            refresh_budget=_rolls)
        if _rolls > 0:
            return NodeGoal(level, 'adaptive', 'd_search',
                            refresh_budget=_rolls)
        return NodeGoal(level, 'interest', 'hold')
    return NodeGoal(_expected_level(round_num, plane), "adaptive", "rush_level")


# ⚖️ r69(2026-08-18):旧 ADR-0155 影子接缝开关 HORIZON_SEAM_ACTIVE **已删**——切流(ADR-0208)
# 完成后 DP 是唯一姿态源(r69 连带删除 0126 区间回退表,见 get_node_goal 注释),开关无消费点。
# 历史:切流依据(ADR-0208)= 160 局对拍「表 hold→DP level」P1 高金段系统性分歧 + 六局 P1
# boss 稳定损 20-36 血→P2 残血开局即崩。回滚方式 = git revert r69 提交。



def economy_score(state: GameState, economy_mode: str) -> float:
    """经济健康度:利息(存金到 50)+ 等级合适度 + streak 档位金(C 杠杆 2)。

    economy_mode 只调利息项(rush_level 弱化守息、interest_first 强化守息),等级项不变。
    阶段保血(前期/低血 → 经济降权)由 evaluate 的 _phase_weights 统一处理(A3)。
    streak 单边计分(ADR-0128 #1:货币战争无连败补偿,只计连胜;连败 0 分);fold(连败保息)已由 HP-gating 实现(02 R2-4b,用户 2026-08-12 确认:血量安全→fold/不安全→急救,经 _phase_weights/_refresh_cap HP gate);方向驱动「保连胜」半(连胜维持>吃息)已接 plan:``_should_save_for_interest`` 连胜≥``WIN_STREAK_BREAK_INTEREST`` 破息(C 杠杆 3,R2-4b)。
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
    from sr_od.application.currency_war.data.cw_shop_odds import (
        DISTINCT_CARDS_PER_COST,
        POOL_COPIES_PER_CARD,
        expected_refreshes,
        refresh_prob,
    )
    _p = (getattr(state, 'refresh_probs', None) or {}).get(cost) \
        or refresh_prob(state.level, cost)   # r77 轮岗:实读概率条优先(翻倍档期望刷次减半)
    _v = DISTINCT_CARDS_PER_COST.get(cost, 13)
    _a = POOL_COPIES_PER_CARD.get(cost, 9)
    e_refreshes = expected_refreshes(_p, _v, _a, c=0, k=1)
    # ADR-0202/53 号点消费:期望边际刷价按台账(免费额度余量折抵期望;v0 以额度摊销近似
    # ——每节点 N 次免费 → 期望刷次中前 N 次零成本)。无 active_strategies = 旧行为(零漂移)。
    _econ = getattr(state, 'active_strategies', None) or []
    _free_per_node = 0
    for _s in _econ:
        from sr_od.application.currency_war.kernel.cw_investments import get_strategy
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


# ===== 经济循环接缝族(分包期 0b 单元2 自 decision_v2.economy_cycle 下沉;§3.3-①a/①b) =====
# 原址:decision_v2.economy_cycle(kernel→decision 断环:本文件是 kernel 桶,
# cw_economy.get_node_goal 标量投影消费两接缝,原函数体内懒 import 决策包
# 成环)。schedule_upgrade 纯移动;refresh_ev_budget 最小重构——应急谓词
# is_emergency 一并下沉本文件(一行纯谓词,decision_v2.filters 改 import
# 重定向,单一源不破),函数体零行为变化(等价锁=sr-od-test
# test_cw_w695_economy_seam.py + 既有 w633/w332b/w154 桩点重钉)。

#: 刷新通道容量上界(刷数;原 DP 求解面动作上限 6 刷同源(git prior art),
#: 不另造第二把尺)。自 economy_cycle 随接缝族同迁(单一源在本文件)。
REFRESH_ROLL_CAP: int = 6


def is_emergency(state: GameState,
                 registry: DecisionV2Registry) -> bool:
    """应急触发(绝对 HP 档简版;redesign §5.4 Phase A 口径)。

    单一源在本文件(kernel);decision_v2.filters.is_emergency 为 import
    重定向,消费方调用零改。"""
    return state.hp <= registry.emergency_hp


def _registry_of(session: StrategySession) -> DecisionV2Registry:
    """接缝函数的注册表解析(A/B 注入面:session.v3_registry 显式注入
    优先,缺省落 DEFAULT_REGISTRY——缺省栈无注入臂,P6 契约同 prep_brain
    装配签名)。"""
    reg = getattr(session, 'v3_registry', None)
    return reg if isinstance(reg, DecisionV2Registry) else DEFAULT_REGISTRY


def schedule_upgrade(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry | None = None) -> bool:
    """排程升级判据(确定性费用查表核;蓝图 §3.4 R4 接缝,预算收权批(ADR-0465))。

    ``registry``:显式注入优先(A/B 注入面,P6 契约:同一调用链全部接缝
    必须传**同一个** registry 实例——prep_brain._budget 单源装配);
    缺省落 _registry_of(session) → DEFAULT_REGISTRY。
    规则集 = `w615_rules_advocacy/` §1.3/§2-R4(机制常量直算,零标定权重);**预告态契约**
    (`w623_batch3_pre-mortem/` D1):排程只回答「要不要开始攒」,不以当帧可负担为前置——
    付不付得起是执行层的事(``ev.levelup_ev_basis`` 可负担性入口门),
    排程判据若收窄成「付得起才排」会造成 R* 塌缩 → 义务花光 → 更排不上
    的自我强化升级迟到循环(DP 无此失败模式:其 level_up 判定不依赖当帧
    是否看得见目标)。

    触发(任一,判据单一址=R4:本函数被 R* 储蓄分量(reserve_cap)、
    arbiter 金地板授权、EV 升级授权 ② 臂三处共调):
    ① 人口位([33]):cap 满 ∧ bench 有成型件(2★)等上场——升级后能
       立即部署,当轮兑现战力,为最高义务;
    ② 概率级([3]/[7]):目标核心概率峰值级 > 当前级 ∧ 息引擎已立
       (g ≥ 息线,[12] 息引擎前置)。
    禁升条件([12]/[32]):息引擎未立不追级(② 的前置即此);空升级
    不升(① 触发本身即「有件可上」,无空升级面;② 是概率抬档语义,
    不涉部署)。
    **规则文本偏差披露(`w635_batch3_attack/` F2)**:`w615_rules_advocacy/` §2-R4 规则 2 原文有第三合取
    「花完升级费后 g′ ≥ interest_floor」,与其 §1.3 伪码矛盾(伪码无此
    项);本实现**取伪码侧**(预告态,不设该合取——保留它会让
    g∈[息线, 息线+费) 帧不排程,恰造 D1 塌缩循环)。可负担性/平台未破
    由执行层收口:ev.levelup_ev_basis 可负担性入口门 + ② 臂花后 ≥息线。

    目标级解析:意向锁定核心 → 兜底 comp 核心 → 缺省 3 费档(meta
    「7 级搜牌」主流带);费用档 → 峰值级查表
    (``cw_plane_table.peak_refresh_level``)。comp 空帧不缺供给——
    兜底链保证 L_target 恒可解(D1:target 级判定迟疑帧返回 False 是
    塌缩循环的入口,禁)。
    """
    from sr_od.application.currency_war.kernel.cw_investments import (
        refresh_invest_active,
    )
    if refresh_invest_active(state):
        return False    # 淘金客姿态:升级通道退役(`w621_sim_explore/`;谓词单一址)
    from sr_od.application.currency_war.kernel.cw_state import (
        deployed_occupied,
    )
    reg = registry or _registry_of(session)
    # ① 人口位:cap 满 ∧ bench 有成型件(2★)等上场([33]/[32](a))
    if deployed_occupied(state.deployed or []) >= state.max_units() \
            and any(b is not None and (getattr(b, 'star', 1) or 1) >= 2
                    for b in (state.bench or [])):
        return True
    # ② 概率级:息引擎已立 ∧ 目标峰值级在当前级之上
    if (state.gold or 0) < reg.interest_cap * 10:
        return False
    return _target_peak_level(state, session) > (state.level or 1)


def _vd_core_of(session: StrategySession) -> str:
    """V_D/V_level 共用的目标核心解析(scoring.vd_target_core 同源;
    自 decision_v2.ev 下沉(期 0b 单元2,schedule_upgrade 的目标核心解析链
    依赖;本模块零 decision 依赖,decision_v2.ev 改 import 重定向)——
    ev 不 import decision_v2 包内模块的判据复刻惯例随单一源归位终结)"""
    from sr_od.application.currency_war.kernel.cw_intention import (
        IntentionState,
        intention_core,
    )
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState) or ist.phase != 'locked' \
            or not ist.locked_comp:
        return ''
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    comp = get_comp(ist.locked_comp)
    if comp is None:
        return ''
    return intention_core(comp)


def _target_peak_level(state: GameState, session: StrategySession) -> int:
    """目标核心费用档 → 概率峰值级(解析链:意向锁定核心 → 兜底 comp
    核心 → 缺省 3 费;核心解析单一源 = _vd_core_of 与其兜底扩展)。"""
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.kernel.cw_plane_table import (
        peak_refresh_level,
    )
    core = _schedule_target_core(session)
    ch = CHARACTERS.get(core) if core else None
    cost = ch.cost if ch is not None and ch.cost else 3
    return peak_refresh_level(cost)


def _schedule_target_core(session: StrategySession) -> str:
    """排程目标核心解析(ev._vd_core_of 锁定核单一源;未锁帧落意向
    ⑤兜底 comp 的核心——方向层 FALLBACK_COMP_NAME 单一源;再缺='' →
    调用方缺省 3 费档,供给不断)。"""
    from sr_od.application.currency_war.kernel.cw_intention import (
        FALLBACK_COMP_NAME,
    )
    core = _vd_core_of(session)
    if core:
        return core
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    fb = get_comp(FALLBACK_COMP_NAME)
    if fb is not None:
        from sr_od.application.currency_war.kernel.cw_intention import intention_core
        return intention_core(fb)
    return ''


def refresh_ev_budget(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry | None = None) -> int:
    """刷新 EV 授权刷数(确定性预算式;蓝图 §3.4 R4 接缝,预算收权批(ADR-0465))。

    ``registry``:显式注入优先(P6 契约,同 schedule_upgrade);缺省落
    _registry_of(session) → DEFAULT_REGISTRY。
    预算 = min(6, ⌊(g − R*)/刷价⌋)——只花溢余(`w615_rules_advocacy/` §2-R3 预算式:
    刷新后仍守储备线;6 刷帽单一源 = REFRESH_ROLL_CAP,原 DP 求解面
    _ACTION_ROLLS 的 DP 上限同源,不另造第二把尺)。

    合法 0 帧契约(`w623_batch3_pre-mortem/` D2,判前锁;**辖域=应急带**,`w635_batch3_attack/` F1 收口):
    - 应急帧(``is_emergency`` 单一源,hp≤emergency_hp)→ 0:
      应激通道根本不产指令(release 让位结构,合并无从放大);
    - g ≤ R* 常态帧(息线以内/储备段持有,0.1/轮 真实收益)→ 0:这个 0
      流过 scoring P2 窗判据(``refresh_budget<=0 → 让位``)与存息
      准入门,「>0 即行动授权」的语义在预算函数口径下成立。
    **血预算带(应急线以上,ADR-0448/0451)不在本函数辖域**:预算字段
    依公式照发,停手由 arbiter 拒付层兜底(discipline.
    blood_budget_levelup_blocked 停升级 / blood_budget_refresh_blocked
    搜索型刷新停付)——防线在拒付层不在预算层;原「血预算帧→0」为
    虚标契约,已随 `w635_batch3_attack/` F1 如实收窄(穿透锁=test_cw_w633_migration_b3)。
    定向刷新授权(directed_refresh_budget)是独立车道(arbiter E2,
    1 次/轮),与本预算不相交、不合并——披露面,非 0 帧契约的一部分。
    """
    reg = registry or _registry_of(session)
    if is_emergency(state, reg):
        return 0
    over = (state.gold or 0) - reserve_cap(state, session, reg)
    if over <= 0:
        return 0
    cost = state.shop_refresh_cost or 2
    return min(REFRESH_ROLL_CAP, over // cost)


def upgrade_plan_fee(state: GameState) -> int:
    """下一级升级总费(逐帧现读:OCR 单击价优先,缺省 flat 常量)。"""
    from sr_od.application.currency_war.kernel.cw_plane_table import clicks_to_level
    from sr_od.application.currency_war.kernel.cw_state import (
        XP_CLICK_COST_FALLBACK,
    )
    click = state.level_up_cost or XP_CLICK_COST_FALLBACK
    return clicks_to_level(state.level) * click


def _rounds_to_plane_end(state: GameState, session: StrategySession) -> int:
    """到本位面末节点(= boss 节点)的剩余轮数(含当前轮;缺读兜底 0
    =不储蓄,保守侧:R* 退化为息线,义务面变宽但方向安全)。
    nodes_of_plane 自带缺表回退(先验 9+一次性告警),此处不再兜层。"""
    from sr_od.application.currency_war.kernel.cw_plane_table import nodes_of_plane
    total = nodes_of_plane(session)
    return max(0, total - state.round_num)


def reserve_cap(state: GameState, session: StrategySession,
                registry: DecisionV2Registry) -> int:
    r"""R\*(t) = interest_floor + Σ 窗口内排程升级费(设计 §1.3)。

    窗口 h = min(3, 到本位面末节点轮数);只储蓄下一级费用——多级
    排程在逐帧重算下自愈(升级完成一轮后 R* 自然滚动到下一级;W481
    A-4:误估最坏=一个升级费量级 ≤50 金,双向有界)。
    排程判据单一址 = ``schedule_upgrade``(确定性查表核,批 3 预算
    收权;与 arbiter 授权/EV 授权 ② 臂共调同一函数,R4)。

    守息线取 `interest_cap × 10`(息帽同源派生,W611 §2.2 恒等式):
    基参数下 5×10=50==interest_floor,行为零漂移;写法保证「守息线
    ≤ 封顶线」结构性成立——两者同源,不可能出现守息线高于持有增益
    归零点(息帽截断点)的态。策略级息帽 override(interest_cap_override)
    走 ledger/DP 通道,registry 息帽与之分离时以封顶线为准(设计 §2.2
    规则原文);分离面=已知缺口,如实挂账。
    """
    h = min(_RESERVE_WINDOW_ROUNDS,
            _rounds_to_plane_end(state, session))
    floor = registry.interest_cap * 10
    if h <= 0 or not schedule_upgrade(state, session):
        return floor
    return floor + upgrade_plan_fee(state)


#: 储备窗口上界(轮;设计 §1.3:h = min(到下一 boss 节点轮数, 3)——
#: 更远的排程升级应即时执行而非长期储蓄,结构界非拍值)。
#: 自 economy_cycle 同迁(reserve_cap 唯一消费,单一源随函数走)。
_RESERVE_WINDOW_ROUNDS: int = 3
