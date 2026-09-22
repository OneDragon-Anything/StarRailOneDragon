"""命运卜者强化三选一确认链动作 op(:class:`CwActionPickFortuneOp`
单类文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡选中 → 确认(建档「按钮-确认选择」查找点击,确认钮查找
全族统一 = ``round_by_find_and_click_area``);机械链发出后直调
自上报单口 ``report_action_pick_fortune_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_fortune_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickFortuneParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    safe_click,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_fortune import (
    CwScreenFortune,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickFortuneOp(SrOperation):
    """命运卜者强化三选一确认链(pick-op-unify 批收编)。

    点卡选中(safe_click 防吞点击;点卡坐标 = 按下标自容器
    ``fortune_opts_xy`` 读〔坐标随报条款,缺/越界 = 守卫断言;选中几何
    避「详情」按钮带归观察侧建档〕)→ 选中动画固定等待 → 确认
    (建档「按钮-确认选择」查找点击,全族统一;不带 until = 动作 op
    禁验证)。本屏零 chosen 写端(选择存证已退役),容器写零。"""

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
        param = self.param
        _gs = game_state_from_ctx(self.ctx)
        _pts = (_gs.fortune_opts_xy.value if _gs is not None else None) or []
        assert _pts, (
            '[cw-pick-fortune] 容器 fortune_opts_xy 缺席/空(观察上报缺失,禁'
            f'坐标现算回退): idx={param.idx}')
        assert 0 <= param.idx < len(_pts), (
            f'[cw-pick-fortune] param.idx 越界容器坐标槽(策略器 bug): '
            f'idx={param.idx} len={len(_pts)}')
        pt = Point(*_pts[param.idx])
        safe_click(op, pt, tag='cw-pick-fortune')
        time.sleep(1.2)
        # 确认 = 建档「按钮-确认选择」查找点击(round_by_find_and_click_area
        # 全族统一,用户裁定 2026-09-22;area 缺失 = 显式失败交框架轮次)。
        env.round_result = op.round_by_find_and_click_area(
            op.screenshot(), CwScreenFortune.SCREEN_NAME, '按钮-确认选择',
            success_wait=1.0)
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_fortune_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('命运卜者确认链已发(结果经旁路回传)')
