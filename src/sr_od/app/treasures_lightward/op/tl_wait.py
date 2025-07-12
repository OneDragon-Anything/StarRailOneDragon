from typing import List

from basic.i18_utils import gt
from sr.context.context import Context
from sr.operation import Operation, OperationOneRoundResult, StateOperation, StateOperationNode, StateOperationEdge
from sr.screen_area.screen_treasures_lightward import ScreenTreasuresLightWard


class TlWaitNodeStart(StateOperation):

    def __init__(self, ctx: Context, first: bool):
        """
        需要在逐光捡金节点内使用
        等待界面加载
        :param ctx: 上下文
        :param first: 是否第一个节点
        """
        edges: List[StateOperationEdge] = []

        click_empty = StateOperationNode('点击空白处关闭', self._click_empty)
        wait = StateOperationNode('等待可移动画面', self._wait)
        edges.append(StateOperationEdge(click_empty, wait))

        super().__init__(ctx, try_times=15,
                         op_name=gt('逐光捡金 等待节点加载'),
                         edges=edges,
                         specified_start_node=click_empty if first else wait
                         )

    def _click_empty(self) -> OperationOneRoundResult:
        """
        第一个节点时存在 点击关闭显示的BUFF
        :return:
        """
        click = self.find_and_click_area(ScreenTreasuresLightWard.NODE_FIRST_CLICK_EMPTY.value)
        if click == Operation.OCR_CLICK_SUCCESS:
            return self.round_success(wait=1)
        else:
            return self.round_retry('点击空白处关闭失败', wait=1)

    def _wait(self) -> OperationOneRoundResult:
        """
        等待加载
        :return:
        """
        if self.find_area(ScreenTreasuresLightWard.EXIT_BTN.value):
            return self.round_success()
        else:
            return self.round_retry('未在可移动画面', wait=1)
