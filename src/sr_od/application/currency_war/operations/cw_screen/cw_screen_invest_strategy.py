
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

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_events import decide_event
from sr_od.application.currency_war.kernel.cw_investments import get_strategy
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
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
    #: 入口锚复探窗(动画帧容忍,治本 20/21 局同型失败 2026-09-06 01:41:30 /
    #: 02:22:28「返回状态 非投资策略屏」):投资策略节点首访时派发帧 → 本 op
    #: 首帧之间落在「备战 → 金币过场动画 → overlay 淡入」过渡段(screen_flow_timing.md
    #: #11),首帧采样可 miss「标识-请选择投资策略」;旧实现单探测 miss 即
    #: round_fail(round_fail 不吃 node_max_retry_times,直接炸出整 op),外层
    #: 重试才自愈但每次触发哨兵报警+退出。修法与 cw_loop._invest_overlay_dispatch
    #: 同族(复探=短窗+新截图):首探 miss → 短窗后新截图复探,窗口内命中即
    #: 继续;超窗仍 miss 才 round_fail(防无限等真非目标屏)。决策记录 =
    #: ADR-0529。执行层时序常量(沿 CwLoop.INVEST_REPROBE_WAIT 先例),非策略数值。
    ENTRY_REPROBE_TIMES: ClassVar[int] = 4
    ENTRY_REPROBE_WAIT_S: ClassVar[float] = 0.8

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资策略')
        self._ocr_map: dict | None = None   # _read_options 存全图 OCR(ADR-0132 效果采集复用,零额外 OCR)

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

    def _entry_anchor_hit(self, screen: MatLike) -> bool:
        """入口锚探测:screen_info id_mark「标识-请选择投资策略」命中(与
        cw_loop 0e 分发 / cw_entry 2b 分支同锚同源)。"""
        return self.round_by_find_area(
            screen, CwScreenInvestStrategy.SCREEN_NAME, '标识-请选择投资策略',
        ).is_success

    def _ensure_entry_screen(self) -> bool:
        """入口锚判定 + 动画帧复探(语义见 ENTRY_REPROBE_* 注):首帧 miss →
        短窗后新截图复探,窗口内命中即 True;超窗仍 miss 返回 False(调用方
        才报失败,防无限等真非目标屏)。"""
        screen = self.last_screenshot
        hit = self._entry_anchor_hit(screen)
        for _ in range(CwScreenInvestStrategy.ENTRY_REPROBE_TIMES):
            if hit:
                return True
            # 复探等待走可中断睡眠:裸 time.sleep 最坏 3.2s 不可停机中断,
            # 绕过框架停机加固(operation.py 停机延迟实证)。
            self._interruptible_sleep(CwScreenInvestStrategy.ENTRY_REPROBE_WAIT_S)
            screen = self.screenshot()
            hit = self._entry_anchor_hit(screen)
        # 末次复探结果必须消费:循环内 if 只判上一轮采样,最后一次采样的
        # 命中若不在此返回,会被整体丢弃(三审 off-by-one:锚恰在窗口末拍
        # 出现仍误报失败——恰是本复探窗要容忍的形态边缘)。
        return hit

    @operation_node(name='投资策略', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        if not self._ensure_entry_screen():
            # 超窗走 round_retry 而非 round_fail(二次治本,2026-09-06
            # 04:16:38 实证复探窗 3.2s 仍不够覆盖个别过渡段):retry 消耗
            # node_max_retry_times 预算有界自愈,且不产生 ERROR 行——
            # round_fail 会炸出整 op 并触发哨兵报警退出(20-22 局实证
            # 每次 fail 一次哨兵退出)。ADR-0529 原「拒 fail→retry」的
            # 前提(外层重试等价)被实证推翻,重审结论见 ADR 修订。
            return self.round_retry('投资策略屏未稳定,复探超窗重试')
        screen = self.last_screenshot

        # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
        # #11,2026-09-02):「请选择投资策略」标题出现 1s 后画面(三卡)才稳定
        # (流转 = 备战 → 金币过场动画 → overlay 自动弹出)——入口帧可能在
        # 稳定期内,立即读刷新次数/卡名有读缺风险。等 1s 重截稳定帧再读
        # (与 cw_screen_invest_env #3 修复同型)。
        time.sleep(1.0)
        screen = self.screenshot()

        # 事件面刷新已退役(ADR-0519 C10:decide_event refresh 恒 False,
        # cw_events.py「refresh 恒 False」注)——原 ADR-0146 刷新流(OCR 次数 +
        # _try_click_refresh + 刷新重读重选分支)永不可达,整段已删。

        opts = self._read_options(screen)
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _x, _y in opts]
        # 不可读 → 传空 GameState(decide_event 只用 board 判 DoT 克制,空 board = 不惩罚,安全)。
        match = self.ctx.cw_match
        if names:
            if match is not None:
                pick = match.strategy.decide_invest('strategy', names, match.session.last_state or GameState(), match.session, config)  # ADR-0144:真状态替空 stub
            else:
                pick = decide_event(names, config, GameState(hp=100, hp_readable=True))  # 防御:无 match(局外独立跑)。ADR-0519 C6/C9 后 decide_event 不读 hp/品质惩罚,hp 字段仅为 GameState 构造完整性
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
        _rr = confirm_and_verify(self, confirm_point=_confirm, entry_keyword='投资策略',
                                 tag='cw-strat')
        # 到账登记(§3.3 #22 ConfirmStrategy):active_strategies += 卡(粗粒度
        # expected;本体追加在上方既有写入点,效果走台账不进 session 推进)。
        # 仅确认落地成功登记(round_retry = 确认未发生)。
        if _rr.is_success and match is not None and chosen != '?':
            from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
                register_confirm_arrival,
            )
            register_confirm_arrival(match.session, 'ConfirmStrategy', chosen,
                                     produced_by='CwScreenInvestStrategy')
        return _rr
