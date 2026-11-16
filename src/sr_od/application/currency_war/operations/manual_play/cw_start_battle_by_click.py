"""出战 op(点出战 + 未达上限弹窗条件确认;MCP 手动游玩纯动作)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

_PREP_SCREEN: str = '货币战争-备战'
_WARN_SCREEN: str = '货币战争-未达上限警告'


class CwStartBattleByClick(CwOperation):
    """点击出战开始本节点战斗(含「未达上限」确认弹窗的确定性处理)。
    起点:货币战争-备战;终点:战斗转场(弹窗出现时先点掉),离开备战画面
    (战斗是否实际开启归调用方对局画面观察)。
    消耗:进入战斗(败局扣小队生命值;战斗本身无直接货币消耗)。

    弹窗处理 = 确定性分支(出现即点确认),非决策闸门;「本局不再提示」
    勾选框不代点(留调用方自行决定是否勾选,勾选属玩家偏好)。
    部署是否满员不判断(零判效):未满员时弹窗由本 op 内分支点掉。

    :param none: 无参数。
    """

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='CW出战',
                             need_check_game_win=False)

    @operation_node(name='点击出战', is_start_node=True)
    def click_start(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, _PREP_SCREEN, '按钮-出战',
            until_not_find_all=[(_PREP_SCREEN, '按钮-出战')],
            pre_delay=0.5, success_wait=2, retry_wait=1)

    @operation_node(name='处理未达上限弹窗')
    def handle_warn_dialog(self) -> OperationRoundResult:
        found = self.round_by_find_area(
            self.last_screenshot, _WARN_SCREEN, '标识-未达上限警告')
        if not found.is_success:
            return self.round_success(status='无未达上限弹窗(直接进战斗)')
        return self.round_by_find_and_click_area(
            self.last_screenshot, _WARN_SCREEN, '按钮-确认',
            until_not_find_all=[(_WARN_SCREEN, '标识-未达上限警告')],
            pre_delay=0.3, success_wait=2, retry_wait=1)
