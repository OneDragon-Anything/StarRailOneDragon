"""点试用角色揭示卡动作 op(CwActionRevealTrialOp)。

终结动作:发光金卡点开即免费得 2★ 试用角色(原地变普通角色卡,后续
SIFT 自然识别)——揭示即引入新事实,点完本动作即交回外循环,下一入口
heavy 观察读到揭示后真实板面再续决策(与 OpenBox R7 终结化同构)。
发射位 = 策略器 entry ① prep 实体面卡片臂(容器 bench 槽位 kind
'trial_card' 触发;原「备战环入口清场段 ``cw_screen_prep._clear_prep_cards``
直接清」已按用户裁定 2026-09-19 撤销——开卡时机归策略实现管)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_reveal_trial_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionRevealTrialParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionRevealTrialOp(SrOperation):
    """点试用角色揭示卡:``find_trial_reveal_cards`` 识别 → 点槽中心 →
    固定动画等待(纯机械执行)。终结动作。"""

    #: 终结动作(揭示即引入新事实:板上多一个未知 2★ 角色,交回外循环
    #: 重观察;禁在揭示帧上续决策)。
    terminal = True

    #: 交回等待 = 揭示动画窗(发光消散 + 角色卡落位;原备战环入口清场
    #: 揭示等待值逐字沿用,行为等价)。
    terminal_wait = 1.2

    def __init__(self, ctx: SrContext, param: CwActionRevealTrialParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionRevealTrialOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='reveal_trial', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行;终结动作(交回等待归消费点按 ``terminal_wait`` 读)。"""
        action: CwActionRevealTrialParam = self.param
        env = self.env
        ex = env.executor
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            _ctx_slots,
            find_trial_reveal_cards,
        )
        screen = ex._op.screenshot()
        cards = find_trial_reveal_cards(
            screen, _ctx_slots(ex._ctx, '备战栏', 9))
        if not cards:
            return self.round_fail('无试用角色揭示卡')
        picked = cards[0]
        if action.slot is not None:
            matched = next((c for c in cards if c[0] == action.slot), None)
            if matched is None:
                return self.round_fail(
                    f'槽{action.slot} 无试用角色揭示卡(实读 {cards})')
            picked = matched
        slot, center = picked
        ex._ctx.controller.mouse_move(center)   # bug#1 缓解(同开箱/开卡口径)
        ex._ctx.controller.click(center)
        # 固定动画等待(A3 纪律:等待归产生动画的操作;判效交下一帧观察)
        time.sleep(self.terminal_wait)
        log.info(f'[cw][trial] 试用角色揭示卡槽{slot} → 点击揭示已发'
                 '(终结交回外循环,免费 2★ 入席待观察)')
        # —— 自上报(机械发出后;零写族,揭示身份归观察收口)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_reveal_trial_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success(f'揭示试用角色槽{slot}')
