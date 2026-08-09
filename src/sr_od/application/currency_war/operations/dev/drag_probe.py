"""probe:逐个验 CW 拖拽机制(用户要求:先确定怎么拖一个生效)。

单次拖:mouse_move 源(settle,bug#1 缓解)→ drag_to(hold_time 长按拾取)→ 验。
跑完外部 CV 验(bench count 降 / 目标槽占)= 是否生效。
"""
import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# 默认:备战栏-1(438,912) → 前排-2(887,398,空槽)
SRC: Point = Point(438, 912)
DST: Point = Point(887, 398)


class DragProbe(SrOperation):
    """临时:验单次拖拽(长按 hold + mouse_move settle)。"""

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='cw-drag-probe')

    @operation_node(name='drag-probe', is_start_node=True)
    def drag(self) -> OperationRoundResult:
        # mouse_move 源 settle(bug#1:截图移光标后紧接 drag 落空;先 settle 到源)
        self.ctx.controller.mouse_move(SRC)
        time.sleep(0.2)
        # 长按 hold_time 拾取 + 拖
        self.ctx.controller.drag_to(start=SRC, end=DST, duration=1.0, hold_time=1.0)
        log.info(f'[cw-drag-probe] drag {SRC}→{DST} hold=1.0 + mouse_move settle')
        time.sleep(1.5)
        return self.round_success('dragged')


_EXPORT = DragProbe
