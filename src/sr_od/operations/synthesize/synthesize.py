from typing import Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.menu import phone_menu_const
from sr_od.operations.menu.click_phone_menu_item import ClickPhoneMenuItem
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.synthesize.synthesize_const import SynthesizeItem, SynthesizeItemEnum


class Synthesize(SrOperation):

    def __init__(self, ctx: SrContext, item: SynthesizeItem, num: int):
        """
        如果不在合成页面 则进入合成页面
        合成指定物品后 停留在指定页面
        :param ctx: 上下文
        :param item: 要合成的物品
        :param num: 要合成的数量 0为最大值。当前只支持最大值
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('合成', 'game'), ''))

        self.item: SynthesizeItem = item  # 要合成的物品
        self.num: int = num  # 要合成的数量 0为最大值

    @node_from(from_name='画面识别')
    @operation_node(name='开始前返回')
    def back_at_first(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始前返回')
    @operation_node(name='打开菜单')
    def open_menu(self) -> OperationRoundResult:
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开菜单')
    @operation_node(name='选择合成')
    def choose_synthesize(self) -> OperationRoundResult:
        op = ClickPhoneMenuItem(self.ctx, phone_menu_const.SYNTHESIZE)
        return self.round_by_op_result(op.execute())

    @operation_node(name='画面识别', is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        """
        识别画面
        :return:
        """
        screen = self.screenshot()
        result = self.round_by_find_area(screen, '合成', '标题-合成')

        if result.is_success:
            return self.round_success(result.status)
        else:
            return self.round_success()

    @node_from(from_name='选择合成')
    @node_from(from_name='画面识别', status='标题-合成')
    @operation_node(name='选择合成类别')
    def choose_category(self) -> OperationRoundResult:
        """
        选择合成类别
        :return:
        """
        screen = self.screenshot()

        area = self.ctx.screen_loader.get_area('合成', '标题-合成分类')
        result = self.round_by_ocr(screen, self.item.category, area=area)

        if result.is_success:
            return self.round_success(result.status)
        else:
            self.round_by_click_area('合成', f'分类-{self.item.category}')
            return self.round_retry(result.status, wait=0.5)

    @node_from(from_name='选择合成类别')
    @operation_node(name='选择合成物品')
    def choose_item(self) -> OperationRoundResult:
        """
        选择合成物品
        :return:
        """
        screen = self.screenshot()
        result = self.get_item_pos(screen)

        if result is None:
            area = self.ctx.screen_loader.get_area('合成', '物品列表')
            drag_from = area.center
            drag_to = drag_from + Point(0, -300)
            self.ctx.controller.drag_to(start=drag_from, end=drag_to)
            return self.round_retry(f'未找到{self.item.name}', wait=2)
        else:
            self.ctx.controller.click(result.center)
            return self.round_success(wait=0.5)

    def get_item_pos(self, screen) -> Optional[MatchResult]:
        """
        获取合成物品的位置
        :param screen:
        :return:
        """
        area = self.ctx.screen_loader.get_area('合成', '物品列表')
        part = cv2_utils.crop_image_only(screen, area.rect)

        mrl = self.ctx.tm.match_template(part, 'synthesize', self.item.template_id)

        if mrl.max is None:
            return None

        result = mrl.max
        result.x += area.rect.left_top.x
        result.y += area.rect.left_top.y

        return result

    @node_from(from_name='选择合成物品')
    @operation_node(name='选择数量')
    def choose_num(self) -> OperationRoundResult:
        """
        选择合成数量 当前只支持最大值
        :return:
        """
        screen = self.screenshot()

        result = self.round_by_find_area(screen, '合成', '合成所需材料不足')
        if result.is_success:
            return self.round_fail(result.status)

        self.round_by_click_area('合成', '按钮-最大值')
        return self.round_success(wait=0.5)

    @node_from(from_name='选择数量')
    @operation_node(name='点击合成')
    def click_synthesize(self) -> OperationRoundResult:
        """
        进行合成
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '合成', '按钮-合成',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='点击合成')
    @operation_node(name='点击确认')
    def click_confirm(self) -> OperationRoundResult:
        """
        合成出现的对话框 点击确认
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '合成', '按钮-合成确认',
                                                 success_wait=5, retry_wait=1)

    @node_from(from_name='点击确认')
    @operation_node(name='点击空白处关闭')
    def click_empty(self) -> OperationRoundResult:
        """
        确认后 点击空白关闭
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '合成', '点击空白处关闭',
                                                 success_wait=1, retry_wait=1)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()

    op = Synthesize(ctx, SynthesizeItemEnum.TRICK_SNACK.value, 0)
    op.execute()


if __name__ == '__main__':
    __debug()