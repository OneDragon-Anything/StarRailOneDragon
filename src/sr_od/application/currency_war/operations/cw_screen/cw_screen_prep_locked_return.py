"""货币战争 备战暗色锁定返回 op(空决策形态;ADR-0584,A6)。

备战「锁定」暗色子态族(0m)的处理迁移:点右上「返回XX选择」按钮回对应
overlay,无验效(回 overlay 由下轮外循环重判)。一份 op 类服务两个画面档
(``货币战争-备战-策略锁定``/``货币战争-备战-遭遇锁定``),分发处传入命中
的那对(带参构造先例 = ``CwScreenBattleWait(ctx, st, config)``)。

背景(原分支注释):overlay 点「返回备战界面」→ 备战画面带暗色蒙层,
此态下备战双锚仍精准命中——不先分流会被当正常备战操作(读暗牌/暗 gold);
通用规则单一源 = screen_flow_timing.md #18(暗色态判别锚 = 右上按钮)。
"""
from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenPrepLockedReturn(CwProgressionScreenOp):
    """备战暗色锁定子态:点「返回XX选择」按钮(画面档参数化)。"""

    def __init__(self, ctx: SrContext, screen_name: str, area_name: str):
        """:param screen_name: 命中的画面档(策略锁定/遭遇锁定二选一)
        :param area_name: 该画面的返回按钮锚(入口与点击同锚)"""
        CwProgressionScreenOp.__init__(
            self, ctx, op_name='货币战争-备战暗色锁定',
            screen_name=screen_name, entry_area=area_name)

    def progress_once(self) -> bool:
        # success_wait=1.5 同原分支内联值;入口与点击同一按钮锚
        return self.round_by_find_and_click_area(
            self.last_screenshot, self._screen_name, self._entry_area,
            success_wait=1.5).is_success
