"""货币战争 星徽详情弹窗 op(空决策形态;ADR-0584,A8)。

「XX星徽套组」详情面板(1d,点球/装备操作误点开星徽图标)的处理迁移:
点右上 X 关回备战,无验效。**刻意不用 ESC**(bug#2,原分支注释随迁,
禁在 op 内「顺手统一」成 ESC):面板已关时 ESC 落备战弹「中断挑战」;
X 是弹窗内坐标永远安全。背景:2026-08-17 M53 停机建档。
"""
from cv2.typing import MatLike

from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenEmblemDetailPopup(CwProgressionScreenOp):
    """星徽详情弹窗:双锚入口其一,点「按钮-关闭」(不用 ESC,见模块头)。"""

    SCREEN_NAME = '货币战争-星徽详情'
    ENTRY_AREA = '标识-流派星徽'

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-星徽详情')

    def entry_ok(self, screen: MatLike | None) -> bool:
        # 与外循环 1d 分发判定同源:双锚(流派星徽/套组标题)其一即接管
        if super().entry_ok(screen):
            return True
        return self.round_by_find_area(
            screen, self.SCREEN_NAME, '标识-套组标题',
            crop_first=False).is_success

    def progress_once(self) -> bool:
        # success_wait=1 同原分支内联值
        return self.round_by_find_and_click_area(
            self.last_screenshot, self.SCREEN_NAME, '按钮-关闭',
            success_wait=1).is_success
