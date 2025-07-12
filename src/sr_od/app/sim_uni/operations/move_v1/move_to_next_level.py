import time

import numpy as np
from cv2.typing import MatLike
from typing import ClassVar, Optional, List

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.utils import cal_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import SimUniLevelType, level_type_from_id, SimUniLevelTypeEnum
from sr_od.app.sim_uni.sim_uni_route import SimUniRoute
from sr_od.config import game_const
from sr_od.context.sr_context import SrContext
from sr_od.context.sr_pc_controller import SrPcController
from sr_od.operations.interact import interact_utils
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state
from sr_od.sr_map import mini_map_utils
from sr_od.sr_map.mini_map_info import MiniMapInfo


class MoveToNextLevel(SrOperation):

    MOVE_TIME: ClassVar[float] = 1.5  # 每次移动的时间
    CHARACTER_CENTER: ClassVar[Point] = Point(960, 920)  # 界面上人物的中心点 取了脚底

    NEXT_CONFIRM_BTN: ClassVar[Rect] = Rect(1006, 647, 1330, 697)  # 确认按钮

    STATUS_ENTRY_NOT_FOUND: ClassVar[str] = '未找到下一层入口'
    STATUS_ENCOUNTER_FIGHT: ClassVar[str] = '遭遇战斗'

    def __init__(self, ctx: SrContext,
                 level_type: SimUniLevelType,
                 route: Optional[SimUniRoute] = None,
                 current_pos: Optional[Point] = None,
                 config: Optional[SimUniChallengeConfig] = None,
                 random_turn: bool = True):
        """
        朝下一层入口走去 并且交互
        :param ctx:
        :param level_type: 当前楼层的类型 精英层的话 有可能需要确定
        :param route: 当前使用路线
        :param current_pos: 当前人物的位置
        :param config: 挑战配置
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('向下一层移动')),)
        self.level_type: SimUniLevelType = level_type
        self.route: SimUniRoute = route
        self.current_pos: Optional[Point] = current_pos
        self.config: Optional[SimUniChallengeConfig] = ctx.sim_uni_challenge_config if config is None else config
        self.random_turn: bool = random_turn  # 随机转动找入口

    def handle_init(self) -> Optional[OperationRoundResult]:
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """
        self.is_moving = False  # 是否正在移动
        self.interacted = False  # 是否已经交互了
        self.start_move_time: float = 0  # 开始移动的时间
        self.move_times: int = 0  # 连续移动的次数
        self.get_rid_direction: str = 'a'  # 脱困方向
        if self.route is None or self.route.next_pos_list is None or len(self.route.next_pos_list) == 0:
            self.next_pos = None
        else:
            avg_pos_x = np.mean([pos.x for pos in self.route.next_pos_list], dtype=np.uint16)
            avg_pos_y = np.mean([pos.y for pos in self.route.next_pos_list], dtype=np.uint16)
            self.next_pos = Point(avg_pos_x, avg_pos_y)

        return None

    @operation_node(name='转向入口', node_max_retry_times=10, is_start_node=True)
    def _turn_to_next(self) -> OperationRoundResult:
        """
        朝入口转向 方便看到所有的入口
        :return:
        """
        if self.route is None:  # 不是使用配置路线时 不需要先转向
            return self.round_success()
        if self.current_pos is None or self.next_pos is None:
            if self.ctx.env_config.is_debug:
                return self.round_fail('未配置下层入口')
            else:
                return self.round_success()
        screen = self.screenshot()

        if not common_screen_state.is_normal_in_world(self.ctx, screen):
            log.error('找下层入口时进入战斗 请反馈给作者 %s', self.route.display_name)
            if self.ctx.env_config.is_debug:
                return self.round_fail(MoveToNextLevel.STATUS_ENCOUNTER_FIGHT)
            op = SimUniEnterFight(self.ctx, self.config)
            op_result = op.execute()
            if op_result.success:
                return self.round_wait()
            else:
                return self.round_retry()

        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        mm_info: MiniMapInfo = mini_map_utils.analyse_mini_map(mm)
        self.ctx.controller.turn_by_pos(self.current_pos, self.next_pos, mm_info.angle)

        return self.round_success(wait=0.5)  # 等待转动完成

    @node_from(from_name='转向入口')
    @operation_node(name='移动交互')
    def _move_and_interact(self) -> OperationRoundResult:
        screen = self.screenshot()

        in_world = common_screen_state.is_normal_in_world(self.ctx, screen)

        if not in_world:
            if self.interacted:
                # 兜底 - 如果已经不在大世界画面且又交互过了 就认为成功了
                return self.round_success()
            else:
                log.error('找下层入口时进入战斗 请反馈给作者 %s', '第九宇宙' if self.route is None else self.route.display_name)
                if self.ctx.env_config.is_debug:
                    return self.round_fail(MoveToNextLevel.STATUS_ENCOUNTER_FIGHT)
                op = SimUniEnterFight(self.ctx, self.config)
                op_result = op.execute()
                if op_result.success:
                    return self.round_wait()
                else:
                    return self.round_retry()

        interact = self._try_interact(screen)
        if interact is not None:
            return interact

        if self.is_moving:
            if time.time() - self.start_move_time > MoveToNextLevel.MOVE_TIME:
                self.ctx.controller.stop_moving_forward()
                self.is_moving = False
                self.move_times += 1

            if self.move_times > 0 and self.move_times % 4 == 0:  # 正常情况不会连续移动这么多次都没有到下层入口 尝试脱困
                self.ctx.controller.move(self.get_rid_direction, 1)
                self.get_rid_direction = game_const.OPPOSITE_DIRECTION[self.get_rid_direction]
            return self.round_wait()
        else:
            type_list = sim_uni_screen_state.match_next_level_entry(self.ctx, screen)
            if len(type_list) == 0:  # 当前没有入口 随便旋转看看
                if self.random_turn:
                    # 因为前面已经转向了入口 所以就算被遮挡 只要稍微转一点应该就能看到了
                    angle = (25 + 10 * self.node_retry_times) * (1 if self.node_retry_times % 2 == 0 else -1)  # 来回转动视角
                else:
                    angle = 35
                self.ctx.controller.turn_by_angle(angle)
                return self.round_retry(MoveToNextLevel.STATUS_ENTRY_NOT_FOUND, wait=1)

            target = self.get_target_entry(type_list, self.config)

            self._move_towards(target)
            return self.round_wait(wait=0.1)

    @staticmethod
    def get_target_entry(type_list: List[MatchResult], config: Optional[SimUniChallengeConfig]) -> MatchResult:
        """
        获取需要前往的入口
        :param type_list: 入口类型
        :param config: 模拟宇宙挑战配置
        :return:
        """
        idx = MoveToNextLevel.match_best_level_type(type_list, config)
        return type_list[idx]

    @staticmethod
    def match_best_level_type(type_list: List[MatchResult], config: Optional[SimUniChallengeConfig]) -> int:
        """
        根据优先级 获取最优的入口类型
        :param type_list: 入口类型 保证长度大于0
        :param config: 挑战配置
        :return: 下标
        """
        if config is None:
            return 0

        for priority_id in config.level_type_priority:
            priority_level_type = level_type_from_id(priority_id)
            if priority_level_type is None:
                continue
            for idx, type_pos in enumerate(type_list):
                if type_pos.data == priority_level_type:
                    return idx

        return 0

    def _move_towards(self, target: MatchResult):
        """
        朝目标移动 先让人物转向 让目标就在人物前方
        :param target:
        :return:
        """
        angle_to_turn = self._get_angle_to_turn(target)
        self.ctx.controller.turn_by_angle(angle_to_turn)
        time.sleep(0.5)
        self.ctx.controller.start_moving_forward()
        self.start_move_time = time.time()
        self.is_moving = True

    def _get_angle_to_turn(self, target: MatchResult) -> float:
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

    def _try_interact(self, screen: MatLike) -> Optional[OperationRoundResult]:
        """
        尝试交互
        :param screen:
        :return:
        """
        if self._can_interact(screen):
            self.ctx.controller.interact(interact_type=SrPcController.MOVE_INTERACT_TYPE)
            log.debug('尝试交互进入下一层')
            self.interacted = True
            self.ctx.controller.stop_moving_forward()
            return self.round_wait(wait=0.1)
        else:
            return None

    def _can_interact(self, screen: MatLike) -> bool:
        """
        当前是否可以交互
        :param screen: 屏幕截图
        :return:
        """
        pos = interact_utils.check_move_interact(self.ctx, screen, '区域', single_line=True)
        return pos is not None

    @node_from(from_name='移动交互')
    @operation_node(name='确认')
    def _confirm(self) -> OperationRoundResult:
        """
        精英层的确认
        :return:
        """
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
