"""全动作单一注册表(统一动作工厂批1;design.md §2.3):词表类 → 动作
op 类一张表,``action_op_for`` = 全动作唯一注册点(单一工厂)。

**收编计划(防「表已单一」误读)**:本表批1 仅商店域五行首批在册——
备战域 op 类批3 收编(design.md §2.4)、事件线 pick 族批4 收编(§2.5)
后,表内行集 = 统一词表全集;注册完备锁(批4)自此以本表为机械约束
对象。(原 CompTransaction 行已随 unified-action-factory 批2b R3 删除
——整档替换宏动作全链退役。)

**注册行顺序敏感**:``action_op_for`` 按行序 isinstance 首中即返——
is-a 链的父类行必须在子类可独立匹配处之前兜底(子类共享父 op 时父行
即足;子类需独立 op 时其行必须插在父行之前)。现役先例 =
``LevelUpShop`` is-a ``LevelUp`` 同 op(单击,无子类独立行)。分区注释
按「族 → 基类兜底行 → 具体类行」摆放(现役仅商店一族,分区随收编扩展)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_vocab import (
    Action,
    BuyCard,
    CloseShop,
    LevelUp,
    RefreshShop,
    SellBench,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_buy_card_action import (
    BuyCardOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_close_shop_action import (
    CloseShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_level_up_action import (
    LevelUpOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_refresh_shop_action import (
    RefreshShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_sell_bench_action import (
    SellBenchOp,
)

# 商店族(批1 首批在册;行序敏感,见模块头「注册行顺序敏感」节)
_REGISTRY: dict[type, type[ActionOp]] = {
    BuyCard: BuyCardOp,
    LevelUp: LevelUpOp,       # LevelUpShop is-a LevelUp,同 op(单击)
    RefreshShop: RefreshShopOp,
    SellBench: SellBenchOp,
    CloseShop: CloseShopOp,
}


def action_op_for(action: Action) -> ActionOp:
    """动作词表 → 动作 op(全动作唯一注册点;按行序 isinstance 首中即
    返)。词表外类型 AssertionError 响亮暴露(沿用 ADR-0517 决策 9 语义:
    非法返回 = 策略器 bug,禁静默跳过;文案中性,注册表现跨域共用)。"""
    for cls, op_cls in _REGISTRY.items():
        if isinstance(action, cls):
            return op_cls(action)
    raise AssertionError(
        f'[cw-action][registry] 动作词表外类型:{type(action).__name__}'
        '(ADR-0517 决策 9:非法返回 = 策略器 bug,禁静默跳过)')
