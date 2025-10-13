import os
import shutil
import time
from typing import Optional, ClassVar, Callable

from one_dragon.base.operation.one_dragon_context import ContextRunStateEnum
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult, OperationRoundResultEnum
from one_dragon.utils import os_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from script_chainer.config.script_config import ScriptConfig
from script_chainer.win_exe.script_runner import run_script
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.auto_run.sim_uni_run_world import SimUniRunWorld
from sr_od.app.sim_uni.operations.bless.sim_uni_choose_path import SimUniChoosePath
from sr_od.app.sim_uni.operations.entry.choose_sim_uni_diff import ChooseSimUniDiff
from sr_od.app.sim_uni.operations.entry.choose_sim_uni_num import ChooseSimUniNum
from sr_od.app.sim_uni.operations.entry.sim_uni_claim_weekly_reward import SimUniClaimWeeklyReward
from sr_od.app.sim_uni.operations.entry.sim_uni_start import SimUniStart
from sr_od.app.sim_uni.operations.sim_uni_exit import SimUniExit
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

    # 在差分宇宙入口处检查积分奖励
    def _check_points_reward(self) -> OperationRoundResult:
        last_count_14000 = -1
        # 默认设置找不到 14000 返回重试
        result = self.round_retry('未找到积分奖励', wait=1)
        # 识别到两次一致的结果就退出循环
        for _ in range(10):
            ocr_result_map = self.ocr(self.ctx.controller.screenshot(), '模拟宇宙', '差分宇宙-积分奖励')

            count_14000 = 0
            for ocr_result, _mrl in ocr_result_map.items():
                count_14000 += ocr_result.count('14000')
            if last_count_14000 != count_14000:
                last_count_14000 = count_14000
                time.sleep(1)
                continue

            if count_14000 == 1:
                # 只有一个 14000
                result = self.round_fail('未打满积分奖励')
            elif count_14000 == 2:
                # 如果周计划未完成, 设置为已完成
                if not self.ctx.sim_uni_record.points_reward_complete:
                    self.ctx.sim_uni_record.points_reward_complete = True
                result = self.round_success('已打满积分奖励')
            break
        return result

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
    @node_from(from_name='调用差分宇宙自动化', success=False)
    @operation_node(name='识别初始画面')
    def _check_initial_screen(self) -> OperationRoundResult:
        # BackToNormalWorldPlus(self.ctx).execute()

        screen = self.screenshot()
        state = sim_uni_screen_state.get_sim_uni_initial_screen_state(self.ctx, screen)

        if state == sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value:
            if self.all_finished:
                return self.round_success(SimUniApp.STATUS_TO_WEEKLY_REWARD)
            if self.ctx.sim_uni_config.weekly_uni_num == 'WORLD_X':
                state = sim_uni_screen_state.ScreenState.SIM_TYPE_X.value # 差分宇宙

        return self.round_success(state)

    @node_from(from_name='识别初始画面')
    @operation_node(name='传送')
    def transport(self) -> OperationRoundResult:
        tab = self.ctx.guide_data.best_match_tab_by_name(gt('模拟宇宙', 'game'))
        # 差分宇宙, 传送之后调用模拟宇宙自动化脚本
        if self.ctx.sim_uni_config.weekly_uni_num == 'WORLD_X':
            category = self.ctx.guide_data.best_match_category_by_name(gt('差分宇宙', 'game'), tab)
            mission = self.ctx.guide_data.best_match_mission_by_name('前往参与', category)
            op = GuideTransport(self.ctx, mission)
            op.execute()
            # return self.round_by_op_result(op.execute())
            state = sim_uni_screen_state.ScreenState.SIM_TYPE_X.value
            return self.round_success(state)
        else:
            category = self.ctx.guide_data.best_match_category_by_name(gt('模拟宇宙', 'game'), tab)
            mission = self.ctx.guide_data.best_match_mission_by_name('模拟宇宙', category)
            op = GuideTransport(self.ctx, mission)
            op.execute()
            # return self.round_by_op_result(op.execute())
            state = sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value
            return self.round_success(state)

    @node_from(from_name='识别初始画面', status=sim_uni_screen_state.ScreenState.SIM_TYPE_X.value)  # 最开始已经在模拟宇宙入口了
    @node_from(from_name='传送', status=sim_uni_screen_state.ScreenState.SIM_TYPE_X.value)  # 传送到差分宇宙, 调用差分宇宙自动化脚本
    @operation_node(name='调用差分宇宙自动化')
    def _execute_sim_universe_x(self) -> OperationRoundResult:
        # 如果只要求打满奖励, 识别是否 14000/14000了
        if self.ctx.sim_uni_config.only_points_reward:
            points_reward = self._check_points_reward()
            if points_reward.result != OperationRoundResultEnum.FAIL:
                return points_reward

        work_dir = os_utils.get_work_dir()
        plugin_path = os.path.join(work_dir, *['plugins', 'Auto_Simulated_Universe'])
        script_file = os.path.join(plugin_path, 'diver.py')
        if not os.path.exists(plugin_path):
            return self.round_fail(f'差分宇宙插件目录不存在: {plugin_path}')
        if not os.path.exists(script_file):
            return self.round_fail(f'差分宇宙脚本不存在: {script_file}')

        # 使用自身的 python 环境启动脚本
        script_config = ScriptConfig(
            script_path=self.ctx.python_service.env_config.python_path,
            script_arguments=script_file,
            script_working_directory=plugin_path,
            script_process_name='None',  # 脚本退出检测需要使用 pid 而不是 python.exe, 故此处填 None
            game_process_name='',
            run_timeout_seconds=2000,
            check_done='script_closed',
            kill_script_after_done=False,
            kill_game_after_done=False,
            notify_start=False,
            notify_done=False,
        )
        BackToNormalWorldPlus(self.ctx).execute()

        # 删除运行记录
        plugin_run_result_path = os.path.join(plugin_path, 'logs', 'notif.txt')
        if os.path.exists(plugin_run_result_path):
            with open(plugin_run_result_path, 'w', encoding='utf-8') as file:
                pass  # 不写入任何内容, 仅清空
            # os.remove(plugin_run_result_path)

        # 复制配置文件
        config_file_path = os.path.join(work_dir,
                                        *['config', '%02d' % self.ctx.current_instance_idx, 'sim_universe_plugin.yml'])
        # 如果没有此用户的配置文件, 则复制默认配置文件到用户文件夹中; 默认 info.yml 存在
        plugin_config_file_path = os.path.join(plugin_path, 'info.yml')
        if not os.path.exists(plugin_config_file_path):
            return self.round_fail(f'差分宇宙默认配置文件不存在: {plugin_config_file_path}')
        if not os.path.exists(config_file_path):
            shutil.copy(plugin_config_file_path, config_file_path)
        shutil.copy(config_file_path, plugin_config_file_path)

        # 运行脚本, 重试次数 = 3
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            if self.ctx.context_running_state == ContextRunStateEnum.STOP:
                break
            elif self.ctx.context_running_state == ContextRunStateEnum.PAUSE:
                time.sleep(1)
                continue
            run_script(script_config, self.ctx)
            if self.ctx.context_running_state == ContextRunStateEnum.PAUSE:
                time.sleep(1)
                continue
            retry_count += 1

            # 进程退出, 检查运行情况
            for _ in range(3):
                try:
                    with open(plugin_run_result_path, 'r', encoding='utf-8') as file:
                        line = file.readline().strip()
                        completed_num = int(line) if line else 0
                    break
                except (ValueError, FileNotFoundError) as e:
                    log.error(f'读取运行结果文件失败: {e}')
                    completed_num = 0
                    time.sleep(5)

            if completed_num > 0:
                # 记录完成次数, 返回失败然后下次运行即可领奖励
                self.ctx.sim_uni_record.add_elite_times()
                return self.round_by_op_result(self.op_fail("已打完, 前往领奖励"))

        op = BackToNormalWorldPlus(self.ctx)
        op.execute()
        return self.round_by_op_result(self.op_fail("失败"))

    @node_from(from_name='识别初始画面', status=sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value)  # 最开始已经在模拟宇宙入口了
    @node_from(from_name='传送', status=sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value)
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
    @node_from(from_name='调用差分宇宙自动化', success=True)
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