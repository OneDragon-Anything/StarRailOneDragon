from cv2.typing import MatLike
from typing import Tuple

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guid_choose_tab import GuideChooseTab
from sr_od.interastral_peace_guide.open_guide import GuideOpen
from sr_od.operations.sr_operation import SrOperation


class GuidePowerResult:

    def __init__(self, power: int, qty: int):
        self.power: int = power  # 体力
        self.qty: int = qty  # 沉浸器数量


class GuideCheckPower(SrOperation):

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=gt('指南检查体力'))

    @operation_node(name='打开指南', is_start_node=True)
    def open_guide(self) -> OperationRoundResult:
        op = GuideOpen(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开指南')
    @operation_node(name='选择生存索引')
    def choose_guide_tab(self) -> OperationRoundResult:
        tab = self.ctx.guide_data.best_match_tab_by_name(gt('生存索引', 'game'))
        op = GuideChooseTab(self.ctx, tab)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择生存索引')
    @operation_node(name='识别开拓力和沉浸器数量')
    def check_power(self) -> OperationRoundResult:
        screen = self.screenshot()
        x, y = self.get_power_and_qty(screen)

        if x is None or y is None:
            return self.round_retry('检测开拓力和沉浸器数量失败', wait=1)

        log.info('检测当前体力 %d 沉浸器数量 %d', x, y)

        return self.round_success(data=GuidePowerResult(x, y))

    def get_power_and_qty(self, screen: MatLike) -> tuple[int | None, int | None]:
        """
        获取开拓力和沉浸器数量
        :param screen: 屏幕截图
        :return:
        """
        area1 = self.ctx.screen_loader.get_area('星际和平指南', '生存索引-完整体力')
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(screen, rect=area1.rect)
        if len(ocr_result_list) > 0:
            found_300 = False
            found_slash = False
            power_str = ocr_result_list[0].data
            if power_str[-1] == '+':
                power_str = power_str[:-1]
            if power_str[-3:] == '300':
                found_300 = True
                power_str = power_str[:-3]
            if power_str[-1] == '/':
                found_slash = True
                power_str = power_str[:-1]
            if found_300 and not found_slash and power_str[-1] == '1':  # 有可能 / 识别成 1 了
                power_str = power_str[:-1]

            power = str_utils.get_positive_digits(power_str, err=None)
        else:
            area1 = self.ctx.screen_loader.get_area('星际和平指南', '生存索引-体力')
            part = cv2_utils.crop_image_only(screen, area1.rect)
            ocr_result = self.ctx.ocr.run_ocr_single_line(part)
            power = str_utils.get_positive_digits(ocr_result, err=None)

        area2 = self.ctx.screen_loader.get_area('星际和平指南', '生存索引-完整沉浸器数量')
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(screen, rect=area2.rect)
        if len(ocr_result_list) > 0:
            found_12 = False
            found_slash = False
            qty_str = ocr_result_list[0].data
            if qty_str[-1] == '+':
                qty_str = qty_str[:-1]
            if qty_str[-2:] == '12':
                found_12 = True
                qty_str = qty_str[:-2]
            if qty_str[-1] == '/':
                found_slash = True
                qty_str = qty_str[:-1]
            if found_12 and not found_slash and qty_str[-1] == '1':  # 有可能 / 识别成 1 了
                qty_str = qty_str[:-1]
            qty = str_utils.get_positive_digits(qty_str, err=None)
        else:
            area2 = self.ctx.screen_loader.get_area('星际和平指南', '生存索引-沉浸器数量')
            part = cv2_utils.crop_image_only(screen, area2.rect)
            ocr_result = self.ctx.ocr.run_ocr_single_line(part)
            qty = str_utils.get_positive_digits(ocr_result, err=None)

        return power, qty


def __debug_get_power_and_qty() -> None:
    ctx = SrContext()
    ctx.init_ocr()
    op = GuideCheckPower(ctx)
    from one_dragon.utils import debug_utils
    screen = debug_utils.get_debug_image('_1760254683683')
    print(op.get_power_and_qty(screen))


if __name__ == '__main__':
    __debug_get_power_and_qty()