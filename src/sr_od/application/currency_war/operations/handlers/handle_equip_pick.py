# 实拍建档 2026-08-20 09:45(局37 r3;哨兵推送 2 分钟响应闭环)。
# 布局:标题"选择装备"(1048,22-53)/副题"请选择1个"(1050,65-89)/三卡
# x≈736/1027/1350 y≈253-283(卡名带)/每卡下方"查看详情"按钮(y≈307-335)。
# 交互(VLM+布局推断):单选,选中后出战按钮确认;无独立"确认选择"按钮
# (选择伙伴屏的 确认选择 区在这里不存在——正是误派发的根因)。

"""货币战争 选择装备三选一(r129):OCR 卡名 → 策略选卡 → 点卡。

误派发根因:选择伙伴屏的 标识-选择伙伴(文本「请选择1个」)在本屏
也命中(装备选择同文案)→ HandleSelectPartner 被误派发找不到确认按钮
→ 失败循环(哨兵 09:45 推送实证)。修:本屏建档(标识-选择装备 id_mark
优先)+ 本 handler + loop 分支在选择伙伴**之前**(双 id_mark:装备标题
+ 请选择1个都命中才算)。
策略:卡名 OCR → key_equips 命中(target/stash comp)+100 / 材料类次之
(与 decide_box_card 同语义,r104 家族)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleEquipPick(SrOperation):
    """选择装备三选一:OCR 卡名 → 策略选卡(点卡即选,出战按钮由主流程点)。"""

    CARD_XS: ClassVar[tuple[int, ...]] = (780, 1070, 1380)
    CARD_Y: ClassVar[int] = 280          # 卡名带中心(避开下方详情按钮 y≈310)
    TEXT_Y_LO: ClassVar[int] = 235
    TEXT_Y_HI: ClassVar[int] = 300

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-选择装备')

    def _read_cards(self, screen) -> list[str]:
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
            if abs(nearest - cx) < 160:
                buckets[nearest].append(text)
        return [' '.join(buckets[x]) for x in self.CARD_XS]

    @operation_node(name='选择装备', is_start_node=True, node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        screen = self.screenshot()
        texts = self._read_cards(screen)
        # 策略:key_equips 命中优先(与 decide_box_card 同语义)
        _match = getattr(self.ctx, 'cw_match', None)
        key_equips: list[str] = []
        if _match is not None and _match.session is not None:
            for comp in (getattr(_match.session, 'target_comp', None),
                         getattr(_match.session, 'stash_comp', None)):
                key_equips.extend(getattr(comp, 'key_equips', ()) or ())
        best_i, best_s = 0, -1.0
        for i, t in enumerate(texts):
            s = 0.0
            for ke in key_equips:
                if ke and ke in t:
                    s += 100.0
                    break
            if s <= 0 and any(kw in t for kw in ('伤害', '强度', '提高')):
                s = 1.0   # 泛用增益次之
            if s > best_s:
                best_i, best_s = i, s
        target = Point(self.CARD_XS[best_i], self.CARD_Y)
        log.info('[cw-equip-pick] 装备选择:卡=%s → 选卡%d(%s)',
                 [t[:10] for t in texts], best_i + 1, texts[best_i][:16] or 'OCR空')
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(1.2)
        # 单选即定(出战按钮由主流程处理);重读验证选中态/标题仍在则 retry
        screen2 = self.screenshot()
        ocr2 = self.ctx.ocr_service.get_ocr_result_map(
            image=screen2, rect=None, color_range=None, crop_first=False,
        )
        if any('请选择' in t for t in ocr2):
            return self.round_retry(wait=1, status='装备选择未生效,重试')
        return self.round_success(status=f'装备选择卡{best_i + 1}')
