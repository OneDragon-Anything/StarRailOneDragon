"""货币战争 经济 / 等级 / 节奏骨架模型(纯函数:金 / 经验 / 息 / 刷新成本,ADR-0131 EconomyEffect 消费 + 0129 单击经验模型 + 0142 重复性效果折算;node_plan 节点×等级节奏骨架,14 §2 —— 三层共享底层,economy/evaluate/plan 均消费)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_factions import (
    INTEREST_THRESHOLD,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    gold_of,
    level_of,
    plane_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    EconomyEffect,
    aggregate_economy,
)
from sr_od.application.currency_war.kernel.cw_plane_table import (
    GOLD_CAP_INTEREST,
    r_remaining,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar
    from sr_od.application.currency_war.kernel.cw_vocab import ShopCard
    from sr_od.application.currency_war.kernel.cw_vocab import CwSimFrame
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )

# ============================================================
# 候裁9 词汇迁入(原 kernel/cw_state.py 经济域):
# 金/经验/刷新/卖出回金/血线族(经济骨架同域)。
# ============================================================


# 卖出回金 = 招募费(cost)× 合成倍数,docs/game/currency_war/research/economy.md §3(卖出退金)。1星=cost 🟢 BWIKI+4399+用户权威;
# 2星=cost×3−1、3星=cost×9−1、4星=cost×27−1(合成成本扣1手续费;2星用户印象「少1」,
# 3/4星推测同逻辑 🟡 待 hook 实机核 —— 拖卡到出售区看显示金额)。
_SELL_MULT: dict[int, int] = {1: 1, 2: 3, 3: 9, 4: 27}   # 星级 → cost 倍数(3合1:1星1/2星3/3星9/4星27 张基础副本);sell_refund 对 star≥2 且 cost≥2 再 −1 手续费(cost=1 exempt,见 sell_refund)

# 购买经验机制(ADR-0129;用户实测口述 2026-08-15,A5+;telemetry 多局 XP 分母 4/6/20/40 对拍一致):
# 「购买经验」每点一次 +XP_PER_BUY 经验、花小额金币(按钮实读 state.level_up_cost);经验攒够当前级
# 门槛自动升级,溢出结转。等级门槛表(升下一级所需总经验):
XP_PER_BUY: int = 4
XP_TO_NEXT_LEVEL: dict[int, int] = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}
XP_CLICK_COST_FALLBACK: int = 4   # 单击经验花金兜底(level_up_cost OCR 缺失时;telemetry lv5 实测 4 金/击)
#: 玩家等级封顶(live 语义:10 级后购买经验无效;xp_apply_clicks/xp_clicks_to_level/
#: simulate LevelUp 分支/cw_game_state 逻辑态直写满级门同此单一源。sim 侧 LEVEL_CAP=9
#: 是已知建模分歧,勿混用——本常量只辖 live 侧)。
MAX_PLAYER_LEVEL: int = 10


def xp_apply_clicks(level: int, xp_cur: int, clicks: int,
                    xp_per_buy: int = XP_PER_BUY) -> tuple[int, int]:
    """N 次「购买经验」后的期望 (level, xp_cur)(纯函数;XP 期望态账本的推进算子)。

    语义 = ADR-0129 单一源:每击 +xp_per_buy 经验;攒满当前级门槛即升级、
    溢出结转(与 cw_state LevelUp 动作应用 / sim 轮末升级清零结转同规则)。
    封顶 MAX_PLAYER_LEVEL(10)级 = 生产 live 语义(满级后购买经验无效;
    sim 侧 LEVEL_CAP=9 是已知建模分歧,勿混用)。

    [字段定义] level = 游戏玩家等级 1-10(整局单调,坐标系 = 游戏 XP 条);
    xp_cur = 当前级已攒经验;取值时机 = 意图应用时纯推算(非执行期现读);
    写入端 = CwScreenPrep XP 期望态账本。clicks ≤ 0 → 原值返回(无意图零推进)。
    """
    if clicks <= 0 or level >= MAX_PLAYER_LEVEL:
        return level, xp_cur   # 封顶/零意图:购买经验无效,零推进(live 语义)
    cur = xp_cur + clicks * xp_per_buy
    while level < MAX_PLAYER_LEVEL:
        need = XP_TO_NEXT_LEVEL.get(level, 4)
        if cur < need:
            break
        cur -= need
        level += 1
    return level, cur


def xp_clicks_to_level(level: int, xp_cur: int,
                       xp_per_buy: int = XP_PER_BUY) -> int:
    """当前级攒到**恰升 1 级**所需的最少购买经验次数(纯函数)。

    = ceil((need − cur) / xp_per_buy);cur 已达门槛 → 1(再点一次即升)。
    消费端 = CwScreenPrep 直接 LevelUp 动作(腾席链「循环点至 level+1、
    首次验证成功即停」通道):progressed=True 时实际击数 = 本值。
    已升满 MAX_PLAYER_LEVEL(10)级 → 0(点击无效,调用方零推进)。
    """
    if level >= MAX_PLAYER_LEVEL:
        return 0
    need = XP_TO_NEXT_LEVEL.get(level, 4)
    gap = need - xp_cur
    if gap <= 0:
        return 1
    return (gap + xp_per_buy - 1) // xp_per_buy

# 刷新商店实付金 = 基价常量(建模值,非 OCR 读数)。出处:多局旧决策行
# 相邻金差对账(只含 LevelUp+Refresh 的最小对账对)全部 = 2,不随金币/
# 次数/等级变;invest_effects.md「刷新 45% 概率免费 → 期望刷价 1.1」隐含基价
# 2(2×0.55=1.1)。右下角「文本-刷新金币数」rect 实际读到的是面板徽标
# (数值 = min(gold//10,5) = 利息公式,非刷价;三流对拍定谳,ADR-0456)——
# 该 OCR 已退出 read_game_state 主链(cw_observation),决策/对账统一消费本常量。
# 消费点沿用 ``or 2`` 兜底语义:字段恒为基价,兜底分支不再触发,零行为波及。
REFRESH_COST_BASE: int = 2

# 保血阈值(策略校准参数,自 config 迁入代码单一源;值随实机校准走 git,不走用户 yml)。
# **保守起步,待实机校准**:A1-A4 = 40(低难不变,可适当卖血保经济);A5+ 升阶(高难敌人更凶 → 更早弃息保血)。
HP_SAFE_THRESHOLD: int = 40    # 保血阈值默认(未检测职级时;语义「安全地板」,kernel 单一源)
DIFFICULTY_HP_TABLE: dict[str, int] = {
    "A1": 40, "A2": 40, "A3": 40, "A4": 40,
    "A5": 45, "A6": 50, "A7": 52, "A8": 55,
}


def card_cost(card: ShopCard) -> int:
    """牌的费用:OCR 读到用真值,未知按 3 估(费用 1-5 中位)。"""
    return card.cost or 3


def sell_refund(star: int, cost: int) -> int:
    """卖出回金(economy.md §3 卖出退金(docs/game/currency_war/research/);用户 2026-08-12 提醒卖出金币重要 + 核 2星)。

    - 1星 = cost(🟢 BWIKI「按其费用获得回收金币」+ 4399 + 用户,权威;无合成 → 无手续费 → 买卖净0)。
    - 2星 = cost×3、3星 = cost×9、4星 = cost×27(合成成本),**star≥2 且 cost≥2 再 −1 手续费**。
    - **cost=1 exempt(无手续费)**:🟢 2026-08-13 live 实测 2★1费 万敌 出售 = **+3 金**(cost×3,无 −1;
      sell-star 停机钩子 + VLM 读出售按钮「金币+3」)。用户:1费 2星不减、**2费开始才减1**(手续费 cost 相关
      非纯 star)。故 −1 条件 = ``star>=2 and cost>=2``。
    - 🟡 cost≥2 的 −1(2★2费=5)+ 3/4星 仍用户记忆 / 推测,待多 cost live 核;cost=1 各星已定(全额退)。
      (置信度分层处置:卖面 refund 消费按保守端=下界组装(mult×c−fee_hi,fee_hi=1);
      live 核定通道=单局复盘协议检查项,sr-od-currency-war-dev skill;
      原设计件 IMPL_FIX_LEMMAS/IMPL_DESIGN 已删档,取回口径=ADR-0644。)
    """
    refund = max(cost, 1) * _SELL_MULT.get(star, 1)
    if star >= 2 and cost >= 2:
        refund -= 1   # 合成手续费:仅 star≥2 且 cost≥2(cost=1 exempt,实测 2★1费=3 无费;用户「2费开始减1」)
    return max(refund, 0)


def bench_char_cost(bc: BenchChar) -> int:
    """备战角色的招募费(sell_refund / 经济决策用):char_id 已识别 → 查 CHARACTERS;未知 → 3(中费保守估)。

    公共名(跨模块私有符号收敛:跨模块消费统一走本名;
    下划线旧名保留为别名,存量消费点不破)。"""
    c = CHARACTERS.get(bc.char_id) if getattr(bc, 'char_id', '') else None
    return c.cost if c and c.cost else 3


def effective_hp_threshold(bs: GameState) -> int:
    """实际保血阈值:selected_difficulty(职级)检测到且 ``DIFFICULTY_HP_TABLE``
    有对应键 → 取覆盖值;否则回退 ``HP_SAFE_THRESHOLD``(40)。容器版单一实现
    (输入 = ``GameState``;职级/位面/轮次/等级经容器域读法——统一 state
    迁移波 2 签名切换,输入字段 selected_difficulty/plane/round_num/level
    容器侧全部就绪)。

    高难(A8)敌人更凶 → 阈值调高,更早弃息保血。阈值表是策略校准参数(代码常量,
    自 config 迁入 —— 用户对「A7 该在 52 血弃息」没有个人意见,不属用户偏好)。

    ⚖️ ADR-0176(桥接拆除):P2+ 位面上浮不再用手写 ×1.25/×1.5(ADR-0174 桥),
    改由 18 号首达生存模型解出 —— ``plane_hp_ratio``(hp_floor(P_win 地板比),随板强/剩余日程
    变化:强板 ratio→1 不盲目抬阈值,弱板长程 ratio 升高更早保血)。P1 分母恒等 → 对 base
    精确零漂移(M57 验证行为保持)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        level_of,
        plane_of,
        round_num_of,
    )
    from sr_od.application.currency_war.kernel.cw_first_passage import (
        board_tier_of,
        plane_hp_ratio,
    )
    from sr_od.application.currency_war.kernel.cw_plane_table import (
        NODES_PER_PLANE,
        TOTAL_NODES,
    )

    diff = (bs.selected_difficulty.value or '').strip()
    base = int(DIFFICULTY_HP_TABLE.get(diff, HP_SAFE_THRESHOLD))
    plane = plane_of(bs)
    if plane <= 1:
        return base
    # 剩余战斗日程估计(位面×轮次 → 节点序;round_num 越界防御夹 [1, NODES_PER_PLANE])
    t = (min(3, plane) - 1) * NODES_PER_PLANE \
        + min(max(1, round_num_of(bs)), NODES_PER_PLANE) - 1
    nodes_left = max(1, TOTAL_NODES - t)
    ratio = plane_hp_ratio(board_tier_of(level_of(bs)), nodes_left, plane=plane)
    return min(100, int(base * ratio))

INTEREST_WEIGHT: float = 4.0          # 每档(10金)利息的分(权重算账见下方注释块)


STREAK_GOLD_TABLE: tuple[int, ...] = (1, 1, 2, 2, 2, 3, 4)
"""连胜金实测真值表(索引=连胜数,越界取末值;49/49 样本,economy.md §10.1;ADR-0262)。

弹窗底部固定规则表,与对局状态无关:0-1→1 / 2-4→2 / 5→3 / 6+→4(末位即 6+ 档)。"""


def streak_gold(streak: int) -> int:
    """连胜奖励金(真值源=奖励弹窗 VLM 判读;表化 ADR-0262)。

    查 STREAK_GOLD_TABLE,越界(连胜 6+)取表尾。
    单一源:sim 收入模型(cw_sim)与决策 EV(decision_v2 经 sim/plan 共用)
    都 import 此函数,防双表漂移。"""
    idx = max(0, min(streak, len(STREAK_GOLD_TABLE) - 1))
    return STREAK_GOLD_TABLE[idx]


# ===== 息账/收入日程(自 strategies statefn/interest+income 下沉单一源,
# ===== kernel 判据(schedule_upgrade 的 U_L 阈值检验)消费
# ===== loss_exact/net_income,下沉保持「kernel 禁 import strategies」桶
# ===== 依赖矩阵;statefn 两模块改 import 重定向,消费方调用零改——
# ===== 与 schedule_upgrade 下沉同款先例)=====

#: 默认息帽档数 = 息封顶金位/10(cw_plane_table.GOLD_CAP_INTEREST=50 的
#: 结构派生,【注】机制真值;禁在本模块另写裸 5)
DEFAULT_INTEREST_CAP: int = GOLD_CAP_INTEREST // 10

#: cap 视界上确界(注册表 interest_cap 值域上界 10;消费位按 canonical
#: 枚举表纪律——原 design_economy §E4.2 已删档,取回口径=ADR-0644——
#: 一律消费 cap_sup 而非决策帧现值 cap_resolved(R63-1)。
INTEREST_CAP_SUP: int = 10


def interest(gold: int, cap: int = DEFAULT_INTEREST_CAP) -> int:
    """利息 = min(g//10, cap);g<0 按 0 计(防负金越界,p47 A1 同源)。"""
    return min(max(gold, 0) // 10, cap)


def interest_cap_resolved(interest_cap_override: int | None = None) -> int:
    """resolved 息帽(「无覆写回默认」的单点归一)。

    override=None(默认局/未持息帽卡)→ DEFAULT_INTEREST_CAP;注册表
    覆写值(开源节流 9/利息上调 10/买断制 0)由调用方经聚合链传入——
    本函数只做归一,禁在判据侧内联 cap 字面量(E4.0 第 1 条)。
    **0 是有效覆写**(买断制 = 息通道改写,在册同判 cw_events
    is_economy_engine):判别只认 None,禁真值折叠——``override or 缺省``
    形态会让买断制静默回 5(ADR-0598 最高危陷阱锁)。
    """
    if interest_cap_override is None:
        return DEFAULT_INTEREST_CAP
    return max(0, int(interest_cap_override))


def cap_resolved_of_session(session: StrategySession | None) -> int:
    """cap_resolved 现读(session resolved 链;息帽三源归一)。

    覆写单一源 = ``aggregate_economy(session.active_strategies).
    interest_cap_override``(注册表派生、零新参数;ADR-0598 息帽死链
    修复):已持投资策略聚合取 cap 覆写(并持取宽 = ADR-0131),未持
    息帽卡 → None → 回 DEFAULT_INTEREST_CAP;None/0 判别语义由
    :func:`interest_cap_resolved` 单点承载。两个写点 = 实机选卡 handler
    (cw_screen_invest_strategy,确认成功后 append)与 sim 注入臂
    (engine_p1,append+state 镜像)——本函数只读 session 级字段,
    禁读 state 镜像(非公共权威)。

    消费位 = 商店线 R1/R2 的 g* 装配(mandate._cap_of 重定向至此)、
    schedule_upgrade ② 前置息线、U_L 阈值检验的 loss_exact cap 参数、
    必花域/发射帧溢余段、registry 预算面守息线分量(reserve_cap/
    BudgetView.interest_floor/换线可负担窗,ADR-0598 随批接线)——
    共用本式,禁再内联 ``interest_cap×10`` 或 loss_exact 裸缺省 cap
    (息律投资 cap=10 局,裸缺省 5 会低估 C_int)。

    边界:本链不读 registry.interest_cap(A/B 旋钮辖观察/检查器镜像
    面,不辖本链);回落问题的实际形态 = 「从未持有」——投资策略
    无卖出/移除建模(handler 只 append),与 economy_score/S2 共享
    同一 append-only 假设,非本函数独立边界。
    """
    strategies = getattr(session, 'active_strategies', None) or []
    override = (aggregate_economy(list(strategies)).interest_cap_override
                if strategies else None)
    return interest_cap_resolved(override)


def saturation_line(cap_resolved: int) -> int:
    """息律饱和线 g* = 10×cap_resolved(守息门/arm2 金下限同源派生)。"""
    return 10 * cap_resolved


def in_must_spend_zone(gold: int, session: StrategySession | None) -> bool:
    """必花域判定(20 号稿 §2.1):g > G_must = 10 × cap_resolved。

    单一源派生 = saturation_line(cap_resolved_of_session(session)),与
    息线 g*/arm2 守息门同链,零新自由参数;买断制语境(cap_resolved = 0)
    出辖恒 False(§2.1,该语境金出口归一般判据)。辖域 = 有动作决策点帧
    (shop/备战决策入口调用点;§3.4)。

    消费点(本批接线):shop.py 出口③ L2 第二触发源(∨ 合并)/L3 必花域
    升级/R1 域内残形切分线/EV 域内降排序——四点共用本判定,禁再内联
    ``gold > 10 * cap`` 字面量式。
    """
    cap = cap_resolved_of_session(session)
    if cap <= 0:
        return False   # 买断制出辖(§2.1)
    return gold > saturation_line(cap)


def in_launch_spend_zone(gold: int, session: StrategySession | None) -> bool:
    """发射帧溢出段判定(金出口族出口 B 触发面;金出口族 DESIGN v1.1 §3.2,
    落码裁决 = ADR-0566)。

    = ``gold > saturation_line(cap_resolved_of_session(session))``——与
    :func:`in_must_spend_zone` 共享 g* 单一源(saturation_line 同链,
    禁内联第二份);买断制语境(cap_resolved = 0)出辖恒 False(与必花域
    §2.1 同口径)。

    **与必花域同 g* 不同域,禁并键**(DESIGN v1.1 §5;launch_gold_tradeoff
    §3 边界①同判):必花域辖「有动作决策点的 shop/备战帧」,本谓词辖
    「发射帧仲裁段」(仲裁段插入后发射帧成为决策点;两域互斥 = 调用点
    约定非结构保证,M-1 降级口径,新增消费点须回 DESIGN §5 对账表)。
    消费点(本批接线):cw_loop 发射帧仲裁段预判 / engine_p1 发射帧
    仲裁段区判,两面直调本函数,禁各自内联 ``gold > g*`` 字面量式。
    """
    cap = cap_resolved_of_session(session)
    if cap <= 0:
        return False   # 买断制出辖(§2.1 同口径)
    return gold > saturation_line(cap)


def loss_exact(gold: int, spend: int, rounds: int, net_income: int,
               cap: int = DEFAULT_INTEREST_CAP) -> int:
    """金位 gold 花 spend 金后未来 rounds 轮的精确期望息损(P47 命题 2)。

    双轨迹对照:基线 B(不花,守饱和线,溢余即花)vs A(花后守线);每轮息损
    = interest(B) − interest(A),两轨迹同收入演化。截断视界 R=rounds 由
    horizon 层供给(schedule_of 实际长度,禁写死,§6.1)。溢金域先实金扣
    再守线截断(IMPL_ADV_R194 症2);gold<0 钳 0。
    """
    gold_cap = 10 * cap
    g0 = max(gold, 0)
    b = min(g0, gold_cap)
    a = max(g0 - spend, 0)
    total = 0
    for _ in range(rounds):
        ib, ia = interest(b, cap), interest(a, cap)
        total += ib - ia
        b = min(b + net_income + ib, gold_cap)
        a = min(a + net_income + ia, gold_cap)
    return total


def round_base_income(round_num: int) -> int:
    """基础奖励金的 **P1 规划投影**(round 单键形态;决策数学规划用)。

    = ``reward_base_gold(1, round_num)`` 薄委托(ADR-0623 处置(①):
    base 曲线实现单一源归 :func:`reward_base_gold`,本函数只剩「P1 键
    当全平面规划曲线」这一申报语义)。**规划近似申报**:决策数学没有
    plane 入参,取 P1 键当通用规划曲线——对 P2/P3 的 r1/r2 轮与真值
    有差(P2r1 真值 5,本投影返 3),差异归属=决策近似口径 vs 记账
    口径,申报面见统一观察架构 §7.1 与 ADR-0623 决策2;等价性锁=
    sr-od-test test_cw_income_single_source(net_income 值域逐位不变)。
    """
    return reward_base_gold(1, round_num)


def net_income(round_num: int, streak_pre: int,
               lost_node_type: str | None = None) -> int:
    """逐节点净收入 Ī(NMF §2「Ī」行;R09 收入三表现算,非 i_bar 常量)。

    **处置申报(统一观察架构方案审 F4-①,ADR-0623 决策2,裁决=委托改造
    +规划近似显式化)**:base/streak 分量已改为委托 T1a 单一源函数族
    (:func:`reward_base_gold` 的 P1 规划投影 + :func:`streak_gold`),
    消费点数值逐位不变(等价性锁在册)。

    - ``round_num``:日程轮号(1 基;开局两轮基础金折半段);
    - ``streak_pre``:**决策前相**连胜数(进轮连胜,奖励轮照发不动计数,
      ADR-0439 引擎口径);
    - ``lost_node_type``:上一轮若为败掉的战斗类节点,其败轮底金在本轮
      轮首补发(battle/encounter/boss → LOSS_GOLD_BY_NODE);非败轮接续
      传 None。**规划近似申报(两处)**:①本参数签名无 plane/round,败补
      只能取类型表底金做规划下界,与记账口径(:func:`loss_compensation_base`
      平面感知键)的差异归属=决策近似,挂玩家确认(ADR-0623 决策3);
      ②现役 6 个决策消费点(mandate_v1 shop.py ×4 / encounter.py / 本模块
      loss_exact 前置)全部传 ``streak_pre=0, lost_node_type=None``——
      败补参数支当前零消费,近似不落值。
    """
    inc = reward_base_gold(1, round_num) + streak_gold(streak_pre)
    if lost_node_type is not None:
        inc += LOSS_GOLD_BY_NODE.get(lost_node_type, 0)
    return inc


# ===== T1a 轮首收入三支·kernel 单一源函数族(统一观察架构 §7-T1/T2 搬迁任务的 =====
# ===== kernel 半部;正本语义=GameState 设计 §4.2 轮首收入行。引擎收入段与 =====
# ===== 实机 live 写端改调本函数族=T1b,本批不动 sim/engine_p1.py)=====


def reward_base_gold(plane: int, round_num: int) -> int:
    """基础奖励金·平面感知键(奖励轮/常规轮共用的 base 分量单一源)。

    键(正本=GameState 设计 §4.2 奖励轮行;真值=economy.md §10.1):
    P1 r1=3 / P1 r2=4(:data:`REWARD_BASE_GOLD_BY_ROUND`,弹窗 VLM 直读
    85/85 零散布);P2r1=5(结构化直读两批独立一致);P3r1 按 5 近似
    (无直读样本,维持挂账);其余轮恒 5。

    **禁按 round_num 单键直查注册表**:P2r1/P3r1 单键误返 3 = 已知
    hazard(注册表 REWARD_BASE_GOLD_BY_ROUND 键是 P1 实测的 round 键,
    不是全平面通用键);本函数是唯一合法取键口,round_base_income 是
    它的 P1 规划投影(见该函数申报)。
    """
    if plane == 1:
        return REWARD_BASE_GOLD_BY_ROUND.get(round_num, _REWARD_BASE_DEFAULT)
    return _REWARD_BASE_DEFAULT


def loss_compensation_base(plane: int, round_num: int, node_type: str) -> int:
    """战斗败轮的补发基项(败补分支的 base 分量单一源)。

    记账口径 = 玩家裁定 2026-09-09「看节点基础奖励」(GameState 设计
    §4.2 败轮行):按**被败节点**的基础奖励取值——平面感知键与奖励轮
    同款,``round_num`` 语义=被败轮节点(败 P1r9 后 P2r1 补发按 P1r9
    口径取键)。

    〔口径冲突挂账·判别已执行〕:旧口径 = LOSS_GOLD_BY_NODE 类型表
    {battle:2, encounter:4, boss:4}(ADR-0439 108 局差分)。仲裁实验
    (分桶重放,tools/cw/loss_comp_bucket_replay.py,146 局语料,
    ADR-0623 决策3)**数据不足以定谳**:判别判据所需的 P1r1/r2 败局阶梯
    样本在语料中不存在(低轮位 bot 恒胜),boss 桶 n=1;且标准节点序把
    「被败节点类型」与「下一节点类型」结构性绑定(battle→encounter→
    reward),差分窗内的类型差分与到账项差分不可分。记录模型**维持
    玩家裁定口径**,待玩家确认(采集口径见 ADR-0623 决策3)。
    """
    return reward_base_gold(plane, round_num)


@dataclass(frozen=True)
class LostNodeRef:
    """被败战斗节点的引用(败补分支的取键输入)。

    ``node_type`` = 引擎 token(battle/encounter/boss,与
    :data:`LOSS_GOLD_BY_NODE` 键同域);坐标系=节点序列台账
    (plane+round_num,跨位面 round 重启)。由调用方在战斗结算段构造:
    仅当上一战斗类节点败(delta<=0)且败态未被消费时传入。
    """

    plane: int
    round_num: int
    node_type: str


@dataclass(frozen=True)
class RoundStartIncome:
    """轮首收入三分支的分解账(实机/sim 记账与决策共读同一份分解)。

    ``branch``:supply/reward/loss_comp/combat 四值——supply=补给轮
    (连胜不动)、reward=奖励轮(连胜照发×倍率)、loss_comp=败补(连胜
    取 0)、combat=常规战斗胜轮(连胜照发×倍率)。分支派发序与引擎
    elif 序一致(supply→reward→败补→常规,GameState 设计 §4.2 行选择
    优先级;奖励/补给轮不发 LOSS_GOLD)。
    """

    branch: str
    base: int            # 基础奖励分量(败补分支=补发基项)
    interest: int        # 利息分量(含息 flat 修饰)
    streak: int          # 连胜分量(已乘 win_reward_mult;supply/loss_comp 恒 0)
    total: int           # 三分量之和

    def as_dict(self) -> dict[str, int | str]:
        """账本行形态(sim 收入段 dict 行与实机遥测行共用的投影)。"""
        return {'branch': self.branch, 'base': self.base,
                'interest': self.interest, 'streak': self.streak,
                'total': self.total}


def _streak_component(streak: int, win_reward_mult: float) -> int:
    """连胜分量 = streak_gold(进轮连胜) × win_reward_mult(四舍五入取整)。

    倍率单一源 = 注册表 STRATEGY_ECONOMY.win_reward_mult(聚合取最大
    不叠乘,cw_investments.aggregate_economy);在册唯一非 1 值=伟大征服
    3.0。**含奖励轮**(GameState 设计 §4.1:win_reward_mult 施于连胜
    分量含奖励轮,消持卡局奖励轮系统性少计——修复 sim 零消费挂账的
    kernel 半部,引擎侧消费=T1b)。
    """
    return int(round(streak_gold(streak) * win_reward_mult))


def round_start_income(
        plane: int, round_num: int, node_type: str, gold: int, streak: int,
        *, lost_node: LostNodeRef | None = None,
        win_reward_mult: float = 1.0,
        interest_flat: int = 0,
        interest_cap: int | None = None) -> RoundStartIncome:
    """轮首收入三支单一源(统一观察架构 §7-T1:同输入必同输出,禁第二份)。

    - 分支派发(与引擎 elif 序同构,supply→reward→败补→常规):
      supply → base+息,连胜不动(补给轮连胜不动,ADR-0439 决策 2);
      reward → base+连胜×倍率+息(连胜照发含 counter0=1);当前为战斗
      类节点且 ``lost_node`` 在场 → 败补(base=补发基项+息,连胜取 0,
      win_reward_mult 不生效);其余 → 常规战斗胜轮(base+连胜×倍率+息)。
    - ``lost_node``:调用方契约=上一战斗类节点败且败态未被消费时传入
      (败态跨奖励/补给轮的归宿——吞掉还是递延——是调用方策略,本函数
      不裁决,待实机实证挂观测期核对项,GameState 设计 §4.2)。
    - ``interest_flat``:息 flat 修饰(狸财经狸每节点固定息,与息帽无关;
      聚合单一源=EconomyEffect.interest_flat_per_node)。
    - ``interest_cap``:resolved 息帽(None→DEFAULT_INTEREST_CAP;归一口
      =:func:`interest_cap_resolved`,禁调用方内联 cap 字面量)。
    - 值域注:奖励/常规轮的 base 经 :func:`reward_base_gold` 平面感知
      取键(P2r1/P3r1 单键误返 3 hazard 在此消灭);r8 位面大奖励
      (ADR-0439 挂账,sim 少发 ~9)与事件金不在本函数辖域(触发面不同,
      调用方单列)。**辖域排除(ADR-0623 决策1)**:gold_per_node/
      gold_per_boss_node/战斗表现条件类三轮首真实金分量(引擎 'invest'
      键单列)签名无槽位,承载方式(分量扩参 or 调用方聚合单列)随 T1b
      定;supply 支 base 取平面感知键=实现选择(正本只写「基础」;现节点
      序 supply 不落 r1/r2 与引擎恒 5 无数值差,节点序变异时两域分叉,
      键语义随 T1b 复核)。
    """
    if node_type == 'supply':
        base = reward_base_gold(plane, round_num)
        streak_amt = 0
        branch = 'supply'
    elif node_type == 'reward':
        base = reward_base_gold(plane, round_num)
        streak_amt = _streak_component(streak, win_reward_mult)
        branch = 'reward'
    elif lost_node is not None:
        base = loss_compensation_base(lost_node.plane, lost_node.round_num,
                                      lost_node.node_type)
        streak_amt = 0
        branch = 'loss_comp'
    else:
        base = reward_base_gold(plane, round_num)
        streak_amt = _streak_component(streak, win_reward_mult)
        branch = 'combat'
    interest_amt = (interest(gold, interest_cap_resolved(interest_cap))
                    + interest_flat)
    return RoundStartIncome(branch=branch, base=base, interest=interest_amt,
                            streak=streak_amt,
                            total=base + interest_amt + streak_amt)


#: 每节点基础收入的近似常量(单一源:cw_sim 收入模型消费)。
#: 边界:基础奖励实际随节点变(VLM 判读 1-1=3/1-2=4,见 docs/game/currency_war/research/economy.md
#: 「基础奖励」行;守卫测试 sr-od-test test_cw_r305_reward_data)——5 是统一近似值,奖励采集成表后替换为查表。
BASE_INCOME: int = 5

#: 败轮收入(节点级固定金;实机 gold 差分实证 2026-08-28,108 局/767 轮:
#: 普通败轮残差众数 2(24/39)、遭遇 4(18/24)、boss 4(8/22,散布大置信中);
#: 见 docs/develop/sr_od/application/currency_war/decisions/0439-sim-economy-income-caliber.md)。
#: 独立常量、**不动 STREAK_GOLD_TABLE**:表是胜轮弹窗真值(streak≥1 域,
#: ADR-0262 锁零触碰);败轮弹窗预期 1 与实发不符,走本表分支。
LOSS_GOLD_BY_NODE: dict[str, int] = {'battle': 2, 'encounter': 4, 'boss': 4}

#: 奖励节点基础收入查表(P1 实测:1-1=3 / 1-2=4,弹窗 VLM 判读 85/85 零散布;
#: 其余轮与全部非奖励节点仍 BASE_INCOME 统一近似)。**与奖励轮 streak 分量成对**:
#: BASE_INCOME=5 恰好盖住奖励轮照发的连胜金 table[0]=1——单独改 streak 不改本表
#: 会让奖励轮多发 1(ADR-0439 成对约束)。
REWARD_BASE_GOLD_BY_ROUND: dict[int, int] = {1: 3, 2: 4}

#: P1 之外各轮的基础奖励统一近似值(与 :data:`BASE_INCOME` 同源同值,禁在本
#: 模块另写裸 5;P2r1=5 是 economy.md §10.1 结构化直读两批独立的定谳值,
#: P3r1=5 是无直读样本下的近似、挂账维持——见 :func:`reward_base_gold`)。
_REWARD_BASE_DEFAULT: int = BASE_INCOME

#: sim 收入口径版本(独立披露,不占 cw_coarse_battle.COARSE_CALIB_VERSION——
#: 那是粗模型战斗引擎校准的版本,收入口径在 cw_economy/cw_sim 收入段,另一子系统)。
#: 跨批次对比先核 manifest.economy_calib_version(局终指纹核对锚,与
#: 既有粗模型版本披露同机制)。
ECONOMY_CALIB_VERSION: int = 2
#: v2(ADR-0447):事件金表按实机逐轮金轨迹反馈整定(状态分布校准总闸),
#: 数值见 engine_p1.EVENT_GOLD_BY_ROUND 注释;v1 旧表(奖励球残差近似)
#: 批次与本版不可比,跨批对照须 economy_calib_version 一致。

# 息权重算账(gold 0-15 < 升级 cost 36-48)→ 卡低 level → 弱 comp。息 delta(50vs0)=20
# > 牌 synergy 10 → bot 攒到 50(息引擎)+ 花超额买/升级 = 经济统一论(若只取 2.0,息 delta=10
# = 牌 synergy 10 → bot 无差别 → 买不攒)。
# streak 经济(C 杠杆 2;fixture 核实 2026-08-11 结算「连胜×N」前缀=方向 → streak 接线):
# ⚖️ **单边**(ADR-0128 #1,2026-08-15:货币战争无连败补偿,vs TFT)——只计连胜方向,
# 连败 0 分(旧「对称取 magnitude」描述已废,行为自 0128 起就是单边;economy_score:306 同源)。
STREAK_WEIGHT: float = 2.0            # 每档 streak 的经济分(占位,待实玩校准)

STREAK_CAP: int = 5                   # streak 经济封顶档(连胜金一般 ≤5 档)

# streak 带符号(连胜 + / 连败 −,结算源 session.last_streak 方向可靠);连败 fold 半已由 HP-gating 覆盖(02 R2-4b)。
# 「连胜 ≥2 破息」旧阈值常量已删(P43 §⑤ 处死名单:与已证破息-保息判据
# 冲突的未核经验值;决策语义现由息线判据默认承载,激活腿 Δp 通道
# 封锁——登记 = ADR-0599 §F3,math_proofs P43)。

# 连胜-保息抉择(攻略专题「连胜与卖血抉择」三变量模型,663 帖精读实证):
# 攻略明文两分支 —— 已连胜→破息保连(#205「如果连胜就多D几个,利息保3」息档降到 30;
# #46「小搜争取连胜,不顺果断存钱」);未连胜+血安全→保息(#151「卡满50利息,大不了先输着先」;
# #145「优先留着吃利息,前期掉点血没事」)。「来牌顺」= 商店有可买战力件(shop_supply,无牌破息也无处花)。
# ⚠️ 用户定调(定性):**攻略的「卖血不低于40」不是急救触发线,是运营质量的
# 报警线** —— 血低于它 = 前面破息决策已经错了;此时花光挺节点是「给前面的策略失败擦屁股」,
# 断息后经济可能永远撑不起整局(死亡螺旋:血低→花光→息断→板半成型→又掉血→又花光)。
# **目标是长期通关,不是苟住多少个节点**。故血低的正确响应 = 最小必要支出止损 + 息引擎
# 尽量保住,真 ALL IN 只留给「位面末最后一战」(赢了带血/板进下位面,不存在后续经济问题)。
# 该常量语义 = 运营质量报警线(策略层诊断/复盘用),不是 spending 触发器。
HP_QUALITY_ALARM: int = 40            # 运营质量报警线(血低于此 = 前面破息决策错;诊断用)
#: 攒息门 hp 急救分位——血低于 职级阈值×此分位
#: = 真活不下去(急救通道 _phase_weights 接管);中危带(此线与阈值之间)按用户定调
#: 「血低是报警非触发」维持攒息,不在此门破息(观察点:中危带持续漏买的场景留回放核)。
HP_DISTRESS_FRAC: float = 0.5

LEVEL_WEIGHT: float = 6.0             # 每级(相对期望)的分。2026-08-04 提权(3→6):bot 不升等级


# —— 购买经验决策 helper(ADR-0129;机制常量 XP_TO_NEXT_LEVEL/XP_PER_BUY 在 cw_state 单一源)——
# ⚠️ 本接缝族签名已切 GameState(W6 波 4;波 2 落码申报的
# 「本接缝族签名切换随 mandate_v1 装配面切换批同波贯通」兑现——见
# refresh_ev_budget docstring 过渡注)。字段读统一经容器读口单一源
# (kernel/cw_game_state 决策面公共读口),禁各消费点自写兜底。

def _strategy_economy(bs: GameState) -> EconomyEffect:
    """当前持有投资策略的聚合经济效果(ADR-0131;active_strategies → 数值效果,策略层算账)。"""
    return aggregate_economy(list(bs.active_strategies.value or []))



def _refresh_cost(state: CwSimFrame, refresh_used: int) -> int:
    """第 refresh_used+1 次刷新的真实花金(ADR-0131):策略免费额度(如 加油站 每节点 1 次)内 = 0。

    (遗留评分面消费;生产刷新费单一源 = refresh_cost_effective,
    本函数零生产调用;旧帧签名 = 过渡期遗留形态,随遗留消费面
    退役收口。)
    """
    if refresh_used < aggregate_economy(
            list(getattr(state, 'active_strategies', None)
                 or [])).free_refresh_per_node:
        return 0
    return SHOP_REFRESH_COST


def refresh_cost_effective(state: CwSimFrame, refresh_count: int,
                           registry: DecisionV2Registry | None = None,
                           bs: GameState | None = None) -> int:
    """刷新 EV 判据用的参数化刷价(基价直通)。

    (原 W875 长线利好折价臂已随 longterm_refresh 开关族删除——旧方案
    清退批,清查报告 OLD_MIX_AUDIT §1.3;``refresh_count``/``registry``
    参数保留占位,消费点 ev/posture_release/scoring 调用零改,行为与
    删除前默认关逐位一致(恒基价)。机制真值(长线利好 30 刷后 1 金)
    仍在 cw_invest_data。)

    消费切换(迁移批次二,§3.3.4 遗留消费面申报的搬迁归宿):``bs``
    给定时刷价 = GameState.shop_refresh_cost 现场识别值(ADR-0622 观察通
    道,免费帧不写保证该域不出 0);None = 未读到 → **建模基价
    SHOP_REFRESH_COST 显式消费缺省**——原 ``or 2`` falsy 兜底形态的消灭
    形态:数值恒同,语义从「静默兜底」升为「声明式建模缺省」。``bs``
    未给(存量调用面)走 state 契约(恒基价,行为零变化)。
    """
    if bs is not None:
        _v = bs.shop_refresh_cost.value
        return int(_v) if _v is not None else SHOP_REFRESH_COST
    return state.shop_refresh_cost or SHOP_REFRESH_COST



def xp_click_cost(bs: GameState) -> int:
    """一次「购买经验」单击花金(观察优先兜底逻辑,strategy-env-impacts §2
    通用模式 1;ADR-0131;折扣语义修复正本 = ADR-0632;W6 波 4 切容器帧)。

    两支语义(来源凭 ``bs.level_up_cost`` 是否有值判别):
    - **显示价支**(OCR 实读):传入值为最近备战帧观察价,游戏侧已算好
      全部折扣(商业间谍/成长的快乐等)→ **原样直通不再减**,下限 0;
      0 与缺省同义走兜底支(falsy 契约,与全部既有调用面一致)。
      「最近观察值」= 写端仅在备战观察权重开启帧更新(cw_observation
      read_level_up_cost),非本帧保证;取数后才拿卡/跨等级门档位的过期
      窗口方向可自愈、有界(下一备战帧同屏重读)。
    - **兜底支**(观察缺省):函数内减折扣 = 基准 XP_CLICK_COST_FALLBACK
      (恒 4=用户口径,非按等级)−[xp_buy_cost_discount + 等级门折扣
      (成长的快乐:xp_click_discount_from_level,``level_of(bs) ≥
      xp_click_discount_from_level_at`` 时生效;哨兵 0=未持有)],
      max(0) 钳。

    出域声明:奋斗协议(xp_buy_hp_cost)血本位下购经验币种切换为血,
    本金费函数不适用(血闸独立车道 blood_xp_gate 承接);按钮显示非金
    数值时显示价支读数同样出域,不在本函数补模。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        level_of,
    )
    lvl_cost = bs.level_up_cost.value
    if lvl_cost:
        return max(0, int(lvl_cost))
    _level = level_of(bs)
    eff = _strategy_economy(bs)
    discount = eff.xp_buy_cost_discount
    if (eff.xp_click_discount_from_level_at
            and _level >= eff.xp_click_discount_from_level_at):
        discount += eff.xp_click_discount_from_level
    return max(0, XP_CLICK_COST_FALLBACK - discount)



def clicks_to_next_level(bs: GameState) -> int:
    """从当前 XP 到升 1 级还需的单击次数(xp 未知按 0 进度向上取整;满级返 0;
    W6 波 4 切容器帧)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        level_of,
    )
    _level = level_of(bs)
    if _level >= MAX_PLAYER_LEVEL:
        return 0
    xp_v = bs.xp.value
    if xp_v:
        cur, need = int(xp_v[0]), int(xp_v[1])
    else:
        cur, need = 0, XP_TO_NEXT_LEVEL.get(_level, 4)
    return max(0, -(-(need - cur) // XP_PER_BUY))


# ===== [40]② 血本位 XP 购买支付能力闸(ADR-0578;判据与模式解析单一源在
# ===== kernel,prep 批入口与 cw4 三消费位同源消费)=====

def blood_xp_full_clicks(level: int) -> int:
    """下一级**全量击数** = ⌈XP_TO_NEXT_LEVEL[level]/XP_PER_BUY⌉([40]② 裁定字面
    「下一级血成本(⌈need/4⌉×6)」的击数项;ADR-0578 N1 拍板全量口径)。

    - 全量口径先例 = ``cw_plane_table.clicks_to_level``(同式,xp 结转忽略);
      本函数与它的差异 = 权威表逐字(无 1/2 级 _XP_NEED 先验补全)。
    - 与 ``clicks_to_next_level``(剩余口径 ⌈(need−cur)/4⌉)**语义不同,闸不消费
      该函数**:cur>0 是常态(买牌 XP 直抬进度 + 购经验溢出结转,cw_state
      .xp_apply_clicks),剩余口径系统性压低门槛、方向恒向放行,与 [40]②
      「否则停」的保护目的反向。
    - 满级分支(R1):level≥MAX_PLAYER_LEVEL → 0 击(购买经验无效,与
      cw_state.xp_apply_clicks/clicks_to_next_level 的满级返 0 同语义)
      ——分支必须在公式本体,否则字面公式对满级产出 ⌈兜底4/4⌉=1 击的
      6 血门槛,与「恒放行」申报分叉。
    - 1/2 级(权威表未收录,游戏内近乎白送)按兜底 need=4 → 1 击,与
      clicks_to_next_level 既有兜底同语义。
    """
    if level >= MAX_PLAYER_LEVEL:
        return 0
    return -(-XP_TO_NEXT_LEVEL.get(level, 4) // XP_PER_BUY)


def blood_xp_gate(hp_trusted: int | None, hp_readable: bool,
                  level: int, cost: int) -> bool:
    """[40]② 血本位 XP 购买支付能力闸(纯函数;ADR-0578)。

    判据(裁定字面):血余额 ≥ 下一级血成本(⌈need/4⌉×6)才买经验,否则停。
    ``hp_trusted ≥ blood_xp_full_clicks(level) × cost``;返回 True=放行。

    - 授权链:闸读 hp 的授权 = [40]② 本身即用户逐项确认(2026-08-31 OPEN-6
      裁定 + 同日三次简化「不留安全量」)+ 00_framework §3 硬闸门条款。与
      [39] 的辖域分界:[39] 禁 hp 作**运营质量信号**驱动决策;本闸是**支付
      能力检查**——血被选卡变成 XP 的支付币种后,闸只回答「买不买得起下一级」,
      不回答「该不该转型/止损」。两裁定并存不冲突(后者立法在后且更具体)。
    - hp 不可信帧 fail-closed 返 False:沿 ``cw_discipline_rules
      .blood_budget_levelup_blocked`` 同面同论证(误放=血线内追级,误拦=少
      升一级,非对称)。``hp_readable`` = 该帧 hp 决策可信位(调用方经
      ``cw_discipline_rules.hp_decision_trusted`` 解析后传入)。
    - 本函数**禁读** hp_pay 遥测(ADR-0577 隔离申报):hp 输入 = 最近可信备战
      帧值,与 P21 闸同一决策输入。
    """
    if not hp_readable:
        return False
    if hp_trusted is None:
        # hp 无真值帧 fail-closed(ADR-0495 消费点对 None 一律保守):误放与
        # 误拦代价非对称,同 blood_budget_levelup_blocked 的 None 支。
        return False
    return hp_trusted >= blood_xp_full_clicks(level) * cost


def blood_xp_gate_for(bs: GameState | None,
                      session: StrategySession) -> bool:
    """血闸消费面适配(mode 解析 + 容器帧输入接线;prep 批入口与 cw4
    三消费位共用,ADR-0578)。

    - 金本位(session 无 active 血本位卡,``cw_investments.blood_xp_mode`` →
      None)→ True 直通:金模式升级零改动([40]② 辖域 = XP 购买通道的**血**
      支付形态)。
    - bs 缺席 → False fail-closed(与判据本体 None 支同论证)。
    - hp 消费 = 政策层读口 ``decision_hp`` 门后值 + ``hp_decision_trusted``
      可信位(统一 state 迁移波 2 起单一读口,消费同门 ADR-0583 §2.4):
      与 P21 闸(``blood_budget_levelup_blocked``)同面同输入;店开态 hp
      结构性不可见时容器沿用最近备战帧可信值(P21 同帧正常工作,
      复盘 15 帧实证);level 取容器读口。
    """
    from sr_od.application.currency_war.kernel.cw_investments import (
        blood_xp_mode,
    )
    mode = blood_xp_mode(session)
    if mode is None:
        return True
    if bs is None:
        return False
    from sr_od.application.currency_war.kernel.cw_game_state import level_of
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        hp_decision_trusted,
    )
    from sr_od.application.currency_war.kernel.cw_hp_policy import decision_hp
    return blood_xp_gate(decision_hp(bs, session), hp_decision_trusted(bs),
                         level_of(bs), mode[1])



#: 刷新基价【注】= 赋值别名,非第二源:正本 = ``cw_state.REFRESH_COST_BASE``
#: (游戏定义真值:实付恒 2 金,不随金位/次数/等级变,ADR-0456 三流对账
#: 定谳,出处注在彼处)。本名保留 = 存量消费面(proof/budget/本模块)零迁移;
#: 改值只改 cw_state 正本,禁在此另写数值。
SHOP_REFRESH_COST: int = REFRESH_COST_BASE


# (通用升级曲线 _DEFAULT_LEVEL_GOAL 已退役 2026-09-04,「未证即退役」裁定:
# 旧值 = auto-chess meta 社区先验(前期 roll 找低费核心→中期 5-7 level_up→
# lv8 roll 找 5 费→lv9 stable),无游戏定义或证明出处。保守缺省:comp 未填
# level_plan 时不退回通用曲线(该回退路径载体已删),升级压力仅由
# 节点地板(get_node_goal,预算收权核)+ 淘金客姿态等已证判据辖。)


def _expected_level(round_num: int, plane: int) -> int:
    """阶段期望等级(里程碑刻度,663 帖攻略精读实证)。

    【拟】社区先验待证挂账:本曲线处置 = 立证明骨架
    (docs/develop/sr_od/application/currency_war/proofs/p58-expected-level-schedule.md 草案,
    由游戏定义量——XP 费用表/收入日程/出战位解锁/商店刷率峰值级——
    派生等级日程),证明完成前数值维持现状;届时按证明输出重derive 或退役。

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
                                # 本函数只产 level/adaptive/interest(ADR-0465)
    action_focus: str = ""      # 描述辅(d_search/chase_star/rush_level;指导动作偏好,不直接驱评分)
    #: DP 授权的可刷次数上界(三方预算合并:随 NodeGoal 下传,消费侧与
    #: plan 层 _refresh_cap 合并——合并语义单一源=decision_v2.posture_release
    #: 模块注释:release 是义务(下界),DP/plan 是许可(上界),义务激活时
    #: 义务优先,未激活时许可取交)。None=无 DP 信息(先验 fallback;不参与
    #: 合并,许可侧原值)。
    refresh_budget: int | None = None
    danger_d: bool = False      # 占位从未被读(见上)


# ⚖️(2026-08-18 用户定夺):旧 _DEFAULT_NODE_PLAN 区间表**已删**。
# 历史:V4.4 先验表 → ADR-0126 用 11 局 bot live「校准」(P1末7/P2早8)→ 0126 被三重降级
# (0127 H4 疑幽灵锚点/0129 等级观测污染/2026-08-18 单局相关≠基准)。ADR-0155 DP 影子接缝
# 切流(ADR-0208)后 live 全部走 DP,该表只剩异常回退一条活路;失败面穷举(删除前评审)仅剩
# MemoryError + 开发期注册表手误(运行时游戏数据不进台账链;未注册策略名静默跳过)→
# **保留脏表回退比停机更危险**(静默掉回 0126 节奏 = 看着在跑实际在错)。删除;
# DP 失败/越界 → _expected_level 平滑先验 + adaptive(V4.4 干净先验,非 0126 数值)。
# 等级基准权威 = 用户口述定夺(docs/game/currency_war/research/economy.md §7 阶段经济共识;
# 息引擎优先与中途过渡 lv5-6 条)+ XP 反推真值。


def get_node_goal(plane: int, round_num: int, *,
                  gold: int | None = None, level: int | None = None, hp: int | None = None,
                  committed: bool = True,
                  strategies: list[str] | None = None) -> NodeGoal:
    """查 (plane, round) → NodeGoal(ADR-0465:确定性预算核单一供给)。

    姿态从预算收权核涌现(原 DP 解供给已退役,BLUEPRINT §3
    裁决;git 历史为 prior art):排程升级 → level/rush_level;刷新预算
    >0 → adaptive/d_search;两者皆无 → interest/hold。供给在任意帧恒有
    定义(预算收权迁移前预验尸 D0 契约:None 级联面消灭),仅传参不全(迁移漏点)时退
    ``_expected_level`` 平滑先验 + adaptive(记 [cw-seam] debug 证据)。

    三档 spend_mode 与决策核同源:level/adaptive/interest 的判据单一址
    = 本模块两接缝(schedule_upgrade/refresh_ev_budget,期 0b 自
    decision_v2.economy_cycle 下沉,R4)——本函数是其标量投影;'release' 档
    不经本函数(帧级态,单一源=decision_v2.posture_release 经 session
    通道)。
    """
    _partial = (gold, level, hp)
    if any(v is not None for v in _partial) and None in _partial:
        log.debug('[cw-seam] get_node_goal 部分传参(%s)→ 走先验 fallback;迁移漏点排查',
                  ('g' if gold is not None else '-') + ('l' if level is not None else '-')
                  + ('h' if hp is not None else '-'))
    if None not in (gold, level, hp):
        # 标量投影容器:直接按入参构造最小决策容器(供给核只读经济/板面
        # 字段;无 session、无现成容器)。字段契约单一源 =
        # kernel cw_game_state.scalar_projection_state(对旧「惰性构造
        # CwSimFrame + 过渡桥装箱」投影的逐字段镜像;旧载体已删)。
        # session=None:nodes_of_plane 走缺表回退先验 9(一次性告警即记档)
        # → h=9−r 常 >0,R* 窗口分量在投影容器**照常储蓄**(预算收权攻击
        # 审读 F6b 纠偏:原注释「投影帧不储蓄」与实现不符;方向保守无害)。
        # ⚠️ 结构性边界(ADR-0598 申报,不扩修):下行两接缝核以
        # session=None 调用 → 息帽 resolved 链恒 DEFAULT(base cap),
        # 持息帽卡局的本投影判据按 base 口径——接缝无 session 入参
        # (标量投影形态,消费面 = entry 兼容调用,量级有界),扩修
        # 随该调用面的 session 通道批。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            scalar_projection_state as _proj,
        )
        _st_bs = _proj(gold=gold, level=level, hp=hp, plane=plane,
                       round_num=round_num, strategies=strategies)
        _rolls = min(6, refresh_ev_budget(_st_bs, None))
        if schedule_upgrade(_st_bs, None):
            return NodeGoal(min(10, level + 1), 'level', 'rush_level',
                            refresh_budget=_rolls)
        if _rolls > 0:
            return NodeGoal(level, 'adaptive', 'd_search',
                            refresh_budget=_rolls)
        return NodeGoal(level, 'interest', 'hold')
    return NodeGoal(_expected_level(round_num, plane), "adaptive", "rush_level")


# ⚖️(2026-08-18):旧 ADR-0155 影子接缝开关 HORIZON_SEAM_ACTIVE **已删**——切流(ADR-0208)
# 完成后 DP 是唯一姿态源(同一裁决连带删除 0126 区间回退表,见 get_node_goal 注释),开关无消费点。
# 历史:切流依据(ADR-0208)= 160 局对拍「表 hold→DP level」P1 高金段系统性分歧 + 六局 P1
# boss 稳定损 20-36 血→P2 残血开局即崩。回滚方式 = revert 预算收权迁移提交。



def economy_score(state: CwSimFrame, economy_mode: str) -> float:
    """经济健康度:利息(存金到 50)+ 等级合适度 + streak 档位金(C 杠杆 2)。

    economy_mode 只调利息项(rush_level 弱化守息、interest_first 强化守息),等级项不变。
    阶段保血(前期/低血 → 经济降权)由 evaluate 的 _phase_weights 统一处理。
    streak 单边计分(ADR-0128 #1:货币战争无连败补偿,只计连胜;连败 0 分);fold(连败保息)已由 HP-gating 实现(02 R2-4b,用户 2026-08-12 确认:血量安全→fold/不安全→急救,经 _phase_weights/_refresh_cap HP gate)。
    """
    # ADR-0131(投资策略效果进经济分):利息上限覆写(开源节流 9 档/利息上调 10 档/买断制 0)+
    # 每节点固定给金(定期福利 2/节点 ≈ 白拿 0.2 档息)+ 连胜奖励倍率(伟大征服 ×3 → streak 更值)。
    # (遗留评分面:旧帧签名过渡形态,随遗留消费面退役收口;
    #  _strategy_economy 已切容器帧,本面就地内联同源聚合,禁再引接缝。)
    _se = aggregate_economy(list(getattr(state, 'active_strategies', None) or []))
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


def effective_refresh_prob(bs: GameState, level: int, cost: int) -> float:
    """轮岗感知的有效刷新概率单一源。

    消费点 = mandate_v1 出口③ A 支对账(shop.py),禁第二套对账语义——
    「bar=0 ∧ 表值>0」形态两消费点
    曾相反(出口③判确证零/economy 判表值非零),已按本优先级统一。
    优先级:
    - refresh_probs 不可得(None/非 dict)→ 基线表(read_refresh_probs
      契约「读不到 → None 退基线」;「部分 dict」形态在上游
      parse_prob_bar 契约(全 5 键或 None)下当前不可达,出现则按
      部分键逐键回退,不整表弃用);
    - 结构内缺键 → 基线表(缺键禁当确证零);
    - 键在但 ≤0 → 基线表(轮岗只翻倍不归零,概率条 0 = 采样不可信,
      同款 `or` 回退;机制出处 = 注册表 `cw_invest_data.py`
      PlazaPortal 114「轮岗」:「备战阶段开始时,使一个随机费用的刷新
      概率翻倍」——翻倍不归零);
    - 键在且 >0 → 实读真值(轮岗翻倍档直用)。
    """
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    # refresh_probs = payload 域(W6 波 4 切容器):离屏/缺读 None → 基线表
    # (与旧帧 None 语义同门)。
    _payload = bs.shop.value
    rp = _payload.refresh_probs if _payload is not None else None
    if not isinstance(rp, dict):
        return refresh_prob(level, cost)
    bar = rp.get(cost)
    if bar is None or bar <= 0:
        return refresh_prob(level, cost)
    return bar



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


# ===== 经济循环接缝族(自 decision_v2.economy_cycle 下沉;§3.3-①a/①b) =====
# 原址:decision_v2.economy_cycle(kernel→decision 断环:本文件是 kernel 桶,
# cw_economy.get_node_goal 标量投影消费两接缝,原函数体内懒 import 决策包
# 成环)。schedule_upgrade 纯移动;refresh_ev_budget 最小重构——应急谓词
# is_emergency 一并下沉本文件(一行纯谓词,decision_v2.filters 改 import
# 重定向,单一源不破),函数体零行为变化(等价锁=sr-od-test
# test_cw_w695_economy_seam.py + 既有经济接缝桩点测试重钉)。

#: 刷新通道容量上界(刷数;原 DP 求解面动作上限 6 刷同源(git prior art),
#: 不另造第二把尺)。自 economy_cycle 随接缝族同迁(单一源在本文件)。
REFRESH_ROLL_CAP: int = 6


def is_emergency(bs: GameState,
                 session: StrategySession,
                 registry: DecisionV2Registry) -> bool:
    """应急触发(绝对 HP 档简版;redesign §5.4 Phase A 口径)。

    单一源在本文件(kernel)。hp 消费 = 政策层读口 ``decision_hp``
    门后值(统一 state 迁移波 2:消费同门 ADR-0583 §2.4,旧链由上游
    施门间接保证,读点显式施门后门幂等保证行为一致);``session``
    形参随波 2 签名切换补入(hp 消费函数统一持 session 装配结算锚,
    依据 = ``blood_budget_levelup_blocked(bs, session, registry)``
    同形态,禁函数内私有第二门)。None(无真值且窗外)= False 保守
    (ADR-0495:应急带不误触发)。"""

    from sr_od.application.currency_war.kernel.cw_hp_policy import decision_hp
    hp = decision_hp(bs, session)
    return hp is not None and hp <= registry.emergency_hp


def _registry_of(session: StrategySession) -> DecisionV2Registry:
    """接缝函数的注册表解析(A/B 注入面:strategy_state_of(session).v3_registry 显式注入
    优先,缺省落 DEFAULT_REGISTRY——缺省栈无注入臂,P6 契约同 prep_brain
    装配签名)。"""
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        strategy_state_of,
    )
    reg = getattr(strategy_state_of(session), 'v3_registry', None)
    return reg if isinstance(reg, DecisionV2Registry) else DEFAULT_REGISTRY


def _pop_slot_indicator(bs: GameState) -> bool:
    """ΔV_pop 指示项(P39 修订式):板满(cap 满)∧ bench 有 2★ 等待件。

    消费位 = schedule_upgrade ①臂 / _upgrade_ul_threshold_ok 翻转分量 /
    mandate_v1 criteria/levelup._realize_chain_ready(P72 支A;ADR-0576)。
    (原「三副本有意复制、改谓词三处同改」纪律随 W6 波 4 签名切换收敛为
    本单一源——strategy 层消费位同批改委托,漂移风险由单源天然消解。)
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
        deployed_count_of,
        max_units_of,
    )
    if deployed_count_of(bs) < max_units_of(bs):
        return False
    return any(b is not None and (getattr(b, 'star', 1) or 1) >= 2
               for b in bench_slots_of(bs))


def _upgrade_ul_threshold_ok(bs: GameState,
                             session: StrategySession) -> bool:
    """② 臂 U_L 阈值检验(升级判据形式二修正①;裸直觉补检验)。

    升级 iff ``c_eff·(E(D|L) − E(D|L+1)) + ΔV_pop > U_L + C_int``——
    全部游戏定义量:c_eff=刷价现读;E(D|L)=expected_refreshes_for_card
    (目标核心 2★ 完成档,owned=j 折算,REFRESH_PROB 池参数);U_L=
    clicks_to_next_level×xp_click_cost(XP 表/OCR 实读);C_int=息损
    P47 L 递推(loss_exact,gold 支 U_L 后 R_剩余 轮,Ī=收入日程现算;
    cap 参数 = cap_resolved_of_session 现读——裸缺省 5 在息律投资
    cap=10 局会低估 C_int,息帽三源归一)。
    ΔV_pop 按 P39 式 = w·1[板满 ∧ bench 有 2★ 等待件](w 待标定禁计值
    → 指示=1 时视为翻转项,方向门;指示=0 时纯概率账须独自过阈)。
    反例锚:希儿 lv7 省刷费 28 < 升级金 40,纯概率账亏 12,
    靠人口位翻转——缺本检验的裸「峰值级>当前级」会在该带过度升级。
    R_剩余视界=r_remaining(决策帧现算,禁写死;本模块下沉实现)。

    单核代表降级申报:规格的 E 为缺件集 ΣE_i(strategy-docs
    11 篇 §3);本实现取单目标核心代表——缺件集成员装配需 strategies
    侧 line_members,违背「kernel 禁 import strategies」桶边界,故申报
    降级而非静默偏差。保守性边界:多成员同受升级受益帧 benefit 低估
    → 检验偏严(保守向);成员在 L+1 概率回落(E 恶化)帧单核可能
    高估净受益(非保守端,边界注)。

    ΔV_pop 指示项谓词(板满 ∧ bench 有 2★ 等待件)与 schedule_upgrade
    ①臂**有意复制**——两处是同一 P39 指示项在「检验内翻转分量」与
    「排程触发①」两个消费位的落点,语义单一源 = P39 修订式;改任一处
    须同步另一处(同步锚对:本函数 / schedule_upgrade ① 臂)。
    第三消费位(ADR-0576):mandate_v1/criteria/levelup.
    ``_realize_chain_ready``(P72 支A 兑现链放行)消费同一指示项——三
    副本逐字一致,改谓词三处同改;三副本一致对拍锁候批(登记面申报,
    防漂移无锁位)。
    """
    import math as _math

    from sr_od.application.currency_war.data.cw_shop_odds import (
        expected_refreshes_for_card,
    )

    # ΔV_pop 指示项(P39 修订式;与 schedule_upgrade ①臂谓词成同步锚对,
    # 见 docstring 末段——改谓词两处同改;第三消费位 = criteria/levelup.
    # _realize_chain_ready(ADR-0576),三处同改)
    if _pop_slot_indicator(bs):
        return True

    level = level_of(bs)
    core, cost = _target_core_cost(session)
    j = _owned_core_copies(bs, core) if core else 0
    e_l = expected_refreshes_for_card(level, cost, target_star=2, owned=j)
    e_l1 = expected_refreshes_for_card(level + 1, cost, target_star=2,
                                       owned=j)
    # 显式守卫:升级后反不可追(e_l1==0 且 e_l>0)⇒ False。前提声明:
    # 现行 REFRESH_PROB 表满足「一旦出牌永不消失」的单调性(低级不出
    # 的费档升级后才出现,不反向),故该形态在现表下不可达、守卫不
    # 触发;池突变使表整体重生成(§8 resolved input)或换表后若失去
    # 该单调性,此守卫生效,防止把「升级后 E 归零」误读成无穷收益。
    if e_l1 == 0.0 and e_l > 0.0:
        return False
    if not (_math.isfinite(e_l) and _math.isfinite(e_l1)):
        return e_l <= 0.0 < e_l1     # 当前级不可追而上级可追:纯解锁收益
    benefit = refresh_cost_effective(None, 0, bs=bs) * (e_l - e_l1)
    if benefit <= 0:
        return False                 # 概率不升反降(内峰回落档):无收益面
    u_gold = clicks_to_next_level(bs) * xp_click_cost(bs)
    if u_gold <= 0:
        return True                  # 满级/零费边界:成本侧空,收益即过
    rounds = r_remaining(session, plane_of(bs), round_num_of(bs))
    ibar = net_income(round_num_of(bs), 0)
    c_int = loss_exact(gold_of(bs), u_gold, rounds, ibar,
                       cap=cap_resolved_of_session(session))
    return benefit > u_gold + c_int


def schedule_upgrade(bs: GameState, session: StrategySession,
                     registry: DecisionV2Registry | None = None) -> bool:
    """排程升级判据(确定性费用查表核;蓝图 §3.4 R4 接缝,ADR-0465)。

    ``registry``:显式注入优先(A/B 注入面,P6 契约:同一调用链全部接缝
    必须传**同一个** registry 实例——prep_brain._budget 单源装配);
    缺省落 _registry_of(session) → DEFAULT_REGISTRY。**cap 归一注**:
    本函数的 ② 前置息线与 U_L 检验息损 cap 已归一到
    ``cap_resolved_of_session``(session resolved 链)单一源,registry
    注入不再移动这两处——registry 仍辖同链其余接缝(refresh_ev_budget/
    reserve_cap 的预算面)。
    规则集 = 规则倡导审读 §1.3/§2-R4(机制常量直算,零标定权重);**预告态契约**
    (预算收权迁移前预验尸 D1 契约):排程只回答「要不要开始攒」,不以当帧可负担为前置——
    付不付得起是执行层的事(``ev.levelup_ev_basis`` 可负担性入口门),
    排程判据若收窄成「付得起才排」会造成 R* 塌缩 → 义务花光 → 更排不上
    的自我强化升级迟到循环(DP 无此失败模式:其 level_up 判定不依赖当帧
    是否看得见目标)。

    触发(任一,判据单一址=R4:本函数被 R* 储蓄分量(reserve_cap)、
    arbiter 金地板授权、EV 升级授权 ② 臂三处共调):
    ① 人口位([33]):cap 满 ∧ bench 有成型件(2★)等上场——升级后能
       立即部署,当轮兑现战力,为最高义务。**辖域 = 战斗帧**(2026-09-08
       奖励帧策略审查):「当轮兑现」的兑现对象是本帧的战斗,奖励帧
       无战斗 → 当帧升级与推迟到下一备战帧升级,2★ 的部署时点对下一场
       战斗相同,本臂收益面在奖励帧不增益;奖励帧行为由 ADR-0580 规则①
       升级抑制先辖(抑制判据置于臂计算之前短路)。辖域注不改谓词本体
       (M3 消费位 = criteria/levelup._realize_chain_ready 同步锚对,
       同款辖域注见彼处);奖励帧政策的命题化归审查建议②命题批。
    ② 概率级([3]/[7]):目标核心概率峰值级 > 当前级 ∧ 息引擎已立
       (g ≥ 息线,[12] 息引擎前置)∧ **U_L 阈值检验**(形式二
       修正①:``c_eff·(E(D|L)−E(D|L+1)) + ΔV_pop > U_L + C_int``,
       装配=``_upgrade_ul_threshold_ok``;裸直觉缺此检验会在小移位带
       过度升级——希儿 lv7 反例,见该函数 docstring)。
    禁升条件([12]/[32]):息引擎未立不追级(② 的前置即此);空升级
    不升(① 触发本身即「有件可上」,无空升级面;② 是概率抬档语义,
    不涉部署)。
    **规则文本偏差披露(预算收权攻击审读 F2)**:规则倡导审读 §2-R4 规则 2 原文有第三合取
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
    if refresh_invest_active(type('_S', (), {'active_strategies': bs.active_strategies.value or []})()):
        return False    # 淘金客姿态:升级通道退役(sim 注入臂实证;谓词单一址)
    # ① 人口位:cap 满 ∧ bench 有成型件(2★)等上场([33]/[32](a));
    # 谓词单一源 = _pop_slot_indicator(原「有意复制三副本」纪律随本批
    # 签名切换收敛为 kernel 单一源——第三消费位 criteria/levelup
    # 同批改委托,同步锚对语义由单一源天然承载)
    if _pop_slot_indicator(bs):
        return True
    # ② 概率级:息引擎已立 ∧ 目标峰值级在当前级之上 ∧ U_L 阈值检验
    # (升级判据形式二修正①:升级 iff c_eff·ΔE + ΔV_pop > U_L + C_int;
    # 裸「峰值级>当前级」直觉缺此检验会在小移位带过度升级——希儿 lv7
    # 省 28 < 升 40 反例,纯概率亏 12)
    # 息线口径 = cap_resolved_of_session(session resolved 链)单一源
    # (息帽三源归一:旧 reg.interest_cap×10 与 session 链
    # 不同源——A/B 旋钮辖 decision_v2 预算面,不辖本前置)
    if gold_of(bs) < saturation_line(cap_resolved_of_session(session)):
        return False
    if _target_peak_level(bs, session) <= level_of(bs):
        return False
    return _upgrade_ul_threshold_ok(bs, session)


def _vd_core_of(session: StrategySession) -> str:
    """V_D/V_level 共用的目标核心解析(scoring.vd_target_core 同源;
    自 decision_v2.ev 下沉(schedule_upgrade 的目标核心解析链
    依赖;本模块零 decision 依赖,decision_v2.ev 改 import 重定向)——
    ev 不 import decision_v2 包内模块的判据复刻惯例随单一源归位终结)

    ⚠️ 批 0 裁决(处死计划 §3 批 0 第 4 项,docs/develop/currency_war/archive/redesign/
    03_legacy_cleanup_plan.md):本函数懒 import 的 IntentionState/intention_core
    属**决策半部**——消费意向锁定状态机的 phase/locked_comp 判定与 comp 核心
    派生,是 schedule_upgrade(升级排程决策)的目标解析链,不是经济事实
    (收入/息/卖退金/刷新价)。不迁:该消费点随 decision 核处死(处死计划
    批 1)一并退役。
    """
    from sr_od.application.currency_war.kernel.cw_intention import (
        IntentionState,
        intention_core,
    )
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        strategy_state_of,
    )
    ist = getattr(strategy_state_of(session), 'v3_intention', None)
    if not isinstance(ist, IntentionState) or ist.phase != 'locked' \
            or not ist.locked_comp:
        return ''
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    comp = get_comp(ist.locked_comp)
    if comp is None:
        return ''
    return intention_core(comp)


def _target_peak_level(bs: GameState, session: StrategySession) -> int:
    """目标核心费用档 → 概率峰值级(解析链:意向锁定核心 → 缺省 3 费;
    核心解析单一源 = _vd_core_of 与其缺省扩展)。"""
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.kernel.cw_plane_table import (
        peak_refresh_level,
    )
    core = _schedule_target_core(session)
    ch = CHARACTERS.get(core) if core else None
    cost = ch.cost if ch is not None and ch.cost else 3
    return peak_refresh_level(cost)


def _schedule_target_core(session: StrategySession) -> str:
    """排程目标核心解析(ev._vd_core_of 锁定核单一源;未锁帧返回 '' →
    调用方缺省 3 费档,供给不断)。

    P86 落码批申报(p86-no-target-period-fund-allocation.md §4.1-1 选项
    「维持缺省 3 费」):原未锁帧⑤兜底 comp 核心锚(FALLBACK_COMP_NAME
    单线硬编码)随四面退役表②面退役——峰值级锚只进概率校准分量,
    方向语义中性,未锁帧峰值档统一回落 3 费缺省。
    ⚠️ 处死计划批 1 的「本消费点随 decision 核处死一并退役」语义由本批
    提前兑现;处死计划文档本体已不在仓(docs/develop/currency_war/archive/
    目录不存在,漂移登记见 P86 正本 §4.1-2),码内注释是原唯一在档裁决
    记录,本注即其承接。"""
    return _vd_core_of(session)


def _target_core_cost(session: StrategySession) -> tuple[str, int]:
    """排程目标核心 → (核心名, 费用档)(与 _target_peak_level 的解析链
    同源拆值,供概率校准分量消费;核心解析单一源=_schedule_target_core)。"""
    core = _schedule_target_core(session)
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    ch = CHARACTERS.get(core) if core else None
    cost = ch.cost if ch is not None and ch.cost else 3
    return core, cost


def _owned_core_copies(bs: GameState, core: str) -> int:
    """目标核心已持有基础副本数 j(3合1 折算:star s → 3^(s-1);
    bench∪deployed 逐件计)。E_find 的 owned 修正输入
    (cw_shop_odds.acquirability_factor 同口径);身份未识别的槽不计
    ——保守方向=低估持有 → E_find 偏大 → 帽偏松(不缩供给侧)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
        deployed_slots_of,
    )
    n = 0
    for bc in (*bench_slots_of(bs), *deployed_slots_of(bs)):
        if bc is not None and bc.char_id == core:
            n += 3 ** ((bc.star or 1) - 1)
    return n


def _omega_collapse_zeroed(bs: GameState, session: StrategySession,
                           registry: DecisionV2Registry,
                           target_cost: int) -> bool:
    """塌缩带判据(概率校准刷新预算的归零腿;ADR-0475)。

    refresh_prob(state.level, target_cost) / refresh_prob(峰值级,
    target_cost) < registry.omega_collapse_ratio → 当前级对该目标费档
    无望,预算归零(合法 0 帧第三类)。
    - **空帧豁免**:非锁定核帧(意向走兜底链)恒 False——兜底 3 费不是
      真目标,对假目标算塌缩比会缩假目标供给、又可能误杀真目标(别的
      费档)搜索量,D1「空帧不缩供给」契约优先;锁定/兜底区分单一址
      = _vd_core_of(锁定核解析,空串=兜底链帧)。
    - **分母非零注记**:峰值级是该费档 refresh_prob 的 argmax
      (cw_plane_table.peak_refresh_level 查表口径),结构性 >0;仍显式
      守卫——分母 ≤0 时判据恒 False(不归零),防消费点换表后静默除零。
    概率源单一址=cw_shop_odds.refresh_prob(与分配器 Π_refresh 估计器
    同源互指,禁第二概率口径)。
    """
    if not _vd_core_of(session):
        return False
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    peak = _target_peak_level(bs, session)
    denom = refresh_prob(peak, target_cost)
    if denom <= 0:
        return False
    return refresh_prob(level_of(bs), target_cost) / denom \
        < registry.omega_collapse_ratio


def _find_budget_cap(bs: GameState, session: StrategySession,
                     registry: DecisionV2Registry, target_cost: int,
                     core: str) -> int:
    """有望帧帽 ⌈−ln(1−q)·E_find⌉(概率校准刷新预算的帽腿;ADR-0475)。

    E_find = expected_refreshes_for_card(level, target_cost,
    target_star=2, owned=j)——首次集齐目标牌所需刷数的有限池精确期望;
    q=registry.refresh_find_quantile 为真分位,−ln(1−q) 是其闭式乘数
    (推导与标定挂账见 registry 字段注释)。E_find=inf(P(0)≈1)时帽不辖
    (交金量式与 6 刷帽裁决);概率源单一址=cw_shop_odds
    (expected_refreshes_for_card 内部消费同表),禁第二概率口径。"""
    import math

    from sr_od.application.currency_war.data.cw_shop_odds import (
        expected_refreshes_for_card,
    )
    j = _owned_core_copies(bs, core)
    e = expected_refreshes_for_card(level_of(bs), target_cost,
                                    target_star=2, owned=j)
    if e == float('inf'):
        return REFRESH_ROLL_CAP
    return math.ceil(-math.log(1.0 - registry.refresh_find_quantile) * e)


def refresh_ev_budget(bs: GameState, session: StrategySession,
                      registry: DecisionV2Registry | None = None) -> int:
    """刷新 EV 授权刷数(确定性预算式;蓝图 §3.4 R4 接缝,ADR-0465;
    概率校准分量=ADR-0475)。

    ``registry``:显式注入优先(P6 契约,同 schedule_upgrade);缺省落
    _registry_of(session) → DEFAULT_REGISTRY。
    预算 = min(6, ⌊(g − R*)/刷价⌋, ⌈−ln(1−q)·E_find⌉)——只花溢余
    (规则倡导审读 §2-R3 预算式:刷新后仍守储备线;6 刷帽单一源
    = REFRESH_ROLL_CAP)∧ 有望帧帽按目标可寻性收紧。概率校准两腿
    (ADR-0475,采纳自其预研提案 B-v2):塌缩带归零(纯金量式与目标可寻性无关的病灶修法;
    归零的账=塌缩带留金弱占优纯烧)+ 有望帧分位帽;**求值次序=先归零
    后帽**(ρ 归零与 min 帽取交即 0,数值良定);概率单一址=cw_shop_odds
    (与分配器 Π_refresh 估计器同源互指,禁第二概率口径)。

    合法 0 帧契约(预算收权迁移前预验尸 D2 契约,判前锁;**辖域=应急带**,
    预算收权攻击审读 F1 收口;第三类=ADR-0475 扩类):
    - ① 应急帧(``is_emergency`` 单一源,hp≤emergency_hp)→ 0:
      应激通道根本不产指令(release 让位结构,合并无从放大);
    - ② g ≤ R* 常态帧(息线以内/储备段持有,0.1/轮 真实收益)→ 0:这个 0
      流过 scoring P2 窗判据(``refresh_budget<=0 → 让位``)与存息
      准入门,「>0 即行动授权」的语义在预算函数口径下成立;
    - ③ 塌缩带归零帧(锁定核解析帧 ∧ ``omega_collapse_ratio`` 判据为真;
      **例外注记:兜底链空帧归零判据恒 False,不属第三类**——D1「空帧
      不缩供给」契约优先)。
    **血预算带(应急线以上,ADR-0448/0451)不在本函数辖域**:预算字段
    依公式照发,停手由 arbiter 拒付层兜底(discipline.
    blood_budget_levelup_blocked 停升级 / blood_budget_refresh_blocked
    搜索型刷新停付)——防线在拒付层不在预算层;原「血预算帧→0」为
    虚标契约,已随预算收权攻击审读 F1 如实收窄(穿透锁=test_cw_w633_migration_b3)。
    定向刷新授权(directed_refresh_budget)是独立车道(arbiter E2,
    1 次/轮),与本预算不相交、不合并;按 ADR-0475 该车道对塌缩判据
    **同判据辖**(含空帧豁免,两车道逐帧一致)——arbiter 接线点挂账:
    decision_v2 当时属在飞分包面禁触,接线留分包收口后补
    (判据单一址=本函数的 ``_omega_collapse_zeroed``,届时零新概率口径)。
    """
    reg = registry or _registry_of(session)
    # (本接缝族 CwSimFrame 签名过渡注已随 W6 波 4 签名切换兑现删除:
    #  is_emergency 直吃容器,桥装箱中间形态消亡。)
    if is_emergency(bs, session, reg):
        return 0
    over = gold_of(bs) - reserve_cap(bs, session)
    if over <= 0:
        return 0
    # 刷价缺省 = 建模基价显式消费(refresh_cost_effective 单一源;
    # 原帧 ``or 2`` falsy 兜底形态的消灭形态,数值恒同)。
    cost = refresh_cost_effective(None, 0, bs=bs)
    core, target_cost = _target_core_cost(session)
    if _omega_collapse_zeroed(bs, session, reg, target_cost):
        return 0
    return min(min(REFRESH_ROLL_CAP, over // cost),
               _find_budget_cap(bs, session, reg, target_cost, core))


def upgrade_plan_fee(bs: GameState) -> int:
    """下一级升级总费 = 到下一级单击数 × 单击价(取价委托 ``xp_click_cost``
    单一源:观察优先/兜底减折扣语义只存在一处,禁第二处独立折扣实现——
    「同一语义两处实现」即互补单侧错漂移温床,正本 = ADR-0632)。"""
    from sr_od.application.currency_war.kernel.cw_plane_table import (
        clicks_to_level,
    )
    return clicks_to_level(level_of(bs)) * xp_click_cost(bs)


def _rounds_to_plane_end(bs: GameState, session: StrategySession) -> int:
    """到本位面末节点(= boss 节点)的剩余轮数(含当前轮;缺读兜底 0
    =不储蓄,保守侧:R* 退化为息线,义务面变宽但方向安全)。
    nodes_of_plane 自带缺表回退(先验 9+一次性告警),此处不再兜层。"""
    from sr_od.application.currency_war.kernel.cw_plane_table import nodes_of_plane
    total = nodes_of_plane(session)
    return max(0, total - round_num_of(bs))


def reserve_cap(bs: GameState, session: StrategySession | None) -> int:
    r"""R\*(t) = interest_floor + Σ 窗口内排程升级费(设计 §1.3)。

    窗口 h = min(3, 到本位面末节点轮数);只储蓄下一级费用——多级
    排程在逐帧重算下自愈(升级完成一轮后 R* 自然滚动到下一级;误差有界核算:
    误估最坏=一个升级费量级 ≤50 金,双向有界)。
    排程判据单一址 = ``schedule_upgrade``(确定性查表核,ADR-0465 预算
    收权;与 arbiter 授权/EV 授权 ② 臂共调同一函数,R4)。

    守息线分量 = ``saturation_line(cap_resolved_of_session(session))``
    (session resolved 链单一源,与排程判据 ② 前置同链;ADR-0598 息帽
    死链修复随批接线:旧 ``registry.interest_cap × 10`` 把策略息帽覆写
    挡在刷新授权车道外——买断制(cap=0)囤金经本车道部分存活,利息
    上调(cap=10)守息线被低估;归一方向 = 息帽三源归一同款)。
    写法保证「守息线 ≤ 封顶线」结构性成立——两者同源(cap_resolved),
    不可能出现守息线高于持有增益归零点(息帽截断点)的态。
    """
    h = min(_RESERVE_WINDOW_ROUNDS,
            _rounds_to_plane_end(bs, session))
    floor = saturation_line(cap_resolved_of_session(session))
    if h <= 0 or not schedule_upgrade(bs, session):
        return floor
    return floor + upgrade_plan_fee(bs)


#: 储备窗口上界(轮;设计 §1.3:h = min(到下一 boss 节点轮数, 3)——
#: 更远的排程升级应即时执行而非长期储蓄,结构界非拍值)。
#: 自 economy_cycle 同迁(reserve_cap 唯一消费,单一源随函数走)。
_RESERVE_WINDOW_ROUNDS: int = 3
