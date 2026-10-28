"""开补给箱动作 op(CwActionOpenBoxOp)——动作 op 重组 换壳(原
``OpenBoxOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内直调
自己的上报函数** ``report_action_open_box_param``(零写族),零分派,
op-layer.md §1.2 动作 op 契约)。

终结动作(R7 终结化):点完「开启」本动作即返回主循环,武装箱选择
画面由外循环按画面分发独立画面 op 选卡。terminal_wait = 开箱动画等待,
与 runner 包络 ``_OVERLAY_ANIM_WAIT_S`` 等价(等价测试 =
test_action_registry 终结集测试)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_open_box_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenBoxParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenBoxOp(CwOperation):
    """开箱:找箱槽 → 点「开启」→ 固定动画等待(纯机械执行)。

    选卡动作不在本执行链(R7 定形):点完开启本动作即终结
    ——武装箱选择画面由外循环按画面分发独立画面 op(:mod:`cw_screen_box_pick`)
    选卡(选卡决策单一源 = 策略 ``decide_box_card`` 契约 / 局外 kernel
    ``pick_equipment`` 机器)。
    A3 拆除:「轮询验 overlay 弹出」判效半删除,改固定动画等待
    (等待归产生动画的操作);弹窗就位与否交下一帧观察。
    """

    #: 终结动作(开箱即引入新事实,返回主循环分发选卡)。
    terminal = True

    #: 返回等待 = 开箱动画等待值(与 prep_actions._OVERLAY_ANIM_WAIT_S
    #: 逐字等价,漂移由等价测试暴露)。
    terminal_wait = 1.8

    #: 「开启」文字区 = 箱 icon 下方偏移(2026-08-14 实测:槽center
    #: (563,911)→命中(565,952);体迁自执行器类属性,唯一消费 = 本 op)。
    BOX_OPEN_DY: ClassVar[int] = 41

    def __init__(self, ctx: SrContext, param: CwActionOpenBoxParam,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionOpenBoxOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_box', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行;终结动作(返回等待归消费点按 ``terminal_wait`` 读)。"""
        action: CwActionOpenBoxParam = self.param
        env = self.env
        ex = env.executor
        if action.slot is not None and not (1 <= action.slot <= len(ex._bench_pts)):
            # 参数违法由 op 自判(flow/action_ops.md §1 决策侧参数现算
            # 契约):slot = 画面物理槽 1 基(可选参数,None = 首槽),
            # 越界响亮暴露零点击。
            raise AssertionError(
                f'CwActionOpenBoxParam slot={action.slot} 越界'
                f'(1-{len(ex._bench_pts)})')
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            read_armory_boxes,
        )
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        screen = ex._op.screenshot()
        boxes = read_armory_boxes(ex._ctx, screen)
        if not boxes:
            return self.round_fail('无简易武装箱')
        picked = boxes[0]
        if action.slot is not None:
            matched = next((b for b in boxes if b[0] == action.slot), None)
            if matched is None:
                return self.round_fail(
                    f'槽{action.slot} 无简易武装箱(实读 {boxes})')
            picked = matched
        slot, center = picked
        open_point = Point(center.x, center.y + self.BOX_OPEN_DY)
        if cw_sim_ports.mechanical_io_allowed():
            ex._ctx.controller.mouse_move(open_point)   # 防吞点击(截图前移光标)
            ex._ctx.controller.click(open_point)
        # else sim:机械执行分支静默成功(直连旁路 port 检查,flow-seam §2)
        # 固定动画等待(原轮询判效半拆除,A3;值取原轮询上界)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][box] 开箱槽{slot} → 点开启已发(交回外循环,武装箱'
                 '选择画面分发选卡)')
        # —— 自上报(机械发出后;零写族,op-layer.md §1.2)——
        # 上报后一行声明喂入(动作后果声明化喂入契约 = design.md §2.2
        # 契约 3;实机端口未装 = no-op,sim 装配后驱动后端 open_box);
        # round data 携带声明(journal 记账面)。
        world_decl = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_open_box_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
            world_decl = outcome.world_decl
            cw_sim_ports.declare_world(world_decl)
        return self.round_success(f'开箱槽{slot}', data=world_decl)
