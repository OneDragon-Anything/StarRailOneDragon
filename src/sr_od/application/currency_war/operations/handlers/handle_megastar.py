"""货币战争 巨星强化选择 op(从主循环拆出)。

巨星强化轮(有「确认选择」、无「选择伙伴」)→ 选候选 + 确认。当前默认选左候选。

TODO(Stage B1):接 ``cw_comps.select_megastar``(cw_comps.py:509 已实现,按 target.core_chars
  绑角色)—— OCR 巨星候选 → select_megastar → 点对应候选,替代当前默认左候选。
TODO(task#20):候选坐标进 screen_info。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleMegastar(SrOperation):
    """巨星强化:选候选 + 确认选择。"""

    # 左候选中心(花火/大丽花位,实测)。TODO select_megastar 后按候选名定位。
    CANDIDATE_LEFT: ClassVar[Point] = Point(822, 333)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-巨星强化')

    @operation_node(name='巨星强化', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 巨星轮:有「确认选择」但无「选择伙伴」(选择伙伴由 HandleSelectPartner 先接)。
        if not self.round_by_ocr(screen, '确认选择').is_success:
            return self.round_fail('非巨星确认屏')
        if self.round_by_ocr(screen, '选择伙伴').is_success:
            return self.round_fail('是选择伙伴屏,应由 HandleSelectPartner 处理')
        self.ctx.controller.click(HandleMegastar.CANDIDATE_LEFT)
        time.sleep(0.6)
        self.round_by_ocr_and_click(self.screenshot(), '确认选择', success_wait=2)
        return self.round_success(wait=2)
