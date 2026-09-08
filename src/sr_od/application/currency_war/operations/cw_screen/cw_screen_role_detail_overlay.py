"""货币战争 详情弹窗(可合成列表/角色详情)op(空决策形态;T-121/ADR-0584,A7)。

点卡/点角色触发的详情弹窗(1b)的处理:点面板外空白关,验「装备推荐」消失。
关闭机制建档先例:装备详情浮窗 2026-08-14 live 验「点画面空白处→关闭回备战,
无关闭按钮」;角色详情大面板 2026-08-13 live 验「点面板外空白→回备战」。
替代 ESC 的理由:ESC 在浮窗已自关时落备战会误弹「中断挑战」(bug#2 三次
实锤),空白点在 overlay 未开时是无害空点。

入口判据(T-163 锚化,原全屏 OCR「可合成列表」∨「角色详情」退役):迁移
archive 双锚——「按钮-装备推荐」(角色详情变体,4 张归档 fixture 全命中)
∨「装备详情-合成公式」(可合成列表变体,该变体 fixture 命中)。退役理由
(outer_loop.md §2.1「优先 area 化」的存量欠账清偿):全屏「角色详情」与
商店卡牌详情弹窗底部的「角色详情」按钮(x560-930)全等共享(LCS 1.0,
收紧 lcs 无济于事)→ T-163 事故中该弹窗被 1b 垄断 26 分钟。位置约束的
area 锚天然区分两变体(本弹窗底部按钮不在右侧面板锚区内)。

验效(T-163,D3):VERIFY_AREA = 按钮-装备推荐——两变体关闭后面板锚消失;
点空白零效果时锚仍在 → round_fail 交外循环 retry 池(卡死从不可见变
分钟级可见失败),替代旧「无验效恒成功」形态。
"""
from cv2.typing import MatLike

from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenRoleDetailOverlay(CwProgressionScreenOp):
    """详情弹窗:双锚其一(装备推荐/合成公式)命中,点面板外空白关+验效。"""

    SCREEN_NAME = '货币战争-备战-角色详情'
    ENTRY_AREA = ''   # 入口实判为双锚其一(见 entry_ok);同源同参随 1b 锚化
    #: 验效锚:右侧面板「装备推荐」(两变体关闭后均消失;ADR-0454 id_mark 成员)
    VERIFY_AREA = '按钮-装备推荐'
    #: 关闭点击位:备战前后排之间的真空白(面板外,两 overlay 家族共用)
    BLANK_SCREEN = '货币战争-备战'
    BLANK_AREA = '区域-空白关闭'

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-详情弹窗')

    def entry_ok(self, screen: MatLike | None) -> bool:
        # 与外循环 1b 分发判定同源同参(T-163 锚化):装备推荐 ∨ 合成公式
        return (self.round_by_find_area(screen, self.SCREEN_NAME,
                                        '按钮-装备推荐',
                                        crop_first=False).is_success
                or self.round_by_find_area(screen, self.SCREEN_NAME,
                                           '装备详情-合成公式',
                                           crop_first=False).is_success)

    def progress_once(self) -> bool:
        # success_wait=1.5 同 0a4/0t 家族口径:点空白后等关闭动画再进验效
        # (落地审 F1:裸 click 无等待 → 验效截图落在动画窗口 → 假失败
        # 自愈循环;区域-空白关闭为纯定位区,find_and_click 走 else 分支
        # 点建档中心,点击语义等价且自带等待)
        return self.round_by_find_and_click_area(
            self.last_screenshot, self.BLANK_SCREEN, self.BLANK_AREA,
            success_wait=1.5).is_success
