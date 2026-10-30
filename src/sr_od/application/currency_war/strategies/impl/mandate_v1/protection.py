"""万金油贯穿件名单与过渡锁定状态槽(mandate_v1 策略实现层)。

**保护集退役申报(统一让位优先级迭代 3.4,拆除清单 §3)**:本模块
原「统一保护集」判据件(:func:`protection_membership` 及四体系全体
成员集)已整段退役——静态不许卖名单与买面囤货判据随总纲 §2.5 拆除,
「谁不该卖/谁该买」改由统一让位序列(criteria/priority.sell_order)
与序 1 义务面承载;本模块保留的仅有两件**数据源/写入端**:

- :data:`CROSS_LINE_KEEP_NAMES`(万金油四角色名单)——统一价值序
  档 6(全线留用层)的判定数据源(消费 = criteria/priority.py;
  名单随攻略数据修订走 research 重跑);
- :func:`refresh_transition_locked_systems`(过渡锁定状态槽写端)——
  配方对锁定判据的派生缓存写入端(flow 层消费)。

依赖方向:本模块属策略实现层,可依 kernel/knowledge/同包 session
作用域;禁反向 import 消费方。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.kernel.cw_intention import (
    P1_PAIR_LOCK_MIN_SUPPORT,
    _p1_system_support,
)
from sr_od.application.currency_war.knowledge.cw_engine_facts import (
    TRANSITION_TRAITS,
)
from sr_od.application.currency_war.knowledge.cw_line_facts import (
    SEELE_SYSTEM,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    session_scope,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    StrategyState,
)

# 点亮判定的 kernel 支持度链为私有形态(下划线)。设计落地批注:
# 跨模块消费若遇访问限制则公开化随批申报;Python 下划线仅约定无强制,
# 未遇访问限制 → 按现名消费(禁复制实现),不触 kernel 文件面。

#: 万金油四角色名单(统一价值序档 6「全线留用层」判定数据源;
#: 「真贯穿层」= Early→Final 全程留用层——E→F 0.66-0.95 与「早期核心」
#: 一致,出处 = docs/game/currency_war/research/stage_transitions.md Q1 表
#: 第一档)。名单随攻略数据修订走 research 重跑,复核流程 =
#: sr-od-currency-war-dev skill 的 references/version-update.md。
#: (原「贯穿件恒囤」纪律已随万金油义务买入面退役废止——统一让位
#: 优先级迭代 3.4 总纲 §2.7 申报②:万金油角色只有在恰为候选线/锁定线
#: 成员时按序 1 正常买入,手里持有的未到两星前受档 6 保护、无自动
#: 补货通道;本常量在役职责 = 档 6 数据源。)
CROSS_LINE_KEEP_NAMES: frozenset[str] = frozenset({
    '千冶·刃', '三月七', '花火', '星期日',
})


def refresh_transition_locked_systems(gs: GameState,
                                      state: StrategyState) -> None:
    """过渡锁定状态槽刷新(写入端单一源;幂等只增不减)。

    判定 = 「点亮(过渡锁定)」:复用现役支持度链
    ``_p1_system_support``(持有域 = bench ∪ deployed),达标门槛 =
    ``P1_PAIR_LOCK_MIN_SUPPORT``(支持度 1.0 = 体系满员,与配方对锁定
    门槛同一常数,禁另立阈值)。希儿系取支持度链字典的希儿系项——该
    项即 ``_seele_system_support`` 的输出(链内单一实现),其首行含希儿
    在场门:希儿缺席恒 0.0。**复用面不含 ``seele_system_formed``**(板面
    域,成型停手语义;持有域选定见统一保护集 design 篇双源差异申报,
    git 历史可溯)。

    - 幂等只增:已入槽体系不因支持度回落移除(锁定持久化取舍);每次
      全量现算「本帧达标集」并与旧槽并集;
    - 位面适用范围:plane2_started 翻真即整域关闭(早退不再入账)——
      清空由 flow 进 P2 分支(配方退场同点)负责,本函数只负责 P1 侧
      单调增长。
    """
    if session_scope.plane2_started_of(gs):
        return   # 过渡域已关闭(域切换;清空点在 flow)
    sup = _p1_system_support(gs)
    reached = frozenset(
        bond for bond, _t in TRANSITION_TRAITS
        if sup.get(bond, 0.0) >= P1_PAIR_LOCK_MIN_SUPPORT)
    if sup.get(SEELE_SYSTEM, 0.0) >= P1_PAIR_LOCK_MIN_SUPPORT:
        reached = reached | {SEELE_SYSTEM}
    if reached:
        state.transition_locked_systems = (
            state.transition_locked_systems | reached)
