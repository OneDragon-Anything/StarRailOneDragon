import time

import random
from cv2.typing import MatLike
from typing import ClassVar, List

from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.yolo import detect_utils
from one_dragon.yolo.detect_utils import DetectObjectResult
from sr_od.app.sim_uni.operations import sim_uni_move_utils
from sr_od.app.sim_uni.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state, battle_screen_state
from sr_od.sr_map import mini_map_utils


class SimUniMoveToEnemyByDetect(SrOperation):

    STATUS_ARRIVAL: ClassVar[str] = '已到达'
    STATUS_FIGHT: ClassVar[str] = '遭遇战斗'
    STATUS_NO_ENEMY: ClassVar[str] = '识别不到敌人'

    def __init__(self, ctx: SrContext):
        """
        根据画面识别怪的位置 朝怪移动。
        进入之前 应该确保当前朝向能识别到怪，本操作不会旋转去找怪
        停下来的条件有
        - 找不到怪
        - 被怪物锁定
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name=gt('向怪物移动'))

        self.no_enemy_times: int = 0  # 没有发现敌人的次数
        self.start_move_time: float = 0  # 开始移动的时间

        self.last_debug_time: float = 0

    @operation_node(name='移动', timeout_seconds=20, is_start_node=True)  # 理论上移动目标都比较近 不可能20秒还没有到达
    def move(self) -> OperationRoundResult:
        now = time.time()
        screen = self.screenshot()

        # 不在大世界 可能被袭击了
        if not common_screen_state.is_normal_in_world(self.ctx, screen):
            return self.enter_battle(False)

        # 被怪锁定了
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        if mini_map_utils.is_under_attack(mm):
            return self.enter_battle(True)

        # 移动2秒后 如果丢失了目标 停下来
        if self.ctx.controller.is_moving and now - self.start_move_time >= 2 and self.no_enemy_times > 0:
            self.ctx.controller.stop_moving_forward()
            return self.round_wait()

        # 进行目标识别判断后续动作
        return self.detect_screen(screen, now)

    def enter_battle(self, in_world: bool) -> OperationRoundResult:
        """
        进入战斗
        :return:
        """
        if in_world:
            state = common_screen_state.ScreenState.NORMAL_IN_WORLD.value
        else:
            state = battle_screen_state.ScreenState.BATTLE.value
        op = SimUniEnterFight(self.ctx, first_state=state)
        op_result = op.execute()
        if op_result.success:
            return self.round_success(SimUniMoveToEnemyByDetect.STATUS_FIGHT)
        else:
            return self.round_by_op_result(op_result, retry_on_fail=True)

    def detect_screen(self, screen: MatLike, screenshot_time: float) -> OperationRoundResult:
        """
        对画面进行识别 根据结果进行后续判断
        :param screen: 游戏画面
        :param screenshot_time: 截图时间
        :return:
        """
        frame_result = self.ctx.yolo_detector.sim_uni_combat_detect(screen, screenshot_time)
        normal_enemy_result = []
        can_attack: bool = False
        for result in frame_result.results:
            if result.detect_class.class_category == '普通怪':
                normal_enemy_result.append(result)
            elif result.detect_class.class_category in ['界面提示被锁定', '界面提示可攻击']:
                can_attack = True

        if self.ctx.env_config.is_debug:
            # cv2_utils.show_image(detect_utils.draw_detections(frame_result), win_name='SimUniMoveToEnemyByDetect')
            if len(frame_result.results) > 3 and random.random() < 0.5:
                self.save_screenshot()

        if can_attack:
            return self.enter_battle(True)
        elif len(normal_enemy_result) > 0:
            return self.handle_enemy(normal_enemy_result)
        else:
            return self.handle_no_enemy()

    def handle_no_enemy(self) -> OperationRoundResult:
        """
        处理当前画面没有中没有怪的情况
        :return:
        """
        self.no_enemy_times += 1
        if self.no_enemy_times >= 9:
            return self.round_fail(SimUniMoveToEnemyByDetect.STATUS_NO_ENEMY)

        # 第一次向右转一点 后续就在固定范围内晃动
        if self.no_enemy_times == 1:
            angle = 15
        else:
            angle = -30 if self.no_enemy_times % 2 == 0 else 30

        self.ctx.controller.turn_by_angle(angle)
        return self.round_wait(SimUniMoveToEnemyByDetect.STATUS_NO_ENEMY, wait=0.5)

    def handle_enemy(self, enemy_pos_list: List[DetectObjectResult]) -> OperationRoundResult:
        """
        处理有敌人的情况
        :param enemy_pos_list: 识别的敌人列表
        :return:
        """
        self.no_enemy_times = 0
        enemy = enemy_pos_list[0]  # 先固定找第一个
        sim_uni_move_utils.turn_to_detected_object(self.ctx, enemy)
        self.ctx.controller.start_moving_forward()
        self.start_move_time = time.time()
        return self.round_wait()

    def after_operation_done(self, result: OperationResult):
        """
        无论以哪种方式结束 都停止移动
        :param result:
        :return:
        """
        SrOperation.after_operation_done(self, result)
        self.ctx.controller.stop_moving_forward()
