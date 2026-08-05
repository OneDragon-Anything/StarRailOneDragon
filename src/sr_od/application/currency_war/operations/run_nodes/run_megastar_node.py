"""货币战争 巨星节点 RunNode(位面首领 round6 的巨星选择 overlay)。

实机(2026-08-04):强化角色**可选**,不选也能确认推进 —— 点确认后 overlay 消失、回备战 1-6
出战。套 RunNode 验证(overlay 消失=完成)+ 预算(点不动 bail,不再无限烧预算)。

TODO(策略):候选按 target_comp 选(现默认左=花火);强化角色可后续接(可选,不影响推进)。
TODO(task#20):候选/确认坐标进 screen_info。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.run_nodes.run_node import RunNode
from sr_od.context.sr_context import SrContext


class RunMegastarNode(RunNode):
    """巨星节点:选候选成巨星 + 确认(强化角色可选)。验证 overlay 消失才完成。"""

    # 左候选(花火)位 —— 实机 bot 点 (822,333) 已选中花火(金边)。
    CANDIDATE_LEFT: ClassVar[Point] = Point(822, 333)
    # 「确认选择」钮中心(OCR 确认选择 x1442y548;钮中心 ~1490,560)。
    CONFIRM: ClassVar[Point] = Point(1490, 560)

    def __init__(self, ctx: SrContext):
        RunNode.__init__(self, ctx, op_name='货币战争-巨星节点')

    @operation_node(name='巨星节点', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        return self._run_node()

    def _in_node(self, screen) -> bool:
        # 巨星 overlay:有「确认选择」且非「选择伙伴」(选择伙伴候选是 stage 立绘,由 RunSelectPartner 接)。
        # lcs 0.7:防「确认选择」与「请选择投资策略」共享「选择」(2/4=0.5)误匹配。
        return (self.round_by_ocr(screen, '确认选择', lcs_percent=0.7).is_success
                and not self.round_by_ocr(screen, '选择伙伴', lcs_percent=0.7).is_success)

    def _do_action(self, screen) -> None:
        self.ctx.controller.click(RunMegastarNode.CANDIDATE_LEFT)
        time.sleep(0.6)
        self.ctx.controller.click(RunMegastarNode.CONFIRM)
