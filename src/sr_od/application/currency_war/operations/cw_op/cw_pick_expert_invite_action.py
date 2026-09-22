"""专家邀请函选卡链动作 op(:class:`CwActionPickExpertInviteOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点选(area 中心,idx=-1 = 现金为王语义由决策半解析为定位点)
+ 弹窗关闭动画固定等待,无确认钮;机械链发出后直调自上报单口
``report_action_pick_expert_invite_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_expert_invite_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickExpertInviteParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickExpertInviteOp(SrOperation):
    """专家邀请函选卡链(pick-op-unify 批收编;点卡即选,无确认钮)。

    点选(area 中心 = 建档「卡-N」/「卡-现金为王」现取,idx=-1 = 现金为王
    由决策半解析为定位点,area 缺失在决策半显式失败)→ 弹窗关闭动画
    固定等待。``chosen_expert``/ConfirmExpertCash 到账登记留守画面 op
    重入裁决出口(动作事实边界),本 op 容器写零。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickExpertInviteParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickExpertInviteOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_expert_invite', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点选 + 弹窗关闭动画等待;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        op.ctx.controller.mouse_move(env.target)
        op.ctx.controller.click(env.target)
        time.sleep(1.2)   # 选卡 → 弹窗关闭动画窗
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_expert_invite_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('邀请函选卡点击已发(结果经旁路回传)')
