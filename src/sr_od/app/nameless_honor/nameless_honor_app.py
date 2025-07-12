import time

from cv2.typing import MatLike
from typing import ClassVar

from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.menu import phone_menu_utils, phone_menu_const
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu
from sr_od.screen_state import common_screen_state


class NamelessHonorApp(SrApplication):

    STATUS_WITH_ALERT: ClassVar[str] = '红点'
    STATUS_NO_ALERT: ClassVar[str] = '无红点'

    def __init__(self, ctx: SrContext):
        """
        1. 从菜单打开无名勋礼 如果有红点的话
        2. 到Tab-2领取点数 如果有红点的话
        3. 到Tab-1领取奖励 如果有的话
        4. 返回菜单
        """
        SrApplication.__init__(self, ctx, 'nameless_honor', op_name=gt('无名勋礼', 'game'),
                               run_record=ctx.nameless_honor_run_record, need_notify=True)

    @operation_node(name='开始前返回', is_start_node=True)
    def back_at_first(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始前返回')
    @operation_node(name='打开菜单')
    def open_menu(self) -> OperationRoundResult:
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开菜单')
    @operation_node(name='点击无名勋礼')
    def _click_honor(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        result: MatchResult = phone_menu_utils.get_phone_menu_item_pos(self.ctx, screen, phone_menu_const.NAMELESS_HONOR, alert=True)
        if result is None:
            return self.round_success(NamelessHonorApp.STATUS_NO_ALERT)
        else:
            self.ctx.controller.click(result.center)
            return self.round_success(NamelessHonorApp.STATUS_WITH_ALERT, wait=1)

    @node_from(from_name='点击无名勋礼', status=STATUS_WITH_ALERT)
    @operation_node(name='点击任务')
    def _click_tab_2(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        result: MatchResult = phone_menu_utils.get_nameless_honor_tab_pos(self.ctx, screen, 2, alert=True)
        if result is None:
            return self.round_success(NamelessHonorApp.STATUS_NO_ALERT)
        else:
            self.ctx.controller.click(result.center)
            return self.round_success(NamelessHonorApp.STATUS_WITH_ALERT, wait=1)

    @node_from(from_name='点击任务')
    @operation_node(name='领取任务奖励')
    def _claim_task(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        result = self.round_by_find_and_click_area(screen, '菜单', '无名勋礼-任务-一键领取')

        if result.is_success:
            time.sleep(2)
            self.round_by_click_area('菜单', '无名勋礼-点击空白处关闭')  # 可能会出现一个升级的画面 多点击一次
            time.sleep(1)
            return self.round_success()
        else:
            return self.round_retry(wait=1)

    @node_from(from_name='点击任务', status=STATUS_NO_ALERT)  # 任务没有红点时 返回奖励
    @node_from(from_name='领取任务奖励')  # 领取任务奖励后 返回奖励
    @node_from(from_name='领取任务奖励', success=False)  # 有新任务的时候这里会有红点 但不会有领取按钮 因此失败也继续
    @operation_node(name='点击奖励')
    def _click_tab_1(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        result: MatchResult = phone_menu_utils.get_nameless_honor_tab_pos(self.ctx, screen, 1, alert=True)
        if result is None:
            return self.round_success(NamelessHonorApp.STATUS_NO_ALERT)
        else:
            self.ctx.controller.click(result.center)
            return self.round_success(NamelessHonorApp.STATUS_WITH_ALERT, wait=1)

    @node_from(from_name='点击奖励')
    @operation_node(name='领取奖励')
    def _claim_reward(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()

        return self.round_by_find_and_click_area(screen, '菜单', '无名勋礼-奖励-一键领取',
                                                 success_wait=2, retry_wait=0.5)

    @node_from(from_name='领取奖励')
    @node_from(from_name='领取奖励', success=False)  # 没有奖励领取时也返回成功
    @operation_node(name='领取奖励后')
    def _check_screen_after_reward(self) -> OperationRoundResult:
        """
        可能出现选择奖励的框 通过判断左上角标题判断
        :return:
        """
        screen = self.screenshot()
        if common_screen_state.in_secondary_ui(self.ctx, screen, '无名勋礼'):
            return self.round_success(wait=0.2)

        area_name_list = [
            '无名勋礼-奖励-取消',
            '无名勋礼-点击空白处关闭'
        ]
        for area_name in area_name_list:
            result = self.round_by_find_and_click_area(screen, '菜单', area_name)
            if result.is_success:
                return self.round_wait(result.status, wait=1)

        return self.round_retry('未知画面状态', wait=1)

    @node_from(from_name='点击无名勋礼', status=STATUS_NO_ALERT)  # 无名勋礼没有红点
    @node_from(from_name='点击奖励', status=STATUS_NO_ALERT)  # 奖励没有红点
    @node_from(from_name='领取奖励后')
    @operation_node(name='完成后返回')
    def back_at_last(self) -> OperationRoundResult:
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())