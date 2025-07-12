from typing import ClassVar

from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class SwitchMember(SrOperation):

    STATUS_CONFIRM: ClassVar[str] = '确认'

    def __init__(self, ctx: SrContext, num: int,
                 skip_first_screen_check: bool = False,
                 skip_resurrection_check: bool = False):
        """
        切换角色 需要在大世界页面
        :param ctx:
        :param num: 第几个队友 从1开始
        :param skip_first_screen_check: 是否跳过第一次画面状态检查
        :param skip_resurrection_check: 跳过复活检测 逐光捡金中可跳过
        """
        SrOperation.__init__(self, ctx, op_name='%s %d' % (gt('切换角色'), num))

        self.num: int = num
        self.skip_first_screen_check: bool = skip_first_screen_check  # 是否跳过第一次的画面状态检查 用于提速
        self.first_screen_check: bool = True  # 是否第一次检查画面状态
        self.skip_resurrection_check: bool = skip_resurrection_check  # 跳过复活检测

    @node_from(from_name='等待')
    @operation_node(name='切换', is_start_node=True)
    def _switch(self) -> OperationRoundResult:
        first = self.first_screen_check
        self.first_screen_check = False
        if first and self.skip_first_screen_check:
            pass
        else:
            screen = self.screenshot()
            if not common_screen_state.is_normal_in_world(self.ctx, screen):
                return self.round_retry('未在大世界页面', wait=1)

        self.ctx.controller.switch_character(self.num)
        return self.round_success(wait=1)

    @node_from(from_name='切换')
    @operation_node(name='确认')
    def _confirm(self) -> OperationRoundResult:
        """
        复活确认
        :return:
        """
        if self.skip_resurrection_check:
            return self.round_success()

        screen = self.screenshot()
        if common_screen_state.is_normal_in_world(self.ctx, screen):  # 无需复活
            return self.round_success()

        result = self.round_by_find_area(screen, '快速恢复对话框', '暂无可用消耗品')
        if result.is_success:
            area = '取消'
        else:
            area = '确认'

        return self.round_by_find_and_click_area(screen, '快速恢复对话框', area,
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='确认', status='确认')
    @operation_node(name='等待')
    def _wait_after_confirm(self) -> OperationRoundResult:
        """
        等待回到大世界画面
        :return:
        """
        screen = self.screenshot()
        if common_screen_state.is_normal_in_world(self.ctx, screen):
            return self.round_success()
        else:
            return self.round_retry('未在大世界画面', wait=1)

    def after_operation_done(self, result: OperationResult):
        SrOperation.after_operation_done(self, result)

        if (not result.success
                or '取消' == result.status):
            # 指令出错 或者 没药复活 导致切换失败
            # 将当前角色设置成一个非法的下标 这样就可以让所有依赖这个的判断失效
            self.ctx.team_info.current_active = -1
        else:
            self.ctx.team_info.current_active = self.num - 1
