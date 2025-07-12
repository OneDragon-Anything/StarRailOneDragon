import time

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.enter_game.enter_game import EnterGame
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu
from sr_od.operations.sr_operation import SrOperation


class SwitchAccount(SrOperation):

    def __init__(self, ctx: SrContext):
        """
        登出当前账号
        """
        SrOperation.__init__(self, ctx, op_name=gt('切换账号'))

    @operation_node(name='打开菜单', is_start_node=True)
    def open_menu(self) -> OperationRoundResult:
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from('打开菜单')
    @operation_node(name='返回登陆')
    def _back_to_login(self) -> OperationRoundResult:
        """
        返回登陆页面
        :return:
        """
        # 偷工减料 暂时直接点击不做匹配
        click = self.round_by_click_area('菜单', '按键-返回登录')

        if not click.is_success:
            return self.round_retry('点击返回登陆按钮失败', wait=1)

        time.sleep(2)

        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '菜单', '按键-返回登录确认',
                                                 success_wait=15, retry_wait=1)

    @node_from(from_name='返回登陆')
    @operation_node(name='进入游戏')
    def enter_game(self) -> OperationRoundResult:
        """
        登出
        :return:
        """
        op = EnterGame(self.ctx, switch=True)
        return self.round_by_op_result(op.execute())
