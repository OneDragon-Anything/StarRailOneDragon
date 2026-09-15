"""卖备战席角色动作 op(PrepSellBenchOp)——备战域动作文件(统一动作
工厂批3 体迁:体自 ``prep_actions.py::PrepActionExecutor._sell_bench``
逐字迁移,原方法改薄委托保持替身缝,design.md unified-action-factory
§2.4)。

命名申报:词表类 ``SellBench`` 的本域 op 不可与商店域
``cw_sell_bench_action.SellBenchOp`` 同名同包(批1 注册行更替为备战 op,
生产发射面策略收缩至备战期后备战域为唯一活执行路径),冠 ``Prep`` 前缀
区分域。非终结。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_vocab import SellBench
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class PrepSellBenchOp(ActionOp):
    """卖备战槽角色:drag 槽中心 → 出售区(``drag_bench_to_sell`` 单一源;
    机械执行,源槽像素验重试拆除)。非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """卖备战槽角色:drag 槽中心 → 出售区(``drag_bench_to_sell`` 单一源;
        机械执行,源槽像素验重试拆除)。

        emitted = 动作已机械发出(拖拽原语零判效,落地事实归观察侧
        reconcile 对账)。bench_idx = 容器槽位表下标,拖点直取(执行坐标
        边:备战栏-N area 序 = 下标序,零换算);detail 沿用物理槽号显示
        (= 下标+1,遥测行连续性)。
        """
        action: SellBench = self.action
        ex = env.executor
        from sr_od.application.currency_war.prep_actions import (
            drag_bench_to_sell,
        )
        drag_bench_to_sell(ex._op, ex._ctx, action.bench_idx)
        ex._track_remove_bench(action.bench_idx)
        # 用户口述口径(screen_flow_timing.md #21,2026-09-02):卖出金币
        # 动画很快,等 1s 足够——批尾观察前补这段,防读到金币动画帧。
        time.sleep(1.0)
        env.detail = f'卖备战槽{action.bench_idx + 1} ✓'
        env.emitted = True
        return True
