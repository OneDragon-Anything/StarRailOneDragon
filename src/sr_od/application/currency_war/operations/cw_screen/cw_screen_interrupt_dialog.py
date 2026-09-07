"""货币战争 中断挑战 dialog op(空决策形态;T-121/ADR-0584,A9)。

ESC 误按/误点左上角弹出的「是否中断挑战」真模态(1g,历史 3 次实锤;
2026-08-17 建档替原停机钩子)的处理迁移:点右上 X 关回备战,X 点击失败
兜底 ESC(实测无副作用),无验效。

**语义红线(原分支注释随迁)**:点遮罩无效;bot 策略 = 点右上 X 关闭继续
对局——不点「暂时离开」免中断对局,**绝不点「放弃并结算」**(不可逆放弃
进度)。弹窗内「小队生命值」为 HP 真值快照,顺带对账备用,暂不消费。
exogenous popup 行随 op 迁移(r378b 测量链 review B1:误触弹窗是外生事件
高频源,bug#2 ESC 三次实锤)。
"""
import contextlib

from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.application.currency_war.telemetry import recorder
from sr_od.context.sr_context import SrContext


class CwScreenInterruptDialog(CwProgressionScreenOp):
    """中断挑战 dialog:点右上 X 关闭(失败兜底 ESC),绝不点放弃并结算。"""

    SCREEN_NAME = '货币战争-中断挑战弹窗'
    ENTRY_AREA = '标识-中断挑战'

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-中断挑战弹窗')

    def progress_once(self) -> bool:
        with contextlib.suppress(Exception):   # 遥测 best-effort
            recorder.record_exogenous(0, 'popup', detail='中断挑战dialog误触')
        _btn = self.round_by_find_and_click_area(
            self.last_screenshot, self.SCREEN_NAME, '按钮-关闭')
        if _btn.is_success:
            self.park_cursor(after_wait=0.1)
            return True
        # X 点击失败兜底:ESC 同样关闭(实测无副作用)
        self.ctx.controller.esc()
        return True
