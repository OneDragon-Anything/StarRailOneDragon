# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 投资策略 3 选 1 op(从主循环拆出)。

OCR 3 张投资策略卡名 → ``cw_decisions.decide_event`` 按事件白名单打分 → 点**最优**卡
+ 确认。替代原"盲点中卡"(无策略)。

卡名按行过滤(2026-08-04 snap 实测):标题「请选择投资策略」顶(y≈98)、卡名中(y≈490,
center)、描述下(y≈520+)、「刷新次数1」底(y≈841)、「确认」底(y≈983);取 y≈490 行
短文本(2-8 字)即 3 张卡名,按 center-x 排序左→右。

点击 mechanics(2026-08-04 实测):点卡名(y≈474)**不选中**(疑似开详情,bot 点名 540+ 次从没
选中 → 确认灰 → 卡死 18min)→ 点**描述区**(CARD_CLICK_Y=545)才选中(同 invest_env:name 不
选中、描述区选中)。选中 → 确认。decide_event 仅用 state.board,投资策略 overlay 时 board 不可
读 → 空 board stub。

CARD_CLICK_Y + 确认坐标进 screen_info(``currency_war_invest_strategy``):``区域-卡牌描述行``
+ ``按钮-确认``,task#20 已完成;本 op 经 ``cw_observation.area_center`` 读,缺失才用兜底常量。
"""
import time
import types
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_decisions import decide_event
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
    confirm_and_verify,
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleInvestStrategy(SrOperation):
    """投资策略 3 选 1:OCR 卡名 → decide_event 打分 → 点最优卡 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-投资策略'   # screen_info 画面(currency_war_invest_strategy.yml)
    # 卡选中点击 Y:screen_info「区域-卡名行」center.y(=卡名选中行);常量=兜底。
    # V4.4 实测(2026-08-05,↺ 推翻 I16「卡底 820 选中」):**点卡名(y≈474)选中**(白边 + 确认亮)。
    # 实机点验:点中产阶级卡名(461,474) → 白边选中 → 点确认 → 推进备战 1-3(链路通)。
    # I16「卡底 820 才选中」错 —— 820 是刷新区/卡底,点没选中 → handle 点 820 不选中 → loop 反复卡死投资策略
    # (整局阻塞,实跑暴露)。旧 doc(2026-08-04「描述区 545 选中」/ I16「卡底 820」)均过时。
    CARD_CLICK_Y: ClassVar[int] = 474   # 兜底(卡名选中);首选 area_center('区域-卡名行')
    # 卡名行 center-y 过滤带(标题 y≈98 / 描述 y≈520+ / 刷新次数 y≈841 / 确认 y≈983)
    NAME_CY_LO: ClassVar[int] = 465
    NAME_CY_HI: ClassVar[int] = 505
    _EXCLUDE: ClassVar[set[str]] = {'请选择投资策略', '攻略', '返回备战界面', '图例', '确认', '刷新次数1'}
    # 确认按钮:screen_info「按钮-确认」center(task#20);常量=兜底。
    CONFIRM: ClassVar[Point] = Point(978, 983)   # 兜底;首选 area_center('按钮-确认')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资策略')

    def _read_options(self, screen) -> list[tuple[str, int, int]]:
        """OCR 3 张卡的 ``(名字, center-x, center-y)``,按卡名行 y 过滤 + 左→右排序。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        opts: list[tuple[str, int, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (HandleInvestStrategy.NAME_CY_LO <= cy <= HandleInvestStrategy.NAME_CY_HI
                    and 2 <= len(text) <= 8 and text not in HandleInvestStrategy._EXCLUDE):
                opts.append((text, mrl.max.center.x, cy))
        opts.sort(key=lambda t: t[1])
        return opts

    @operation_node(name='投资策略', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-投资策略', '标识-请选择投资策略').is_success:
            return self.round_fail('非投资策略屏')

        opts = self._read_options(screen)
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _x, _y in opts]
        # 不可读 → 传空 GameState(decide_event 只用 board 判 DoT 克制,空 board = 不惩罚,安全)。
        match = self.ctx.cw_match
        if names:
            if match is not None:
                pick = match.strategy.decide_invest('strategy', names, GameState(), match.session, config)
            else:
                pick = decide_event(names, config, types.SimpleNamespace(board={}))  # 防御:无 match(局外独立跑)
        else:
            pick = None
        if pick is not None and 0 <= pick.option_idx < len(opts):
            chosen, choose_x, choose_y = opts[pick.option_idx]
            reason = pick.reason
        elif opts:
            chosen, choose_x, choose_y, reason = opts[0][0], opts[0][1], opts[0][2], 'fallback(no-decision)'
        else:
            chosen, choose_x, choose_y, reason = '?', 920, 490, 'fallback(no-ocr)'
        log.info(f'[cw-strat] options={names} chose={chosen!r}@({choose_x},{choose_y}) reason={reason}')
        # 写入 session.active_strategies(原 bug:chosen 只点不存 → active_strategies 恒空 → 经济/难度判定静默失效,
        # 如 cw_decisions.L286 刷新减费策略判定、刷新费用减免都读不到已持有策略)。
        # 投资策略可多张(局中重复选)→ append;去重防重选同一张时重复入列。
        if match is not None and chosen != '?':
            if chosen not in match.session.active_strategies:
                match.session.active_strategies.append(chosen)

        # 点最优卡的**卡名**选中(Y 从 screen_info「区域-卡名行」center 读;缺失兜底 CARD_CLICK_Y=474)。
        # safe_click 带 bug#1 mouse_move 缓解(partner reset 根因同类)。
        _sel = area_center(self.ctx, '区域-卡名行', HandleInvestStrategy.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else HandleInvestStrategy.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        safe_click(self, target, tag='cw-strat')
        time.sleep(0.7)
        # 确认 + 验关(投资策略 消失 = overlay 关)。原「点了就 success」不验 → bug#1/卡未选中/隐藏多步 flat-loop
        # (partner reset 根因同类;write-operation「点了≠成了」;本 op docstring 已记「点名 540+ 次不选中→卡死 18min」)。
        # 确认 center 从 screen_info 读,缺失兜底。
        _confirm = area_center(self.ctx, '按钮-确认', HandleInvestStrategy.SCREEN_NAME) or HandleInvestStrategy.CONFIRM
        return confirm_and_verify(self, confirm_point=_confirm, entry_keyword='投资策略',
                                  tag='cw-strat')
