from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.choose_support import ChooseSupport


class ChooseOeSupport(SrOperation):

    STATUS_DUPLICATE_REPLACED: ClassVar[str] = '已替换重复角色'

    def __init__(self, ctx: SrContext, character_id: str | None):
        """
        在位面饰品提取画面 选择支援
        执行后停留在 位面饰品提取画面
        """
        SrOperation.__init__(self, ctx, op_name=f"{gt('饰品提取', 'game')} {gt('选择支援')}")

        self.character_id: str | None = character_id
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

        screen = self.last_screenshot

        return self.round_by_find_area(screen, '饰品提取', '左上角标题-饰品提取', retry_wait=1)

    @node_from(from_name='识别画面', status='左上角标题-饰品提取')
    @operation_node(name='点击支援按钮')
    def click_support(self) -> OperationRoundResult:
        """
        点击支援按钮
        :return:
        """
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(screen, '饰品提取', '按钮-支援',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='点击支援按钮')
    @operation_node(name='检测替换图标', node_max_retry_times=10)
    def check_duplicate_replaced(self) -> OperationRoundResult:
        """
        检查目标角色头像是否有替换图标
        找不到角色时滑动列表重试
        """
        screen = self.screenshot()
        pos = ChooseSupport.get_character_pos(self, screen, self.character_id)
        return ChooseSupport.check_replace_icon(
            self, screen, pos,
            '队伍', '角色列表',
            '饰品提取', '支援角色替换图标',
            ChooseOeSupport.STATUS_DUPLICATE_REPLACED
        )

    @node_from(from_name='检测替换图标')
    @node_from(from_name='检测替换图标', success=False)
    @operation_node(name='踢掉自己的角色', node_max_retry_times=10)
    def remove_chara(self) -> OperationRoundResult:
        """
        游戏内的角色不能直接替换, 可以踢掉4号位让支援角色入队
        """
        return self.round_by_click_area('饰品提取', '支援入队踢4号位角色')

    @node_from(from_name='检测替换图标', status=STATUS_DUPLICATE_REPLACED)
    @node_from(from_name='踢掉自己的角色')
    @operation_node(name='选择支援角色')
    def choose_support(self) -> OperationRoundResult:
        """
        选择支援角色
        :return:
        """
        screen = self.last_screenshot
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
