"""卖出通道排除仲裁·统一装配 A(T-126;P78 卖出资格仲裁不变量,ADR-0585)。

架构根(ADR-0585 §1):4 个卖出通道函数 × 9 个发射位 + 1 个投影读位的
排除装配此前在 7 个调用点各自手搓,共 5 种互不一致形态——同一架构根
在 W1/W3/W4/备战 F1(双攻击报告)与 entry 两处 funding 空装配(方案
v3 §2.9 新格 A)、P56 投影脱节(新格 B)反复发病。本模块把「不许卖谁」
收拢为单一入口 ``sell_exclusions``;通道保留「何时卖/卖多少/卖序」
(触发、止盈、排序、特有禁令),判据本体纯函数零改(B3 纪律,方案
v3 §3.2)。

落点声明(方案 v3 §3.1):不放 kernel、不放 criteria——A 消费策略器
会话态(MandateState.v3_intention / 统一发射登记簿),kernel 输入纯度
禁反向依赖;criteria 判据本体 = 纯函数,排除集由消费位传入。

A 三段(方案 v3 §2.2;与 ADR-0580「资格判定 = 物理硬闸 ∧ 身份分层 ∧
辖域闸三段式」同构):
1. 身份段(批 2 落地):义务基座(锁线态 = locked_buy_membership
   锁定采购集宽集 / 未锁态 = k_members,解析单点)∪ 静态持有两集
   (kernel.cw_card_identity.sell_hold_exclusion_names = registry 核心
   ∪ ④放行集)。辖义务类 + 持有类买因(τ=∞ 至账闭合事件,P78-2a;
   ③④ 持有件禁入一切通道燃料资格 = P41 燃料类「边际贡献≈0」资格
   本义,P78-4,非 P60 新辖域)。
2. 窗口段(本批落地):press 与 stall_protect 两类买入共簿登记
   {名 → (买因, 登记轮)},活跃判据 = 登记轮 == 当前轮(与 T3 同界,
   P78-2b)。**排除面 = press 类**:垫保类的通道处置属通道对价段
   defer(T3 不升入 A,方案 v3 §2.2 第 3 段——垫保在凑息是绝对跳过、
   在 M4/funding 是降序放行 = 转化类,P78-5′ 四关系表「放行(在册
   语义保持)」),经 ``stall_protect_active`` 视图喂 defer 参数;
   硬排除会杀死转化类放行 = 在册语义破面。press 类无对价豁免(P78-1
   无条件下),全通道硬禁。旧 ②(b) 动态集的 F1 锁线清空语义废除
   (P78-3:锁线定型不是任何买因类的账闭合事件,修法 = 轮界过期;
   过度禁卖上界 ≤1 轮有界可判读)。current_round=None ⇒ 窗口段失效
   = INV 显式例外,方向 = 放行向(V2-09;三读端同源 state.round_num,
   轮号恒可得,None 为死分支防御位)。
3. 通道对价段(显式豁免,每条一行+出处):funding 筹资兜底豁免
   (P78-5 四条件,``funding_hold_fallback`` 单一源供三消费位拼装)、
   line_switch 闭合线界投影(消费现参,行为等价)、projection 视图 =
   interest 全资格面(身份 ∪ 窗口 ∪ T3 活跃集,P78-6 读端同源,M7)。

发射登记统一(ADR-0585 §2/§3):``LaunchCause`` 闭集
{obligation, hold, press, stall_protect},12 买入臂逐一映射
(``LAUNCH_CAUSE_BY_ARM``,ADR 定稿载体);T3 垫保簿与 ②(b) 压库簿
完全合一为单载体双视图(载体属性沿用 T3 簿名——执行侧 cw_op_deploy
鸭子读契约在先,禁改名破契约)。生命周期四出口:卖出销 / 部署销 /
合成销(V2-05 新增)/ 轮界销;账闭合按五键分键承载(close_on_sell/
deploy/merge/round/switch)供矩阵断言可观测。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_card_identity import (
    TIER_TRANSITION,
    line_identity_tier,
    sell_hold_exclusion_names,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    locked_buy_membership,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BenchChar,
    bench_char_cost,
    sell_refund,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    refund_full_star_ok,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

#: 卖出通道闭集(方案 v3 §3.1)。新通道必须先在此登记再接线——枚举外
#: 值拒收(单一入口防线,防「新通道绕 A 手搓排除」的第五通道复发形态)。
SELL_CHANNELS: frozenset[str] = frozenset({
    'interest', 'funding', 'm4_fuel', 'line_switch', 'projection',
})

#: 买因闭集(ADR-0585 §2;12 买入臂 → 因果类映射的值域)。闭集外值
#: 拒收——新买入臂只有归入某因果类才合法(登记闭集强制,方案 v3 §5.3)。
LAUNCH_CAUSES: frozenset[str] = frozenset({
    'obligation', 'hold', 'press', 'stall_protect',
})

#: 窗口段辖域买因(P78 §2.2 第 2 段):压库与垫保两类,τ=同轮
#(登记轮==当前轮);obligation/hold 类 τ=∞,由身份段辖,登记仅作
#: 账本观测面(五键闭合分键),不入窗口段排除。
WINDOW_LAUNCH_CAUSES: frozenset[str] = frozenset({'press', 'stall_protect'})

#: 12 买入臂 → 因果类全映射(ADR-0585 §2 定稿载体;方案 v3 §3.1 表)。
#: 批 3 落写点的臂 = 窗口段两类(shop 发射位 _emit_buy 统一登记)+ ②(b)
#: 按 prio 三分显式传因;obligation/hold 类的 M2 族/C1/④ 产物由身份段
#: 辖(写点不辖行为),写点随矩阵批按需落——本表先钉全映射防第 5 臂复发。
LAUNCH_CAUSE_BY_ARM: dict[str, str] = {
    'm2_line_member': 'obligation',
    'm2_locked_member': 'obligation',
    'm2_stockpile': 'obligation',
    'm2_merge_completion': 'obligation',
    'dominance_buy': 'press',
    'm6_stockpile': 'press',
    'ev_buy': 'press',
    'core_single_card_buy': 'hold',
    'core_single_card_buy:unlocked': 'hold',
    'transition_component_buy': 'hold',
    # ②(b) 按 prio 三分(obligation/hold/press),发射位显式传因覆写本行。
    'dead_gold_press_buy': 'press',
    'fuel_filler_stall': 'stall_protect',
    't3_unlocked_hemostat': 'stall_protect',
}


def launch_cause_of(reason: str) -> str | None:
    """买入臂名(BuyCard.reason)→ 因果类(LAUNCH_CAUSE_BY_ARM 查因;
    未映射臂 = None——新臂必须先入映射表再可登记,登记闭集强制)。"""
    return LAUNCH_CAUSE_BY_ARM.get(reason)


#: 统一发射登记簿载体属性(MandateState 字段名)。沿用 T3 垫保簿旧名:
#: 执行侧 cw_op_deploy.prune_fuel_filler_deployed /
#: record_fuel_filler_held_postbuy 按鸭子属性读本名(属性契约级接线,
#: 禁 import 策略模块),改名 = 静默断供给(读 None → 部署销恒 0);
#: 语义已从 T3 专用簿升级为四因类登记簿,见 MandateState 字段注释。
LAUNCH_REGISTRY_ATTR: str = 'cw4_fuel_filler_stall_buys'

#: 兼容别名(T3 时代常量;mandate.py 再出口与既有测试引用零断链)。
STALL_BUYS_ATTR: str = LAUNCH_REGISTRY_ATTR


def _counters_of(session: StrategySession) -> dict | None:
    """分键容器读口(缺容器 = 不计数,不静默造桶——计数面自带载体)。"""
    ct = getattr(state_of(session), 'cw4_counters', None)
    return ct if isinstance(ct, dict) else None


def _bump(counters: dict | None, key: str, n: int = 1) -> None:
    """分键累加(counters=None = 观测缺载体,零静默跳过)。"""
    if counters is not None:
        counters[key] = counters.get(key, 0) + n


def _registry_of(session: StrategySession) -> dict:
    """登记簿读口(dict 载体缺省就地建;旧 set 载体容忍在读端逐点处理)。"""
    st = state_of(session)
    reg = getattr(st, LAUNCH_REGISTRY_ATTR, None)
    if not isinstance(reg, dict):
        reg = {}
        setattr(st, LAUNCH_REGISTRY_ATTR, reg)
    return reg


def _entry_norm(value: object) -> tuple[str, int | None]:
    """登记值归一:新形态 (买因, 轮);旧 T3 int 轮戳 → stall_protect
    (T3 值形态在先,归一只读不回写——就地改值会破坏既有测试/会话的
    载体观测面,值升级由写端自然完成)。"""
    if isinstance(value, tuple) and len(value) == 2:
        return str(value[0]), (int(value[1]) if value[1] is not None else None)
    if isinstance(value, int):
        return 'stall_protect', value
    return 'stall_protect', None


# ===== 发射登记 API(写端 + 四出口生命周期;ADR-0585 §2/§3)=====


def register_launch(session: StrategySession,
                    name: str, *, cause: str, round_num: int,
                    star: int | None = None, cost: int | None = None,
                    ) -> bool:
    """买入发射登记(写端单一源;P78 §2.2 窗口段载体)。

    簿形态 = {名: (买因, 登记轮)},同名重登记覆盖(最新买因胜——
    排除面按名判定,单名多笔并发登记以最近授权为准,同轮界同过期)。

    ``cause`` 闭集外值抛错(登记闭集强制)。

    hold 类附类资格断言(W5 登记侧;N1/V2-06):名 ∈ 静态持有集 ∧
    该层买入硬闸通过(transition 层 = refund_full_star_ok 1★ 全额退,
    vopt 单一源;registry_core 层 = 恒买无星闸,裁定410/ADR-0569)。
    违例 = launch_cause_mismatch 计数红 + 拒绝该笔登记,**不拦发射**
    ——买面门槛(W5 本体)归臂自身判据批,防范围 smuggle(方案 v3
    §4.3 划界)。红证存在性:2★ 转线直出卡名 ∈ TRANSITION_PACK ⊆
    静态持有集(名字腿必过),红由硬闸腿产生。

    返回登记是否落账(断言拒收/空名 = False;测试断言用)。
    """
    if not name:
        return False
    if cause not in LAUNCH_CAUSES:
        raise ValueError(
            f'未知买因 {cause!r}:合法闭集 = {sorted(LAUNCH_CAUSES)}'
            ' (ADR-0585 §2;新买因先登记 LAUNCH_CAUSES 再接线)')
    counters = _counters_of(session)
    if cause == 'hold' and not _hold_qualification_ok(name, star, cost,
                                                      counters):
        return False
    _registry_of(session)[name] = (cause, int(round_num))
    return True


def _hold_qualification_ok(name: str, star: int | None, cost: int | None,
                           counters: dict | None) -> bool:
    """hold 类登记资格 = 名字腿 ∧ 硬闸腿(V2-06 合取;缺合取则 2★
    转线登记恒绿 = 锁恒绿形态,红对由硬闸腿补齐)。registry_core 层
    恒买无星闸(裁定410);其余在册档(transition)按 1★ 全额退硬闸;
    星/费缺读 = fail-closed 拒登记(资格判据禁缺读放行)。"""
    name_ok = name in sell_hold_exclusion_names()
    tier = line_identity_tier(name)
    if tier == TIER_TRANSITION:
        gate = (star is not None and cost is not None
                and refund_full_star_ok(int(star), int(cost)))
    else:
        # registry_core 层(裁定410 恒买)与静态集兜底域:无星闸。
        gate = True
    ok = name_ok and gate
    if not ok:
        _bump(counters, 'launch_cause_mismatch')
    return ok


def consume_on_sell(session: StrategySession, name: str) -> None:
    """出口①卖出销(账兑现):该名被任一通道实际卖出时销账,防同
    visit 内第二次命中。分键 close_on_sell(五键账闭合,方案 v3 §5.3)。
    容旧 set 载体(兼容未升级会话;旧形态无因类,不计分键)。"""
    if not name:
        return
    reg = getattr(state_of(session), LAUNCH_REGISTRY_ATTR, None)
    if isinstance(reg, dict):
        if name in reg:
            del reg[name]
            _bump(_counters_of(session), 'close_on_sell')
    elif isinstance(reg, set):
        reg.discard(name)


def prune_on_deploy(session: StrategySession, deployed_names: object) -> int:
    """出口②部署销(件离场闭合):上板名登记账移除(保护使命完成,
    P24/M1 同帧部署语义;漏销 = 后续误保面)。分键 close_on_deploy。
    返回销账数(测试断言用)。容旧 set 载体(仅成员摘除,不计分键
    ——旧载体无因类语义,计了也是假账)。"""
    reg = getattr(state_of(session), LAUNCH_REGISTRY_ATTR, None)
    if isinstance(reg, set):
        hit = {n for n in reg if n in set(deployed_names or ())}
        reg.difference_update(hit)
        return len(hit)
    if not isinstance(reg, dict) or not reg:
        return 0
    hit = [n for n in reg if n in set(deployed_names or ())]
    for n in hit:
        del reg[n]
    if hit:
        _bump(_counters_of(session), 'close_on_deploy', len(hit))
    return len(hit)


def consume_on_merge(session: StrategySession, name: str) -> int:
    """出口②′合成销(V2-05 新增;件离场闭合):同名 1★ 三张买入应用
    即合成 2★,登记的 1★ 副本离场——不销则同名再买 1★ 被过禁(≤1 轮
    有界)。分键 close_on_merge。返回销账数(测试断言用)。未接线
    窗口有界性:滞留 ≤1 轮,轮界销兜底(方案 v3 §3.1 申报)。"""
    if not name:
        return 0
    reg = getattr(state_of(session), LAUNCH_REGISTRY_ATTR, None)
    if isinstance(reg, dict) and name in reg:
        del reg[name]
        _bump(_counters_of(session), 'close_on_merge')
        return 1
    if isinstance(reg, set) and name in reg:
        reg.discard(name)
        return 1
    return 0


def active_window(session: StrategySession, current_round: int | None, *,
                  counters: dict | None = None) -> frozenset[str]:
    """窗口段读端(P78 §2.2 第 2 段;出口③轮界销,读端就地销账)。

    **排除面 = press 类**(硬禁;垫保的通道处置 = defer 对价,见模块
    docstring 第 2 段与 P78-5′ 四关系表)。两类共享轮界过期生命周期
    (本读端过期销账不分因类):press 类过期计 press_window_expired_
    round,stall_protect 类过期计 t3_protect_expired_round(键名零断
    链),账闭合键 close_on_round 合计(五键分键,方案 v3 §5.3)。
    current_round=None ⇒ 窗口段失效(V2-09:INV 显式例外,方向 =
    放行向;轮不可得帧登记全集按过期销账,T3 既有语义继承)。
    同帧多读端幂等:首个读端完成过期销账,后续读端见空集零重复计数。
    """
    return _expire_and_read(session, current_round,
                            face_causes=frozenset({'press'}),
                            counters=counters)


def stall_protect_active(session: StrategySession, current_round: int | None,
                         *, counters: dict | None = None,
                         ) -> frozenset[str]:
    """T3 垫保单类视图(stall_protect 因果类;defer 通道专用——垫保
    在凑息是绝对跳过、在 M4/funding 是降序放行,通道对价语义,与窗口
    段排除是两个面)。press 类登记名不入本视图;轮界过期与本视图共享
    单点销账(两类一同过期,过期计数按因类分键,禁双读端重复计数)。"""
    return _expire_and_read(session, current_round,
                            face_causes=frozenset({'stall_protect'}),
                            counters=counters)


def _expire_and_read(session: StrategySession, current_round: int | None, *,
                     face_causes: frozenset[str],
                     counters: dict | None) -> frozenset[str]:
    """轮界过期(两类共簿共享)+ 因类过滤读(窗口段与 T3 视图单点)。

    旧裸 set 载体(轮戳缺失)= 轮界硬兜底整集失效并升级 dict(T3 先例
    mandate.py 既有语义平移)。obligation/hold 类登记不轮界过期
    (τ=∞,P78-2a),由卖出/部署/合成/换线出口闭合。
    ``counters=None`` = 读会话容器(state_of(session).cw4_counters;
    缺容器 = 不计数,窗口段诊断键经 sell_exclusions 读端照常显影)。
    """
    if counters is None:
        counters = _counters_of(session)
    st = state_of(session)
    reg = getattr(st, LAUNCH_REGISTRY_ATTR, None)
    if reg is None:
        return frozenset()
    if not isinstance(reg, dict):
        # 旧 set 载体:整集过期销账后升级 dict(因类不可辨,按 T3 计)
        setattr(st, LAUNCH_REGISTRY_ATTR, {})
        _bump(counters, 't3_protect_expired_round', len(reg))
        _bump(counters, 'close_on_round', len(reg))
        return frozenset()
    rn = int(current_round) if current_round is not None else None
    expired = []
    for n, value in list(reg.items()):
        cause, seen = _entry_norm(value)
        if cause not in WINDOW_LAUNCH_CAUSES:
            continue   # obligation/hold 类 τ=∞,不轮界过期
        if rn is None or seen is None or seen != rn:
            del reg[n]
            expired.append(cause)
    if expired:
        _bump(counters, 'close_on_round', len(expired))
        _bump(counters, 't3_protect_expired_round',
              expired.count('stall_protect'))
        _bump(counters, 'press_window_expired_round',
              expired.count('press'))
    active = {n for n, value in reg.items()
              if _entry_norm(value)[0] in face_causes}
    return frozenset(active)


def _close_switched_obligations(session: StrategySession,
                                base: set[str]) -> None:
    """换线闭合读点(P78 §2.1 账闭合事件「线账闭合」;N6:撤销出口
    ①②③ 与换线同义同效):义务类登记名已不在义务基座 = 线账已闭合,
    登记账就地销账 + close_on_switch 分键。读点幂等(销账后不可再命中);
    hold 类不受此出口辖(④件 = 候选终局线结构件,线账闭合不注销持有账,
    P78 §2.1 分类表「无时间闭合」)。行为零面:义务类不入窗口段排除,
    本闭合纯账本观测(五键分键承载,方案 v3 §5.3)。"""
    reg = getattr(state_of(session), LAUNCH_REGISTRY_ATTR, None)
    if not isinstance(reg, dict) or not reg:
        return
    closed = 0
    for n in list(reg):
        cause, _seen = _entry_norm(reg[n])
        if cause == 'obligation' and n not in base:
            del reg[n]
            closed += 1
    if closed:
        _bump(_counters_of(session), 'close_on_switch', closed)


# ===== 装配 A(身份段 + 窗口段 + 通道对价段)=====


def _resolve_base(session: StrategySession,
                  k_members: tuple[str, ...],
                  ) -> tuple[frozenset[str] | None, set[str]]:
    """义务基座解析单点(身份段第 1 构件;ADR-0580 §7 低-1 修复平移)。

    锁线态 = ``locked_buy_membership(ist)`` 锁定采购集宽集,未锁态 =
    ``k_members``。返回 (锁定解析结果, 基座集):解析结果供本模块内
    两处单点消费(换线闭合读点的基座对账 + funding 兜底减法②,
    P78-5 池定义「义务基座产物」同源),禁调用侧自选基座——宽−窄成员
    被卖出 → shop 域 M2 重买 = Z1 锁线域残留病理(与 shop.py
    ``buy_members`` 装配同一语义源 = cw_intention.locked_buy_membership)。
    """
    st = state_of(session)
    locked = locked_buy_membership(getattr(st, 'v3_intention', None))
    base = set(locked) if locked is not None else set(k_members)
    return locked, base


def identity_exclusions(session: StrategySession,
                        k_members: tuple[str, ...]) -> set[str]:
    """装配 A 身份段(方案 v3 §2.2 第 1 段;P78 INV)。

    = 义务基座 ∪ 静态持有两集。静态/动态切分与「禁静态全集」论证
    (name 型零重叠语义下静态全集排除会掏空 (a) 的全部 1★ 燃料资格,
    方案审 v3 攻击点①实证)继承 Z1(ADR-0580);本集取窄形态 =
    基座 ∪ 注册表两集,覆盖「已买待持有」与「在售未买」两态。

    附带换线闭合读点(义务类登记账对账,见
    ``_close_switched_obligations``;读端幂等,行为零面)。
    """
    _locked, base = _resolve_base(session, k_members)
    _close_switched_obligations(session, base)
    excl = set(base)
    excl |= set(sell_hold_exclusion_names())
    return excl


def sell_exclusions(session: StrategySession,
                    k_members: tuple[str, ...], *, channel: str,
                    current_round: int | None = None) -> frozenset[str]:
    """统一装配 A 单一入口(P78 INV 主不变量;ADR-0585 §2/§3)。

    任何卖出通道的资格排除必须经本入口装配——「不许卖谁」独占于 A,
    消费位禁手搓排除集。批 3 全量形态 = 身份段 ∪ 窗口段;projection
    通道视图 = interest 全资格面再并 T3 活跃集(P78-6 读端同源/M7:
    凑息实际资格面含 T3 绝对跳过,投影漏 T3 则 liquid_refund 高估 →
    s_reserve 低估 → 预留被吃;T3 的 defer 参数语义零改,B3)。

    ``channel``:卖出通道标记(SELL_CHANNELS 闭集;枚举外值抛错)。
    ``current_round``:窗口段活跃判据轮号(M5 定稿;三读端同源
    state.round_num);None ⇒ 窗口段失效 = INV 显式例外,方向 = 放行向
    (V2-09;实际全部消费位轮号恒可得,死分支防御位)。
    """
    if channel not in SELL_CHANNELS:
        raise ValueError(
            f'未知卖出通道 {channel!r}:合法闭集 = {sorted(SELL_CHANNELS)}'
            ' (方案 v3 §3.1;新通道先登记 SELL_CHANNELS 再接线)')
    excl = identity_exclusions(session, k_members)
    if current_round is not None:
        excl |= active_window(session, current_round)
    if channel == 'projection':
        # T3 活跃集并入投影视图(资格级 defer 的读端同源;通道侧
        # defer 参数不升入 A,判据本体零改——方案 v3 §2.8/M7)。
        excl |= stall_protect_active(session, current_round)
    return frozenset(excl)


def funding_hold_fallback(session: StrategySession,
                          k_members: tuple[str, ...],
                          bench: list[BenchChar], *, gold: int, need: int,
                          a_exclusions: frozenset[str] | set[str],
                          ) -> list[BenchChar]:
    """funding 持有件兜底豁免(P78-5 四条件单一源;三消费位拼装用)。

    触发前提由消费位判(主路径空 ∧ 仍需筹资 = gold < need);本函数
    只承载兜底池定义与达成量化(P78-5 条③机制授权条款,V3-04):

    - 兜底池 = (A 排除集 ∩ 静态持有集) − cw4_visit_bought_names(减法①,
      本 visit 买入禁入——否则豁免机制自己制造 P78-1 同 visit 违例)
      − 义务基座产物(减法②,locked_buy_membership;未锁态 = k_members,
      此时与 funding 判据内部 zero_overlap 重叠,减法冗余但无害);
      prep 位减法①实际辖「上一 visit」买入名(prep 卖出恒先于本轮
      买入 + visit 入口清账,方向偏保守无害,V2-10 语义注);
    - 取 (star, slot) 序首件;达成量化 = 本笔退金 ≥ need − gold——
      refund < 缺口帧不放行,否则持有件期权损失(P01)已付而义务仍未
      达成,严格有害;该量化同时封死逐帧级联清空兜底池而始终不达
      need 的路径。

    返回至多一件(单笔即止,need 即止);空列表 = 无合法兜底。
    """
    st = state_of(session)
    _locked, base = _resolve_base(session, k_members)
    holds = sell_hold_exclusion_names()
    visit = set(getattr(st, 'cw4_visit_bought_names', ()) or ())
    pool = [b for b in bench
            if (b.char_id or '') in holds
            and (b.char_id or '') in a_exclusions
            and (b.char_id or '') not in visit
            and (b.char_id or '') not in base]
    pool.sort(key=lambda b: (b.star, b.slot))
    gap = need - gold
    for b in pool:
        if sell_refund(b.star, bench_char_cost(b)) >= gap:
            return [b]
    return []


def sell_hold_exclusions(session: StrategySession,
                         k_members: tuple[str, ...]) -> frozenset[str]:
    """凑息通道身份段(兼容再出口;批 3 渐进迁移终点形态)。

    生产消费位已全量迁移 ``sell_exclusions(channel='interest',
    current_round=...)``(批 3;ADR-0585 渐进迁移申报)——本名保留 =
    测试/外部引用零断链,语义 = 身份段(无轮号 ⇒ 窗口段失效,V2-09
    放行向例外)。

    旧 F1 锁线清空语义已废除(P78-3:锁线定型不是任何买因类的账闭合
    事件;W3 漏口修法 = 轮界过期,随窗口段在 sell_exclusions 承载)——
    本出口不再消费动态登记、也不再清空旧载体。
    """
    return sell_exclusions(session, k_members, channel='interest')
