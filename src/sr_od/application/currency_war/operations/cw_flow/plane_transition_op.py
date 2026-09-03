"""货币战争 位面过渡 op(W971 P3a;01-opening §2/§3)。

「点击空白处继续」提示出现即点空白(简报下一步后 / 每个 boss 位面开始时各一次)。
完成 = 提示消失(真转移)交回循环;提示未现 = 该步不适用(编排壳按步分流)。
识别与点击坐标均走 screen_info(``currency_war_plane_transition``:
提示 text area + 区域-空白点击,cw_loop 实证空白点建档)。
"""
import time
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class PlaneTransitionOp(SrOperation):
    """位面过渡:识别「点击空白处继续」→ 点空白 → 验提示消失。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-位面过渡'
    PROMPT_AREA: ClassVar[str] = '提示-点击空白继续'
    BLANK_AREA: ClassVar[str] = '区域-空白点击'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-位面过渡')

    @operation_node(name='位面过渡', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.PROMPT_AREA, crop_first=False).is_success:
            # 提示未现:未到位(上位面未结束)或已过去 → fail 交编排壳/循环重新分流。
            return self.round_fail('位面过渡提示未出现')
        blank = area_center(self.ctx, self.BLANK_AREA, self.SCREEN_NAME)
        if blank is None:
            return self.round_fail('位面过渡缺「区域-空白点击」建档')
        log.info('[cw-flow-plane] 过渡提示命中 → 点空白 (%s,%s)', blank.x, blank.y)
        # bug#1 缓解(mouse_move 先,overlay 族同款)
        self.ctx.controller.mouse_move(blank)
        self.ctx.controller.click(blank)
        time.sleep(1.0)   # click 异步落地 + 过渡翻页动画
        # 出口验真转移:提示消失(点空白后仍见提示 = 未生效,重点计预算)。
        if self.round_by_find_area(
                self.screenshot(), self.SCREEN_NAME, self.PROMPT_AREA,
                crop_first=False).is_success:
            return self.round_retry('点空白后过渡提示仍在')
        log.info('[cw-flow-plane] 过渡完成(提示已消失)')
        return self.round_success('位面过渡完成', wait=1.0)
