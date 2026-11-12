from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.menu import phone_menu_const
from sr_od.operations.menu.click_phone_menu_item import ClickPhoneMenuItem
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.choose_team import ChooseTeam


class ChooseTeamInWorld(SrOperation):
    """从大世界出发完成配队切换并回到大世界(开菜单 → 编队 → 选配队并启用 → 返回)。
    起点:任意可控画面;终点:大世界(目标配队已启用)。
    """

    def __init__(self, ctx: SrContext, team_num: int):
        """
        :param ctx: 上下文
        :param team_num: 队伍编号,从 1 开始
        """
        SrOperation.__init__(self, ctx, op_name=gt('选择配队'))
        self.team_num: int = team_num

    @operation_node(name='返回大世界', is_start_node=True)
    def back_to_normal_world(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='返回大世界')
    @operation_node(name='打开菜单')
    def open_menu(self) -> OperationRoundResult:
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开菜单')
    @operation_node(name='点击编队')
    def click_team(self) -> OperationRoundResult:
        op = ClickPhoneMenuItem(self.ctx, phone_menu_const.TEAM_SETUP)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击编队')
    @operation_node(name='选择组队')
    def choose_team(self) -> OperationRoundResult:
        op = ChooseTeam(self.ctx, self.team_num, on=True)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择组队')
    @operation_node(name='返回')
    def back(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())