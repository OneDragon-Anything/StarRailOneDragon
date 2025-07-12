from cv2.typing import MatLike
from typing import ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ClickStartChallenge(SrOperation):


    START_CHALLENGE_BTN_RECT: ClassVar[Rect] = Rect(1500, 960, 1840, 1010)

    def __init__(self, ctx: SrContext):
        """
        在队伍页面
        点击【开始挑战】
        """
        SrOperation.__init__(self, ctx, op_name=gt('点击开始挑战'))

    @operation_node(name='点击', is_start_node=True)
    def click(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()

        return self.round_by_find_and_click_area(screen, '挑战副本', '开始挑战按钮',
                                                 success_wait=1, retry_wait=1)
