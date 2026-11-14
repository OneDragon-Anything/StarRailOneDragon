"""v4.7 换赛季注册表收缩·构建期哨放行集(中间态兼容层)。

v4.7 role_list 收缩(相对 V4.4 名单)移出 23 名角色与一批旧羁绊键,而发放
登记表/过渡阵容库/顾问表仍以 V4.4 名单为底——整层 v4.7 迁移与掉出残余
清偿归后继羁绊消费点迁移批(挂账板 ``.debug/progress/CW跨迭代挂账.md``
「v4.7 换赛季适配欠账族」:单删登记会与旧羁绊/阵容层互锁,中间态共存是
既定拓扑)。本模块只承载**构建期校验**(import 即炸面)的「已确认漂移」
放行集:

- ``V47_DROPPED_CHARS``:已确认掉出角色名——漂移已被注册表收缩确认,
  非新漂移,哨放行;一次确认的字面清单(旧名单已随注册表重写删除,无
  运行时推导源),迁移批清偿登记残余时整集删除;
- ``GUARD_ALL_UNIT_NAMES`` / ``GUARD_CHARACTER_ROSTER``:闭集闸词表 =
  现役 roster ∪ 掉出名——闸对集合外新名照常炸,保护力不变;
- ``v47_dropped_bonds()``:FACTIONS 中不再被现役注册表角色自报的旧羁绊键,
  派生式(FACTIONS 迁 v4.7 名单后自动清空),供随机赠卡池空哨放行。

消费纪律:只许构建期校验消费本模块;运行期闭集闸(assert_expert_names
等)不消费——运行期语义按注册表存留表(registry 详设 2.5)裁定不变。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import (
    ALL_UNIT_NAMES,
    CHARACTER_ROSTER,
    CHARACTERS,
)
from sr_od.application.currency_war.data.cw_factions import FACTIONS

#: v4.7 换赛季已确认掉出角色名(= V4.4 名单 − v4.7 role_list 差集,
#: 一次确认的字面清单;含系统单位迁出无关的纯角色 23 名)。
V47_DROPPED_CHARS: frozenset[str] = frozenset({
    'Archer', 'Saber', '佩拉', '停云', '加拉赫', '吉尔伽美什', '姬子',
    '布洛妮娅', '希儿', '开拓者·欢愉', '开拓者·记忆', '彦卿', '杰帕德',
    '桑博', '真理医生', '艾丝妲', '貊泽', '远坂凛', '银枝', '银狼',
    '阮·梅', '青雀', '黑塔',
})

#: 发放角色/反扫词表闸词表(系统单位 capable + 已确认掉出名放行)。
GUARD_ALL_UNIT_NAMES: frozenset[str] = ALL_UNIT_NAMES | V47_DROPPED_CHARS

#: 纯角色语义闸词表(判据角色/参与名等 + 已确认掉出名放行)。
GUARD_CHARACTER_ROSTER: frozenset[str] = CHARACTER_ROSTER | V47_DROPPED_CHARS


def v47_dropped_bonds() -> frozenset[str]:
    """FACTIONS 中不再被现役注册表角色自报的旧羁绊键(阵营∪流派全集口径)。

    派生式:键 ∈ FACTIONS 且无任何现役角色自报 → 掉出羁绊;FACTIONS
    迁 v4.7 名单后恒空集。仅构建期哨消费。"""
    live = {b for c in CHARACTERS for b in (*c.factions, *c.schools)}
    return frozenset(f for f in FACTIONS if f not in live)
