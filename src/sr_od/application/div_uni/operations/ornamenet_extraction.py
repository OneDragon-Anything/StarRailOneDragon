from typing import Optional, Callable

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.match_result import MatchResultList
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils, cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.div_uni.operations.choose_oe_file import ChooseOeFile
from sr_od.application.div_uni.operations.choose_oe_support import ChooseOeSupport
from sr_od.application.sim_universe.operations.move_v1.sim_uni_move_to_enemy_by_mm import SimUniMoveToEnemyByMiniMap
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
                 diff: int, file_num: int, team_name: str, support_character: str,
                 get_reward_callback: Optional[Callable[[int], None]] = None):
        SrOperation.__init__(self, ctx, op_name=gt('饰品提取', 'game'))

        self.mission: GuideMission = mission
        """需要挑战的副本"""

        self.run_times: int = run_times
        """需要挑战的次数"""

        self.choose_times: int = 1
        """单次挑战选择的次数"""

        self.file_num: int = file_num
        """需要使用的存档 0为不选择"""

        self.team_name: str = team_name
        """预设编队名称"""

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

    @node_from(from_name='等待退出', status='重新选择次数')
    @operation_node(name='传送', is_start_node=True, screenshot_before_round=False)
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

    @node_from(from_name='传送')
    @operation_node(name='选择存档', screenshot_before_round=False)
    def choose_file(self) -> OperationRoundResult:
        op = ChooseOeFile(self.ctx, self.file_num)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择存档')
    @operation_node(name='点击预设编队按钮', screenshot_before_round=False)
    def click_predefined_team(self) -> OperationRoundResult:
        if len(self.team_name) == 0:
            return self.round_success('使用默认编队')
        result = self.round_by_click_area('饰品提取', '支援入队踢4号位角色')
        if result.is_success:
            return self.round_by_find_and_click_area(self.screenshot(), '饰品提取', '按钮-预设编队',
                                                     success_wait=1, retry_wait=1)
        return result

    @node_from(from_name='点击预设编队按钮')
    @operation_node(name='选择预设编队')
    def choose_predefined_team(self) -> OperationRoundResult:
        area = self.ctx.screen_loader.get_area('饰品提取', '区域-预设编队名称')
        part = cv2_utils.crop_image_only(self.last_screenshot, area.rect)
        ocr_result_map = self.ctx.ocr.run_ocr(part)

        name_list = []
        mrl_list: list[MatchResultList] = []
        for ocr_word, mrl in ocr_result_map.items():
            name_list.append(ocr_word)
            mrl_list.append(mrl)

        # 找队伍
        team_idx = str_utils.find_best_match_by_difflib(gt(self.team_name), name_list, cutoff=0.5)
        if team_idx is not None:
            self.ctx.controller.click(area.left_top + mrl_list[team_idx][0].center)
            return self.round_success(wait=0.5)

        # 没找到, 向上滑动翻页
        drag_start = Point(area.rect.x1 + 100, area.rect.y2 - 300)
        drag_end = Point(area.rect.x1 + 100, area.rect.y1 + 100)
        self.ctx.controller.drag_to(start=drag_start, end=drag_end)
        # 拖动之后列表会有惯性, 鼠标点一下消除惯性, 防止拖过头
        self.ctx.controller.click()
        return self.round_retry('未找到编队: ' + self.team_name, wait=1)

    @node_from(from_name='点击预设编队按钮', status='使用默认编队')
    @node_from(from_name='选择预设编队')
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
            self.choose_times = min(6, self.run_times)
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
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(screen, '饰品提取', '按钮-开始挑战',
                                                 success_wait=2, retry_wait=1)

    @node_from(from_name='点击挑战')
    @operation_node(name='等待副本加载', node_max_retry_times=20)
    def wait_mission_loaded(self) -> OperationRoundResult:
        """
        等待副本加载。
        途中可能弹对话框(编队角色位空缺等),只认「角色图标」会盲等超时
        (2026-08-24 实证:支援角色未找到 → 编队 3 人 → 「当前编队中仍有
        角色位空缺,是否继续出战?」弹窗卡住 20 次失败)。
        处置:默认选「确认」继续出战——外层开拓力计划按「计划次数未完成
        会一直重试」的语义循环,点取消+FAIL 会死循环重进同一弹窗;继续出战
        让战斗进行,打不过(battle_fail_times≥5)反而是可靠的中断器(用户定调)。
        """
        screen = self.last_screenshot

        # 开拓力不足 → 点取消(打不了,同历战余响 check_dialog 语义;次数由外层体力门控)
        result = self.round_by_find_area(screen, '挑战副本', '开拓力弹框-标题')
        if result.is_success:
            return self.round_by_find_and_click_area(
                screen, '挑战副本', '开拓力弹框-取消',
                success_wait=1, retry_wait=1,
            )

        # 其余提示类弹窗(编队空缺/次数用完/阵亡)→ 点确认继续出战
        for title_area in ('提示弹框-标题', '阵亡弹框-标题'):
            result = self.round_by_find_area(screen, '挑战副本', title_area)
            if result.is_success:
                confirm_area = title_area.replace('标题', '确认')
                return self.round_by_find_and_click_area(
                    screen, '挑战副本', confirm_area,
                    success_wait=2, retry_wait=1,
                )

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
            self.battle_success_times += self.choose_times
            if self.get_reward_callback is not None:
                self.get_reward_callback(self.choose_times)
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
        screen = self.last_screenshot
        if self.battle_fail_times >= 5 or self.battle_success_times + self.choose_times > self.run_times:  # 失败过多或者再来一次就会超出指定次数 退出
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
        screen = self.last_screenshot
        result = self.round_by_find_area(screen, '大世界', '角色图标', retry_wait=1)

        # 如果未完成指定次数, 则继续打
        if result.is_success and self.battle_fail_times < 5 and self.battle_success_times < self.run_times:
            return self.round_success('重新选择次数')
        return result

