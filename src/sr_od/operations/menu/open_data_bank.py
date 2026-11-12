"""打开智库(导航 op)。

从任意画面进入智库主页,作为智库内后续操作(选分类 / 读图鉴)的统一入口。

导航链(复用现成件):``OpenPhoneMenu`` 保证手机菜单已展开 →
``ClickPhoneMenuItem(DATA_BANK)`` 菜单项模板匹配(语言无关)→
智库主页(标题「智库」文本锚,screen_info 走框架 gt 翻译,
en 词条见 ``assets/text/game/en.po`` → game.mo)。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.menu import phone_menu_const
from sr_od.operations.menu.click_phone_menu_item import ClickPhoneMenuItem
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu
from sr_od.operations.sr_operation import SrOperation

_HOME_SCREEN: str = '智库主页'


class OpenDataBankOp(SrOperation):
    """从任意画面导航到智库主页。

    失败:菜单项持续找不到,或智库主页标题持续不命中。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=gt('打开智库'),
                             node_max_retry_times=20)

    @operation_node(name='打开菜单', is_start_node=True)
    def open_menu(self) -> OperationRoundResult:
        """保证手机菜单已展开(菜单项模板匹配的前提)。"""
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开菜单')
    @operation_node(name='点智库菜单项')
    def click_data_bank(self) -> OperationRoundResult:
        op = ClickPhoneMenuItem(self.ctx, phone_menu_const.DATA_BANK)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点智库菜单项')
    @operation_node(name='核对智库主页')
    def check_home(self) -> OperationRoundResult:
        """智库主页判定(标题「智库」文本锚,gt 翻译)。"""
        if self.round_by_find_area(self.last_screenshot,
                                   _HOME_SCREEN, '标题-智库').is_success:
            return self.round_success()
        return self.round_retry('智库主页标题未命中,等待页面加载', wait=2)
