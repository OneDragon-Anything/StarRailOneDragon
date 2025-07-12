from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state
from sr_od.sr_map import large_map_utils


class OpenMap(SrOperation):

    def __init__(self, ctx: SrContext):
        """
        通过按 esc 和 m 打开大地图
        """
        SrOperation.__init__(self, ctx, op_name=gt('打开地图'))

    @operation_node(name='画面识别', node_max_retry_times=10, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.screenshot()

        if common_screen_state.is_normal_in_world(self.ctx, screen):  # 主界面
            log.info('尝试打开地图')
            self.ctx.controller.open_map()
            return self.round_wait(wait=2)

        # 二级地图中 需要返回
        r1 = self.round_by_find_area(screen, '大地图', '标题-导航')
        if r1.is_success:
            # 在导航 但是没有开拓力的图标 说明在子区域中 需要返回
            r2 = self.round_by_find_area(screen, '大地图', '图标-开拓力')
            if not r2.is_success:
                # 如果是当前所在的子区域 会显示返回
                result = self.round_by_find_and_click_area(screen, '大地图', '子区域-返回')
                if result.is_success:
                    return self.round_wait(result.status, wait=1)
                else:
                    # 如果不是当前所在的子区域 则不会显示返回
                    result = self.round_by_click_area('大地图', '子区域-关闭')
                    return self.round_wait(result.status, wait=1)

        planet = large_map_utils.get_planet(self.ctx, screen)
        log.info('当前大地图所处星球 %s', planet)
        if planet is not None:  # 左上角找到星球名字的话 证明在在大地图页面了
            return self.round_success()

        # 其他情况都需要通过返回上级菜单再尝试打开大地图
        log.info('尝试返回上级菜单')
        self.ctx.controller.esc()
        return self.round_retry(wait=2)
