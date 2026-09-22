"""开书册卡动作 op(CwActionOpenBookcardOp)——框架 ``SrOperation`` 直
继承动作 op;机械执行后 **op 内直调自己的上报函数**
``report_action_open_bookcard_param``,零分派(依据 = op-layer.md §1.2
动作 op 契约);机械半 = ``find_bookcards`` 识别 → 点槽中心 → 固定动画
等待(纯机械,识别单一源 = ``obs/cw_identity_obs.py::find_bookcards``)。

终结动作(开卡时机归策略器,发射位 = entry ① prep 实体面卡片臂,
screens/README §5.5):点完开启即引入新事实(专家邀请函弹窗在场)→
本动作终结交回外循环,弹窗由外循环按画面分发 ``CwScreenExpertInvite``
选卡(分发判定单一源 = flow/outer_loop.md §2 阶段一身份分发)。"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.open_bookcard import (
    report_action_open_bookcard_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenBookcardParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenBookcardOp(SrOperation):
    """开书册卡:``find_bookcards`` 识别 → 点槽中心 → 固定动画等待
    (纯机械执行)。终结动作(发射位 = 策略器 entry ① prep 实体面卡片
    臂,screens/README §5.5;弹专家邀请函 = 新事实 → 终结交回,与
    OpenBox 终结化同构,规范锚 = op-layer.md §1.4)。"""

    #: 终结动作(专家邀请函弹窗在场 = 新事实,交回外循环重分发选卡)。
    terminal = True

    #: 交回等待 = 开卡动画等待值(与 prep_actions._OVERLAY_ANIM_WAIT_S
    #: 逐字等价,漂移由等价锁暴露)。
    terminal_wait = 1.8

    def __init__(self, ctx: SrContext, param: CwActionOpenBookcardParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionOpenBookcardOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_bookcard', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """开书册卡:``find_bookcards`` 识别 → 点槽中心 → 固定动画等待。

        点完开启本动作即交回——专家邀请函弹窗由外循环按画面分发
        ``CwScreenExpertInvite`` 选卡(选卡决策不在本执行链)。动画等待取
        家族常量 ``_OVERLAY_ANIM_WAIT_S``;弹窗就位与否交下一帧观察。识别
        按 ``action.slot`` 对位(slot=None = 首张);书册卡识别含
        「青蓝卡+白色书册 icon+『开启』」模板语义,单一源 = ``find_bookcards``。
        """
        action: CwActionOpenBookcardParam = self.param
        env = self.env
        ex = env.executor
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            _ctx_slots,
            find_bookcards,
        )
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        screen = ex._op.screenshot()
        cards = find_bookcards(screen, _ctx_slots(ex._ctx, '备战栏', 9))
        if not cards:
            return self.round_fail('无书册卡')
        picked = cards[0]
        if action.slot is not None:
            matched = next((c for c in cards if c[0] == action.slot), None)
            if matched is None:
                return self.round_fail(
                    f'槽{action.slot} 无书册卡(实读 {cards})')
            picked = matched
        slot, center = picked
        ex._ctx.controller.mouse_move(center)   # 防吞点击(同开箱/采晶矿口径)
        ex._ctx.controller.click(center)
        # 固定动画等待(等待归产生动画的操作,固定等待族 =
        # flow/action_ops.md §2.2;判效交下一帧观察)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][bookcard] 开书册卡槽{slot} → 点开启已发'
                 '(交回外循环,专家邀请函分发选卡)')
        # —— 自上报(机械发出后;op-layer.md §1.2 动作 op 契约):开卡腾席 ——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_open_bookcard_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success(f'开书册卡槽{slot}')
