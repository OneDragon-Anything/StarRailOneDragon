"""sim 特殊规则建模助手(占位与特殊判据的 sim 侧宿主)。

现役成员与单一源关系:planner 触发判据 = kernel 值回调
(cw_faction_callbacks 星级回调,每费用档簿记 = ScreenChanges
sidecar);本模块仅存留与其判据解耦的 sim 侧特殊建模件。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import (
    is_trailblazer,
    trailblazer_form,
)

#: 银狼LV.999 注册表规范名(单一源 = ``data/cw_chars.py``;名字含
#: 「LV.999」后缀,与普通「银狼」4 费条目是两个角色)。

#: 三星五费特效披露键(M13 战力特征,第一期无消费面)。
THREE_STAR_FIVE_COST_PENDING: str = 'three_star_five_cost_effect_pending_u26'


# (planner 升星判据助手已随评估器退役删除:
#  判据单一源 = kernel/cw_faction_callbacks 的星级值回调[S3],
#  每费用档簿记 = ScreenChanges.planner_tiers_fired。)

def trailblazer_form_of(char_id: str, row: str) -> str:
    """开拓者按排形态名(kernel 单一源引用口;非开拓者原样返回)。

    ``row`` 坐标系 = 'front'|'back'(kernel 同名参数同域);部署腿的
    形态归一已在 kernel 转移函数内,本口仅供 sim 侧查询/测试对账。
    """
    if not is_trailblazer(char_id):
        return char_id
    return trailblazer_form(char_id, row)
