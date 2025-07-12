from cv2.typing import MatLike
from typing import ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ClickChallenge(SrOperation):

    """
    点击挑战
    """

    CHALLENGE_BTN_RECT: ClassVar[Rect] = Rect(1360, 950, 1890, 1010)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=gt('点击挑战'))  # 交互后打开副本页面大概需要3秒 所以重试设置5次

    @operation_node(name='点击', is_start_node=True)
    def click(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()
        return self.round_by_find_and_click_area(screen, '挑战副本', '挑战按钮',
                                                 success_wait=1, retry_wait=1)
