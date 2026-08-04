"""货币战争 出战确认弹窗(「可出战角色人数未达上限」)处理 op(从主循环拆出)。

勾「本局不再提示」+ 确认,解除 bench-full 警告阻塞出战。原 active_window+click 被 bug#1
吞 → 弹窗不消 → stall(round3 实测根因);改 mouse_move+click。

bug#1 mitigation: 关键 click 前 mouse_move。

TODO(task#20):勾选/确认坐标进 screen_info。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleDeployNotFull(SrOperation):
    """出战人数未达上限弹窗:勾本局不再提示 + 确认。"""

    CHECKBOX_NO_PROMPT: ClassVar[Point] = Point(912, 589)   # 「本局不再提示」勾选
    BTN_CONFIRM: ClassVar[Point] = Point(1159, 653)          # 「确认」

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-未达上限确认')

    @operation_node(name='未达上限确认', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_ocr(screen, '未达上限').is_success:
            return self.round_fail('非未达上限弹窗')
        self.ctx.controller.mouse_move(HandleDeployNotFull.CHECKBOX_NO_PROMPT)  # bug#1 mitigation
        time.sleep(0.3)
        self.ctx.controller.click(HandleDeployNotFull.CHECKBOX_NO_PROMPT)
        time.sleep(0.3)
        self.ctx.controller.mouse_move(HandleDeployNotFull.BTN_CONFIRM)
        time.sleep(0.3)
        self.ctx.controller.click(HandleDeployNotFull.BTN_CONFIRM)
        return self.round_success(wait=3)
