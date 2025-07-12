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


class EmailApp(SrApplication):

    STATUS_WITH_ALERT: ClassVar[str] = '邮件红点'
    STATUS_NO_ALERT: ClassVar[str] = '无邮件红点'

    def __init__(self, ctx: SrContext):
        """
        收取邮件奖励 但不会删除邮件
        2023-11-12 中英文最高画质测试通过
        """
        SrApplication.__init__(self, ctx, 'email',
                               op_name=gt('邮件', 'game'),
                               run_record=ctx.email_run_record,
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
    @operation_node(name='点击邮件')
    def _click_email(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        result: MatchResult = phone_menu_utils.get_phone_menu_item_pos_at_right(self.ctx, screen, phone_menu_const.EMAILS, alert=True)
        if result is None:
            return self.round_success(EmailApp.STATUS_NO_ALERT)
        else:
            self.ctx.controller.click(result.center)
            return self.round_success(EmailApp.STATUS_WITH_ALERT, wait=1)

    @node_from(from_name='点击邮件', status=STATUS_WITH_ALERT)
    @operation_node(name='全部领取')
    def _claim(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        return self.round_by_find_and_click_area(screen, '菜单', '邮件-全部领取',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='点击邮件', status=STATUS_NO_ALERT)
    @node_from(from_name='全部领取')
    @node_from(from_name='全部领取', success=False)
    @operation_node(name='结束后返回')
    def back_at_last(self) -> OperationRoundResult:
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())