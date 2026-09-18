"""卖备战席角色动作 op(CwActionSellBenchOp)——动作 op 重组批③ 换壳
(原 ``PrepSellBenchOp``,ActionOp ABC → 框架 SrOperation;机械执行后
**op 内直调自己的上报函数** ``report_action_sell_bench_param``,零分派,
design.md §1.1/§1.2)。非终结。

命名申报:词表类 ``CwActionSellBenchParam`` 全框架唯一活执行路径 = 本 op
(原商店域 ``cw_sell_bench_action.SellBenchOp`` 生产不可达,随批③文件
删除;发射面策略收缩至备战期后备战域为唯一执行路径)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.sell_bench import (
    report_action_sell_bench_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionSellBenchParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionSellBenchOp(SrOperation):
    """卖备战槽角色:drag 槽中心 → 出售区(``drag_bench_to_sell`` 单一源;
    机械执行,源槽像素验重试拆除)。非终结。

    自上报(design.md §1.1):机械发出后直调上报函数,session 透传
    (溢出腿 tracked 对称吸收)。
    """

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionSellBenchParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionSellBenchOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='sell_bench', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """卖备战槽角色:drag 槽中心 → 出售区。

        emitted 语义 = 动作已机械发出(拖拽原语零判效,落地事实归观察侧
        reconcile 对账)。bench_idx = 容器槽位表下标,拖点直取(执行坐标
        边:备战栏-N area 序 = 下标序,零换算)。
        """
        action: CwActionSellBenchParam = self.param
        env = self.env
        ex = env.executor
        from sr_od.application.currency_war.prep_actions import (
            drag_bench_to_sell,
        )
        drag_bench_to_sell(ex._op, ex._ctx, action.bench_idx)
        ex._track_remove_bench(action.bench_idx)
        # 用户口述口径(screen_flow_timing.md #21,2026-09-02):卖出金币
        # 动画很快,等 1s 足够——批尾观察前补这段,防读到金币动画帧。
        time.sleep(1.0)
        # —— 自上报(机械发出后;design.md §1.1)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_sell_bench_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                session=getattr(getattr(self.ctx, 'cw_match', None),
                                'session', None))
        return self.round_success(f'卖备战槽{action.bench_idx + 1} ✓')
