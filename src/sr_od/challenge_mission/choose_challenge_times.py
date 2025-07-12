import time

from cv2.typing import MatLike
from typing import ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ChooseChallengeTimes(SrOperation):

    def __init__(self, ctx: SrContext, total_times: int):
        """
        在挑战副本的选择难度页面
        选择挑战次数
        :param ctx:
        :param total_times: 总共挑战次数 <=6
        """
        SrOperation.__init__(self, ctx, op_name=gt('选择挑战次数'))
        self.total_times: int = total_times

    @operation_node(name='选择', node_max_retry_times=5, is_start_node=True)
    def choose(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()

        current = self._get_current_times(screen)
        if current == 0:  # 可能界面还没有加载出来 等等
            return self.round_retry(wait=0.5)

        if current == self.total_times:
            return self.round_success()
        elif current < self.total_times:
            if self._click_plus(screen, self.total_times - current):
                return self.round_success()
        else:
            if self._click_minus(screen, self.total_times - current):
                return self.round_success()

        return self.round_retry('未能判断当前选择次数', wait=1)

    def _get_current_times(self, screen: MatLike) -> int:
        """
        判断当前选择的次数
        :param screen: 屏幕截图
        :return: 当前选择次数
        """
        area = self.ctx.screen_loader.get_area('拟造花萼', '文本-挑战次数')
        part = cv2_utils.crop_image_only(screen, area.rect)
        # cv2_utils.show_image(part, win_name='_get_current_times')
        ocr_result = self.ctx.ocr.run_ocr_single_line(part, strict_one_line=True)
        return str_utils.get_positive_digits(ocr_result, err=0)

    def _click_plus(self, screen: MatLike, click_times: int) -> bool:
        """
        找到加号并点击
        :param screen: 屏幕截图
        :param click_times: 需要点击的次数
        :return: 是否点击成功
        """
        area = self.ctx.screen_loader.get_area('挑战副本', '次数加')
        result = self.round_by_find_area(screen, '挑战副本', '次数加')

        if not result.is_success:
            return False

        to_click = area.center
        for _ in range(click_times):
            if not self.ctx.controller.click(to_click):
                return False
            time.sleep(0.2)

        return True

    def _click_minus(self, screen: MatLike, click_times: int) -> bool:
        """
        找到减号并点击
        :param screen: 屏幕截图
        :param click_times: 需要点击的次数
        :return: 是否点击成功
        """
        area = self.ctx.screen_loader.get_area('挑战副本', '次数减')
        result = self.round_by_find_area(screen, '挑战副本', '次数减')

        if not result.is_success:
            return False

        to_click = area.center
        for _ in range(click_times):
            if not self.ctx.controller.click(to_click):
                return False
            time.sleep(0.2)

        return True
