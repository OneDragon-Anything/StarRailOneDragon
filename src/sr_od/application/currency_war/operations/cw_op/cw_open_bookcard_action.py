"""开书册卡动作 op(OpenBookcardOp)——备战域动作文件(统一动作工厂批3
体迁:体自 ``prep_actions.py::PrepActionExecutor._open_bookcard`` 逐字
迁移,原方法改薄委托保持替身缝,design.md unified-action-factory §2.4;
机械半本体 = R10/批2c 自 ``cw_screen_expert_invite.open_card`` 迁入执行器
的形态,本批只迁形不改语义)。

非终结:点完开启本动作即交回——专家邀请函弹窗由外循环 0k 分发
``CwScreenExpertInvite`` 选卡(R7 OpenBox 终结化同构)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_vocab import OpenBookcard
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class OpenBookcardOp(ActionOp):
    """开书册卡:``find_bookcards`` 识别 → 点槽中心 → 固定动画等待
    (纯机械执行)。非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """开书册卡:``find_bookcards`` 识别 → 点槽中心 → 固定动画等待。

        点完开启本动作即交回——专家邀请函弹窗由外循环 0k 分发
        ``CwScreenExpertInvite`` 选卡(选卡决策不在本执行链,与 OpenBox
        终结化同构)。动画等待取家族常量 ``_OVERLAY_ANIM_WAIT_S``(原
        open_card 固定 1.5s,统一至开箱/典籍同族单一源,值只增不减 =
        弹窗弹出窗覆盖面不缩水);弹窗就位与否交下一帧观察。识别按
        ``action.slot`` 对位(slot=None = 首张,与 OpenBox/OpenTome 同形);
        书册卡识别含「青蓝卡+白色书册 icon+『开启』」模板语义,单一源 =
        ``find_bookcards``。
        """
        action: OpenBookcard = self.action
        ex = env.executor
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            _ctx_slots,
            find_bookcards,
        )
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        screen = ex._op.screenshot()
        cards = find_bookcards(screen, _ctx_slots(ex._ctx, '备战栏', 9))
        if not cards:
            env.detail, env.emitted = '无书册卡', False
            return True
        picked = cards[0]
        if action.slot is not None:
            matched = next((c for c in cards if c[0] == action.slot), None)
            if matched is None:
                env.detail, env.emitted = (
                    f'槽{action.slot} 无书册卡(实读 {cards})', False)
                return True
            picked = matched
        slot, center = picked
        ex._ctx.controller.mouse_move(center)   # bug#1 缓解(同开箱/点球口径)
        ex._ctx.controller.click(center)
        # 固定动画等待(A3 纪律:等待归产生动画的操作;判效交下一帧观察)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][bookcard] 开书册卡槽{slot} → 点开启已发'
                 '(交回外循环,专家邀请函分发选卡)')
        env.detail, env.emitted = f'开书册卡槽{slot}', True
        return True
