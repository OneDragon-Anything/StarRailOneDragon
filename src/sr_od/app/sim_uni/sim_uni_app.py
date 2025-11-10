from typing import Optional, ClassVar, Callable

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.bless.sim_uni_choose_path import SimUniChoosePath
from sr_od.app.sim_uni.operations.entry.choose_sim_uni_diff import ChooseSimUniDiff
from sr_od.app.sim_uni.operations.entry.choose_sim_uni_num import ChooseSimUniNum
from sr_od.app.sim_uni.operations.entry.sim_uni_start import SimUniStart
from sr_od.app.sim_uni.operations.entry.sim_uni_claim_weekly_reward import SimUniClaimWeeklyReward
from sr_od.app.sim_uni.operations.sim_uni_exit import SimUniExit
from sr_od.app.sim_uni.operations.auto_run.sim_uni_run_world import SimUniRunWorld
from sr_od.app.sim_uni.sim_uni_const import SimUniWorldEnum, SimUniPath
from sr_od.app.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_transport import GuideTransport
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus


class SimUniApp(SrApplication):

    STATUS_NOT_FOUND_IN_SI: ClassVar[str] = '生存索引中未找到模拟宇宙'
    STATUS_ALL_FINISHED: ClassVar[str] = '已完成通关次数'
    STATUS_EXCEPTION: ClassVar[str] = '异常次数过多'
    STATUS_TO_WEEKLY_REWARD: ClassVar[str] = '领取每周奖励'

    def __init__(self, ctx: SrContext,
                 specified_uni_num: Optional[int] = None,
                 max_reward_to_get: int = 0,
                 get_reward_callback: Optional[Callable[[int, int], None]] = None):
        """
        模拟宇宙应用 需要在大世界中非战斗、非特殊关卡界面中开启
        :param ctx:
        """
        SrApplication.__init__(self, ctx, 'sim_universe',
                               op_name=gt('模拟宇宙', 'game'),
                               run_record=ctx.sim_uni_record,
                               need_notify=True)

        self.current_uni_num: int = 0  # 当前运行的第几宇宙 启动时会先完成运行中的宇宙

        self.specified_uni_num: Optional[int] = specified_uni_num  # 指定宇宙 用于沉浸奖励
        self.max_reward_to_get: int = max_reward_to_get  # 最多获取多少次奖励
        self.get_reward_cnt: int = 0  # 当前获取的奖励次数
        self.get_reward_callback: Optional[Callable[[int, int], None]] = get_reward_callback  # 获取奖励后的回调

        self.exception_times: int = 0  # 异常出现次数
        self.not_found_in_survival_times: int = 0  # 在生存索引中找不到模拟宇宙的次数
        self.all_finished: bool = False

    @node_from(from_name='自动宇宙')
    @node_from(from_name='异常退出')
    @operation_node(name='检查运行次数', is_start_node=True)
    def _check_times(self) -> OperationRoundResult:
        self.ctx.init_for_sim_uni()

        if self.specified_uni_num is not None:
            if self.get_reward_cnt < self.max_reward_to_get:
                return self.round_success()
            else:
                self.all_finished = True
                return self.round_success(SimUniApp.STATUS_ALL_FINISHED)

        if self.exception_times >= 10:
            return self.round_success(SimUniApp.STATUS_EXCEPTION)

        log.info('本日精英次数 %d 本周精英次数 %d', self.ctx.sim_uni_record.elite_daily_times, self.ctx.sim_uni_record.elite_weekly_times)
        if (self.ctx.sim_uni_record.elite_daily_times >= self.ctx.sim_uni_config.elite_daily_times
                or self.ctx.sim_uni_record.elite_weekly_times >= self.ctx.sim_uni_config.elite_weekly_times):
            self.all_finished = True
            return self.round_success(SimUniApp.STATUS_ALL_FINISHED)
        else:
            return self.round_success()

    @node_from(from_name='检查运行次数')
    @operation_node(name='识别初始画面')
    def _check_initial_screen(self) -> OperationRoundResult:
        screen = self.screenshot()
        state = sim_uni_screen_state.get_sim_uni_initial_screen_state(self.ctx, screen)

        if state == sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value:
            if self.all_finished:
                return self.round_success(SimUniApp.STATUS_TO_WEEKLY_REWARD)

        return self.round_success(state)

    @node_from(from_name='识别初始画面')
    @operation_node(name='传送')
    def transport(self) -> OperationRoundResult:
        tab = self.ctx.guide_data.best_match_tab_by_name(gt('旷宇纷争', 'game'))
        category = self.ctx.guide_data.best_match_category_by_name(gt('差分宇宙', 'game'), tab)
        mission = self.ctx.guide_data.best_match_mission_by_name('前往模拟宇宙', category)
        op = GuideTransport(self.ctx, mission)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='识别初始画面', status=sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value)  # 最开始已经在模拟宇宙入口了
    @node_from(from_name='传送')
    @operation_node(name='选择宇宙')
    def _choose_sim_uni_num(self) -> OperationRoundResult:
        if self.specified_uni_num is None:
            world = SimUniWorldEnum[self.ctx.sim_uni_config.weekly_uni_num]
        else:
            world = SimUniWorldEnum['WORLD_%02d' % self.specified_uni_num]

        op = ChooseSimUniNum(self.ctx, world.value.idx)
        op_result = op.execute()
        if op_result.success:
            self.current_uni_num = op_result.data  # 使用OP的结果 可能选的并不是原来要求的
            self.ctx.sim_uni_info.world_num = self.current_uni_num
        else:
            self.ctx.sim_uni_info.world_num = 0
        return self.round_by_op_result(op_result)


    @node_from(from_name='选择宇宙', status=ChooseSimUniNum.STATUS_RESTART)
    @operation_node(name='选择难度')
    def _choose_sim_uni_diff(self) -> OperationRoundResult:
        op = ChooseSimUniDiff(self.ctx, self.ctx.sim_uni_config.weekly_uni_diff)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择宇宙', status=ChooseSimUniNum.STATUS_CONTINUE)
    @node_from(from_name='选择难度')
    @operation_node(name='开始挑战')
    def start_sim_uni(self) -> OperationRoundResult:
        op = SimUniStart(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始挑战', status=SimUniStart.STATUS_RESTART)
    @operation_node(name='选择命途')
    def _choose_path(self) -> OperationRoundResult:
        cfg = self.ctx.sim_uni_config.get_challenge_config(self.current_uni_num)
        op = SimUniChoosePath(self.ctx, SimUniPath[cfg.path])
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始挑战', status=SimUniStart.STATUS_CONTINUE)
    @node_from(from_name='选择命途')
    @operation_node(name='自动宇宙')
    def _run_world(self) -> OperationRoundResult:
        uni_challenge_config = self.ctx.sim_uni_config.get_challenge_config(self.current_uni_num)
        get_reward = self.current_uni_num == self.specified_uni_num  # 只有当前宇宙和开拓力需要的宇宙是同一个 才能拿奖励

        op = SimUniRunWorld(self.ctx, self.current_uni_num,
                            config=uni_challenge_config,
                            max_reward_to_get=self.max_reward_to_get - self.get_reward_cnt if get_reward else 0,
                            get_reward_callback=self._on_sim_uni_get_reward if get_reward else None
                            )
        return self.round_by_op_result(op.execute())

    def _on_sim_uni_get_reward(self, use_power: int, user_qty: int):
        self.get_reward_cnt += 1
        if self.get_reward_callback is not None:
            self.get_reward_callback(use_power, user_qty)

    @node_from(from_name='自动宇宙', success=False)
    @operation_node(name='自动宇宙发生异常')
    def run_world_fail(self) -> OperationRoundResult:
        if self.ctx.env_config.is_debug:
            # 调试模式下不退出 直接失败等待处理
            return self.round_fail()

        # 任何异常错误都退出当前宇宙
        return self.round_success()

    @node_from(from_name='自动宇宙发生异常')
    @operation_node(name='异常退出')
    def _exception_exit(self) -> OperationRoundResult:
        self.exception_times += 1
        op = SimUniExit(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='识别初始画面', status=STATUS_TO_WEEKLY_REWARD)
    @operation_node(name='领取每周奖励')
    def check_reward_before_exit(self) -> OperationRoundResult:
        op = SimUniClaimWeeklyReward(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='检查运行次数', status=STATUS_EXCEPTION)
    @node_from(from_name='领取每周奖励')
    @node_from(from_name='领取每周奖励', success=False)
    @operation_node(name='完成后返回')
    def back_at_last(self) -> OperationRoundResult:
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_for_sim_uni()
    ctx.start_running()
    op = SimUniApp(ctx)
    op.execute()


if __name__ == '__main__':
    __debug()