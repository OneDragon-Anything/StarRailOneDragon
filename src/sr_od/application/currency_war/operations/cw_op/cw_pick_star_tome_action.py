"""星徽秘典四选一选卡链动作 op(:class:`CwActionPickStarTomeOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡即选(safe_click 防吞点击)+ 选中动画固定等待,零确认
步;机械链发出后直调自上报单口
``report_action_pick_star_tome_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_star_tome_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickStarTomeParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickStarTomeOp(SrOperation):
    """星徽秘典四选一选卡链(pick-op-unify 批收编;点卡即选,弹窗自关)。

    点卡(safe_click 防吞点击;点击点 = 容器 ``star_tome_opts_xy[idx]``——
    观察期解出上报,op-layer.md §1.1 :35 坐标单一真相源 = 观察上报,
    动作 op 自取,缺席/越界 = 守卫断言)→ 选中动画固定等待。
    ``chosen_tome``/ConfirmTome 到账登记留守画面 op 重入裁决出口(动作
    事实边界),本 op 容器写零。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickStarTomeParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickStarTomeOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_star_tome', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡即选 + 固定等待;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        # 点击点 = 观察上报容器(op-layer.md §1.1 :35 坐标单一真相源);
        # 禁回退 env.target、禁坐标现组装(均 = 第二坐标源)。缺席/越界 =
        # 守卫断言响亮暴露零点击(防 bug 路栏,非控制流;直构动作 op 的
        # 测试语境 = 显式注入坐标域,缺席即炸 = 防线非缺陷)。
        gs = game_state_from_ctx(self.ctx)
        pts = None if gs is None else gs.star_tome_opts_xy.value
        if pts is None or not (0 <= action.idx < len(pts)):
            raise AssertionError(
                f'star_tome_opts_xy 坐标域缺席/下标越界(观察上报欠供,'
                f'禁现算回退): idx={action.idx} pts={pts!r}')
        safe_click(op, Point(*pts[action.idx]), tag='cw-pick-tome')
        time.sleep(1.0)
        # 自上报(机械链发出后;零写,契约面统一)。
        if gs is not None:
            report_action_pick_star_tome_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('星徽秘典选卡点击已发(结果经旁路回传)')
