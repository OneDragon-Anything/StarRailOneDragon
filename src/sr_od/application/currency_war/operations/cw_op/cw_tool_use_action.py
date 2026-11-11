"""工具消耗动作 op(CwActionToolUseOp)——动作 op 重组换壳(原
``ToolUseOp``,ActionOp ABC → 框架 SrOperation,op-layer.md §1.2 动作
op 契约)。
机械执行后 **op 内直调自己的上报函数**(七工具参数共用机械半,上报 =
各自状态容器写函数,按 param 类型一行解析;零分派语义 = op-layer.md §1.2;
tool-gain-report
迭代起上报 = 机械执行直接上报写状态容器,状态容器写权威版本 =
``kernel/cw_action_report/tool_use``)。非终结。

一个 op 类覆盖工具原子七类(R8 按消耗品各立词表类,机械半同构:owned
网格内 icon → 目标拖曳;工具名解析表 ``_TOOL_NAME_BY_CLASS`` 随体迁)。
注册表七行(每词表类一行)同指本 op,消费语义逐类一致。零消耗确认
交叉核对(裁决 3:消耗交叉核对由观察承接)。"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.tool_use import (
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
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionToolUseOp(CwOperation):
    """工具消耗单步(七类共用机械半:owned 网格内 icon → 目标拖曳)。
    非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    #: 工具词表类 → 注册名(icon 定位识别标志,与装备注册表同名)。
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
    #: param 类型一行解析,零分派语义 = 直调自己的上报,op-layer.md §1.2)。
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
        CwOperation.__init__(self, ctx, op_name='CwActionToolUseOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='tool_use', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """工具消耗单步(七类共用机械半:owned 网格内 icon → 目标拖曳)。

        源件 = 工具 icon(按注册名定位);目标 = equip 模式 owned 网格
        icon / char 模式角色槽位中心。零消耗确认交叉核对(裁决 3)——拖后固定
        等待,消费真值 = 下一帧装备区读数;机械链发出后直调上报 =
        机械执行直接上报写状态容器(tool_use 确定面 write_logic / 随机面
        write_logic_rand 采样链,上报无条件不判成败)。
        """
        action: CwAction = self.param
        env = self.env
        ex = env.executor
        tool_name = self._TOOL_NAME_BY_CLASS[type(action)]
        # —— 参数守卫(执行器集中式 validate 退役进 op,flow/action_ops.md
        # §1 决策侧参数现算契约;合法域静态可判分支,违法响亮暴露零拖拽)——
        if isinstance(action, (CwActionFurnaceUseParam,
                               CwActionPrivilegeCardUseParam)):
            if action.target_kind not in ('equip', 'char'):
                raise AssertionError(
                    f'{type(action).__name__} target_kind='
                    f'{action.target_kind!r} 非法(equip/char)')
            if action.target_kind == 'equip':
                if not action.item_name:
                    raise AssertionError(
                        f'{type(action).__name__} equip 分支缺目标件名')
            else:
                # char 模式行槽直取前排/后排点表:row 非法会静默落到
                # 后排点表(负下标回环同族),守卫断言闭合。
                if action.row not in ('front', 'back'):
                    raise AssertionError(
                        f'{type(action).__name__} row={action.row!r} '
                        '非法(front/back)')
                _n = len(ex._front_pts if action.row == 'front'
                         else ex._back_pts)
                if not (1 <= action.slot <= _n):
                    raise AssertionError(
                        f'{type(action).__name__} slot={action.slot} '
                        f'越界(1-{_n})')
        else:
            # 工具原子其余五类(扳手/投影仪/令牌,char 模式行槽直取):
            # 同款 row/slot 静态合法域守卫。
            if action.row not in ('front', 'back'):
                raise AssertionError(
                    f'{type(action).__name__} row={action.row!r} '
                    '非法(front/back)')
            _n = len(ex._front_pts if action.row == 'front'
                     else ex._back_pts)
            if not (1 <= action.slot <= _n):
                raise AssertionError(
                    f'{type(action).__name__} slot={action.slot} '
                    f'越界(1-{_n})')
        if cw_sim_ports.mechanical_io_allowed():
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
            ex._ctx.controller.mouse_move(start)   # 防吞点击(截图前移光标)
            time.sleep(0.2)
            ex._ctx.controller.drag_to(start=start, end=end,
                                       hold_time=0.5, duration=1.2)
            time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        else:
            # sim:owned 网格定位属帧识别域(sentinel 无读),机械拖拽静默
            # 成功(直连旁路 port 检查,sim-design.md §6.5);自上报照走
            if getattr(action, 'target_kind', 'char') == 'equip':
                tgt_desc = getattr(action, 'item_name', '')
            else:
                tgt_desc = f'{action.row}-{action.slot}'
        ex._op.park_cursor(after_wait=0.1)
        # —— 自上报(机械发出后;按 param 类型直调自己的上报函数,
        # 机械执行直接上报写状态容器)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            self._REPORT_BY_CLASS[type(action)](
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        detail = f'{tool_name} → {tgt_desc} 拖曳已发(上报已按成功写状态容器)'
        log.info(f'[cw][tool] {detail}')
        return self.round_success(detail)
