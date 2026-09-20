"""点晶矿动作 op(CwActionCollectOreOp)——动作 op 重组批③ 换壳
(原 ``CollectOreOp``,ActionOp ABC → 框架 SrOperation;机械执行后
**op 内直调自己的上报函数** ``report_action_collect_ore_param``,零分派,
design.md §1.1/§1.2)。R4 改形定形:载荷 = kernel ``select_ore_clicks``
产出的有序点击列,本 op 纯机械逐个点。非终结。"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.collect_ore import (
    report_action_collect_ore_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionCollectOreParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionCollectOreOp(SrOperation):
    """点晶矿:零读屏零排序零截断(挑选归决策侧 kernel 单一源),
    席满时部分晶矿可能没点开由后续观察回补。非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionCollectOreParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionCollectOreOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='collect_ore', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """逐坐标采晶矿(R4 机械执行半;载荷 = kernel ``select_ore_clicks``
        产出的有序点击列)。

        大晶矿优先/上界挑选归决策侧 kernel 单一源(发射位构造载荷),本方法
        纯机械逐个点(2026-09-02 用户指导 screen_flow_timing.md #16:晶矿
        飞行动画最长 ~2s → 点完等满动画;去向 = 备战/商店/装备栏)。零读屏
        零排序零截断;席满时部分晶矿可能没点开——由后续 heavy 观察自然回补。
        掉箱感知随之删除(掉箱归下一帧观察 → CwActionOpenBoxParam 臂)。
        """
        action: CwActionCollectOreParam = self.param
        env = self.env
        ex = env.executor
        for _x, _y in action.points:
            center = Point(_x, _y)
            ex._ctx.controller.mouse_move(center)   # bug#1 缓解
            ex._ctx.controller.click(center)
            ex._op.park_cursor(after_wait=0.1)
        # 用户口径:飞行动画最长 ~2s → 等满(固定等待归产生动画的操作)
        time.sleep(2.0)
        # —— 自上报(机械发出后;design.md §1.1):摘晶矿 + 收入待吸收窗 ——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_collect_ore_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                session=getattr(getattr(self.ctx, 'cw_match', None),
                                'session', None))
        detail = (f'采晶矿 {len(action.points)} 个(载荷机械点;'
                  f'动画等待 2s,晶矿未消由下一帧观察回补)')
        log.info(f'[cw][ore] {detail}')
        return self.round_success(detail)
