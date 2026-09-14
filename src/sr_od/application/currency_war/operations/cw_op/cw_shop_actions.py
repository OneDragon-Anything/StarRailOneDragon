"""商店工厂门面(unified-action-factory 批1 起转薄):词表→op 注册表
已迁 ``cw_action_registry.py``(单一工厂),本文件只保留
``shop_action_op_for`` 薄委托——消费面(cw_screen_buy_cards 调用点零
改动)与测试替身缝(函数内 lazy import 本文件)不变,零行为
(design.md §2.3)。op 类仍住各自 ``cw_<action>_action.py`` 文件,
通用基类 ``ActionOp`` 住 cw_action_base。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_vocab import Action
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
    action_op_for,
)


def shop_action_op_for(action: Action) -> ActionOp:
    """商店消费面口径(薄委托单一工厂):行为语义 = ``action_op_for``
    原样(注册表行序 isinstance 首中即返;词表外类型 AssertionError
    响亮暴露,决策 9 语义不变)。"""
    return action_op_for(action)
