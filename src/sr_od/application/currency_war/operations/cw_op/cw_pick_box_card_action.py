"""武装箱四选一选卡链动作 op(:class:`CwActionPickBoxCardOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡选中即确认(单步,无确认钮)+ overlay 动画固定等待;
机械链发出后直调自上报单口 ``report_action_pick_box_card_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.geometry.point import Point
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

    点卡(mouse_move+click;点击点 = 容器 ``box_card_names_xy[idx]``——
    观察期按避让几何(卡名带下方 y,避「查看详情」按钮)解出上报,
    op-layer.md §1.1 :35,动作 op 自取,缺席/越界 = 守卫断言)→ overlay
    动画固定等待(``_OVERLAY_ANIM_WAIT_S``,与开箱终结交回等待同源)。
    选卡即终结 = 画面 op 派发后 round_success 交回(落地归下一帧观察);
    本 op 零 chosen 写端,容器写零。"""

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
        # 点击点 = 观察上报容器(op-layer.md §1.1 :35 坐标单一真相源);
        # 禁回退 env.target、禁坐标现组装(均 = 第二坐标源)。缺席/越界 =
        # 守卫断言响亮暴露零点击(防 bug 路栏,非控制流;直构动作 op 的
        # 测试语境 = 显式注入坐标域,缺席即炸 = 防线非缺陷)。
        gs = game_state_from_ctx(self.ctx)
        pts = None if gs is None else gs.box_card_names_xy.value
        if pts is None or not (0 <= self.param.idx < len(pts)):
            raise AssertionError(
                f'box_card_names_xy 坐标域缺席/下标越界(观察上报欠供,'
                f'禁现算回退): idx={self.param.idx} pts={pts!r}')
        pt = Point(*pts[self.param.idx])
        op.ctx.controller.mouse_move(pt)
        op.ctx.controller.click(pt)
        # 固定动画等待(来源写死 = 现役 overlay 动画等待常量)。
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        # 自上报(机械链发出后;零写,契约面统一)。
        if gs is not None:
            report_action_pick_box_card_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('武装箱选卡点击已发(结果经旁路回传)')
