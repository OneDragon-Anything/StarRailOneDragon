import time

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.menu import phone_menu_utils
from sr_od.operations.menu.phone_menu_const import PhoneMenuItem
from sr_od.operations.sr_operation import SrOperation


class ClickPhoneMenuItem(SrOperation):

    def __init__(self, ctx: SrContext, item: PhoneMenuItem):
        """
        点击菜单中的某个特定的项（中间大图标那块）
        需要先保证在菜单页面上
        """
        super().__init__(ctx, op_name=gt('点击菜单 %s') % gt(item.cn))

        self.item: PhoneMenuItem = item
        """需要点击的菜单"""

    @operation_node(name='点击菜单', node_max_retry_times=10, is_start_node=True)
    def click_item(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()

        result: MatchResult = phone_menu_utils.get_phone_menu_item_pos(self.ctx, screen, self.item)

        if result is None:  # 没找到的情况 上下随机滑动
            log.info('菜单中未找到 %s 尝试滑动', self.item.cn)
            self.scroll_menu_area(1 if self.node_retry_times % 2 == 1 else -1)
            return self.round_retry(wait=0.5)
        else:
            log.info('菜单中找到 %s 尝试点击', self.item.cn)
            r = self.ctx.controller.click(result.center)
            time.sleep(0.5)
            if r:
                return self.round_success()
            else:
                return self.round_retry(wait=0.5)

    def scroll_menu_area(self, d: int = 1):
        """
        在菜单区域的地方滚动鼠标
        :param d: 滚动距离 正向下 负向上
        :return:
        """
        x1, y1 = phone_menu_utils.MENU_ITEMS_PART.center.tuple()
        x2, y2 = x1, y1 + d * -200
        self.ctx.controller.drag_to(start=Point(x1, y1), end=Point(x2, y2), duration=0.5)
