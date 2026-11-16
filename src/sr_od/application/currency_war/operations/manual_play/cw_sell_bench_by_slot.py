"""卖出备战槽角色 op(拖拽至出售区;MCP 手动游玩纯动作)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import drag_bench_to_sell
from sr_od.context.sr_context import SrContext


class CwSellBenchBySlot(CwOperation):
    """卖出备战席指定槽位的角色(拖拽至出售区)。
    起点:货币战争-备战(商店面板开合均可,两画面档自备 备战栏/出售区 area);
    终点:拖拽发出,停留原画面(卖出是否生效归调用方下一帧 analyze_screen 对账)。
    消耗:角色被卖出换金币,不可逆。

    槽位占用实况 = analyze_screen extras ``bench.slots``(kind=unit 才有角色);
    本 op 只负责机械拖拽,不判断槽位内容。

    :param slot: 备战栏物理槽位号,1-9(= screen_info「备战栏-N」序号;
        extras.bench.slots 数组下标 + 1)。越界构造期拒绝(带可用值 ValueError)。
    """

    def __init__(self, ctx: SrContext, slot: int):
        CwOperation.__init__(self, ctx, op_name='CW卖备战槽',
                             need_check_game_win=False)
        if not 1 <= slot <= 9:
            raise ValueError(f'slot 越界: {slot}(可用值 1-9,备战栏物理槽位)')
        self.slot: int = slot

    @operation_node(name='拖拽至出售区', is_start_node=True)
    def drag_sell(self) -> OperationRoundResult:
        # drag_bench_to_sell 入参 = 列表下标 0-8(物理槽位 1-9 减一,原语 docstring 口径)
        drag_bench_to_sell(self, self.ctx, self.slot - 1)
        return self.round_success(
            status=f'已拖备战栏{self.slot}槽至出售区(机械发出,零判效)',
            data={'slot': self.slot}, wait=1)
