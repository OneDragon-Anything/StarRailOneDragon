from typing import Optional, Callable, ClassVar, List

from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni.operations.auto_run.sim_uni_run_level import SimUniRunLevel
from sr_od.app.sim_uni.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.app.sim_uni.operations.sim_uni_exit import SimUniExit
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import UNI_NUM_CN
from sr_od.config.character_const import Character
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class SimUniRunWorld(SrOperation):

    STATUS_SUCCESS: ClassVar[str] = '通关'

    def __init__(self, ctx: SrContext, world_num: int,
                 config: Optional[SimUniChallengeConfig] = None,
                 max_reward_to_get: int = 0,
                 get_reward_callback: Optional[Callable[[int, int], None]] = None,
                 op_callback: Optional[Callable[[OperationResult], None]] = None):
        """
        模拟宇宙 完成整个宇宙
        最后退出
        """
        op_name = '%s %s' % (
            gt('模拟宇宙', 'game'),
            gt('第%s世界' % UNI_NUM_CN[world_num])
        )


        SrOperation.__init__(self, ctx, op_name=op_name, op_callback=op_callback)

        self.world_num: int = world_num
        self.config: Optional[SimUniChallengeConfig] = config
        self.max_reward_to_get: int = max_reward_to_get  # 最多获取多少次奖励
        self.get_reward_callback: Optional[Callable[[int, int], None]] = get_reward_callback  # 获取奖励后的回调
        self.get_reward_cnt = 0
        self.last_members: List[Character] = []  # 上一次识别的配队
        self.skip_check_members: bool = False  # 是否可跳过配队检测 当连续两次检测配队都一样之后 就可以跳过了

    @node_from(from_name='挑战楼层')
    @operation_node(name='挑战楼层', is_start_node=True)
    def _run_level(self) -> OperationRoundResult:
        if self.ctx.team_info.same_as_current(self.last_members):
            self.skip_check_members = True
        op = SimUniRunLevel(self.ctx, self.world_num, config=self.config,
                            max_reward_to_get=self.max_reward_to_get - self.get_reward_cnt,
                            get_reward_callback=self._on_get_reward,
                            skip_check_members=self.skip_check_members)
        op_result = op.execute()
        self.last_members = self.ctx.team_info.character_list  # 每次运行后 保存上一次识别的结果
        return self.round_by_op_result(op_result)

    @node_from(from_name='挑战楼层', status=SimUniRunLevel.STATUS_BOSS_CLEARED)
    @operation_node(name='结束')
    def _finish(self) -> OperationRoundResult:
        return self.round_success(status=SimUniRunWorld.STATUS_SUCCESS)

    @node_from(from_name='挑战楼层', success=False)
    @operation_node(name='异常处理')
    def _exit(self) -> OperationRoundResult:
        if self.ctx.env_config.is_debug:  # 调试情况下 原地失败即可
            return self.round_fail()
        else:
            op = SimUniExit(self.ctx)
            return self.round_by_op_result(op.execute())

    def _on_get_reward(self, use_power: int, user_qty: int):
        """
        获取奖励后的回调
        :return:
        """
        self.get_reward_cnt += 1
        if self.get_reward_callback is not None:
            self.get_reward_callback(use_power, user_qty)

    @node_from(from_name='挑战楼层', success=False, status=SimUniEnterFight.STATUS_BATTLE_FAIL)
    @operation_node(name='战斗失败结算')
    def battle_fail_exit(self) -> OperationRoundResult:
        """
        战斗失败后 点击结算
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '战斗失败-终止战斗并结算',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='战斗失败结算')
    @operation_node(name='战斗失败结算确认')
    def battle_fail_exit_confirm(self) -> OperationRoundResult:
        """
        战斗失败后 点击结算后 确认
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '战斗失败-确认',
                                                 success_wait=6, retry_wait=1)

    @node_from(from_name='战斗失败结算确认')
    @operation_node(name='战斗失败结算点击空白')
    def click_empty(self) -> OperationRoundResult:
        """
        结算画面点击空白
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '点击空白处继续',
                                                 success_wait=1, retry_wait=1)



def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.sim_uni_info.world_num = 8
    ctx.init_for_sim_uni()
    ctx.start_running()
    op = SimUniRunWorld(ctx, world_num=8)
    op.execute()


if __name__ == '__main__':
    __debug()