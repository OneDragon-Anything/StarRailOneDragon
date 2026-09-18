"""卖上阵角色动作 op(CwActionSellDeployedOp)——动作 op 重组批③ 换壳
(原 ``SellDeployedOp``,ActionOp ABC → 框架 SrOperation;机械执行后
**op 内直调自己的上报函数** ``report_action_sell_deployed_param``,零分派,
design.md §1.1/§1.2)。非终结。"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.sell_deployed import (
    report_action_sell_deployed_param,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    deployed_row_slot,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionSellDeployedParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionSellDeployedOp(SrOperation):
    """卖上阵角色:drag 排槽中心 → 出售区(落点经 ``sell_point`` 单一源)。
    非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionSellDeployedParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionSellDeployedOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='sell_deployed', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """卖上阵角色:drag 排槽中心 → 出售区。

        emitted 语义 = 机械发出(拖拽原语零判效,落地事实归观察侧
        reconcile 对账)。执行坐标边:deployed_idx → (row, 物理槽号)
        单一换算函数 = kernel ``deployed_row_slot``。
        """
        action: CwActionSellDeployedParam = self.param
        env = self.env
        ex = env.executor
        from sr_od.application.currency_war.prep_actions import sell_point
        row, slot_no = deployed_row_slot(action.deployed_idx)
        pts = ex._front_pts if row == 'front' else ex._back_pts
        src = pts[slot_no - 1]
        ex._drag(src, sell_point(ex._ctx))
        ex._track_remove_deployed(row, slot_no)
        time.sleep(1.0)   # 用户口述口径 #21:卖出动画 1s
        # —— 自上报(机械发出后;design.md §1.1):装备回收/退款单点 ——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_sell_deployed_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                session=getattr(getattr(self.ctx, 'cw_match', None),
                                'session', None))
        return self.round_success(f'卖{row}排{slot_no} ✓')
