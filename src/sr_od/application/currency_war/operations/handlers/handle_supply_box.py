# 未验证(2026-08-14 新建;机制 live 验过(交互链实测),op 流程待实机跑验)

"""货币战争 补给箱开箱 op(奖励球收取链路中段;2026-08-14 首见机制)。

补给箱 = 奖励球(晶矿)开启掉落,落备战席占 1 槽(read_supply_boxes TM 识别)。本 op 开箱:
点箱槽'开启'文字区(箱 icon 下方)→ 弹'<档位>武装箱'装备 4 选 1 overlay(``货币战争-备战-武装箱选择``,
2026-08-14 建档)→ OCR 4 卡名 → 按 key_equips/合成材料通用性选卡 → 点卡=选中即确认(单步)
→ overlay 关 + 装备入 owned + 箱槽腾空。

为何要开箱:① 奖励球在'备战席满时点不动'(球可能给角色/箱都占席)→ 先开箱腾席才能继续收球;
② 箱内装备本身有价值(简易合成组件)。

选卡策略(v1):OCR 卡名行 → 优先 target_comp.key_equips 命中;否则按合成材料通用性
(配方数多的组件:生命之花 7 配方/轮滑鞋 6/光能电池 6);都读不到 fallback 第 1 张。
点卡后验 overlay 关(武装箱 消失;同 _overlay_confirm'点了≠成了')。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_identity_obs import read_supply_boxes
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _material_value(name: str) -> int:
    """合成材料通用性(v1 静态表:进阶配方引用数;数据源 docs/game/currency_war/data/equipment.md 合成公式)。"""
    table = {
        '生命之花': 7, '轮滑鞋': 6, '光能电池': 6, '以太钻头': 5, '折叠小刀': 5,
        '量产型装甲': 5, '和平手枪': 4, '幸运星': 3,
    }
    return table.get(name, 0)


class HandleSupplyBox(SrOperation):
    """开补给箱:点箱槽「开启」→ 武装箱 4 选 1 → 按策略点卡 → 验 overlay 关。"""

    BOX_SCREEN: ClassVar[str] = '货币战争-备战-武装箱选择'
    # 「开启」文字区 = 箱 icon 下方;槽 center y + 此偏移(2026-08-14 实测 (565,952) 命中,槽center(563,911)→dy≈41)
    OPEN_TEXT_DY: ClassVar[int] = 41

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-补给箱开箱')

    @operation_node(name='补给箱开箱', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        boxes = read_supply_boxes(self.ctx, screen)
        if not boxes:
            return self.round_success('无补给箱(无需开箱)')
        _slot, box_center = boxes[0]
        open_point = Point(box_center.x, box_center.y + HandleSupplyBox.OPEN_TEXT_DY)
        log.info(f'[cw-box] 开箱:槽{_slot} 箱({box_center.x},{box_center.y}) → 点开启({open_point.x},{open_point.y})')
        # bug#1 缓解(mouse_move 先,同 safe_click;自写因还要验弹层)
        self.ctx.controller.mouse_move(open_point)
        self.ctx.controller.click(open_point)
        time.sleep(1.5)

        # 验武装箱 overlay 弹出(标识-请选择;没弹 = 点击落空/箱已被开 → retry 重读箱)
        overlay = self.screenshot()
        if not self.round_by_find_area(overlay, HandleSupplyBox.BOX_SCREEN, '标识-请选择').is_success:
            log.info('[cw-box] 武装箱 overlay 未弹 → retry(重读箱位置)')
            return self.round_retry(wait=1)

        # OCR 4 卡名(区域-卡名行)→ 选卡 → 点卡
        overlay = self.screenshot()
        from sr_od.application.currency_war.cw_obs_core import _area_rect, _ocr
        rect = _area_rect(self.ctx, '区域-卡名行', HandleSupplyBox.BOX_SCREEN)
        names: list[tuple[str, int]] = []
        if rect is not None:
            for r in _ocr(self.ctx, overlay, rect):
                if 2 <= len(r.data) <= 8:
                    names.append((r.data, r.center.x))
        names.sort(key=lambda t: t[1])
        chosen = self._pick_card([n for n, _ in names])
        if chosen is not None:
            xs = [x for n, x in names if n == chosen] or [names[0][1]]
            choose_x = xs[0]
        elif names:
            chosen, choose_x = names[0][0], names[0][1]   # fallback 第1卡
        else:
            chosen, choose_x = '(no-ocr)', 620   # 区域左端中心兜底
        log.info(f'[cw-box] 卡={[n for n, _ in names]} 选={chosen}@x={choose_x}')

        # 点卡选中即确认(实测单步);点卡身(卡名下方一点,避「查看详情」)
        card_point = Point(choose_x, 290)
        self.ctx.controller.mouse_move(card_point)
        self.ctx.controller.click(card_point)
        time.sleep(1.5)
        # 验 overlay 关(武装箱 消失 = 开箱完成 + 箱槽腾空)
        if self.round_by_ocr(self.screenshot(), '武装箱', lcs_percent=0.5).is_success:
            log.info('[cw-box] 选卡后 overlay 仍在 → retry')
            return self.round_retry(wait=1)
        log.info(f'[cw-box] 开箱完成({chosen}) → 箱槽腾空')
        return self.round_success(wait=1.5)

    def _pick_card(self, names: list[str]) -> str | None:
        """选卡:target_comp.key_equips 命中优先 → 材料通用性最高 → None(调用方兜底第1卡)。"""
        if not names:
            return None
        match = self.ctx.cw_match
        if match is not None and match.session.target_comp is not None:
            key_equips = set(match.session.target_comp.key_equips or [])
            for n in names:
                if n in key_equips:
                    return n
        return max(names, key=_material_value, default=None)
