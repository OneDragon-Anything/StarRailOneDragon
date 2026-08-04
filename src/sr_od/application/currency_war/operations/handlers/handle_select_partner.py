"""货币战争 选择伙伴 overlay 处理 op(从主循环拆出)。

「选择伙伴」overlay 会挡住出战 → stall。点 stage 角色立绘选中 → 确认选择。
必须在「确认选择/巨星」(HandleMegastar)之前判断 —— 选择伙伴也有「确认选择」但候选是
stage 立绘(1048,299),非巨星的左候选(822,333)。

bug#1 mitigation: mouse_move + click。

TODO(task#20):stage 立绘坐标进 screen_info。
TODO:策略化选伙伴(按 target_comp.core_chars 评估候选)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleSelectPartner(SrOperation):
    """选择伙伴 overlay:点 stage 立绘 + 确认选择。"""

    # stage 角色立绘中心(vision 定位,2026-08-04 实测)。
    STAGE_PORTRAIT: ClassVar[Point] = Point(1048, 299)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-选择伙伴')

    @operation_node(name='选择伙伴', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_ocr(screen, '选择伙伴').is_success:
            return self.round_fail('非选择伙伴屏')
        self.ctx.controller.mouse_move(HandleSelectPartner.STAGE_PORTRAIT)  # bug#1 mitigation
        time.sleep(0.3)
        self.ctx.controller.click(HandleSelectPartner.STAGE_PORTRAIT)
        time.sleep(0.6)
        self.round_by_ocr_and_click(self.screenshot(), '确认选择', success_wait=2)
        return self.round_success(wait=2)
