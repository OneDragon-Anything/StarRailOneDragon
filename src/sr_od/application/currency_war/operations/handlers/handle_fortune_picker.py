# live-verified 2026-08-21(局32 P2r2 卡死 30min 后建;交互实锤:点卡下半部
# y≈480 选中,确认 (1491,600) 消费成功——同策划事件坐标族)。

"""货币战争 命运卜者「强化效果三选一」overlay 处理 op(r115)。

事件族:策划系 overlay(标题=事件名+「请选择N个强化效果」+N 卡+Q 详情+确认)。
银狼策划(r103)同族;命运卜者强化在 P2 出现(黑天鹅/奥迹系强化)。
布局(局32 实拍):标题 y~58-94 / 指令 y~122 / 卡文字 y~296-405 / 三卡
x≈510/900/1290 / 确认 (1441-1543,584-615)。

识别:「请选择」+「强化效果」关键词(id_mark 由 screen_info 承担)。
策略:OCR 三卡文字 → decide_event 类打分(机制词缀向);v1 用
decide_planner 同款文本规则(奥迹/伤害=战力类,留白=保守)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleFortunePicker(SrOperation):
    """命运卜者强化三选一:OCR 卡文字 → 文本策略选卡 → 确认。"""

    # 三卡卡身(选中点击点=卡下半部,避详情按钮 y~430-462;同策划事件教训)
    CARD_XS: ClassVar[tuple[int, ...]] = (510, 900, 1290)
    CARD_Y: ClassVar[int] = 480
    TEXT_Y_LO: ClassVar[int] = 290
    TEXT_Y_HI: ClassVar[int] = 410
    CONFIRM: ClassVar[Point] = Point(1491, 600)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-命运卜者强化')

    def _read_cards(self, screen) -> list[str]:
        """OCR 三卡文字 → x 近邻分流。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        buckets: dict[int, list[str]] = {x: [] for x in self.CARD_XS}
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            cx = mrl.max.center.x
            if not (self.TEXT_Y_LO <= cy <= self.TEXT_Y_HI):
                continue
            nearest = min(self.CARD_XS, key=lambda x: abs(x - cx))
            if abs(nearest - cx) < 190:
                buckets[nearest].append(text)
        return [' '.join(buckets[x]) for x in self.CARD_XS]

    @operation_node(name='命运卜者强化', is_start_node=True, node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        screen = self.screenshot()
        texts = self._read_cards(screen)
        # 文本策略 v1:战力关键词优先(伤害/强度/提高),无匹配选第一张
        best_i, best_s = 0, -1.0
        for i, t in enumerate(texts):
            s = 0.0
            for kw, w in (('伤害倍率', 3.0), ('强度提高', 2.0), ('层数提高', 2.0),
                          ('伤害', 1.0), ('提高', 0.5)):
                if kw in t:
                    s += w
            if s > best_s:
                best_i, best_s = i, s
        target = Point(self.CARD_XS[best_i], self.CARD_Y)
        log.info('[cw][fortune] 命运卜者强化:卡=%s → 选卡%d(%s)',
                 [t[:12] for t in texts], best_i + 1, texts[best_i][:20] or 'OCR空')
        # r315(等画面审查 P0②:全无出口验证,失败分支死码):
        # 选卡=safe_click(bug#1 缓解);确认+验关统一走
        # confirm_and_verify(入口关键词=命运卜者;确认落空→
        # overlay 不关→round_retry 计预算兜底,不再无限重点)
        from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
            confirm_and_verify,
            safe_click,
        )
        safe_click(self, target, tag='cw-fortune')
        time.sleep(1.2)
        return confirm_and_verify(
            self, confirm_point=self.CONFIRM,
            entry_keyword='命运卜者', tag='cw-fortune')
