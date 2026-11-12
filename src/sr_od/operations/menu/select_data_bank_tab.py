"""智库主页选分类(导航 op)。

前提:已在智库主页(由 ``OpenDataBankOp`` 到达)。点击目标分类图标进入
对应图鉴列表页,以「标题-分类名 + 锚-已收录」双锚确认到达 —— 单锚
「已收录」在全部列表页都有,验不了进对没进。

分类按钮坐标与各列表页锚均在 screen_info(智库主页 / 智库-<分类>图鉴),
文字锚走框架 gt 翻译(英文用词取自实机英文界面截图,
词条见 ``assets/text/game/en.po`` → game.mo)。
"""

from enum import Enum

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_HOME_SCREEN: str = '智库主页'
_INDEX_ANCHOR: str = '锚-已收录'


class DataBankTab(Enum):
    """智库主页的分类;枚举值即中文名,画面名与按钮 area 名由它派生。"""

    LIGHT_CONE = '光锥'
    CHARACTER = '角色'
    RELIC = '遗器'
    ENEMY = '敌对物种'
    AEON = '星神'
    PATH = '派系'
    TERM = '专有名词'

    @property
    def list_screen_name(self) -> str:
        """分类图鉴列表画面名(screen_info 的 screen_name)。"""
        return f'智库-{self.value}图鉴'

    @property
    def button_area_name(self) -> str:
        """主页分类按钮 area 名(screen_info 的 area_name)。"""
        return f'按钮-{self.value}'


class SelectDataBankTabOp(SrOperation):
    """在智库主页点选分类,进入对应图鉴列表页。

    失败:起点不在智库主页(需先跑 ``OpenDataBankOp``),或点击后目标
    列表页锚持续不命中。
    """

    def __init__(self, ctx: SrContext, tab: DataBankTab | str):
        """
        :param ctx: 上下文
        :param tab: 目标分类(枚举或枚举值中文名,如 '遗器')
        """
        self.tab: DataBankTab = tab if isinstance(tab, DataBankTab) else DataBankTab(tab)
        SrOperation.__init__(self, ctx,
                             op_name=gt('选择智库分类 %s') % gt(self.tab.value),
                             node_max_retry_times=20)

    @operation_node(name='选择分类', is_start_node=True)
    def select_tab(self) -> OperationRoundResult:
        screen = self.last_screenshot

        if screen_utils.is_target_screen(self.ctx, screen,
                                         self.tab.list_screen_name):
            return self.round_success()

        if not screen_utils.is_target_screen(self.ctx, screen, _HOME_SCREEN):
            return self.round_fail('当前不在智库主页,需先运行 OpenDataBankOp')

        return self.round_by_find_and_click_area(
            screen, _HOME_SCREEN, self.tab.button_area_name,
            until_find_all=[
                (self.tab.list_screen_name, f'标题-{self.tab.value}'),
                (self.tab.list_screen_name, _INDEX_ANCHOR),
            ],
            success_wait=1, retry_wait=2)
