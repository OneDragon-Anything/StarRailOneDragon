"""货币战争 补给节点 RunNode(从 ``HandleSupply`` 升级为节点生命周期 owner)。

补给阶段 = 3 选 1 装备 + 确认。RunNode 化后:每轮**验证**"还在补给屏?"(关键词在)→ 点卡身 +
确认 → ``round_retry``;overlay 消失(关键词没了)= 节点完成 → ``round_success``;超预算(点不动)
→ FAIL bail(**不无限烧**,旧 HandleSupply 盲单发失败也回 success → flat loop 无限 round_wait 烧预算)。

动作沿用 HandleSupply(已验证可完成补给:log 实跑 supply→megastar 衔接成功):点卡身 (900,550)
不开对话直接选中 + 确认。本次重构**只改生命周期(验证完成 + 预算),不改动作**,隔离模式效果。

TODO(Stage C4):接 ``cw_decisions.decide_supply`` 按 target_comp.key_equips 契合选,替代默认选中牌。
TODO(task#20):卡位 / 确认坐标进 screen_info。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.run_nodes.run_node import RunNode
from sr_od.context.sr_context import SrContext


class RunSupplyNode(RunNode):
    """补给节点:点卡身选中 + 确认,**验证 overlay 消失**才完成。"""

    CARD_BODY: ClassVar[Point] = Point(900, 550)  # 补给卡 body 不开对话(沿用 HandleSupply)

    def __init__(self, ctx: SrContext):
        RunNode.__init__(self, ctx, op_name='货币战争-补给节点')

    @operation_node(name='补给节点', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        return self._run_node()

    def _in_node(self, screen) -> bool:
        # 还在补给屏 = 「补给阶段」关键词在(lcs 0.8 防与「备战阶段」共享「阶段」误匹配)。
        return self.round_by_ocr(screen, '补给阶段', lcs_percent=0.8).is_success

    def _do_action(self, screen) -> None:
        # 动作沿用 HandleSupply(已验证可完成);只外层套验证 + 预算。
        self.ctx.controller.click(RunSupplyNode.CARD_BODY)
        time.sleep(0.6)
        self.round_by_ocr_and_click(self.screenshot(), '确认', success_wait=1.5)
