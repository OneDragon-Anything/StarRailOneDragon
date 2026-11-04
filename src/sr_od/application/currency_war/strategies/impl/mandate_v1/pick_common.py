"""pick 族两画面共用判据(mandate_v1 共用模块)。

宪法六「共用判据显式抽离」(strategy-docs/00_framework.md §1 第 6 条):
投资环境屏(invest_env.py)与投资策略屏(invest_strategy.py)共用的用户
转向轴常数与选卡克制减分判据在此单一源;画面文件 → 共用模块单向依赖,
禁画面文件互相 import。设计正本 = 28 号稿 §3(环境屏)与 29 号稿
§2.4/§3(策略屏);共用语义文档单一源 = strategy-docs/13_pick_family.md §4
(共用判据节,本模块是其代码承载面)。

承载面:
- 转向轴:``STEERING_PRIORITY_BONUS``(user-priority 软偏好,立场
  系数——「用户点名是偏好不是支配」;forbid 罚值不在此——策略屏 forbid
  改集合排除,分值化禁选停用,罚值禁搬进共用件);
- 选卡克制减分:选项名含 ``AFFIX_COUNTERS_FACTIONS`` 词缀关键词 ∧
  该词缀克制名单与选卡锚点线(``line_select.anchor_line_of``,P1/P2
  同式)档 0 羁绊键集有交集 → 选卡分 ``COUNTER_PICK_PENALTY``(克制档,
  纯加权非排除;无方向线帧不触发,保守缺省)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_line_scales import (
    COUNTER_PICK_PENALTY,
)

#: user-priority 软偏好分(固定偏好分,立场系数;两屏同值——软偏好,
#: 「用户点名是偏好不是支配」)。
STEERING_PRIORITY_BONUS: float = 30.0

#: 词缀 → 它克制的羁绊名(直写,无中间层;活链路 2 条的如实迁移)
AFFIX_COUNTERS_FACTIONS: dict[str, list[str]] = {
    '净化身心': ['持续伤害', '减益'],   # 克 DOT队/专家桑博DOT/黄泉减益/千冶减益
    '永久创伤': ['燃血'],              # 克 万敌单C
}


def counter_pick_penalty(opt: str, core_factions: frozenset[str]) -> int:
    """选项名含词缀关键词 ∧ 该词缀克制名单与阵容档 0 羁绊键有交集 → -750。

    core_factions = core_faction_reqs 键集(契约 A;候选首位线/锁定线现读,
    无方向线帧传空集 = 减分不触发,保守缺省同现行)。
    """
    for affix, countered in AFFIX_COUNTERS_FACTIONS.items():
        if affix in opt and not core_factions.isdisjoint(countered):
            return COUNTER_PICK_PENALTY
    return 0
