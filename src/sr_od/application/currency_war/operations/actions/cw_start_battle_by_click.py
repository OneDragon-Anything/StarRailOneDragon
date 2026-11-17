"""出战 op(纯机械:定位出战按钮→点击;公用底层动作原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

_PREP_SCREEN: str = '货币战争-备战'


class CwStartBattleByClick(CwOperation):
    """点击出战按钮(纯机械一段;零校验零特殊处理)。
    起点/终点:货币战争-备战画面自身(点击后是否转场归调用方下一帧观察)。
    消耗:进入战斗(败局扣小队生命值;战斗本身无直接货币消耗)。

    动作 op 契约(用户裁定):状态前置(收店/弹窗/软锁)全部由调用方负责。
    实现注记(如实声明):点击走框架 ``round_by_find_and_click_area``——该框架
    方法对带 text 的 area 自带「OCR 可见才点」门与至多 3 次重试(构造默认),
    即本 op 存在**框架级目标可见性守卫**,非纯盲点;契约字面(盲点机械)与
    此实现的取舍待用户裁决,当前按更安全形态保留。
    其余状态前置仍零处理:不判收店、不处理弹窗、不兜底。

    :param none: 无参数。
    """

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='CW出战',
                             need_check_game_win=False)

    @operation_node(name='点击出战', is_start_node=True)
    def click_start(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, _PREP_SCREEN, '按钮-出战',
            success_wait=1)
