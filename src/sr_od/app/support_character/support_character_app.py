from cv2.typing import MatLike
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.menu import phone_menu_utils
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu


class SupportCharacterApp(SrApplication):

    STATUS_WITH_ALERT: ClassVar[str] = '红点'
    STATUS_NO_ALERT: ClassVar[str] = '无红点'

    def __init__(self, ctx: SrContext):
        """
        收取支援角色奖励
        2023-11-12 中英文最高画质测试通过
        """
        SrApplication.__init__(self, ctx, 'support_character', op_name=gt('支援角色奖励'),
                               run_record=ctx.support_character_run_record, need_notify=True)

    @operation_node(name='打开菜单', is_start_node=True)
    def open_menu(self) -> OperationRoundResult:
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开菜单')
    @operation_node(name='点击省略号')
    def _click_ellipsis(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        result: MatchResult = phone_menu_utils.get_phone_menu_ellipsis_pos(self.ctx, screen, alert=True)
        if result is None:
            return self.round_success(SupportCharacterApp.STATUS_NO_ALERT)
        else:
            self.ctx.controller.click(result.center)
            return self.round_success(SupportCharacterApp.STATUS_WITH_ALERT, wait=1)

    @node_from(from_name='点击省略号', status=STATUS_WITH_ALERT)
    @operation_node(name='点击漫游签证')
    def _click_profile(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        result: MatchResult = phone_menu_utils.get_phone_menu_ellipsis_item_pos(self.ctx, screen, '漫游签证', alert=True)
        if result is None:
            return self.round_success(SupportCharacterApp.STATUS_NO_ALERT)
        else:
            self.ctx.controller.click(result.center)
            return self.round_success(SupportCharacterApp.STATUS_WITH_ALERT, wait=1)

    @node_from(from_name='点击漫游签证', status=STATUS_WITH_ALERT)
    @operation_node(name='领取奖励')
    def _click_character(self) -> OperationRoundResult:
        self.ctx.controller.click(Point(1659, 286))
        return self.round_success(wait=1)

    @node_from(from_name='领取奖励')
    @node_from(from_name='点击省略号', status=STATUS_NO_ALERT)
    @node_from(from_name='点击漫游签证', status=STATUS_NO_ALERT)
    @operation_node(name='结束后返回')
    def back_at_last(self) -> OperationRoundResult:
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())
