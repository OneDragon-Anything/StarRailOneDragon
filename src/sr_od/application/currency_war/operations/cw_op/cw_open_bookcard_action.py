"""开书册卡动作 op(CwActionOpenBookcardOp)——动作 op 重组批③ 换壳(原
``OpenBookcardOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内
直调自己的上报函数** ``report_action_open_bookcard_param``,零分派,
design.md §1.1/§1.2;机械半本体 = R10/批2c 自 ``cw_screen_expert_invite.
open_card`` 迁入执行器的形态)。非终结:点完开启本动作即交回——专家邀请
函弹窗由外循环 0k 分发 ``CwScreenExpertInvite`` 选卡。"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.open_bookcard import (
    report_action_open_bookcard_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenBookcardParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenBookcardOp(SrOperation):
    """开书册卡:``find_bookcards`` 识别 → 点槽中心 → 固定动画等待
    (纯机械执行)。非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionOpenBookcardParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionOpenBookcardOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_bookcard', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """开书册卡:``find_bookcards`` 识别 → 点槽中心 → 固定动画等待。

        点完开启本动作即交回——专家邀请函弹窗由外循环 0k 分发
        ``CwScreenExpertInvite`` 选卡(选卡决策不在本执行链)。动画等待取
        家族常量 ``_OVERLAY_ANIM_WAIT_S``;弹窗就位与否交下一帧观察。识别
        按 ``action.slot`` 对位(slot=None = 首张);书册卡识别含
        「青蓝卡+白色书册 icon+『开启』」模板语义,单一源 = ``find_bookcards``。
        """
        action: CwActionOpenBookcardParam = self.param
        env = self.env
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
            return self.round_fail('无书册卡')
        picked = cards[0]
        if action.slot is not None:
            matched = next((c for c in cards if c[0] == action.slot), None)
            if matched is None:
                return self.round_fail(
                    f'槽{action.slot} 无书册卡(实读 {cards})')
            picked = matched
        slot, center = picked
        ex._ctx.controller.mouse_move(center)   # bug#1 缓解(同开箱/采晶矿口径)
        ex._ctx.controller.click(center)
        # 固定动画等待(A3 纪律:等待归产生动画的操作;判效交下一帧观察)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][bookcard] 开书册卡槽{slot} → 点开启已发'
                 '(交回外循环,专家邀请函分发选卡)')
        # —— 自上报(机械发出后;design.md §1.1):开卡腾席 ——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_open_bookcard_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success(f'开书册卡槽{slot}')
