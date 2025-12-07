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
from sr_od.screen_state import common_screen_state


class GuideOpen(SrOperation):

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=gt('打开指南'))

    @operation_node(name='画面识别', is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if common_screen_state.in_secondary_ui(self.ctx, screen, '星际和平指南'):
            return self.round_success('星际和平指南')
        else:
            return self.round_success('其他')

    @node_from(from_name='画面识别', status='其他')
    @operation_node(name='返回大世界')
    def back_to_world(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='返回大世界')
    @operation_node(name='打开菜单')
    def open_menu(self) -> OperationRoundResult:
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开菜单')
    @operation_node(name='选择指南')
    def choose_guide(self) -> OperationRoundResult:
        op = ClickPhoneMenuItem(self.ctx, phone_menu_const.INTERASTRAL_GUIDE)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择指南')
    @operation_node(name='等待加载')
    def wait(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if common_screen_state.in_secondary_ui(self.ctx, screen, '星际和平指南'):
            return self.round_success()
        else:
            return self.round_retry(wait=1)
