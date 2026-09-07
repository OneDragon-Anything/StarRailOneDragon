"""货币战争 详情弹窗(可合成列表/角色详情)op(空决策形态;T-121/ADR-0584,A7)。

点卡/点角色触发的详情弹窗(1b)的处理迁移:ESC 关,无验效。
lcs_percent=0.8 的理由(原分支注释,随迁):「角色详情」与 invest env 等屏的
「角色」label 共享「角色」(2/4=0.5)→ 不收紧则凡有"角色"标签的屏都被
吞 → ESC 卡死(2026-08-04 实跑,1b 修复引入的误匹配)。序位:本分支在
外循环备战分支**后**才到达(双锚不命中才轮到),分发序不动。
"""
from cv2.typing import MatLike

from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenRoleDetailOverlay(CwProgressionScreenOp):
    """详情弹窗(可合成列表/角色详情):双 OCR 入口其一,ESC 关闭。"""

    SCREEN_NAME = ''
    ENTRY_AREA = ''   # 双 OCR 条件入口(无画面档),见模块头

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-详情弹窗')

    def entry_ok(self, screen: MatLike | None) -> bool:
        # 与外循环 1b 分发判定同源同参:「可合成列表」∨「角色详情」(lcs 0.8)
        return (self.round_by_ocr(screen, '可合成列表', lcs_percent=0.8).is_success
                or self.round_by_ocr(screen, '角色详情', lcs_percent=0.8).is_success)

    def progress_once(self) -> bool:
        self.ctx.controller.btn_tap('esc')
        return True
