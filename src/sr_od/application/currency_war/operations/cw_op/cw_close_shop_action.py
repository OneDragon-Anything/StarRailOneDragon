"""关店动作 op(CwActionCloseShopOp)——动作 op 重组批③ 换壳
(ActionOp ABC → 框架 SrOperation;design.md §1.1/§1.2)。一 op 一文件。

终结跳写语义长在动作自己身上:体内不调上报(结构离屏写 = 关店编排壳
``CwOpCloseShop`` 的观察写端承接,design.md §1.1)。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_vocab import CwActionCloseShopParam
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionCloseShopOp(SrOperation):
    """关店 = 恒可用终结 op(决策 4/6):执行即本画面访问结束;关店点击
    由编排壳(CwOpCloseShop)承担——与旧「空序列触发关店」同一落点,
    动作 op 内为 no-op。体内不调上报(终结跳写)。"""

    #: 终结动作(执行即本画面访问结束,交回外循环)。
    terminal = True
    #: 终结交回等待秒数(无转移动画等待语义)。
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionCloseShopParam,
                 env: ShopExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionCloseShopOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='close_shop', is_start_node=True)
    def run(self) -> OperationRoundResult:
        return self.round_success('关店(编排壳承接点击;终结交回)')
