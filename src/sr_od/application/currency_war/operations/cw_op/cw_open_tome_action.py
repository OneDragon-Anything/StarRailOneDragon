"""开秘密典籍动作 op(OpenTomeOp)——备战域动作文件(统一动作工厂批3
体迁:体自 ``prep_actions.py::PrepActionExecutor._open_tome`` 逐字迁移,
原方法改薄委托保持替身缝,design.md unified-action-factory §2.4)。

非终结:点两次开典籍后星徽四选一 overlay 弹出,选卡交外循环 0i 接管
(overlay 检出走环中止交外环 handler,非本动作终结语义)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_vocab import OpenTome
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class OpenTomeOp(ActionOp):
    """开秘密典籍:点槽两次(选中→开启)→ 固定动画等待。非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """点两次间隔 ~1s(第一次选中边框高亮,第二次弹窗);弹窗后 loop 0i
        接管选卡(本动作不选 —— 选卡是策略决策,板上阵营匹配在 0i handler)。
        A3 拆除:「轮询验星徽四选一弹出」判效半删除,改固定等待;弹窗就位
        与否交下一帧观察(0i 分发重判)。
        """
        action: OpenTome = self.action
        ex = env.executor
        from sr_od.application.currency_war.obs.cw_identity_obs import read_tomes
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        screen = ex._op.screenshot()
        tomes = read_tomes(ex._ctx, screen)
        if not tomes:
            env.detail, env.emitted = '无秘密典籍', False
            return True
        picked = tomes[0]
        if action.slot is not None:
            matched = next((t for t in tomes if t[0] == action.slot), None)
            if matched is None:
                env.detail, env.emitted = (
                    f'槽{action.slot} 无典籍(实读 {tomes})', False)
                return True
            picked = matched
        slot, center = picked
        ex._ctx.controller.mouse_move(center)   # bug#1 缓解
        ex._ctx.controller.click(center)        # 第一次:选中
        time.sleep(1.0)
        ex._ctx.controller.click(center)        # 第二次:开启
        # 固定动画等待(原轮询判效半拆除,A3)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][tome] 开典籍槽{slot} → 点两次已发(选卡交 loop 0i)')
        env.detail, env.emitted = f'开典籍槽{slot}', True
        return True
