import time

import numpy as np

from sr_od.application.calibrator import calibrator_const
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.sr_application import SrApplication
from sr_od.config.game_config import MiniMapPos, GameConfig
from sr_od.context.sr_context import SrContext
from sr_od.sr_map import mini_map_utils
from sr_od.sr_map.operations.transport_by_map import TransportByMap


class Calibrator(SrApplication):
    """
    首次运行需要的校准
    """

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, calibrator_const.APP_ID, op_name='校准')

    @operation_node(name='传送1')
    def tp1(self) -> OperationRoundResult:
        sp = self.ctx.map_data.best_match_sp_by_all_name('空间站「黑塔」', '基座舱段', '接待中心')
        op = TransportByMap(self.ctx, sp)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='传送1')
    @operation_node(name='小地图定位校准')
    def check_mini_map_pos(self) -> OperationRoundResult:
        log.info('[小地图定位校准] 开始')
        screenshot = self.screenshot()
        mm_pos: MiniMapPos = mini_map_utils.cal_little_map_pos(screenshot)
        cfg: GameConfig = self.ctx.game_config
        cfg.mini_map_pos = mm_pos
        cfg.update('mini_map', {
            'x': mm_pos.x,
            'y': mm_pos.y,
            'r': mm_pos.r
        })
        cfg.save()

        log.info('[小地图定位校准] 完成 位置: (%d, %d) 半径: %d', mm_pos.x, mm_pos.y, mm_pos.r)
        return self.round_success(wait=0.5)

    @node_from(from_name='小地图定位校准')
    @operation_node(name='传送2', is_start_node=True)
    def tp2(self) -> OperationRoundResult:
        sp = self.ctx.map_data.best_match_sp_by_all_name('空间站「黑塔」', '主控舱段', '黑塔的办公室')
        op = TransportByMap(self.ctx, sp)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='传送2')
    @operation_node(name='转向校准')
    def check_turning_rate(self) -> OperationRoundResult:
        """
        检测转向 需要找一个最容易检测到见箭头的位置
        通过固定滑动距离 判断转动角度
        反推转动角度所需的滑动距离
        :return:
        """
        log.info('[转向校准] 开始')
        turn_distance = 500

        angle = self._get_current_angle()
        turn_angle = []
        for _ in range(10):
            self.ctx.controller.turn_by_distance(turn_distance)
            time.sleep(1)
            next_angle = self._get_current_angle()
            if angle is not None:
                ta = (next_angle - angle) if next_angle >= angle else (next_angle - angle + 360)
                turn_angle.append(ta)
            angle = next_angle

        avg_turn_angle = np.mean(turn_angle)
        log.info('平均旋转角度 %.4f', avg_turn_angle)
        ans = float(turn_distance / avg_turn_angle)
        log.info('每度移动距离 %.4f', ans)
        gc: GameConfig = self.ctx.game_config
        gc.turn_dx = ans
        self.ctx.controller.turn_dx = ans
        log.info('[转向校准] 完成')
        # cv2.waitKey(0)
        return self.round_success(wait=0.5)

    def _get_current_angle(self) -> float:
        self.ctx.controller.move('w')
        time.sleep(1)
        screen = self.screenshot()
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        center_arrow_mask, arrow_mask, next_angle = mini_map_utils.analyse_arrow_and_angle(mm)
        log.info('当前角度 %.2f', next_angle)
        return next_angle


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    app = Calibrator(ctx)
    app.execute()


if __name__ == '__main__':
    __debug()
