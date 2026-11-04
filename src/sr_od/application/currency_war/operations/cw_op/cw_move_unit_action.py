"""统一拖动动作 op(CwActionMoveUnitOp)——部署统一批(用户指令
2026-10-30「统一拖动角色 Op」):全域移动四元组载荷,机械拖拽源点位 →
目标点位。非终结。

机械执行零判效(同 CwActionDeployMoveOp 契约:拖后不做像素验证,
落地事实归观察侧 reconcile 对账;拖拽静默不生效属执行环境噪声,由
下一入口 heavy 实读对账暴露,重试 = 决策循环按新观察自然重派)。"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.move_unit import (
    report_action_move_unit_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionMoveUnitParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionMoveUnitOp(CwOperation):
    """统一拖动(front/back/bench 任意源 → 任意目标)。非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionMoveUnitParam,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionMoveUnitOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='move_unit', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """统一拖动:源点位 → 目标点位机械拖拽。

        执行坐标边:域内点位表直取——bench = 备战栏 area 序(状态容器下标 =
        area 序,0 基)/ front/back = 排 area 序(排内 1 基画面槽号 - 1)。
        静态合法域(front 1-4 / back 1-画面后排槽数 / bench 0-8;域枚举
        外)守卫断言 AssertionError 响亮暴露零拖拽(详设 D2-11 越界
        fail-closed;负下标回环 = 静默错点同防)。
        """
        action: CwActionMoveUnitParam = self.param
        env = self.env
        ex = env.executor

        def _pt(domain: str, slot: int):
            if domain == 'bench':
                if not 0 <= slot < len(ex._bench_pts):
                    raise AssertionError(
                        f'CwActionMoveUnitParam bench slot={slot} 越界'
                        f'(0-{len(ex._bench_pts) - 1})')
                return ex._bench_pts[slot]
            if domain == 'front':
                if not 1 <= slot <= len(ex._front_pts):
                    raise AssertionError(
                        f'CwActionMoveUnitParam front slot={slot} 越界'
                        f'(1-{len(ex._front_pts)})')
                return ex._front_pts[slot - 1]
            if domain == 'back':
                if not 1 <= slot <= len(ex._back_pts):
                    raise AssertionError(
                        f'CwActionMoveUnitParam back slot={slot} 越界'
                        f'(1-{len(ex._back_pts)})')
                return ex._back_pts[slot - 1]
            raise AssertionError(
                f'CwActionMoveUnitParam domain={domain!r} 非法'
                '(front/back/bench)')

        src = _pt(action.src_domain, int(action.src_slot))
        dst = _pt(action.dst_domain, int(action.dst_slot))
        ex._drag(src, dst)
        # 拖动触发的羁绊徽章动画口径同 CwActionDeployMoveOp
        # (screen_flow_timing #10「都等 2s」简单方案)。
        time.sleep(2.0)
        # —— 自上报(机械发出后;op-layer.md §1.2)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_move_unit_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success(
            f'拖动{action.src_domain}{action.src_slot}'
            f'->{action.dst_domain}{action.dst_slot} ✓'
            '(发出即记账,落地归观察对账)')
