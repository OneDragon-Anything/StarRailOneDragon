from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class OpenPhoneMenu(SrOperation):
    """打开手机菜单(右上角开拓等级可见的那个面板)。
    起点:任意可控画面(不在菜单时先回大世界再按菜单键);终点:菜单画面。
    """

    def __init__(self, ctx: SrContext):
        """
        :param ctx: 上下文
        """
        super().__init__(ctx, op_name=gt('打开菜单'))

    @operation_node(name='画面识别', node_max_retry_times=10, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.last_screenshot

        result = self.round_by_find_area(screen, '菜单', '开拓等级')
        if result.is_success:
            return self.round_success()

        if common_screen_state.is_normal_in_world(self.ctx, screen):
            self.ctx.controller.esc()
            log.info('尝试打开菜单')
            return self.round_retry(status='未在菜单画面', wait=2)
        else:
            op = BackToNormalWorldPlus(self.ctx)
            return self.round_retry(op.execute().status)
