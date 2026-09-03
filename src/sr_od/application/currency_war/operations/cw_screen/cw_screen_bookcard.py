"""货币战争 星徽秘典四选一画面 op(原 overlay 族内联实现落位,NAMING §2 BookcardOp 行)。

OCR 卡名 → decide_star_tome 选卡(点卡即选,弹窗自关);入口 id_mark 校验 +
出口验真转移 + 完成承诺固定时长(06-overlays §4)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_flow.cw_flow_const import (
    CW_OVERLAY_SETTLE_S,
)
from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenBookcard(SrOperation):
    """星徽秘典四选一:OCR 卡名 → decide_star_tome 选卡(点卡即选,弹窗自关)。

    现役逻辑内联在 cw_loop 0i 分支(无独立 handler op),本批按现役读法直写:
    全屏 OCR 取「XX星徽」名 → 策略打分(target 阵营/board 已有/配方框架),
    无命中 fallback 卡1(06-overlays §4:决策待定,策略归口批 B 定)。
    点击坐标走 screen_info 星徽卡-1..4 area(OCR x 近邻匹配 area,不硬编码)。
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-星徽秘典弹窗'
    MARK_AREA: ClassVar[str] = '标识-星徽秘典'
    CARD_AREAS: ClassVar[tuple[str, ...]] = ('星徽卡-1', '星徽卡-2', '星徽卡-3', '星徽卡-4')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-星徽秘典')

    def _read_card_factions(self, screen) -> list[tuple[str, int]]:
        """全屏 OCR 取「XX星徽」卡名 → [(阵营名, x 中心)] 左→右(现役 0i 读法)。"""
        ocr = self.ctx.ocr_service.get_ocr_result_list(screen, crop_first=False)
        cards: list[tuple[str, int]] = []
        for o in ocr:
            t = (o.data or '').strip()
            if t.endswith('星徽') and len(t) > 2:
                cards.append((t[:-2], o.x + o.w // 2))
        cards.sort(key=lambda c: c[1])
        return cards

    def _card_point(self, idx: int, faction_x: int | None) -> Point | None:
        """卡身点击点 = 星徽卡-N area 中心;OCR x 已知时取 x 近邻 area(防 area 序与画面序错位)。"""
        centers: list[Point] = []
        for area in self.CARD_AREAS:
            pt = area_center(self.ctx, area, self.SCREEN_NAME)
            if pt is None:
                return None
            centers.append(pt)
        if faction_x is not None:
            idx = min(range(len(centers)),
                      key=lambda i: abs(centers[i].x - faction_x))
        return centers[idx]

    @operation_node(name='星徽秘典', is_start_node=True, node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            return self.round_fail('非星徽秘典画面')
        cards = self._read_card_factions(screen)
        idx, pick_name = 0, '(fallback卡1)'
        if cards:
            _match = getattr(self.ctx, 'cw_match', None)
            if _match is not None:
                from sr_od.application.currency_war.kernel.cw_state import GameState
                _st = _match.session.last_state or GameState()
                _decided = _match.strategy.decide_star_tome(
                    [c[0] for c in cards], _st, _match.session,
                    getattr(_match, 'config', None))
                if 0 <= _decided < len(cards):
                    idx, pick_name = _decided, cards[_decided][0]
        # 近邻匹配锚 = 选中卡的 OCR x(决策后取,防把候选首位当选中位)
        faction_x = cards[idx][1] if idx < len(cards) else None
        target = self._card_point(idx, faction_x)
        if target is None:
            return self.round_fail('星徽秘典缺「星徽卡-N」建档')
        log.info('[cw-flow-bookcard] 候选=%s → 选 %s @(%s,%s)',
                 [c[0] for c in cards] or 'OCR未读到', pick_name, target.x, target.y)
        safe_click(self, target, tag='cw-flow-bookcard')
        time.sleep(1.0)   # 点卡即选,弹窗自关(现役 0i 实测口径)
        # 出口验真转移:弹窗消失;仍在 = 选卡未生效,重试计预算。
        if self.round_by_find_area(
                self.screenshot(), self.SCREEN_NAME, self.MARK_AREA,
                crop_first=False).is_success:
            return self.round_retry('选卡后秘典弹窗仍在')
        return self.round_success('星徽秘典选卡完成', wait=CW_OVERLAY_SETTLE_S)

