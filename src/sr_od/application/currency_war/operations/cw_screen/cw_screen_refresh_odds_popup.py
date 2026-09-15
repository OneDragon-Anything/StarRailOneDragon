"""货币战争 商店刷新概率表弹窗 op(空决策形态;ADR-0584,A2)。

点球误触开后遮出战按钮的实机事故补分支(0e2)的处理迁移:点 × 关闭,
无验效(关闭确认由下轮外循环重判承接)。× 坐标已 area 化
(``货币战争-商店刷新概率表``/``按钮-关闭概率表``,矩形中心 = 原 Point
(1501,263),坐标单一真相源);``mouse_move`` 先行保留(bug#1 缓解:
恢复原语同坐标点击曾落空,原分支注释)。
"""
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenRefreshOddsPopup(CwProgressionScreenOp):
    """商店刷新概率表弹窗:点 × 关闭(mouse_move bug#1 缓解保留)。"""

    SCREEN_NAME = '货币战争-商店刷新概率表'
    ENTRY_AREA = '标识-刷新概率表'
    CLOSE_AREA = '按钮-关闭概率表'

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-商店刷新概率表')

    def progress_once(self) -> bool:
        close = area_center(self.ctx, self.CLOSE_AREA, self.SCREEN_NAME)
        if close is None:
            return False   # 建档缺失(分发锚预检会先炸,此处兜不命中)
        self.ctx.controller.mouse_move(close)
        self.ctx.controller.click(close)
        return True
