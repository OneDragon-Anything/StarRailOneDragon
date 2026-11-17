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

    动作 op 契约(用户裁定):只管机械执行,不管校验、不管特殊情况——
    收店前置(商店开着时点击只收店)、未达上限弹窗确认、投资策略未选完
    的软锁等**状态前置全部由调用方负责**(编排层保证或 agent 按 skill
    画面文档自查);本 op 不判断、不重试、不兜底。

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
