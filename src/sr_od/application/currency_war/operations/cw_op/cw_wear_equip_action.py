"""穿装备动作 op(CwActionWearEquipOp)——动作 op 重组 换壳(原
``WearEquipOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内
直调自己的上报函数** ``report_action_wear_equip_param``,零分派,
op-layer.md §1.2 动作 op 契约)。组合壳溶解后的原子通路机械半。
非终结。

机械执行零判效(用户裁定「动作 op = 机械执行」,落地判定归观察侧
reconcile 对账):发出即记账,拖后不做像素验证。拖拽静默不生效属执行
环境噪声,由下一入口 heavy 实读对账暴露,重试 = 决策循环按新观察自然
重派。装备域状态容器分支 = 上报函数单点(owned −1 + tracked 目标 +1)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.wear_equip import (
    report_action_wear_equip_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionWearEquipParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import PREP_DRAG_SETTLE_WAIT_S
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionWearEquipOp(CwOperation):
    """穿装备单步(CwActionWearEquipParam 原子通路机械半)。非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionWearEquipParam,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionWearEquipOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='wear_equip', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """穿装备单步。

        流程 = 固定等待 `PREP_DRAG_SETTLE_WAIT_S`(非判效)→ owned 网格
        按名定位源件 → 单次拖拽。机械执行零判效:发出即记账,拖后零读屏
        零落地判定;拖拽静默不生效由下一入口观察对账暴露,重派重算 =
        决策循环按新观察自然承接。

        [索引定义] 拖拽坐标 = owned 网格定位点(格心 = read_equips 逐格
        分类现读)→ 目标排 avatar 拖点(screen_info 建档派生)。
        """
        action: CwActionWearEquipParam = self.param
        env = self.env
        ex = env.executor
        if action.row not in ('front', 'back'):
            # 参数违法由 op 自判(flow/action_ops.md §1 决策侧参数现算
            # 契约):row = 画面物理排枚举,slot = 排内画面槽 1 基;
            # 非法/越界响亮暴露零拖拽(禁负下标回环静默错点)。
            raise AssertionError(
                f'CwActionWearEquipParam row={action.row!r} 非法(front/back)')
        _row_n = len(ex._front_pts if action.row == 'front' else ex._back_pts)
        if not (1 <= action.slot <= _row_n):
            raise AssertionError(
                f'CwActionWearEquipParam slot={action.slot} 越界(1-{_row_n})')
        target = ex._equip_slot_drag_point(action.row, action.slot)
        if cw_sim_ports.mechanical_io_allowed():
            start = ex._owned_grid_locate(action.item_name)
            if start is None:
                return self.round_fail(
                    f'owned 网格未定位到 {action.item_name}'
                    '(模板库缺失/计划失效,下帧重派重算)')
            time.sleep(PREP_DRAG_SETTLE_WAIT_S)   # 拖前固定等待(非判效)
            ex._ctx.controller.mouse_move(start)   # 防吞点击(截图前移光标)
            time.sleep(0.2)
            ex._ctx.controller.drag_to(start=start, end=target,
                                       hold_time=0.5, duration=1.5)
            time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        else:
            # sim:owned 网格定位属帧识别域(sentinel 无读),机械拖拽静默
            # 成功(直连旁路 port 检查,sim-design.md §6.5);自上报照走
            pass
        ex._op.park_cursor(after_wait=0.1)
        # —— 自上报(机械发出后;op-layer.md §1.2)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_wear_equip_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        detail = (f'穿戴 {action.item_name} → {action.char_name or "前排空槽"}'
                  f'({action.row}-{action.slot}) 已发(发出即记账,'
                  '落地归观察对账)')
        log.info(f'[cw][wear] {detail}')
        return self.round_success(detail)
