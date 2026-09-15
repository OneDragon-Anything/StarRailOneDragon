"""货币战争 前进按钮 op(空决策形态;ADR-0584,A10)。

简报等画面的「下一步」前进按钮(分支 5)的处理迁移:OCR 找到即点,
无验效,序位近外循环尾(兜底点击)。入口观察 = OCR「下一步」;
推进 = ``round_by_ocr_and_click`` 再定位点击(入口与点击两次 OCR 扫描,
申报:该帧型每局出现次数少,成本可接受;success_wait=2 同原分支内联值)。
"""
from cv2.typing import MatLike

from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenNextButton(CwProgressionScreenOp):
    """前进按钮:OCR「下一步」→ 点击(简报等画面的兜底推进)。"""

    SCREEN_NAME = ''
    ENTRY_AREA = ''   # OCR 入口(无画面档),见模块头

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-前进按钮')

    def entry_ok(self, screen: MatLike | None) -> bool:
        # 与外循环分支 5 判定同源同参(默认 lcs 0.5)
        return self.round_by_ocr(screen, '下一步').is_success

    def progress_once(self) -> bool:
        return self.round_by_ocr_and_click(
            self.last_screenshot, '下一步', success_wait=2).is_success
