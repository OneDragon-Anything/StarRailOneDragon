import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.application.currency_war.operations.prep.deploy_bench import DeployBench
from sr_od.application.currency_war.operations.prep.shop import BuyShopCards
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class BattlePrepCycle(SrOperation):
    """货币战争 备战单轮自动化:买牌 → 部署 → 出战。

    把三个已实机验证的子 op 串成单轮:``BuyShopCards``(开商店 naive 买 3-5 张 + sell/升等级)→
    ``DeployBench``(拖备战栏→舞台前排优先)→ 点「出战」进自动战斗。
    naive 策略:买全部 + 填位 deploy,不选羁绊/不读价格(见 design.md Strategy 可插拔升级)。

    注:智能选角(识别角色→按羁绊/命途部署)依赖角色识别,见 char_id 思路;
    本 op 是 v1 naive 填位。待接进 app + 实机测试(需游戏到备战)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-备战单轮')

    # 出战按钮 center:screen_info「按钮-出战」(货币战争-备战);常量=screen_info 缺失兜底。
    BATTLE_FALLBACK: ClassVar[Point] = Point(1817, 749)

    @operation_node(name='买牌', is_start_node=True)
    def buy(self) -> OperationRoundResult:
        return self.round_by_op_result(BuyShopCards(self.ctx).execute())

    @node_from(from_name='买牌')
    @operation_node(name='部署')
    def deploy(self) -> OperationRoundResult:
        return self.round_by_op_result(DeployBench(self.ctx).execute())

    @node_from(from_name='部署')
    @operation_node(name='出战')
    def battle(self) -> OperationRoundResult:
        # 点出战 + verify transition(仍在备战→retry)。
        screen = self.last_screenshot
        if self.round_by_ocr(screen, '出战').is_success:
            _btn = area_center(self.ctx, '按钮-出战') or BattlePrepCycle.BATTLE_FALLBACK
            self.ctx.controller.click(_btn)
            time.sleep(1.0)  # 等出战→战斗过渡
            # verify:仍在备战(购买经验 visible)→ click 未落地 → retry(防假成功 prep-loop)
            if self.round_by_ocr(self.screenshot(), '购买经验').is_success:
                return self.round_retry('出战 click 未落地,重试', wait=1)
            return self.round_success(wait=3)
        return self.round_retry('找不到出战', wait=1)
