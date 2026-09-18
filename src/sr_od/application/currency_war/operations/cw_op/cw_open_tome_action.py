"""开秘密典籍动作 op(CwActionOpenTomeOp)——动作 op 重组批③ 换壳(原
``OpenTomeOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内直调
自己的上报函数** ``report_action_open_tome_param``,零分派,design.md
§1.1/§1.2)。非终结:点两次开典籍后星徽四选一 overlay 弹出,选卡交外循环
0i 接管(overlay 检出走环中止交外环 handler,非本动作终结语义)。"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.open_tome import (
    report_action_open_tome_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenTomeParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenTomeOp(SrOperation):
    """开秘密典籍:点槽两次(选中→开启)→ 固定动画等待。非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionOpenTomeParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionOpenTomeOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_tome', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """点两次间隔 ~1s(第一次选中边框高亮,第二次弹窗);弹窗后 loop 0i
        接管选卡(本动作不选 —— 选卡是策略决策,板上阵营匹配在 0i handler)。
        A3 拆除:「轮询验星徽四选一弹出」判效半删除,改固定等待;弹窗就位
        与否交下一帧观察(0i 分发重判)。
        """
        action: CwActionOpenTomeParam = self.param
        env = self.env
        ex = env.executor
        from sr_od.application.currency_war.obs.cw_identity_obs import read_tomes
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        screen = ex._op.screenshot()
        tomes = read_tomes(ex._ctx, screen)
        if not tomes:
            return self.round_fail('无秘密典籍')
        picked = tomes[0]
        if action.slot is not None:
            matched = next((t for t in tomes if t[0] == action.slot), None)
            if matched is None:
                return self.round_fail(
                    f'槽{action.slot} 无典籍(实读 {tomes})')
            picked = matched
        slot, center = picked
        ex._ctx.controller.mouse_move(center)   # bug#1 缓解
        ex._ctx.controller.click(center)        # 第一次:选中
        time.sleep(1.0)
        ex._ctx.controller.click(center)        # 第二次:开启
        # 固定动画等待(原轮询判效半拆除,A3)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][tome] 开典籍槽{slot} → 点两次已发(选卡交 loop 0i)')
        # —— 自上报(机械发出后;design.md §1.1):开件腾席 ——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_open_tome_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success(f'开典籍槽{slot}')
