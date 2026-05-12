import time

from cv2.typing import MatLike
from typing import ClassVar, Optional

from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.sim_universe import sim_uni_screen_state
from sr_od.application.sim_universe.operations.move_v1.sim_uni_move_to_interact_by_detect import SimUniMoveToInteractByDetect
from sr_od.application.sim_universe.operations.move_v2.sim_uni_move_to_next_level_v3 import MoveToNextLevelV3
from sr_od.application.sim_universe.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.application.sim_universe.sim_uni_data import SimUniLevelType, SimUniLevelTypeEnum
from sr_od.config import game_const
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state
from sr_od.sr_map import mini_map_utils


class SimUniRunRouteBaseV2(SrOperation):

    STATUS_FIGHT: ClassVar[str] = '遭遇战斗'
    STATUS_WITH_RED: ClassVar[str] = '小地图有红点'
    STATUS_NO_RED: ClassVar[str] = '小地图无红点'
    STATUS_WITH_MM_EVENT: ClassVar[str] = '小地图有事件'
    STATUS_NO_MM_EVENT: ClassVar[str] = '小地图无事件'
    STATUS_WITH_DETECT_EVENT: ClassVar[str] = '识别到事件'
    STATUS_NO_DETECT_EVENT: ClassVar[str] = '识别不到事件'
    STATUS_WITH_ENEMY: ClassVar[str] = '识别到敌人'
    STATUS_NO_ENEMY: ClassVar[str] = '识别不到敌人'
    STATUS_WITH_ENTRY: ClassVar[str] = '识别到下层入口'
    STATUS_NO_ENTRY: ClassVar[str] = '识别不到下层入口'
    STATUS_NOTHING: ClassVar[str] = '识别不到任何内容'
    STATUS_BOSS_EXIT: ClassVar[str] = '首领后退出'
    STATUS_HAD_EVENT: ClassVar[str] = '已处理事件'
    STATUS_HAD_FIGHT: ClassVar[str] = '已进行战斗'
    STATUS_NO_NEED_REWARD: ClassVar[str] = '无需沉浸奖励'
    STATUS_WITH_DETECT_REWARD: ClassVar[str] = '识别到沉浸奖励'
    STATUS_NO_DETECT_REWARD: ClassVar[str] = '识别不到沉浸奖励'
    STATUS_WITH_DANGER: ClassVar[str] = '被敌人锁定'
    STATUS_WRONG_LEVEL_TYPE: ClassVar[str] = '楼层识别错误'

    def __init__(self, ctx: SrContext, level_type: SimUniLevelType):
        SrOperation.__init__(self, ctx=ctx, op_name=gt(f'区域-{level_type.type_name}-v2', 'ui'))
        self.level_type: SimUniLevelType = level_type  # 楼层类型
        self.moved_to_target: bool = False  # 是否已经产生了朝向目标的移动
        self.nothing_times: int = 0  # 识别不到任何内容的次数
        self.previous_angle: float = 0  # 之前的朝向 识别到目标时应该记录下来 后续可以在这个方向附近找下一个目标
        self.turn_direction_when_nothing: int = 1  # 没有目标时候的转动方向 正数向右 负数向左
        self.detect_move_timeout_times: int = 0  # 识别移动的超时失败次数
        self.check_next_entry_knn: float = 0.5  # 特征匹配下层入口的阈值 越小精度越高
        self.detect_entry: bool = False  # 识别到入口 只有yolo识别的才认可
        self.next_entry_direction: int = -1  # 下层入口的方向 1=右边 -1=左边
        self.move_to_next_fail_times: int = 0  # 向下层移动失败的次数
        self.move_to_next_get_rid_direction: str = 'a'  # 向下层移动的脱困方向

    def check_angle(self, screen: MatLike):
        """
        检测并更新角度
        :return:
        """
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        self.previous_angle = mini_map_utils.analyse_angle(mm)

    def _turn_to_previous_angle(self, screen: Optional[MatLike] = None) -> OperationRoundResult:
        """
        战斗后的处理 先转到原来的朝向 再取找下一个目标
        :return:
        """
        if screen is None:
            screen = self.screenshot()
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        angle = mini_map_utils.analyse_angle(mm)
        self.ctx.controller.turn_from_angle(angle, self.previous_angle)
        self.moved_to_target = False
        return self.round_success(wait=0.2)

    def check_next_entry(self) -> OperationRoundResult:
        """
        找下层入口 主要判断能不能找到
        :return:
        """
        if self.level_type == SimUniLevelTypeEnum.BOSS.value:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_BOSS_EXIT)
        self._view_up()
        screen: MatLike = self.screenshot()
        entry_list = sim_uni_screen_state.match_next_level_entry(self.ctx, screen, knn_distance_percent=self.check_next_entry_knn)
        if len(entry_list) == 0:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_NO_ENTRY)
        else:
            self.nothing_times = 0
            left = 0
            right = 0
            for entry in entry_list:
                if entry.center.x < game_const.STANDARD_CENTER_POS.x:
                    left += 1
                elif entry.center.x > game_const.STANDARD_CENTER_POS.x:
                    right += 1
            if left > right:
                self.next_entry_direction = -1
            elif right > left:
                self.next_entry_direction = 1
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_ENTRY)

    def move_to_next(self):
        """
        朝下层移动
        :return:
        """
        self.nothing_times = 0
        self.moved_to_target = True

        self._view_up()
        op = MoveToNextLevelV3(self.ctx, level_type=self.level_type, turn_direction=self.next_entry_direction)
        op_result = op.execute()

        if not op_result.success:
            self.move_to_next_fail_times += 1
            if self.move_to_next_fail_times >= 3:  # 向下层移动失败过多时 尝试脱困
                self.ctx.controller.move(self.move_to_next_get_rid_direction, 1)
                self.move_to_next_get_rid_direction = game_const.OPPOSITE_DIRECTION[self.move_to_next_get_rid_direction]

        return self.round_by_op_result(op_result)

    def move_to_next_by_detect(self):
        """
        按YOLO识别结果 朝下层移动
        只适合中途没有其它交互的楼层使用
        :return:
        """
        self.nothing_times = 0
        self.moved_to_target = True

        self._view_up()
        op = SimUniMoveToInteractByDetect(self.ctx,
                                          interact_class='模拟宇宙下层入口',
                                          interact_word='区域',
                                          interact_during_move=True)
        return self.round_by_op_result(op.execute())

    def turn_when_nothing(self) -> OperationRoundResult:
        """
        当前画面识别不到任何内容时候 转动一下
        :return:
        """
        self.nothing_times += 1
        log.debug('无内容次数 %d', self.nothing_times)

        if not self.moved_to_target:
            # 还没有产生任何移动的情况下 又识别不到任何内容 则可能是距离较远导致。先尝试往前走1秒
            self.ctx.controller.move('w', 1)
            self.moved_to_target = True
            return self.round_success()

        if self.nothing_times >= 23:
            return self.round_fail(SimUniRunRouteBaseV2.STATUS_NOTHING)

        # angle = (25 + 10 * self.nothing_times) * (1 if self.nothing_times % 2 == 0 else -1)  # 来回转动视角
        # 由于攻击之后 人物可能朝反方向了 因此要转动多一点
        # 不要被360整除 否则转一圈之后还是被人物覆盖了看不到
        angle = 35 * self.turn_direction_when_nothing
        self.ctx.controller.turn_by_angle(angle)
        time.sleep(0.5)

        if self.nothing_times % 11 == 0:
            # 识别不到内容太多次 判断楼层类型是否有问题
            screen = self.screenshot()
            if not self.is_level_type_correct(screen):
                return self.round_fail(SimUniRunRouteBaseV2.STATUS_WRONG_LEVEL_TYPE)

            # 大概转了一圈之后还没有找到东西 就往之前的方向走一点
            self.moved_to_target = False
            return self._turn_to_previous_angle()

        return self.round_success()

    def _view_down(self):
        """
        视角往下移动 方便识别目标
        :return:
        """
        if self.ctx.detect_info.view_down:
            return
        self.ctx.controller.turn_down(25)
        self.ctx.detect_info.view_down = True
        time.sleep(0.2)

    def _view_up(self):
        """
        视角往上移动 恢复原来的视角
        :return:
        """
        if not self.ctx.detect_info.view_down:
            return
        self.ctx.controller.turn_down(-25)
        self.ctx.detect_info.view_down = False
        time.sleep(0.2)

    def after_detect_timeout(self) -> OperationRoundResult:
        """
        识别移动超时后的处理
        1. 可能被可破坏物卡住了
        2. 被路挡住了
        :return:
        """
        self.detect_move_timeout_times += 1
        if self.detect_move_timeout_times >= 4:
            return self.round_fail(status=SrOperation.STATUS_TIMEOUT)

        # 先尝试攻击破坏物
        op = SimUniEnterFight(self.ctx, disposable=True, first_state=common_screen_state.ScreenState.NORMAL_IN_WORLD.value)
        op_result = op.execute()
        if not op_result.success:
            return self.round_by_op_result(op_result)

        # 看上一帧识别结果
        frame_result = self.ctx.yolo_detector.last_detect_result
        min_x = self.ctx.project_config.screen_standard_width
        max_x = 0
        for r in frame_result.results:
            if r.x1 < min_x:
                min_x = r.x1
            if r.x2 > max_x:
                max_x = r.x2

        mid_x = self.ctx.project_config.screen_standard_width // 2
        if min_x >= mid_x:  # 都在右边
            to_right = True
        elif max_x <= mid_x:  # 都在左边
            to_right = False
        elif mid_x - min_x >= max_x - mid_x:  # 左边偏移更多
            to_right = False
        else:  # 右边偏移更多
            to_right = True

        if to_right:
            self.ctx.controller.move('d', 1)
        else:
            self.ctx.controller.move('a', 1)

        return self.round_success()

    def is_level_type_correct(self, screen: MatLike) -> bool:
        """
        当前识别的楼层类型是否正确
        :param screen: 游戏画面
        :return:
        """
        level_type = sim_uni_screen_state.get_level_type(self.ctx, screen)
        return level_type is not None and self.level_type.type_id == level_type.type_id


