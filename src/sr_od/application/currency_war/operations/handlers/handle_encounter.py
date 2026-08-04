"""货币战争 遭遇节点 二选一处理 op(从主循环 ``CurrencyWarRunLoop`` 拆出)。

检测「遭遇其一」+ 底部「选择」→ 点卡身选中 + 点选择确认。2026-08-04 实测交互模型
(见 ``docs/game/screens/currency_war_encounter.md``):
  点卡身(选中)→ 点选择(确认),**中间不要插空白点击**(会取消选中 → 死循环)。

bug#1 mitigation: 关键 click 前 ``mouse_move``(零移动 click 不被 before_screenshot 判 drag)。

TODO(Stage C2):接 ``cw_decisions.decide_encounter``(待实现,design 08§遭遇)按 comp 成型度 +
  遭遇词缀选卡(避开急速制冷/正当防卫等克 comp 的),替代当前默认选左卡(难度低、稳)。
TODO(task#20):卡身/选择坐标进 screen_info(遭遇屏 ``currency_war_encounter`` 未建模)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleEncounter(SrOperation):
    """遭遇节点二选一:点卡选中 + 选择确认。"""

    # 遭遇卡卡身中心。左卡=遭遇其一(难度低,金币×2);右卡=遭遇其四(难度高,随机4费角色×3)。
    CARD_LEFT: ClassVar[Point] = Point(665, 500)
    CARD_RIGHT: ClassVar[Point] = Point(1288, 550)
    # 底部「选择」按钮中心(未选中卡时灰置禁用,选中后才可点)。
    SELECT_BTN: ClassVar[Point] = Point(1082, 898)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-遭遇节点')

    @operation_node(name='遭遇节点', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_ocr(screen, '遭遇其一').is_success:
            return self.round_fail('非遭遇节点屏')
        # 默认选左卡(难度低、稳);TODO 策略化按 comp 选左/右。
        card = HandleEncounter.CARD_LEFT
        self.ctx.controller.mouse_move(card)  # bug#1 mitigation
        time.sleep(0.3)
        self.ctx.controller.click(card)
        time.sleep(0.8)
        self.ctx.controller.mouse_move(HandleEncounter.SELECT_BTN)
        time.sleep(0.3)
        self.ctx.controller.click(HandleEncounter.SELECT_BTN)
        return self.round_success(wait=2)
