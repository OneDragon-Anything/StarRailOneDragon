"""货币战争 阿哈装备选择 overlay op(空决策形态;ADR-0584,A5)。

投资策略「阿哈大悦」装备选择(为阿哈选 1 件简易装备)overlay(0g)的
处理迁移:点第 1 装备自动关 overlay,无验效。**固定策略申报**:点首件 =
现行为(原分支注释「先关 overlay 推进」),按 key_equips 择优属策略面
后续批(契约改版另立,ADR-0584 §2.6——为它设 decide 接口 = 给无选择面
画面造空选择,违契约收缩方向)。背景:bot 不选 → overlay 持续
卡备战(2026-08-07 实跑 plane1 1-3 卡此 overlay 666s)。

首件点击坐标已 area 化(``货币战争-备战``/``按钮-简易装备首件``,矩形
中心 = 原 Point(626,250)「幸运星位」);原分支无 mouse_move,保持。
"""
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen._progression_base import (
    CwProgressionScreenOp,
)
from sr_od.context.sr_context import SrContext


class CwScreenAhaEquipPick(CwProgressionScreenOp):
    """阿哈装备选择:点第 1 装备(固定策略申报,见模块头)。"""

    SCREEN_NAME = '货币战争-备战'
    ENTRY_AREA = '标识-简易装备'
    FIRST_EQUIP_AREA = '按钮-简易装备首件'

    def __init__(self, ctx: SrContext):
        CwProgressionScreenOp.__init__(self, ctx, op_name='货币战争-阿哈装备选择')

    def progress_once(self) -> bool:
        first = area_center(self.ctx, self.FIRST_EQUIP_AREA, self.SCREEN_NAME)
        if first is None:
            return False
        self.ctx.controller.click(first)
        return True
