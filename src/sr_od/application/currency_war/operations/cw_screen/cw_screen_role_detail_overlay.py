"""货币战争 详情弹窗(可合成列表/角色详情)op(空决策形态;T-121/ADR-0584,A7)。

点卡/点角色触发的详情弹窗(1b)的处理迁移:点面板外空白关,无验效。
关闭机制建档先例:装备详情浮窗 2026-08-14 live 验「点画面空白处→关闭回备战,
无关闭按钮」;角色详情大面板 2026-08-13 live 验「点面板外空白→回备战」。
替代 ESC 的理由:ESC 在浮窗已自关时落备战会误弹「中断挑战」(bug#2 三次
实锤),空白点在 overlay 未开时是无害空点。
lcs_percent=0.8 的理由(原分支注释,随迁):「角色详情」与 invest env 等屏的
「角色」label 共享「角色」(2/4=0.5)→ 不收紧则凡有"角色"标签的屏都被
吞 → 卡死(2026-08-04 实跑,1b 修复引入的误匹配)。序位:本分支在
外循环备战分支**后**才到达(双锚不命中才轮到),分发序不动。

⚠️ 待实机核(离线正形化):两 overlay 帧上「区域-空白关闭」坐标未实机复点
(关闭机制经建档 live 验;坐标取 prep.md 2026-08-14 实测真空白,建档见
货币战争-备战「区域-空白关闭」)。
"""
from cv2.typing import MatLike

from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenRoleDetailOverlay(CwProgressionScreenOp):
    """详情弹窗(可合成列表/角色详情):双 OCR 入口其一,点面板外空白关闭。"""

    SCREEN_NAME = ''
    ENTRY_AREA = ''   # 双 OCR 条件入口(无画面档),见模块头
    #: 关闭点击位:备战前后排之间的真空白(面板外,两 overlay 家族共用)
    BLANK_SCREEN = '货币战争-备战'
    BLANK_AREA = '区域-空白关闭'

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-详情弹窗')

    def entry_ok(self, screen: MatLike | None) -> bool:
        # 与外循环 1b 分发判定同源同参:「可合成列表」∨「角色详情」(lcs 0.8)
        return (self.round_by_ocr(screen, '可合成列表', lcs_percent=0.8).is_success
                or self.round_by_ocr(screen, '角色详情', lcs_percent=0.8).is_success)

    def progress_once(self) -> bool:
        _blank = area_center(self.ctx, self.BLANK_AREA, self.BLANK_SCREEN)
        if _blank is None:
            return False
        self.ctx.controller.click(_blank)
        return True
