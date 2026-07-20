import time

from cv2.typing import MatLike
from typing import List

from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils, cv2_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def check_line_green(ctx: SrContext, screen: MatLike, lcs_percent):
    """
    检查弹珠机轨迹是否连通;;
    """
    words = get_move_interact_words(ctx, screen)
    for word in words:
        if str_utils.find_by_lcs(word.data, gt('轨迹连通', 'ocr'), percent=lcs_percent):
            return word
    return None


def get_move_interact_words(ctx: SrContext, screen: MatLike) -> List[MatchResult]:
    """
    获取交互文本
    :param ctx:
    :param screen:
    :return:
    """
    area = ctx.screen_loader.get_area('弹珠机', '移动交互-单行')
    part, _ = cv2_utils.crop_image(screen, area.rect)
    # cv2_utils.show_image(white_part, wait=0)

    word = ctx.ocr.run_ocr_single_line(part)
    if word is not None:
        return [MatchResult(1, area.rect.x1, area.rect.y1, area.rect.width, area.rect.height, data=word)]
    else:
        return []


class Catapult(SrOperation):
    """
    弹珠机
    """

    def __init__(self, ctx: SrContext, lcs_percent: float = 0.1):
        """
        :param ctx:
        :param lcs_percent: ocr匹配阈值
        """
        super().__init__(ctx)
        self.lcs_percent: float = lcs_percent

    @operation_node(name='画面识别', is_start_node=True, screenshot_before_round=False)
    def check_on_screen(self) -> OperationRoundResult:
        """
        在屏幕上找到交互内容进行交互
        :return: 操作结果
        """
        time.sleep(3)  # 稍微等待一下 可能路径连线还没完成
        screen = self.screenshot()
        word_pos = check_line_green(self.ctx, screen, lcs_percent=self.lcs_percent)
        if word_pos:
            self.round_by_click_area('弹珠机', '弹射')
            return self.round_success()
        else:
            self.leave_trillion()
            return self.round_fail('连通线路被阻挡')

    def leave_trillion(self):
        self.round_by_click_area('弹珠机', '离开按钮')
        time.sleep(1)
        self.round_by_click_area('弹珠机', '退出对话框-确认')
