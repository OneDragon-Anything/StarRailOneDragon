import cv2
from cv2.typing import MatLike
from typing import Callable, Optional, ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class SimUniReward(SrOperation):

    POWER_NUM_RECT: ClassVar[Rect] = Rect(623, 715, 655, 744)  # 开拓力数字部分
    QTY_RECT: ClassVar[Rect] = Rect(1060, 715, 1090, 744)  # 沉浸器数字部分
    CLOSE_REWARD_BTN: ClassVar[Rect] = Rect(1433, 331, 1492, 382)  # 关闭沉浸奖励

    STATUS_GET_REWARD: ClassVar[str] = '获取奖励'

    def __init__(self, ctx: SrContext, max_to_get: int,
                 on_reward: Optional[Callable[[int, int], None]] = None
                 ):
        """
        模拟宇宙 - 获取沉浸奖励 需要已经打开领取的对话框
        :param ctx:
        :param max_to_get: 最多获取多少次奖励
        :param on_reward: 获取奖励时的回调
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('沉浸奖励')),)

        self.max_to_get: int = max_to_get  # 最多获取多少次奖励
        self.get_reward_cnt: int = 0  # 当前获取了多少次奖励
        self.on_reward: Optional[Callable[[int, int], None]] = on_reward  # 获取奖励时的回调

    @node_from(from_name='检查画面', status=sim_uni_screen_state.ScreenState.SIM_REWARD.value)
    @operation_node(name='获取奖励', is_start_node=True)
    def _get_reward(self) -> OperationRoundResult:
        screen = self.screenshot()

        state = sim_uni_screen_state.get_sim_uni_screen_state(self.ctx, screen, reward=True)

        if state != sim_uni_screen_state.ScreenState.SIM_REWARD.value:
            return self.round_retry('未在沉浸奖励画面', wait=1)

        if self.get_reward_cnt >= self.max_to_get:
            log.info('领取奖励完毕')
            self.ctx.controller.click(SimUniReward.CLOSE_REWARD_BTN.center)
            return self.round_success(wait=1)

        rect = self._get_reward_pos(screen)
        if rect is not None:
            self.ctx.controller.click(rect.center)
            if self.on_reward is not None:
                self.on_reward(
                    40 if rect == SimUniReward.POWER_NUM_RECT else 0,
                    1 if rect == SimUniReward.QTY_RECT else 0
                )
            return self.round_success(SimUniReward.STATUS_GET_REWARD)
        else:
            self.ctx.controller.click(SimUniReward.CLOSE_REWARD_BTN.center)
            return self.round_success(wait=1)

    def _get_reward_pos(self, screen: MatLike) -> Optional[Rect]:
        """
        获取可以点击的获取奖励按钮
        :param screen:
        :return:
        """
        for rect in [SimUniReward.QTY_RECT, SimUniReward.POWER_NUM_RECT]:  # 优先使用沉浸器
            part = cv2_utils.crop_image_only(screen, rect)
            black_part = cv2_utils.color_in_range(part, [0, 0, 0], [80, 80, 80])
            to_ocr = cv2.bitwise_and(part, part, cv2_utils.dilate(black_part, 5))
            # cv2_utils.show_image(black_part, win_name='black_part', wait=0)
            ocr_result = self.ctx.ocr.run_ocr_single_line(to_ocr)
            digit = str_utils.get_positive_digits(ocr_result, err=0)
            if digit > 0:
                return rect

        return None

    @node_from(from_name='获取奖励', status=STATUS_GET_REWARD)
    @operation_node(name='点击空白处关闭')
    def _click_empty(self) -> OperationRoundResult:
        """
        领取奖励后点击空白继续
        :return:
        """
        screen = self.screenshot()
        state = sim_uni_screen_state.get_sim_uni_screen_state(self.ctx, screen, empty_to_close=True)

        if state != sim_uni_screen_state.ScreenState.EMPTY_TO_CLOSE.value:
            return self.round_retry('未在点击空白处关闭画面', wait=1)

        return self.round_by_click_area('模拟宇宙', '点击空白处关闭',
                                        success_wait=1, retry_wait=1)

    @node_from(from_name='点击空白处关闭')
    @operation_node(name='检查画面')
    def _check_state(self) -> OperationRoundResult:
        """
        每轮后检查状态
        :return:
        """
        screen = self.screenshot()
        state = sim_uni_screen_state.get_sim_uni_screen_state(self.ctx, screen, in_world=True, reward=True)
        if state is None:
            return self.round_retry('判断画面状态失败', wait=1)
        else:
            return self.round_success(state)

    @node_from(from_name='获取奖励')  # 到达领取上限 或者 已经没有体力领取了
    @node_from(from_name='获取奖励', success=False)  # 可能画面判断出错了
    @node_from(from_name='检查画面', status=common_screen_state.ScreenState.NORMAL_IN_WORLD.value)  # 已经领取完了
    @operation_node(name='退出')
    def _esc(self) -> OperationRoundResult:
        """
        领取够了就退出
        :return:
        """
        return self.round_success()
