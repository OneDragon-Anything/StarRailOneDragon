# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.application.currency_war.operations.handlers.handle_reward_sphere import (
    CollectRewardSpheres,
)
from sr_od.application.currency_war.operations.prep.deploy_bench import DeployBench
from sr_od.application.currency_war.operations.prep.equip_all import EquipAll
from sr_od.application.currency_war.operations.prep.shop import BuyShopCards
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class BattlePrepCycle(SrOperation):
    """货币战争 备战单轮自动化:买牌 → 部署 → 装备 → 出战。

    把四个子 op 串成单轮:``BuyShopCards``(开商店 → ``cw_decisions.plan`` 驱动买卡/升等级/刷新)→
    ``DeployBench``(SIFT 身份 + 策略驱动部署 target 优先)→ ``EquipAll``(read_equips owned → 过滤工具 →
    drag 穿戴类 → 空槽,P0-2 占位检测)→ 点「出战」进自动战斗。

    注:DeployBench 已接 SIFT 身份(D-8 立绘库)+ 策略驱动部署(D-7 CV 确定性 + D-10 卖 off-target
    + D-12 观测回路纠 tracking 漂),非 v1 naive 填位。EquipAll 接入 cycle(D-77:supply 装备自动穿,
    无穿戴 no-op;P0-2 占位 D-58 + 假阳修 D-62)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-备战单轮')

    # 出战按钮 center:screen_info「按钮-出战」(货币战争-备战);常量=screen_info 缺失兜底。
    BATTLE_FALLBACK: ClassVar[Point] = Point(1817, 749)

    @operation_node(name='收球', is_start_node=True)
    def collect(self) -> OperationRoundResult:
        """收奖励球(B6;通关奖励节点后的面板球 + 备战席补给箱开箱)。无球无箱时 no-op 快速过。"""
        log.info('[cw-prep] 备战单轮 ⓪ 收球(CollectRewardSpheres:开箱+点球,无球 no-op)')
        return self.round_by_op_result(CollectRewardSpheres(self.ctx).execute())

    @node_from(from_name='收球')
    @operation_node(name='买牌')
    def buy(self) -> OperationRoundResult:
        log.info('[cw-prep] 备战单轮 ① 买牌(BuyShopCards)')
        # 识别核对/节点标定钩子已随 P1 挂载切换搬入 PrepDirector(环入口对账 + _probe_node_type;
        # doc 15 §7 L1)。本类保留为 P3 前回退路径,不再重复采集。
        return self.round_by_op_result(BuyShopCards(self.ctx).execute())

    @node_from(from_name='买牌')
    @operation_node(name='部署')
    def deploy(self) -> OperationRoundResult:
        # 且每轮 +12s 拖慢)。clean op 代码留(clean_offtarget.py)待 late-game(target 充足)重接。
        log.info('[cw-prep] 备战单轮 ② 部署(DeployBench)')
        return self.round_by_op_result(DeployBench(self.ctx).execute())

    @node_from(from_name='部署')
    @operation_node(name='装备')
    def equip(self) -> OperationRoundResult:
        log.info('[cw-prep] 备战单轮 ③ 装备(EquipAll)')
        _r = self.round_by_op_result(EquipAll(self.ctx).execute())
        self._verify_equipped()   # [装备核对钩子·临时] EquipAll 后 read_row_equipped → log(对比 EquipAll 意图核装备识别)
        return _r

    def _verify_equipped(self) -> None:
        """[装备核对钩子·临时] EquipAll(drag 穿戴 / 触发合成)后 read_row_equipped → log 已穿装备。

        对比 EquipAll 意图(拖了哪些装备到哪些槽):若拖了但 read 没读到 / 合成结果没识别 → 装备识别(reader)错。
        采:截图(详情面板关后,clean 帧)+ log ``[cw-hook][equip]``。仅 log read 结果(意图对比离线 / 人眼),
        不阻塞备战。核完装备 reader 删本方法 + equip 调用(CLAUDE.md「两种钩子」)。
        """
        try:
            from sr_od.application.currency_war.cw_equipment import (
                ensure_equip_tm_templates,
            )
            from sr_od.application.currency_war.cw_identity_obs import read_row_equipped
            _grays = ensure_equip_tm_templates(self.ctx)
            if _grays is None:
                return
            _scr = self.screenshot()
            _fe = read_row_equipped(self.ctx, _scr, _grays, '前排', 4)
            _be = read_row_equipped(self.ctx, _scr, _grays, '后排', 6)
            log.info(f'[cw-hook][equip] read 已穿装备: front={_fe} back={_be}')
        except Exception as e:  # noqa: BLE001  live 验证 best-effort,失败不阻塞备战
            log.info(f'[cw-hook][equip] skip:{e}')

    @node_from(from_name='装备')
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
            log.info(f'[cw-prep] 备战单轮 ④ 出战 click @({_btn.x},{_btn.y})')
            # verify transition(D-70:轮询等转移,非 1.0s 单次负复核 —— transition 慢时误判"仍在备战"报败)。
            # 出战 → 战斗(deploy=cap,备战标识消失)/ 未达上限警告(deploy<cap,点确认让战斗开)。
            for _ in range(6):  # 6 × 0.5s = 3s 轮询窗口
                time.sleep(0.5)
                scr = self.screenshot()
                # 未达上限警告(deploy<cap)→ 点确认(让战斗开;确认 btn center ~1159,653)
                if self.round_by_find_area(scr, '货币战争-未达上限警告', '标识-未达上限警告').is_success:
                    log.info('[cw-prep] 出战 → 未达上限警告(deploy<cap)→ 确认')
                    _confirm = area_center(self.ctx, '按钮-确认', '货币战争-未达上限警告') or Point(1159, 653)
                    self.ctx.controller.click(_confirm)
                    time.sleep(1.0)
                    continue
                # 转移成功:备战标识(购买经验)消失 → 战斗/结算
                if not self.round_by_find_area(scr, '货币战争-备战', '备战标识-购买经验').is_success:
                    log.info('[cw-prep] 出战成功 → 过渡到战斗/结算')
                    return self.round_success(wait=3)
            log.warning('[cw-prep] ⚠️ 出战后 3s 仍在备战(click 未落地 / bug#1?),retry')
            self.save_screenshot()  # 诊断存证(insights 出战 click 条):看 retry 时屏上 bug#1 drag(无 overlay) vs overlay 挡出战(有 dialog/事件) vs 坐标偏
            return self.round_retry('出战 click 未落地,重试', wait=1)
        log.info('[cw-prep] 找不到出战按钮,retry')
        return self.round_retry('找不到出战', wait=1)
