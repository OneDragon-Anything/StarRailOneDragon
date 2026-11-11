
from cv2.typing import MatLike

from one_dragon.base.config.basic_game_config import TypeInputWay
from one_dragon.base.config.one_dragon_config import InstanceRun
from one_dragon.base.controller.pc_clipboard import PcClipboard
from one_dragon.base.matcher.match_result import MatchResultList
from one_dragon.base.matcher.ocr import ocr_utils
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.sim_universe import sim_uni_screen_state
from sr_od.application.sim_universe.operations.auto_run.sim_uni_wait_level_start import (
    SimUniWaitLevelStart,
)
from sr_od.application.sim_universe.operations.sim_uni_enter_fight import (
    SimUniEnterFight,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation

# 每个版本出现一次的剧情提醒弹窗(新版本主线引导)的判定词与跳过词。
# 双词同时存在才算命中:单词易与他屏同位文字误配;按钮位置随版本浮动,
# 无法建档固定 area,走全屏 OCR(difflib 匹配口径同 check_screen_to_interact)。
STORY_REMINDER_WORDS: list[str] = ['稍后再看', '观看前情提要']
STORY_REMINDER_SKIP_WORD: str = '稍后再看'

# 未知画面兜底(点右上角返回,处理新角色跃迁宣传页)的三道闸参数。
UNKNOWN_FALLBACK_ROUNDS: int = 3  # 连续全不命中达到该轮数才点:转场/加载/弹回空窗只持续 1-2 轮,计数门槛挡住瞬时误触
LOGIN_PAGE_MARK_WORD: str = '公告'  # 登录页标志词:登录页右上角是公告等菜单按钮热区而非返回语义,与「右上角返回」坐标重叠,兜底须排除(两个登录页版式都有公告按钮)


class EnterGame(SrOperation):

    def __init__(self, ctx: SrContext, switch: bool = False):
        """
        进入游戏后 进行登陆
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name=gt('进入游戏'))

        self.force_login: bool = (self.ctx.one_dragon_config.instance_run == InstanceRun.ALL.value.value
            and len(self.ctx.one_dragon_config.instance_list_in_od) > 1)

        # 切换账号的情况下 一定需要登录
        if switch:
            self.force_login = True

        self.already_login: bool = False  # 是否已经登录了
        self.use_clipboard: bool = self.ctx.game_config.type_input_way == TypeInputWay.CLIPBOARD.value.value  # 使用剪切板输入
        self._login_clicked: bool = False  # 「文本-点击进入」已命中过:登录页已通过,之后才可能遇到版本宣传页(未知画面兜底的启用闸)
        self._unknown_rounds: int = 0  # 连续全不命中的轮次计数:命中已知画面即清零,只在尾部兜底累计
        self._last_ocr_map: dict[str, MatchResultList] | None = None  # 最近一轮全屏 OCR 结果(check_screen_to_interact 产出,兜底排除登录页复用,避免重复跑 OCR)

    @node_from(from_name='国服-输入账号密码')
    @node_from(from_name='登陆其他账号')
    @operation_node(name='画面识别', node_max_retry_times=60, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.last_screenshot

        login_result = self.check_login_related(screen)
        if login_result is not None:
            return login_result

        interact_result = self.check_screen_to_interact(screen)
        if interact_result is not None:
            return interact_result

        login_result = self.check_login_related(screen)
        if login_result is not None:
            self._unknown_rounds = 0
            return login_result

        interact_result = self.check_screen_to_interact(screen)
        if interact_result is not None:
            self._unknown_rounds = 0
            return interact_result

        in_game_result = self.round_by_find_area(screen, '大世界', '角色图标')
        if in_game_result.is_success:  # 右上角有角色图标
            self._unknown_rounds = 0
            return self.round_success(status='大世界', wait=1)

        # 未知画面兜底:连续多轮全不命中才点右上角返回,处理新角色跃迁画面(每个
        # 版本更新后弹出的整屏版本宣传页:右上角关闭钮无文字、全图无稳定文本锚,
        # OCR 词兜底失效;关闭钮与「菜单-右上角返回」坐标一致,实机点击一次即关闭验证)。
        # 三道闸防误触(登录页右上角是公告等菜单按钮热区,坐标与返回钮重叠,曾误开公告):
        # ①登录页未通过前整个不启用(登录后才有宣传页);②连续 UNKNOWN_FALLBACK_ROUNDS
        # 轮全不命中(转场/加载/弹回空窗只持续 1-2 轮);③本轮 OCR 有登录页标志词则跳过。
        # pc_alt 按最坏光标态点(未知态可能是锁光标恢复态,自由光标下 Alt+点击无害);
        # round_retry 计入节点 retry 上限,点击无效时有界失败不永动。
        self._unknown_rounds += 1
        if self._login_clicked and self._unknown_rounds >= UNKNOWN_FALLBACK_ROUNDS:
            login_mark_map = (ocr_utils.match_all_words(self._last_ocr_map, [LOGIN_PAGE_MARK_WORD])
                              if self._last_ocr_map is not None else {})
            if len(login_mark_map) == 0:
                fallback_area = self.ctx.screen_loader.get_area('菜单', '右上角返回')
                if fallback_area is not None:
                    self.ctx.controller.click(fallback_area.center, pc_alt=True)
        return self.round_retry(wait=1)

    def check_login_related(self, screen: MatLike) -> OperationRoundResult:
        """
        判断登陆相关的出现内容
        :param screen: 游戏画面
        :return: 是否有相关操作 有的话返回对应操作结果
        """
        # 判断“错误提示-重新启动”
        result_restart = self.round_by_find_and_click_area(screen, '进入游戏', '错误提示-重新启动')
        if result_restart.is_success:
            # 点击到“重新启动”，说明需要检查本地网络连接情况。
            return self.round_fail("获取全局分发错误，登录失败，请检查网络设置并重新启动脚本")

        if self.force_login and not self.already_login:
            result = self.round_by_find_area(screen, '进入游戏', '文本-点击进入')
            if result.is_success:
                result2 = self.round_by_find_and_click_area(screen, '进入游戏', '按钮-登出确定')
                if result2.is_success:
                    return self.round_wait(result2.status, wait=2)

                result2 = self.round_by_find_area(screen, '进入游戏-退出登陆', '标题-退出登录')
                if result2.is_success:
                    return self.round_success(result2.status)

                result2 = self.round_by_find_and_click_area(screen, '进入游戏', '按钮-登出')
                if result2.is_success:
                    return self.round_wait(result2.status, wait=1)

                return self.round_retry(result2.status, wait=1)
            else:
                result2 = self.round_by_find_and_click_area(screen, '进入游戏-选择账号', '按钮-登陆其他账号')
                if result2.is_success:
                    return self.round_wait(result2.status, wait=1)
        else:
            result = self.round_by_find_and_click_area(screen, '进入游戏', '文本-点击进入')
            if result.is_success:
                self._login_clicked = True
                return self.round_wait(result.status, wait=1)

            result = self.round_by_find_and_click_area(screen, '进入游戏', '提示-确认')
            if result.is_success:
                # 如果检测到了“提示-确认”并点击
                return self.round_wait(status=result.status, wait=1)

        result = self.round_by_find_and_click_area(screen, '进入游戏', '国服-账号密码')
        if result.is_success:
            return self.round_success(result.status, wait=1)

        result = self.round_by_find_and_click_area(screen, '进入游戏', '文本-开始游戏')
        if result.is_success:
            return self.round_wait(result.status, wait=1)

        return None

    @node_from(from_name='画面识别', status='国服-账号密码')
    @operation_node(name='国服-输入账号密码')
    def input_account_password(self) -> OperationRoundResult:
        if self.ctx.game_account_config.account == '' or self.ctx.game_account_config.password == '':
            return self.round_fail('未配置账号密码')

        screen = self.last_screenshot
        self.round_by_click_area('进入游戏', '国服-账号输入区域')
        self._interruptible_sleep(0.5)
        if self.use_clipboard:
            PcClipboard.copy_and_paste(self.ctx.game_account_config.account)
        else:
            self.ctx.controller.keyboard_controller.keyboard.type(self.ctx.game_account_config.account)
        self._interruptible_sleep(1.5)

        self.round_by_click_area('进入游戏', '国服-密码输入区域')
        self._interruptible_sleep(0.5)
        if self.use_clipboard:
            PcClipboard.copy_and_paste(self.ctx.game_account_config.password)
        else:
            self.ctx.controller.keyboard_controller.keyboard.type(self.ctx.game_account_config.password)
        self._interruptible_sleep(1.5)

        result = self.round_by_find_area(screen, '进入游戏', '文本-同意-旧')
        if result.is_success:
            self.round_by_click_area('进入游戏', '国服-同意按钮-旧')

        result = self.round_by_find_area(screen, '进入游戏', '文本-同意-新')
        if result.is_success:
            self.round_by_click_area('进入游戏', '国服-同意按钮')
        self._interruptible_sleep(0.5)

        screen = self.screenshot()
        self.already_login = True
        return self.round_by_find_and_click_area(screen, '进入游戏', '国服-账号密码进入游戏',
                                                 success_wait=5, retry_wait=1)

    @node_from(from_name='画面识别', status='标题-退出登录')
    @operation_node(name='退出并保留登陆记录')
    def logout_with_account_kept(self) -> OperationRoundResult:
        screen = self.last_screenshot
        self.round_by_click_area('进入游戏-退出登陆', '按钮-退出并保留登陆记录', success_wait=1)
        return self.round_by_find_and_click_area(screen, '进入游戏-退出登陆', '按钮-退出',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='退出并保留登陆记录')
    @operation_node(name='登陆其他账号')
    def choose_other_account(self) -> OperationRoundResult:
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(screen, '进入游戏-选择账号', '按钮-登陆其他账号',
                                                 success_wait=1, retry_wait=1)

    def check_screen_to_interact(self, screen: MatLike) -> OperationRoundResult | None:
        """
        判断画面 处理可能出现的需要交互的情况
        :param screen: 游戏画面
        :return: 是否有相关操作 有的话返回对应操作结果
        """
        result = self.check_sim_uni(screen)
        if result is not None:
            return result

        ocr_result_map = self.ctx.ocr.run_ocr(screen)
        self._last_ocr_map = ocr_result_map  # 存到实例供尾部兜底复用(登录页排除判定),避免兜底重复跑全屏 OCR

        target_word_list: list[str] = [
            '确认',  # 登陆失败 issue #442
            '点击领取今日补给',  # 小月卡
        ]
        ignore_list: list[str] = [
        ]
        target_word_idx_map: dict[str, int] = {}
        to_match_list: list[str] = []
        for idx, target_word in enumerate(target_word_list):
            target_word_idx_map[target_word] = idx
            to_match_list.append(gt(target_word, 'game'))

        match_word, match_word_mrl = ocr_utils.match_word_list_by_priority(
            ocr_result_map,
            target_word_list,
            ignore_list=ignore_list
        )
        if match_word is not None and match_word_mrl is not None and match_word_mrl.max is not None:
            for mr in match_word_mrl:
                self.ctx.controller.click(mr.center)
                self._interruptible_sleep(1)
            return self.round_wait(status=match_word)

        story_result = self.check_story_reminder(ocr_result_map)
        if story_result is not None:
            return story_result

        return None

    def check_sim_uni(self, screen: MatLike) -> OperationRoundResult | None:
        """
        判断是否有模拟宇宙相关的画面

        Args:
            screen: 游戏画面

        Returns:
            是否有相关操作 有的话返回对应操作结果
        """
        state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            bless=True, drop_bless=True,
            sim_uni=True,
        )
        if state is not None:
            if state == sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value:
                op = SimUniWaitLevelStart(self.ctx)
            else:
                op = SimUniEnterFight(self.ctx)
            return self.round_by_op_result(op.execute())
        else:
            return None

    def check_story_reminder(self, ocr_result_map: dict[str, MatchResultList]) -> OperationRoundResult | None:
        """
        检测每个版本出现一次的剧情提醒弹窗(新版本主线引导,按钮组如「开始/稍后再看/
        观看前情提要」),命中则点「稍后再看」跳过——bot 不应自动开始版本主线剧情。

        判据:判定词全部同时存在才动作(常量 STORY_REMINDER_WORDS 注释里的误配理由);
        点击后 round_retry 逐帧重识别——点击可能不落地,WAIT 不消耗 retry 会死循环
        (同 BackToNormalWorldPlus 弹窗分支先例);点掉后下一轮由「角色图标」分支 SUCCESS。

        :param ocr_result_map: 复用 check_screen_to_interact 已跑的全屏 OCR 结果
        :return: 命中并点击后返回 round 结果;未命中返回 None
        """
        match_map = ocr_utils.match_all_words(ocr_result_map, STORY_REMINDER_WORDS)
        if len(match_map) < len(STORY_REMINDER_WORDS):
            return None

        skip_mrl = match_map.get(STORY_REMINDER_SKIP_WORD)
        if skip_mrl is None or skip_mrl.max is None:
            return None

        log.info('[进入游戏] 命中版本剧情提醒弹窗,点击「%s」跳过', STORY_REMINDER_SKIP_WORD)
        self.ctx.controller.click(skip_mrl.max.center)
        return self.round_retry('版本剧情提醒', wait=1)

    @node_from(from_name='画面识别', status='大世界')
    @operation_node(name='等待画面加载')
    def wait_game(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()
    app = EnterGame(ctx, switch=True)
    app.execute()


if __name__ == '__main__':
    __debug()

