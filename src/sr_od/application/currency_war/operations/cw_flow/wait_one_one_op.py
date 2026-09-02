"""货币战争 等待 1-1 备战 op(W971 P3a;01-opening §2 WaitOneOneOp 形态)。

投资环境确认后进 1-1:开局补给动画长且无结束标志(用户裁定特殊等待)。
主判据 = 轮询「备战阶段」文本出现(备战屏建档锚 ``标识-备战阶段``——该文本
两档同址无画面判别力,但此处只判「备战面板就绪」非画面分支,用途正当);
固定 ~10s(ONE_ONE_MAX_WAIT_S,待校准)仅作超时兜底:锚一直不现 = 异常,
留证(存图)交循环。不给备战循环加「现在是 1-1」特殊状态参数。
"""
import time
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.operations.cw_flow.cw_flow_const import (
    ONE_ONE_MAX_WAIT_S,
    ONE_ONE_POLL_INTERVAL_S,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _monotonic() -> float:
    """可测时钟(模块级单点:测试换假时钟验超时,生产等价 time.monotonic)。"""
    return time.monotonic()


class WaitOneOneOp(SrOperation):
    """等待 1-1 备战就绪:轮询「备战阶段」锚;超上界留证 fail 交循环。"""

    PREP_SCREEN: ClassVar[str] = '货币战争-备战'
    PREP_ANCHOR: ClassVar[str] = '标识-备战阶段'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-等待1-1备战')
        self._first_seen_ts: float | None = None   # 首见非就绪帧的时钟起点(超时兜底基)

    @operation_node(name='等待1-1', is_start_node=True)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self.round_by_find_area(
                screen, self.PREP_SCREEN, self.PREP_ANCHOR, crop_first=False).is_success:
            log.info('[cw-flow-wait11] 备战阶段锚命中(1-1 备战就绪)')
            return self.round_success('1-1 备战就绪')
        now = _monotonic()
        if self._first_seen_ts is None:
            self._first_seen_ts = now
        if now - self._first_seen_ts >= ONE_ONE_MAX_WAIT_S:
            self.save_screenshot(prefix='wait_one_one_timeout')   # 留证交循环
            log.warning('[cw-flow-wait11] 等待超时(%.0fs 锚未现),留证交循环',
                        ONE_ONE_MAX_WAIT_S)
            return self.round_fail('等待 1-1 备战超时(锚未现,已留证)')
        # round_wait 重跑本节点且不耗 retry:轮询由固定超时兜底,不吃框架预算。
        return self.round_wait(wait=ONE_ONE_POLL_INTERVAL_S)
