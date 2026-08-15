"""货币战争 节点武装箱弹窗 op(「武装突入」类节点首见,2026-08-15 M19 停机建档)。

画面链(与备战补给箱同下游、不同入口):
1. ``货币战争-武装箱弹窗``(currency_war_armory_box_dialog,独立弹窗):标题「简易武装箱」
   + 说明「点击后开启…从四件简易装备中选择一件」。入口 = 节点推进中弹出(备战箱是奖励球
   掉落占席,M19 实锤两者并存于不同链路)。
2. 点箱图标(按钮-开箱点击,VLM grounding 2026-08-15)→ ``货币战争-备战-武装箱选择``
   四选一 overlay(2026-08-14 建档)→ 选卡(key_equips 优先,公用 pick_box_card)→ 点卡
   单步确认 → overlay 关。

选卡与验关逻辑同 HandleSupplyBox(点卡即确认/overlay 消失=完成),卡片坐标区域复用
「区域-卡名行」。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_obs_core import _area_rect, _ocr
from sr_od.application.currency_war.operations.handlers.handle_supply_box import (
    pick_box_card,
)
from sr_od.operations.sr_operation import SrOperation


class HandleArmoryBoxDialog(SrOperation):
    """节点武装箱弹窗:点开箱 → 四选一 → 选卡点卡 → 验 overlay 关。"""

    DIALOG_SCREEN: ClassVar[str] = '货币战争-武装箱弹窗'
    BOX_SCREEN: ClassVar[str] = '货币战争-备战-武装箱选择'
    # 四选一点卡 Y(卡名行下方,避「查看详情」;同 HandleSupplyBox 实测 290)
    CARD_CLICK_Y: ClassVar[int] = 290

    @operation_node(name='武装箱弹窗', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, HandleArmoryBoxDialog.DIALOG_SCREEN, '标识-简易武装箱', crop_first=False).is_success:
            return self.round_fail('非武装箱弹窗')

        # ① 点箱图标开箱(按钮-开箱点击;说明文本「点击后开启」)
        from sr_od.application.currency_war.cw_observation import area_center
        _pt = area_center(self.ctx, '按钮-开箱点击', HandleArmoryBoxDialog.DIALOG_SCREEN)
        if _pt is None:
            return self.round_fail('武装箱弹窗缺「按钮-开箱点击」坐标')
        log.info(f'[cw-armbox] 点开箱({_pt.x},{_pt.y})')
        self.ctx.controller.mouse_move(_pt)   # bug#1 缓解
        self.ctx.controller.click(_pt)
        time.sleep(1.5)

        # ② 验四选一 overlay 弹出(标识-请选择);没弹 = 点击落空 → retry 重点
        overlay = self.screenshot()
        if not self.round_by_find_area(
                overlay, HandleArmoryBoxDialog.BOX_SCREEN, '标识-请选择', crop_first=False).is_success:
            log.info('[cw-armbox] 四选一未弹 → retry')
            return self.round_retry(wait=1)

        # ③ OCR 4 卡名 → 选卡(公用:key_equips 优先)→ 点卡(单步确认)
        names: list[tuple[str, int]] = []
        rect = _area_rect(self.ctx, '区域-卡名行', HandleArmoryBoxDialog.BOX_SCREEN)
        if rect is not None:
            for r in _ocr(self.ctx, overlay, rect):
                if 2 <= len(r.data) <= 8:
                    names.append((r.data, r.center.x))
        names.sort(key=lambda t: t[1])
        chosen = pick_box_card(self.ctx, [n for n, _ in names])
        if chosen is not None:
            xs = [x for n, x in names if n == chosen] or [names[0][1]]
            choose_x = xs[0]
        elif names:
            chosen, choose_x = names[0][0], names[0][1]   # fallback 第 1 卡
        else:
            chosen, choose_x = '(no-ocr)', 620
        log.info(f'[cw-armbox] 卡={[n for n, _ in names]} 选={chosen}@x={choose_x}')
        card_point = Point(choose_x, HandleArmoryBoxDialog.CARD_CLICK_Y)
        self.ctx.controller.mouse_move(card_point)
        self.ctx.controller.click(card_point)
        time.sleep(1.5)

        # ④ 验 overlay 关(武装箱 消失 = 完成)
        if self.round_by_ocr(self.screenshot(), '武装箱', lcs_percent=0.5).is_success:
            log.info('[cw-armbox] 选卡后 overlay 仍在 → retry')
            return self.round_retry(wait=1)
        log.info(f'[cw-armbox] 开箱完成({chosen})')
        return self.round_success(wait=1.5)
