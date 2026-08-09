import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.application.currency_war.operations.prep.deploy_bench import DeployBench
from sr_od.application.currency_war.operations.prep.equip_all import EquipAll
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
        log.info('[cw-prep] 备战单轮 ① 买牌(BuyShopCards)')
        return self.round_by_op_result(BuyShopCards(self.ctx).execute())

    @node_from(from_name='买牌')
    @operation_node(name='部署')
    def deploy(self) -> OperationRoundResult:
        # D-154:D-153 clean 解绑(fill-all deploy 下 moot —— 卖的 off-target 又被 re-deploy;
        # 且每轮 +12s 拖慢)。clean op 代码留(clean_offtarget.py)待 late-game(target 充足)重接。
        log.info('[cw-prep] 备战单轮 ② 部署(DeployBench)')
        return self.round_by_op_result(DeployBench(self.ctx).execute())

    @node_from(from_name='部署')
    @operation_node(name='装备')
    def equip(self) -> OperationRoundResult:
        # D-148/D-155:部署后→装备(drag 装备区 owned equip icon → 前排 char avatar y350)。
        # bot own equip 不装 = 执行 gap;EquipAll 解(panel 开/无 equip 时自跳过)。
        log.info('[cw-prep] 备战单轮 ③ 全员装备(EquipAll, D-148/D-155)')
        return self.round_by_op_result(EquipAll(self.ctx).execute())

    @node_from(from_name='装备')
    @operation_node(name='出战')
    def battle(self) -> OperationRoundResult:
        # 点出战 + verify transition(仍在备战→retry)。
        screen = self.last_screenshot
        if self.round_by_find_area(screen, '货币战争-备战', '按钮-出战').is_success:
            _btn = area_center(self.ctx, '按钮-出战') or BattlePrepCycle.BATTLE_FALLBACK
            # bug#1 缓解(D-62):click 前 mouse_move 到出战键(零移动),防 before_screenshot 移光标到角落 →
            # click 落在移动中 → 被游戏判拖拽落空。2026-08-06 r9 实跑:出战 click ×4 未落地(手动 click 即开战)
            # → bug#1 间歇连发(此前 r1-8 出战正常)。同 buy_store_item 的 mouse_move 缓解。verify 仍在(下行)。
            self.ctx.controller.mouse_move(_btn)
            self.ctx.controller.click(_btn)
            log.info(f'[cw-prep] 备战单轮 ③ 出战 click @({_btn.x},{_btn.y})')
            time.sleep(1.0)  # 等出战→战斗过渡
            # verify:仍在备战(购买经验 visible)→ click 未落地 → retry(防假成功 prep-loop)
            if self.round_by_find_area(self.screenshot(), '货币战争-备战', '备战标识-购买经验').is_success:
                log.warning('[cw-prep] ⚠️ 出战后仍在备战(click 未落地 / bug#1?),retry')
                return self.round_retry('出战 click 未落地,重试', wait=1)
            log.info('[cw-prep] 出战成功 → 自动战斗')
            return self.round_success(wait=3)
        log.info('[cw-prep] 找不到出战按钮,retry')
        return self.round_retry('找不到出战', wait=1)
