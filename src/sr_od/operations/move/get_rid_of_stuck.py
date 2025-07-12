import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class GetRidOfStuck(SrOperation):

    def __init__(self, ctx: SrContext, stuck_times: int):
        """
        简单的脱困指令
        返回数据为脱困使用的时间
        以下方式各尝试2遍
        1. 往左 然后往前走
        2. 往右 然后往前走
        3. 往后再往右 然后往前走  # 注意这里左右顺序要跟上面相反 可以防止一左一右还卡在原处
        4. 往后再往左 然后往前走
        5. 往左再往后再往右 然后往前走
        6. 往右再往后再往左 然后往前走
        :param ctx:
        :param stuck_times: 被困次数 1~12
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