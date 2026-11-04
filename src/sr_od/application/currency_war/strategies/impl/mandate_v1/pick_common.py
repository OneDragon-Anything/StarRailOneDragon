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
- 选卡克制减分(2026-11-03-unified-line-scoring 迭代:counters_dot
  硬排除退役 → 纯加权减分,design §3.2/§7):克制 top1 线主派的卡给
  选卡分 ``COUNTER_PICK_PENALTY``(克制档)。锚 = 选卡锚点线
  (``line_select.anchor_line_of``,P1/P2 同式);触发时序差异申报 =
  现行〔旧 counters_dot〕读板面 持续伤害+减益 计数 ≥2(成型后触发)
  → 新 = top1 线主派含受克属性即触发(P1 即触发,更早更广)——行为
  变更入 sim(design r4/Y4-5)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import merged_mechanic_tables
from sr_od.application.currency_war.kernel.cw_line_scales import (
    COUNTER_PICK_PENALTY,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp

#: user-priority 软偏好分(固定偏好分,立场系数;两屏同值——软偏好,
#: 「用户点名是偏好不是支配」)。
STEERING_PRIORITY_BONUS: float = 30.0

#: 主派羁绊名 → 机制属性名映射(MECHANIC_COUNTERS 值域对齐):批 1 只收
#: 直接同名对(持续伤害→DoT / 减益→减益 / 燃血→燃血);其余主派
#: (治疗→治疗护盾、战技点→战技点依赖 等)语义对应但命名不同,归批 2
#: 词缀面扩展时逐对核实登记,禁凭音近推定(design §3.2 边界:批 1 数据
#: = 投资面 + 万敌行)。
LINE_FACTION_TO_MECH: dict[str, str] = {
    '持续伤害': 'DoT',
    '减益': '减益',
    '燃血': '燃血',
}


def punished_mechs_of(comp: Comp | None) -> frozenset[str]:
    """选卡锚点线(anchor_line_of)的受克机制属性集(top1/锁定线主派 →
    MECHANIC_COUNTERS 值域投影;comp = None〔锚点线缺失帧〕→ 空集 =
    减分不触发,保守缺省)。

    读法 = 档 0 ∪ or_reqs 键(选卡受克判定的 3.1 中间态:键集与旧
    form_tiers 读法恒等 → 行为恒等;3.2 克制表直写时判定整体改写)。"""
    if comp is None:
        return frozenset()
    core_keys = set(comp.core_faction_reqs) \
        | {f for f, _t in (getattr(comp, 'or_reqs', None) or ())}
    return frozenset(
        mech for faction, mech in LINE_FACTION_TO_MECH.items()
        if faction in core_keys)


def counter_pick_penalty(opt: str, punished: frozenset[str]) -> int:
    """选项名对给定受克属性集的克制减分(−750 克制档;0 = 不克制)。

    事实判定沿旧 ``counters_dot`` 通道:选项名 → ``AFFIX_MECHANIC_MAP``
    机制 tag(子串包含匹配保留 OCR 容错语义)→ ``MECHANIC_COUNTERS``
    克制属性与受克集求交;未知名不命中 = 不减分。
    """
    affix_map, counters = merged_mechanic_tables()
    for affix, tag in affix_map.items():
        if affix in opt and not punished.isdisjoint(counters.get(tag, ())):
            return COUNTER_PICK_PENALTY
    return 0
