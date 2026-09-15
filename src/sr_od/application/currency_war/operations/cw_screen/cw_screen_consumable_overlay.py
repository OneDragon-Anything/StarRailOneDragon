"""货币战争 消耗品详情浮层 op(空决策形态;ADR-0584,A4)。

获消耗品奖励(投资策略「星星相印」给【员工投影仪】等)后游戏自动弹介绍
modal(0f')的处理迁移:点 modal 右上 × 关,无验效。× 复用同族建档
「货币战争-道具详情弹窗/按钮-关闭」(消耗品 modal 与聘用书 modal 同为
道具详情弹窗家族,× 同位;**待实机核**:消耗品帧上该坐标未实机复点)。
替代 ESC 的理由:× 是弹窗内坐标永远安全,ESC 在 modal 已自关时落备战
会误弹「中断挑战」(bug#2)。背景(原分支注释):2026-08-06 实跑
plane2 supply 后弹「员工投影仪」modal,flat retry ~19min 失败——非策略死,
UI 弹窗卡死。签名「消耗品」(类型 label) AND 「拖动到」(拖动使用说明,
只出现在消耗品详情 modal,备战底部消耗品栏无)→ 双条件精确,不误匹配备战;
装备类详情 modal(无「拖动到」)是长尾,观察到再补。
"""
from cv2.typing import MatLike

from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenConsumableOverlay(CwProgressionScreenOp):
    """消耗品详情浮层:双 OCR 条件入口,点右上 × 关闭。"""

    SCREEN_NAME = ''
    ENTRY_AREA = ''   # 双 OCR 条件入口(无画面档),见模块头
    #: 关闭控件:同族「道具详情弹窗」的右上 ×(道具详情弹窗家族共用)
    CLOSE_SCREEN = '货币战争-道具详情弹窗'
    CLOSE_AREA = '按钮-关闭'

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-消耗品浮层')

    def entry_ok(self, screen: MatLike | None) -> bool:
        # 与外循环 0f' 分发判定同源同参:双 lcs 0.9 精确签名
        return (self.round_by_ocr(screen, '消耗品', lcs_percent=0.9).is_success
                and self.round_by_ocr(screen, '拖动到', lcs_percent=0.9).is_success)

    def progress_once(self) -> bool:
        _close = area_center(self.ctx, self.CLOSE_AREA, self.CLOSE_SCREEN)
        if _close is None:
            return False
        # mouse_move+click 同 CwScreenItemDetailPopup(同族 modal 的 bug#1 缓解保留)
        self.ctx.controller.mouse_move(_close)
        self.ctx.controller.click(_close)
        return True
