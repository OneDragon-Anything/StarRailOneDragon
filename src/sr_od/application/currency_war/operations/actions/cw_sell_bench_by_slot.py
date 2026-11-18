"""卖出备战槽角色 op(拖拽至出售区;公用底层动作原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import (
    drag_bench_to_sell,
    drag_overlay_block_status,
    prep_drag_overlay_gate,
)
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext


class CwSellBenchBySlot(CwOperation):
    """卖出备战席指定槽位的角色(拖拽至出售区)。
    起点:货币战争-备战(商店面板开合均可,两画面档自备 备战栏/出售区 area);
    终点:拖拽发出,停留原画面(卖出是否生效归调用方下一帧 analyze_screen 对账)。
    消耗:角色被卖出换金币,不可逆。

    槽位占用实况 = analyze_screen extras ``bench.slots``(kind=unit 才有角色);
    本 op 只负责机械拖拽,不判断槽位内容。

    拖前浮层守卫(执行前输入契约拒绝,prep_actions 模块头「防线边界申报」
    辖面):合成确认浮层/角色详情面板在场时拖拽会被游戏静默吞(全局模态
    阻断),守卫先行拦截——round_fail 带家族受阻指引,拖拽零发出;直调方
    从 round 结果感知受阻后先收尾浮层再重调。

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
        # 浮层守卫装在本节点而非 drag_bench_to_sell helper 内。选点理由:
        # helper 现役消费者 = 本 op 单一(prep_actions.drag_bench_to_sell
        # docstring 申报,备战域 op 已迁移自持),「helper 内一处覆盖所有
        # 调用方」无覆盖增益;且 helper 为 void 机械原语(发出即职责完成、
        # 零返回),守卫受阻需 round_fail 通道(受阻码闭集
        # _PREP_RECEIPT_BLOCK_CODES + drag_overlay_block_status 家族指引),
        # 节点内安装 = 与现役各安装点同构,直调入口(MCP run_operation 面)
        # 受阻语义最清晰。守卫置于机械 IO 门内 = sim 零触及;机械段 sim
        # 静默在 drag_bench_to_sell → drag_char_guarded 内自持。
        if cw_sim_ports.mechanical_io_allowed():
            overlay_hit = prep_drag_overlay_gate(self)
            if overlay_hit is not None:
                log.info(f'[cw][sell-by-slot] 浮层在场({overlay_hit})'
                         '→ 拖拽未发出')
                return self.round_fail(
                    status=drag_overlay_block_status(overlay_hit))
        # drag_bench_to_sell 入参 = 列表下标 0-8(物理槽位 1-9 减一,原语 docstring 口径)
        drag_bench_to_sell(self, self.ctx, self.slot - 1)
        return self.round_success(
            status=f'已拖备战栏{self.slot}槽至出售区(机械发出,零判效)',
            data={'slot': self.slot}, wait=1)
