import time

from typing import ClassVar, List, Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cal_utils
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.config.game_config import RunModeEnum
from sr_od.context.sr_context import SrContext
from sr_od.operations.move.get_rid_of_stuck import GetRidOfStuck
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state, battle_screen_state
from sr_od.sr_map import mini_map_utils
from sr_od.sr_map.mini_map_info import MiniMapInfo


class SimUniMoveToEnemyByMiniMap(SrOperation):
    STATUS_ARRIVAL: ClassVar[str] = '已到达'
    STATUS_FIGHT: ClassVar[str] = '遭遇战斗'

    REC_POS_INTERVAL: ClassVar[float] = 0.1
    DIS_MAX_LEN: ClassVar[int] = 2 // REC_POS_INTERVAL  # 2秒没移动

    def __init__(self, ctx: SrContext, no_attack: bool = False, stop_after_arrival: bool = False):
        """
        从小地图上判断 向其中一个红点移动
        停下来的条件有
        - 距离红点过近
        - 被怪物锁定
        :param ctx: 上下文
        :param no_attack: 不主动发起攻击
        :param stop_after_arrival: 到达后停止 如果明确知道到达后会发起攻击 则可以不停止
        """
        SrOperation.__init__(self, ctx, op_name=gt('向红点移动'))

        self.current_pos: Point = Point(0, 0)
        """当前距离 默认是远点"""

        self.dis: List[float] = []
        """与红点的距离"""

        self.last_rec_time: float = 0
        """上一次记录距离的时间"""

        self.stuck_times: int = 0
        """被困次数"""

        self.no_attack: bool = no_attack
        """不发起主动攻击 适用于精英怪场合"""

        self.stop_after_arrival: bool = stop_after_arrival
        """到达后停止"""

    @operation_node(name='移动', is_start_node=True, timeout_seconds=60)
    def _execute_one_round(self) -> OperationRoundResult:
        stuck = self.move_in_stuck()  # 先尝试脱困 再进行移动
        if stuck is not None:  # 只有脱困失败的时候会有返回结果
            return stuck

        now = time.time()
        screen = self.screenshot()

        if not common_screen_state.is_normal_in_world(self.ctx, screen):  # 不在大世界 可能被袭击了
            return self.enter_battle(False)

        if not self.no_attack:
            self.ctx.yolo_detector.detect_should_attack_in_world_async(screen, now)
            if self.ctx.yolo_detector.should_attack_in_world_last_result(now):
                return self.enter_battle(True)

        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        mm_info: MiniMapInfo = mini_map_utils.analyse_mini_map(mm)
        enemy_pos_list = mini_map_utils.get_enemy_pos(mm_info)

        if len(enemy_pos_list) == 0:  # 没有红点 可能太近被自身箭头覆盖了
            return self._arrive()

        # 最近的红点
        closest_dis: float = 999
        closest_pos: Point = None

        for pos in enemy_pos_list:
            dis = cal_utils.distance_between(self.current_pos, pos)
            if dis < closest_dis:
                closest_dis = dis
                closest_pos = pos

        if closest_dis < 10:
            return self._arrive()

        if len(self.dis) == 0:  # 第一个点 无条件放入
            return self._add_pos(now, closest_pos, closest_dis, mm_info.angle)

        # 只要开始移动了 目标点的角度应该在当前朝向附近
        del_angle = abs(cal_utils.get_angle_by_pts(self.current_pos, closest_pos) - 270)
        if del_angle > 20 and len(self.dis) > 3:
            pass  # 未知怎么处理

        return self._add_pos(now, closest_pos, closest_dis, mm_info.angle)

    def _add_pos(self, now: float, pos: Point, dis: float, angle: float) -> OperationRoundResult:
        """
        记录距离 每0.2秒一次 最多20个
        :param now: 这次运行的时间
        :param pos: 最近的红点位置
        :param dis: 最近的红点距离
        :param angle: 当前朝向
        :return:
        """
        if now - self.last_rec_time <= SimUniMoveToEnemyByMiniMap.REC_POS_INTERVAL:
            return self.round_wait()

        # 新距离比旧距离大 大概率已经到了一个点了 捕捉到的是第二个点
        if len(self.dis) > 0 and dis - self.dis[-1] > 10:
            return self._arrive()

        self.dis.append(dis)
        self.last_rec_time = now

        if len(self.dis) > SimUniMoveToEnemyByMiniMap.DIS_MAX_LEN:
            self.dis.pop(0)

        self.ctx.controller.move_towards(self.current_pos, pos, angle,
                                         run=self.ctx.game_config.run_mode != RunModeEnum.OFF.value.value)
        return self.round_wait()

    def move_in_stuck(self) -> Optional[OperationRoundResult]:
        """
        判断是否被困且进行移动
        :return: 如果被困次数过多就返回失败
        """
        if len(self.dis) == 0:
            return None

        first_dis = self.dis[0]
        last_dis = self.dis[len(self.dis) - 1]

        # 通过第一个坐标和最后一个坐标的距离 判断是否困住了
        if (len(self.dis) >= SimUniMoveToEnemyByMiniMap.DIS_MAX_LEN
                and last_dis >= first_dis):
            self.stuck_times += 1
            if self.stuck_times > 12:
                return self.round_fail('脱困失败')
            get_rid_of_stuck = GetRidOfStuck(self.ctx, self.stuck_times)
            stuck_op_result = get_rid_of_stuck.execute()
            if stuck_op_result.success:
                self.last_rec_time += stuck_op_result.data
        else:
            self.stuck_times = 0

        return None

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
            return self.round_success(SimUniMoveToEnemyByMiniMap.STATUS_FIGHT)
        else:
            return self.round_by_op_result(op_result)

    def _arrive(self) -> OperationRoundResult:
        """
        到达红点后处理
        :return:
        """
        if self.stop_after_arrival:
            self.ctx.controller.stop_moving_forward()
        return self.round_success(SimUniMoveToEnemyByMiniMap.STATUS_ARRIVAL)
