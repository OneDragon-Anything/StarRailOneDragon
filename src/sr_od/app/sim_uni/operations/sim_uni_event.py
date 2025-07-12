from cv2.typing import MatLike
from typing import ClassVar, List, Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen.screen_area import ScreenArea
from one_dragon.utils import str_utils, cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.bless.sim_uni_choose_bless import SimUniChooseBless
from sr_od.app.sim_uni.operations.bless.sim_uni_drop_bless import SimUniDropBless
from sr_od.app.sim_uni.operations.bless.sim_uni_upgrade_bless import SimUniUpgradeBless
from sr_od.app.sim_uni.operations.curio.sim_uni_choose_curio import SimUniChooseCurio, SimUniDropCurio
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import battle_screen_state


class SimUniEventOption:

    def __init__(self, title: str, title_rect: Rect, confirm_rect: Optional[Rect] = None):
        self.title: str = title
        self.title_rect: Rect = title_rect
        self.confirm_rect: Optional[Rect] = confirm_rect  # 开始对话部分的选项不需要确认


class SimUniEvent(SrOperation):

    STATUS_NO_OPT: ClassVar[str] = '无选项'
    STATUS_CHOOSE_OPT_CONFIRM: ClassVar[str] = '需确定'
    STATUS_CHOOSE_OPT_NO_CONFIRM: ClassVar[str] = '无需确定'
    STATUS_CONFIRM_SUCCESS: ClassVar[str] = '确定成功'

    OPT_RECT: ClassVar[Rect] = Rect(1335, 204, 1826, 886)  # 选项所在的地方
    EMPTY_POS: ClassVar[Point] = Point(778, 880)

    def __init__(self, ctx: SrContext,
                 config: Optional[SimUniChallengeConfig] = None,
                 skip_first_screen_check: bool = True):
        """
        模拟宇宙 事件
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('事件', 'game')))

        self.opt_list: List[SimUniEventOption] = []
        self.chosen_opt_set: set[str] = set()  # 已经选择过的选项名称
        self.config: Optional[SimUniChallengeConfig] = ctx.sim_uni_challenge_config if config is None else config
        self.skip_first_screen_check: bool = skip_first_screen_check

    @operation_node(name='等待加载', is_start_node=True)
    def _wait(self) -> OperationRoundResult:
        self.ctx.detect_info.view_down = False  # 进入事件后 重置视角
        if self.skip_first_screen_check:
            return self.round_success()
        screen = self.screenshot()

        if sim_uni_screen_state.in_sim_uni_event(self.ctx, screen):
            return self.round_success()
        else:
            return self.round_retry('未在事件页面', wait=1)

    @node_from(from_name='等待加载')
    @node_from(from_name='确定后判断', status=sim_uni_screen_state.ScreenState.SIM_EVENT.value)
    @operation_node(name='选择选项')
    def _choose_opt_by_priority(self) -> OperationRoundResult:
        """
        根据优先级选一个选项
        目前固定选第一个
        :return:
        """
        screen = self.screenshot()
        self.opt_list = self._get_opt_list(screen)
        if self.ctx.env_config.is_debug:
            title = self._get_event_title(screen)
            if str_utils.find_by_lcs(gt('孤独太空美虫', 'game'), title, percent=0.5):
                pass
                # return self.round_fail('遇到需要测试的事件啦')

        if len(self.opt_list) == 0:
            # 有可能在对话
            self.ctx.controller.click(SimUniEvent.EMPTY_POS)
            return self.round_success(SimUniEvent.STATUS_NO_OPT, wait=0.5)
        else:
            return self._do_choose_opt(0)

    def _get_opt_list(self, screen: MatLike) -> List[SimUniEventOption]:
        """
        获取当前的选项
        :param screen:
        :return:
        """
        opt_list_1 = self._get_confirm_opt_list(screen)
        opt_list_2 = self._get_no_confirm_opt_list(screen)
        return opt_list_1 + opt_list_2

    def _get_confirm_opt_list(self, screen: MatLike) -> List[SimUniEventOption]:
        """
        获取当前需要确定的选项
        :param screen:
        :return:
        """
        part, _ = cv2_utils.crop_image(screen, SimUniEvent.OPT_RECT)
        match_result_list = self.ctx.tm.match_template(part, 'sim_uni', 'event_option_icon',
                                                       threshold=0.7, only_best=False)

        opt_list = []
        for mr in match_result_list:
            title_lt = SimUniEvent.OPT_RECT.left_top + mr.left_top + Point(30, 0)
            title_rb = SimUniEvent.OPT_RECT.left_top + mr.right_bottom + Point(430, 0)
            title_rect = Rect(title_lt.x, title_lt.y, title_rb.x, title_rb.y)

            title_part, _ = cv2_utils.crop_image(screen, title_rect)
            title = self.ctx.ocr.run_ocr_single_line(title_part)

            confirm_lt = SimUniEvent.OPT_RECT.left_top + mr.left_top + Point(260, 85)
            confirm_rb = SimUniEvent.OPT_RECT.left_top + mr.left_top + Point(440, 165)  #
            confirm_rect = Rect(confirm_lt.x, confirm_lt.y, confirm_rb.x, confirm_rb.y)
            # confirm_part, _ = cv2_utils.crop_image(screen, confirm_rect)
            # cv2_utils.show_image(confirm_part, wait=0)

            opt = SimUniEventOption(title, title_rect, confirm_rect)
            log.info('识别需确定选项 %s', opt.title)
            opt_list.append(opt)

        return opt_list

    def _get_no_confirm_opt_list(self, screen: MatLike) -> List[SimUniEventOption]:
        """
        获取当前不需要确定的选项
        :param screen:
        :return:
        """
        part, _ = cv2_utils.crop_image(screen, SimUniEvent.OPT_RECT)
        opt_list = []
        template_id_list = [
            'event_option_no_confirm_icon',
            'event_option_enhance_icon',
            'event_option_exit_icon'
        ]

        for template_id in template_id_list:
            match_result_list = self.ctx.tm.match_template(part, 'sim_uni', template_id,
                                                           threshold=0.7, only_best=False)

            for mr in match_result_list:
                title_lt = SimUniEvent.OPT_RECT.left_top + mr.left_top + Point(50, 0)
                title_rb = SimUniEvent.OPT_RECT.left_top + mr.right_bottom + Point(430, 0)
                title_rect = Rect(title_lt.x, title_lt.y, title_rb.x, title_rb.y)

                title_part, _ = cv2_utils.crop_image(screen, title_rect)
                title = self.ctx.ocr.run_ocr_single_line(title_part)

                opt = SimUniEventOption(title, title_rect)
                log.info('识别无需选项 %s', opt.title)
                opt_list.append(opt)

        return opt_list

    @node_from(from_name='选择选项', status=STATUS_CHOOSE_OPT_CONFIRM)
    @node_from(from_name='选择离开')
    @operation_node(name='确定')
    def _confirm(self):
        screen = self.screenshot()
        fake_area = ScreenArea(pc_rect=self.chosen_opt.confirm_rect, area_name='选项确定')

        result = self.round_by_ocr_and_click(screen, '确定', area=fake_area)

        if result.is_success:
            return self.round_success(SimUniEvent.STATUS_CONFIRM_SUCCESS, wait=2)
        elif result.status.startswith('找不到'):
            return self.round_success('无效选项')
        else:
            return self.round_success('点击确定失败', wait=0.25)

    def _do_choose_opt(self, idx: int) -> OperationRoundResult:
        """
        选择一个事件选项
        :param idx:
        :return:
        """
        click = self.ctx.controller.click(self.opt_list[idx].title_rect.center)
        if click:
            self.chosen_opt = self.opt_list[idx]
            self.chosen_opt_set.add(self.chosen_opt.title)
            if self.chosen_opt.confirm_rect is None:
                status = SimUniEvent.STATUS_CHOOSE_OPT_NO_CONFIRM
                return self.round_success(status, wait=1.5)
            else:
                status = SimUniEvent.STATUS_CHOOSE_OPT_CONFIRM
                return self.round_success(status, wait=1)
        else:
            return self.round_retry('点击选项失败', wait=0.5)

    @node_from(from_name='确定', status='无效选项')
    @operation_node(name='选择离开')
    def _choose_leave(self):
        """
        选择最后一个代表离开
        :return:
        """
        idx = len(self.opt_list) - 1

        # 部分事件没有离开选项 且最后一个选项可能无法选择 这里需要遍历还没有选过的选项
        while True:
            title = self.opt_list[idx].title
            chosen: bool = False
            for chosen_title in self.chosen_opt_set:
                if str_utils.find_by_lcs(chosen_title, title, percent=0.8):
                    chosen = True
                    break
            if chosen:
                idx -= 1
                if idx < 0:  # 应该不存在这种情况
                    return self.round_fail('所有选项都无效')
            else:
                break

        return self._do_choose_opt(idx)

    @node_from(from_name='确定', status=STATUS_CONFIRM_SUCCESS)
    @node_from(from_name='选择选项', status=STATUS_NO_OPT)
    @node_from(from_name='选择选项', status=STATUS_CHOOSE_OPT_NO_CONFIRM)
    @node_from(from_name='选择祝福')
    @node_from(from_name='丢弃祝福')
    @node_from(from_name='祝福强化')
    @node_from(from_name='选择奇物')
    @node_from(from_name='丢弃奇物')
    @node_from(from_name='点击空白处关闭')
    @node_from(from_name='战斗')
    @operation_node(name='确定后判断')
    def _check_after_confirm(self) -> OperationRoundResult:
        """
        确定后判断下一步动作
        :return:
        """
        screen = self.screenshot()
        state = self._get_screen_state(screen)
        if state is None:
            return self.round_retry('未能判断当前页面', wait=1)
        else:
            return self.round_success(state)

    def _get_screen_state(self, screen: MatLike) -> Optional[str]:
        state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            in_world=True,
            empty_to_close=True,
            bless=True,
            drop_bless=True,
            upgrade_bless=True,
            curio=True,
            drop_curio=True,
            event=True,
            battle=True)
        log.info('当前画面状态 %s', state)
        if state is not None:
            return state

        # 未知情况都先点击一下
        self.round_by_click_area('模拟宇宙', '点击空白处关闭')
        return None

    @node_from(from_name='确定后判断', status=sim_uni_screen_state.ScreenState.SIM_BLESS.value)
    @operation_node(name='选择祝福')
    def _choose_bless(self) -> OperationRoundResult:
        op = SimUniChooseBless(self.ctx, config=self.config)
        op_result = op.execute()

        if op_result.success:
            return self.round_success(wait=1)
        else:
            return self.round_retry(status=op_result.status)

    @node_from(from_name='确定后判断', status=sim_uni_screen_state.ScreenState.SIM_DROP_BLESS.value)
    @operation_node(name='丢弃祝福')
    def _drop_bless(self) -> OperationRoundResult:
        op = SimUniDropBless(self.ctx, config=self.config)
        op_result = op.execute()

        if op_result.success:
            return self.round_success()
        else:
            return self.round_retry(status=op_result.status)

    @node_from(from_name='确定后判断', status=sim_uni_screen_state.ScreenState.SIM_UPGRADE_BLESS.value)
    @operation_node(name='祝福强化')
    def _upgrade_bless(self) -> OperationRoundResult:
        op = SimUniUpgradeBless(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='确定后判断', status=sim_uni_screen_state.ScreenState.SIM_CURIOS.value)
    @operation_node(name='选择奇物')
    def _choose_curio(self) -> OperationRoundResult:
        op = SimUniChooseCurio(self.ctx, config=self.config)
        op_result = op.execute()

        if op_result.success:
            return self.round_success()
        else:
            return self.round_retry(status=op_result.status)

    @node_from(from_name='确定后判断', status=sim_uni_screen_state.ScreenState.SIM_DROP_CURIOS.value)
    @operation_node(name='丢弃奇物')
    def _drop_curio(self) -> OperationRoundResult:
        op = SimUniDropCurio(self.ctx, config=self.config)
        op_result = op.execute()

        if op_result.success:
            return self.round_success()
        else:
            return self.round_retry(status=op_result.status)

    @node_from(from_name='确定后判断', status=sim_uni_screen_state.ScreenState.EMPTY_TO_CLOSE.value)
    @operation_node(name='点击空白处关闭')
    def _click_empty_to_continue(self) -> OperationRoundResult:
        return self.round_by_click_area('模拟宇宙', '点击空白处关闭',
                                        success_wait=2, retry_wait=1)

    @node_from(from_name='确定后判断', status=battle_screen_state.ScreenState.BATTLE.value)
    @operation_node(name='战斗')
    def _battle(self) -> OperationRoundResult:
        # op = SimUniEnterFight(self.ctx,
        #                       bless_config=self.bless_priority,
        #                       curio_config=self.curio_priority)
        # op_result = op.execute()
        #
        # if op_result.success:
        #     return self.round_success()
        # else:
        #     return self.round_fail(status=op_result.status)
        # 这里似乎不用进去战斗画面也可以
        return self.round_success(wait=1)

    def _get_event_title(self, screen: MatLike) -> str:
        """
        获取当前事件的名称
        :return:
        """
        area = self.ctx.screen_loader.get_area('模拟宇宙', '事件标题')
        part = cv2_utils.crop_image_only(screen, area.rect)
        return self.ctx.ocr.run_ocr_single_line(part)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.sim_uni_info.world_num = 8
    ctx.init_for_sim_uni()
    ctx.start_running()
    op = SimUniEvent(ctx)
    op.execute()


if __name__ == '__main__':
    __debug()
