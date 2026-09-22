"""专家邀请函选卡链动作 op(:class:`CwActionPickExpertInviteOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点选(点击点 = 容器 ``expert_invite.card_points[idx]`` ∨
``cash_point``(idx=-1;词表特形显式分支),op-layer.md §1.1 :35 坐标
单一真相源 = 观察上报)+ 弹窗关闭动画固定等待,无确认钮;机械链发出后
直调自上报单口 ``report_action_pick_expert_invite_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.geometry.point import Point
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

    点选(点击点 = 容器 ``expert_invite.card_points[idx]`` ∨ ``cash_point``
    (idx=-1;观察上报写入,op-layer.md §1.1 :35),动作 op 按下标自取,
    缺席/越界 = 守卫断言)→ 弹窗关闭动画固定等待。``chosen_expert``/
    ConfirmExpertCash 到账登记留守画面 op 重入裁决出口(动作事实边界),
    本 op 容器写零。"""

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
        # 点击点 = 观察上报容器(op-layer.md §1.1 :35 坐标单一真相源);
        # 禁回退 env.target、禁 area_center 二次现取(均 = 第二坐标源)。
        # 缺席/越界 = 守卫断言 AssertionError 响亮暴露零点击(防 bug 路栏,
        # 非控制流;直构动作 op 的测试语境 = 显式注入坐标域,缺席即炸 =
        # 防线非缺陷)。
        gs = game_state_from_ctx(self.ctx)
        payload = None if gs is None else gs.expert_invite.value
        if payload is None:
            raise AssertionError(
                'expert_invite 坐标域缺席(观察上报欠供,禁现算回退)')
        # idx=-1 = 词表特形(现金为王):显式分支 = 词表语义消费,非值域改写。
        if action.idx == -1:
            if payload.cash_point is None:
                raise AssertionError(
                    'cash_point 缺席(观察上报欠供,禁现算回退)')
            pt = Point(*payload.cash_point)
        else:
            if payload.card_points is None or len(payload.card_points) != 4 \
                    or not (0 <= action.idx < len(payload.card_points)):
                raise AssertionError(
                    f'card_points 缺席/下标越界(观察上报欠供,禁现算回退): '
                    f'idx={action.idx} pts={payload.card_points!r}')
            pt = Point(*payload.card_points[action.idx])
        op.ctx.controller.mouse_move(pt)
        op.ctx.controller.click(pt)
        time.sleep(1.2)   # 选卡 → 弹窗关闭动画窗
        # 自上报(机械链发出后;零写,契约面统一)。
        if gs is not None:
            report_action_pick_expert_invite_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('邀请函选卡点击已发(结果经旁路回传)')
