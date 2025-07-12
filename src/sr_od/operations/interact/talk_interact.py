from cv2.typing import MatLike
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.context.sr_pc_controller import SrPcController
from sr_od.operations.sr_operation import SrOperation


class TalkInteract(SrOperation):

    INTERACT_RECT: ClassVar[Rect] = Rect(1292, 560, 1878, 802)

    def __init__(self, ctx: SrContext, option: str,
                 lcs_percent: float = -1,
                 conversation_seconds: int = 10):
        """
        交谈过程中的交互
        :param ctx:
        :param option: 交谈中选择的选项
        :param lcs_percent: 使用LCS匹配的阈值
        :param conversation_seconds: 交谈最多持续的秒数
        """

        super().__init__(ctx, timeout_seconds=conversation_seconds,
                         op_name=gt('交谈') + ' ' + gt(option, 'ocr'))

        self.option: str = option
        self.lcs_percent: float = lcs_percent
        self.start_time: float = 0

    @operation_node(name='交互', is_start_node=True)
    def interact(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        part = cv2_utils.crop_image_only(screen, TalkInteract.INTERACT_RECT)
        # cv2_utils.show_image(part, wait=0)

        ocr_result = self.ctx.ocr.match_words(part, words=[self.option], lcs_percent=self.lcs_percent)

        if len(ocr_result) == 0:  # 目前没有交互按钮 说明当前在对话 点击继续
            to_click = Point(self.ctx.project_config.screen_standard_width // 2,
                             self.ctx.project_config.screen_standard_height - 100)  # 空白点击继续的地方
            self.ctx.controller.click(to_click)
            return self.round_wait(wait=1)
        else:
            for r in ocr_result.values():
                to_click: Point = r.max.center + TalkInteract.INTERACT_RECT.left_top
                if self.ctx.controller.interact(to_click, SrPcController.TALK_INTERACT_TYPE):
                    return self.round_success()

        return self.round_wait(wait=1)
