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


class CwScreenPlaneTransition(SrOperation):
    """位面过渡:识别「点击空白处继续」→ 点空白 → 重入观察裁决交回(验证废除)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-位面过渡'
    PROMPT_AREA: ClassVar[str] = '提示-点击空白继续'
    BLANK_AREA: ClassVar[str] = '区域-空白点击'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-位面过渡')
        # 点空白已发待重入裁决标志(验证废除形态,用户裁定 2026-09-10):
        # 重入裁决见 handle——提示不在 + 已发 = 过渡完成 → success 交回
        #(外循环 0q 的误分发计数只认 fail,完成路径必须 success)。
        self._click_pending: bool = False

    @operation_node(name='位面过渡', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        _hit = self.round_by_find_area(
            screen, self.SCREEN_NAME, self.PROMPT_AREA, crop_first=False).is_success
        # 重入裁决(观察驱动):上轮点空白已发 → 提示不在 = 过渡完成(提示
        # 已消失)→ success 交回;提示在 = 点击未落地 → 重点(计节点预算)。
        if self._click_pending:
            self._click_pending = False
            if not _hit:
                log.info('[cw-flow-plane] 过渡完成(重入观察:提示已消失)')
                return self.round_success('位面过渡完成(重入观察裁决)', wait=1.0)
        if not _hit:
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
        # 机械交回(验证废除):提示消失与否由下一轮重入观察裁决(本方法顶部)。
        self._click_pending = True
        return self.round_retry('点空白已发,重入观察裁决')
