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
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
    confirm_and_verify,
    find_text_center,
    safe_click,
)
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
        safe_click(self, HandleMegastar.CANDIDATE_LEFT, tag='cw-megastar')
        time.sleep(0.6)
        # 确认 + 验关(确认选择 消失 = overlay 关)。原「点了就 success」不验 → bug#1/隐藏多步 flat-loop
        # (partner overlay reset 根因同类;write-operation「点了≠成了」)。确认坐标未进 screen_info → OCR 定位。
        confirm = find_text_center(self, '确认选择')
        if confirm is None:
            log.info('[cw-megastar] 未找到 确认选择 → round_retry')
            return self.round_retry(wait=1)
        return confirm_and_verify(self, confirm_point=confirm, entry_keyword='确认选择',
                                  lcs_percent=0.7, tag='cw-megastar')
