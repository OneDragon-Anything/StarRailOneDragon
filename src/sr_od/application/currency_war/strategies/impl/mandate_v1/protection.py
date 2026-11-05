"""万金油贯穿件名单(mandate_v1 策略实现层)。

本模块原保留两件数据源/写入端,现役一件(原「统一保护集」判据件
:func:`protection_membership` 及四体系全体成员集已退役——静态不许卖
名单与买面囤货判据随之拆除,「谁不该卖/谁该买」改由统一让位序列
(criteria/priority.sell_order)与序 1 义务面承载;退役考古走 git 历史):

- :data:`CROSS_LINE_KEEP_NAMES`(万金油四角色名单)——统一价值序
  档 8(全线留用层)的判定数据源(消费 = criteria/priority.py;
  名单随攻略数据修订走 research 重跑);
- ~~:func:`refresh_transition_locked_systems`(过渡锁定状态槽写端)~~
  ——已随 comp-structure-unification 3.3 合并裁定删除:过渡锁定态
  单一承载 = ``v3_intention.transition_locked``(写端 = kernel 过渡
  候选机器 ``update_transition_candidates``,候选内成型即锁;清空点
  = 终局锁定写入 session_scope.write_line_lock),不并存两套锁定态。

依赖方向:本模块属策略实现层,可依 kernel/knowledge/同包 session
作用域;禁反向 import 消费方。
"""
from __future__ import annotations

#: 万金油四角色名单(统一价值序档 8「全线留用层」判定数据源;
#: 「真贯穿层」= Early→Final 全程留用层——E→F 0.66-0.95 与「早期核心」
#: 一致,出处 = docs/game/currency_war/research/stage_transitions.md Q1 表
#: 第一档)。名单随攻略数据修订走 research 重跑,复核流程 =
#: sr-od-dev-currency-war skill 的 references/version-update.md。
#: (万金油角色无自动补货通道——只在恰为候选线/锁定线成员时按序 1
#: 义务面买入;手里持有的未到两星前受档 8 保护、不轻易卖。本常量
#: 在役职责 = 档 8 数据源。)
CROSS_LINE_KEEP_NAMES: frozenset[str] = frozenset({
    '千冶·刃', '三月七', '花火', '星期日',
})
