"""货币战争 补给阶段 选装备 op(从主循环拆出)。

补给卡 body (900,550) 不开对话,直接点 body 选中 + 确认。

TODO(Stage C4):接 ``cw_decisions.decide_supply``(待实现,design 08§补给 / 07)——
  OCR 补给装备选项 → decide_supply 按 target_comp.key_equips 契合选(带钻/核心装备优先),
  替代当前默认选中牌。
TODO(task#20):卡位坐标进 screen_info。
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


class HandleSupply(SrOperation):
    """补给阶段选装备:点卡身 + 确认。"""

    CARD_BODY: ClassVar[Point] = Point(900, 550)  # 补给卡 body 不开对话

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-补给阶段')

    @operation_node(name='补给阶段', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_ocr(screen, '补给阶段').is_success:
            return self.round_fail('非补给阶段屏')
        safe_click(self, HandleSupply.CARD_BODY, tag='cw-supply')
        time.sleep(0.6)
        # 确认 + 验关(补给阶段 消失 = overlay 关)。原「点了就 success」不验 → bug#1/隐藏多步 flat-loop
        # (partner reset 根因同类;write-operation「点了≠成了」)。确认坐标未进 screen_info → OCR 定位「确认」。
        confirm = find_text_center(self, '确认')
        if confirm is None:
            log.info('[cw-supply] 未找到 确认 → round_retry')
            return self.round_retry(wait=1)
        return confirm_and_verify(self, confirm_point=confirm, entry_keyword='补给阶段',
                                  lcs_percent=0.7, tag='cw-supply')
