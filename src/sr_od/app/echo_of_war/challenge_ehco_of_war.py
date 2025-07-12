from cv2.typing import MatLike
from typing import Optional, Callable, ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.challenge_mission.choose_support_in_team import ChooseSupportInTeam
from sr_od.challenge_mission.click_challenge import ClickChallenge
from sr_od.challenge_mission.click_start_challenge import ClickStartChallenge
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideMission
from sr_od.interastral_peace_guide.guide_transport import GuideTransport
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.choose_team import ChooseTeam
from sr_od.screen_state import battle_screen_state
from sr_od.sr_map.operations.transport_to_recover import TransportToRecover


class ChallengeEchoOfWar(SrOperation):

    STATUS_WITH_DEAD: ClassVar[str] = '有阵亡角色'

    def __init__(self, ctx: SrContext, mission: GuideMission,
                 team_num: int, plan_times: int,
                 support: Optional[str] = None,
                 on_battle_success: Optional[Callable[[int, int], None]]=None):
        """
        挑战历战余响
        这里不关注有没有剩余次数 由调用方控制
        这里就算没有剩余次数也会进行挑战的
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s %s %d' % (
                                 gt('历战余响', 'game'),
                                 mission.display_name,
                                 gt('次数'),
                                 plan_times
                             ))

        self.mission: GuideMission = mission
        self.team_num: int = team_num
        self.support: str = support
        self.on_battle_success = on_battle_success
        self.plan_times: int = plan_times  # 计划挑战次数
        self.no_challenge_dialog: int = 0  # 没有阵亡的统计次数
        self.battle_fail_times: int = 0  # 战斗失败次数
        self.battle_success_times: int = 0  # 战斗成功次数

    @node_from(from_name='角色阵亡')
    @operation_node(name='传送', is_start_node=True)
    def tp(self) -> OperationRoundResult:
        op = GuideTransport(self.ctx, self.mission)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='传送')
    @operation_node(name='点击挑战')
    def click_challenge(self) -> OperationRoundResult:
        op = ClickChallenge(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击挑战')
    @operation_node(name='点击挑战后确认')
    def after_click_challenge(self) -> OperationRoundResult:
        """
        点击挑战后 判断当前有没有对话框 需保证点击挑战1秒后再触发
        :return:
        """
        screen = self.screenshot()

        result = self.check_dialog(screen)
        if result is not None:
            return result

        return self.round_success()

    @node_from(from_name='点击挑战后确认', status='开拓力弹框-取消')
    @node_from(from_name='点击开始挑战后确认', status='开拓力弹框-取消')
    @node_from(from_name='点击再来一次后确认', status='开拓力弹框-取消')
    @operation_node(name='体力不足')
    def exit_first_challenge_without_tp(self) -> OperationRoundResult:
        """
        点击挑战后 开拓力不足退出
        说明之前识别开拓力错了
        :return:
        """
        if self.on_battle_success is not None:
            self.on_battle_success(0, 200)  # 清空开拓力
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击挑战后确认', status='提示弹框-取消')
    @node_from(from_name='点击开始挑战后确认', status='提示弹框-取消')
    @node_from(from_name='点击再来一次后确认', status='提示弹框-取消')
    @operation_node(name='次数不足')
    def exit_first_challenge_with_full(self) -> OperationRoundResult:
        """
        点击挑战后 奖励次数用完退出
        :return:
        """
        self.ctx.echo_of_war_run_record.left_times = 0  # 清空剩余次数
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击挑战后确认', status='阵亡弹框-取消')
    @node_from(from_name='点击开始挑战后确认', status='阵亡弹框-取消')
    @node_from(from_name='点击再来一次后确认', status='阵亡弹框-取消')
    @operation_node(name='角色阵亡')
    def exit_to_recover(self) -> OperationRoundResult:
        """
        退出先恢复
        :return:
        """
        op = TransportToRecover(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击挑战后确认')
    @operation_node(name='选择配队')
    def choose_team(self) -> OperationRoundResult:
        op = ChooseTeam(self.ctx, self.team_num)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择配队')
    @operation_node(name='选择支援')
    def choose_support(self) -> OperationRoundResult:
        op = ChooseSupportInTeam(self.ctx, self.support)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择支援')
    @operation_node(name='点击开始挑战')
    def click_start_challenge(self) -> OperationRoundResult:
        op = ClickStartChallenge(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击开始挑战')
    @operation_node(name='点击开始挑战后确认')
    def after_click_start_challenge(self) -> OperationRoundResult:
        screen = self.screenshot()

        result = self.check_dialog(screen)
        if result is not None:
            return result

        return self.round_success()

    @node_from(from_name='点击开始挑战后确认')
    @node_from(from_name='点击再来一次后确认')
    @operation_node(name='等待战斗结果')
    def _wait_battle_result(self) -> OperationRoundResult:
        """
        等待战斗结果
        :return:
        """
        screen = self.screenshot()

        state = battle_screen_state.get_tp_battle_screen_state(self.ctx, screen, battle_success=True, battle_fail=True)

        if state == battle_screen_state.ScreenState.BATTLE_FAIL.value:
            self.battle_fail_times += 1
            return self.round_success(state)
        elif state ==battle_screen_state.ScreenState.BATTLE_SUCCESS.value:
            self.battle_success_times += 1
            if self.on_battle_success is not None:
                self.on_battle_success(1, self.mission.power)
            return self.round_success(state)
        else:
            return self.round_wait('等待战斗结束', wait=1)

    @node_from(from_name='等待战斗结果')
    @operation_node(name='战斗结果处理')
    def _after_battle_result(self) -> OperationRoundResult:
        """
        战斗结果出来后 点击再来一次或退出
        :return:
        """
        screen = self.screenshot()
        if self.battle_fail_times >= 5 or self.battle_success_times >= self.plan_times:  # 失败过多或者完成指定次数了 退出
            return self.round_by_find_and_click_area(screen, '战斗画面', '退出关卡按钮',
                                                     success_wait=2, retry_wait=1)
        else:  # 还需要继续挑战
            return self.round_by_find_and_click_area(screen, '战斗画面', '再来一次按钮',
                                                     success_wait=2, retry_wait=1)

    @node_from(from_name='战斗结果处理', status='再来一次按钮')
    @operation_node(name='点击再来一次后确认')
    def after_challenge_again(self) -> OperationRoundResult:
        """
        再来一次的确认 在有角色阵亡时候会弹出来
        :return:
        """
        screen = self.screenshot()

        result = self.check_dialog(screen)
        if result is not None:
            return result

        return self.round_success()

    def check_dialog(self, screen: MatLike) -> Optional[OperationRoundResult]:
        """
        识别有没有对话框
        :param screen:
        :return:
        """
        # 开拓力不足
        result1 = self.round_by_find_area(screen, '挑战副本', '开拓力弹框-标题')
        if result1.is_success:
            return self.round_by_find_and_click_area(screen, '挑战副本', '开拓力弹框-取消',
                                                     success_wait=1, retry_wait=1)

        # 挑战次数用完
        result3 = self.round_by_find_area(screen, '挑战副本', '提示弹框-标题')
        result4 = self.round_by_find_area(screen, '挑战副本', '提示弹框-次数用完')
        if result3.is_success and result4.is_success:
            return self.round_by_find_and_click_area(screen, '挑战副本', '提示弹框-取消',
                                                     success_wait=1, retry_wait=1)

        # 有阵亡角色
        result2 = self.round_by_find_area(screen, '挑战副本', '阵亡弹框-标题')
        if result2.is_success:
            return self.round_by_find_and_click_area(screen, '挑战副本', '阵亡弹框-取消',
                                                     success_wait=1, retry_wait=1)

    @node_from(from_name='体力不足')
    @node_from(from_name='次数不足')
    @node_from(from_name='战斗结果处理', status='退出关卡按钮')
    @operation_node(name='完成后返回')
    def back_at_last(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())
