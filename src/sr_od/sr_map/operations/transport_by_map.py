from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.wait.wait_in_world import WaitInWorld
from sr_od.sr_map.operations.choose_planet import ChoosePlanet
from sr_od.sr_map.operations.choose_region import ChooseRegion
from sr_od.sr_map.operations.choose_special_point import ChooseSpecialPoint
from sr_od.sr_map.operations.open_map import OpenMap
from sr_od.sr_map.sr_map_def import SpecialPoint


class TransportByMap(SrOperation):

    def __init__(self, ctx: SrContext, tp: SpecialPoint):
        """
        :param ctx: 上下文
        :param tp: 传送点
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s %s %s' % (
                                 gt('传送', 'game'),
                                 gt(tp.planet.display_name, 'game'),
                                 gt(tp.region.display_name, 'game'),
                                 gt(tp.display_name, 'game')
                             ))

        self.tp: SpecialPoint = tp

    @operation_node(name='打开地图', is_start_node=True)
    def open_map(self) -> OperationRoundResult:
        op = OpenMap(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开地图')
    @operation_node(name='选择星球')
    def choose_planet(self) -> OperationRoundResult:
        op = ChoosePlanet(self.ctx, self.tp.planet)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择星球')
    @operation_node(name='选择区域')
    def choose_region(self) -> OperationRoundResult:
        op = ChooseRegion(self.ctx, self.tp.region)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择区域')
    @operation_node(name='选择传送点')
    def choose_tp(self) -> OperationRoundResult:
        op = ChooseSpecialPoint(self.ctx, self.tp)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择传送点')
    @operation_node(name='等待传送完成')
    def wait_in_world(self) -> OperationRoundResult:
        op = WaitInWorld(self.ctx, 100)
        return self.round_by_op_result(op.execute())
