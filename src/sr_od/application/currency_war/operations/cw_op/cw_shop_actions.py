"""聚合注册文件,非 op 文件(T-201 一 op 一文件拆分):商店单动作 op
族已拆至各自 ``cw_<action>_action.py``,本文件只做词表→op 工厂注册与
聚合导出(消费面 import 口径不变:工厂与 op 类从本文件取,基类从
cw_action_base 取)。新增动作 = 建 op 文件 + 在 _OP_TABLE 注册一行。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_vocab import (
    Action,
    BuyCard,
    CloseShop,
    CompTransaction,
    LevelUp,
    RefreshShop,
    SellBench,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ShopActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_buy_card_action import (
    BuyCardOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_close_shop_action import (
    CloseShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_comp_transaction_action import (
    CompTransactionOp,
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

_OP_TABLE = {
    BuyCard: BuyCardOp,
    LevelUp: LevelUpOp,       # LevelUpShop is-a LevelUp,同 op(单击)
    RefreshShop: RefreshShopOp,
    SellBench: SellBenchOp,
    CloseShop: CloseShopOp,
    CompTransaction: CompTransactionOp,
}


def shop_action_op_for(action: Action) -> ShopActionOp:
    """动作词表 → 动作 op(词表外类型 = 策略器 bug 响亮暴露,决策 9)。"""
    for cls, op_cls in _OP_TABLE.items():
        if isinstance(action, cls):
            return op_cls(action)
    raise AssertionError(
        f'[cw-shop][guard] 商店动作词表外类型:{type(action).__name__}'
        '(ADR-0517 决策 9:非法返回 = 策略器 bug,禁静默跳过)')
