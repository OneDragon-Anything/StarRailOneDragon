from typing import ClassVar, Optional

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.div_uni.operations.ornamenet_extraction import ChallengeOrnamentExtraction
from sr_od.app.sim_uni.sim_uni_app import SimUniApp
from sr_od.app.sim_uni.sim_uni_const import SimUniWorldEnum
from sr_od.app.sr_application import SrApplication
from sr_od.app.trailblaze_power.trailblaze_power_config import TrailblazePowerPlanItem
from sr_od.challenge_mission.use_trailblaze_power import UseTrailblazePower
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_check_power import GuideCheckPower, GuidePowerResult
from sr_od.interastral_peace_guide.guide_def import GuideMission
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus


class TrailblazePowerApp(SrApplication):

    STATUS_NORMAL_TASK: ClassVar[str] = '普通副本'
    STATUS_SIM_UNI_TASK: ClassVar[str] = '模拟宇宙'
    STATUS_OE_TASK: ClassVar[str] = '饰品提取'
    STATUS_NO_ENOUGH_POWER: ClassVar[str] = '体力不足'
    STATUS_NO_PLAN: ClassVar[str] = '没有开拓力计划'
    STATUS_WITH_PLAN: ClassVar[str] = '有开拓力计划'
    STATUS_PLAN_FINISHED: ClassVar[str] = '完成计划'

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, 'trailblaze_power',
                               op_name=gt('开拓力'),
                               run_record=ctx.power_record,
                               need_notify=True)

        self.last_mission: Optional[GuideMission] = None  # 上一个挑战副本
        self.power: int = 0  # 剩余开拓力
        self.qty: int = 0  # 沉浸器数量

    @operation_node(name='检查当前需要挑战的关卡', is_start_node=True)
    def check_task(self) -> OperationRoundResult:
        """
        判断下一个是什么副本
        :return:
        """
        self.ctx.power_config.check_plan_run_times()
        plan: Optional[TrailblazePowerPlanItem] = self.ctx.power_config.get_next_plan()

        if plan is None:
            return self.round_success(status=TrailblazePowerApp.STATUS_NO_PLAN)

        return self.round_success(status=TrailblazePowerApp.STATUS_WITH_PLAN)

    @node_from(from_name='检查当前需要挑战的关卡', status=STATUS_WITH_PLAN)
    @operation_node(name='打开指南检查体力')
    def open_guide(self) -> OperationRoundResult:
        op = GuideCheckPower(self.ctx)
        op_result = op.execute()
        if op_result.success:
            power_result: GuidePowerResult = op_result.data
            self.power = power_result.power
            self.qty = power_result.qty
        return self.round_by_op_result(op_result)

    @node_from(from_name='打开指南检查体力')
    @node_from(from_name='执行开拓力计划')
    @operation_node(name='执行开拓力计划')
    def execute_plan(self) -> OperationRoundResult:
        self.ctx.power_config.check_plan_run_times()
        plan: Optional[TrailblazePowerPlanItem] = self.ctx.power_config.get_next_plan()
        for _ in range(100):
            if plan is None:
                return self.round_success(TrailblazePowerApp.STATUS_NO_PLAN)

            mission: Optional[GuideMission] = self.ctx.guide_data.get_mission_by_unique_id(plan.mission_id)
            if mission is None:
                return self.round_success(TrailblazePowerApp.STATUS_NO_PLAN)

            can_run_times: int = self.power // mission.power
            if mission.cate.cn in ['模拟宇宙', '饰品提取']:  # 模拟宇宙相关的增加沉浸器数量
                can_run_times += self.qty

            if can_run_times > 0:
                break
            plan = self.ctx.power_config.get_next_plan(plan)
            if plan is None:
                break

        if can_run_times == 0:
            return self.round_success(TrailblazePowerApp.STATUS_NO_ENOUGH_POWER)

        if can_run_times + plan.run_times > plan.plan_times:
            run_times = plan.plan_times - plan.run_times
        else:
            run_times = can_run_times

        log.info(f'准备挑战 {mission.mission_name} 次数 {run_times}')
        if run_times == 0:
            return self.round_success(TrailblazePowerApp.STATUS_PLAN_FINISHED)

        self.ctx.sim_uni_record.check_and_update_status()
        self.last_mission = mission

        if mission.cate.cn not in ['模拟宇宙', '饰品提取']:
            op = UseTrailblazePower(self.ctx, mission, plan.team_num, run_times,
                                    support=plan.support if plan.support != 'none' else None,
                                    on_battle_success=self._on_normal_task_success)
        elif mission.cate.cn == '模拟宇宙':
            sim_num = 0
            for i in SimUniWorldEnum:
                if i.value.name == mission.mission_name:
                    sim_num = i.value.idx

            if sim_num == 0:
                return self.round_fail('未支持模拟宇宙 %s', mission.mission_name)

            op = SimUniApp(self.ctx,
                           specified_uni_num=sim_num,
                           max_reward_to_get=run_times,
                           get_reward_callback=self._on_sim_uni_get_reward
                           )
            op.init_context_before_start = False
            op.stop_context_after_stop = False
            return self.round_by_op_result(op.execute())
        elif mission.cate.cn == '饰品提取':
            op = ChallengeOrnamentExtraction(self.ctx, mission,
                                             run_times=run_times,
                                             diff=0,
                                             file_num=plan.team_num,
                                             support_character=plan.support if plan.support != 'none' else None,
                                             get_reward_callback=self.on_oe_get_reward)
        else:
            return self.round_fail('未知副本类型')

        return self.round_by_op_result(op.execute())

    def _on_normal_task_success(self, finished_times: int, use_power: int):
        """
        普通副本获取一次奖励时候的回调
        :param finished_times: 完成次数
        :param use_power: 使用的体力
        :return:
        """
        log.info('挑战成功 完成次数 %d 使用体力 %d', finished_times, use_power)
        self.power -= use_power
        if self.power < 0:
            self.power = 0
        self.ctx.power_config.add_run_times(self.last_mission.unique_id, finished_times)

    def _on_sim_uni_get_reward(self, use_power: int, user_qty: int):
        """
        模拟宇宙 获取沉浸奖励后的回调
        :return:
        """
        log.info('获取沉浸奖励 使用体力 %d 使用沉浸器 %d', use_power, user_qty)
        self.ctx.power_config.add_run_times(self.last_mission.unique_id, 1)

        self.power -= use_power
        if self.power < 0:
            self.power = 0
        self.qty -= user_qty
        if self.qty < 0:
            self.qty = 0

    def on_oe_get_reward(self, qty: int):
        """
        饰品提取 获取奖励后的回调
        :return:
        """
        log.info('饰品提取获取奖励 次数 %d', qty)
        for _ in range(qty):
            if self.qty > 0:  # 优先使用沉浸器
                self.qty -= 1
            elif self.power >= self.last_mission.power:
                self.power -= self.last_mission.power

            self.ctx.power_config.add_run_times(self.last_mission.unique_id, 1)

    @node_from(from_name='检查当前需要挑战的关卡')
    @node_from(from_name='执行开拓力计划', status=STATUS_NO_PLAN)
    @node_from(from_name='执行开拓力计划', status=STATUS_NO_ENOUGH_POWER)
    @node_from(from_name='执行开拓力计划', status=STATUS_PLAN_FINISHED)
    @operation_node(name='完成后返回')
    def back_at_last(self) -> OperationRoundResult:
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())


def debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()
    op = TrailblazePowerApp(ctx)

    op.execute()


if __name__ == '__main__':
    debug()
