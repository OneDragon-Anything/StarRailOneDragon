import time
from typing import ClassVar, List, Optional

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.bless import bless_utils
from sr_od.app.sim_uni.operations.bless.bless_utils import SimUniBlessPos
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import SimUniBless
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class SimUniChooseBless(SrOperation):

    RESET_BTN: ClassVar[Rect] = Rect(1160, 960, 1460, 1000)  # 重置祝福
    CONFIRM_BTN: ClassVar[Rect] = Rect(1530, 960, 1865, 1000)  # 确认
    CONFIRM_BEFORE_LEVEL_BTN: ClassVar[Rect] = Rect(783, 953, 1133, 997)  # 确认 - 楼层开始前

    STATUS_STILL_BLESS: ClassVar[str] = '仍在选择祝福'

    def __init__(self, ctx: SrContext,
                 config: Optional[SimUniChallengeConfig] = None,
                 skip_first_screen_check: bool = True,
                 before_level_start: bool = False,
                 fast_back_to_world: bool = False):
        """
        按照优先级选择祝福 如果选择后仍然在选择祝福画面 则继续选择。可能的情况有
        - 连续祝福，例如第一场战斗有两次祝福
        - 脚本并没有选择到祝福，游戏画面一直停流

        选择祝福后 如果还有再次触发的内容，左上角title会较快消失。返回大世界的话，左上角title会较慢消失。
        :param ctx:
        :param config: 挑战配置
        :param skip_first_screen_check: 是否跳过第一次的画面状态检查
        :param before_level_start: 是否在楼层开始的选择
        :param fast_back_to_world 需要快速判断返回世界
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('选择祝福')))

        self.config: Optional[SimUniChallengeConfig] = ctx.sim_uni_challenge_config if config is None else config  # 祝福优先级
        self.skip_first_screen_check: bool = skip_first_screen_check  # 是否跳过第一次的画面状态检查 用于提速
        self.before_level_start: bool = before_level_start  # 在真正楼层开始前 即选择开拓祝福时
        self.fast_back_to_world: bool = fast_back_to_world  # 需要快速判断返回世界

    def handle_init(self) -> Optional[OperationRoundResult]:
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """
        self.first_screen_check = True
        self.choose_bless_time: Optional[float] = None  # 选择祝福的时间

        return None

    @operation_node(name='等待画面', node_max_retry_times=5, is_start_node=True)
    def first_wait(self):
        screen = self.screenshot()

        if not self.first_screen_check or not self.skip_first_screen_check:
            self.first_screen_check = False
            if not sim_uni_screen_state.in_sim_uni_choose_bless(screen, self.ctx.ocr):
                return self.round_retry('未在模拟宇宙-选择祝福页面', wait=1)

        return self.round_success()

    @node_from(from_name='等待画面')
    @operation_node(name='选择祝福')
    def choose(self) -> OperationRoundResult:
        screen = self.screenshot()

        bless_pos_list: List[SimUniBlessPos] = bless_utils.get_bless_pos(self.ctx, screen)

        if len(bless_pos_list) == 0:
            return self.round_retry('未识别到祝福', wait=1)

        target_bless_pos: Optional[SimUniBlessPos] = self._get_bless_to_choose(screen, bless_pos_list)
        if target_bless_pos is None:
            self.ctx.controller.click(SimUniChooseBless.RESET_BTN.center)
            return self.round_wait('重置祝福', wait=1)
        else:
            self.ctx.controller.click(target_bless_pos.rect.center)
            time.sleep(0.25)
            if self.before_level_start:
                confirm_point = SimUniChooseBless.CONFIRM_BEFORE_LEVEL_BTN.center
            else:
                confirm_point = SimUniChooseBless.CONFIRM_BTN.center
            self.ctx.controller.click(confirm_point)
            self.choose_bless_time = time.time()
            return self.round_success(wait=0.1)

    def _can_reset(self, screen: MatLike) -> bool:
        """
        判断当前是否能重置
        :param screen: 屏幕祝福
        :return:
        """
        part, _ = cv2_utils.crop_image(screen, SimUniChooseBless.RESET_BTN)
        lower_color = np.array([220, 220, 220], dtype=np.uint8)
        upper_color = np.array([255, 255, 255], dtype=np.uint8)
        white_part = cv2.inRange(part, lower_color, upper_color)
        to_ocr = cv2.bitwise_and(part, part, mask=white_part)

        ocr_result = self.ctx.ocr.run_ocr_single_line(to_ocr)

        return str_utils.find_by_lcs(gt('重置祝福', 'ocr'), ocr_result)

    def _get_bless_to_choose(self, screen: MatLike, bless_pos_list: List[SimUniBlessPos]) -> Optional[SimUniBlessPos]:
        """
        根据优先级选择对应的祝福
        :param bless_pos_list: 祝福列表
        :return:
        """
        bless_list: list[SimUniBless] = [i.bless for i in bless_pos_list]
        can_reset = self._can_reset(screen)
        target_idx = bless_utils.get_bless_by_priority(bless_list, self.config, can_reset, asc=True)
        if target_idx is None:
            return None
        else:
            return bless_pos_list[target_idx]

    @node_from(from_name='选择祝福')
    @operation_node(name='选择后等待结束')
    def wait_not_in_bless(self) -> OperationRoundResult:
        """
        选择祝福后 等待画面不是【选择祝福】再退出
        这样方便后续指令在选择祝福后立刻做其它事情
        一段时间后还在选择祝福的话 可能是连续祝福 仍然返回
        :return:
        """
        if self.fast_back_to_world:
            now = time.time()
            screen = self.screenshot()
            if sim_uni_screen_state.in_sim_uni_choose_bless(self.ctx, screen):

                # OCR需要时间 这里就不等待了
                if now - self.choose_bless_time >= 2:
                    return self.round_success(status=SimUniChooseBless.STATUS_STILL_BLESS)
                else:
                    return self.round_wait(status=SimUniChooseBless.STATUS_STILL_BLESS)
            else:
                return self.round_success()
        else:
            return self.round_success(wait=1)


def __debug():
    ctx = SrContext()
    ctx.init_ocr()
    ctx.init_by_config()
    ctx.init_for_sim_uni()

    ctx.start_running()
    op = SimUniChooseBless(ctx)
    op.execute()
    ctx.stop_running()


if __name__ == '__main__':
    __debug()
