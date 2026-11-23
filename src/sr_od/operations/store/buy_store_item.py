import time

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.store.store_const import StoreItem

_POPUP_SCREEN: str = '商店-兑换弹窗'
"""购买数量弹窗与兑换弹窗是同一游戏组件(数量滑条 + 取消/确认),共用兑换弹窗档案
(docs/game/screens/store.md §8)。本 op 只按「画面名 + 区域名」取坐标,不做画面级
识别:弹窗锚文案「兑换数量」在各商店形态下是否恒可见未实证,购买链不得依赖它。"""

_AREA_STATUS_SOLD_OUT: str = '文本-弹窗状态横条-已售罄'
_AREA_STATUS_INSUFFICIENT: str = '文本-弹窗状态横条-兑换材料不足'
"""弹窗状态横条的两种不可购态(与兑换侧 :class:`ExchangeShopBuyGoods` 读同一横条)"""
_AREA_MAX: str = '按钮-拉满'
"""滑条上限钮(模板 ``store_buy_max``,滑条行随弹窗形态上下浮动时模板仍能定位)"""
_AREA_CONFIRM: str = '按钮-确认'
_AREA_CANCEL: str = '按钮-取消'
_AREA_CLOSE_HINT: str = '点击空白处关闭'
"""购买成功后「获得物品」弹窗底部提示文字;本 op 作为关闭点击点(非弹窗本体元素)"""


class BuyStoreItem(SrOperation):
    """在商店页面购买指定商品(模板匹配定位,列表外自动下滑寻找),处理购买
    数量弹窗后完成购买。非 MCP 传参单元:item 参数为运行时商品对象,
    仅限代码内调用。
    起点:商店页面;终点:商店页面(商品已购买)。
    副作用:消耗游戏货币购买商品,购买不可退。
    """

    def __init__(self, ctx: SrContext, item: StoreItem, buy_num: int):
        """
        :param ctx: 上下文
        :param item: 要购买的商品(商店商品常量表对象)
        :param buy_num: 购买数量,0 代表买满(弹窗默认最大值)
        """
        SrOperation.__init__(self, ctx, op_name=f'{gt("购买商品")} {gt(item.cn, "game")}')

        self.item: StoreItem = item  # 要购买的商品
        self.buy_num: int = buy_num  # 要购买的数量

    @operation_node(name='选择商品', is_start_node=True)
    def choose_item(self) -> OperationRoundResult:
        screen = self.last_screenshot
        pos = self.get_item_pos(screen)
        if pos is None:  # 找不到的时候 向下滑动
            area = self.ctx.screen_loader.get_area('商店', '商品列表')
            start_point = area.center
            end_point = start_point + Point(0, - 200)
            self.ctx.controller.drag_to(end_point, start_point)
            return self.round_retry(status=f'未找到商品{self.item.cn}', wait=0.5)
        else:
            # 先 mouse_move 到商品上、稍停再点 + 等待:click 后紧接的鼠标移动(下个 op 的 before_screenshot
            # 移光标到角落做截图卫生)会被游戏判拖拽 → 没点中。mouse_move 让 click 零移动、sleep+wait 留间隔避开。
            self.ctx.controller.mouse_move(pos)
            time.sleep(0.1)
            self.ctx.controller.click(press_time=0.1)
            return self.round_success(wait=0.5)

    def get_item_pos(self, screen: MatLike) -> Point | None:
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
        screen = self.last_screenshot
        # 售罄 / 兑换材料不足时弹窗无「购买最大值」按钮,直接进确认节点(会点取消),避免空找按钮重试到超时
        if self.round_by_find_area(screen, _POPUP_SCREEN, _AREA_STATUS_SOLD_OUT).is_success \
                or self.round_by_find_area(screen, _POPUP_SCREEN, _AREA_STATUS_INSUFFICIENT).is_success:
            return self.round_success(wait=0.5)
        return self.round_by_find_and_click_area(screen, _POPUP_SCREEN, _AREA_MAX,
                                                 success_wait=0.5, retry_wait=1)

    @node_from(from_name='选择数量')
    @operation_node(name='确认购买')
    def buy_confirm(self) -> OperationRoundResult:
        """
        点击确认 不能购买时点击取消
        :return:
        """
        screen = self.last_screenshot

        result1 = self.round_by_find_area(screen, _POPUP_SCREEN, _AREA_STATUS_SOLD_OUT)
        result2 = self.round_by_find_area(screen, _POPUP_SCREEN, _AREA_STATUS_INSUFFICIENT)

        if result1.is_success or result2.is_success:
            return self.round_by_find_and_click_area(screen, _POPUP_SCREEN, _AREA_CANCEL,
                                                     success_wait=2, retry_wait=1)
        else:
            return self.round_by_find_and_click_area(screen, _POPUP_SCREEN, _AREA_CONFIRM,
                                                     success_wait=2, retry_wait=1)

    # round_by_find_and_click_area 成功时 status = 区域名;本边只接「点了确认」,
    # 售罄/材料不足分支点取消后 status 为取消区域名、无出边 → op 正常结束
    @node_from(from_name='确认购买', status=_AREA_CONFIRM)
    @operation_node(name='点击空白处关闭')
    def click_empty(self) -> OperationRoundResult:
        """
        够买后 点击空白处关闭
        :return:
        """
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(screen, _POPUP_SCREEN, _AREA_CLOSE_HINT,
                                                 success_wait=1, retry_wait=1)
