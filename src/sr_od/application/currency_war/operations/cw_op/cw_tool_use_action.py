"""工具消耗动作 op(CwActionToolUseOp)——动作 op 重组批③ 换壳(原
``ToolUseOp``,ActionOp ABC → 框架 SrOperation,design.md §1.1/§1.2)。
机械执行后 **op 内直调自己的上报函数**(七工具参数共用机械半,上报 =
各自零写函数,按 param 类型一行解析;design.md §1.2)。非终结。

一个 op 类辖工具原子七类(R8 按消耗品各立词表类,机械半同构:owned
网格内 icon → 目标拖曳;工具名解析表 ``_TOOL_NAME_BY_CLASS`` 随体迁)。
注册表七行(每词表类一行)同指本 op,消费语义逐类一致。零消耗确认
对拍(裁决 3:消耗对拍由观察承接)。"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_furnace_use_param,
    report_action_lucky_token_use_param,
    report_action_perfect_projector_use_param,
    report_action_precision_wrench_use_param,
    report_action_privilege_card_use_param,
    report_action_staff_projector_use_param,
    report_action_wrench_use_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionFurnaceUseParam,
    CwActionLuckyTokenUseParam,
    CwActionPerfectProjectorUseParam,
    CwActionPrecisionWrenchUseParam,
    CwActionPrivilegeCardUseParam,
    CwActionStaffProjectorUseParam,
    CwActionWrenchUseParam,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionToolUseOp(SrOperation):
    """工具消耗单步(七类共用机械半:owned 网格内 icon → 目标拖曳)。
    非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    #: 工具词表类 → 注册名(icon 定位锚,与装备注册表同名)。
    _TOOL_NAME_BY_CLASS: ClassVar[dict[type, str]] = {
        CwActionFurnaceUseParam: '冶金炉',
        CwActionPrivilegeCardUseParam: '特权赋予卡',
        CwActionWrenchUseParam: '拆装扳手',
        CwActionPrecisionWrenchUseParam: '精密拆装扳手',
        CwActionStaffProjectorUseParam: '员工投影仪',
        CwActionPerfectProjectorUseParam: '完美投影仪',
        CwActionLuckyTokenUseParam: '好运令牌',
    }

    #: 工具词表类 → 自身上报函数(每动作一个具名接口;op 组装后按自身
    #: param 类型一行解析,零分派语义 = 直调自己的上报,design.md §1.2)。
    _REPORT_BY_CLASS: ClassVar[dict[type, Callable]] = {
        CwActionFurnaceUseParam: report_action_furnace_use_param,
        CwActionPrivilegeCardUseParam: report_action_privilege_card_use_param,
        CwActionWrenchUseParam: report_action_wrench_use_param,
        CwActionPrecisionWrenchUseParam: report_action_precision_wrench_use_param,
        CwActionStaffProjectorUseParam: report_action_staff_projector_use_param,
        CwActionPerfectProjectorUseParam: report_action_perfect_projector_use_param,
        CwActionLuckyTokenUseParam: report_action_lucky_token_use_param,
    }

    def __init__(self, ctx: SrContext, param: CwAction,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionToolUseOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='tool_use', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """工具消耗单步(七类共用机械半:owned 网格内 icon → 目标拖曳)。

        源件 = 工具 icon(按注册名定位);目标 = equip 模式 owned 网格
        icon / char 模式角色槽位中心。零消耗确认对拍(裁决 3)——拖后固定
        等待,消费真值 = 下一帧装备区读数;装备域容器腿 = 容器零写
        (消费真值归观察,截断点独占发射帧零窗口,下一入口 heavy 覆盖)。
        """
        action: CwAction = self.param
        env = self.env
        ex = env.executor
        tool_name = self._TOOL_NAME_BY_CLASS[type(action)]
        start = ex._owned_grid_locate(tool_name)
        if start is None:
            return self.round_fail(
                f'owned 网格未定位到工具 {tool_name}'
                '(模板库缺失/已消耗,下帧重派)')
        if getattr(action, 'target_kind', 'char') == 'equip':
            tgt_name = getattr(action, 'item_name', '')
            end = ex._owned_grid_locate(tgt_name)
            if end is None:
                return self.round_fail(
                    f'owned 网格未定位到目标件 {tgt_name}'
                    '(合成消耗/reflow,下帧重派)')
            tgt_desc = tgt_name
        else:
            pts = ex._front_pts if action.row == 'front' else ex._back_pts
            end = pts[action.slot - 1]
            tgt_desc = f'{action.row}-{action.slot}'
        ex._ctx.controller.mouse_move(start)   # bug#1 缓解
        time.sleep(0.2)
        ex._ctx.controller.drag_to(start=start, end=end,
                                   hold_time=0.5, duration=1.2)
        time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        ex._op.park_cursor(after_wait=0.1)
        # —— 自上报(机械发出后;按 param 类型直调自己的零写上报)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            self._REPORT_BY_CLASS[type(action)](
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        detail = f'{tool_name} → {tgt_desc} 拖曳已发(零对拍,消费归观察)'
        log.info(f'[cw][tool] {detail}')
        return self.round_success(detail)
