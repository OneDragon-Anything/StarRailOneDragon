"""主角光环团队规模代价事实(知识层;注册表效果原文派生)。

游戏机制:团队规模上限(「X/Y」的 Y)约束的是**各单位占用之和**,非常规认知的
「单位数」——主角光环可让持有者多占(官方原文「上阵该角色占用2团队规模」,
持有者在上场时 X = 单位数 + 1)。板满后再选此类光环即进入超限态(红色计数
X > Y,出战被游戏静默拒绝)。消费点 = 上阵规模占用派生
(``cw_game_state.team_size_used_of``)与备战识别器 extras 说明。

两层结构(data-collection.md §五 建模增量层 / §四 派生层):base 事实层 =
``data/cw_spot_lights.py``(plaza 官方镜像,生成器产物勿手编);本模块 = 规模
代价的**派生层**——自效果原文 import 期派生(先例 = ``cw_synthesis`` 自装备
注册表 recipes 派生),零手抄,注册表重跑 / 原文改写自动传导。派生失配(官方
改写措辞导致漏派生)由测试仓对账锁暴露(全注册表代价 ≠ 1 的光环集)。

依赖方向:仅 import 数据注册表,不 import 任何决策符号。
"""
from __future__ import annotations

import re

from sr_od.application.currency_war.data.cw_spot_lights import SPOT_LIGHTS

#: 每个单位的基础团队规模占用(无光环加成时的缺省;也是未知名 / None 的缺省——
#: 代价缺省永远落在「不额外占用」侧,不虚构超限)。
DEFAULT_TEAM_SIZE_PER_UNIT: int = 1

#: 效果原文 → 规模代价(官方措辞「占用N团队规模」;括号捕获 N)。
_TEAM_SIZE_RE = re.compile(r'占用(\d+)团队规模')


def _derive() -> dict[str, int]:
    """注册表效果原文 → {光环标准名: 占用规模}(仅收原文明说代价的光环)。"""
    table: dict[str, int] = {}
    for x in SPOT_LIGHTS:
        m = _TEAM_SIZE_RE.search(x.desc)
        if m is not None:
            table[x.name] = int(m.group(1))
    return table


#: 主角光环 → 团队规模占用数(import 期派生;不在表内的光环 = 缺省 1)。
AURA_TEAM_SIZE_COST: dict[str, int] = _derive()


def aura_team_size_cost(aura_name: str | None) -> int:
    """主角光环持有者上场时的团队规模占用数(无光环 / 未知名 → 缺省 1)。

    调用方只需回答「持有者是否在上场」——不在场(备战席 / 闭关离场)时该
    光环不产生额外占用,调用方按缺省计。
    """
    if aura_name is None:
        return DEFAULT_TEAM_SIZE_PER_UNIT
    return AURA_TEAM_SIZE_COST.get(aura_name, DEFAULT_TEAM_SIZE_PER_UNIT)
