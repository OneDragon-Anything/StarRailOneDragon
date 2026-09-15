"""货币战争 商店卡牌详情弹窗 op(空决策形态;ADR-0584 合同)。

奖励节点点球误触开的「角色 offer 购买页」弹窗(实机事故第三例同族:
0e2 概率表/1d 星徽详情之后),中央角色大面板 + 底部五牌条 + 角色详情/购买
双按钮 + 右上 X。建档 = 货币战争-商店卡牌详情(id_mark = 弹窗前景独有
双锚「按钮-购买」+「按钮-角色详情」,禁取衬底透出的底层锚)。

处理 = 点 X 关闭(弹窗内坐标,1d 先例「永远安全」;不点购买——买不买的
决策归商店域,关闭动作不得代替购买决策)→ 机械交回(验证废除批,用户
裁定 2026-09-10:动作 op 禁验证;原「验 X 消失」判效半拆除,落地由基类
重入观察裁决承载——X 点击零效果时锚仍在 → 重入再做一次,预算耗尽 FAIL
交外循环,事故 26 分钟放大器的防线语义由重入裁决 + 有界 FAIL 保持)
→ 交回外循环全分支重判(店开 → 0n 商店访问接管购买;备战 → 备战环)。
**X 复用大厅同族模板** cw_lobby_close
(同款关闭控件,失败帧实测 conf 0.98;备战右上数据统计按钮与 X 区重叠但
模板实测零误配,见建档对拍)。

序位:0 系(先于 0n 开商店与备战双锚)——弹窗暗色衬底会遮蔽底层全部
锚(实证:开商店三锚与备战双锚在该衬底下 OCR 全灭),不先分流
则只剩变体不敏感的关键词兜底接住 = 事故形态。
"""
from cv2.typing import MatLike

from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenShopCardDetailPopup(CwProgressionScreenOp):
    """商店卡牌详情弹窗:双 id_mark 锚入口,点 X → 重入裁决交回(验证废除)。"""

    SCREEN_NAME = '货币战争-商店卡牌详情'
    ENTRY_AREA = '按钮-购买'   # 入口实判为双锚(见 entry_ok);此值供基类读面

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-商店卡牌详情')

    def entry_ok(self, screen: MatLike | None) -> bool:
        # 与外循环 0t 分发判定同源同参:双 id_mark 锚(购买 ∧ 角色详情)——
        # 双锚全中才接管,单锚形态(如其他弹窗带购买按钮)不放行
        return (self.round_by_find_area(screen, self.SCREEN_NAME, '按钮-购买',
                                        crop_first=False).is_success
                and self.round_by_find_area(screen, self.SCREEN_NAME,
                                            '按钮-角色详情',
                                            crop_first=False).is_success)

    def progress_once(self) -> bool:
        # success_wait=1.5:点 X 后等关闭动画再交回裁决(同 0a4 位面详情口径)
        return self.round_by_find_and_click_area(
            self.last_screenshot, self.SCREEN_NAME, '按钮-关闭',
            success_wait=1.5).is_success
