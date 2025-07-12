from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.world_patrol.world_patrol_enter_fight import WorldPatrolEnterFight
from sr_od.app.world_patrol.world_patrol_route import WorldPatrolRoute, WorldPatrolRouteOperation
from sr_od.config import operation_const
from sr_od.config.character_const import get_character_by_id
from sr_od.context.sr_context import SrContext
from sr_od.operations.interact.catapult import Catapult
from sr_od.operations.interact.gameplay_interact import GameplayInteract
from sr_od.operations.interact.move_interact import MoveInteract
from sr_od.operations.move.move_directly import MoveDirectly
from sr_od.operations.move.move_without_pos import MoveWithoutPos
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.check_team_members_in_world import CheckTeamMembersInWorld
from sr_od.operations.team.switch_member import SwitchMember
from sr_od.operations.technique import UseTechnique
from sr_od.operations.wait.wait_in_seconds import WaitInSeconds
from sr_od.operations.wait.wait_in_world import WaitInWorld
from sr_od.screen_state import common_screen_state
from sr_od.sr_map.operations.transport_by_map import TransportByMap
from sr_od.sr_map.sr_map_def import Region


class WorldPatrolRunRoute(SrOperation):
    STATUS_ALL_DONE: ClassVar[str] = '执行结束'

    def __init__(self, ctx: SrContext, route: WorldPatrolRoute):
        """
        运行一条锄地路线
        :param ctx:
        :param route: 路线
        """
        self.route: WorldPatrolRoute = route

        self.feixiao_attack: bool = True  # 飞霄是否进行了攻击 路线开始的时候不需要攻击 因此设置为已经攻击

        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('锄地路线'), self.route.display_name))

    def handle_init(self):
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """
        self.op_idx: int = -1
        """当前执行的指令下标"""

        self.current_pos: Point = self.route.tp.tp_pos
        """当前角色的坐标信息"""

        self.current_region: Region = self.route.tp.region
        """当前的区域"""

        log.info('准备执行线路 %s', self.route.display_name)
        log.info('感谢以下人员提供本路线 %s', self.route.author_list)

        self.ctx.ban_technique = False  # 每条路线开始前 重置

        return None

    @operation_node(name='传送', is_start_node=True)
    def transport(self) -> OperationRoundResult:
        op = TransportByMap(self.ctx, self.route.tp)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='传送')
    @operation_node(name='切换1号位')
    def switch_first(self) -> OperationRoundResult:
        """
        切换到1号位
        :return:
        """
        op = SwitchMember(self.ctx, 1)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='切换1号位')
    @operation_node(name='检测组队')
    def _check_members(self) -> OperationRoundResult:
        """
        检测队员
        :return:
        """
        c1 = None
        c1_id = self.ctx.world_patrol_config.character_1
        if c1_id != 'none':
            c1 = get_character_by_id(c1_id)
        op = CheckTeamMembersInWorld(self.ctx, [c1, None, None, None])
        return self.round_by_op_result(op.execute())

    @node_from(from_name='检测组队')
    @node_from(from_name='执行路线指令')
    @operation_node(name='执行路线指令')
    def _next_op(self) -> OperationRoundResult:
        """
        下一个操作指令
        :return:
        """
        self.op_idx += 1

        # if self.op_idx == 0:  # 测试传送点用
        #     return self.round_success(WorldPatrolRunRoute.STATUS_ALL_DONE)

        if self.op_idx >= len(self.route.route_list):
            return self.round_success(WorldPatrolRunRoute.STATUS_ALL_DONE)

        if self.ctx.is_fx_world_patrol_tech:
            return self.run_op_for_feixiao()
        else:
            return self.run_op_for_normal()

    def run_op_for_normal(self) -> OperationRoundResult:
        """
        普通锄大地的逻辑
        :return:
        """
        op = None
        route_item = self.route.route_list[self.op_idx]
        if self.op_idx + 1 < len(self.route.route_list):
            next_route_item = self.route.route_list[self.op_idx + 1]
        else:
            next_route_item = None

        # 判断是否需要用buff
        should_use_tech: bool = False
        if (self.ctx.world_patrol_config.technique_fight
                and self.ctx.team_info.is_buff_technique
                and not self.ctx.tech_used_in_lasting):
            for i in range(self.op_idx, len(self.route.route_list)):
                item = self.route.route_list[i]
                if item.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE, operation_const.OP_NO_POS_MOVE,
                               operation_const.OP_UPDATE_POS,
                               operation_const.OP_BAN_TECH, operation_const.OP_ALLOW_TECH]:
                    # 需要找下一个不是移动的指令
                    continue
                elif item.op in [operation_const.OP_PATROL, ]:
                    # 如果下一个不是移动的指令 是攻击攻击怪物类的 则需要使用buff
                    should_use_tech = True
                    break
                else:
                    # 剩下的类型 都不需要使用buff
                    should_use_tech = False
                    break

        if should_use_tech:
            op = UseTechnique(self.ctx,
                              max_consumable_cnt=self.ctx.world_patrol_config.max_consumable_cnt,
                              need_check_point=True,  # 检查秘技点是否足够 可以在没有或者不能用药的情况加快判断
                              trick_snack=self.ctx.game_config.use_quirky_snacks
                              )
            # 由于是中途插入的指令 需要特殊处理下标
            op_result = op.execute()
            self.op_idx -= 1
            return self.round_by_op_result(op_result)
        elif route_item.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE]:
            op = self.move(route_item, next_route_item)
        elif route_item.op == operation_const.OP_NO_POS_MOVE:
            op = self.no_pos_move(route_item)
        elif route_item.op == operation_const.OP_PATROL:
            op = WorldPatrolEnterFight(self.ctx,
                                       technique_fight=self.ctx.world_patrol_config.technique_fight,
                                       technique_only=self.ctx.world_patrol_config.technique_only,
                                       first_state=common_screen_state.ScreenState.NORMAL_IN_WORLD.value)
        elif route_item.op == operation_const.OP_DISPOSABLE:
            op = WorldPatrolEnterFight(self.ctx,
                                       first_state=common_screen_state.ScreenState.NORMAL_IN_WORLD.value,
                                       disposable=True)
        elif route_item.op == operation_const.OP_INTERACT:
            op = MoveInteract(self.ctx, route_item.data)
        elif route_item.op == operation_const.OP_CATAPULT:
            op = Catapult(self.ctx)
        elif route_item.op == operation_const.OP_WAIT:
            op = self.wait(route_item.data[0], float(route_item.data[1]))
        elif route_item.op == operation_const.OP_UPDATE_POS:
            next_pos = Point(route_item.data[0], route_item.data[1])
            self._update_pos_after_op(OperationResult(True, data=next_pos))
            return self.round_success()
        elif route_item.op == operation_const.OP_ENTER_SUB:
            self.current_region = self.ctx.map_data.get_sub_region_by_cn(self.current_region, route_item.data[0], int(route_item.data[1]))
            return self.round_success()
        elif route_item.op == operation_const.OP_BAN_TECH:
            self.ctx.ban_technique = True
            return self.round_success()
        elif route_item.op == operation_const.OP_ALLOW_TECH:
            self.ctx.ban_technique = False
            return self.round_success()
        elif route_item.op == operation_const.OP_GAMEPLAY_INTERACT:
            op = GameplayInteract(self.ctx, int(route_item.data[0]))
        else:
            return self.round_fail(status='错误的锄大地指令 %s' % route_item.op)


        # 以下代码仅用作记录坐标和小地图测试用
        # if self.ctx.record_coordinate and op_result.success and (
        #         (  # 当前是移动 下一个不是战斗 避免被怪攻击卡死
        #                 route_item.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE] and
        #                 next_route_item is not None and
        #                 next_route_item.op not in [operation_const.OP_PATROL]
        #         )
        #         or
        #         (  # 当前是战斗
        #                 route_item.op == operation_const.OP_PATROL
        #         )
        # ):
        #     record_times = 5
        #     if route_item.op == operation_const.OP_PATROL:  # 战斗后小地图已经缩放完了 只记录一次就可以了
        #         record_times = 1
        #     op2 = RecordCoordinate(self.ctx, self.current_region, self.current_pos, record_times=record_times)
        #     op2.execute()

        if op is not None:
            return self.round_by_op_result(op.execute())
        else:
            return self.round_fail('指令错误 %d', self.op_idx)

    def run_op_for_feixiao(self) -> OperationRoundResult:
        """
        飞霄锄大地的逻辑
        :return:
        """
        route_item = self.route.route_list[self.op_idx]
        if self.op_idx + 1 < len(self.route.route_list):
            next_route_item = self.route.route_list[self.op_idx + 1]
        else:
            next_route_item = None

        # 当前是否应该攻击
        should_attack: bool = False
        for i in range(self.op_idx, len(self.route.route_list)):
            item = self.route.route_list[i]
            if item.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE, operation_const.OP_NO_POS_MOVE,
                           operation_const.OP_UPDATE_POS,
                           operation_const.OP_BAN_TECH, operation_const.OP_ALLOW_TECH]:
                # 需要找下一个不是移动的指令
                continue
            elif item.op in [operation_const.OP_PATROL, operation_const.OP_DISPOSABLE]:
                # 如果下一个不是移动的指令 是攻击类的 则当前不需要攻击
                should_attack = False
                break
            elif item.op in [operation_const.OP_INTERACT, operation_const.OP_CATAPULT,
                             operation_const.OP_GAMEPLAY_INTERACT]:
                # 如果下一个不是移动的指令 是交互类的 这类通常都会触发传送 则当前可以攻击了
                should_attack = True
                break
            else:
                # 剩下的类型 其实都是交互后才会出现的 这些也归到可以攻击
                should_attack = True
                break

        if self.feixiao_attack:
            should_attack = False

        op = None
        if should_attack:
            op = WorldPatrolEnterFight(self.ctx,
                                       technique_fight=self.ctx.world_patrol_config.technique_fight,
                                       technique_only=self.ctx.world_patrol_config.technique_only,
                                       first_state=common_screen_state.ScreenState.NORMAL_IN_WORLD.value)
            # 由于是中途插入的指令 需要特殊处理下标
            op_result = op.execute()
            if op_result.success:
                self.feixiao_attack = True
            self.op_idx -= 1
            return self.round_by_op_result(op_result)
        elif route_item.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE]:
            op = self.move(route_item, next_route_item)
        elif route_item.op == operation_const.OP_NO_POS_MOVE:
            op = self.no_pos_move(route_item)
        elif route_item.op == operation_const.OP_PATROL:
            self.feixiao_attack = False  # 经过怪物点后 因为携带了怪物 即后续需要攻击 所以需要把已经攻击的标志重置
            return self.round_success()
        elif route_item.op == operation_const.OP_DISPOSABLE:
            return self.round_success()
        elif route_item.op == operation_const.OP_INTERACT:
            op = MoveInteract(self.ctx, route_item.data)
        elif route_item.op == operation_const.OP_CATAPULT:
            op = Catapult(self.ctx)
        elif route_item.op == operation_const.OP_WAIT:
            op = self.wait(route_item.data[0], float(route_item.data[1]))
        elif route_item.op == operation_const.OP_UPDATE_POS:
            next_pos = Point(route_item.data[0], route_item.data[1])
            self._update_pos_after_op(OperationResult(True, data=next_pos))
            return self.round_success()
        elif route_item.op == operation_const.OP_ENTER_SUB:
            self.current_region = self.ctx.map_data.get_sub_region_by_cn(self.current_region, route_item.data[0], int(route_item.data[1]))
            return self.round_success()
        elif route_item.op == operation_const.OP_BAN_TECH:
            self.ctx.ban_technique = True
            return self.round_success()
        elif route_item.op == operation_const.OP_ALLOW_TECH:
            self.ctx.ban_technique = False
            return self.round_success()
        elif route_item.op == operation_const.OP_GAMEPLAY_INTERACT:
            op = GameplayInteract(self.ctx, int(route_item.data[0]))
        else:
            return self.round_fail(status='错误的锄大地指令 %s' % route_item.op)

        if op is not None:
            return self.round_by_op_result(op.execute())
        else:
            return self.round_fail('指令错误 %d', self.op_idx)

    def move(self, route_item, next_route_item) -> SrOperation:
        """
        移动到某个点
        :param route_item: 本次指令
        :param next_route_item: 下次指令
        :return:
        """
        current_pos = self.current_pos
        current_lm_info = self.ctx.map_data.get_large_map_info(self.current_region)

        next_pos = Point(route_item.data[0], route_item.data[1])
        next_lm_info = None
        if len(route_item.data) > 2:  # 需要切换层数
            next_region = self.ctx.map_data.best_match_region_by_name(
                gt(current_lm_info.region.cn, 'game'), current_lm_info.region.planet, target_floor=route_item.data[2])
            next_lm_info = self.ctx.map_data.get_large_map_info(next_region)

        stop_afterwards = not (
                next_route_item is not None and
                next_route_item.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE,
                                       operation_const.OP_PATROL,  # 如果下一个是攻击 则靠攻击停止移动 这样还可以取消疾跑后摇
                                       ]
        )
        no_run = route_item.op == operation_const.OP_SLOW_MOVE

        # if self.ctx.record_coordinate:  # 需要记录坐标时 强制禁疾跑 以及到达后停止跑动
        #     stop_afterwards = True
        #     no_run = True

        return MoveDirectly(self.ctx, current_lm_info, next_lm_info=next_lm_info,
                            target=next_pos, start=current_pos,
                            stop_afterwards=stop_afterwards, no_run=no_run,
                            technique_fight=self.ctx.world_patrol_config.technique_fight,
                            technique_only=self.ctx.world_patrol_config.technique_only,
                            op_callback=self._update_pos_after_op)

    def no_pos_move(self, route_item: WorldPatrolRouteOperation) -> SrOperation:
        start = Point(0, 0)
        target = Point(route_item.data[0], route_item.data[1])
        move_time = route_item.data[2]

        return MoveWithoutPos(self.ctx, start, target, move_time=move_time)

    def _update_pos_after_op(self, op_result: OperationResult):
        """
        移动后更新坐标
        :param op_result:
        :return:
        """
        if not op_result.success:
            return

        self.current_pos = op_result.data

        route_item = self.route.route_list[self.op_idx]
        if len(route_item.data) > 2:
            self.current_region = self.ctx.map_data.best_match_region_by_name(
                gt(self.current_region.cn, 'game'), self.current_region.planet, target_floor=route_item.data[2])

    def wait(self, wait_type: str, seconds: float) -> SrOperation:
        """
        等待
        :param wait_type: 等待类型
        :param seconds: 等待秒数
        :return:
        """
        if wait_type == 'in_world':
            return WaitInWorld(self.ctx, seconds, wait_after_success=1)  # 多等待一秒 动画后界面完整显示需要点时间
        elif wait_type == operation_const.WAIT_TYPE_SECONDS:
            return WaitInSeconds(self.ctx, seconds)

    @node_from(from_name='执行路线指令', status=STATUS_ALL_DONE)
    @operation_node(name='执行路线指令完毕')
    def finish(self) -> OperationRoundResult:
        """
        路线执行完毕
        :return:
        """
        if self.ctx.is_fx_world_patrol_tech:  # 飞霄需要在结束时候攻击
            op = WorldPatrolEnterFight(self.ctx,
                                       technique_fight=self.ctx.world_patrol_config.technique_fight,
                                       technique_only=self.ctx.world_patrol_config.technique_only,
                                       first_state=common_screen_state.ScreenState.NORMAL_IN_WORLD.value)
            return self.round_by_op_result(op.execute())
        return self.round_success()


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_for_world_patrol()
    ctx.start_running()

    from sr_od.app.world_patrol.world_patrol_whitelist_config import WorldPatrolWhitelist
    whitelist = WorldPatrolWhitelist('名单_3')  # 单条测试
    route = ctx.world_patrol_route_data.load_all_route(
        whitelist=whitelist
    )
    op = WorldPatrolRunRoute(ctx, route[0])
    op.execute()


if __name__ == '__main__':
    __debug()