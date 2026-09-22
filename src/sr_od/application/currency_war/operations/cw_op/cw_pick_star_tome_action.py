"""星徽秘典四选一选卡链动作 op(:class:`CwActionPickStarTomeOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡即选(safe_click bug#1 缓解)+ 选中动画固定等待,零确认
步;机械链发出后直调自上报单口
``report_action_pick_star_tome_param``。
"""
from __future__ import annotations

import time

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

    点卡(safe_click bug#1 缓解;选中点 = 建档「星徽卡-N」近邻匹配,决策半
    现算经 env 传入)→ 选中动画固定等待。``chosen_tome``/ConfirmTome 到账
    登记留守画面 op 重入裁决出口(动作事实边界),本 op 容器写零。"""

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
        safe_click(op, env.target, tag='cw-pick-tome')
        time.sleep(1.0)
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_star_tome_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('星徽秘典选卡点击已发(结果经旁路回传)')
