"""货币战争 经济 / 等级 / 节奏骨架模型(纯函数:金 / 经验 / 息 / 刷新成本,EconomyEffect 消费 + 单击经验模型 + 重复性效果折算;node_plan 节点×等级节奏骨架,14 §2 —— 三层共享底层,economy/evaluate/plan 均消费)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_game_state import (
    gold_of,
    level_of,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_ECONOMY,
    EconomyEffect,
    aggregate_economy,
)
from sr_od.application.currency_war.kernel.cw_plane_table import (
    GOLD_CAP_INTEREST,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )
    from sr_od.application.currency_war.kernel.cw_vocab import ShopCard

# ============================================================
# 经济域词汇(金/经验/刷新/卖出回金/血线族,经济骨架同域)。
# ============================================================


# 卖出回金 = 招募费(cost)× 合成倍数,docs/game/currency_war/research/economy.md §3(卖出退金)。1星=cost 🟢 BWIKI+4399+用户权威;
# 2星=cost×3−1、3星=cost×9−1、4星=cost×27−1(合成成本扣1手续费;2星用户印象「少1」,
# 3/4星推测同逻辑 🟡 待 hook 实机核 —— 拖卡到出售区看显示金额)。
_SELL_MULT: dict[int, int] = {1: 1, 2: 3, 3: 9, 4: 27}   # 星级 → cost 倍数(3合1:1星1/2星3/3星9/4星27 张基础副本);sell_refund 对 star≥2 且 cost≥2 再 −1 手续费(cost=1 exempt,见 sell_refund)

# 购买经验机制(用户实测口述 2026-08-15,A5+;telemetry 多局 XP 分母 4/6/20/40 交叉核对一致):
# 「购买经验」每点一次 +XP_PER_BUY 经验、花小额金币(按钮实读 state.level_up_cost);经验攒够当前级
# 门槛自动升级,溢出结转。等级门槛表(升下一级所需总经验):
XP_PER_BUY: int = 4
XP_TO_NEXT_LEVEL: dict[int, int] = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}
XP_CLICK_COST_FALLBACK: int = 4   # 单击经验花金兜底(level_up_cost OCR 缺失时;telemetry lv5 实测 4 金/击)
#: 玩家等级封顶(live 与 sim 同此单一源:10 级后购买经验无效;消费方 =
#: xp_apply_clicks/xp_clicks_to_level/cw_game_state 逻辑态直写满级门
#: ——live 与 sim 同一规则核同消费,不存在第二把尺)。
MAX_PLAYER_LEVEL: int = 10


def xp_apply_clicks(level: int, xp_cur: int, clicks: int,
                    xp_per_buy: int = XP_PER_BUY) -> tuple[int, int]:
    """N 次「购买经验」后的期望 (level, xp_cur)(纯函数;XP 期望态账本的推进算子)。

    语义单一源:每击 +xp_per_buy 经验;攒满当前级门槛即升级、
    溢出结转(消费方 = 升级上报函数 ``report_action_level_up_param``,
    live 与 sim 同一段 op 代码同消费)。
    封顶 MAX_PLAYER_LEVEL(10)级(live 与 sim 同语义:满级后购买经验无效)。

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


def xp_apply_amount(level: int, xp_cur: int, amount: int) -> tuple[int, int]:
    """任意经验量推进 ``(level, xp_cur)``(升级结转与 ``xp_apply_clicks``
    单一源同式:攒满门槛即升级、溢出结转;cap = ``MAX_PLAYER_LEVEL``,
    满级零推进——lv10 分母未定,按 U18 口径不再累计)。

    通用量版理由:节点基础经验含非单击倍数(+2/+12),无法折成
    「购买经验击数」走既有算子。
    消费方清单:节点基础经验入账 ``apply_node_xp``(sim/cw_sim_backend)
    + 白送经验发放原语 ``grant_xp``(kernel/cw_game_state,环境 XP
    窗口通道;两消费方经本单一实现共享升级结转式,禁第二份)。
    """
    if amount <= 0 or level >= MAX_PLAYER_LEVEL:
        return level, xp_cur
    cur = xp_cur + amount
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
    消费端 = CwScreenPrep 直接 CwActionLevelUpParam 动作(腾席链「循环点至 level+1、
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
# 相邻金差对账(只含 CwActionLevelUpParam+Refresh 的最小对账对)全部 = 2,不随金币/
# 次数/等级变;invest_effects.md「刷新 45% 概率免费 → 期望刷价 1.1」隐含基价
# 2(2×0.55=1.1)。右下角「文本-刷新金币数」rect 实际读到的是面板徽标
# (数值 = min(gold//10,5) = 利息公式,非刷价;三流交叉核对定案)——
# 该 OCR 已退出 read_game_state 主链(cw_observation),决策/对账统一消费本常量。
# 消费点语义:容器 ``shop_refresh_cost`` 缺读帧 ``or`` 回退本常量(刷新上报
# 扣费/op 花销账/渲染 helper world_shop_refresh_cost 三读口同式);非缺读帧
# 读容器现值——长线利好改价后为 1(live 改价观察/sim 开店呈现写回,
# fields.md §3.3.4),兜底分支在缺读帧照常触发。
REFRESH_COST_BASE: int = 2


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
      原设计件 IMPL_FIX_LEMMAS/IMPL_DESIGN 已删档 历史)。
    """
    refund = max(cost, 1) * _SELL_MULT.get(star, 1)
    if star >= 2 and cost >= 2:
        refund -= 1   # 合成手续费:仅 star≥2 且 cost≥2(cost=1 exempt,实测 2★1费=3 无费;用户「2费开始减1」)
    return max(refund, 0)


def bench_char_cost(bc, gs: GameState | None = None) -> int:
    """备战角色的招募费(sell_refund / 经济决策用):char_id 已识别 → 查
    CHARACTERS;未知 → 3(中费保守估)。**银狼LV.999 档感知**(口述·权威
    2026-09-21:升费后卖价按新费用档标准公式,无特殊口径):gs 给定时经
    :func:`effective_cost` 取当前档;gs 缺省 = 注册表起始费(保底兼容存量
    调用面——静态画像族与部分估值注记;卖价/退款账实链经 gs 形参传入)。

    入参 = 容器单位(行域/bench unit 槽的 ``Unit``,duck 读 char_id;
    benchchar-retirement P4 容器形)。
    公共名(跨模块私有符号收敛:跨模块消费统一走本名;
    下划线旧名保留为别名,存量消费点不破)。"""
    c = CHARACTERS.get(bc.char_id) if getattr(bc, 'char_id', '') else None
    if c is None or not c.cost:
        return 3
    if bc.char_id == _LV999_ID and gs is not None:
        return effective_cost(gs, bc.char_id)
    return c.cost


_LV999_ID: str = '银狼LV.999'   # 规范名(单一源 = cw_chars 注册名;现役唯一档分支成员)


def effective_cost(gs: GameState, char_id: str) -> int:
    """角色**当前费用档**唯一读口(观察除数/账实结算/随机授予采样空间)。

    - 银狼LV.999 → 容器档 ``gs.lv999_cost_tier.value``(纯逻辑态,写端 =
      pick_planner 升费分支 / deploy_move 上阵变费分支);未观察(None = 未触发
      任何变换)归约 3(开局档语义默认);
    - 其余角色 → 注册表 ``CHARACTERS[char_id].cost``(静态);**未注册名 → 0**
      (无费用语义,禁用于金额计算——与 :func:`bench_char_cost` 未知 → 3
      「退款保守估」分野,两口径不互借);
    - **语义双轨边界**:本口 = 当前费用档;静态画像族(低费集合/费用分布/
      telemetry 特征)语义 = 起始费,直读注册表,永不经本口(变费中间态
      对静态画像的双口径影响归该族消费点逐处申报);
    - **档分支扩展位**:现役仅银狼LV.999;第二变费成员(飞光·映月:特殊
      1 费景元随镜流星级 3/5 费,策略赋予型)接入时在本口扩展成员档表,
      禁另起平行访问器。
    """
    if char_id == _LV999_ID:
        tier = getattr(gs.lv999_cost_tier, 'value', None)
        return tier if tier in (3, 4, 5) else 3
    c = CHARACTERS.get(char_id)
    return c.cost if c and c.cost else 0


STREAK_GOLD_TABLE: tuple[int, ...] = (1, 1, 2, 2, 2, 3, 4)
"""连胜金实测真值表(索引=连胜数,越界取末值;49/49 样本,economy.md §10.1)。

弹窗底部固定规则表,与对局状态无关:0-1→1 / 2-4→2 / 5→3 / 6+→4(末位即 6+ 档)。"""


def streak_gold(streak: int) -> int:
    """连胜奖励金(真值源=奖励弹窗 VLM 判读;表化)。

    查 STREAK_GOLD_TABLE,越界(连胜 6+)取表尾。
    单一源:sim 收入模型(cw_sim)与决策 EV(decision_v2 经 sim/plan 共用)
    都 import 此函数,防双表漂移。"""
    idx = max(0, min(streak, len(STREAK_GOLD_TABLE) - 1))
    return STREAK_GOLD_TABLE[idx]


# ===== 息账/收入日程(自 strategies statefn/interest+income 下沉单一源,
# ===== kernel 判据消费 loss_exact/net_income,下沉保持「kernel 禁 import
# ===== strategies」桶依赖矩阵;statefn 两模块改 import 重定向,消费方
# ===== 调用零改)=====

#: 默认利息帽档数 = 息封顶金位/10(cw_plane_table.GOLD_CAP_INTEREST=50 的
#: 结构派生,【注】机制真值;禁在本模块另写裸 5)
DEFAULT_INTEREST_CAP: int = GOLD_CAP_INTEREST // 10

#: cap 视界上确界(注册表 interest_cap 值域上界 10;消费位按 canonical
#: 枚举表纪律——原 design_economy §E4.2 已删档 历史——
#: 一律消费 cap_sup 而非决策帧现值 cap_resolved(R63-1)。
INTEREST_CAP_SUP: int = 10


def interest(gold: int, cap: int = DEFAULT_INTEREST_CAP) -> int:
    """利息 = min(g//10, cap);g<0 按 0 计(防负金越界,p47 A1 同源)。"""
    return min(max(gold, 0) // 10, cap)


def interest_cap_resolved(interest_cap_override: int | None = None) -> int:
    """resolved 利息帽(「无覆写回默认」的单点归一)。

    override=None(默认局/未持利息帽卡)→ DEFAULT_INTEREST_CAP;注册表
    覆写值(开源节流 9/利息上调 10/买断制 0)由调用方经聚合链传入——
    本函数只做归一,禁在判据侧内联 cap 字面量(E4.0 第 1 条)。
    **0 是有效覆写**(买断制 = 息通道改写,已登记同判 kernel/cw_investments
    is_economy_engine):判别只认 None,禁真值折叠——``override or 缺省``
    形态会让买断制静默回 5(最高危陷阱锁)。
    """
    if interest_cap_override is None:
        return DEFAULT_INTEREST_CAP
    return max(0, int(interest_cap_override))


def cap_resolved_of_session(session: StrategySession | None) -> int:
    """cap_resolved 现读(session resolved 链;利息帽三源归一)。

    覆写单一源 = ``aggregate_economy(session.active_strategies).
    interest_cap_override``(注册表派生、零新参数;利息帽死链
    修复):已持投资策略聚合取 cap 覆写(并持取宽),未持
    利息帽卡 → None → 回 DEFAULT_INTEREST_CAP;None/0 判别语义由
    :func:`interest_cap_resolved` 单点承载。两个写点 = 实机选卡 handler
    (cw_screen_invest_strategy,确认成功后 append)——本函数只读 session 级字段,
    禁读 state 镜像(非公共权威)。

    消费位 = 商店线 R1/R2 的 g* 装配(mandate._cap_of 重定向至此)、
    升级资金线门下界(saturation_line)、富余段/动作发出帧富余段、
    registry 预算面保利利息线分量(reserve_cap 保利息线/换线可负担窗)——
    共用本式,禁再内联 ``interest_cap×10`` 或 loss_exact 裸缺省 cap
    (利息律投资 cap=10 局,裸缺省 5 会低估 C_int)。

    边界:本链不读 registry.interest_cap(A/B 旋钮覆盖观察/检查器镜像
    面,不覆盖本链);回落问题的实际形态 = 「从未持有」——投资策略
    无卖出/移除建模(handler 只 append),与 S2 口径共享
    同一 append-only 假设,非本函数独立边界。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import game_state_of
    # 终态契约 §B:active_strategies 单一源 = gs(write_logic 选择写点)。
    strategies = (game_state_of(session).active_strategies.value
                  or []) if session is not None else []
    override = (aggregate_economy(list(strategies)).interest_cap_override
                if strategies else None)
    return interest_cap_resolved(override)


def saturation_line(cap_resolved: int) -> int:
    """利息律饱和线 g* = 10×cap_resolved(保利息门/arm2 金下限同源派生)。"""
    return 10 * cap_resolved


def next_interest_line(gold: int, cap_resolved: int) -> int | None:
    """下一利息档线(凑息卖出止盈目标的单一源)。

    跨到下一利息档所需的金位线 = ``(min(g//10, cap-1)+1)×10``。凑息
    卖出只有跨档才有收益(interest = min(g//10, cap),档内卖出金额
    变动不涨息),缺口 = 本线 − 当前金;返回 None = 无档可跨,凑息
    零收益,消费位必须零发出:

    - 已达满档(gold ≥ cap×10,含饱和线之上)——利息已封顶;
    - 买断制(cap_resolved ≤ 0)——利息通道整体关闭。
    """
    gold_n = int(gold or 0)
    if cap_resolved <= 0 or gold_n >= 10 * cap_resolved:
        return None
    return (min(gold_n // 10, cap_resolved - 1) + 1) * 10


def in_must_spend_zone(gold: int, session: StrategySession | None) -> bool:
    """富余段判定(20 号稿 §2.1):g > G_must = 10 × cap_resolved。

    单一源派生 = saturation_line(cap_resolved_of_session(session)),与
    利息线 g*/arm2 保利息门同链,零新自由参数;买断制语境(cap_resolved = 0)
    不适用恒 False(§2.1,该语境金出口归一般判据)。适用范围 = 有动作决策点帧
    (shop/备战决策入口调用点;§3.4)。

    消费点(接线位):shop.py 出口③ L2 第二触发源(∨ 合并)/L3 富余段
    升级/R1 域内残形切分线/EV 域内降排序——四点共用本判定,禁再内联
    ``gold > 10 * cap`` 字面量式。
    """
    cap = cap_resolved_of_session(session)
    if cap <= 0:
        return False   # 买断制不适用(§2.1)
    return gold > saturation_line(cap)


def in_launch_spend_zone(gold: int, session: StrategySession | None) -> bool:
    """动作发出帧溢出段判定(金出口族出口 B 触发面;金出口族 DESIGN v1.1 §3.2,

    = ``gold > saturation_line(cap_resolved_of_session(session))``——与
    :func:`in_must_spend_zone` 共享 g* 单一源(saturation_line 同链,
    禁内联第二份);买断制语境(cap_resolved = 0)不适用恒 False(与富余段
    §2.1 同口径)。

    **与富余段同 g* 不同域,禁并键**(DESIGN v1.1 §5;launch_gold_tradeoff
    §3 边界①同判):富余段覆盖「有动作决策点的 shop/备战帧」,本谓词覆盖
    「动作发出帧溢出段」(出战就绪帧发出前的受限访问入段判定;两域互斥 =
    调用点约定非结构保证,M-1 降级口径,新增消费点须回 DESIGN §5 对账
    表)。消费点:mandate_v1 前置动作发出点帧级金判定
    (strategies/impl/mandate_v1/bridge._launch_front_check),直调本函数,
    禁内联 ``gold > g*`` 字面量式。
    """
    cap = cap_resolved_of_session(session)
    if cap <= 0:
        return False   # 买断制不适用(§2.1 同口径)
    return gold > saturation_line(cap)


def loss_exact(gold: int, spend: int, rounds: int, net_income: int,
               cap: int = DEFAULT_INTEREST_CAP) -> int:
    """金位 gold 花 spend 金后未来 rounds 轮的精确期望息损(P47 命题 2)。

    双轨迹对照:基线 B(不花,守饱和线,富余即花)vs A(花后守线);每轮息损
    = interest(B) − interest(A),两轨迹同收入演化。截断视界 R=rounds 由
    调用方按场字段求和现算(视界量不入框架,裁决点 9;禁写死,§6.1)。
    溢金域先实金扣
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

    = ``reward_base_gold(1, round_num)`` 薄委托(处置(①):
    base 曲线实现单一源归 :func:`reward_base_gold`,本函数只剩「P1 键
    当全平面规划曲线」这一申报语义)。**规划近似申报**:决策数学没有
    plane 入参,取 P1 键当通用规划曲线——对 P2/P3 的 r1/r2 轮与真值
    有差(P2r1 真值 5,本投影返 3),差异归属=决策近似口径 vs 记账
    口径,申报面见统一观察架构 §7.1;等价性测试=
    sr-od-test test_cw_income_single_source(net_income 值域逐位不变)。
    """
    return reward_base_gold(1, round_num)


def net_income(round_num: int, streak_pre: int,
               lost_node_type: str | None = None) -> int:
    """逐节点净收入 Ī(NMF §2「Ī」行;R09 收入三表现算,非 i_bar 常量)。

    **处置申报(统一观察架构方案审 F4-①,裁决=委托改造
    +规划近似显式化)**:base/streak 分量已改为委托 T1a 单一源函数族
    (:func:`reward_base_gold` 的 P1 规划投影 + :func:`streak_gold`),
    消费点数值逐位不变(等价性测试已登记)。

    - ``round_num``:日程轮号(1 基;开局两轮基础金折半段);
    - ``streak_pre``:**决策前相**连胜数(进轮连胜,奖励轮照发不动计数,
      kernel 记账口径);
    - ``lost_node_type``:上一轮若为败掉的战斗类节点,其败轮底金在本轮
      轮首补发(battle/encounter/boss → LOSS_GOLD_BY_NODE);非败轮接续
      传 None。**规划近似申报(两处)**:①本参数签名无 plane/round,败补
      只能取类型表底金做规划下界,与记账口径(:func:`loss_compensation_base`
      平面感知键)的差异归属=决策近似,挂玩家确认;
      ②现役 5 个决策消费点(mandate_v1 shop.py ×4 / 本模块
      loss_exact 前置)全部传 ``streak_pre=0, lost_node_type=None``——
      败补参数支当前零消费,近似不落值。
    """
    inc = reward_base_gold(1, round_num) + streak_gold(streak_pre)
    if lost_node_type is not None:
        inc += LOSS_GOLD_BY_NODE.get(lost_node_type, 0)
    return inc


# ===== T1a 轮首收入三支·kernel 单一源函数族(统一观察架构 §7-T1/T2 搬迁任务的 =====
# ===== kernel 半部;正本语义=GameState 设计 §4.2 轮首收入行。实机写端与 =====
# ===== sim 后端包装(cw_sim_backend.apply_round_start_income)均调本函数族)=====


def reward_base_gold(plane: int, round_num: int) -> int:
    """基础奖励金·平面感知键(奖励轮/常规轮共用的 base 分量单一源)。

    键(正本=GameState 设计 §4.2 奖励轮行;真值=economy.md §10.1):
    P1 r1=3 / P1 r2=4(:data:`REWARD_BASE_GOLD_BY_ROUND`,弹窗 VLM 直读
    85/85 零散布);P2r1=5(结构化直读两批独立一致);P3r1 按 5 近似
    (无直读样本,维持待办);其余轮恒 5。

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

    〔口径冲突待办·判别已执行〕:旧口径 = LOSS_GOLD_BY_NODE 类型表
    {battle:2, encounter:4, boss:4}(108 局差分)。仲裁实验
    (分桶重放,tools/cw/loss_comp_bucket_replay.py,146 局语料,
    )**数据不足以定案**:判别判据所需的 P1r1/r2 败局阶梯
    样本在语料中不存在(低轮位 bot 恒胜),boss 桶 n=1;且标准节点序把
    「被败节点类型」与「下一节点类型」结构性绑定(battle→encounter→
    reward),差分窗内的类型差分与到账项差分不可分。记录模型**维持
    玩家裁定口径**,待玩家确认)。
    """
    return reward_base_gold(plane, round_num)


@dataclass(frozen=True)
class LostNodeRef:
    """被败战斗节点的引用(败补分支的取键输入)。

    ``node_type`` = 节点类型 token(battle/encounter/boss,与
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
    取 0)、combat=常规战斗胜轮(连胜照发×倍率)。分支派发序
    (supply→reward→败补→常规,GameState 设计 §4.2 行选择
    优先级;奖励/补给轮不发 LOSS_GOLD)。
    """

    branch: str
    base: int            # 基础奖励分量(败补分支=补发基项)
    interest: int        # 利息分量(含息 flat 修饰)
    streak: int          # 连胜分量(已乘 win_reward_mult;supply/loss_comp 恒 0)
    total: int           # 三分量之和

    def as_dict(self) -> dict[str, int | str]:
        """账本行形态(sim 后端收入分支 dict 行与实机遥测行共用的投影)。"""
        return {'branch': self.branch, 'base': self.base,
                'interest': self.interest, 'streak': self.streak,
                'total': self.total}


def _streak_component(streak: int, win_reward_mult: float) -> int:
    """连胜分量 = streak_gold(进轮连胜) × win_reward_mult(四舍五入取整)。

    倍率单一源 = 注册表 STRATEGY_ECONOMY.win_reward_mult(聚合取最大
    不叠乘,cw_investments.aggregate_economy);已登记唯一非 1 值=伟大征服
    3.0。**含奖励轮**(GameState 设计 §4.1:win_reward_mult 施于连胜
    分量含奖励轮,消持卡局奖励轮系统性少计;sim 侧消费 =
    cw_sim_backend.apply_round_start_income 包装,生产双端同源)。
    """
    return int(round(streak_gold(streak) * win_reward_mult))


def round_start_income(
        plane: int, round_num: int, node_type: str, gold: int, streak: int,
        *, lost_node: LostNodeRef | None = None,
        win_reward_mult: float = 1.0,
        interest_flat: int = 0,
        interest_cap: int | None = None,
        lost_round: bool = False) -> RoundStartIncome:
    """轮首收入三支单一源(统一观察架构 §7-T1:同输入必同输出,禁第二份)。

    - 分支派发(supply→reward→败补→常规):
      supply → base+息,连胜不动(补给轮连胜不动);
      reward → base+连胜×倍率+息(连胜照发含 counter0=1);当前为战斗
      类节点且 ``lost_node`` 在场 → 败补(base=补发基项+息,连胜取 0,
      win_reward_mult 不生效);其余 → 常规战斗胜轮(base+连胜×倍率+息)。
    - ``lost_node``:调用方契约=上一战斗类节点败且败态未被消费时传入
      (败态跨奖励/补给轮的归宿——吞掉还是递延——是调用方策略,本函数
      不裁决,待实机实证挂观测期核对项,GameState 设计 §4.2)。
    - ``lost_round``:统一公式败局形(每节点 = 基础+息+连胜成分,战败无
      连胜成分,economy.md 收入口径)——reward 轮消费(扑满败局;胜局
      按进轮连胜照发不变)。战斗轮败局仍走败补支,不在本参数域。
    - ``interest_flat``:息 flat 修饰(狸财经狸每节点固定息,与利息帽无关;
      聚合单一源=EconomyEffect.interest_flat_per_node)。
    - ``interest_cap``:resolved 利息帽(None→DEFAULT_INTEREST_CAP;归一口
      =:func:`interest_cap_resolved`,禁调用方内联 cap 字面量)。
    - 值域注:奖励/常规轮的 base 经 :func:`reward_base_gold` 平面感知
      取键(P2r1/P3r1 单键误返 3 hazard 在此消灭);r8 位面大奖励
      (待办,sim 少发 ~9)与事件金不在本函数适用范围(触发面不同,
      调用方单列)。**适用范围排除**:gold_per_node/
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
        streak_amt = (0 if lost_round
                      else _streak_component(streak, win_reward_mult))
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
#: 锁零触碰);败轮弹窗预期 1 与实发不符,走本表分支。
LOSS_GOLD_BY_NODE: dict[str, int] = {'battle': 2, 'encounter': 4, 'boss': 4}

#: 奖励节点基础收入查表(P1 实测:1-1=3 / 1-2=4,弹窗 VLM 判读 85/85 零散布;
#: 其余轮与全部非奖励节点仍 BASE_INCOME 统一近似)。**与奖励轮 streak 分量成对**:
#: BASE_INCOME=5 恰好盖住奖励轮照发的连胜金 table[0]=1——单独改 streak 不改本表
#: 会让奖励轮多发 1(成对约束)。
REWARD_BASE_GOLD_BY_ROUND: dict[int, int] = {1: 3, 2: 4}

#: P1 之外各轮的基础奖励统一近似值(与 :data:`BASE_INCOME` 同源同值,禁在本
#: 模块另写裸 5;P2r1=5 是 economy.md §10.1 结构化直读两批独立的定案值,
#: P3r1=5 是无直读样本下的近似、待办维持——见 :func:`reward_base_gold`)。
_REWARD_BASE_DEFAULT: int = BASE_INCOME

# streak 带符号(连胜 + / 连败 −);真值归宿 = gs.streak 结算覆盖写端
# (kernel/cw_game_state.py::apply_settlement_cover 的 streak_after,
# 写点 = battle_wait 结算观测),经济/观察消费读容器。
# 无「连胜 ≥2 跌破利息档」阈值常量(未核经验值,与已证跌破利息档-保利息判据
# 冲突;连胜经济语义由利息线判据默认承载,激活分支 Δp 通道
# 封锁——登记 = math_proofs P43)。

# —— 购买经验决策 helper(机制常量 XP_TO_NEXT_LEVEL/XP_PER_BUY 在 cw_economy 单一源)——
# ⚠️ 本接缝族签名已切 GameState。字段读统一经容器读口单一源
# (kernel/cw_game_state 决策面公共读口),禁各消费点自写兜底。

def _strategy_economy(gs: GameState) -> EconomyEffect:
    """当前持有投资策略的聚合经济效果(active_strategies → 数值效果,策略层算账)。"""
    return aggregate_economy(list(gs.active_strategies.value or []))



def refresh_cost_effective(refresh_count: int = 0,
                           registry: DecisionV2Registry | None = None,
                           gs: GameState | None = None) -> int:
    """刷新 EV 判据用的参数化刷价(基价直通)。

    (旧长线利好折价分支已停用,现行行为 = 恒基价;``refresh_count``/``registry``
    参数保留占位,消费点 = cw_line_switch/economy_cycle/ev/scoring 族
    (原 posture_release 消费位已随死代码清偿移除)。机制真值
    (长线利好 30 刷后 1 金)仍在 cw_invest_data。)

    ``gs`` 给定时刷价 = GameState.shop_refresh_cost 现场识别值(观察通
    道,免费帧不写保证该域不出 0);None = 未读到 → **建模基价
    SHOP_REFRESH_COST 显式消费缺省**——数值恒同,语义从「静默兜底」
    升为「声明式建模缺省」。
    """
    if gs is not None:
        _v = gs.shop_refresh_cost.value
        return int(_v) if _v is not None else SHOP_REFRESH_COST
    return SHOP_REFRESH_COST


def world_shop_refresh_cost(gs: GameState) -> int:
    """当前环境改价规则下商店刷新的世界刷价(改价分支渲染单一源)。

    环境在 ENV_ECONOMY 在册且注册了改价字段 ``refresh_cost_after``
    (语义 = (刷新阈值, 新成本),如长线利好 (30, 1))且付费刷新累计
    ``gs.effects.refresh_paid`` 已达阈值 → 返回新成本;否则返回基价
    ``REFRESH_COST_BASE``(环境不在册/改价字段 None 同基价)。付费域
    计数与 ENV_REFRESH_GRANTS 登记计数同口同语义;阈值与新成本全出
    注册表、基价出常量,本函数零新增数值。

    消费端 = sim 开店呈现(cw_sim_backend._open_shop 把本渲染值经观察
    通道写 ``gs.shop_refresh_cost``,对偶实机「每次进店读屏重读刷价」
    ——live 无识别缺口走 OCR,sim 无识别面走本渲染)。与决策面读价
    :func:`refresh_cost_effective` 同模块并排,两个刷价读口不漂移。
    """
    env = gs.active_env.value
    econ = ENV_ECONOMY.get(env) if env else None
    cost_after = econ.refresh_cost_after if econ is not None else None
    if cost_after is not None and gs.effects.refresh_paid >= cost_after[0]:
        return int(cost_after[1])
    return REFRESH_COST_BASE



def xp_click_cost(gs: GameState) -> int:
    """一次「购买经验」单击花金(观察优先兜底逻辑,strategy-env-impacts §2
    通用模式 1;折扣语义修复正本=行内申报)。

    两支语义(来源凭 ``gs.level_up_cost`` 是否有值判别):
    - **显示价支**(OCR 实读):传入值为最近备战帧观察价,游戏侧已算好
      全部折扣(商业间谍/成长的快乐等)→ **原样直通不再减**,下限 0;
      0 与缺省同义走兜底支(falsy 契约,与全部既有调用面一致)。
      「最近观察值」= 写端仅在备战观察权重开启帧更新(cw_observation
      read_level_up_cost),非本帧保证;取数后才拿卡/跨等级门档位的过期
      窗口方向可自愈、有界(下一备战帧同屏重读)。
    - **兜底支**(观察缺省):函数内减折扣 = 基准 XP_CLICK_COST_FALLBACK
      (恒 4=用户口径,非按等级)−[xp_buy_cost_discount + 等级门折扣
      (成长的快乐:xp_click_discount_from_level,``level_of(gs) ≥
      xp_click_discount_from_level_at`` 时生效;哨兵 0=未持有)],
      max(0) 钳。

    出域声明:奋斗协议(xp_buy_hp_cost)血本位下购经验币种切换为血,
    本金费函数不适用(经验批支付门独立车道 xp_batch_payment_gate
    承接);按钮显示非金数值时显示价支读数同样出域,不在本函数补模。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        level_of,
    )
    lvl_cost = gs.level_up_cost.value
    if lvl_cost:
        return max(0, int(lvl_cost))
    _level = level_of(gs)
    eff = _strategy_economy(gs)
    discount = eff.xp_buy_cost_discount
    if (eff.xp_click_discount_from_level_at
            and _level >= eff.xp_click_discount_from_level_at):
        discount += eff.xp_click_discount_from_level
    return max(0, XP_CLICK_COST_FALLBACK - discount)



def clicks_to_next_level(gs: GameState) -> int:
    """从当前 XP 到升 1 级还需的单击次数(xp 未知按 0 进度向上取整;满级返 0)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        level_of,
    )
    _level = level_of(gs)
    if _level >= MAX_PLAYER_LEVEL:
        return 0
    xp_v = gs.xp.value
    if xp_v:
        cur, need = int(xp_v[0]), int(xp_v[1])
    else:
        cur, need = 0, XP_TO_NEXT_LEVEL.get(_level, 4)
    return max(0, -(-(need - cur) // XP_PER_BUY))


# ===== 经验批支付门(币种通式;R-1 裁决:血本位局「血余额够不够买
# ===== 下一级」与金本位局「金不够买不起」同构,是支付能力检查非 hp
# ===== 判据——判据与模式解析单一源在 kernel,prep 批入口与 cw4 消费位同源)=====

def blood_xp_full_clicks(level: int) -> int:
    """下一级**全量击数** = ⌈XP_TO_NEXT_LEVEL[level]/XP_PER_BUY⌉([40]② 裁定字面
    「下一级血成本(⌈need/4⌉×6)」的击数项;N1 拍板全量口径)。

    - 全量口径先例 = 原平面表 ``clicks_to_level``(同式,xp 结转忽略;载体已随
      死代码清偿移除);本函数与剩余口径的差异 = 权威表逐字(无 1/2 级先验补全)。
    - 与 ``clicks_to_next_level``(剩余口径 ⌈(need−cur)/4⌉)**语义不同,闸不消费
      该函数**:cur>0 是常态(买牌 XP 直抬进度 + 购经验溢出结转,
      ``xp_apply_clicks``),剩余口径系统性压低门槛、方向恒向放行,与 [40]②
      「否则停」的保护目的反向。
    - 满级分支(R1):level≥MAX_PLAYER_LEVEL → 0 击(购买经验无效,与
      ``xp_apply_clicks``/``clicks_to_next_level`` 的满级返 0 同语义)
      ——分支必须在公式本体,否则字面公式对满级产出 ⌈兜底4/4⌉=1 击的
      6 血门槛,与「恒放行」申报分叉。
    - 1/2 级(权威表未收录,游戏内近乎白送)按兜底 need=4 → 1 击,与
      clicks_to_next_level 既有兜底同语义。
    """
    if level >= MAX_PLAYER_LEVEL:
        return 0
    return -(-XP_TO_NEXT_LEVEL.get(level, 4) // XP_PER_BUY)


def xp_batch_payment_gate(balance: int | None, balance_readable: bool,
                          level: int, cost: int) -> bool:
    """经验批支付门·币种通式(纯函数;R-1 裁决归类)。

    判据:支付币余额 ≥ 整批成本(⌈need/4⌉×每击支付币价)才买经验,
    ``balance ≥ blood_xp_full_clicks(level) × cost``;返回 True=放行。

    - 币种通式语义(R-1):血本位局里血就是购经验的币种,「余额够不够
      买下一级」与金本位局「金不够买不起」同构——支付能力检查,账户
      读数非质量信号;金本位局的同构检查 = 金余额够不够,由升级发射门
      序的资金线门(criteria/levelup 门⑥)承担,本门不辖金本位局
      (消费适配层 mode=None 直通)。依据 = 11_shop_decisions.md:58
      ([40]② 支付能力检查定性)。
    - 支付币不可信帧 fail-closed 返 False(读数损坏防护,非 hp 判据
      ——误放=买不起的购买、误拦=少买一批,取拒侧)。
      ``balance_readable`` = 该帧支付币读数可信位(调用方经
      ``cw_discipline_rules.hp_decision_trusted`` 解析后传入)。
    - 本函数**禁读** hp_pay 遥测(隔离申报):支付币输入 = 最近可信备战
      帧值。

    「买一半」缺陷的 as-built 消歧(11 号篇 §2 支出形态):
    部分购买的真实机理 = **逐帧单击发出形态 × 本门静态全量阈值逐帧
    重闸**——支付币余额跌回阈值之下即停止发出、留下部分级;本门
    本体(全量击数口径)从来不是截断源。修法 = 发出粒度整批化
    (升级预授权 + 实付上界 = 授权支付成本,执行帧不再逐帧重闸——
    余额为静态阈值,授权帧一次检查即无逐帧重闸复发面),门本体
    语义不变。
    """
    if not balance_readable:
        return False
    if balance is None:
        # 无真值帧 fail-closed(消费点对 None 一律保守):误放与
        # 误拦代价非对称,取拒侧。
        return False
    return balance >= blood_xp_full_clicks(level) * cost


def xp_batch_payment_gate_for(gs: GameState | None,
                              session: StrategySession) -> bool:
    """经验批支付门消费面适配(mode 解析 + 容器帧输入接线;prep 批入口
    与 cw4 消费位共用)。

    - 金本位(session 无 active 血本位卡,``cw_investments.blood_xp_mode``
      → None)→ True 直通:金模式升级零改动(金侧「买不买得起」由升级
      发射门序资金线门承担,本门不辖)。
    - gs 缺席 → False fail-closed(与门本体 None 支同论证)。
    - 支付币读数 = 政策层读口 ``decision_hp`` 门后值 +
      ``hp_decision_trusted`` 可信位(容器单一读口,消费同门):
      店开态读数结构性不可见时容器沿用最近备战帧可信值(同帧正常
      工作,复盘 15 帧实证);level 取容器读口。
    """
    from sr_od.application.currency_war.kernel.cw_investments import (
        blood_xp_mode,
    )
    mode = blood_xp_mode(session)
    if mode is None:
        return True
    if gs is None:
        return False
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        hp_decision_trusted,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import level_of
    from sr_od.application.currency_war.kernel.cw_hp_policy import decision_hp
    return xp_batch_payment_gate(decision_hp(gs, session),
                                 hp_decision_trusted(gs),
                                 level_of(gs), mode[1])



#: 刷新基价【注】= 赋值别名,非第二源:正本 = ``cw_state.REFRESH_COST_BASE``
#: (游戏定义真值:实付恒 2 金,不随金位/次数/等级变,三流对账
#: 定案,出处注在彼处)。本名保留 = 存量消费面(proof/budget/本模块)零迁移;
#: 改值只改 cw_state 正本,禁在此另写数值。
SHOP_REFRESH_COST: int = REFRESH_COST_BASE


# (通用升级曲线 _DEFAULT_LEVEL_GOAL 已停用 2026-09-04,「未证即停用」裁定:
# 旧值 = auto-chess meta 社区先验(前期 roll 找低费核心→中期 5-7 level_up→
# lv8 roll 找 5 费→lv9 stable),无游戏定义或证明出处。保守缺省:阵容未填
# level_plan 时不退回通用曲线(该回退路径载体已删),升级压力仅由
# 节点地板(get_node_goal,预算收权核)+ 淘金客姿态等已证判据覆盖。)


def _expected_level(round_num: int, plane: int) -> int:
    """阶段期望等级(里程碑刻度,663 帖攻略精读实证)。

    【拟】社区先验待证待办:本曲线处置 = 立证明骨架
    (docs/develop/sr_od/application/currency_war/proofs/p58-expected-level-schedule.md 草案,
    由游戏定义量——XP 费用表/收入日程/出战位解锁/商店刷率峰值级——
    派生等级日程),证明完成前数值维持现状;届时按证明输出重derive 或停用。

    P1:1-3 上5 / 1-7 遭遇前6 / boss 前 6-7(7 是 3费C 阵容的 level_plan 域,通用曲线取 6)。
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
@dataclass

class NodeGoal:
    """某节点(位面-轮)的节奏目标(阵容无关骨架;阵容只换 level_plan/core_chars 参数;14 §2.0)。"""
    target_level: int           # 该节点目标等级(地板);plan level gate 显式 gate
    spend_mode: str             # saving/interest/level/hold/spend/allin/adaptive(§2.2 经济档位)
                                # 'release' 档现役无生产位(原帧级态生产口
                                # decision_v2.posture_release 已随死代码清偿
                                # 移除;义务语义现役 = economy_cycle 义务核算
                                # + ``disclose_budget`` 披露面);
                                # 本函数只产 level/adaptive/interest
    action_focus: str = ""      # 描述辅(d_search/chase_star/rush_level;指导动作偏好,不直接驱评分)
    #: DP 授权的可刷次数上界(三方预算合并:随 NodeGoal 下传,消费侧与
    #: plan 层 _refresh_cap 合并——release 是义务(下界),DP/plan 是许可
    #: (上界),义务激活时义务优先,未激活时许可取交;原 posture_release
    #: 注释载体已随死代码清偿移除)。None=无 DP 信息(先验 fallback;不参与
    #: 合并,许可侧原值)。
    refresh_budget: int | None = None


# ⚖️(2026-08-18 用户定夺):旧 _DEFAULT_NODE_PLAN 区间表**已删**。
# 历史:V4.4 先验表 → 用 11 局 bot live「校准」(P1末7/P2早8)→ 0126 被三重降级
# (0127 H4 疑幽灵锚点/0129 等级观测污染/2026-08-18 单局相关≠基准)。DP 影子接缝
# 切流后 live 全部走 DP,该表只剩异常回退一条活路;失败面穷举(删除前评审)仅剩
# MemoryError + 开发期注册表手误(运行时游戏数据不进台账链;未注册策略名静默跳过)→
# **保留脏表回退比停机更危险**(静默掉回 0126 节奏 = 看着在跑实际在错)。删除;
# DP 失败/越界 → _expected_level 平滑先验 + adaptive(V4.4 干净先验,非 0126 数值)。
# 等级基准权威 = 用户口述定夺(docs/game/currency_war/research/economy.md §7 阶段经济共识;
# 息引擎优先与中途过渡 lv5-6 条)+ XP 反推真值。


def get_node_goal(plane: int, round_num: int, *,
                  gold: int | None = None, level: int | None = None,
                  committed: bool = True,
                  strategies: list[str] | None = None) -> NodeGoal:
    """查 (plane, round) → NodeGoal(确定性预算核单一供给)。

    姿态从预算收权核涌现(原 DP 解供给已停用,BLUEPRINT §3
    裁决;git 历史为 prior art):刷新预算 > 0 → adaptive/d_search;
    否则 → interest/hold。供给在任意帧恒有定义(预算收权迁移前预验尸
    D0 契约:None 级联面消灭),仅传参不全(迁移漏点)时退
    ``_expected_level`` 平滑先验 + adaptive(记 [cw-seam] debug 证据)。
    升级不占姿态位:升级触发归策略层单判据三分派,升级攒批资金保护 =
    升级资格门⑥资金线门(现金口径花后守 saturation_line,凑金域由
    备战侧凑金收敛)+ 刷新判据「升级优先」支资金序,不经 node_goal
    预算。

    三档 spend_mode 与决策核同源:adaptive/interest 的判据单一址 =
    本模块接缝 refresh_ev_budget(期 0b 自 decision_v2.economy_cycle
    下沉,R4)——本函数是其标量投影;'release' 档不经本函数(帧级态,
    'release' 档现役无生产位(原帧级态生产口 decision_v2.posture_release
    已随死代码清偿移除,义务语义现役 = economy_cycle 义务核算 + 披露面)。
    """
    _partial = (gold, level)
    if any(v is not None for v in _partial) and None in _partial:
        log.debug('[cw-seam] get_node_goal 部分传参(%s)→ 走先验 fallback;迁移漏点排查',
                  ('g' if gold is not None else '-') + ('l' if level is not None else '-'))
    if None not in (gold, level):
        # 标量投影容器:直接按入参构造最小决策容器(供给核只读经济/板面
        # 字段;无 session、无现成容器)。字段契约单一源 =
        # kernel cw_game_state.scalar_projection_state。
        # session=None:nodes_of_plane 走缺表回退(节点序列默认表 P1 长,
        # 一次性告警即记档)
        # → h=9−r 常 >0,R* 窗口分量在投影容器**照常储蓄**(预算收权攻击
        # 审读 F6b 纠偏:原注释「投影帧不储蓄」与实现不符;方向保守无害)。
        # ⚠️ 结构性边界(申报,不扩修):下行接缝核以
        # session=None 调用 → 利息帽 resolved 链恒 DEFAULT(base cap),
        # 持利息帽卡局的本投影判据按 base 口径——接缝无 session 入参
        # (标量投影形态,消费面 = entry 兼容调用,量级有界),扩修
        # 随该调用面的 session 通道批。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            scalar_projection_state as _proj,
        )
        _st_gs = _proj(gold=gold, level=level, plane=plane,
                       round_num=round_num, strategies=strategies)
        _rolls = min(6, refresh_ev_budget(_st_gs, None))
        if _rolls > 0:
            return NodeGoal(level, 'adaptive', 'd_search',
                            refresh_budget=_rolls)
        return NodeGoal(level, 'interest', 'hold')
    return NodeGoal(_expected_level(round_num, plane), "adaptive", "rush_level")


# ⚖️(2026-08-18):旧 影子接缝开关 HORIZON_SEAM_ACTIVE **已删**——切流
# 完成后 DP 是唯一姿态源(同一裁决连带删除 0126 区间回退表,见 get_node_goal 注释),开关无消费点。
# 历史:切流依据= 160 局交叉核对「表 hold→DP level」P1 高金段系统性分歧 + 六局 P1
# boss 稳定损 20-36 血→P2 残血开局即崩。回滚方式 = revert 预算收权迁移提交。



def effective_refresh_prob(gs: GameState, level: int, cost: int) -> float:
    """轮岗感知的有效刷新概率单一源。

    消费点 = mandate_v1 出口③ A 支对账(shop.py)+ 刷新上报随机态分支的
    采样表构建(``cw_shop_deal.state_deal_probs``;同一优先级链零复制),
    禁第二套对账语义——
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
    # refresh_probs = payload 域:离屏/缺读 None → 基线表(缺省语义同门)。
    _payload = gs.shop.value
    rp = _payload.refresh_probs if _payload is not None else None
    if not isinstance(rp, dict):
        return refresh_prob(level, cost)
    bar = rp.get(cost)
    if bar is None or bar <= 0:
        return refresh_prob(level, cost)
    return bar


# ===== 经济循环接缝族(自 decision_v2.economy_cycle 下沉;§3.3-①a/①b) =====
# 原址:decision_v2.economy_cycle(kernel→decision 断环:本文件是 kernel 层,
# cw_economy.get_node_goal 标量投影消费接缝,原函数体内懒 import 决策包
# 成环)。函数体零行为变化(等价测试=sr-od-test test_cw_w695_economy_seam.py +
# 既有经济接缝桩点测试重钉)。排程升级接缝(schedule_upgrade)已随
# 升级触发统一删除(升级判据归策略层单判据,R* 升级排程分量恒 0)。

#: 刷新通道容量上界(刷数;原 DP 求解面动作上限 6 刷同源(git prior art),
#: 不另造第二把尺)。自 economy_cycle 随接缝族同迁(单一源在本文件)。
REFRESH_ROLL_CAP: int = 6


def _registry_of(session: StrategySession) -> DecisionV2Registry:
    """接缝函数的注册表解析(A/B 注入面:strategy_state_of(session).v3_registry 显式注入
    优先,缺省落 DEFAULT_REGISTRY——缺省栈无注入分支,P6 契约同 prep_brain
    装配签名)。"""
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        strategy_state_of,
    )
    reg = getattr(strategy_state_of(session), 'v3_registry', None)
    return reg if isinstance(reg, DecisionV2Registry) else DEFAULT_REGISTRY


def _vd_core_of(session: StrategySession) -> str:
    """V_D/V_level 共用的目标核心解析(scoring.vd_target_core 同源;
    自 decision_v2.ev 下沉——ev 不 import decision_v2 包内模块的判据
    复刻惯例随单一源归位终结)。

    ⚠️ 边界申报:本函数懒 import 的 IntentionState/intention_core
    属**决策半部**——消费意向锁定状态机的 phase/locked_comp 判定与阵容核心
    派生,是刷新 EV 预算概率校准分量的目标解析链,不是经济事实
    (收入/息/卖退金/刷新价)。
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


def _target_peak_level(gs: GameState, session: StrategySession) -> int:
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

    P86 正本申报(p86-no-target-period-fund-allocation.md §4.1-1 选项
    「维持缺省 3 费」):未锁帧阵容核心锚(FALLBACK_COMP_NAME
    单线硬编码)已停用——峰值级锚只进概率校准分量,
    方向语义中性,未锁帧峰值档统一回落 3 费缺省。
    ⚠️ 边界申报:淘汰计划文档本体已不在仓(docs/develop/currency_war/archive/
    目录不存在,漂移登记见 P86 正本 §4.1-2),码内注释是原唯一在档裁决
    记录,本注即其承接。"""
    return _vd_core_of(session)


def _target_core_cost(session: StrategySession) -> tuple[str, int]:
    """排程目标核心 → (核心名,费用档)(与 _target_peak_level 的解析链
    同源拆值,供概率校准分量消费;核心解析单一源=_schedule_target_core)。"""
    core = _schedule_target_core(session)
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    ch = CHARACTERS.get(core) if core else None
    cost = ch.cost if ch is not None and ch.cost else 3
    return core, cost


def _owned_core_copies(gs: GameState, core: str) -> int:
    """目标核心已持有基础副本数 j(3合1 折算:star s → 3^(s-1);
    bench∪deployed 逐件计)。E_find 的 owned 修正输入
    (持有折算与 ``cw_shop_odds.reencounter_window_frames`` held 参数同口径:
    1★1/2★3/3★9);身份未识别的槽不计
    ——保守方向=低估持有 → E_find 偏大 → 帽偏松(不缩供给侧)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
        deployed_rows_of,
    )
    front, back = deployed_rows_of(gs)
    n = 0
    for u in (*front, *back, *bench_units_of(gs)):
        if u is not None and u.char_id == core:
            n += 3 ** ((u.star or 1) - 1)
    return n


def _omega_collapse_zeroed(gs: GameState, session: StrategySession,
                           registry: DecisionV2Registry,
                           target_cost: int) -> bool:
    """归零带判据(概率校准刷新预算的归零分支)。

    refresh_prob(state.level, target_cost) / refresh_prob(峰值级,
    target_cost) < registry.omega_collapse_ratio → 当前级对该目标费档
    无望,预算归零(合法 0 帧第三类)。
    - **空帧豁免**:非锁定核帧(意向走兜底链)恒 False——兜底 3 费不是
      真目标,对假目标算归零比会缩假目标供给、又可能误杀真目标(别的
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
    peak = _target_peak_level(gs, session)
    denom = refresh_prob(peak, target_cost)
    if denom <= 0:
        return False
    return refresh_prob(level_of(gs), target_cost) / denom \
        < registry.omega_collapse_ratio


def _find_budget_cap(gs: GameState, session: StrategySession,
                     registry: DecisionV2Registry, target_cost: int,
                     core: str) -> int:
    """有望帧帽 ⌈−ln(1−q)·E_find⌉(概率校准刷新预算的帽分支)。

    E_find = expected_refreshes_for_card(level, target_cost,
    target_star=2, owned=j)——首次集齐目标牌所需刷数的有限池精确期望;
    q=registry.refresh_find_quantile 为真分位,−ln(1−q) 是其闭式乘数
    (推导与标定待办见 registry 字段注释)。E_find=inf(P(0)≈1)时帽不覆盖
    (交金量式与 6 刷帽裁决);概率源单一址=cw_shop_odds
    (expected_refreshes_for_card 内部消费同表),禁第二概率口径。"""
    import math

    from sr_od.application.currency_war.data.cw_shop_odds import (
        expected_refreshes_for_card,
    )
    j = _owned_core_copies(gs, core)
    e = expected_refreshes_for_card(level_of(gs), target_cost,
                                    target_star=2, owned=j)
    if e == float('inf'):
        return REFRESH_ROLL_CAP
    return math.ceil(-math.log(1.0 - registry.refresh_find_quantile) * e)


def refresh_ev_budget(gs: GameState, session: StrategySession,
                      registry: DecisionV2Registry | None = None) -> int:
    """刷新 EV 授权刷数(确定性预算式;蓝图 §3.4 R4 接缝;
    概率校准分量=行内申报 历史)。

    ``registry``:显式注入优先(P6 契约:同一调用链全部接缝必须传
    **同一个** registry 实例);缺省落
    _registry_of(session) → DEFAULT_REGISTRY。
    预算 = min(6, ⌊(g − R*)/刷价⌋, ⌈−ln(1−q)·E_find⌉)——只花富余
    (规则倡导审读 §2-R3 预算式:刷新后仍守储备线;6 刷帽单一源
    = REFRESH_ROLL_CAP)∧ 有望帧帽按目标可寻性收紧。概率校准两条分支
    (采纳自其预研提案 B-v2):归零带归零(纯金量式与目标可寻性无关的病灶修法;
    归零的账=归零带留金弱占优纯烧)+ 有望帧分位帽;**求值次序=先归零
    后帽**(ρ 归零与 min 帽取交即 0,数值良定);概率单一址=cw_shop_odds
    (与分配器 Π_refresh 估计器同源互指,禁第二概率口径)。

    合法 0 帧契约(预算收权迁移前预验尸 D2 契约,判前锁):
    - ① g ≤ R* 常态帧(利息线以内/储备段持有,0.1/轮 真实收益)→ 0:这个 0
      流过 scoring P2 窗判据(``refresh_budget<=0 → 让位``)与存息
      准入门,「>0 即行动授权」的语义在预算函数口径下成立;
    - ② 归零带归零帧(锁定核解析帧 ∧ ``omega_collapse_ratio`` 判据为真;
      **例外注记:兜底链空帧归零判据恒 False,不属第二类**——D1「空帧
      不缩供给」契约优先)。
    定向刷新授权(directed_refresh_budget)是独立车道(arbiter E2,
    1 次/轮),与本预算不相交、不合并;按该车道对归零判据
    **同判据覆盖**(含空帧豁免,两车道逐帧一致)——arbiter 接线点待办:
    接线落地后补(判据单一址=本函数的 ``_omega_collapse_zeroed``,
    届时零新概率口径)。
    """
    reg = registry or _registry_of(session)
    over = gold_of(gs) - reserve_cap(gs, session)
    if over <= 0:
        return 0
    # 刷价缺省 = 建模基价显式消费(refresh_cost_effective 单一源;
    # 原帧 ``or 2`` falsy 兜底形态的消灭形态,数值恒同)。
    cost = refresh_cost_effective(gs=gs)
    core, target_cost = _target_core_cost(session)
    if _omega_collapse_zeroed(gs, session, reg, target_cost):
        return 0
    return min(min(REFRESH_ROLL_CAP, over // cost),
               _find_budget_cap(gs, session, reg, target_cost, core))


def reserve_cap(gs: GameState, session: StrategySession | None) -> int:
    r"""R\*(t) = 保利利息线(11 号稿 §3 金前提行;R4 规则集标量)。

    R\* 分量 = 保利利息线单项,升级不占 R\*(升级触发归策略层单判据
    三分派):升级攒批资金保护 = 升级资格门⑥资金线门(现金口径花后守
    saturation_line)+ 刷新判据「升级优先」支资金序。本函数保留
    为预算层 R\* 单一表达位
    (消费位 = refresh_ev_budget 溢余面 / economy_cycle.overflow/
    disclose_budget 披露面),保利利息线分量单一源 =
    ``saturation_line(cap_resolved_of_session(session))``
    (session resolved 链;利息帽取 cap_resolved(= 策略利息帽,禁
    ``registry.interest_cap × 10`` 旧式直乘——买断制(cap=0)囤金经
    本车道部分存活、利息上调(cap=10)时保利利息线会被低估)。写法
    保证「保利利息线 ≤ 封顶线」结构性成立——两者同源(cap_resolved),
    不可能出现保利利息线高于持有增益归零点(利息帽截断点)的态。
    """
    return saturation_line(cap_resolved_of_session(session))
