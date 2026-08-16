from typing import Optional, Callable

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation import Operation
from one_dragon.base.operation.operation_base import OperationResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.enter_game.open_and_enter_game import OpenAndEnterGame


class SrOperation(Operation):

    # 光标中立区(SR 通用):UID 黑块 —— 各屏截图管线(fill_uid_black)无条件涂灰区,
    # 光标停此恒不可见、不遮任何识别区域(审计 2026-08-16)。
    PARK_POINT: Point = Point(115, 1055)

    def __init__(self, ctx: SrContext,
                 node_max_retry_times: int = 3,
                 op_name: str = '',
                 timeout_seconds: float = -1,
                 op_callback: Optional[Callable[[OperationResult], None]] = None,
                 need_check_game_win: bool = True
                 ):
        self.ctx: SrContext = ctx
        op_to_enter_game = OpenAndEnterGame(ctx)
        Operation.__init__(self,
                           ctx=ctx,
                           node_max_retry_times=node_max_retry_times,
                           op_name=op_name,
                           timeout_seconds=timeout_seconds,
                           op_callback=op_callback,
                           need_check_game_win=need_check_game_win,
                           op_to_enter_game=op_to_enter_game)

    def park_cursor(self, before_wait: float = 0.1, after_wait: float = 0.2) -> None:
        """光标停到 SR 中立区(UID 黑块):动作后、识别截图前调用,防停靠光标污染识别区。

        场景:点击/拖拽目标与后续识别区域重叠(如购买经验按钮紧邻等级显示区,M38 level
        毒化根因链)。通用动作见 ``PcControllerBase.park_cursor``;此处封装 SR 默认停车点。
        """
        self.ctx.controller.park_cursor(self.PARK_POINT,
                                         before_wait=before_wait, after_wait=after_wait)
