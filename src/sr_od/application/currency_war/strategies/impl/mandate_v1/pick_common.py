"""pick 族两画面共用判据(mandate_v1 共用模块)。

宪法六「共用判据显式抽离」(strategy-docs/00_framework.md §1 第 6 条):
投资环境屏(invest_env.py)与投资策略屏(invest_strategy.py)共用的用户
转向轴常数与自拆台判据在此单一源;画面文件 → 共用模块单向依赖,禁画面
文件互相 import。设计正本 = 28 号稿 §3(环境屏)与 29 号稿 §2.4/§3
(策略屏);共用语义文档单一源 = strategy-docs/13_pick_family.md §4
(共用判据节,本模块是其代码承载面)。

承载面:
- 转向轴:``STEERING_PRIORITY_BONUS``(user-priority 软偏好 +30,立场
  系数——「用户点名是偏好不是支配」;forbid 罚值不在此——策略屏 forbid
  改集合排除,分值化禁选退役,罚值禁搬进共用件);
- 自拆台:``BOARD_DOT_COUNT_THRESHOLD``(板面 持续伤害+减益 ≥ 2)+ 克制
  判定 :func:`counters_dot`(表源统一 = ``merged_mechanic_tables()``
  基表直通单一入口,消 env 直读基表/kernel 走入口函数的双路径)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_comps import merged_mechanic_tables

#: user-priority 软偏好分(固定偏好分,立场系数;两屏同值——软偏好,
#: 压不过 S 线方向分 100,「用户点名是偏好不是支配」)。
STEERING_PRIORITY_BONUS: float = 30.0

#: 自拆台板面阈值:上阵羁绊计数中 持续伤害+减益 ≥ 2(板面 = gs.board 现读,
#: 调用方单帧单读)。
BOARD_DOT_COUNT_THRESHOLD: int = 2

#: 本策略阵容的机械属性面(与 kernel ``MECHANIC_COUNTERS`` 值域对齐):
#: 板面以 DoT/减益为主派时,克制这些机制的候选 = 自拆台,排除。
#: 集合本身是策略侧立场(「我们在玩什么」);「某选项是否克制某机制」
#: 的事实判定 = kernel 表。
DOT_PUNISHED_MECHS: frozenset[str] = frozenset({'DoT', '减益'})


def counters_dot(opt: str) -> bool:
    """选项名是否克制 DoT/减益主派(事实判定;表源 = merged_mechanic_tables)。

    选项名 → ``AFFIX_MECHANIC_MAP`` 机制 tag → ``MECHANIC_COUNTERS`` 克制
    属性(子串包含匹配保留 OCR 容错语义;未知名不命中 = 不排除)。
    """
    affix_map, counters, _ = merged_mechanic_tables()
    for affix, tag in affix_map.items():
        if affix in opt and not DOT_PUNISHED_MECHS.isdisjoint(
                counters.get(tag, ())):
            return True
    return False
