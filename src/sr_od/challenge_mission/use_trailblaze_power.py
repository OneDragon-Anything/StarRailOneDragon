from PIL.ImageChops import screen
from typing import Optional, Callable, ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.challenge_mission.choose_challenge_times import ChooseChallengeTimes
from sr_od.challenge_mission.choose_support_in_team import ChooseSupportInTeam
from sr_od.challenge_mission.click_challenge import ClickChallenge
from sr_od.challenge_mission.click_start_challenge import ClickStartChallenge
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideMission
from sr_od.interastral_peace_guide.guide_transport import GuideTransport
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.choose_team import ChooseTeam
from sr_od.operations.wait.wait_in_world import WaitInWorld
from sr_od.screen_state import battle_screen_state
from sr_od.sr_map.operations.transport_to_recover import TransportToRecover


class UseTrailblazePower(SrOperation):

    STATUS_WITH_DEAD: ClassVar[str] = '有阵亡角色'
    STATUS_CHALLENGE_EXIT_AGAIN: ClassVar[str] = '退出关卡后再来一次'

    def __init__(self, ctx: SrContext, mission: GuideMission,
                 team_num: int, plan_times: int, support: Optional[str] = None,
                 on_battle_success: Optional[Callable[[int, int], None]] = None):
        """
        使用开拓力刷本
        :param ctx: 上下文
        :param mission: 挑战关卡
        :param team_num: 使用配队编号
        :param support: 使用支援 传入角色ID
        :param plan_times: 计划挑战次数
        :param on_battle_success: 战斗成功的回调 用于记录、扣体力等
        """

        SrOperation.__init__(
            self, ctx, op_name='%s %s %d' % (
                gt(mission.unique_id),
                gt('次数'),
                plan_times)
        )

        self.mission: GuideMission = mission
        self.team_num: int = team_num
        self.support: Optional[str] = support
        self.plan_times: int = plan_times  # 计划挑战次数
        self.on_battle_success: Optional[Callable[[int, int], None]] = on_battle_success
        self.current_challenge_times: int = 1  # 当前挑战的次数
        self.finish_times: int = 0  # 已经完成的次数
        self.battle_fail_times: int = 0  # 战斗失败次数

    @node_from(from_name='阵亡传送恢复')
    @operation_node(name='传送', is_start_node=True)
    def transport(self) -> OperationRoundResult:
        """
        传送
        :return:
        """
        op = GuideTransport(self.ctx, self.mission)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='传送')
    @operation_node(name='选择次数')
    def _before_click_challenge(self) -> OperationRoundResult:
        """
        点击挑战之前的初始化 由不同副本自行实现
        :return:
        """
        self.current_challenge_times = self._get_current_challenge_times()
        log.info('本次挑战次数 %d', self.current_challenge_times)
        if self.current_challenge_times > 1:
            op = ChooseChallengeTimes(self.ctx, self.current_challenge_times, mission_type='其他')
            return self.round_by_op_result(op.execute())
        else:
            return self.round_success()

    def _get_current_challenge_times(self) -> int:
        """
        获取当前的挑战次数
        :return:
        """
        current_challenge_times = self.plan_times - self.finish_times
        if self.mission.cate.cn in ['拟造花萼（金）', '拟造花萼（赤）']:
            return min(24, current_challenge_times)
        elif self.mission.cate.cn == '凝滞虚影':
            return min(8, current_challenge_times)
        elif self.mission.cate.cn == '侵蚀隧洞':
            return min(6, current_challenge_times)
        # elif self.mission.cate.cn == '饰品提取':
        #     return min(6, current_challenge_times)
        return 1

    @node_from(from_name='选择次数')
    @operation_node(name='点击挑战')
    def click_challenge(self) -> OperationRoundResult:
        op = ClickChallenge(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击挑战')
    @operation_node(name='点击挑战后确认')
    def confirm_after_click_challenge(self) -> OperationRoundResult:
        """
        点击挑战后 判断当前有没有对话框 需保证点击挑战1秒后再触发
        :return:
        """
        screen = self.screenshot()

        result1 = self.round_by_find_area(screen, '挑战副本', '开拓力弹框-标题')
        if result1.is_success:
            if self.on_battle_success is not None:
                self.on_battle_success(0, 200)  # 清空开拓力
            return self.round_by_find_and_click_area(screen, '挑战副本', '开拓力弹框-取消',
                                                     success_wait=1, retry_wait=1)

        result2 = self.round_by_find_area(screen, '挑战副本', '阵亡弹框-标题')
        if result2.is_success:
            return self.round_by_find_and_click_area(screen, '挑战副本', '阵亡弹框-取消',
                                                     retry_wait=1)

        return self.round_retry('无对话框', wait=0.3)

    @node_from(from_name='点击挑战后确认', success=False, status='无对话框')
    @operation_node(name='选择配队')
    def choose_team(self) -> OperationRoundResult:
        op = ChooseTeam(self.ctx, self.team_num)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择配队')
    @operation_node(name='选择支援')
    def _choose_support(self):
        """
        选择支援
        :return:
        """
        if self.support is None:
            return self.round_success()
        op = ChooseSupportInTeam(self.ctx, self.support)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择支援')
    @operation_node(name='点击开始挑战')
    def click_start_challenge(self) -> OperationRoundResult:
        op = ClickStartChallenge(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击开始挑战')
    @operation_node(name='开始挑战后')
    def _after_start_challenge(self) -> OperationRoundResult:
        """
        点击开始挑战后 进入战斗前
        :return:
        """
        screen = self.screenshot()
        # 有阵亡角色
        result2 = self.round_by_find_area(screen, '挑战副本', '阵亡弹框-标题')
        if result2.is_success:
            return self.round_by_find_and_click_area(screen, '挑战副本', '阵亡弹框-取消',
                                                     success_wait=1, retry_wait=1)


        if self.mission.cate.cn == '凝滞虚影':
            op = WaitInWorld(self.ctx, wait=5, wait_after_success=1)  # 等待怪物苏醒
            op_result = op.execute()
            if not op_result.success:
                # 使用指南传送后 凝滞虚影会直接进入战斗 不需要平A
                return self.round_success('未在大世界画面')
            self.ctx.controller.move('w', press_time=1)
            self.ctx.controller.initiate_attack()
            return self.round_success(wait=1)
        else:
            return self.round_success()

    @node_from(from_name='开始挑战后')
    @node_from(from_name='再来一次后确认')
    @node_from(from_name='再来一次后确认', success=False, status='无对话框')
    @operation_node(name='等待战斗结果', timeout_seconds=600)
    def _wait_battle_result(self) -> OperationRoundResult:
        """
        等待战斗结果
        :return:
        """
        screen = self.screenshot()

        state = battle_screen_state.get_tp_battle_screen_state(
            self.ctx, screen,
            battle_success=True, battle_fail=True)

        if state == battle_screen_state.ScreenState.BATTLE_FAIL.value:
            self.battle_fail_times += 1
            return self.round_success(state, wait=1)  # 稍微等待 让按键可按
        elif state == battle_screen_state.ScreenState.BATTLE_SUCCESS.value:
            self.finish_times += self.current_challenge_times
            log.info('挑战成功，当前完成次数 %d', self.finish_times)
            if self.on_battle_success is not None:
                self.on_battle_success(self.current_challenge_times, self.mission.power * self.current_challenge_times)
            return self.round_success(state, wait=1)  # 稍微等待 让按键可按
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
        if self.battle_fail_times >= 5 or self.finish_times >= self.plan_times:  # 失败过多或者完成指定次数了 退出
            return self.round_by_find_and_click_area(screen, '战斗画面', '退出关卡按钮',
                                                     success_wait=2, retry_wait=1)
        else:  # 还需要继续挑战
            next_challenge_times = self._get_current_challenge_times()  # 看下一次挑战轮数是否跟当前一致
            if next_challenge_times != self.current_challenge_times:  # 需要退出再来一次
                return self.round_by_find_and_click_area(screen, '战斗画面', '退出关卡按钮',
                                                         success_wait=2, retry_wait=1)
            else:
                return self.round_by_find_and_click_area(screen, '战斗画面', '再来一次按钮',
                                                         success_wait=2, retry_wait=1)

    @node_from(from_name='战斗结果处理', status='再来一次按钮')
    @operation_node(name='再来一次后确认')
    def confirm_after_challenge_again(self) -> OperationRoundResult:
        screen = self.screenshot()

        result1 = self.round_by_find_area(screen, '挑战副本', '开拓力弹框-标题')
        if result1.is_success:
            if self.on_battle_success is not None:
                self.on_battle_success(0, 200)  # 清空开拓力
            return self.round_by_find_and_click_area(screen, '挑战副本', '开拓力弹框-取消',
                                                     success_wait=1, retry_wait=1)

        result2 = self.round_by_find_area(screen, '挑战副本', '阵亡弹框-标题')
        if result2.is_success:
            return self.round_by_find_and_click_area(screen, '挑战副本', '阵亡弹框-取消',
                                                     retry_wait=1)

        return self.round_retry('无对话框', wait=0.5)

    @node_from(from_name='开始挑战后', status='阵亡弹框-取消')
    @node_from(from_name='再来一次后确认', status='阵亡弹框-取消')
    @operation_node(name='阵亡传送恢复')
    def tp_to_recover(self) -> OperationRoundResult:
        """
        退出先恢复
        :return:
        """
        op = TransportToRecover(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from('点击挑战后确认', success=False)
    @node_from('点击挑战后确认', status='开拓力弹框-取消')
    @node_from('点击挑战后确认', status='退出关卡按钮')
    @operation_node(name='完成后退出')
    def back_at_last(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())


def __debug_op():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()

    tab = ctx.guide_data.best_match_tab_by_name('生存索引')
    category = ctx.guide_data.best_match_category_by_name('拟造花萼（赤）', tab)
    mission = ctx.guide_data.best_match_mission_by_name('存护之蕾', category, '克劳克影视乐园')

    op = UseTrailblazePower(ctx, mission, 2, 7)

    op.execute()


if __name__ == '__main__':
    __debug_op()