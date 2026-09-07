"""货币战争 道具详情弹窗(聘用书类)op(空决策形态;T-121/ADR-0584,A3)。

获得道具(如 3 费聘用书)后自动弹介绍 modal(0e3)的处理迁移:点 × 关闭,
无验效。**入口观察用 OCR 回退**(本画面尚无 screen_info 档案,方案审 N9):
「聘用书」∧ 非祈愿屏,与外循环分发判定同源同参——祈愿试炼选项名含
「聘用书」(4 费聘用书)的截胡死循环修复(r31 实锤 15min+)靠这道排他,
排他双写于外循环分支判定与本 op 入口(两处同参,建档含 id_mark 后 op 侧
可切 area 锚,切换属实施批内部对齐,ADR-0584 §2.2)。
"""
from cv2.typing import MatLike

from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenItemDetailPopup(CwProgressionScreenOp):
    """道具详情弹窗:点 × 关闭;入口 = OCR「聘用书」∧ 非祈愿屏。"""

    SCREEN_NAME = '货币战争-道具详情弹窗'
    ENTRY_AREA = ''   # 无画面档:OCR 回退(见模块头)
    CLOSE_AREA = '按钮-关闭'

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-道具详情弹窗')

    def entry_ok(self, screen: MatLike | None) -> bool:
        # 与外循环 0e3 分发判定同源同参:「聘用书」(lcs 0.8)∧ 祈愿锚不命中
        return (self.round_by_ocr(screen, '聘用书', lcs_percent=0.8).is_success
                and not self.round_by_find_area(
                    screen, '货币战争-祈愿试炼', '标识-祈愿试炼',
                    crop_first=False).is_success)

    def progress_once(self) -> bool:
        close = area_center(self.ctx, self.CLOSE_AREA, self.SCREEN_NAME)
        if close is None:
            return False
        # × 位于 (1862,65)(原 VLM 定位,已 area 化);mouse_move bug#1 缓解保留
        self.ctx.controller.mouse_move(close)
        self.ctx.controller.click(close)
        return True
