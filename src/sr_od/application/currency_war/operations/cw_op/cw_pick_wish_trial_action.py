"""祈愿试炼确认链动作 op(:class:`CwActionPickWishTrialOp` 单类文件,
一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点试炼卡身选中 → 「按钮-确认选择」area 确认;机械链发出后
直调自上报单口 ``report_action_pick_wish_trial_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.geometry.point import Point
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

    点试炼卡身选中(防吞点击,选中点 = 动作 op 自容器
    ``wish_trial_opts_xy`` 按 ``param.idx`` 取——op-layer.md §1.1 :35,
    坐标单一真相源 = 观察上报;观察上报与名字域同门一并入容器,等长
    同进退)→ 选中动画固定等待 → 确认(「按钮-确认选择」area 位置点击,
    success_wait=1.5,现役形态逐位迁移;本屏独有检测在前,不与伙伴/
    巨星的「确认选择」撞)。``chosen_wish`` = 重入裁决出口写,留守画面 op。"""

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
        """机械执行(自容器取点 → 点卡选中 → 动画等待 → area 确认;轮次
        结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        # 点击点 = 观察上报容器(op-layer.md §1.1 :35 坐标单一真相源);
        # 禁回退 env.target、禁坐标现组装(均 = 第二坐标源)。缺席/越界 =
        # 守卫断言响亮暴露零点击(防 bug 路栏,非控制流;直构动作 op 的
        # 测试语境 = 显式注入坐标域,缺席即炸 = 防线非缺陷)。
        gs = game_state_from_ctx(self.ctx)
        pts = None if gs is None else gs.wish_trial_opts_xy.value
        if pts is None or not (0 <= self.param.idx < len(pts)):
            raise AssertionError(
                f'wish_trial_opts_xy 坐标域缺席/下标越界(观察上报欠供,'
                f'禁现算回退): idx={self.param.idx} pts={pts!r}')
        pt = Point(*pts[self.param.idx])
        # 点卡选中(防吞点击:mouse_move 先,零移动落 click)。
        op.ctx.controller.mouse_move(pt)
        op.ctx.controller.click(pt)
        time.sleep(1.0)
        # 确认选择(祈愿试炼屏 area;原位形态:找到才点,success_wait 等
        # 关闭动画,零判效)。轮次结果经旁路回传(族形态)。
        env.round_result = op.round_by_find_and_click_area(
            op.screenshot(), '货币战争-祈愿试炼', '按钮-确认选择',
            success_wait=1.5)
        # 自上报(机械链发出后;零写,契约面统一)。
        if gs is not None:
            report_action_pick_wish_trial_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('祈愿试炼确认链已发')
