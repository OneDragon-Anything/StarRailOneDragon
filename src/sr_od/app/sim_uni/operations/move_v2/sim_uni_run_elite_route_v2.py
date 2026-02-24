from typing import Optional, Callable

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.log_utils import log
from one_dragon.yolo import detect_utils
from sr_od.app.sim_uni.operations.battle.sim_uni_fight_elite import SimUniFightElite
from sr_od.app.sim_uni.operations.event.sim_uni_reward import SimUniReward
from sr_od.app.sim_uni.operations.move_v1.sim_uni_move_to_enemy_by_mm import SimUniMoveToEnemyByMiniMap
from sr_od.app.sim_uni.operations.move_v1.sim_uni_move_to_interact_by_detect import SimUniMoveToInteractByDetect
from sr_od.app.sim_uni.operations.move_v2.sim_uni_run_route_base_v2 import SimUniRunRouteBaseV2
from sr_od.app.sim_uni.operations.sim_uni_exit import SimUniExit
from sr_od.app.sim_uni.sim_uni_const import SimUniLevelType, SimUniLevelTypeEnum
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.sr_map import mini_map_utils


class SimUniRunEliteRouteV2(SimUniRunRouteBaseV2):

    def __init__(self, ctx: SrContext, level_type: SimUniLevelType = SimUniLevelTypeEnum.ELITE.value,
                 max_reward_to_get: int = 0,
                 get_reward_callback: Optional[Callable[[int, int], None]] = None,):
        """
        区域-精英
        1. 检查小地图是否有红点 有就向红点移动
        2. 开怪
        3. 领取奖励
        4. 朝下层移动
        :param ctx: 上下文
        :param level_type: 楼层类型
        :param max_reward_to_get: 最多获取多少次奖励
        :param get_reward_callback: 获取奖励后的回调
        """
        SimUniRunRouteBaseV2.__init__(self, ctx, level_type=level_type)

        self.had_fight: bool = False  # 已经进行过战斗了
        self.had_reward: bool = False  # 已经拿过沉浸奖励了
        self.max_reward_to_get: int = max_reward_to_get  # 最多获取多少次奖励
        self.get_reward_callback: Optional[Callable[[int, int], None]] = get_reward_callback  # 获取奖励后的回调

    @operation_node(name='区域开始前', is_start_node=True)
    def before_route(self) -> OperationRoundResult:
        """
        路线开始前
        1. 按照小地图识别初始的朝向
        :return:
        """
        screen = self.last_screenshot
        self.check_angle(screen)
        return self.round_success()

    @node_from(from_name='区域开始前')
    @node_from(from_name='转动找目标')  # 转动后 重新开始识别
    @operation_node(name='识别小地图红点')
    def _check_red(self) -> OperationRoundResult:
        """
        检查小地图是否有红点
        :return:
        """
        if self.had_fight:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_HAD_FIGHT)
        screen = self.last_screenshot
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        mm_info = mini_map_utils.analyse_mini_map(mm)
        pos_list = mini_map_utils.get_enemy_pos(mm_info)
        if len(pos_list) == 0:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_NO_RED)
        else:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_RED)

    @node_from(from_name='识别小地图红点', status=SimUniRunRouteBaseV2.STATUS_NO_RED)
    @operation_node(name='无红点处理')
    def _move_forward_if_no_red(self) -> OperationRoundResult:
        """
        没红点时 又是没有战斗的情况
        - 重试进来没有精英怪
        - 精英怪太远了
        先尝试往前走一段距离 再进行后续识别 否则YOLO识别到入口 但老方法识别不到
        :return:
        """
        if not self.had_fight:
            self.ctx.controller.move('w', 2)

        return self.round_success()

    @node_from(from_name='识别小地图红点', status=SimUniRunRouteBaseV2.STATUS_WITH_RED)
    @operation_node(name='向红点移动')
    def _move_by_red(self) -> OperationRoundResult:
        """
        往小地图红点移动
        :return:
        """
        self.nothing_times = 0
        self.moved_to_target = True
        op = SimUniMoveToEnemyByMiniMap(self.ctx, no_attack=True, stop_after_arrival=True)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='向红点移动', status=SimUniMoveToEnemyByMiniMap.STATUS_ARRIVAL)
    @operation_node(name='进入战斗')
    def _enter_fight(self) -> OperationRoundResult:
        """
        移动到精英怪旁边之后 发起攻击
        :return:
        """
        op = SimUniFightElite(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='进入战斗')
    @operation_node(name='战斗后处理')
    def _after_fight(self) -> OperationRoundResult:
        """
        精英怪战斗后
        :return:
        """
        self.had_fight = True
        self.ctx.sim_uni_record.add_elite_times()
        self._turn_to_previous_angle()
        self.moved_to_target = True  # 与精英战斗后 该识别的目标都在附近了 就算识别不到也不需要往前走了

        return self.round_success()

    @node_from(from_name='识别小地图红点', status=SimUniRunRouteBaseV2.STATUS_HAD_FIGHT)
    @node_from(from_name='战斗后处理')
    @node_from(from_name='无红点处理') # 没红点时 识别沉浸奖励装置
    @node_from(from_name='识别移动超时脱困')
    @operation_node(name='识别沉浸奖励')
    def _detect_reward(self) -> OperationRoundResult:
        if self.had_reward:
            log.debug('领取过沉浸奖励')
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_NO_NEED_REWARD)

        # 调试时候强制走到沉浸奖励
        if not self.ctx.env_config.is_debug and self.max_reward_to_get == 0:
            log.debug('不需要领取沉浸奖励')
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_NO_NEED_REWARD)

        # self._view_down()  # 入口和下层奖励 都比较大 应该不需要视角往下
        screen = self.last_screenshot

        frame_result = self.ctx.yolo_detector.sim_uni_yolo.run(screen)

        detected: bool = False
        for result in frame_result.results:
            if result.detect_class.class_category == '模拟宇宙沉浸奖励':
                detected = True
                break

        if detected:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_DETECT_REWARD)
        else:
            if self.ctx.env_config.is_debug:
                if self.nothing_times == 1:
                    self.save_screenshot()
                cv2_utils.show_image(detect_utils.draw_detections(frame_result), win_name='SimUniRunEliteRouteV2')

            if self.had_fight and self.nothing_times <= 11:  # 战斗后 一定要找到沉浸奖励
                return self.round_success(SimUniRunRouteBaseV2.STATUS_NO_DETECT_REWARD)
            else:  # 重进的情况(没有战斗) 或者 找不到沉浸奖励太多次了 就不找了
                log.debug('没有战斗 或者 找不到沉浸奖励太多次了')
                return self.round_success(SimUniRunRouteBaseV2.STATUS_NO_NEED_REWARD)

    @node_from(from_name='识别沉浸奖励', status=SimUniRunRouteBaseV2.STATUS_WITH_DETECT_REWARD)
    @operation_node(name='朝沉浸奖励移动')
    def _move_to_reward(self) -> OperationRoundResult:
        """
        朝沉浸装置移动
        :return:
        """
        # 按照目前的固定布局 从精英怪走向沉浸奖励后 下层入口必定往左转更快发现
        self.turn_direction_when_nothing = -1

        self.nothing_times = 0
        self.moved_to_target = True
        op = SimUniMoveToInteractByDetect(self.ctx,
                                          interact_class='模拟宇宙沉浸奖励',
                                          interact_word='沉浸奖励',
                                          interact_during_move=True)
        op_result = op.execute()
        return self.round_by_op_result(op_result, wait=1 if op_result.success else 0)  # 稍微等待画面加载

    @node_from(from_name='朝沉浸奖励移动', success=False, status=SrOperation.STATUS_TIMEOUT)  # 识别移动超时的话 尝试脱困
    @operation_node(name='识别移动超时脱困')
    def after_detect_timeout(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.after_detect_timeout(self)

    @node_from(from_name='朝沉浸奖励移动', status=SimUniMoveToInteractByDetect.STATUS_INTERACT)
    @operation_node(name='领取沉浸奖励')
    def _get_reward(self) -> OperationRoundResult:
        """
        领取沉浸奖励
        :return:
        """
        self.had_fight = True  # 能交互沉浸奖励的话 说明精英怪已经死了
        self.had_reward = True
        self.detect_move_timeout_times = 0
        op = SimUniReward(self.ctx, self.max_reward_to_get, self.get_reward_callback)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='识别沉浸奖励', status=SimUniRunRouteBaseV2.STATUS_NO_NEED_REWARD)  # 识别不到沉浸奖励 尝试识别下层入口
    @node_from(from_name='领取沉浸奖励')  # 领取奖励后向下层移动
    @node_from(from_name='朝沉浸奖励移动', success=False)  # 走不到沉浸奖励时 尝试识别下层入口
    @operation_node(name='识别下层入口')
    def check_next_entry(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.check_next_entry(self)

    @node_from(from_name='识别下层入口', status=SimUniRunRouteBaseV2.STATUS_WITH_ENTRY)
    @operation_node(name='向下层移动')
    def move_to_next(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.move_to_next(self)

    @node_from(from_name='识别下层入口', status=SimUniRunRouteBaseV2.STATUS_NO_ENTRY)  # 识别不到下层入口
    @node_from(from_name='识别沉浸奖励', status=SimUniRunRouteBaseV2.STATUS_NO_DETECT_REWARD)   # 需要领取沉浸奖励 而又找不到沉浸奖励时 也转向重新开始
    @operation_node(name='转动找目标')
    def turn_when_nothing(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.turn_when_nothing(self)

    @node_from(from_name='识别下层入口', status=SimUniRunRouteBaseV2.STATUS_BOSS_EXIT)
    @operation_node(name='首领后退出')
    def _boss_exit(self) -> OperationRoundResult:
        """
        战胜首领后退出
        :return:
        """
        op = SimUniExit(self.ctx)
        return self.round_by_op_result(op.execute())
