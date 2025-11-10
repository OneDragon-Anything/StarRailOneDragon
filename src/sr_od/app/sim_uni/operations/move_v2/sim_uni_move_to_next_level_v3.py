import time

import numpy as np
from cv2.typing import MatLike
from typing import Optional, List

from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.utils import str_utils, cal_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations import sim_uni_move_utils
from sr_od.app.sim_uni.operations.move_v1.move_to_next_level import MoveToNextLevel
from sr_od.app.sim_uni.sim_uni_const import SimUniLevelType, SimUniLevelTypeEnum
from sr_od.config import game_const
from sr_od.context.sr_context import SrContext
from sr_od.context.sr_pc_controller import SrPcController
from sr_od.operations.interact import interact_utils
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state
from sr_od.sr_map import mini_map_utils


class MoveToNextLevelV3(SrOperation):

    def __init__(self, ctx: SrContext, level_type: SimUniLevelType, with_entry: bool = True,
                 turn_direction: int = 0):
        SrOperation.__init__(self, ctx, op_name=gt('向下层移动v3'))
        self.level_type: SimUniLevelType = level_type
        self.start_with_entry: bool = with_entry  # 开始前是否识别到入口
        self.turn_direction: int = turn_direction  # 转动找下层入口的方向 1=右边 -1=左边

        self.detect_entry_angle: float = -1  # YOLO识别的入口所在的方向
        self.feature_no_entry_times: int = 0  # 特征识别图标没有找到入口的次数
        self.current_interact_word: str = ''  # 当前存在的交互词
        self.get_rid_direction: str = 'a'  # 脱困方向
        self.move_times: int = 0  # 累计的移动次数
        self.start_move_time: float = 0  # 开始移动的时间
        self.interacted: bool = False  # 是否已经尝试过交互
        self.interact_time: float = 0  # 交互的时间
        self.detect_fail_times: int = 0  # YOLO识别失败的次数

        # 是否出现过交互词
        # 休整、精英楼层有其它可以交互的内容 因此需要出现过正确交互词才能交互
        # 其它楼层无脑交互即可
        self.existed_interact_word: bool = self.level_type not in [
            SimUniLevelTypeEnum.RESPITE.value,
            SimUniLevelTypeEnum.ELITE.value
        ]

    @operation_node(name='画面识别前初始化', is_start_node=True)
    def check_before_detect(self) -> OperationRoundResult:
        """
        YOLO识别前的初始化
        :return:
        """
        if self.start_with_entry:
            self.record_detect_angle()

        return self.round_success()

    @node_from(from_name='画面识别前初始化')
    @node_from(from_name='画面识别失败后移动')  # 往前移动后 再继续识别
    @operation_node(name='画面识别转向入口')
    def turn_by_detect(self) -> OperationRoundResult:
        """
        靠YOLO识别 先大概转到下层入口方向
        :return:
        """
        screen = self.screenshot()

        frame_result = self.ctx.yolo_detector.sim_uni_yolo.run(screen)

        entry_angles: List[float] = []
        for result in frame_result.results:
            delta_angle = sim_uni_move_utils.delta_angle_to_detected_object(result)
            if result.detect_class.class_category == '模拟宇宙下层入口':
                entry_angles.append(delta_angle)

        if len(entry_angles) > 0:
            avg_delta_angle = np.mean(entry_angles)
            log.debug('转向 %.2f', avg_delta_angle)
            sim_uni_move_utils.turn_by_angle_slowly(self.ctx, avg_delta_angle)
            if avg_delta_angle < 30:  # 慢慢转过去
                return self.round_success()
            else:
                return self.round_wait(wait=0.1)
        else:
            self.ctx.controller.turn_by_angle(35 * self.turn_direction)
            return self.round_retry(status=MoveToNextLevel.STATUS_ENTRY_NOT_FOUND, wait=0.5)

    @node_from(from_name='画面识别转向入口')
    @operation_node(name='记录入口角度')
    def record_detect_angle(self) -> OperationRoundResult:
        """
        记录YOLO识别入口的方向
        :return:
        """
        screen = self.screenshot()
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        self.detect_entry_angle = mini_map_utils.analyse_angle(mm)

        # 其它的初始化
        self.feature_no_entry_times = 0

        return self.round_success()

    @node_from(from_name='画面识别转向入口', success=False, status=MoveToNextLevel.STATUS_ENTRY_NOT_FOUND)  # YOLO识别不到的话 可能是距离太远 往最开始的方向靠近试试
    @operation_node(name='画面识别失败后移动')
    def move_when_detect_fail(self) -> OperationRoundResult:
        """
        朝最初的方向前进
        :return:
        """
        self.detect_fail_times += 1
        if self.detect_fail_times >= 3:
            return self.round_fail(status=MoveToNextLevel.STATUS_ENTRY_NOT_FOUND)
        else:
            return self.move_by_detect_angle()

    @node_from(from_name='记录入口角度')
    @operation_node(name='图标识别下层入口')
    def check_by_feature_match(self) -> OperationRoundResult:
        """
        使用特征匹配识别当前有没有下层入口的图标
        :return:
        """
        screen = self.screenshot()
        type_list = sim_uni_screen_state.match_next_level_entry(self.ctx, screen)

        if len(type_list) == 0:
            self.feature_no_entry_times += 1
            if self.feature_no_entry_times <= 6:
                # 来回转动视角
                angle = (25 + 10 * self.feature_no_entry_times) * (1 if self.feature_no_entry_times % 2 == 0 else -1)
                self.ctx.controller.turn_by_angle(angle)
                return self.round_wait(wait=1)
            else:
                return self.round_success(status=MoveToNextLevel.STATUS_ENTRY_NOT_FOUND)
        else:
            self.turn_to_target(type_list[0])
            return self.round_success()

    @node_from(from_name='图标识别下层入口', status=MoveToNextLevel.STATUS_ENTRY_NOT_FOUND) # 图标识别不到的话 可能是距离太远 往YOLO识别的方向靠近
    @operation_node(name='往画面识别的入口移动')
    def move_by_detect_angle(self) -> OperationRoundResult:
        """
        特征匹配识别不到下层入口的图标 说明距离有点远
        先转到原来YOLO可以识别的视角 往前移动一段距离后重新尝试
        :return:
        """
        screen = self.screenshot()
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        current_angle = mini_map_utils.analyse_angle(mm)
        self.ctx.controller.turn_from_angle(current_angle, self.detect_entry_angle)

        time.sleep(1)
        # 先判断当前画面YOLO能否看到入口
        screen = self.screenshot()
        type_list = sim_uni_screen_state.match_next_level_entry(self.ctx, screen)
        if len(type_list) > 0:
            # 如果能识别 则说明离入口有点远 特征匹配失败 往前移动一段距离后重新尝试
            self.ctx.controller.move('w', 0.5)
        else:
            # 如果不能识别 则可能是之前移动超过了入口 往后一段距离后重新尝试
            self.ctx.controller.move('s', 0.5)

        return self.round_success()

    @node_from(from_name='图标识别下层入口')
    @operation_node(name='移动前初始化')
    def check_before_move(self) -> OperationRoundResult:
        """
        移动前的初始化
        :return:
        """
        screen = self.screenshot()
        self.check_interact_word(screen)

        return self.round_success()

    def check_interact_word(self, screen: MatLike) -> None:
        """
        识别当前出现的交互词
        :param screen: 游戏画面
        :return:
        """
        words = interact_utils.get_move_interact_words(self.ctx, screen, single_line=True)
        self.current_interact_word = words[0].data if len(words) > 0 and len(words[0].data) > 0 else ''
        if len(self.current_interact_word) > 0:
            self.existed_interact_word = True

    @node_from(from_name='移动前初始化')
    @operation_node(name='往图标识别的入口移动')
    def move_and_interact(self) -> OperationRoundResult:
        """
        移动并交互
        :return:
        """
        now = time.time()
        screen = self.screenshot()

        in_world = common_screen_state.is_normal_in_world(self.ctx, screen)

        if self.interacted:  # 交互之后 只识别当前画面是不是不在大世界
            if now - self.interact_time > 1:  # 交互之后超过1秒 而且画面还没有变化的话 就放弃这次的交互
                self.interacted = False
                return self.round_retry(status='交互后无反应')

            if not in_world:
                # 如果已经不在大世界画了 就认为成功了
                return self.round_success()
            else:
                return self.round_wait(wait=0.02)

        if self.ctx.controller.is_moving:
            if now - self.start_move_time > MoveToNextLevel.MOVE_TIME:
                self.ctx.controller.stop_moving_forward()
                self.move_times += 1

                if self.move_times >= 4:  # 正常情况不会连续移动这么多次都没有到下层入口 尝试脱困
                    self.ctx.controller.move(self.get_rid_direction, 1)
                    self.get_rid_direction = game_const.OPPOSITE_DIRECTION[self.get_rid_direction]
            else:
                interact = self.try_interact(screen)
                if interact is not None:
                    return interact
            return self.round_wait()
        else:
            type_list = sim_uni_screen_state.match_next_level_entry(self.ctx, screen)
            if len(type_list) == 0:  # 当前没有入口 随便旋转看看
                # 因为前面已经转向了入口 所以就算被遮挡 只要稍微转一点应该就能看到了
                angle = (25 + 10 * self.node_retry_times) * (1 if self.node_retry_times % 2 == 0 else -1)  # 来回转动视角
                self.ctx.controller.turn_by_angle(angle)
                self.move_times = 0  # 没有识别到就是没有移动
                return self.round_retry(MoveToNextLevel.STATUS_ENTRY_NOT_FOUND, wait=1)

            target = MoveToNextLevel.get_target_entry(type_list, self.ctx.sim_uni_challenge_config)

            self.move_towards_target(target)
            return self.round_wait(wait=0.1)

    def try_interact(self, screen: MatLike) -> Optional[OperationRoundResult]:
        """
        尝试交互
        :param screen:
        :return:
        """
        if self.can_interact(screen):
            self.ctx.controller.interact(interact_type=SrPcController.MOVE_INTERACT_TYPE)
            log.debug('尝试交互进入下一层')
            self.interacted = True
            self.interact_time = time.time()
            self.ctx.controller.stop_moving_forward()
            return self.round_wait(wait=0.1)
        else:
            return None

    def can_interact(self, screen: MatLike) -> bool:
        """
        当前是否可以交互
        :param screen: 屏幕截图
        :return:
        """
        self.check_interact_word(screen)
        return self.is_target_interact()

    def is_target_interact(self) -> bool:
        return (
                len(self.current_interact_word) > 0
                and str_utils.find_by_lcs(self.current_interact_word, gt('区域', 'ocr'), percent=0.1)
        )

    def move_towards_target(self, target: MatchResult):
        """
        朝目标移动 先让人物转向 让目标就在人物前方
        :param target:
        :return:
        """
        self.turn_to_target(target)
        self.ctx.controller.start_moving_forward()
        self.start_move_time = time.time()

    def turn_to_target(self, target: MatchResult, wait: float = 0.5):
        """
        朝目标转向
        :param target:
        :return:
        """
        angle_to_turn = self.get_angle_to_turn(target)
        self.ctx.controller.turn_by_angle(angle_to_turn)
        time.sleep(wait)

    def get_angle_to_turn(self, target: MatchResult) -> float:
        """
        获取需要转向的角度
        角度的定义与 game_controller.turn_by_angle 一致
        正数往右转 人物角度增加；负数往左转 人物角度减少
        :param target:
        :return:
        """
        # 小地图用的角度 正右方为0 顺时针为正
        mm_angle = cal_utils.get_angle_by_pts(MoveToNextLevel.CHARACTER_CENTER, target.center)

        return mm_angle - 270

    @node_from(from_name='往图标识别的入口移动')
    @operation_node(name='确认')
    def confirm(self) -> OperationRoundResult:
        """
        精英层的确认
        :return:
        """
        self.ctx.controller.stop_moving_forward()
        if self.level_type != SimUniLevelTypeEnum.ELITE.value:
            return self.round_success()
        screen = self.screenshot()
        if not common_screen_state.is_normal_in_world(self.ctx, screen):
            click_confirm = screen_utils.find_and_click_area(self.ctx, screen, '模拟宇宙', '前往下层-确认')
            if click_confirm == screen_utils.OcrClickResultEnum.OCR_CLICK_SUCCESS:
                return self.round_success(wait=1)
            elif click_confirm == screen_utils.OcrClickResultEnum.OCR_CLICK_NOT_FOUND:
                return self.round_success()
            else:
                return self.round_retry('点击确认失败', wait=0.25)
        else:
            return self.round_retry('在大世界页面')
