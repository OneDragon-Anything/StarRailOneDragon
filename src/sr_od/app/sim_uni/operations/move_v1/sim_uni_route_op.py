from typing import ClassVar, Optional, Callable

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni.operations.move_v1.move_directly_in_sim_uni import MoveDirectlyInSimUni
from sr_od.app.sim_uni.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_route import SimUniRoute
from sr_od.app.world_patrol.world_patrol_route import WorldPatrolRouteOperation
from sr_od.config import operation_const
from sr_od.context.sr_context import SrContext
from sr_od.operations.move.move_without_pos import MoveWithoutPos
from sr_od.operations.sr_operation import SrOperation
from sr_od.sr_map.sr_map_def import Region


class SimUniRunRouteOp(SrOperation):

    STATUS_ALL_OP_DONE: ClassVar[str] = '执行结束'

    def __init__(self, ctx: SrContext, route: SimUniRoute,
                 config: Optional[SimUniChallengeConfig] = None,
                 op_callback: Optional[Callable[[OperationResult], None]] = None):
        """
        模拟宇宙 按照特定路线执行
        最后返回 data=Point 最新坐标
        """
        self.route: SimUniRoute = route
        self.route_no_battle: bool = self.route.no_battle_op  # 路线上是否无战斗 可以优化移动的效率
        self.op_idx: int = -1  # 当前执行的指令下标
        self.current_pos: Point = self.route.start_pos  # 当前的坐标
        self.config: Optional[SimUniChallengeConfig] = config
        self.current_region: Region = self.route.region  # 当前的区域

        SrOperation.__init__(self, ctx,
                             op_name='%s %s %s' % (
                                 gt('模拟宇宙', 'game'),
                                 gt('执行路线指令'),
                                 route.display_name
                             ),
                             op_callback=op_callback)

    @node_from(from_name='执行路线指令')
    @operation_node(name='执行路线指令', is_start_node=True)
    def _next_op(self) -> OperationRoundResult:
        """
        执行下一个指令
        :return:
        """
        self.op_idx += 1

        if self.op_idx >= len(self.route.op_list):
            return self.round_success(SimUniRunRouteOp.STATUS_ALL_OP_DONE)

        current_op: WorldPatrolRouteOperation = self.route.op_list[self.op_idx]
        next_op: Optional[WorldPatrolRouteOperation] = None
        if self.op_idx + 1 < len(self.route.op_list):
            next_op = self.route.op_list[self.op_idx + 1]

        if current_op.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE]:
            op = self.move(current_op, next_op)
        elif current_op.op == operation_const.OP_NO_POS_MOVE:
            op = self._move_by_no_pos(current_op)
        elif current_op.op == operation_const.OP_PATROL:
            op = SimUniEnterFight(self.ctx, config=self.config)
        elif current_op.op == operation_const.OP_DISPOSABLE:
            op = SimUniEnterFight(self.ctx, config=self.config, disposable=True)
        else:
            return self.round_fail('未知指令')

        return self.round_by_op_result(op.execute())

    def move(self, current_op: WorldPatrolRouteOperation, next_op: Optional[WorldPatrolRouteOperation]) -> SrOperation:
        """
        按坐标进行移动
        :param current_op: 当前指令
        :param next_op: 下一个指令
        :return:
        """
        next_pos = Point(current_op.data[0], current_op.data[1])
        stop_afterwards = not (
            next_op is not None
            and next_op.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE,
                                  # 如果下一个是攻击 则靠攻击停止移动 这样还可以取消疾跑后摇
                                  operation_const.OP_PATROL, operation_const.OP_DISPOSABLE,
                                  ]
        )

        current_lm_info = self.ctx.map_data.get_large_map_info(self.current_region)
        if len(current_op.data) > 2:
            next_region = self.ctx.map_data.best_match_region_by_name(
                gt(self.current_region.cn, 'game'), planet=self.current_region.planet,
                target_floor=current_op.data[2])
            next_lm_info = self.ctx.map_data.get_large_map_info(next_region)
        else:
            next_lm_info = None
        op = MoveDirectlyInSimUni(self.ctx, current_lm_info,
                                  next_lm_info=next_lm_info,
                                  start=self.current_pos, target=next_pos,
                                  stop_afterwards=stop_afterwards,
                                  op_callback=self._update_pos,
                                  config=self.config,
                                  no_battle=self.route_no_battle,
                                  no_run=current_op.op == operation_const.OP_SLOW_MOVE
                                  )
        return op

    def _move_by_no_pos(self, current_op: WorldPatrolRouteOperation):
        start = self.current_pos
        target = Point(current_op.data[0], current_op.data[1])
        move_time = None if len(current_op.data) < 3 else current_op.data[2]
        return MoveWithoutPos(self.ctx, start, target, move_time=move_time, op_callback=self._update_pos)

    def _update_pos(self, op_result: OperationResult):
        """
        更新坐标
        :param op_result:
        :return:
        """
        if not op_result.success:
            return
        self.current_pos = op_result.data

        route_item = self.route.op_list[self.op_idx]
        if len(route_item.data) > 2:
            self.current_region = self.ctx.map_data.best_match_region_by_name(
                gt(self.current_region.cn, 'game'), planet=self.current_region.planet,
                target_floor=route_item.data[2])

    @node_from(from_name='执行路线指令', status=STATUS_ALL_OP_DONE)
    @operation_node(name='结束')
    def _finished(self) -> OperationRoundResult:
        """
        指令执行结束
        :return:
        """
        return self.round_success(data=self.current_pos)