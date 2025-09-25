from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import battle_screen_state


class SimUniExit(SrOperation):

    STATUS_EXIT_CLICKED: ClassVar[str] = '点击结算'
    STATUS_BACK_MENU: ClassVar[str] = '返回菜单'

    def __init__(self, ctx: SrContext):
        """
        模拟宇宙 结束并结算
        :param ctx:
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s' %
                                     (gt('模拟宇宙', 'game'),
                                      gt('结束并结算'))
                             )

    @operation_node(name='画面识别', node_max_retry_times=10, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        """
        检查屏幕
        这个指令作为兜底的退出模拟宇宙的指令 应该兼容当前处于模拟宇宙的任何一种场景
        :return:
        """
        screen = self.screenshot()
        state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            in_world=True,
            battle=True,
            battle_fail=True
        )
        if state == sim_uni_screen_state.ScreenState.NORMAL_IN_WORLD.value:  # 只有在大世界画面才继续
            return self.round_success()
        elif state == battle_screen_state.ScreenState.BATTLE_FAIL.value:  # 战斗失败
            return self.round_by_find_and_click_area(screen, '模拟宇宙', '点击空白处继续',
                                                     success_wait=2, retry_wait=1)
        else:  # 其他情况 统一交给 battle 处理
            op = SimUniEnterFight(self.ctx)
            op_result = op.execute()
            if op_result.success:
                return self.round_wait()  # 重新判断
            else:
                return self.round_retry()

    @node_from(from_name='画面识别')
    @node_from(from_name='点击结算', status=STATUS_BACK_MENU)
    @operation_node(name='打开菜单')
    def open_menu(self) -> OperationRoundResult:
        """
        打开菜单 或者 战斗中的打开退出
        :return:
        """
        self.ctx.controller.esc()
        return self.round_success(wait=1)

    @node_from(from_name='打开菜单')
    @operation_node(name='点击结算')
    def click_exit(self) -> OperationRoundResult:
        screen = self.screenshot()

        area_list = [
            ('模拟宇宙', '菜单-结束并结算'),
            ('模拟宇宙', '终止战斗并结算'),
        ]
        for area in area_list:
            result = self.round_by_find_and_click_area(screen, area[0], area[1])
            if result.is_success:
                return self.round_success(SimUniExit.STATUS_EXIT_CLICKED, wait=1)

        return self.round_success(SimUniExit.STATUS_BACK_MENU, wait=1)

    @node_from(from_name='点击结算', status=STATUS_EXIT_CLICKED)
    @operation_node(name='点击确认')
    def click_confirm(self) -> OperationRoundResult:
        """
        确认退出模拟宇宙
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '退出对话框-确认',
                                                 success_wait=6, retry_wait=1)

    @node_from(from_name='点击确认')
    @operation_node(name='点击空白处继续')
    def click_empty(self) -> OperationRoundResult:
        """
        结算画面点击空白
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '点击空白处继续',
                                                 success_wait=2, retry_wait=1)


def __debug():
    ctx = SrContext()
    ctx.init_ocr()
    ctx.init_by_config()
    ctx.init_for_sim_uni()

    ctx.start_running()
    op = SimUniExit(ctx)
    op.execute()
    ctx.stop_running()


if __name__ == '__main__':
    __debug()
