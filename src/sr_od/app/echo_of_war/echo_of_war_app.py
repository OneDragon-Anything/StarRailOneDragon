from typing import Optional

from one_dragon.base.operation.application_run_record import AppRunRecord
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.echo_of_war.challenge_ehco_of_war import ChallengeEchoOfWar
from sr_od.app.echo_of_war.echo_of_war_run_record import EchoOfWarRunRecord
from sr_od.app.sr_application import SrApplication
from sr_od.app.trailblaze_power.trailblaze_power_app import TrailblazePowerApp
from sr_od.app.trailblaze_power.trailblaze_power_config import TrailblazePowerPlanItem
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_check_power import GuideCheckPower, GuidePowerResult
from sr_od.interastral_peace_guide.guide_def import GuideMission


class EchoOfWarApp(SrApplication):

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, 'echo_of_war', op_name=gt('历战余响', 'game'),
                               run_record=ctx.echo_of_war_run_record, need_notify=True)
        self.power: int = 0

    @operation_node(name='检查当前需要挑战的关卡', is_start_node=True)
    def check_task(self) -> OperationRoundResult:
        """
        判断下一个是什么副本
        :return:
        """
        self.ctx.power_config.check_plan_run_times()
        plan: Optional[TrailblazePowerPlanItem] = self.ctx.echo_of_war_config.next_plan_item

        if plan is None:
            return self.round_success(status=TrailblazePowerApp.STATUS_NO_PLAN)

        if self.ctx.echo_of_war_run_record.left_times <= 0:
            return self.round_success(status=TrailblazePowerApp.STATUS_NO_PLAN)

        return self.round_success(status=TrailblazePowerApp.STATUS_WITH_PLAN)

    @node_from(from_name='检查当前需要挑战的关卡')
    @operation_node(name='检查体力')
    def check_power(self) -> OperationRoundResult:
        op = GuideCheckPower(self.ctx)
        op_result = op.execute()
        if op_result.success:
            power: GuidePowerResult = op_result.data
            self.power = power.power
        return self.round_by_op_result(op_result)

    @node_from(from_name='检查体力')
    @operation_node(name='挑战')
    def _use_power(self) -> OperationRoundResult:
        config = self.ctx.echo_of_war_config
        config.check_plan_finished()
        plan: Optional[TrailblazePowerPlanItem] = config.next_plan_item
        if plan is None:
            return self.round_success('无挑战计划')
        mission: Optional[GuideMission] = self.ctx.guide_data.get_mission_by_unique_id(plan.mission_id)

        run_times: int = self.power // mission.power

        record: EchoOfWarRunRecord = self.ctx.echo_of_war_run_record
        if record.left_times < run_times:
            run_times = record.left_times

        if run_times == 0:
            return self.round_success('无足够体力 或 无挑战次数')

        if run_times + plan.run_times > plan.plan_times:
            run_times = plan.plan_times - plan.run_times

        def on_battle_success(run_times: int, use_power: int):
            self.power -= use_power
            log.info('运行次数 %d, 消耗体力: %d, 剩余体力: %d', run_times, use_power, self.power)
            plan.run_times += run_times
            log.info('副本完成次数: %d, 计划次数: %d', plan.run_times, plan.plan_times)
            record.left_times = record.left_times - run_times
            log.info('本周历战余响剩余次数: %d', record.left_times)
            config.save()
            record.update_status(AppRunRecord.STATUS_RUNNING)

        op = ChallengeEchoOfWar(
            self.ctx,
            mission=mission,
            team_num=plan.team_num,
            plan_times=run_times,
            support=plan.support if plan.support != 'none' else None,
            on_battle_success=on_battle_success
        )
        if op.execute().success:
            self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
            return self.round_wait()
        else:  # 挑战
            return self.round_retry('挑战失败')

def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_for_sim_uni()
    ctx.start_running()
    op = EchoOfWarApp(ctx)
    op.execute()


if __name__ == '__main__':
    __debug()