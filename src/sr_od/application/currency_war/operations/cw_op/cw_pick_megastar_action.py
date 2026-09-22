"""盛会之星 pick 确认链动作 op(:class:`CwActionPickMegastarOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:``env.need_select`` 驱动的选中半(点候选)→ 确认钮单发;
机械链发出后直调自上报单口 ``report_action_pick_megastar_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_megastar_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickMegastarParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_megastar import (
    CwScreenMegastar,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickMegastarOp(SrOperation):
    """盛会之星 pick 确认链(统一动作工厂批4 迁入)。

    候选选中半迁入本类(pick-op-unify 批,``env.need_select`` 驱动,见
    ``run``);``chosen_megastar`` 写端留守画面 op(单次逻辑写入豁免面,
    派发前写)——确认机械半 = 确认钮单发。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickMegastarParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickMegastarOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_megastar', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(选中半[need_select] → 确认钮单发 + 固定等待;零判效)。

        选中半(pick-op-unify 批自画面 op 迁入):``env.need_select`` 且
        ``env.target`` 在场 → 点候选选中 + 固定等待(原选中后 0.6s 动画窗,
        时序逐位保留)。``chosen_megastar`` 写端与选中旗标留守画面 op
        (单次逻辑写入豁免面,派发前写)。"""
        action = self.param
        env = self.env
        op = env.op
        if env.need_select and env.target is not None:
            op.ctx.controller.mouse_move(env.target)
            op.ctx.controller.click(env.target)
            time.sleep(0.6)
        # confirm(确认钮纯机械单发;overlay 关否由下一帧重入裁决)。
        # 确认钮中心从 screen_info 读;缺失兜底常量。
        confirm = area_center(op.ctx, '按钮-确认选择', '货币战争-盛会之星') or CwScreenMegastar.CONFIRM
        op.ctx.controller.mouse_move(confirm)
        op.ctx.controller.click(confirm)
        time.sleep(0.9)
        # 确认 = 纯机械单发(用户裁定 2026-09-14):「请选择强化角色」
        # 文本 = 确认钮旁伴随文案,禁据它判步。
        # 确认未落地 overlay 残留 =
        # 下一帧重入裁决自愈:节点循环读「仍在巨星 overlay?」(标识锚仍
        # 命中)→ 重走本方法 → 候选已选 → 机械单发确认再推进
        # (宿主 round_wait 循环推进,不烧节点重试预算)。
        # chosen_megastar 写端留守画面 op(动作事实边界,派发前写 =
        # 选择点),无挂账登记环节。
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_megastar_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('盛会之星确认已发')
