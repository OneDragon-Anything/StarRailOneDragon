"""开秘密典籍动作 op(CwActionOpenTomeOp)——动作 op 重组换壳(原
``OpenTomeOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内直调
自己的上报函数** ``report_action_open_tome_param``,零分派,op-layer.md
§1.2 动作 op 契约)。非终结:单击开典籍后星徽四选一 overlay 弹出,选卡交外循环
CwScreenBookcard 接管(overlay 检出走环中止交外环 handler,非本动作终结语义)。"""
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
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenTomeOp(CwOperation):
    """开秘密典籍:单击典籍槽(开启)→ 固定动画等待。非终结。

    单击化(用户确认 游戏实际 = 单击
    即弹;原双击序列的第二击落在已弹出的弹窗上有误触风险):
    实机核凭据 = 待实机局 journal(代码批先落地,实机验证随迭代收尾,
    )。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionOpenTomeParam,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionOpenTomeOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_tome', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """单击典籍槽即开启(单击化 = 用户确认 游戏实际,
        双击序列的第二击落在已弹弹窗上有误触风险;实机核凭据 = 待实机
        局 journal);弹窗后外循环分发 CwScreenBookcard
        接管选卡(本动作不选 —— 选卡是策略决策,板上阵营匹配在 CwScreenBookcard)。
        A3 拆除:「轮询验星徽四选一弹出」判效半删除,改固定等待;弹窗就位
        与否交下一帧观察(外循环分发重判)。
        """
        action: CwActionOpenTomeParam = self.param
        env = self.env
        ex = env.executor
        if action.slot is not None and not (1 <= action.slot <= len(ex._bench_pts)):
            # 参数违法由 op 自判(flow/action_ops.md §1 决策侧参数现算
            # 契约):slot = 画面物理槽 1 基(可选参数,None = 首槽),
            # 越界响亮暴露零点击。
            raise AssertionError(
                f'CwActionOpenTomeParam slot={action.slot} 越界'
                f'(1-{len(ex._bench_pts)})')
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
        if cw_sim_ports.mechanical_io_allowed():
            ex._ctx.controller.mouse_move(center)   # 防吞点击(截图前移光标)
            ex._ctx.controller.click(center)        # 单击:开启即弹
        # else sim:机械腿静默成功(直连旁路 port 检查,flow-seam §2)
        # 固定动画等待(原轮询判效半拆除,A3)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][tome] 开典籍槽{slot} → 单击已发(选卡交 CwScreenBookcard)')
        # —— 自上报(机械发出后;op-layer.md §1.2):开件腾位 ——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_open_tome_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success(f'开典籍槽{slot}')
