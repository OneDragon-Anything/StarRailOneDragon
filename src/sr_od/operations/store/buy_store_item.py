from cv2.typing import MatLike
from typing import Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.store.store_const import StoreItem


class BuyStoreItem(SrOperation):

    def __init__(self, ctx: SrContext, item: StoreItem, buy_num: int):
        """
        在一个商店页面使用
        购买商品后 最后停留在商店页面
        :param ctx: 上下文
        :param item: 要购买的商品
        :param buy_num: 要购买的数量 0的话代表最大值
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('购买商品'), gt(item.cn, 'game')))

        self.item: StoreItem = item  # 要购买的商品
        self.buy_num: int = buy_num  # 要购买的数量

    @operation_node(name='选择商品', is_start_node=True)
    def choose_item(self) -> OperationRoundResult:
        screen = self.screenshot()
        pos = self.get_item_pos(screen)
        if pos is None:  # 找不到的时候 向下滑动
            area = self.ctx.screen_loader.get_area('商店', '商品列表')
            start_point = area.center
            end_point = start_point + Point(0, - 200)
            self.ctx.controller.drag_to(end_point, start_point)
            return self.round_retry(status=f'未找到商品{self.item.cn}', wait=0.5)
        else:
            self.ctx.controller.click(pos)
            return self.round_success(wait=0.5)

    def get_item_pos(self, screen: MatLike) -> Optional[Point]:
        """
        获取商品的位置
        :param screen: 游戏画面
        :return:
        """
        area = self.ctx.screen_loader.get_area('商店', '商品列表')
        part = cv2_utils.crop_image_only(screen, area.rect)

        mrl = self.ctx.tm.match_template(part, 'store', self.item.template_id, ignore_template_mask=True)
        if mrl.max is None:
            return None
        else:
            return mrl.max.center + area.rect.left_top

    @node_from(from_name='选择商品')
    @operation_node(name='选择数量')
    def choose_buy_num(self) -> OperationRoundResult:
        """
        选择购买数量 暂时只支持全量
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '商店', '按钮-购买最大值',
                                                 success_wait=0.5, retry_wait=1)

    @node_from(from_name='选择数量')
    @operation_node(name='确认购买')
    def buy_confirm(self) -> OperationRoundResult:
        """
        点击确认 不能购买时点击取消
        :return:
        """
        screen = self.screenshot()

        result1 = self.round_by_find_area(screen, '商店', '购买-已售罄')
        result2 = self.round_by_find_area(screen, '商店', '购买-兑换材料不足')

        if result1.is_success or result2.is_success:
            return self.round_by_find_and_click_area(screen, '商店', '按钮-购买取消',
                                                     success_wait=2, retry_wait=1)
        else:
            return self.round_by_find_and_click_area(screen, '商店', '按钮-购买确认',
                                                     success_wait=2, retry_wait=1)

    @node_from(from_name='确认购买', status='按钮-购买确认')
    @operation_node(name='点击空白处关闭')
    def click_empty(self) -> OperationRoundResult:
        """
        够买后 点击空白处关闭
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '大世界', '点击空白处关闭',
                                                 success_wait=1, retry_wait=1)
