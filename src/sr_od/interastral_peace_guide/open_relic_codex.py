"""打开智库的遗器图鉴页(导航 op)。

用途:快速到达「智库 → 遗器」图鉴列表页,查看遗器套装收录情况
(每套卡片显示 x/4 部位收录数;列表尾部锁定卡 = 未获得套装)。

导航链(复用现成件):
点击手机菜单图标(语言无关锚+置前)→ ``ClickPhoneMenuItem(DATA_BANK)``
(菜单项模板匹配)→ 智库主页 → 点「遗器」图标 → 遗器图鉴列表。

画面判定走框架 gt 翻译:智库主页标题「智库」、图鉴页「已收录」均为
screen_info 文本锚(en 词条见 ``assets/text/game/en.po`` → game.mo)。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.menu import phone_menu_const
from sr_od.operations.menu.click_phone_menu_item import ClickPhoneMenuItem
from sr_od.operations.sr_operation import SrOperation

_HOME_SCREEN: str = '智库主页'
_LIST_SCREEN: str = '智库-遗器图鉴'


class OpenRelicCodexOp(SrOperation):
    """导航到智库的遗器图鉴列表页。

    失败:智库主页/遗器图鉴判定持续不命中。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=gt('打开遗器图鉴'),
                             node_max_retry_times=20)

    @operation_node(name='打开菜单', is_start_node=True)
    def open_menu(self) -> OperationRoundResult:
        """自判定循环:菜单已开(开拓等级锚)→ success;大世界(角色图标
        锚)→ 点击手机菜单图标展开;其它画面(智库页等)→
        ``BackToNormalWorldPlus`` 兜底回大世界后下轮再点。
        大世界是锁光标画面(screen 级 pc_alt=true),取 area 中心显式
        pc_alt=True 点击。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  '菜单', '开拓等级') == FindAreaResultEnum.TRUE:
            return self.round_success()
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  '大世界', '角色图标') == FindAreaResultEnum.TRUE:
            menu_area = self.ctx.screen_loader.get_area('大世界', '按钮-手机菜单')
            self.ctx.controller.click(menu_area.rect.center, pc_alt=True)
            return self.round_retry('已点击手机菜单,等待菜单展开', wait=3)
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_retry(op.execute().status, wait=2)

    @node_from(from_name='打开菜单')
    @operation_node(name='打开智库')
    def open_data_bank(self) -> OperationRoundResult:
        """菜单点「智库」图标(菜单项模板匹配,语言无关)。"""
        op = ClickPhoneMenuItem(self.ctx, phone_menu_const.DATA_BANK)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开智库')
    @operation_node(name='核对智库主页')
    def check_home(self) -> OperationRoundResult:
        """智库主页判定(标题「智库」文本锚,gt 翻译)。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _HOME_SCREEN, '标题-智库') == FindAreaResultEnum.TRUE:
            return self.round_success()
        return self.round_retry('智库主页标题未命中,等待页面加载', wait=2)

    @node_from(from_name='核对智库主页')
    @operation_node(name='进入遗器图鉴')
    def open_relic_list(self) -> OperationRoundResult:
        """点「遗器」图标进入遗器图鉴;以「已收录」锚确认到达。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LIST_SCREEN, '锚-已收录') == FindAreaResultEnum.TRUE:
            return self.round_success()
        relic_area = self.ctx.screen_loader.get_area(_HOME_SCREEN, '按钮-遗器')
        self.ctx.controller.click(relic_area.rect.center)
        return self.round_retry('已点击遗器图标,等待图鉴打开', wait=3)
