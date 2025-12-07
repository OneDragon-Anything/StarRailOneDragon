from typing import Optional, Callable, ClassVar

from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.auto_run.reset_sim_uni_level import ResetSimUniLevel
from sr_od.app.sim_uni.operations.auto_run.sim_uni_wait_level_start import SimUniWaitLevelStart
from sr_od.app.sim_uni.operations.move_v1.move_to_next_level import MoveToNextLevel
from sr_od.app.sim_uni.operations.move_v1.sim_uni_run_combat_route_v1 import SimUniRunCombatRoute
from sr_od.app.sim_uni.operations.move_v2.sim_uni_run_combat_route_v2 import SimUniRunCombatRouteV2
from sr_od.app.sim_uni.operations.move_v2.sim_uni_run_elite_route_v2 import SimUniRunEliteRouteV2
from sr_od.app.sim_uni.operations.move_v2.sim_uni_run_event_route_v2 import SimUniRunEventRouteV2
from sr_od.app.sim_uni.operations.move_v2.sim_uni_run_respite_route_v2 import SimUniRunRespiteRouteV2
from sr_od.app.sim_uni.operations.move_v2.sim_uni_run_route_base_v2 import SimUniRunRouteBaseV2
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import UNI_NUM_CN, SimUniLevelTypeEnum, SimUniLevelType
from sr_od.app.sim_uni.sim_uni_route import SimUniRoute
from sr_od.context.sr_context import SrContext
from sr_od.operations.move.move_directly import MoveDirectly
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.check_team_members_in_world import CheckTeamMembersInWorld
from sr_od.operations.team.switch_member import SwitchMember
from sr_od.sr_map import mini_map_utils


class SimUniRunLevel(SrOperation):

    STATUS_BOSS_CLEARED: ClassVar[str] = '首领通关'
    STATUS_NO_RESET: ClassVar[str] = '失败到达重置上限'

    def __init__(self, ctx: SrContext, world_num: int,
                 config: Optional[SimUniChallengeConfig] = None,
                 max_reward_to_get: int = 0,
                 get_reward_callback: Optional[Callable[[int, int], None]] = None,
                 op_callback: Optional[Callable[[OperationResult], None]] = None,
                 skip_check_members: bool = False):
        """
        模拟宇宙中 识别楼层类型并运行
        完整通过整个楼层 进入下个楼层或通关后退出
        异常情况交由外层处理
        - 战斗失败
        """
        op_name = '%s %s %s' % (
            gt('模拟宇宙', 'game'),
            gt('第%s世界' % UNI_NUM_CN[world_num], 'game'),
            gt('挑战楼层')
        )

        SrOperation.__init__(self, ctx, op_name=op_name, op_callback=op_callback)

        self.world_num: int = world_num
        self.level_type: Optional[SimUniLevelType] = None
        self.route: Optional[SimUniRoute] = None
        self.config: SimUniChallengeConfig = config
        if config is None:
            ctx.sim_uni_info.world_num = world_num
            self.config = ctx.sim_uni_challenge_config
        self.max_reward_to_get: int = max_reward_to_get  # 最多获取多少次奖励
        self.get_reward_callback: Optional[Callable[[int, int], None]] = get_reward_callback  # 获取奖励后的回调
        self.reset_times: int = 0  # 重置次数
        self.skip_check_members: bool = skip_check_members  # 是否跳过配队检测

    def handle_init(self) -> Optional[OperationRoundResult]:
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """
        self.level_type = None
        self.route = None
        self.reset_times = 0

        return None

    @operation_node(name='等待加载', is_start_node=True)
    def _wait(self) -> OperationRoundResult:
        op = SimUniWaitLevelStart(self.ctx, config=self.config)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='等待加载')
    @operation_node(name='识别组队成员')
    def _check_members(self) -> OperationRoundResult:
        if self.skip_check_members:
            return self.round_success('跳过')
        op = CheckTeamMembersInWorld(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='识别组队成员')
    @operation_node(name='切换1号位')
    def _switch_first(self) -> OperationRoundResult:
        op = SwitchMember(self.ctx, 1)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='切换1号位')
    @node_from(from_name='按类型运行路线指令v1', success=False, status=SimUniRunRouteBaseV2.STATUS_WRONG_LEVEL_TYPE) # 有可能是楼层类型判断错了
    @node_from(from_name='按类型运行路线指令v1', success=False, status=SimUniRunRouteBaseV2.STATUS_NO_ENEMY) # 识别不到敌人
    @node_from(from_name='按类型运行路线指令v2', success=False, status=SimUniRunRouteBaseV2.STATUS_WRONG_LEVEL_TYPE) # 有可能是楼层类型判断错了
    @node_from(from_name='重置')  # 重置后完全重新来一遍
    @operation_node(name='识别楼层类型')
    def _check_level_type(self) -> OperationRoundResult:
        """
        识别楼层类型
        :return:
        """
        screen = self.screenshot()

        self.level_type = sim_uni_screen_state.get_level_type(self.ctx, screen)

        if self.level_type is None:
            return self.round_retry('匹配楼层类型失败', wait=1)
        else:
            return self.round_success()

    @node_from(from_name='识别楼层类型')
    @operation_node(name='匹配路线')
    def _check_route(self) -> OperationRoundResult:
        """
        根据小地图匹配路线
        防止匹配错误 两次匹配一样时才认为是正确 牺牲一点时间换取稳定性
        :return:
        """
        # 只有3~8宇宙的战斗楼层需要
        if (self.world_num > 8
                or self.level_type != SimUniLevelTypeEnum.COMBAT.value):
            return self.round_success()

        screen = self.screenshot()

        another_route = False  # 是否匹配到另一条路线
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        target_route = self.ctx.sim_uni_route_data.match_best_sim_uni_route(self.world_num, self.level_type, mm)

        if target_route is None:
            self.route = None
            return self.round_retry('匹配路线失败', wait=0.25)
        elif self.route is None or self.route.uid != target_route.uid:
            self.route = target_route
            another_route = True

        if another_route:
            return self.round_wait(wait=0.2)
        else:
            return self.round_success()

    @node_from(from_name='匹配路线')
    @operation_node(name='按类型运行路线指令v1')
    def _route_op(self, only_v2: bool = False) -> OperationRoundResult:
        """
        获取路线指令
        :return:
        """
        op: SrOperation = self._get_route_op(only_v2=only_v2)

        if op is None:
            return self.round_fail(status='未支持的楼层类型 %s' % self.level_type)

        op_result = op.execute()
        if op_result.success and self.level_type == SimUniLevelTypeEnum.BOSS.value:
            return self.round_success(status=SimUniRunLevel.STATUS_BOSS_CLEARED)
        else:
            return self.round_by_op_result(op_result)

    @node_from(from_name='匹配路线', success=False)  # 没有设置路线也尝试使用v2算法
    @node_from(from_name='按类型运行路线指令v1', success=False, status=MoveDirectly.STATUS_NO_POS) # 部分v1的失败情况 可以使用v2兜底
    @operation_node(name='按类型运行路线指令v2')
    def _route_op_v2(self) -> OperationRoundResult:
        """
        获取路线指令
        :return:
        """
        return self._route_op(only_v2=True)

    def _get_route_op(self, only_v2: bool = False) -> Optional[SrOperation]:
        """
        1. 匹配路线失败时 使用v2算法
        2. 根据匹配路线中的配置 选择使用的算法
        :return:
        """
        if self.level_type == SimUniLevelTypeEnum.COMBAT.value:
            if self.route is None or self.route.algo == 2 or only_v2:
                return SimUniRunCombatRouteV2(self.ctx, self.level_type)
            else:
                return SimUniRunCombatRoute(self.ctx, self.world_num, self.level_type, self.route, config=self.config)
        elif self.level_type == SimUniLevelTypeEnum.EVENT.value or \
                self.level_type == SimUniLevelTypeEnum.TRANSACTION.value or \
                self.level_type == SimUniLevelTypeEnum.ENCOUNTER.value:
            return SimUniRunEventRouteV2(self.ctx, self.level_type)
        elif self.level_type == SimUniLevelTypeEnum.RESPITE.value:
            return SimUniRunRespiteRouteV2(self.ctx, self.level_type)
        elif self.level_type == SimUniLevelTypeEnum.ELITE.value or \
                self.level_type == SimUniLevelTypeEnum.BOSS.value:
            return SimUniRunEliteRouteV2(self.ctx, self.level_type,
                                         max_reward_to_get=self.max_reward_to_get,
                                         get_reward_callback=self.get_reward_callback)
        else:
            return None

    @node_from(from_name='按类型运行路线指令v1', success=False, status=MoveToNextLevel.STATUS_ENTRY_NOT_FOUND)  # 最终还是失败时 部分场景可以尝试重置
    @node_from(from_name='按类型运行路线指令v2', success=False, status=MoveToNextLevel.STATUS_ENTRY_NOT_FOUND)  # 最终还是失败时 部分场景可以尝试重置
    @operation_node(name='重置')
    def _reset(self) -> OperationRoundResult:
        """
        重置再来
        :return:
        """
        if self.reset_times >= 1:  # 最多重置1次
            return self.round_fail(SimUniRunLevel.STATUS_NO_RESET)

        self.reset_times += 1
        op = ResetSimUniLevel(self.ctx, self.world_num)
        return self.round_by_op_result(op.execute())


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_for_sim_uni()
    ctx.start_running()
    op = SimUniRunLevel(ctx, world_num=8)
    op.execute()


if __name__ == '__main__':
    __debug()