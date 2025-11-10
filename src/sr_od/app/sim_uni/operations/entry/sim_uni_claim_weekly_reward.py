from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class SimUniClaimWeeklyReward(SrOperation):

    def __init__(self, ctx: SrContext):
        """
        模拟宇宙 领取每周的积分奖励
        需要在模拟宇宙的主页面中使用
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('获取每周积分奖励')))

    @operation_node(name='等待画面', is_start_node=True)
    def _wait_ui(self) -> OperationRoundResult:
        """
        等待加载页面
        :return:
        """
        screen = self.screenshot()
        state = sim_uni_screen_state.get_sim_uni_initial_screen_state(self.ctx, screen)

        if state in [sim_uni_screen_state.ScreenState.SIM_TYPE_EXTEND.value,
                     sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value]:
            return self.round_success()
        else:
            return self.round_retry('未在模拟宇宙画面', wait=1)

    @node_from(from_name='等待画面')
    @operation_node(name='检查奖励')
    def _check_reward(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '每周奖励红点',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='检查奖励', status='每周奖励红点')
    @operation_node(name='领取奖励')
    def _claim_reward(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '每周奖励-一键领取',
                                                 success_wait=1, retry_wait=1)
