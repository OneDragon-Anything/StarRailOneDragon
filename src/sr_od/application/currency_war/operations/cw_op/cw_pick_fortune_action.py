"""命运卜者强化三选一确认链动作 op(:class:`CwActionPickFortuneOp`
单类文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡选中 → 确认(裁决词「命运卜者」);机械链发出后直调
自上报单口 ``report_action_pick_fortune_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_fortune_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickFortuneParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    emit_overlay_confirm,
    safe_click,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_fortune import (
    CwScreenFortune,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickFortuneOp(SrOperation):
    """命运卜者强化三选一确认链(pick-op-unify 批收编)。

    点卡选中(safe_click bug#1 缓解;选中点 = 卡下半部避「详情」按钮区,
    决策半从 OCR 桶现算经 env 传入)→ 选中动画固定等待 → 确认
    (emit_overlay_confirm 机械交回,裁决词 = 标题「命运卜者」)。确认钮
    中心 = 建档「按钮-确认选择」现取,缺失兜底常量(巨星/策划同款派生
    模式)。本屏零 chosen 写端(选择存证已退役),容器写零。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickFortuneParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickFortuneOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_fortune', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡 → 选中动画等待 → 确认;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        safe_click(op, env.target, tag='cw-pick-fortune')
        time.sleep(1.2)
        # 确认钮主源 = 建档「按钮-确认选择」中心(坐标单一真相源);缺失
        # 回退兜底常量。
        _confirm = (area_center(op.ctx, '按钮-确认选择', CwScreenFortune.SCREEN_NAME)
                    or CwScreenFortune.CONFIRM)
        env.round_result = emit_overlay_confirm(
            op, confirm_point=_confirm,
            entry_keyword='命运卜者', tag='cw-pick-fortune')
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_fortune_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('命运卜者确认链已发(结果经旁路回传)')
