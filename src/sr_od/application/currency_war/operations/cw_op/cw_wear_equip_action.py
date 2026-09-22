"""穿装备动作 op(CwActionWearEquipOp)——动作 op 重组批③ 换壳(原
``WearEquipOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内
直调自己的上报函数** ``report_action_wear_equip_param``,零分派,
design.md §1.1/§1.2)。CwActionWearEquipParam 原子通路机械半(R2)。
非终结。

机械执行零判效(用户裁定「动作 op = 机械执行」,落地判定归观察侧
reconcile 对账):发出即记账,拖后不做像素验证。拖拽静默不生效属执行
环境噪声,由下一入口 heavy 实读对账显影,重试 = 决策循环按新观察自然
重派。装备域容器腿 = 上报函数单点(owned −1 + tracked 目标 +1)。
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
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionWearEquipOp(SrOperation):
    """穿装备单步(CwActionWearEquipParam 原子通路机械半)。非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionWearEquipParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionWearEquipOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='wear_equip', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """穿装备单步。

        流程 = 稳帧确认(动画收尾输入条件化等待,非判效)→ owned 网格
        按名定位源件 → 单次拖拽。机械执行零判效:发出即记账,拖后零读屏
        零落地判定;拖拽静默不生效由下一入口观察对账显影,重派重算 =
        决策循环按新观察自然承接。

        [索引定义] 拖拽坐标 = owned 网格定位点(格心 = read_equips 逐格
        分类现读)→ 目标排 avatar 拖点(screen_info 建档派生)。
        """
        action: CwActionWearEquipParam = self.param
        env = self.env
        ex = env.executor
        target = ex._equip_slot_drag_point(action.row, action.slot)
        if target is None:
            return self.round_fail(
                f'装备槽位坐标缺失:{action.row}-{action.slot}'
                '(建档漂移,禁兜底坐标)')
        start = ex._owned_grid_locate(action.item_name)
        if start is None:
            return self.round_fail(
                f'owned 网格未定位到 {action.item_name}'
                '(模板库缺失/计划失效,下帧重派重算)')
        ex._wait_stable_frame()
        ex._ctx.controller.mouse_move(start)   # 防吞点击(截图前移光标)
        time.sleep(0.2)
        ex._ctx.controller.drag_to(start=start, end=target,
                                   hold_time=0.5, duration=1.5)
        time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        ex._op.park_cursor(after_wait=0.1)
        # —— 自上报(机械发出后;design.md §1.1)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_wear_equip_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                session=getattr(getattr(self.ctx, 'cw_match', None),
                                'session', None))
        detail = (f'穿戴 {action.item_name} → {action.char_name or "前排空槽"}'
                  f'({action.row}-{action.slot}) 已发(发出即记账,'
                  '落地归观察对账)')
        log.info(f'[cw][wear] {detail}')
        return self.round_success(detail)
