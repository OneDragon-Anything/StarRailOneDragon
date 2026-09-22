"""武装箱四选一选卡链动作 op(:class:`CwActionPickBoxCardOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡选中即确认(单步,无确认钮)+ overlay 动画固定等待;
机械链发出后直调自上报单口 ``report_action_pick_box_card_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_box_card_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickBoxCardParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickBoxCardOp(SrOperation):
    """武装箱四选一选卡链(pick-op-unify 批收编;点卡选中即确认,单步)。

    点卡(mouse_move+click 防吞点击;点击点 = 卡名带下方 y=290 避
    「查看详情」按钮,决策半现算经 env 传入)→ overlay 动画固定等待
    (``_OVERLAY_ANIM_WAIT_S``,与开箱终结交回等待同源)。选卡即终结 =
    画面 op 派发后 round_success 交回(落地归下一帧观察);本 op 零
    chosen 写端,容器写零。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickBoxCardParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickBoxCardOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_box_card', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡选中即确认 + 动画等待;轮次结果经旁路回传)。"""
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        action = self.param
        env = self.env
        op = env.op
        op.ctx.controller.mouse_move(env.target)
        op.ctx.controller.click(env.target)
        # 固定动画等待(来源写死 = 现役 overlay 动画等待常量)。
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_box_card_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('武装箱选卡点击已发(结果经旁路回传)')
