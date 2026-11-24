"""v4.7 换赛季注册表收缩·构建期哨放行集(中间态兼容层)。

v4.7 role_list 收缩(相对 V4.4 名单)移出 23 名角色,而发放登记表/
过渡阵容库/顾问表仍以 V4.4 名单为底——整层 v4.7 迁移与掉出残余清偿
归策略批(待跟进事项 ``.temp/tracking/currency-war/待跟进事项.md``「v4.7 换赛季
适配欠账族」)。本模块只承载**构建期校验**(import 即炸面)的「已确认
漂移」放行集:

- ``V47_DROPPED_CHARS``:已确认掉出角色名——漂移已被注册表收缩确认,
  非新漂移,哨放行;一次确认的字面清单(旧名单已随注册表重写删除,无
  运行时推导源),策略批清偿登记残余时整集删除;
- ``GUARD_ALL_UNIT_NAMES`` / ``GUARD_CHARACTER_ROSTER``:闭集闸词表 =
  现役 roster ∪ 掉出名——闸对集合外新名照常炸,保护力不变。

羁绊轴(v47_dropped_bonds)已随羁绊消费点迁移批清偿退役:随机赠卡
等登记表中依赖放行的消失档羁绊条目(概念股/契约)已删,FACTIONS 旧键
派生不再有消费面,函数与放行分支一并移除——考古走 git 历史。

消费纪律:只许构建期校验消费本模块;运行期闭集闸(assert_expert_names
等)不消费——运行期语义按注册表存留表(registry 详设 2.5)裁定不变。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import (
    ALL_UNIT_NAMES,
    CHARACTER_ROSTER,
)

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

# (v47_dropped_bonds 已退役:FACTIONS 旧键 − 现役自报的派生式随
#  cw_factions 退役路径消亡;消费点〔cw_investments 随机赠卡/晶矿
#  契约两哨的放行分支〕已随登记残余清偿删除。迁移时实测核对:派生值
#  23 项 = 22 消失档羁绊 + 巡海游侠(沿用名但 v4.7 类别迁移为独立羁绊、
#  现役注册表无角色自报),与映射表消失档一致——独立 7 族单卡羁绊与
#  巡海游侠特例的语义说明见迁移处置记录。)
