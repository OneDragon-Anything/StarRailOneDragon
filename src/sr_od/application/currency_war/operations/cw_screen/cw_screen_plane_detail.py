"""货币战争 位面详情 overlay op(空决策形态;T-121/ADR-0584,A1)。

主循环兜底分支 0a4 的处理迁移:情报采集 op 失败退出残留/开局自动弹出等
一切来源的位面详情 → 点 X 验标题消失。此前不在 0 系名单的教训(2026-08-30
残局恢复局,ADR-0269「新增画面忘进名单」结构性缺口)见外循环分支注释。
"""
from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenPlaneDetail(CwProgressionScreenOp):
    """位面详情:点「按钮-关闭位面详情」→ 重入观察裁决交回(验证废除)。"""

    SCREEN_NAME = '货币战争-位面详情'
    ENTRY_AREA = '标识-位面详情标题'

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-位面详情')

    def progress_once(self) -> bool:
        # success_wait=1.5 同原分支内联值:点 X 后等过渡动画再交回裁决
        return self.round_by_find_and_click_area(
            self.last_screenshot, self.SCREEN_NAME, '按钮-关闭位面详情',
            success_wait=1.5).is_success
