"""开补给箱动作 op(CwActionOpenBoxOp)——动作 op 重组批③ 换壳(原
``OpenBoxOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内直调
自己的上报函数** ``report_action_open_box_param``(零写族),零分派,
design.md §1.1/§1.2)。

终结动作(R7 批2a 终结化):点完「开启」本动作即交回外循环,武装箱选择
画面由外循环按画面分发独立画面 op 选卡。terminal_wait = 开箱动画等待,
与 runner 包络 ``_OVERLAY_ANIM_WAIT_S`` 等价(等价测试锁 =
test_cw_unified_action_3)。
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
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenBoxOp(SrOperation):
    """开箱:找箱槽 → 点「开启」→ 固定动画等待(纯机械执行)。

    选卡动作不在本执行链(R7 批 2a 定形):点完开启本动作即终结
    ——武装箱选择画面由外循环按画面分发独立画面 op(:mod:`cw_screen_box_pick`)
    选卡(选卡决策单一源 = 策略 ``decide_box_card`` 契约 / 局外 kernel
    ``pick_equipment`` 机器)。
    A3 拆除:「轮询验 overlay 弹出」判效半删除,改固定动画等待
    (等待归产生动画的操作);弹窗就位与否交下一帧观察。
    """

    #: 终结动作(开箱即引入新事实,交回外循环分发选卡)。
    terminal = True

    #: 交回等待 = 开箱动画等待值(与 prep_actions._OVERLAY_ANIM_WAIT_S
    #: 逐字等价,漂移由等价锁暴露)。
    terminal_wait = 1.8

    #: 「开启」文字区 = 箱 icon 下方偏移(2026-08-14 实测:槽center
    #: (563,911)→命中(565,952);体迁自执行器类属性,唯一消费 = 本 op)。
    BOX_OPEN_DY: ClassVar[int] = 41

    def __init__(self, ctx: SrContext, param: CwActionOpenBoxParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionOpenBoxOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_box', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行;终结动作(交回等待归消费点按 ``terminal_wait`` 读)。"""
        action: CwActionOpenBoxParam = self.param
        env = self.env
        ex = env.executor
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            read_supply_boxes,
        )
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        screen = ex._op.screenshot()
        boxes = read_supply_boxes(ex._ctx, screen)
        if not boxes:
            return self.round_fail('无补给箱')
        picked = boxes[0]
        if action.slot is not None:
            matched = next((b for b in boxes if b[0] == action.slot), None)
            if matched is None:
                return self.round_fail(
                    f'槽{action.slot} 无补给箱(实读 {boxes})')
            picked = matched
        slot, center = picked
        open_point = Point(center.x, center.y + self.BOX_OPEN_DY)
        ex._ctx.controller.mouse_move(open_point)   # 防吞点击(截图前移光标)
        ex._ctx.controller.click(open_point)
        # 固定动画等待(原轮询判效半拆除,A3;值取原轮询上界)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][box] 开箱槽{slot} → 点开启已发(交回外循环,武装箱'
                 '选择画面分发选卡)')
        # —— 自上报(机械发出后;零写族,design.md §1.2)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_open_box_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success(f'开箱槽{slot}')
