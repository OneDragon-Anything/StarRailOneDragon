from typing import Optional, Callable

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.div_uni.operations.choose_oe_file import ChooseOeFile
from sr_od.app.div_uni.operations.choose_oe_support import ChooseOeSupport
from sr_od.app.sim_uni.operations.move_v1.sim_uni_move_to_enemy_by_mm import SimUniMoveToEnemyByMiniMap
from sr_od.challenge_mission.choose_challenge_times import ChooseChallengeTimes
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideMission
from sr_od.interastral_peace_guide.guide_transport import GuideTransport
from sr_od.operations.battle.start_fight_for_elite import StartFightForElite
from sr_od.operations.battle.wait_battle_result import WaitBattleResult
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import battle_screen_state


class ChallengeOrnamentExtraction(SrOperation):

    def __init__(self, ctx: SrContext, mission: GuideMission, run_times: int,
                 diff: int, file_num: int, support_character: str,
                 get_reward_callback: Optional[Callable[[int], None]] = None):
        SrOperation.__init__(self, ctx, op_name=gt('饰品提取', 'game'))

        self.mission: GuideMission = mission
        """需要挑战的副本"""

        self.run_times: int = run_times
        """需要挑战的次数"""

        self.file_num: int = file_num
        """需要使用的存档 0为不选择"""

        self.diff: int = diff
        """需要挑战的难度 0为不选择"""

        self.support_character: str = support_character
        """需要使用的支援角色 None为不是用"""

        self.get_reward_callback: Callable[[int], None] = get_reward_callback
        """挑战成功后 获取奖励的回调"""

    def handle_init(self) -> Optional[OperationRoundResult]:
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """

        self.battle_fail_times: int = 0
        """战斗失败次数"""

        self.battle_success_times: int = 0
        """战斗胜利的次数"""

        return None

    @operation_node(name='传送', is_start_node=True)
    def tp(self) -> OperationRoundResult:
        """
        TODO 未加入难度选择
        识别当前画面
        :return:
        """
        op = GuideTransport(self.ctx, self.mission)
        return self.round_by_op_result(op.execute())

    # def choose_diff(self) -> OperationRoundResult:
    #     """
    #     选择难度
    #     :return:
    #     """
    #     if self.diff == 0:
    #         return self.round_success('默认难度')
    #     if self.diff < 0 or self.diff > 5:
    #         return self.round_fail('难道只支持1~5')
    #
    #     diff_opts = [
    #         ScreenGuide.OE_DIFF_OPT_1.value,
    #         ScreenGuide.OE_DIFF_OPT_2.value,
    #         ScreenGuide.OE_DIFF_OPT_3.value,
    #         ScreenGuide.OE_DIFF_OPT_4.value,
    #         ScreenGuide.OE_DIFF_OPT_5.value
    #     ]
    #
    #     self.ctx.controller.click(ScreenGuide.OE_DIFF_DROPDOWN.value.center)
    #     time.sleep(0.5)
    #
    #     area = diff_opts[self.diff - 1]
    #     self.ctx.controller.click(area.center)
    #     time.sleep(0.5)
    #
    #     return self.round_success()

    # todo 这个函数是不是没用
    # @node_from(from_name='传送')
    # @operation_node(name='选择存档')
    # def choose_file(self) -> OperationRoundResult:
    #     op = ChooseOeFile(self.ctx, self.file_num)
    #     return self.round_by_op_result(op.execute())

    @node_from(from_name='传送')
    @operation_node(name='选择支援')
    def choose_support(self) -> OperationRoundResult:
        op = ChooseOeSupport(self.ctx, self.support_character)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择支援')
    @node_from(from_name='选择支援', success=False)
    @operation_node(name='选择挑战次数')
    def click_challenge_times(self) -> OperationRoundResult:
        log.info('本次挑战次数 %d', self.run_times)
        if self.run_times > 1:
            op = ChooseChallengeTimes(self.ctx, min(6, self.run_times), mission_type='饰品提取')
            return self.round_by_op_result(op.execute())
        else:
            return self.round_success()

    @node_from(from_name='选择挑战次数')
    @operation_node(name='点击挑战')
    def click_challenge(self) -> OperationRoundResult:
        """
        点击挑战
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '饰品提取', '按钮-开始挑战',
                                                 success_wait=2, retry_wait=1)

    @node_from(from_name='点击挑战')
    @operation_node(name='等待副本加载', node_max_retry_times=20)
    def wait_mission_loaded(self) -> OperationRoundResult:
        """
        等待副本加载
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_area(screen, '大世界', '角色图标', retry_wait=1)

    @node_from(from_name='等待副本加载')
    @operation_node(name='向红点移动')
    def move_by_red(self) -> OperationRoundResult:
        op = SimUniMoveToEnemyByMiniMap(self.ctx, no_attack=True, stop_after_arrival=True)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='向红点移动')
    @operation_node(name='进入战斗')
    def start_fight(self) -> OperationRoundResult:
        op = StartFightForElite(self.ctx, skip_point_check=True, skip_resurrection_check=True)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='进入战斗')
    @node_from(from_name='处理战斗结果', status='再来一次按钮')
    @operation_node(name='等待战斗结果')
    def wait_battle_result(self) -> OperationRoundResult:
        """
        等待战斗结果
        :return:
        """
        op = WaitBattleResult(self.ctx, try_attack=True)
        op_result = op.execute()
        if not op_result.success:
            return self.round_by_op_result(op_result)

        if op_result.status == battle_screen_state.ScreenState.BATTLE_FAIL.value:
            self.battle_fail_times += 1
            return self.round_by_op_result(op_result)
        elif op_result.status == battle_screen_state.ScreenState.BATTLE_SUCCESS.value:
            self.battle_success_times += 1
            if self.get_reward_callback is not None:
                self.get_reward_callback(1)
            return self.round_by_op_result(op_result)
        else:
            return self.round_fail('未知状态')

    @node_from(from_name='等待战斗结果')
    @operation_node(name='处理战斗结果')
    def after_battle_result(self) -> OperationRoundResult:
        """
        战斗结果出来后 点击再来一次或退出
        :return:
        """
        screen = self.screenshot()
        if self.battle_fail_times >= 5 or self.battle_success_times >= self.run_times:  # 失败过多或者完成指定次数了 退出
            area_name = '退出关卡按钮'
        else:  # 还需要继续挑战
            area_name = '再来一次按钮'

        return self.round_by_find_and_click_area(screen, '战斗画面', area_name,
                                                 success_wait=2, retry_wait_round=0.5)

    @node_from(from_name='处理战斗结果', status='退出关卡按钮')
    @operation_node(name='等待退出', node_max_retry_times=20)
    def wait_back(self) -> OperationRoundResult:
        """
        等待退出到大世界
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_area(screen, '大世界', '角色图标', retry_wait=1)
