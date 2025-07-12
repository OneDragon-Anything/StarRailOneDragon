import time

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ChooseOeFile(SrOperation):

    def __init__(self, ctx: SrContext, num: int):
        """
        选择存档 最终返回【位面饰品提取】画面
        """
        SrOperation.__init__(self, ctx, op_name=gt('选择存档'))

        self.num: int = num  # 需要选择的存档编号 0代表不选

    @operation_node(name='识别画面', is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        """
        识别当前所在的画面
        :return:
        """
        if self.num < 1 or self.num > 4:
            return self.round_fail('存档编号只能是1~4')

        if self.num == 0:
            return self.round_success('使用默认档案')

        screen = self.screenshot()

        result = self.round_by_find_area(screen, '饰品提取', '左上角标题-饰品提取')
        if result.is_success:
            return self.round_success(result.status)

        result = self.round_by_find_area(screen, '饰品提取', '左上角标题-存档管理')
        if result.is_success:
            return self.round_success(result.status)

        return self.round_retry(status='未在指定页面', wait=1)

    @node_from(from_name='识别画面', status='左上角标题-饰品提取')
    @operation_node(name='点击切换存档')
    def click_switch_file(self) -> OperationRoundResult:
        """
        点击切换存档
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '饰品提取', '按钮-切换存档入口',
                                                 success_wait=1.5, retry_wait=1)

    @node_from(from_name='点击切换存档')
    @operation_node(name='等待存档管理画面')
    def wait_management_screen(self) -> OperationRoundResult:
        """
        等待选择存档的画面
        :return:
        """
        screen = self.screenshot()

        return self.round_by_find_area(screen, '饰品提取', '左上角标题-存档管理', retry_wait=1)

    @node_from(from_name='识别画面', status='左上角标题-存档管理')
    @node_from(from_name='等待存档管理画面')
    @operation_node(name='选择存档')
    def choose_file(self) -> OperationRoundResult:
        """
        选择存档
        :return:
        """
        file_areas = [
            '档案-1',
            '档案-2',
            '档案-3',
            '档案-4',
        ]

        # 点击存档 由于每个存档的名字都不一样 就不使用OCR识别了
        area = self.ctx.screen_loader.get_area('饰品提取', file_areas[self.num-1])
        self.ctx.controller.click(area.center)
        time.sleep(0.25)

        screen = self.screenshot()
        result = self.round_by_find_and_click_area(screen, '饰品提取', '按钮-切换存档确认')
        if result.is_success:
            return self.round_success(result.status, wait=1.5)  # 选择后 等待一会返回外层界面

        result = self.round_by_find_area(screen, '饰品提取', '按钮-存档使用中')
        if result.is_success:
            self.round_by_click_area('菜单', '')
            return self.round_success(result.status, wait=1.5)  # 已经在使用了 返回即可

        return self.round_retry(result.status, wait=1)
