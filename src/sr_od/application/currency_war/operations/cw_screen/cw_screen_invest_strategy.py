
"""货币战争 投资策略 3 选 1 op(从主循环拆出)。

OCR 3 张投资策略卡名 → ``cw_events.decide_event`` 按事件白名单打分 → 点**最优**卡
+ 确认。替代原"盲点中卡"(无策略)。

卡名按行过滤(2026-08-04 snap 实测):标题「请选择投资策略」顶(y≈98)、卡名中(y≈490,
center)、描述下(y≈520+)、「刷新次数1」底(y≈841)、「确认」底(y≈983);取 y≈490 行
短文本(2-8 字)即 3 张卡名,按 center-x 排序左→右。

点击 mechanics(2026-08-04 实测):点卡名(y≈474)**不选中**(疑似开详情,bot 点名 540+ 次从没
选中 → 确认灰 → 卡死 18min)→ 点**描述区**(CARD_CLICK_Y=545)才选中(同 invest_env:name 不
选中、描述区选中)。选中 → 确认。decide_event 仅用 state.board,投资策略 overlay 时 board 不可
读 → 空 board stub。

CARD_CLICK_Y + 确认坐标进 screen_info(``currency_war_invest_strategy``):``区域-卡牌描述行``
+ ``按钮-确认``,task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,缺失才用兜底常量。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_events import decide_event
from sr_od.application.currency_war.kernel.cw_investments import get_strategy
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
    confirm_and_verify,
    safe_click,
)
from sr_od.application.currency_war.telemetry import recorder, schema
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenInvestStrategy(SrOperation):
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
        self._ocr_map: dict | None = None   # _read_options 存全图 OCR(ADR-0132 效果采集复用,零额外 OCR)
        self._refresh_count: int = 0        # OCR 到的「刷新次数N」(刷新流读;ADR-0146)

    # 刷新按钮动态定位(2026-08-16 用户指认圆形按钮 + CV 实测):按钮 = 圆形图标,
    # 位于「刷新次数N」文本**左侧 ~88px** 同 y(r≈24);文本 x 有两种位置(476/974,随屏
    # 形态漂移)→ 固定 area 不可行,OCR 文本锚定 + 左偏移(HoughCircles 复核圆存在)。
    _REFRESH_BTN_DX: int = -88

    def _try_click_refresh(self) -> bool:
        """动态定位刷新圆钮(文本锚定;2026-08-16 CV 实测修正,替 yml 固定坐标 VLM 猜测值)。

        OCR「刷新次数N」文本(已记坐标 self._refresh_text_pt)→ 按钮 = 文本左偏 88px;
        无文本锚 → False(不点)。⚠️ 未做 HoughCircles 圆复核(review:三帧实测偏移恒定,
        复核留待多样性本不足时再上)。偏移错时刷新验证失败 → 静默选旧三张照常选
        (ADR-0146 失败安全设计;该态=需重新 CV 实测锚定的版本变更信号)。
        """
        _pt = getattr(self, '_refresh_text_pt', None)
        if _pt is None:
            return False
        target = Point(int(_pt.x + CwScreenInvestStrategy._REFRESH_BTN_DX), int(_pt.y))
        log.info(f'[cw-strat] 建议刷新(次数={self._refresh_count})→ 圆钮@({target.x},{target.y})(文本锚定)')
        self.ctx.controller.mouse_move(target)   # bug#1 缓解
        self.ctx.controller.click(target)
        time.sleep(1.5)
        return True

    def _read_options(self, screen) -> list[tuple[str, int, int]]:
        """OCR 3 张卡的 ``(名字, center-x, center-y)``,按卡名行 y 过滤 + 左→右排序。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        self._ocr_map = ocr_map   # ADR-0132:采集复用(同一帧 OCR,不重跑)
        opts: list[tuple[str, int, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (CwScreenInvestStrategy.NAME_CY_LO <= cy <= CwScreenInvestStrategy.NAME_CY_HI
                    and 2 <= len(text) <= 8 and text not in CwScreenInvestStrategy._EXCLUDE):
                opts.append((text, mrl.max.center.x, cy))
        opts.sort(key=lambda t: t[1])
        return opts

    @operation_node(name='投资策略', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-投资策略', '标识-请选择投资策略').is_success:
            return self.round_fail('非投资策略屏')

        # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
        # #11,2026-09-02):「请选择投资策略」标题出现 1s 后画面(三卡)才稳定
        # (流转 = 备战 → 金币过场动画 → overlay 自动弹出)——入口帧可能在
        # 稳定期内,立即读刷新次数/卡名有读缺风险。等 1s 重截稳定帧再读
        # (与 cw_screen_invest_env #3 修复同型)。
        time.sleep(1.0)
        screen = self.screenshot()

        # ADR-0146 刷新流(生产依赖):OCR「刷新次数N」→ 记次数 + 文本锚(_try_click_refresh
        # 动态定位刷新圆钮用)。原临时采集钩子已删(结论已达成:样本 574 张归档
        # refresh_ui_samples.jsonl,2026-08-17 标结论;jsonl 落盘与整屏 cw_shot_unique 移除)。
        import re as _re

        from one_dragon.base.geometry.rectangle import Rect as _Rect
        for _t, _m in self.ctx.ocr_service.get_ocr_result_map(
                image=screen, rect=_Rect(300, 790, 1650, 890), crop_first=False).items():
            _mm = _re.search(r'刷新次数\s*(\d+)', _t)
            if _mm and _m.max is not None:
                self._refresh_count = int(_mm.group(1))
                self._refresh_text_pt = Point(int(_m.max.center.x), int(_m.max.center.y))
                log.info(f'[cw-strat] 刷新次数={_mm.group(1)} @({_m.max.center.x:.0f},{_m.max.center.y:.0f})')
                break

        opts = self._read_options(screen)
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _x, _y in opts]
        # 不可读 → 传空 GameState(decide_event 只用 board 判 DoT 克制,空 board = 不惩罚,安全)。
        match = self.ctx.cw_match
        if names:
            if match is not None:
                pick = match.strategy.decide_invest('strategy', names, match.session.last_state or GameState(), match.session, config)  # ADR-0144:真状态替空 stub
            else:
                pick = decide_event(names, config, GameState(hp=100, hp_readable=True))  # 防御:无 match(局外独立跑)。满血档语义改由构造点显式声明(W823 hp None 化后默认 None;ADR-0141 品质难度惩罚读 state.hp,SimpleNamespace 缺字段会 AttributeError(invest_env 同款已实锤))
        else:
            pick = None
        # ADR-0146(缺口1):decide 建议刷新(PickEvent.refresh = 三张最优 < 50)且 OCR 到次数>0
        # → 点刷新圆钮(_try_click_refresh 文本锚定)→ 重读重选(一次性)。
        # 原停机钩子已删(按钮坐标已由 CV 实测文本锚定实锤,挂入至删除零触发;
        # 生命周期定谳:W437 投资钩子审计报告 .debug/temp/currency_war/w437_invest_hooks_audit/)。
        if (pick is not None and getattr(pick, 'refresh', False)
                and self._refresh_count > 0
                and self._try_click_refresh()):
            _after = self.screenshot()
            _new = self._read_options(_after)
            if _new and [n for n, _x, _y in _new] != names:
                log.info(f'[cw-strat] 刷新成功重读: {[n for n, _x, _y in _new]}')
                opts, names = _new, [n for n, _x, _y in _new]
                if match is not None:
                    pick = match.strategy.decide_invest('strategy', names, match.session.last_state or GameState(), match.session, config)
                else:
                    pick = decide_event(names, config, GameState())
            else:
                # 验证失败但次数减了 = 刷新生效但新三张碰巧同名(罕见);只 log 不停
                # (原停机钩子已删,定谳见 cw_screen_invest_env 同位注释)。
                import re as _re2
                _cnt2 = None
                for _t, _m in self.ctx.ocr_service.get_ocr_result_map(
                        image=_after, crop_first=False).items():
                    _mm2 = _re2.search(r'刷新次数\s*(\d+)', _t)
                    if _mm2 and _m.max is not None:
                        _cnt2 = int(_mm2.group(1))
                        break
                log.info('[cw-strat] 刷新生效但候选同名(次数 %s→%s),按新决策继续', self._refresh_count, _cnt2)
        if pick is not None and 0 <= pick.option_idx < len(opts):
            chosen, choose_x, choose_y = opts[pick.option_idx]
            reason = pick.reason
        elif opts:
            chosen, choose_x, choose_y, reason = opts[0][0], opts[0][1], opts[0][2], 'fallback(no-decision)'
        else:
            chosen, choose_x, choose_y, reason = '?', 920, 490, 'fallback(no-ocr)'
        log.info(f'[cw-strat] options={names} chose={chosen!r}@({choose_x},{choose_y}) reason={reason}')
        # 写入 session.active_strategies(原 bug:chosen 只点不存 → active_strategies 恒空 → 经济/难度判定静默失效,
        # 如 cw_economy._refresh_cost 刷新减费策略判定、刷新费用减免都读不到已持有策略)。
        # 投资策略可多张(局中重复选)→ append;去重防重选同一张时重复入列。
        if match is not None and chosen != '?':
            if chosen not in match.session.active_strategies:
                match.session.active_strategies.append(chosen)
        # ADR-0132 采集:候选全集 + 效果原文(描述带 y 505-835,排除卡名行/确认/刷新次数 UI)按卡分桶
        # → invest_cards.jsonl;未注册名告警(注册表只 T0 子集,315 长尾靠采集渐进补全)。
        _items = [(t, m.max.center.x, m.max.center.y)
                  for t, m in (self._ocr_map or {}).items() if m.max is not None]
        _anchors = [(i, x) for i, (_n, x, _y) in enumerate(opts)]
        _buckets = schema.bucket_card_texts(_anchors, _items,
                                                  CwScreenInvestStrategy.NAME_CY_HI, 835)
        _cards = [{"idx": i, "name": n, "x": x,
                   "effect_text": " | ".join(_buckets.get(i, [])), "chosen": n == chosen}
                  for i, (n, x, _y) in enumerate(opts)]
        recorder.record_invest_cards("strategy", _cards)
        for _c in _cards:
            if _c["name"] not in ('?',) and get_strategy(_c["name"]) is None:
                log.warning(f'[cw-strat] 投资策略名不在注册表(数据缺口,效果原文已采集): {_c["name"]!r}')

        # 点最优卡的**卡名**选中(Y 从 screen_info「区域-卡名行」center 读;缺失兜底 CARD_CLICK_Y=474)。
        # safe_click 带 bug#1 mouse_move 缓解(partner reset 根因同类)。
        _sel = area_center(self.ctx, '区域-卡名行', CwScreenInvestStrategy.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else CwScreenInvestStrategy.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        safe_click(self, target, tag='cw-strat')
        time.sleep(0.7)
        # 确认 + 验关(投资策略 消失 = overlay 关)。原「点了就 success」不验 → bug#1/卡未选中/隐藏多步 flat-loop
        # (partner reset 根因同类;write-operation「点了≠成了」;本 op docstring 已记「点名 540+ 次不选中→卡死 18min」)。
        # 确认 center 从 screen_info 读,缺失兜底。
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenInvestStrategy.SCREEN_NAME) or CwScreenInvestStrategy.CONFIRM
        return confirm_and_verify(self, confirm_point=_confirm, entry_keyword='投资策略',
                                  tag='cw-strat')
