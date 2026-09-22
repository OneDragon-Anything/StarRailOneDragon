"""祈愿试炼确认链动作 op(:class:`CwActionPickWishTrialOp` 单类文件,
一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点试炼卡身选中 → 「按钮-确认选择」area 确认;机械链发出后
直调自上报单口 ``report_action_pick_wish_trial_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_wish_trial_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickWishTrialParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickWishTrialOp(SrOperation):
    """祈愿试炼确认链(pick-op-unify 批收编)。

    点试炼卡身选中(防吞点击,选中点 = 建档卡位决策半现算)→ 选中
    动画固定等待 → 确认(「按钮-确认选择」area 位置点击,success_wait
    =1.5,现役形态逐位迁移;本屏独有检测在前,不与伙伴/巨星的
    「确认选择」撞)。``chosen_wish`` = 重入裁决出口写,留守画面 op。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickWishTrialParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickWishTrialOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_wish_trial', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡 → 选中动画等待 → area 确认;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        # 点卡选中(防吞点击:mouse_move 先,零移动落 click)。
        op.ctx.controller.mouse_move(env.target)
        op.ctx.controller.click(env.target)
        time.sleep(1.0)
        # 确认选择(祈愿试炼屏 area;原位形态:找到才点,success_wait 等
        # 关闭动画,零判效)。轮次结果经旁路回传(族形态)。
        env.round_result = op.round_by_find_and_click_area(
            op.screenshot(), '货币战争-祈愿试炼', '按钮-确认选择',
            success_wait=1.5)
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_wish_trial_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('祈愿试炼确认链已发')
