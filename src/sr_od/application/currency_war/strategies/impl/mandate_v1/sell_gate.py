"""卖出通道排除仲裁·统一装配 A(T-126;P78 卖出资格仲裁不变量,ADR-0585)。

架构根(ADR-0585 §1):4 个卖出通道函数 × 9 个发射位 + 1 个投影读位的
排除装配此前在 7 个调用点各自手搓,共 5 种互不一致形态——同一架构根
在 W1/W3/W4/备战 F1(双攻击报告)与 entry 两处 funding 空装配(方案 v3
§2.9 新格 A)、P56 投影脱节(新格 B)反复发病。本模块把「不许卖谁」
收拢为单一入口 ``sell_exclusions``;通道保留「何时卖/卖多少/卖序」
(触发、止盈、排序、特有禁令),判据本体纯函数零改(B3 纪律,方案
v3 §3.2)。

落点声明(方案 v3 §3.1):不放 kernel、不放 criteria——A 消费策略器
会话态(MandateState.v3_intention / cw4_dead_gold_bought_names),kernel
输入纯度禁反向依赖;criteria 判据本体 = 纯函数,排除集由消费位传入。

A 三段(方案 v3 §2.2;与 ADR-0580「资格判定 = 物理硬闸 ∧ 身份分层 ∧
辖域闸三段式」同构):
1. 身份段(永久,本批落地):义务基座(锁线态 = locked_buy_membership
   锁定采购集宽集 / 未锁态 = k_members,解析单点)∪ 静态持有两集
   (kernel.cw_card_identity.sell_hold_exclusion_names = registry 核心
   ∪ ④放行集)。辖义务类 + 持有类买因(τ=∞ 至账闭合事件,P78-2a;
   ③④ 持有件禁入一切通道燃料资格 = P41 燃料类「边际贡献≈0」资格
   本义,P78-4,非 P60 新辖域)。
2. 窗口段(动态,批 3):press 与 stall_protect 两类买入的发射登记
   {名 → (买因, 登记轮)},活跃判据 = 登记轮 == 当前轮。现行 ②(b)
   动态登记集的 F1 锁线清空语义仍在役(P78-3 已证其为错误,修法随
   批 3),批 2 平移保留于 ``sell_hold_exclusions``。
3. 通道对价段(显式豁免,每条一行+出处,批 3):funding 筹资兜底豁免
   (P78-5 四条件)、line_switch 闭合线界投影、projection 视图并 T3
   活跃集(M7)。

通道闭集 = {interest, funding, m4_fuel, line_switch, projection}
(方案 v3 §3.1);批 2 身份段通道无关(各通道同集),通道参数为对价
段/视图路由的定形位。current_round(M5 定稿签名)为批 3 窗口段签名
位,批 2 接受不消费;None ⇒ 窗口段失效 = INV 显式例外,方向 = 放行向
(V2-09;三读端同源 state.round_num,轮号恒可得,None 为死分支防御位)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_card_identity import (
    sell_hold_exclusion_names,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    locked_buy_membership,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
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


def _resolve_base(session: StrategySession,
                  k_members: tuple[str, ...],
                  ) -> tuple[frozenset[str] | None, set[str]]:
    """义务基座解析单点(身份段第 1 构件;ADR-0580 §7 低-1 修复平移)。

    锁线态 = ``locked_buy_membership(ist)`` 锁定采购集宽集,未锁态 =
    ``k_members``。返回 (锁定解析结果, 基座集):解析结果供动态生命
    周期消费(``sell_hold_exclusions`` 的 F1 清空判据与本基座共用同一
    次解析,单点双消费禁第二读);禁调用侧自选基座——宽−窄成员被
    卖出 → shop 域 M2 重买 = Z1 锁线域残留病理(与 shop.py
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
    """
    _locked, base = _resolve_base(session, k_members)
    excl = set(base)
    excl |= set(sell_hold_exclusion_names())
    return excl


def sell_exclusions(session: StrategySession,
                    k_members: tuple[str, ...], *, channel: str,
                    current_round: int | None = None) -> frozenset[str]:
    """统一装配 A 单一入口(P78 INV 主不变量;ADR-0585 §2/§3)。

    任何卖出通道的资格排除必须经本入口装配——「不许卖谁」独占于 A,
    消费位禁手搓排除集。批 2 = 身份段全覆盖(方案 v3 §6.1):各通道
    返回同一身份段;窗口段与通道对价段随批 3 接线(届时 interest 视图
    = 身份段 ∪ 窗口段,projection 视图 = interest 全资格面并 T3 活跃集,
    P78-6/M7)。

    ``channel``:卖出通道标记(SELL_CHANNELS 闭集;枚举外值抛错)。
    ``current_round``:批 3 窗口段签名位(M5 定稿形态,批 2 接受不消费
    ——签名先行定形,免批 3 再改全部消费位签名);None ⇒ 窗口段失效
    = INV 显式例外,方向 = 放行向(V2-09)。
    """
    if channel not in SELL_CHANNELS:
        raise ValueError(
            f'未知卖出通道 {channel!r}:合法闭集 = {sorted(SELL_CHANNELS)}'
            ' (方案 v3 §3.1;新通道先登记 SELL_CHANNELS 再接线)')
    return frozenset(identity_exclusions(session, k_members))


def sell_hold_exclusions(session: StrategySession,
                         k_members: tuple[str, ...]) -> set[str]:
    """凑息通道排除集(原 mandate.sell_hold_exclusions 平移;兼容签名,
    消费点渐进迁移申报 ADR-0585——凑息两消费位批 2 仍经本出口消费,
    批 3 换窗口段 API;mandate 模块保留同名再出口,测试引用零断链)。

    = 身份段(identity_exclusions)∪ ②(b) 动态买入登记集(mandate_state
    .cw4_dead_gold_bought_names)。动态集生命周期暂保留 F1 申报形态:
    锁线定型时清空——定型后 ④ 放行收窄、静态集护住持有面,残留登记
    只对 Early 期 (b) 买入的燃料件造成过度禁卖。P78-3 已证明「锁线
    定型不是账闭合事件」、清空改轮界过期属批 3(ADR-0585 消费限制:
    F1 语义仍在役,批 2 平移零行为变更,B3)。清空判据与义务基座共用
    同一次解析(单点双消费),在读点惰性清,不挂锁线转移钩子。

    funding 有意不扩本集的 F2 申报已由 ADR-0585 §4 拆三块修订:义务
    基座并入全部 funding 消费位(经 ``sell_exclusions``),③④ 持有件
    变现降级为显式兜底豁免(P78-5,批 3 接线)。
    """
    st = state_of(session)
    locked, base = _resolve_base(session, k_members)
    excl = set(base)
    excl |= set(sell_hold_exclusion_names())
    if locked is not None:
        st.cw4_dead_gold_bought_names.clear()   # F1:定型清空(见 docstring)
    else:
        excl |= set(st.cw4_dead_gold_bought_names)
    return excl
