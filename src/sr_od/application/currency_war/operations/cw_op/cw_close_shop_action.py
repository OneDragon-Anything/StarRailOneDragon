"""关店动作 op(CwActionCloseShopOp)。一 op 一文件。

执行体 = 机械关店(找「按钮-收起」:miss = 店已关,幂等无动作可发;
命中 = 点击 + 固定等待)+ 自上报 ``report_action_close_shop_param``
(leave_screen 结构离屏清场,两出口同调)。零转移验证,落地归下一帧
观察侧对账(flow/action_ops.md §1)。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.close_shop import (
    report_action_close_shop_param,
)
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.kernel.cw_vocab import CwActionCloseShopParam
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)
from sr_od.application.currency_war.prep_actions import SHOP_CLOSE_ANIM_S
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _note_receipt(op: SrOperation, applied: bool, reason: str) -> None:
    """关商店动作回执(receipts 域,渠道②,唯一写点 = kernel 口)。

    两出口全簿记:点击已发 = applied=true;幂等已关(无动作可发)=
    applied=false + reason。发出即簿记非验证;journal 常开
    回执写入无条件,无局跳过在 kernel 口。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_from_ctx,
            note_action_receipt,
        )
        gs = game_state_from_ctx(getattr(op, 'ctx', None))
        if gs is None:
            return
        note_action_receipt(gs, op='CwActionCloseShopOp', applied=applied,
                            reason=reason, screen=SHOP_SCREEN_NAME,
                            actor='CwActionCloseShopOp')
    except Exception as e:  # noqa: BLE001  回执失败不阻塞动作链
        log.warning('[cw][receipt] 关商店回执写入失败(不阻塞): %s', e)


class CwActionCloseShopOp(SrOperation):
    """关店 = 恒可用终结动作 op(恒可用终结不变量 = screens/op-layer.md
    §1.4;终结集总表 = screens/README.md §6):执行即本画面访问结束、
    交回外循环。"""

    #: 终结动作(执行即本画面访问结束,交回外循环)。
    terminal = True
    #: 终结交回等待秒数(无转移动画等待语义)。
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionCloseShopParam,
                 env: ShopExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionCloseShopOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='close_shop', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械关店两出口(均 round_success = 终结交回;零转移验证):

        - 帧上找「按钮-收起」miss = 店已关(幂等,无动作可发)→ 回执
          applied=false + 清场上报;
        - 命中 → 点击 + 固定等待 ``SHOP_CLOSE_ANIM_S`` → 回执
          applied=true + 清场上报。收起消失与否归下一帧观察;点击未生效
          = 外循环 0n 重分发自然重派,重派即重试。
        """
        # 「按钮-收起」融合判定点击(动作 op 体内点击目标定位 = 瞄准,
        # flow/action_ops.md §1 在册允许形态)。
        if not self.round_by_find_and_click_area(
                self.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success:
            _note_receipt(self, False, '商店已关(幂等入口观察,无动作可发)')
            self._report_leave_screen()
            return self.round_success('商店已关(收起不在,幂等入口观察)')
        time.sleep(SHOP_CLOSE_ANIM_S)
        _note_receipt(self, True, '')
        self._report_leave_screen()
        return self.round_success('关店点击已发(机械交回,零转移验证)')

    def _report_leave_screen(self) -> None:
        """清场上报(``report_action_close_shop_param`` = leave_screen 结构
        离屏写):两出口同调,已关残留同样陈旧故同清;容器缺席/已离屏在
        上报函数内静默跳过,失败不阻塞动作链。"""
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                game_state_from_ctx,
            )
            gs = game_state_from_ctx(getattr(self, 'ctx', None))
            if gs is None:
                return
            report_action_close_shop_param(
                gs, self.param,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        except Exception as e:  # noqa: BLE001  清场失败不阻塞动作链
            log.warning('[cw][shop] 关店清场写入失败(不阻塞): %s', e)
