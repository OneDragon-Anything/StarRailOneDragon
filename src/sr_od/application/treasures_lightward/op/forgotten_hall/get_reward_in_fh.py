import time
from typing import ClassVar, Optional

from cv2.typing import MatLike

from basic import Rect, Point
from basic.i18_utils import gt
from basic.img import cv2_utils
from sr.context.context import Context
from sr.operation import Operation, OperationOneRoundResult


class GetRewardInForgottenHall(Operation):

    REWARD_ICON_RECT: ClassVar[Rect] = Rect(1780, 910, 1890, 1020)  # 礼物图标的位置 包含红点
    CLAIM_REWARD_BTN_RECT: ClassVar[Rect] = Rect(1330, 360, 1480, 405)  # 可领取的按钮会在最上方 因此只需要判断最上方位置即可
    EMPTY_POS_AFTER_CLAIM: ClassVar[Point] = Point(965, 950)  # 领取奖励后点击的空白地方

    def __init__(self, ctx: Context):
        """
        需要已经在【逐光捡金】页面
        点击右下角领取奖励
        :param ctx:
        """
        super().__init__(ctx, try_times=5, op_name=gt('逐光捡金 领取星数奖励'))
        self.phase: int = 0

    def _execute_one_round(self) -> OperationOneRoundResult:
        if self.phase == 0:  # 判断右下角是否有红点
            if not self._check_reward():
                return self.round_success('无奖励')
            elif self.ctx.controller.click(GetRewardInForgottenHall.REWARD_ICON_RECT.center):
                self.phase += 1
                return self.round_wait()
        elif self.phase == 1:  # 点击领取奖励
            click = self.ocr_and_click_one_line('领取', GetRewardInForgottenHall.CLAIM_REWARD_BTN_RECT, wait_after_success=1)
            if click == Operation.OCR_CLICK_SUCCESS:  # 有领取按钮并点击成功
                self.ctx.controller.click(GetRewardInForgottenHall.EMPTY_POS_AFTER_CLAIM)
                time.sleep(1)
                return self.round_wait()
            elif click == Operation.OCR_CLICK_NOT_FOUND:
                return self.round_retry('领取完毕')
            else:
                return self.round_retry('领取奖励失败')

    def _check_reward(self, screen: Optional[MatLike] = None) -> bool:
        """
        检测是否有奖励可领取
        :param screen: 屏幕截图
        :return:
        """
        if screen is None:
            screen = self.screenshot()
        part, _ = cv2_utils.crop_image(screen, GetRewardInForgottenHall.REWARD_ICON_RECT)
        match_result_list = self.ctx.im.match_template(part, 'ui_alert', threshold=0.7)
        return len(match_result_list) > 0

    def _retry_fail_to_success(self, retry_status: str) -> Optional[str]:
        if '领取完毕' == retry_status:
            return '领取完毕'
        else:
            return None