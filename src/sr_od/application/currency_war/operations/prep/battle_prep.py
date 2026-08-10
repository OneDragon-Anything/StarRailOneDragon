# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.application.currency_war.operations.prep.deploy_bench import DeployBench
from sr_od.application.currency_war.operations.prep.shop import BuyShopCards
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class BattlePrepCycle(SrOperation):
    """货币战争 备战单轮自动化:买牌 → 部署 → 出战。

    把三个子 op 串成单轮:``BuyShopCards``(开商店 → ``cw_decisions.plan`` 驱动买卡/升等级/刷新)→
    ``DeployBench``(SIFT 身份 + 策略驱动部署 target 优先)→ 点「出战」进自动战斗。

    注:DeployBench 已接 SIFT 身份(D-8 立绘库)+ 策略驱动部署(D-7 CV 确定性 + D-10 卖 off-target
    + D-12 观测回路纠 tracking 漂),非 v1 naive 填位。装备穿戴待 equip_all 重建(D-27/D-28 cw_equip SIFT)。
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
        # 且每轮 +12s 拖慢)。clean op 代码留(clean_offtarget.py)待 late-game(target 充足)重接。
        log.info('[cw-prep] 备战单轮 ② 部署(DeployBench)')
        return self.round_by_op_result(DeployBench(self.ctx).execute())

    @node_from(from_name='部署')
    @operation_node(name='出战')
    def battle(self) -> OperationRoundResult:
        # 点出战 + verify transition(仍在备战→retry)。
        screen = self.last_screenshot
        if self.round_by_find_area(screen, '货币战争-备战', '按钮-出战').is_success:
            _btn = area_center(self.ctx, '按钮-出战') or BattlePrepCycle.BATTLE_FALLBACK
            # click 落在移动中 → 被游戏判拖拽落空。2026-08-06 r9 实跑:出战 click ×4 未落地(手动 click 即开战)
            # → bug#1 间歇连发(此前 r1-8 出战正常)。同 buy_store_item 的 mouse_move 缓解。verify 仍在(下行)。
            self.ctx.controller.mouse_move(_btn)
            self.ctx.controller.click(_btn)
            log.info(f'[cw-prep] 备战单轮 ③ 出战 click @({_btn.x},{_btn.y})')
            # verify transition(D-70:轮询等转移,非 1.0s 单次负复核 —— transition 慢时误判"仍在备战"报败)。
            # 出战 → 战斗(deploy=cap,备战标识消失)/ 未达上限警告(deploy<cap,点确认让战斗开)。
            for _ in range(6):  # 6 × 0.5s = 3s 轮询窗口
                time.sleep(0.5)
                scr = self.screenshot()
                # 未达上限警告(deploy<cap)→ 点确认(让战斗开;确认 btn center ~1159,653)
                if self.round_by_find_area(scr, '货币战争-未达上限警告', '标识-未达上限警告').is_success:
                    log.info('[cw-prep] 出战 → 未达上限警告(deploy<cap)→ 确认')
                    self.ctx.controller.click(Point(1159, 653))
                    time.sleep(1.0)
                    continue
                # 转移成功:备战标识(购买经验)消失 → 战斗/结算
                if not self.round_by_find_area(scr, '货币战争-备战', '备战标识-购买经验').is_success:
                    log.info('[cw-prep] 出战成功 → 过渡到战斗/结算')
                    return self.round_success(wait=3)
            log.warning('[cw-prep] ⚠️ 出战后 3s 仍在备战(click 未落地 / bug#1?),retry')
            return self.round_retry('出战 click 未落地,重试', wait=1)
        log.info('[cw-prep] 找不到出战按钮,retry')
        return self.round_retry('找不到出战', wait=1)
