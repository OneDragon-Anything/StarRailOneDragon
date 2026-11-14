"""sim 特殊规则建模助手(占位与特殊判据的 sim 侧宿主)。

现役成员与单一源关系:planner 触发判据 = kernel 值回调
(cw_faction_callbacks 星级回调,每费用档簿记 = ScreenChanges
sidecar);本模块仅存留与其判据解耦的 sim 侧特殊建模件。
"""
from __future__ import annotations

#: 三星五费特效披露键(战力特征无档,第一期无消费面)。
THREE_STAR_FIVE_COST_PENDING: str = 'three_star_five_cost_effect_pending_u26'


# (planner 升星判据助手已停用删除:
#  判据单一源 = kernel/cw_faction_callbacks 的星级值回调,
#  每费用档簿记 = ScreenChanges.planner_tiers_fired。)
