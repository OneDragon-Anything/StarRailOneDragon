"""卖上阵角色动作 op(CwActionSellDeployedOp)——动作 op 重组换壳
(原 ``SellDeployedOp``,ActionOp ABC → 框架 SrOperation;机械执行后
**op 内直调自己的上报函数** ``report_action_sell_deployed_param``,零分派,
op-layer.md §1.2 动作 op 契约)。非终结。"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.sell_deployed import (
    report_action_sell_deployed_param,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    DEPLOYED_CAPACITY,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionSellDeployedParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionSellDeployedOp(CwOperation):
    """卖上阵角色:drag 排槽中心 → 出售区(落点经 ``sell_point`` 单一源)。
    非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionSellDeployedParam,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionSellDeployedOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='sell_deployed', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """卖上阵角色:drag 排槽中心 → 出售区。

        emitted 语义 = 机械发出(拖拽原语零判效,落地事实归观察侧
        reconcile 对账)。执行坐标边:deployed_idx → (row,物理槽号)
        固定双射内联换算(0-3=前排 1-4 / 4-9=后排 1-6;随 tracked 账停用,换算五函数删除,动作坐标系算术就地承载;
        后排 7-9 扩展格超出动作坐标系不可寻址,3.1 在案)。
        """
        action: CwActionSellDeployedParam = self.param
        env = self.env
        ex = env.executor
        if not (0 <= action.deployed_idx < DEPLOYED_CAPACITY):
            # 参数违法由 op 自判(flow/action_ops.md §1 决策侧参数现算
            # 契约):deployed_idx = deployed 定长槽位表下标 0 基,越界 =
            # 决策逻辑 bug,守卫断言响亮暴露零拖拽。
            raise AssertionError(
                f'CwActionSellDeployedParam deployed_idx={action.deployed_idx} '
                f'越界(0-{DEPLOYED_CAPACITY - 1})')
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            DEPLOYED_FRONT_CAPACITY,
        )
        from sr_od.application.currency_war.prep_actions import sell_point
        row = 'front' if action.deployed_idx < DEPLOYED_FRONT_CAPACITY else 'back'
        slot_no = (action.deployed_idx + 1 if row == 'front'
                   else action.deployed_idx - DEPLOYED_FRONT_CAPACITY + 1)
        pts = ex._front_pts if row == 'front' else ex._back_pts
        src = pts[slot_no - 1]
        ex._drag(src, sell_point(ex._ctx))
        time.sleep(1.0)   # 用户口述口径 #21:卖出动画 1s
        # —— 自上报(机械发出后;op-layer.md §1.2):装备回收/退款单点 ——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_sell_deployed_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                session=getattr(getattr(self.ctx, 'cw_match', None),
                                'session', None))
        return self.round_success(f'卖{row}排{slot_no} ✓')
