"""选择伙伴 pick 确认链动作 op(:class:`CwActionPickPartnerOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:「点选候选 → 确认」脉冲链(未选中实证下重点选);确认点
读缺的 retry 旁路分支未发确认点击,不上报;机械链发出后直调自上报
单口 ``report_action_pick_partner_param``。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_partner_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickPartnerParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickPartnerOp(SrOperation):
    """选择伙伴 pick 确认链(统一动作工厂批4 迁入)。

    「点选候选 → 确认」脉冲链整体迁入(未选中实证下重点选,单选语义
    无反选面;确认被拒的防线判定留守画面 op 决策半)。选中态标记
    (``_pick_point``)与脉冲计数(``_confirm_pulses``/``_confirm_pending``)
    宿主仍是画面 op,经 env.op 消费——计数生命周期 = 节点级,画面 op
    单一归属不变。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickPartnerParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickPartnerOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_partner', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点选脉冲 + 确认脉冲;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        unselected = env.unselected
        if unselected or op._confirm_pulses == 0:
            # 未选中实证(或首轮强制)→ 点候选卡选中。y 由建档「候选-卡区」
            # 带中心锚定:旧 offset「label cy-60」实点落在立绘底边下方卡体
            # 死区(几何根源见 ``_pick_point_for`` 注)。
            op.ctx.controller.mouse_move(op._pick_point)
            op.ctx.controller.click(op._pick_point)
            time.sleep(0.7)
            log.info('[cw-partner] 点选候选 %s(未选中提示在场=%s)',
                     op._pick_point, unselected)
        # bug#1 吞(before_screenshot 移光标)→ overlay 不关 flat-loop(2026-08-06 r6 stall;手动 click 即关)。
        confirm = op._find_text_center(op.screenshot(), '确认选择')
        if confirm is None:
            log.info('[cw-partner] 未找到 确认选择 → round_retry')
            env.round_result = op.round_retry(wait=1)
            return self.round_success('确认点未找到(重试经旁路回传)')
        op.ctx.controller.mouse_move(confirm)
        op.ctx.controller.click(confirm)
        time.sleep(1.0)
        op._confirm_pulses += 1
        # 确认 = 单屏单选的一次确认(用户澄清+建档证据更正 2026-09-14):
        # 本屏无第二画面、无「选强化目标」步——点选→确认 → 重入裁决即完。
        # retry 轮重复确认零副作用(置灰态被游戏拒绝,无确认穿透风险)。
        op._confirm_pending = True
        # 自上报(确认点击发出后;零写,契约面统一。读缺旁路分支未发
        # 确认点击,不上报——见模块头)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_partner_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        env.round_result = op.round_retry(wait=1)
        return self.round_success('伙伴选择确认脉冲已发(重入裁决承接)')
