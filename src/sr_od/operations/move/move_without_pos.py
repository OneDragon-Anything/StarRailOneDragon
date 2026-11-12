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
    """从起始坐标朝目标点「盲走」:按距离换算的秒数直线步行,不计算坐标、
    不做战斗判断。适合难以定位坐标的短途移动。非 MCP 传参单元:参数为运行时
    坐标对象,仅限代码内调用。

    使用前人物应处于静止(转向基准才稳定);到达后 data 返回目标点坐标。
    起点:大世界(起始坐标附近);终点:目标点附近(纯移动,原画面)。
    """

    def __init__(self, ctx: SrContext,
                 start: Point,
                 target: Point,
                 move_time: Optional[float] = None,
                 op_callback: Optional[Callable[[OperationResult], None]] = None):
        """
        :param ctx: 上下文
        :param start: 起始坐标(小地图像素系)
        :param target: 目标坐标(与 start 同系)
        :param move_time: 移动秒数;None=按两点距离与步行速度自动换算
        :param op_callback: 运行结束回调
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
        screen = self.last_screenshot

        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        angle = mini_map_utils.analyse_angle(mm)

        self.ctx.controller.turn_by_pos(self.start, self.target, angle)

        return self.round_success(wait=0.5)  # 等待转向结束

    @node_from(from_name='转向')
    @operation_node(name='移动')
    def _move(self) -> OperationRoundResult:
        self.ctx.controller.move('w', self.move_time)

        return self.round_success(data=self.target)