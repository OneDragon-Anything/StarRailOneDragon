"""卡牌身份谓词(kernel;输入纯度面)。

「自己人」(持有保护)身份判定单一源 = 策略层
``mandate_v1/protection``(保护集,买卖两侧同源;域分派见其模块
docstring),本模块不承载任何持有名单;C1 单卡核心 =
``kernel.cw_comps.CORE_SINGLE_CARD_REGISTRY`` 直判。

本模块现役唯一职责 = :func:`is_engine_piece` 引擎件身份谓词
(注册表现算单一源;种子排除等消费方经本口取用)。

依赖方向:本模块只 import data/knowledge/kernel 注册表,不 import
strategies 面(kernel 输入纯度,同 cw_line_facts 声明)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_line_defs import (
    ENGINE_FACTIONS,
)


def is_engine_piece(name: str) -> bool:
    """引擎件身份(注册表现算单一源;种子排除,P78-7)。

    判据 = 角色注册表 factions∪flows 与引擎三阵营(ENGINE_FACTIONS,
    桥池 engine_bonds 派生)交集非空——与 ``cw_line_defs.classify_buy``
    的 ``'engine'`` 分支同判据;本函数 = 生产决策位可直调的单一源
    (禁第二实现)。种子身份 = 本谓词 ∧ 购买时未持有(第二合取需购买史语境,
    由 sell_gate 种子登记簿在获取时点承载)。

    import 边申报:cw_line_defs 头部迁移待办的「勿新增消费」明示对象
    = RECIPE_FACTIONS/RECIPE_BASE/recipe_tier 三符号(权威副本在
    knowledge/cw_line_facts);ENGINE_FACTIONS 无 knowledge 侧权威
    副本,本 import 是既有判定核的消费边非复制。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    ch = CHARACTERS.get(name or '')
    if ch is None:
        return False
    bonds = set(ch.factions) | set(ch.flows)
    return bool(bonds & set(ENGINE_FACTIONS))
