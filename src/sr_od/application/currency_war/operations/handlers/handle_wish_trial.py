# 已接入 battle_loop:255(2026-08-08 实测:bot 卡此 overlay 68min 后接入检测 + HandleWishTrial 点卡+确认+验关;出战不再被 overlay 卡,D-87~89 闭环)。
# r104(2026-08-20):选卡接入策略模块 decide_wish_trial(用户定调「所有 overlay 选择都接策略」)——
# OCR 各卡 objective 文字 → 策略打分(金币/阵营相关/操作向)→ 点选中卡。OCR 失败 fallback 第 1 张。

"""货币战争 祈愿试炼 overlay 处理 op(事件长尾:2026-08-08 实跑发现,bot 卡此 overlay 68min)。

「祈愿试炼」= **节点级 quest 选择 overlay**(出现在特定节点前,如「再临仪式-二」「遭遇战」):
选 1 个试炼 → 该节点/本局完成 objective(如「累计刷新10次」「进行一场难度3+遭遇节点战斗」)
→ 得奖励(金币 / 阵营星徽)。overlay 叠在备战上,**挡备战分支** → 必须在备战分支(1)前检测处理。

交互(2026-08-08 实测):ESC **不关**;点试炼卡身 → 选中(金色边框 + 确认选择亮)→ 点
「确认选择」→ overlay 关回备战。候选卡数/内容随节点变(实测 2 张)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleWishTrial(SrOperation):
    """祈愿试炼 overlay:OCR objective → decide_wish_trial 策略选卡 → 确认 → 验关。"""

    CARD_Y: ClassVar[int] = 340
    # 卡 x 中心(实测左卡 660 命中;多卡间距 ~300;读 objective 后近邻分流)
    CARD_XS: ClassVar[tuple[int, ...]] = (660, 960, 1260)
    TEXT_Y_LO: ClassVar[int] = 250
    TEXT_Y_HI: ClassVar[int] = 400
    FIRST_CARD: ClassVar[Point] = Point(660, 340)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, op_name='货币战争-祈愿试炼')

    def _read_objectives(self, screen) -> list[str]:
        """OCR 各卡 objective 文字 → 按 x 近邻分流到卡槽。"""
        ocr = self.ctx.ocr_service.get_ocr_result_list(screen, crop_first=False)
        buckets: dict[int, list[str]] = {x: [] for x in self.CARD_XS}
        for o in ocr:
            t = (o.data or '').strip()
            if not t or not (self.TEXT_Y_LO <= o.y + o.h // 2 <= self.TEXT_Y_HI):
                continue
            cx = o.x + o.w // 2
            nearest = min(self.CARD_XS, key=lambda x: abs(x - cx))
            if abs(nearest - cx) < 160:
                buckets[nearest].append(t)
        return [' '.join(buckets[x]) for x in self.CARD_XS]

    @operation_node(name='祈愿试炼', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼').is_success:
            return self.round_fail('非祈愿试炼屏')
        # 策略决策(r104):OCR objective → decide_wish_trial → 对应卡
        target = HandleWishTrial.FIRST_CARD
        pick_desc = 'fallback第1张'
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            try:
                objs = self._read_objectives(screen)
                from sr_od.application.currency_war.cw_state import GameState
                _st = _match.session.last_state or GameState()
                idx = _match.strategy.decide_wish_trial(
                    objs, _st, _match.session, getattr(_match, 'config', None))
                if 0 <= idx < len(self.CARD_XS):
                    target = Point(self.CARD_XS[idx], HandleWishTrial.CARD_Y)
                    pick_desc = f'卡{idx + 1}({objs[idx][:20] or "OCR空"})'
            except Exception as e:   # noqa: BLE001  策略失败 fallback 第1张
                log.warning('[cw-wish] 策略决策异常(fallback 第1张): %s', e)
        log.info('[cw-wish] 祈愿决策: %s → 点 (%s,%s)', pick_desc, target.x, target.y)
        # 点卡选中(bug#1 缓解:mouse_move 先,零移动落 click,防 before_screenshot 移光标)。
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(1.0)
        # 确认选择(本屏 area 位置;祈愿试炼 独有检测在前,不与 partner/megastar 的「确认选择」撞)。
        self.round_by_find_and_click_area(
            self.screenshot(), '货币战争-祈愿试炼', '按钮-确认选择', success_wait=1.5)
        # 验 overlay 关(标识-祈愿试炼 消失 = 推进);没关 → retry(confirm 未落地,bug#1 / 选中未生效)。
        if self.round_by_find_area(self.screenshot(), '货币战争-祈愿试炼', '标识-祈愿试炼').is_success:
            log.info('[cw-wish] 确认后 overlay 仍在 → round_retry')
            return self.round_retry(wait=1)
        log.info('[cw-wish] 祈愿试炼 overlay 关 → 回备战')
        return self.round_success(wait=2)
