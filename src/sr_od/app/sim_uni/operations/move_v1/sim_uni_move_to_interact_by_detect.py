import time

import random
from cv2.typing import MatLike
from typing import ClassVar, Optional, List

from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from one_dragon.yolo import detect_utils
from one_dragon.yolo.detect_utils import DetectObjectResult
from sr_od.app.sim_uni.operations import sim_uni_move_utils
from sr_od.context.sr_context import SrContext
from sr_od.context.sr_pc_controller import SrPcController
from sr_od.operations.interact import interact_utils
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class SimUniMoveToInteractByDetect(SrOperation):

    STATUS_ARRIVAL: ClassVar[str] = '已到达'
    STATUS_INTERACT: ClassVar[str] = '已交互'
    STATUS_NO_DETECT: ClassVar[str] = '识别不到交互目标'

    def __init__(self, ctx: SrContext,
                 interact_class: str,
                 interact_word: str,
                 interact_during_move: bool = False):
        """
        根据画面识别可交互内容的位置 并朝之移动。
        进入之前 应该确保当前朝向能识别到内容，本操作不会旋转太多去找识别目标
        停下来的条件有
        - 识别不到可交互内容
        - 可交互(单行文本)
        - 进行了交互
        :param ctx: 上下文
        :param interact_class: 需要交互的类型
        :param interact_word: 交互文本
        :param interact_during_move: 移动过程中不断尝试交互 开启后不会再使用OCR判断是否有可交互的文本。使用前需满足 1.移动时任何交互都能接受 2.交互后不在大世界
        """
        SrOperation.__init__(self, ctx, op_name=gt(f'向 {interact_class} 移动', 'ui'))

        self.no_detect_times: int = 0
        """没有识别的次数"""

        self.start_move_time: float = 0
        """开始移动的时间"""

        self.interact_class: str = interact_class
        """需要交互的类型"""

        self.interact_word: str = interact_word
        """交互文本"""

        self.interact_during_move: bool = interact_during_move
        """移动过程中不断尝试交互"""
        
        self.existed_interact_word: Optional[str] = None
        """还没开始移动就已经存在的交互词"""

        self.find_in_last_detect: bool = False
        """在上一次识别中找到目标"""

    @operation_node(name='移动', timeout_seconds=20, is_start_node=True)  # 理论上移动目标都比较近 不可能20秒还没有到达
    def move(self) -> OperationRoundResult:
        now = time.time()
        screen = self.last_screenshot

        if self.existed_interact_word is None:
            self._check_interact_word(screen)

        if self.interact_during_move:  # 只有不断交互的情况 可能会进入不在大世界的页面
            in_world = common_screen_state.is_normal_in_world(self.ctx, screen)
        else:
            in_world = True

        if in_world:
            return self.handle_in_world(screen, now)
        else:
            return self.handle_not_in_world(screen, now)

    def handle_in_world(self, screen: MatLike, now: float) -> Optional[OperationRoundResult]:
        """
        处理在大世界的情况
        :param screen: 游戏画面
        :param now: 当前时间
        :return:
        """
        need_ocr = len(self.existed_interact_word) > 0 or not self.interact_during_move

        if not need_ocr:
            area = self.ctx.screen_loader.get_area('大世界', '移动交互-单行')
            self.ctx.controller.interact(
                pos=area.center,
                interact_type=SrPcController.MOVE_INTERACT_TYPE
            )

        # 移动2秒后 如果丢失了目标 停下来
        if self.ctx.controller.is_moving and now - self.start_move_time >= 2 and self.no_detect_times > 0:
            self.ctx.controller.stop_moving_forward()
            return self.round_wait()

        # 只有不直接交互的情况下 使用OCR判断是否已经到达
        if need_ocr and self._check_interact_word(screen):
            self.ctx.controller.stop_moving_forward()
            return self.round_success(status=SimUniMoveToInteractByDetect.STATUS_ARRIVAL)

        # 判断交互物体的位置
        pos_list = self.get_interact_pos(screen)
        if len(pos_list) == 0:
            return self.handle_no_detect()
        else:
            return self.handle_detect(pos_list)

    def get_interact_pos(self, screen: MatLike) -> List[DetectObjectResult]:
        """
        识别画面中交互物体的位置
        :param screen: 游戏截图
        :return:
        """
        frame_result = self.ctx.yolo_detector.sim_uni_yolo.run(screen)
        filter_results = []
        for result in frame_result.results:
            if not result.detect_class.class_category == self.interact_class:
                continue
            filter_results.append(result)
        if self.ctx.env_config.is_debug:
            # cv2_utils.show_image(detect_utils.draw_detections(frame_result), win_name='SimUniMoveToInteractByDetect')
            if len(frame_result.results) > 3 and random.random() < 0.3:
                self.save_screenshot()
        return filter_results

    def handle_no_detect(self) -> OperationRoundResult:
        """
        处理当前画面识别不到交互物体的情况
        :return:
        """
        if self.no_detect_times == 0 and self.find_in_last_detect:
            # 上一次能识别的 但转向之后刚好盖住了 那也可以开始移动了
            self.ctx.controller.start_moving_forward()
            self.start_move_time = time.time()

        self.no_detect_times += 1
        self.find_in_last_detect = False

        if self.no_detect_times >= 9:
            return self.round_fail(SimUniMoveToInteractByDetect.STATUS_NO_DETECT)

        # 第一次向右转一点 后续就在固定范围内晃动
        if self.no_detect_times == 1:
            angle = 15
        else:
            angle = -30 if self.no_detect_times % 2 == 0 else 30

        self.ctx.controller.turn_by_angle(angle)
        return self.round_wait(SimUniMoveToInteractByDetect.STATUS_NO_DETECT, wait=0.3)

    def handle_detect(self, pos_list: List[DetectObjectResult]) -> OperationRoundResult:
        """
        处理有交互物体的情况
        :param pos_list: 识别的列表
        :return:
        """
        self.find_in_last_detect = True
        self.no_detect_times = 0
        target = pos_list[0]  # 先固定找第一个
        target_angle = sim_uni_move_utils.delta_angle_to_detected_object(target)
        log.debug('目标角度 %.2f', target_angle)
        sim_uni_move_utils.turn_by_angle_slowly(self.ctx, target_angle)
        if abs(target_angle) >= sim_uni_move_utils._MAX_TURN_ANGLE * 2:  # 转向较大时 先完成转向再开始移动
            return self.round_wait()
        self.ctx.controller.start_moving_forward()
        self.start_move_time = time.time()
        return self.round_wait()

    def handle_not_in_world(self, screen: MatLike, now: float) -> Optional[OperationRoundResult]:
        """
        处理不在大世界的情况 暂时只有交互成功会进入
        :param screen: 游戏画面
        :param now: 当前时间
        :return:
        """
        self.ctx.controller.stop_moving_forward()
        return self.round_success(status=SimUniMoveToInteractByDetect.STATUS_INTERACT)

    def after_operation_done(self, result: OperationResult):
        """
        无论以哪种方式结束 都停止移动
        :param result:
        :return:
        """
        SrOperation.after_operation_done(self, result)
        self.ctx.controller.stop_moving_forward()

    def _check_interact_word(self, screen: MatLike) -> bool:
        """
        识别当前画面的交互文本
        :param screen:
        :return: 是否符合目标 可以交互
        """
        words = interact_utils.get_move_interact_words(self.ctx, screen, single_line=True)
        self.existed_interact_word = words[0].data if len(words) > 0 else ''
        log.debug('移动前已有交互 %s', self.existed_interact_word)
        is_target = self._is_target_interact()
        if is_target:  # 符合目标交互 就不需要OCR了
            self.existed_interact_word = ''

        return is_target

    def _is_target_interact(self) -> bool:
        return (
                len(self.existed_interact_word) > 0
                and str_utils.find_by_lcs(self.existed_interact_word, gt(self.interact_word, 'ocr'), percent=0.1)
        )
