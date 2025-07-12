import time
from typing import ClassVar, Optional

import cv2
import numpy as np
from cv2.typing import MatLike

from basic import Rect, Point
from basic.i18_utils import gt
from basic.img import cv2_utils, MatchResult
from sr.context.context import Context
from sr.operation import Operation


class ClickStoreItem(Operation):

    """
    商店购买页面 点击特定的商品
    """

    STORE_ITEM_LIST: ClassVar[Rect] = Rect(290, 110, 1790, 817)

    def __init__(self, ctx: Context, item_name: str, lcs_percent: float):
        super().__init__(ctx, try_times=5,
                         op_name='%s %s' % (gt('点击商品'), gt(item_name, 'game')))
        self.item_name: str = item_name
        self.lcs_percent: float = lcs_percent

    def _execute_one_round(self) -> int:
        screen: MatLike = self.screenshot()

        best_result = self._get_item_pos(screen)
        if best_result is None:
            start_point: Point = ClickStoreItem.STORE_ITEM_LIST.center
            end_point: Point = Point(start_point.x, start_point.y - 100)
            self.ctx.controller.drag_to(end_point, start_point)
            time.sleep(0.5)
            return Operation.RETRY

        to_click: Point = best_result.center
        click = self.ctx.controller.click(to_click)
        if click:
            return Operation.SUCCESS
        else:
            return Operation.RETRY

    def _get_item_pos(self, screen: Optional[MatLike] = None) -> Optional[MatchResult]:
        """
        获取对应商品的位置
        :param screen: 屏幕截图
        :return: 商品在屏幕上的位置
        """
        if screen is None:
            screen = self.screenshot()

        part, _ = cv2_utils.crop_image(screen, ClickStoreItem.STORE_ITEM_LIST)
        lower_color = np.array([200, 200, 200], dtype=np.uint8)
        upper_color = np.array([255, 255, 255], dtype=np.uint8)
        white_part = cv2.inRange(part, lower_color, upper_color)
        to_ocr = cv2.bitwise_and(part, part, mask=white_part)

        best_result = self.ctx.ocr.match_one_best_word(to_ocr, self.item_name, self.lcs_percent)

        if best_result is not None:
            lt = ClickStoreItem.STORE_ITEM_LIST.left_top
            best_result.x += lt.x
            best_result.y += lt.y

        return best_result
