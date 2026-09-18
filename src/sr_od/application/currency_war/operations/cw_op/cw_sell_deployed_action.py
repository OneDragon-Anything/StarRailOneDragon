"""卖上阵角色动作 op(SellDeployedOp)——备战域动作文件(统一动作工厂
批3 体迁:体自 ``prep_actions.py::PrepActionExecutor._sell_deployed``
逐字迁移,原方法改薄委托保持替身缝,design.md unified-action-factory
§2.4)。非终结。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_exec_state import (
    deployed_row_slot,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionSellDeployedParam
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class SellDeployedOp(ActionOp):
    """卖上阵角色:drag 排槽中心 → 出售区(落点经 ``sell_point`` 单一源)。
    非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """卖上阵角色:drag 排槽中心 → 出售区(落点经 ``sell_point`` 单一源)。

        emitted 语义 = 同备战卖出(机械发出,拖拽原语零判效,落地事实归
        观察侧 reconcile 对账)。执行坐标边:deployed_idx → (row, 物理槽号)
        单一换算函数 = kernel ``deployed_row_slot``。
        """
        action: CwActionSellDeployedParam = self.action
        ex = env.executor
        from sr_od.application.currency_war.prep_actions import sell_point
        row, slot_no = deployed_row_slot(action.deployed_idx)
        pts = ex._front_pts if row == 'front' else ex._back_pts
        src = pts[slot_no - 1]
        ex._drag(src, sell_point(ex._ctx))
        ex._track_remove_deployed(row, slot_no)
        time.sleep(1.0)   # 同上 #21 口径:卖出动画 1s
        env.detail = f'卖{row}排{slot_no} ✓'
        env.emitted = True
        return True
