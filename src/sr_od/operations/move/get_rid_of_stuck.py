import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class GetRidOfStuck(SrOperation):
    """移动脱困:按被困次数选择六种绕行组合之一(左前/右前/后左前/后右前/
    左后右前/右后左前,左右顺序交错防原地打转),绕行后恢复前进;
    data 返回本次脱困耗时秒数。
    起点:大世界(移动中被困);终点:大世界(已恢复前进)。
    """

    def __init__(self, ctx: SrContext, stuck_times: int):
        """
        :param ctx: 上下文
        :param stuck_times: 被困次数,1~12;次数决定用哪种绕行组合与步幅
        """
        super().__init__(ctx, op_name='%s %d' % (gt('尝试脱困'), stuck_times))
        self.stuck_times: int = stuck_times

    @operation_node(name='脱困', is_start_node=True)
    def get_rid(self) -> OperationRoundResult:
        self.ctx.controller.stop_moving_forward()

        move_unit_sec = 0.25
        try_move_unit = self.stuck_times % 2 if self.stuck_times % 2 != 0 else 2
        try_method = (self.stuck_times + 1) // 2

        if try_method == 1:  # 左 前
            walk_sec = try_move_unit * move_unit_sec
            self.ctx.controller.move('a', walk_sec)
            self.ctx.controller.start_moving_forward()  # 多往前走1秒再判断是否被困
            time.sleep(1)
            total_time = walk_sec + 1
        elif try_method == 2:  # 右 前
            walk_sec = try_move_unit * move_unit_sec
            self.ctx.controller.move('d', walk_sec)
            self.ctx.controller.start_moving_forward()
            time.sleep(1)
            total_time = walk_sec + 1
        elif try_method == 4:  # 后左 前  # 注意这里左右顺序要跟1, 2相反 可以防止一左一右还卡在原处
            walk_sec = try_move_unit * move_unit_sec
            self.ctx.controller.move('s', walk_sec)
            self.ctx.controller.move('a', walk_sec)
            self.ctx.controller.move('w', walk_sec)
            self.ctx.controller.start_moving_forward()
            time.sleep(1)
            total_time = walk_sec * 3 + 1
        elif try_method == 3:  # 后右 前
            walk_sec = try_move_unit * move_unit_sec
            self.ctx.controller.move('s', walk_sec)
            self.ctx.controller.move('d', walk_sec)
            self.ctx.controller.move('w', walk_sec)
            self.ctx.controller.start_moving_forward()
            time.sleep(1)
            total_time = walk_sec * 3 + 1
        elif try_method == 5:  # 左后右 前
            walk_sec = try_move_unit * move_unit_sec
            self.ctx.controller.move('a', walk_sec)
            self.ctx.controller.move('s', walk_sec)
            self.ctx.controller.move('d', walk_sec + move_unit_sec)
            self.ctx.controller.start_moving_forward()
            time.sleep(1)
            total_time = walk_sec * 3 + move_unit_sec + 1
        elif try_method == 6:  # 右后左 前
            walk_sec = try_move_unit * move_unit_sec
            self.ctx.controller.move('d', walk_sec)
            self.ctx.controller.move('s', walk_sec)
            self.ctx.controller.move('a', walk_sec + move_unit_sec)
            self.ctx.controller.start_moving_forward()
            time.sleep(1)
            total_time = walk_sec * 3 + move_unit_sec + 1
        else:
            total_time = 0

        return self.round_success(data=total_time)