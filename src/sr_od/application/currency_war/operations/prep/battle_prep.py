import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
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
        # 点出战。⚠️ bug#1:框架 before_screenshot 移鼠标到角落 → 紧接 controller.click(从角落到目标)
        # 被游戏判拖拽 → click 落空。2026-08-04 实测:出战 click CONSISTENTLY 被吞(手动 click_game 行,
        # 因无 before_screenshot)。
        # 根因修复:**先 mouse_move 到目标(mouse_move 是纯移动不触发 drag 判断)→ 再 click(鼠标已在
        # 目标 → 零移动 → 不被判 drag → 必落)**。+ verify transition(仍在备战→retry)。
        screen = self.last_screenshot
        if self.round_by_ocr(screen, '出战').is_success:
            self.ctx.controller.active_window()
            time.sleep(0.3)
            self.ctx.controller.mouse_move(Point(1817, 749))  # 先移鼠标到出战(纯移动,不触发 drag)
            time.sleep(0.3)
            self.ctx.controller.click(Point(1817, 749))  # click(鼠标已到位 → 零移动 → 不被吞)
            time.sleep(1.0)  # 等出战→战斗过渡
            # verify:仍在备战(购买经验 visible)→ click 未落地 → retry(防假成功 prep-loop)
            if self.round_by_ocr(self.screenshot(), '购买经验').is_success:
                return self.round_retry('出战 click 未落地,重试', wait=1)
            return self.round_success(wait=3)
        return self.round_retry('找不到出战', wait=1)
