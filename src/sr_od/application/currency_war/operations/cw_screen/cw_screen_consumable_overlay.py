"""货币战争 消耗品详情浮层 op(空决策形态;T-121/ADR-0584,A4)。

获消耗品奖励(投资策略「星星相印」给【员工投影仪】等)后游戏自动弹介绍
modal(0f')的处理迁移:ESC 关,无验效。背景(原分支注释):2026-08-06 实跑
plane2 supply 后弹「员工投影仪」modal,flat retry ~19min 失败——非策略死,
UI 弹窗卡死。签名「消耗品」(类型 label) AND 「拖动到」(拖动使用说明,
只出现在消耗品详情 modal,备战底部消耗品栏无)→ 双条件精确,不误匹配备战;
装备类详情 modal(无「拖动到」)是长尾,观察到再补。
"""
from cv2.typing import MatLike

from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenConsumableOverlay(CwProgressionScreenOp):
    """消耗品详情浮层:双 OCR 条件入口,ESC 关闭。"""

    SCREEN_NAME = ''
    ENTRY_AREA = ''   # 双 OCR 条件入口(无画面档),见模块头

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-消耗品浮层')

    def entry_ok(self, screen: MatLike | None) -> bool:
        # 与外循环 0f' 分发判定同源同参:双 lcs 0.9 精确签名
        return (self.round_by_ocr(screen, '消耗品', lcs_percent=0.9).is_success
                and self.round_by_ocr(screen, '拖动到', lcs_percent=0.9).is_success)

    def progress_once(self) -> bool:
        self.ctx.controller.btn_tap('esc')
        return True
