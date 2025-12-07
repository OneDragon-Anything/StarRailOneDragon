import time

import numpy as np
from cv2.typing import MatLike
from typing import List

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cal_utils
from one_dragon.utils.log_utils import log
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations import sim_uni_move_utils
from sr_od.app.sim_uni.operations.move_v1.sim_uni_move_to_enemy_by_detect import SimUniMoveToEnemyByDetect
from sr_od.app.sim_uni.operations.move_v1.sim_uni_move_to_enemy_by_mm import SimUniMoveToEnemyByMiniMap
from sr_od.app.sim_uni.operations.move_v2.sim_uni_run_route_base_v2 import SimUniRunRouteBaseV2
from sr_od.app.sim_uni.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.app.sim_uni.sim_uni_const import SimUniLevelType, SimUniLevelTypeEnum
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.technique import UseTechnique
from sr_od.screen_state import common_screen_state
from sr_od.sr_map import mini_map_utils
from sr_od.sr_map.mini_map_info import MiniMapInfo


class SimUniRunCombatRouteV2(SimUniRunRouteBaseV2):

    def __init__(self, ctx: SrContext, level_type: SimUniLevelType = SimUniLevelTypeEnum.COMBAT.value):
        """
        区域-战斗
        1. 检测地图是否有红点
        2. 如果有红点 移动到最近的红点 并进行攻击。攻击一次后回到步骤1判断。
        3. 如果没有红点 识别敌对物种位置，向最大的移动，并进行攻击。攻击一次后回到步骤1判断。
        4. 如果没有红点也没有识别到敌对物种，检测下层入口位置，发现后进入下层移动。未发现则选择视角返回步骤1判断。
        """
        SimUniRunRouteBaseV2.__init__(self, ctx, level_type=level_type)

        self.last_state: str = ''  # 上一次的画面状态
        self.current_state: str = ''  # 这一次的画面状态

    @operation_node(name='区域开始前', is_start_node=True)
    def before_route(self) -> OperationRoundResult:
        """
        路线开始前
        1. 按照小地图识别初始的朝向
        2. 如果是 buff秘技 且需要 秘技开怪，先使用秘技
        :return:
        """
        screen = self.last_screenshot
        self.check_angle(screen)

        if (self.ctx.sim_uni_challenge_config.technique_fight
                and self.ctx.team_info.is_buff_technique
                and not self.ctx.tech_used_in_lasting):
            op = UseTechnique(self.ctx,
                              max_consumable_cnt=self.ctx.sim_uni_challenge_config.max_consumable_cnt,
                              need_check_point=True,  # 检查秘技点是否足够 可以在没有或者不能用药的情况加快判断
                              trick_snack=self.ctx.game_config.use_quirky_snacks,
                              )
            return self.round_by_op_result(op.execute())

        return self.round_success()

    @node_from(from_name='区域开始前')
    @node_from(from_name='识别移动超时脱困')  # 脱困后重新识别
    @node_from(from_name='战斗后处理')  # 战斗后重新识别
    @node_from(from_name='转动找目标')  # 转动后重新识别
    @operation_node(name='画面识别')
    def check_screen(self) -> OperationRoundResult:
        """
        检测屏幕
        :return:
        """
        screen = self.last_screenshot

        # 为了保证及时攻击 外层仅判断是否在大世界画面 非大世界画面时再细分处理
        self.current_state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            in_world=True, battle=True)
        log.debug('当前画面 %s', self.current_state)

        if self.current_state == common_screen_state.ScreenState.NORMAL_IN_WORLD.value:
            return self._handle_in_world(screen)
        else:
            return self._handle_not_in_world(screen)

    def _handle_in_world(self, screen: MatLike) -> OperationRoundResult:
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        mm_info: MiniMapInfo = mini_map_utils.analyse_mini_map(mm)

        pos, _ = mini_map_utils.get_closest_enemy_pos(mm_info)

        if pos is None:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_NO_RED)
        else:
            if self.ctx.env_config.is_debug:  # 红点已经比较成熟 调试时强制使用yolo
                return self.round_success(status=SimUniRunRouteBaseV2.STATUS_NO_RED)
            self.previous_angle = cal_utils.get_angle_by_pts(Point(0, 0), pos)  # 记录有目标的方向
            log.debug(f'根据红点记录角度 {self.previous_angle}')
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_RED)

    @node_from(from_name='画面识别', status=SimUniRunRouteBaseV2.STATUS_WITH_RED)  # 小地图有红点 就按红点移动
    @operation_node(name='向红点移动')
    def _move_by_red(self) -> OperationRoundResult:
        """
        朝小地图红点走去
        :return:
        """
        self.nothing_times = 0
        self.moved_to_target = True
        op = SimUniMoveToEnemyByMiniMap(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='向红点移动', status=SimUniMoveToEnemyByMiniMap.STATUS_ARRIVAL)  # 红点移动到达后
    @node_from(from_name='识别敌人', status=SimUniRunRouteBaseV2.STATUS_WITH_DANGER)  # 识别到被锁定也进入战斗
    @operation_node(name='进入战斗')
    def _enter_fight(self) -> OperationRoundResult:
        op = SimUniEnterFight(self.ctx, first_state=common_screen_state.ScreenState.NORMAL_IN_WORLD.value)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='进入战斗')
    @node_from(from_name='画面识别', status=SimUniRunRouteBaseV2.STATUS_FIGHT)  # 其它可能会进入战斗的情况
    @node_from(from_name='向红点移动', status=SimUniMoveToEnemyByMiniMap.STATUS_FIGHT)  # 其它可能会进入战斗的情况
    @node_from(from_name='向敌人移动', status=SimUniMoveToEnemyByDetect.STATUS_FIGHT)  # 其它可能会进入战斗的情况
    @operation_node(name='战斗后处理')
    def after_fight(self) -> OperationRoundResult:
        return self._turn_to_previous_angle()

    def _handle_not_in_world(self, screen: MatLike) -> OperationRoundResult:
        """
        不在大世界的场景 无论是什么 都可以交给 SimUniEnterFight 处理
        :param screen:
        :return:
        """
        op = SimUniEnterFight(self.ctx, config=self.ctx.sim_uni_challenge_config)
        op_result = op.execute()
        if op_result.success:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_FIGHT)
        else:
            return self.round_by_op_result(op_result)

    @node_from(from_name='画面识别', status=SimUniRunRouteBaseV2.STATUS_NO_RED)  # 小地图没有红点 就在画面上找敌人
    @operation_node(name='识别敌人', screenshot_before_round=False)
    def _detect_screen(self) -> OperationRoundResult:
        """
        没有红点时 对画面进行目标识别
        :return:
        """
        self.detect_entry = False
        self._view_down()
        screenshot_time = time.time()
        screen: MatLike = self.screenshot()

        frame_result = self.ctx.yolo_detector.sim_uni_combat_detect(screen, screenshot_time)

        enemy_angles: List[float] = []
        entry_angles: List[float] = []
        inactive_entry_angles: List[float] = []
        with_danger: bool = False
        for result in frame_result.results:
            delta_angle = sim_uni_move_utils.delta_angle_to_detected_object(result)
            if result.detect_class.class_category == '普通怪':
                enemy_angles.append(delta_angle)
            elif result.detect_class.class_category == '模拟宇宙下层入口':
                entry_angles.append(delta_angle)
                self.detect_entry = True
            elif result.detect_class.class_category == '模拟宇宙下层入口未激活':
                inactive_entry_angles.append(delta_angle)
            elif result.detect_class.class_category == '界面提示被锁定':
                with_danger = True

        if with_danger:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_DANGER)
        elif len(enemy_angles) > 0:
            mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
            angle = mini_map_utils.analyse_angle(mm)
            avg_delta_angle = np.mean(enemy_angles)
            self.previous_angle = cal_utils.angle_add(angle, avg_delta_angle)
            log.debug(f'根据YOLO记录角度 识别怪角度 {enemy_angles}, 当前角度 {angle} 最终记录角度 {self.previous_angle}')
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_ENEMY)
        elif len(entry_angles) > 0 and len(inactive_entry_angles) == 0:  # 只有激活了的下层入口
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_ENTRY)
        else:
            if self.ctx.env_config.is_debug:
                if self.nothing_times == 1:
                    self.save_screenshot()
            return self.round_success(SimUniRunRouteBaseV2.STATUS_NOTHING)

    @node_from(from_name='识别敌人', status=SimUniRunRouteBaseV2.STATUS_WITH_ENEMY)  # 识别到敌人就朝向敌人移动
    @operation_node(name='向敌人移动')
    def _move_by_detect(self) -> OperationRoundResult:
        """
        识别到敌人人开始移动
        :return:
        """
        self.nothing_times = 0
        self.moved_to_target = True
        op = SimUniMoveToEnemyByDetect(self.ctx)
        op_result = op.execute()
        if op_result.success:
            self.detect_move_timeout_times = 0
        return self.round_by_op_result(op_result)

    @node_from(from_name='向敌人移动', success=False, status=SrOperation.STATUS_TIMEOUT)  # 识别移动超时的话 尝试脱困
    @operation_node(name='识别移动超时脱困')
    def after_detect_timeout(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.after_detect_timeout(self)

    @node_from(from_name='识别敌人', status=SimUniRunRouteBaseV2.STATUS_NO_ENEMY)
    @node_from(from_name='向敌人移动', status=SimUniMoveToEnemyByDetect.STATUS_NO_ENEMY)
    @operation_node(name='识别下层入口')
    def handle_no_detect(self) -> OperationRoundResult:
        """
        画面上识别不到任何内容时 使用旧的方法进行识别下层入口兜底
        :return:
        """
        return SimUniRunRouteBaseV2.check_next_entry(self)

    @node_from(from_name='识别下层入口', status=SimUniRunRouteBaseV2.STATUS_WITH_ENTRY)
    @node_from(from_name='识别敌人', status=SimUniRunRouteBaseV2.STATUS_WITH_ENTRY)
    @operation_node(name='移动到下层')
    def move_to_next(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.move_to_next(self)

    @node_from(from_name='识别下层入口', status=SimUniRunRouteBaseV2.STATUS_NO_ENTRY)
    @node_from(from_name='识别敌人', status=SimUniRunRouteBaseV2.STATUS_NOTHING)  # 画面识别不到内容时 也转动找目标
    @node_from(from_name='移动到下层', success=False)  # 移动到下层入口失败时 也转动找目标: 可能1 走过了 没交互成功; 可能2 识别错了未激活的入口 移动过程中被攻击了
    @operation_node(name='转动找目标')
    def turn_when_nothing(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.turn_when_nothing(self)