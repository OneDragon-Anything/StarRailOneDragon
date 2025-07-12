from typing import Optional, Callable

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cal_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.sr_map import mini_map_utils


class MoveWithoutPos(SrOperation):

    def __init__(self, ctx: SrContext,
                 start: Point,
                 target: Point,
                 move_time: Optional[float] = None,
                 op_callback: Optional[Callable[[OperationResult], None]] = None):
        """
        从当前位置 朝目标点直线前行
        按照不疾跑的速度移动若干秒 中途不会计算坐标 也不会进行任何战斗判断
        适合在难以判断坐标的情况下使用 且中途不会有任何打断或困住的情况

        为了更稳定移动到目标点 使用前人物应该静止

        返回 data = 目标点坐标
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s -> %s' % (gt('机械移动'), start, target),
                             op_callback=op_callback)

        self.start: Point = start
        self.target: Point = target
        self.move_time: float = move_time
        if move_time is None:
            dis = cal_utils.distance_between(self.start, self.target)
            self.move_time = dis / self.ctx.controller.walk_speed

    @operation_node(name='转向', is_start_node=True)
    def _turn(self) -> OperationRoundResult:
        screen = self.screenshot()

        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        angle = mini_map_utils.analyse_angle(mm)

        self.ctx.controller.turn_by_pos(self.start, self.target, angle)

        return self.round_success(wait=0.5)  # 等待转向结束

    @node_from(from_name='转向')
    @operation_node(name='移动')
    def _move(self) -> OperationRoundResult:
        self.ctx.controller.move('w', self.move_time)

        return self.round_success(data=self.target)