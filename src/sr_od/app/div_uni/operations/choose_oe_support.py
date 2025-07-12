from typing import Optional

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.choose_support import ChooseSupport


class ChooseOeSupport(SrOperation):

    def __init__(self, ctx: SrContext, character_id: Optional[str]):
        """
        在位面饰品提取画面 选择支援
        执行后停留在 位面饰品提取画面
        """
        SrOperation.__init__(self, ctx, op_name=f"{gt('饰品提取', 'game')} {gt('选择支援')}")

        self.character_id: str = character_id
        """支援角色ID"""

        self.found_character: bool = False
        """是否找到支援角色"""

    @operation_node(name='识别画面', is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        """
        识别画面
        :return:
        """
        if self.character_id is None:
            return self.round_success('无需支援')

        screen = self.screenshot()

        return self.round_by_find_area(screen, '饰品提取', '左上角标题-饰品提取', retry_wait=1)

    @node_from(from_name='识别画面', status='左上角标题-饰品提取')
    @operation_node(name='点击支援按钮')
    def click_support(self) -> OperationRoundResult:
        """
        点击支援按钮
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '饰品提取', '按钮-支援',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='点击支援按钮')
    @operation_node(name='选择支援角色')
    def choose_support(self) -> OperationRoundResult:
        """
        选择支援角色
        :return:
        """
        screen = self.screenshot()
        round_result = ChooseSupport.click_avatar(self, screen, self.character_id)
        if round_result.is_success:
            self.found_character = True
        return round_result

    @node_from(from_name='选择支援角色')
    @node_from(from_name='选择支援角色', success=False)
    @operation_node(name='返回')
    def click_empty(self) -> OperationRoundResult:
        """
        选择后 点击空白继续
        :return:
        """
        self.round_by_click_area('饰品提取', '按钮-支援')
        if self.found_character:
            return self.round_success(wait=0.25)
        else:
            return self.round_fail(status=ChooseSupport.STATUS_SUPPORT_NOT_FOUND)
