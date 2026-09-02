from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.sim_universe import sim_uni_screen_state
from sr_od.application.sim_universe.operations.sim_uni_enter_fight import (
    SimUniEnterFight,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import battle_screen_state


class SimUniExit(SrOperation):

    STATUS_EXIT_CLICKED: ClassVar[str] = '点击结算'
    STATUS_BACK_MENU: ClassVar[str] = '返回菜单'

    #: 打开菜单⇄点击结算 无界循环的上限(次):连续这么多次找不到结算入口就
    #: 以 FAIL 结束。循环全走 success 边不消耗任何 retry 预算(2026-09-02
    #: 一条龙饰品提取段实证空转 27 分钟),必须用本计数器自带上界兜底。
    MAX_BACK_MENU_CYCLES: ClassVar[int] = 5

    def __init__(self, ctx: SrContext, is_in_x: bool = False, temporarily_leave: bool = False ):
        """
        模拟宇宙 结束并结算
        :param ctx:
        """
        SrOperation.__init__(self, ctx,
                             op_name=f'{gt("模拟宇宙", "game")} {gt("结束并结算")}'
                             )
        # 差分宇宙中需要点一个返回主界面
        self.is_in_x = is_in_x
        self.temporarily_leave = temporarily_leave
        # 坐标系=本 op 实例内连续 BACK_MENU 计数(打开菜单⇄点击结算 循环圈数):
        # 命中结算项或确认已在大世界时归零,达 MAX_BACK_MENU_CYCLES 则 FAIL
        # 交上层兜底(BackToNormalWorldPlus.sim_uni_exit 有 round_retry)。
        self._back_menu_cycles: int = 0

    @operation_node(name='画面识别', node_max_retry_times=10, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        """
        检查屏幕
        这个指令作为兜底的退出模拟宇宙的指令 应该兼容当前处于模拟宇宙的任何一种场景
        :return:
        """
        screen = self.last_screenshot
        state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            in_world=True,
            battle=True,
            battle_fail=True
        )
        if state == sim_uni_screen_state.ScreenState.NORMAL_IN_WORLD.value:  # 只有在大世界画面才继续
            # 已确认在大世界=有进展:连续 BACK_MENU 计数归零,重新给满循环预算。
            self._back_menu_cycles = 0
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
        # 决策点日志:Esc 已发,供卡死时复盘「循环期 Esc 是否真的改变了画面」
        # (2026-09-02 事故循环期 Esc 未生效的底层机制未明,留观察)。
        log.info('SimUniExit 打开菜单: Esc 已发')
        self.ctx.controller.esc()
        return self.round_success(wait=1)

    @node_from(from_name='打开菜单')
    @operation_node(name='点击结算')
    def click_exit(self) -> OperationRoundResult:
        screen = self.last_screenshot

        if self.temporarily_leave:
            result = self.round_by_find_and_click_area(screen, '模拟宇宙', '差分宇宙-暂离')
            if result.is_success:
                return self.round_success(result.status)

        area_list = [
            ('模拟宇宙', '菜单-结束并结算'),
            ('模拟宇宙', '终止战斗并结算'),
        ]
        for area in area_list:
            result = self.round_by_find_and_click_area(screen, area[0], area[1])
            if result.is_success:
                # 命中并点击结算项=有进展:连续 BACK_MENU 计数归零。
                self._back_menu_cycles = 0
                return self.round_success(SimUniExit.STATUS_EXIT_CLICKED, wait=1)

        # 找不到结算入口:走 success 边回 open_menu 的循环不消耗 retry 预算,
        # 必须自带计数上界——连续 MAX_BACK_MENU_CYCLES 圈仍找不到即 FAIL
        # 交上层兜底,避免无界空转(2026-09-02 实证 27 分钟)。
        self._back_menu_cycles += 1
        log.info(
            'SimUniExit 未找到 结束并结算 入口: 连续 BACK_MENU 第 %d/%d 圈',
            self._back_menu_cycles, SimUniExit.MAX_BACK_MENU_CYCLES,
        )
        if self._back_menu_cycles >= SimUniExit.MAX_BACK_MENU_CYCLES:
            return self.round_fail(
                status='多次未找到 结束并结算 入口(菜单未打开或条目不匹配)', wait=1)
        return self.round_success(SimUniExit.STATUS_BACK_MENU, wait=1)

    @node_from(from_name='点击结算', status=STATUS_EXIT_CLICKED)
    @operation_node(name='点击确认')
    def click_confirm(self) -> OperationRoundResult:
        """
        确认退出模拟宇宙
        :return:
        """
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(screen, '模拟宇宙', '退出对话框-确认',
                                                 success_wait=6, retry_wait=1)

    @node_from(from_name='点击确认')
    @operation_node(name='点击空白处继续')
    def click_empty(self) -> OperationRoundResult:
        """
        结算画面点击空白
        :return:
        """
        screen = self.last_screenshot
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

