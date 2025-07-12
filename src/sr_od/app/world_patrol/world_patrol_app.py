import time

from typing import List, Optional, ClassVar

from one_dragon.base.operation.application_run_record import AppRunRecord
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.sr_application import SrApplication
from sr_od.app.world_patrol.world_patrol_route import WorldPatrolRoute
from sr_od.app.world_patrol.world_patrol_run_route import WorldPatrolRunRoute
from sr_od.app.world_patrol.world_patrol_whitelist_config import load_all_whitelist_list, WorldPatrolWhitelist
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.cancel_mission_trace import CancelMissionTrace
from sr_od.operations.team.choose_team_in_world import ChooseTeamInWorld


class WorldPatrolApp(SrApplication):

    STATUS_ALL_ROUTE_FINISHED: ClassVar[str] = '所有路线已完成'

    def __init__(self, ctx: SrContext,
                 whitelist: Optional[WorldPatrolWhitelist] = None,
                 ignore_record: bool = False,
                 team_num: Optional[int] = None):
        SrApplication.__init__(self, ctx, 'world_patrol', op_name=gt('锄大地'),
                               run_record=ctx.world_patrol_record if not ignore_record else None,
                               need_notify=True)
        self.route_list: List[WorldPatrolRoute] = []
        self.current_route_idx: int = 0
        self.ignore_record: bool = ignore_record
        self.current_route_start_time = time.time()  # 当前路线开始时间
        self.current_fail_times: int = 0  # 当前路线的失败次数

        self.team_num: Optional[int] = team_num
        self.param_whitelist: WorldPatrolWhitelist = whitelist

    @operation_node(name='加载路线', is_start_node=True)
    def load_route_list(self) -> OperationRoundResult:
        whitelist = self.param_whitelist

        if whitelist is None:
            whitelist_id = self.ctx.world_patrol_config.whitelist_id
            valid_whitelist_id_list = load_all_whitelist_list()
            if whitelist_id in valid_whitelist_id_list:
                whitelist = WorldPatrolWhitelist(whitelist_id)

        self.route_list = self.ctx.world_patrol_route_data.load_all_route(
            whitelist=whitelist,
            finished=[] if self.ignore_record else self.ctx.world_patrol_record.finished
        )
        self.current_route_idx = 0

        if len(self.route_list) == 0:
            return self.round_success(WorldPatrolApp.STATUS_ALL_ROUTE_FINISHED)
        else:
            self.ctx.init_for_world_patrol()
            return self.round_success()

    @node_from(from_name='加载路线')
    @operation_node(name='返回大世界')
    def back_to_normal_world(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='返回大世界')
    @operation_node(name='取消任务追踪')
    def cancel_trace(self) ->OperationRoundResult:
        op = CancelMissionTrace(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='取消任务追踪')
    @operation_node(name='选择配队')
    def _choose_team(self) -> OperationRoundResult:
        """
        选择配队
        :return:
        """
        team_num = self.ctx.world_patrol_config.team_num if self.team_num is None else self.team_num
        if team_num == 0:
            return self.round_success('无配队配置')
        op = ChooseTeamInWorld(self.ctx, team_num)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择配队')
    @node_from(from_name='运行路线')
    @operation_node(name='运行路线')
    def _run_route(self):
        if self.current_route_idx >= len(self.route_list):
            return self.round_success(WorldPatrolApp.STATUS_ALL_ROUTE_FINISHED)
        route = self.route_list[self.current_route_idx]

        self.current_route_start_time = time.time()
        op = WorldPatrolRunRoute(self.ctx, route)
        route_result = op.execute().success

        if route_result:
            if not self.ignore_record:
                self.save_record(route.unique_id, time.time() - self.current_route_start_time)
            self.current_fail_times = 0
            self.current_route_idx += 1
            return self.round_success()
        elif self.current_fail_times < 1:  # 失败时 进行一次重试
            log.info('准备重试当前路线')
            self.current_fail_times += 1
            return self.round_success()
        else:  # 失败次数到达阈值 进行下一条路线
            self.current_fail_times = 0
            self.current_route_idx += 1
            return self.round_success()

    @node_from(from_name='加载路线', status=STATUS_ALL_ROUTE_FINISHED)
    @node_from(from_name='运行路线', status=STATUS_ALL_ROUTE_FINISHED)
    @operation_node(name='完成')
    def finished(self) -> OperationRoundResult:
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        return self.round_success()

    def save_record(self, route_id: str, time_cost: float):
        """
        保存当天运行记录
        :param route_id: 路线ID
        :param time_cost: 使用时间
        :return:
        """
        self.ctx.world_patrol_record.add_record(route_id, time_cost)

    # def estimate_end_time(self):
    #     """
    #     剩余路线预估的完成时间
    #     :return:
    #     """
    #     total = - (time.time() - self.current_route_start_time)
    #     for i in range(self.current_route_idx, len(self.route_id_list)):
    #         total += self.ctx.world_patrol_record.get_estimate_time(self.route_id_list[i])
    #
    #         if total < 0:  # 只有第一条，也就是当前线路时会为负
    #             total = 0
    #
    #     return total

    def after_operation_done(self, result: OperationResult):
        SrApplication.after_operation_done(self, result)
        if self.ignore_record:
            return
        if not result.success:
            self.ctx.world_patrol_record.update_status(AppRunRecord.STATUS_FAIL)
            return

        for route in self.route_list:
            route_id = route.unique_id
            if route_id not in self.ctx.world_patrol_record.finished:
                self.ctx.world_patrol_record.update_status(AppRunRecord.STATUS_FAIL)
                return

        self.ctx.world_patrol_record.update_status(AppRunRecord.STATUS_SUCCESS)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    app = WorldPatrolApp(ctx)
    app.execute()


if __name__ == '__main__':
    __debug()