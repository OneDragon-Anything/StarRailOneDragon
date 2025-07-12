from typing import Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni.operations.move_v1.move_to_next_level import MoveToNextLevel
from sr_od.app.sim_uni.operations.move_v1.sim_uni_route_op import SimUniRunRouteOp
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import SimUniLevelType
from sr_od.app.sim_uni.sim_uni_route import SimUniRoute
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.technique import UseTechnique


class SimUniRunCombatRoute(SrOperation):

    def __init__(self, ctx: SrContext, world_num: int, level_type: SimUniLevelType, route: SimUniRoute,
                 config: Optional[SimUniChallengeConfig] = None,
                 ):
        """
        模拟宇宙 按照路线执行
        """
        self.world_num: int = world_num
        self.level_type: SimUniLevelType = level_type
        self.route: Optional[SimUniRoute] = route
        self.current_pos: Optional[Point] = None
        self.config: Optional[SimUniChallengeConfig] = config
        if config is None:
            ctx.sim_uni_info.world_num = world_num
            self.config = ctx.sim_uni_challenge_config

        SrOperation.__init__(self, ctx,
                             op_name='%s %s' % (
                                 gt('模拟宇宙', 'game'),
                                 gt('区域-%s' % level_type.type_name)
                             ),
                             )

    @operation_node(name='指令前初始化', is_start_node=True)
    def before_route(self) -> OperationRoundResult:
        """
        如果是秘技开怪 且是上buff类的 就在路线运行前上buff
        :return:
        """
        if not self.config.technique_fight or not self.ctx.team_info.is_buff_technique or self.ctx.tech_used_in_lasting:
            return self.round_success()
        else:
            op = UseTechnique(self.ctx,
                              max_consumable_cnt=0 if self.config is None else self.config.max_consumable_cnt,
                              need_check_point=True,  # 检查秘技点是否足够 可以在没有或者不能用药的情况加快判断
                              trick_snack=self.ctx.game_config.use_quirky_snacks,
                              )
            return self.round_by_op_result(op.execute())

    @node_from(from_name='指令前初始化')
    @operation_node(name='执行路线指令')
    def _run_route(self) -> OperationRoundResult:
        """
        执行下一个指令
        :return:
        """
        op = SimUniRunRouteOp(self.ctx, self.route, config=self.config, op_callback=self._update_pos)
        return self.round_by_op_result(op.execute())

    def _update_pos(self, op_result: OperationResult):
        """
        更新坐标
        :param op_result:
        :return:
        """
        if op_result.success:
            self.current_pos = op_result.data

    @node_from(from_name='执行路线指令')
    @operation_node(name='区域特殊指令')
    def _after_route(self) -> OperationRoundResult:
        """
        执行路线后的特殊操作 由各类型楼层自行实现
        :return:
        """
        return self.round_success()

    @node_from(from_name='区域特殊指令')
    @operation_node(name='下一层')
    def _go_next(self) -> OperationRoundResult:
        """
        前往下一层
        :return:
        """
        op = MoveToNextLevel(self.ctx, level_type=self.level_type, route=self.route,
                             config=self.config,
                             current_pos=self.current_pos)

        return self.round_by_op_result(op.execute())
