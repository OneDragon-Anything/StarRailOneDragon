from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation import Operation
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.challenge_mission.battle_wait_windows import (
    WAIT_RESULT_CLEANUP_TIMEOUT_SECONDS,
    WAIT_RESULT_TIMEOUT_SECONDS,
)
from sr_od.challenge_mission.choose_support_in_team import ChooseSupportInTeam
from sr_od.challenge_mission.click_challenge import ClickChallenge
from sr_od.challenge_mission.click_start_challenge import ClickStartChallenge
from sr_od.challenge_mission.resume_from_battle_fail import ResumeFromBattleFail
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.choose_team import ChooseTeam
from sr_od.screen_state import battle_screen_state
from sr_od.sr_map.operations.transport_to_recover import TransportToRecover

# 弹窗防线与战斗等待识别用的画面档(周本挑战画面独立建档,含弹窗组镜像;
# 挑战按钮点击走 ClickChallenge 的「挑战副本」通用几何,与画面档无冲突)
SCREEN_WEEKLY: str = '挑战副本-历战余响'

# 结算交互封顶:「点击恒成功但锚恒不出现」的 until 无界等待防线。
# 退出关卡/再来一次是即时交互,不搬 25 分钟战斗等待窗口径。
RESULT_SETTLE_TIMEOUT_SECONDS: int = 3 * 60

# 战斗等待窗家族口径:单一源在 challenge_mission/battle_wait_windows(WAIT_RESULT_TIMEOUT_SECONDS,
# 贪饕侵蚀实测最坏 20分49秒 + 余量;周本实测约 2分23秒/场,属兜底口径挪用)。
# 主窗(等待战斗结果)与二次观察窗(战斗超时收尾)同取,二次窗内仍无结算才是真死锁。

# 对外出口 status(模块层常量:包装层按名导入做全名单分支,不随类被桩替换漂移)
STATUS_NOT_IN_CHALLENGE_SCREEN: str = '不在历战余响挑战画面'
STATUS_PLAN_FINISHED: str = '已完成计划次数'
STATUS_TIMEOUT_VICTORY_EXITED: str = '超时胜利已退出'
STATUS_GIVE_UP_ON_LOSING_STREAK: str = '连败放弃'
STATUS_TIMES_EXHAUSTED: str = '本周次数耗尽'
STATUS_POWER_INSUFFICIENT: str = '开拓力不足'
STATUS_WITH_DEAD_RECOVERED: str = '有阵亡角色已复活'
STATUS_BATTLE_DEADLOCK: str = '战斗超时无结算'


class ChallengeEchoOfWarCore(SrOperation):
    """在历战余响挑战画面发起挑战并完成指定次数的自动战斗循环。
    起点:挑战副本-历战余响·挑战态(无弹窗覆盖,入口导航归调用方);终点:按结果落
    挑战画面或大世界(有阵亡角色复活后),以运行结果 status 为准。
    副作用:消耗周本挑战次数与开拓力(30/次,指南档位数据),真实不可逆;
    调用方发起前须向用户说明并获同意。
    战斗失败走版本更新新形态适配(共享失败继续件),连败 5 次放弃。

    :param ctx: 上下文
    :param team_num: 队伍编号,从 1 起;0 = 不切队沿用当前编队
    :param plan_times: 计划成功次数,>=1
    :param support: 支援角色 ID;None = 不用支援('none' 的翻译在带 mission 语义的
        包装层完成,本 op 兜底归一:'none' 与 None 同样跳过支援)
    """

    # 内部路由 status(非对外出口,类体内以裸名供 @node_from 引用):
    # 弹窗取消点击结果、弹窗迟到等待、战斗态值、超时收尾分流
    # (对外出口 status 在模块层常量,包装层/测试按名导入,类内不设副本防双源)
    _ROUTE_DEATH_CANCEL: ClassVar[str] = '阵亡弹框-取消'
    _ROUTE_NO_DIALOG: ClassVar[str] = '无对话框'
    _ROUTE_RETRY_INITIATE: ClassVar[str] = '重试再发起'
    _ROUTE_TIMEOUT_VICTORY: ClassVar[str] = '超时胜利待退出'
    _ROUTE_TIMEOUT_FAIL: ClassVar[str] = '超时判负'

    def __init__(self, ctx: SrContext, team_num: int, plan_times: int,
                 support: str | None = None):
        if plan_times < 1:
            raise ValueError(f'计划成功次数须 >=1,得到 {plan_times}')
        if team_num < 0:
            raise ValueError(f'队伍编号从 1 起(0=沿用当前编队),得到 {team_num}')

        SrOperation.__init__(self, ctx, op_name=gt('历战余响挑战循环'))

        self.team_num: int = team_num
        self.plan_times: int = plan_times
        # 'none' 兜底归一(防线):包装层翻译是主责,这里保证委托链只见到 None
        self.support: str | None = None if support in (None, 'none') else support
        self.battle_success_times: int = 0  # 已成功次数(供代码调用方读取)
        self.battle_fail_times: int = 0  # 已失败次数(供代码调用方读取)

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def entry_check(self) -> OperationRoundResult:
        """
        画面级判定:只认周本挑战画面,不符显式失败(禁逐 area 试命中推断)
        :return:
        """
        screen = self.last_screenshot
        matched = self.check_and_update_current_screen(
            screen, screen_name_list=[SCREEN_WEEKLY])
        if matched == SCREEN_WEEKLY:
            return self.round_success()
        self.save_screenshot(prefix='入口核对')
        return self.round_fail(STATUS_NOT_IN_CHALLENGE_SCREEN)

    @node_from(from_name='入口核对')
    @node_from(from_name='失败画面继续', status=_ROUTE_RETRY_INITIATE)
    @operation_node(name='点击挑战', node_max_retry_times=10)
    def click_challenge(self) -> OperationRoundResult:
        """
        委托 ClickChallenge(子 op 只处理点击,编队态等待由弹窗防线循环承担)
        :return:
        """
        op = ClickChallenge(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击挑战')
    @operation_node(name='挑战后确认', node_max_retry_times=10)
    def confirm_after_challenge(self) -> OperationRoundResult:
        """
        挑战后三弹窗防线;无弹窗重试等待(弹窗迟到),预算耗尽=编队态已就绪
        :return:
        """
        screen = self.last_screenshot
        result = self._check_dialogs(screen)
        if result is not None:
            return result
        return self.round_retry(self._ROUTE_NO_DIALOG, wait=0.5)

    @node_from(from_name='挑战后确认', success=False, status=_ROUTE_NO_DIALOG)
    @operation_node(name='选择配队')
    def choose_team(self) -> OperationRoundResult:
        """
        委托 ChooseTeam(0 = 跳过选择沿用当前编队,子 op 内判定)
        :return:
        """
        op = ChooseTeam(self.ctx, self.team_num)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择配队')
    @operation_node(name='选择支援', node_max_retry_times=10)
    def choose_support(self) -> OperationRoundResult:
        """
        None/none 归一后委托 ChooseSupportInTeam(只认 None)
        :return:
        """
        if self.support is None:
            return self.round_success()
        op = ChooseSupportInTeam(self.ctx, self.support)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择支援')
    @operation_node(name='点击开始挑战')
    def click_start_challenge(self) -> OperationRoundResult:
        """
        委托 ClickStartChallenge
        :return:
        """
        op = ClickStartChallenge(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击开始挑战')
    @operation_node(name='编队后确认', node_max_retry_times=10)
    def confirm_after_start(self) -> OperationRoundResult:
        """
        开始挑战后三弹窗防线;无弹窗重试等待,预算耗尽=战斗已开始
        :return:
        """
        screen = self.last_screenshot
        result = self._check_dialogs(screen)
        if result is not None:
            return result
        return self.round_retry(self._ROUTE_NO_DIALOG, wait=0.5)

    @node_from(from_name='编队后确认', success=False, status=_ROUTE_NO_DIALOG)
    @node_from(from_name='再来一次后确认', success=False, status=_ROUTE_NO_DIALOG)
    # 上限仅为防真死锁的兜底窗(家族口径,单一源见 use_trailblaze_power 常量注释);
    # 正常战斗按结算画面信号识别结束,超时到点转「战斗超时收尾」继续观察
    @operation_node(name='等待战斗结果', timeout_seconds=WAIT_RESULT_TIMEOUT_SECONDS)
    def wait_battle_result(self) -> OperationRoundResult:
        """
        等待战斗结果(信号驱动轮询)
        :return:
        """
        screen = self.screenshot()
        state = battle_screen_state.get_tp_battle_screen_state(
            self.ctx, screen, battle_success=True, battle_fail=True)

        if state == battle_screen_state.ScreenState.BATTLE_FAIL.value:
            self.battle_fail_times += 1
            return self.round_success(state, wait=1)  # 稍等让失败画面就绪
        elif state == battle_screen_state.ScreenState.BATTLE_SUCCESS.value:
            self.battle_success_times += 1
            log.info('挑战成功 当前成功次数 %d', self.battle_success_times)
            return self.round_success(state, wait=1)  # 稍等让结算画面就绪
        else:
            return self.round_wait('等待战斗结束', wait=1)

    @node_from(from_name='等待战斗结果',
               status=battle_screen_state.ScreenState.BATTLE_SUCCESS.value)
    # 结算交互封顶:退出关卡/再来一次是即时交互,until 无界等待需交互级防线
    @operation_node(name='战斗结果处理', timeout_seconds=RESULT_SETTLE_TIMEOUT_SECONDS)
    def after_battle_success(self) -> OperationRoundResult:
        """
        胜利后:达标点退出关卡(验证挑战画面回归),未达标点再来一次
        :return:
        """
        screen = self.last_screenshot
        if self.battle_success_times >= self.plan_times:
            click_result = self.round_by_find_and_click_area(
                screen, '战斗画面', '退出关卡按钮',
                success_wait=2, retry_wait=1,
                until_find_all=[(SCREEN_WEEKLY, '标题-历战余响')])
            if click_result.is_success:
                return self.round_success(STATUS_PLAN_FINISHED)
            return click_result
        else:
            return self.round_by_find_and_click_area(
                screen, '战斗画面', '再来一次按钮',
                success_wait=2, retry_wait=1)

    @node_from(from_name='等待战斗结果',
               status=battle_screen_state.ScreenState.BATTLE_FAIL.value)
    @node_from(from_name='战斗超时收尾', status=_ROUTE_TIMEOUT_FAIL)
    @operation_node(name='失败画面继续')
    def after_battle_fail(self) -> OperationRoundResult:
        """
        委托共享失败继续件回挑战画面,再决策:连败达阈值放弃,否则重新发起
        :return:
        """
        op = ResumeFromBattleFail(self.ctx)
        op_result = op.execute()
        if not op_result.success:
            # 失败画面未能离开:原样透传交上层处置
            return self.round_by_op_result(op_result)
        if self.battle_fail_times >= 5:
            return self.round_success(STATUS_GIVE_UP_ON_LOSING_STREAK)
        return self.round_success(self._ROUTE_RETRY_INITIATE)

    @node_from(from_name='战斗结果处理', status='再来一次按钮')
    @operation_node(name='再来一次后确认', node_max_retry_times=10)
    def confirm_after_challenge_again(self) -> OperationRoundResult:
        """
        再来一次后三弹窗防线(弹窗盖在战斗结算画面上);无弹窗=战斗已开始
        :return:
        """
        screen = self.last_screenshot
        result = self._check_dialogs(screen)
        if result is not None:
            return result
        return self.round_retry(self._ROUTE_NO_DIALOG, wait=0.5)

    @node_from(from_name='挑战后确认', status=_ROUTE_DEATH_CANCEL)
    @node_from(from_name='编队后确认', status=_ROUTE_DEATH_CANCEL)
    @node_from(from_name='再来一次后确认', status=_ROUTE_DEATH_CANCEL)
    @operation_node(name='阵亡传送恢复')
    def recover_after_death(self) -> OperationRoundResult:
        """
        阵亡弹窗取消后传送复活点复活;复活停大世界,重入归调用方(核心退出、入口无关)
        :return:
        """
        op = TransportToRecover(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_success(STATUS_WITH_DEAD_RECOVERED)
        return self.round_by_op_result(op_result)

    @node_from(from_name='等待战斗结果', success=False, status=Operation.STATUS_TIMEOUT)
    # 与主等待窗统一取家族常量口径:主窗语义 = 战斗死锁兜底,超时后不清场继续
    # 观察至结算(贪饕教训防战场残留,机制照 use_trailblaze_power 同名节点)
    @operation_node(name='战斗超时收尾', timeout_seconds=WAIT_RESULT_CLEANUP_TIMEOUT_SECONDS)
    def wait_battle_result_timeout(self) -> OperationRoundResult:
        """
        主等待窗超时的收尾观察:见结算分流,仍无结算继续等待
        :return:
        """
        screen = self.screenshot()
        state = battle_screen_state.get_tp_battle_screen_state(
            self.ctx, screen, battle_success=True, battle_fail=True)

        if state == battle_screen_state.ScreenState.BATTLE_SUCCESS.value:
            # 主窗被打断导致计数缺失:战斗实际胜利且奖励已发,补记保证计数一致
            self.battle_success_times += 1
            log.info('超时后战斗结束 挑战成功 补记成功次数 %d',
                     self.battle_success_times)
            return self.round_success(self._ROUTE_TIMEOUT_VICTORY)
        elif state == battle_screen_state.ScreenState.BATTLE_FAIL.value:
            return self.round_success(self._ROUTE_TIMEOUT_FAIL)
        else:
            # 游戏内战斗仍在自打:继续观察(结算信号由上面分支识别)
            return self.round_wait('超时后继续等待战斗结束', wait=5)

    @node_from(from_name='战斗超时收尾', status=_ROUTE_TIMEOUT_VICTORY)
    @operation_node(name='超时退出与达标判定', timeout_seconds=RESULT_SETTLE_TIMEOUT_SECONDS)
    def exit_after_timeout(self) -> OperationRoundResult:
        """
        超时胜利收尾:点退出关卡验证挑战画面回归后按达标与否落终态
        (达标判定在点击成功之后——until 重入期间不得提前判达标)
        :return:
        """
        screen = self.last_screenshot
        click_result = self.round_by_find_and_click_area(
            screen, '战斗画面', '退出关卡按钮',
            success_wait=2, retry_wait=1,
            until_find_all=[(SCREEN_WEEKLY, '标题-历战余响')])
        if not click_result.is_success:
            return click_result
        if self.battle_success_times >= self.plan_times:
            return self.round_success(STATUS_PLAN_FINISHED)
        log.info('超时胜利未达计划 成功 %d/计划 %d',
                 self.battle_success_times, self.plan_times)
        return self.round_success(STATUS_TIMEOUT_VICTORY_EXITED)

    @node_from(from_name='战斗超时收尾', success=False, status=Operation.STATUS_TIMEOUT)
    @operation_node(name='战斗卡死终局')
    def battle_deadlock_end(self) -> OperationRoundResult:
        """
        二次观察窗仍无结算的真死锁:自定义失败文案落终态(框架超时默认文案经此转换)
        :return:
        """
        self.save_screenshot(prefix='战斗卡死终局')
        return self.round_fail(STATUS_BATTLE_DEADLOCK)

    def _check_dialogs(self, screen: MatLike) -> OperationRoundResult | None:
        """
        三弹窗防线:开拓力不足 / 本周次数耗尽 / 有阵亡角色(结构照家族
        use_trailblaze_power.check_dialog,识别区域用周本挑战画面镜像副本)
        命中并处理返回对应结果;无弹窗返回 None(调用方 round_retry 等待)
        :param screen: 游戏截图
        :return:
        """
        # 开拓力不足
        result = self.round_by_find_area(screen, SCREEN_WEEKLY, '开拓力弹框-标题')
        if result.is_success:
            click_result = self.round_by_find_and_click_area(
                screen, SCREEN_WEEKLY, '开拓力弹框-取消', success_wait=1, retry_wait=1)
            if click_result.is_success:
                return self.round_success(STATUS_POWER_INSUFFICIENT)
            return click_result

        # 本周次数耗尽(标题+正文双锚,防与阵亡提示弹窗同标题误判)
        if (self.round_by_find_area(screen, SCREEN_WEEKLY, '提示弹框-标题').is_success
                and self.round_by_find_area(
                    screen, SCREEN_WEEKLY, '提示弹框-次数用完').is_success):
            click_result = self.round_by_find_and_click_area(
                screen, SCREEN_WEEKLY, '提示弹框-取消', success_wait=1, retry_wait=1)
            if click_result.is_success:
                return self.round_success(STATUS_TIMES_EXHAUSTED)
            return click_result

        # 有阵亡角色(取消后由边路由到传送恢复)
        result = self.round_by_find_area(screen, SCREEN_WEEKLY, '阵亡弹框-标题')
        if result.is_success:
            return self.round_by_find_and_click_area(
                screen, SCREEN_WEEKLY, '阵亡弹框-取消', retry_wait=1)

        return None
