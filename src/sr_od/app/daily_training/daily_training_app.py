from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guid_choose_tab import GuideChooseTab
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.menu import phone_menu_const, phone_menu_utils
from sr_od.operations.menu.click_phone_menu_item import ClickPhoneMenuItem
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu
from sr_od.screen_state import common_screen_state


class DailyTrainingApp(SrApplication):

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, 'daily_training',
                               op_name=gt('每日实训', 'game'),
                               run_record=ctx.daily_training_run_record,
                               need_notify=True)

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
    @operation_node(name='点击指南')
    def click_guide(self) -> OperationRoundResult:
        op = ClickPhoneMenuItem(self.ctx, phone_menu_const.INTERASTRAL_GUIDE)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点击指南')
    @operation_node(name='选择每日实训')
    def guide_choose_tab(self) -> OperationRoundResult:
        tab = self.ctx.guide_data.best_match_tab_by_name(gt('每日实训', 'game'))
        op = GuideChooseTab(self.ctx, tab)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择每日实训')
    @operation_node(name='领取点数')
    def claim_score(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()

        target_cn_list: list[str] = [
            '领取',
            '已领取',
        ]
        ignore_cn_list: list[str] = [
            '已领取'
        ]

        result = self.round_by_ocr_and_click_by_priority(screen, target_cn_list, ignore_cn_list)
        if result.is_success:
            return self.round_wait(status=result.status, wait=1)
        else:
            return self.round_retry(status=result.status, wait=0.5)

    @node_from(from_name='领取点数')
    @node_from(from_name='领取点数', success=False)
    @operation_node(name='领取奖励')
    def claim_reward(self) -> OperationRoundResult:
        screen = self.screenshot()

        if not common_screen_state.in_secondary_ui(self.ctx, screen,'指南'):
            return self.round_retry('未在指南页面', wait=1)

        if not common_screen_state.in_secondary_ui(self.ctx, screen,'每日实训'):
            return self.round_retry('未在每日实训页面', wait=1)

        pos = phone_menu_utils.get_training_reward_claim_btn_pos(self.ctx, screen)
        completed = phone_menu_utils.is_training_reward_completed(self.ctx, screen)
        if completed:
            return self.round_success('已领取过每日实训奖励', wait=1)
        if pos is None:
            return self.round_retry('未找到奖励按钮', wait=0.5)
        self.ctx.controller.click(pos.center)
        completed = phone_menu_utils.is_training_reward_completed(self.ctx, screen)
        if not completed:
            return self.round_fail('每日实训还未完成')
        return self.round_success('每日实训已完成', wait=1)

    @node_from(from_name='领取奖励')
    @operation_node(name='结束后返回')
    def back_at_last(self) -> OperationRoundResult:
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_for_sim_uni()
    ctx.start_running()
    op = DailyTrainingApp(ctx)
    op.execute()


if __name__ == '__main__':
    __debug()