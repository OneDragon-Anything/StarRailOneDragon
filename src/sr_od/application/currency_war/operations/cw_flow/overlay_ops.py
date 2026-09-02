"""货币战争 备战触发型 overlay 族 op(W971 P3a;06-overlays §4 统一模式)。

七 overlay 一 op:盛会之星 / 列车同行 / 武装箱 / 祈愿试炼 / 骇入策划 / 命运卜者 / 星徽秘典。
统一模式(W971 06-overlays §4):识别 overlay(id_mark)→ 待选项识别 + 决策 + 点选确认
→ 完成承诺 = 固定 1.0s(CW_OVERLAY_SETTLE_S,DD-011 形态①)交回循环。

现役 handler 的完整逻辑(读法 + 策略函数 decide_megastar / core 兜底 / 执行器默认 /
naive / decide_planner)本批不改:六 op 薄封装委托现役 handler op,handler 退役与
「点选 + 确认」原子两步化归 P3b。例外:星徽秘典(BookcardOp)现役逻辑内联在
battle_loop 0i 分支(无独立 op),本批按其现役读法直写(决策待定 = 沿用
decide_star_tome + fallback 卡1,策略归口批 B 定)。
"""
import time
from collections.abc import Callable
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
from sr_od.application.currency_war.operations.handlers.handle_bookcard import (
    HandleBookcard,  # noqa: F401  专家邀请函链现状参照(七 overlay 外,不封装)
)
from sr_od.application.currency_war.operations.handlers.handle_fortune_picker import (
    HandleFortunePicker,
)
from sr_od.application.currency_war.operations.handlers.handle_planner_event import (
    HandlePlannerEvent,
)
from sr_od.application.currency_war.operations.handlers.handle_select_partner import (
    HandleSelectPartner,
)
from sr_od.application.currency_war.operations.handlers.handle_supply_box import (
    HandleSupplyBox,
)
from sr_od.application.currency_war.operations.handlers.handle_wish_trial import (
    HandleWishTrial,
)
from sr_od.application.currency_war.operations.run_nodes.run_megastar_node import (
    RunMegastarNode,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 现役 handler 工厂(ctx → handler op)。
HandlerFactory = Callable[[SrContext], SrOperation]


class CwOverlayOp(SrOperation):
    """overlay 族基类:id_mark 入口识别 → 委托现役 handler → 固定 1.0s 交回。

    入口识别不中 → round_fail(交上层循环/编排重新分流,不在错屏盲跑 handler);
    handler 失败原样上抛其结果(其内部 retry 预算已兜底);成功后固定时长等待
    (overlay 关闭动画)交回。
    """

    #: op 显示名(子类必设,构造参数化,基类不做无参默认)。
    LABEL: ClassVar[str]
    #: overlay 画面名 / 入口 id_mark area(screen_info 单一源)。
    SCREEN_NAME: ClassVar[str]
    MARK_AREA: ClassVar[str]
    #: 现役 handler 工厂(薄封装委托;P3b handler 退役后内联原子两步)。
    HANDLER_FACTORY: ClassVar[HandlerFactory]

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=f'货币战争-{self.LABEL}')

    @operation_node(name='overlay处理', is_start_node=True, node_max_retry_times=3)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            return self.round_fail(f'非{self.LABEL}画面')
        _handler = self.HANDLER_FACTORY(self.ctx)
        _result = self.round_by_op_result(_handler.execute())
        if not _result.is_success:
            return _result
        # 完成承诺 = DD-011 形态①固定时长(overlay 关闭动画窗,06-overlays §4)。
        return self.round_success(f'{self.LABEL}处理完成', wait=CW_OVERLAY_SETTLE_S)


class MegastarOp(CwOverlayOp):
    """盛会之星:候选立绘 → decide_megastar(comp 引擎 × 乘区绑定)选巨星 + 确认。"""

    LABEL: ClassVar[str] = '盛会之星'
    SCREEN_NAME: ClassVar[str] = '货币战争-盛会之星'
    MARK_AREA: ClassVar[str] = '标识-盛会之星'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = RunMegastarNode


class PartnerOp(CwOverlayOp):
    """列车同行:SIFT 立绘识别候选真身 → core/build_around 命中兜底(decide_partner)。"""

    LABEL: ClassVar[str] = '列车同行'
    SCREEN_NAME: ClassVar[str] = '货币战争-列车同行'
    MARK_AREA: ClassVar[str] = '标识-选择伙伴'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = HandleSelectPartner


class ArmoryBoxOp(CwOverlayOp):
    """武装箱选卡:装备卡卡面 → 执行器默认(key_equips → 材料通用性)点卡(选中即确认)。"""

    LABEL: ClassVar[str] = '武装箱选卡'
    SCREEN_NAME: ClassVar[str] = '货币战争-备战-武装箱选择'
    MARK_AREA: ClassVar[str] = '标识-请选择'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = HandleSupplyBox


class WishTrialOp(CwOverlayOp):
    """祈愿试炼:候选卡 objective → naive/decide_wish_trial 首张兜底 + 确认。"""

    LABEL: ClassVar[str] = '祈愿试炼'
    SCREEN_NAME: ClassVar[str] = '货币战争-祈愿试炼'
    MARK_AREA: ClassVar[str] = '标识-祈愿试炼'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = HandleWishTrial


class PlannerEventOp(CwOverlayOp):
    """骇入策划(银狼「我来当策划」):两选项 OCR → decide_planner(升费优先)。"""

    LABEL: ClassVar[str] = '策划事件'
    SCREEN_NAME: ClassVar[str] = '货币战争-骇入策划'
    MARK_AREA: ClassVar[str] = '标识-我来当策划'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = HandlePlannerEvent


class FortunePickerOp(CwOverlayOp):
    """命运卜者强化:三强化卡 → 执行器文本规则(战力关键词)选卡 + 确认。"""

    LABEL: ClassVar[str] = '命运卜者强化'
    SCREEN_NAME: ClassVar[str] = '货币战争-命运卜者强化'
    MARK_AREA: ClassVar[str] = '标识-命运卜者'
    HANDLER_FACTORY: ClassVar[HandlerFactory] = HandleFortunePicker


class BookcardOp(SrOperation):
    """星徽秘典四选一:OCR 卡名 → decide_star_tome 选卡(点卡即选,弹窗自关)。

    现役逻辑内联在 battle_loop 0i 分支(无独立 handler op),本批按现役读法直写:
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


#: 06-overlays §4 表序的七 op 全集(P3b 接线按画面分发消费)。
OVERLAY_OPS: tuple[type[SrOperation], ...] = (
    MegastarOp, PartnerOp, ArmoryBoxOp, WishTrialOp,
    PlannerEventOp, FortunePickerOp, BookcardOp,
)
