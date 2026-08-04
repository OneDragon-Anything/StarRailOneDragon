"""货币战争 投资策略 3 选 1 op(从主循环拆出)。

投资策略卡位因变体不同:点 body (900,550) 对部分变体直接选中、对部分开 detail;
故先点 body → 若「确认」被遮(detail 开了)→ ESC + 点卡底 (920,815) → 确认。

TODO(Stage B2):接 ``cw_decisions.decide_event``(cw_decisions.py:519 已实现,事件白名单打分)
  —— OCR 3 张投资策略选项 → decide_event 按 target_comp 打分 → 选最优,替代当前默认选中牌。
TODO(task#20):卡位坐标进 screen_info。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleInvestStrategy(SrOperation):
    """投资策略 3 选 1:点卡身(+ 兜底卡底)+ 确认。"""

    CARD_BODY: ClassVar[Point] = Point(900, 550)    # 中牌 body(部分变体直接选中)
    CARD_BOTTOM: ClassVar[Point] = Point(920, 815)  # 卡底(开 detail 时点此选中)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资策略')

    @operation_node(name='投资策略', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_ocr(screen, '投资策略').is_success:
            return self.round_fail('非投资策略屏')
        self.ctx.controller.click(HandleInvestStrategy.CARD_BODY)
        time.sleep(0.6)
        if not self.round_by_ocr(self.screenshot(), '确认').is_success:
            # detail 开了遮住确认 → ESC 关 detail + 点卡底选中
            self.ctx.controller.btn_tap('esc')
            time.sleep(0.5)
            self.ctx.controller.click(HandleInvestStrategy.CARD_BOTTOM)
            time.sleep(0.6)
        self.round_by_ocr_and_click(self.screenshot(), '确认', success_wait=2)
        return self.round_success(wait=2)
