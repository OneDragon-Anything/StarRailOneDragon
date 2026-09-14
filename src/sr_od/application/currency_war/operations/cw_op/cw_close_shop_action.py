"""关店动作 op(CloseShopOp)——动作文件一 op 一文件拆分自
cw_shop_actions.py(该文件转聚合注册,本文件只放本动作)。
"""
from __future__ import annotations

from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)


class CloseShopOp(ActionOp):
    """关店 = 恒可用终结 op(决策 4/6):执行即本画面访问结束;关店点击
    由编排壳(CwOpCloseShop)承担——与旧「空序列触发关店」同一落点,
    动作 op 内为 no-op。"""

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
        return True
