"""统一保护集(买卖身份同源;全仓单一源)。

迭代出处 = ``changes/2026-10-15-unified-protection-set/design.md``
(§2.1 方向状态模型 / §2.7 关键取舍)。保护集回答「哪些牌是『自己人』」:
买面序 1 名单与卖面禁卖身份自本模块单一取源(接线归后续批,本批只建
函数与状态槽写点)。

两个域、同一套候选→锁定语义(design §2.1 表):

- **过渡域**(plane2_started = 假):候选 = 四体系**全体**注册表成员;
  锁定 = 已点亮体系(支持度达标,可多个,持久槽
  ``StrategyState.transition_locked_systems`` 幂等只增);
- **终局域**(plane2_started = 真):候选 = 候选 top3 线成员;锁定 =
  锁定线名单。过渡域在翻真帧整体关闭,非终局线成员自然滑向可卖
  (与 stage_transitions Q2 换血保留率数据对齐)。

体系键与成员集单一源(design §2.1 定死):三羁绊键 import 面唯一指向
``knowledge/cw_engine_facts.TRANSITION_TRAITS``;成员枚举消费
``knowledge/cw_line_facts.bond_members`` 公开口;希儿系成员判定单一源 =
现役 ``is_seele_system_member``。本模块不消费 ``GUARD_SYSTEM_TIERS``
(守卫档位面,非本模块依赖)。

依赖方向:本模块属策略实现层,可依 kernel/knowledge/同包 session
作用域;shop 等消费方 import 本模块(贯穿件常量自 shop 迁入本模块,
shop 回导),本模块禁反向 import 消费方。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    is_seele_system_member,
)
from sr_od.application.currency_war.kernel.cw_game_state import GameState

# 点亮判定的 kernel 支持度链为私有形态(下划线)。design §2.1 落地批注:
# 跨模块消费若遇访问限制则公开化随批申报;Python 下划线仅约定无强制,
# 未遇访问限制 → 按现名消费(禁复制实现),不触 kernel 文件面。
from sr_od.application.currency_war.kernel.cw_intention import (
    P1_PAIR_LOCK_MIN_SUPPORT,
    _p1_system_support,
)
from sr_od.application.currency_war.knowledge.cw_engine_facts import (
    TRANSITION_TRAITS,
)
from sr_od.application.currency_war.knowledge.cw_line_facts import (
    SEELE_SYSTEM,
    bond_members,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    session_scope,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    StrategyState,
)

#: 全线路通用贯穿件恒囤名单(shop_session §2.2 序 1 未锁定期囤积纪律;
#: 「真贯穿层」= Early→Final 全程留用层——E→F 0.66-0.95 与「早期核心」
#: 一致,出处 = docs/game/currency_war/research/stage_transitions.md Q1 表
#: 第一档)。策略层立场常量(「恒囤」为策略裁定,名单随攻略数据修订走
#: research 重跑;3.7 候选内核实现后随选线函数统一消费)。
#: 单一源搬家自 shop.py(本迭代 design §2.1),shop 回导维持旧消费点。
CROSS_LINE_KEEP_NAMES: frozenset[str] = frozenset({
    '千冶·刃', '三月七', '花火', '星期日',
})

#: 四体系全体成员(过渡域候选集):
#: - 三羁绊系 = TRANSITION_TRAITS 键经 ``bond_members`` 全成员枚举
#:   (阵营∪流派口径);
#: - 希儿系 = 现役 ``is_seele_system_member`` 全注册表枚举(希儿本人 +
#:   量子同频/贝洛伯格放大器)。
#: 注册表为导入期静态数据,模块级一次派生(零行为:值只在注册表)。
_FOUR_SYSTEM_MEMBERS: frozenset[str] = frozenset(
    {m for bond, _t in TRANSITION_TRAITS for m in bond_members(bond)}
    | {name for name, ch in CHARACTERS.items()
       if is_seele_system_member(name, {*ch.factions} | {*ch.flows})})


def four_system_members() -> frozenset[str]:
    """四体系全体成员名集只读口(:data:`_FOUR_SYSTEM_MEMBERS` 的公开形态)。

    消费面 = 测试/判读侧的「非自己人」名选取(与保护集同一成员派生,
    禁第二实现);决策面一律经 :func:`protection_membership`(带域分派),
    不直读本集。
    """
    return _FOUR_SYSTEM_MEMBERS


def protection_membership(gs: GameState, state: StrategyState) -> frozenset[str]:
    """保护集成员名集(全仓单一源;design §2.1 域分派)。

    公共构成(两域同吃)= 贯穿件 ∪ 已锁定终局线成员 ∪ 候选 top3 终局
    线成员——锁定线名单经 ``line_members_view`` 读口;候选快照解析失败
    (注册表漂移)跳过并告警,该线贡献空集(与 ``sell_line_membership``
    同款保守方向:少保护 = 多可卖,自救面不受阻)。锁定帧候选快照恒空
    (锁定写入时已清空停算),故「锁定 ∪ 候选」并集与现行两分支语义
    同构。``state`` 必须是挂接在 ``gs`` 上的策略器状态
    (``gs.strategy_state`` 同源对象)。

    过渡域(plane2_started = 假)额外并集四体系**全体**成员
    (:data:`_FOUR_SYSTEM_MEMBERS`)——过渡锁定体系 ⊆ 候选全体,对保护
    集无增量(design §2.1 注)。终局域不加:位面 2 起保护 = 终局候选/
    锁定 + 贯穿件,过渡件滑向可卖。

    消费面(后续批接线,本批零消费):买面序 1 未锁定名单并集(3.2)、
    卖出资格装配 A 身份段(3.3)。
    """
    names: set[str] = set(CROSS_LINE_KEEP_NAMES)
    view = session_scope.line_members_view(gs)
    names |= set(view.members)
    for comp_name in state.line_candidates:
        comp = get_comp(comp_name) if comp_name else None
        if comp is None:
            log.warning('[cw!][protection] 候选线名解析失败(%s),'
                        '该线成员不入保护集', comp_name)
            continue
        names |= set(comp.core_chars)
        names |= set(getattr(comp, 'shared_chars', None) or ())
    if not session_scope.plane2_started_of(gs):
        names |= _FOUR_SYSTEM_MEMBERS
    return frozenset(names)


def refresh_transition_locked_systems(gs: GameState,
                                      state: StrategyState) -> None:
    """过渡锁定状态槽刷新(写入端单一源;幂等只增不减)。

    判定 = design §2.1「点亮(过渡锁定)」:复用现役支持度链
    ``_p1_system_support``(持有域 = bench ∪ deployed),达标门槛 =
    ``P1_PAIR_LOCK_MIN_SUPPORT``(支持度 1.0 = 体系满员,与配方对锁定
    门槛同一常数,禁另立阈值)。希儿系取支持度链字典的希儿系项——该
    项即 ``_seele_system_support`` 的输出(链内单一实现),其首行含希儿
    在场门:希儿缺席恒 0.0。**复用面不含 ``seele_system_formed``**(板面
    域,成型停手语义;持有域选定见 design §2.1 双源差异申报)。

    - 幂等只增:已入槽体系不因支持度回落移除(design §2.7 锁定持久化
      取舍);每次全量现算「本帧达标集」并与旧槽并集;
    - 位面适用范围:plane2_started 翻真即整域关闭(早退不再入账)——
      清空由 flow 进 P2 分支(配方退场同点)负责,本函数只负责 P1 侧
      单调增长。
    """
    if session_scope.plane2_started_of(gs):
        return   # 过渡域已关闭(design §2.1 域切换;清空点在 flow)
    sup = _p1_system_support(gs)
    reached = frozenset(
        bond for bond, _t in TRANSITION_TRAITS
        if sup.get(bond, 0.0) >= P1_PAIR_LOCK_MIN_SUPPORT)
    if sup.get(SEELE_SYSTEM, 0.0) >= P1_PAIR_LOCK_MIN_SUPPORT:
        reached = reached | {SEELE_SYSTEM}
    if reached:
        state.transition_locked_systems = (
            state.transition_locked_systems | reached)
