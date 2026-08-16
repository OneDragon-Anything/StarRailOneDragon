# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 投资环境 3 选 1 op(从主循环拆出)。

OCR 3 张投资环境卡名 → ``cw_events.decide_event`` 按事件白名单打分 → 点**最优**卡底
+ 确认。替代原"盲点中卡"(无策略)。

卡名按行过滤:标题「投资环境」在顶(y≈98)、卡名在中(y≈392)、描述在下(y≈432)、
「确认」在底(y≈982);取 y≈392 行的短文本(2-6 字)即 3 张卡名,按 center-x 排序
左→右。decide_event 仅用 ``state.board`` 做克制判定,投资环境常在开局/局内 overlay、
board 不可读 → 传空 board stub(dot_punish 为次要细化,白名单主策略不依赖 board)。

卡底 Y + 确认坐标进 screen_info(``currency_war_invest_env``):``区域-卡牌描述行``(给 Y)
+ ``按钮-确认``(给 center),task#20 已完成;本 op 经 ``cw_observation.area_center`` 读,
缺失才用兜底常量。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_telemetry
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_events import decide_event
from sr_od.application.currency_war.cw_investments import is_known_env
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.application.currency_war.cw_observe import cw_shot_unique
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
    confirm_and_verify,
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleInvestEnv(SrOperation):
    """投资环境 3 选 1:OCR 卡名 → decide_event 打分 → 点最优卡底 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-投资环境'   # screen_info 画面(currency_war_invest_env.yml)
    # 卡选中点击 Y:screen_info「区域-卡牌描述行」center.y(task#20);常量=screen_info 缺失兜底。
    # 实测(2026-08-04):立绘在卡顶 y≈100-400(点立绘/name y390 开角色详情,非选中);
    # **描述区 y≈450 才选中**(立绘下方);卡底 y700 无效。区别 invest_strategy(描述区 y545)。
    CARD_CLICK_Y: ClassVar[int] = 450   # 兜底;首选 area_center('区域-卡牌描述行')
    # 卡名行 center-y 过滤带(排除标题 y≈98 / 描述 y≈419+ / 确认 y≈982)。
    # 卡名 y 随立绘变(实机见过 375-378 / 392),放宽 [360,410] 容变;原 [378,408] 漏 y<378 的卡名。
    NAME_CY_LO: ClassVar[int] = 360
    NAME_CY_HI: ClassVar[int] = 410
    # 非卡名(同 y 行可能误入或已知 UI 文本)
    _EXCLUDE: ClassVar[set[str]] = {'投资环境', '攻略', '确认', '角色', '装备', '剩余次数：1'}
    # 确认按钮:screen_info「按钮-确认」center(task#20);常量=兜底。
    CONFIRM: ClassVar[Point] = Point(1082, 982)   # 兜底;首选 area_center('按钮-确认')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资环境')
        self._ocr_map: dict | None = None   # ADR-0132:效果采集复用同一帧 OCR
        self._refresh_count: int = 0        # OCR 到的「剩余次数:N」(钩子写入;ADR-0146 刷新流读)
        self._refresh_text_pt = None        # 次数文本坐标(刷新圆钮动态锚;2026-08-16 CV 实测)

    # 刷新按钮动态定位(2026-08-16 CV 实测):env 屏刷新圆钮 = 「剩余次数:N」文本左侧 ~100px 同 y
    # (HoughCircles 实测圆心 (672,983) r24 vs 文本 (772,983));图标按钮 OCR 无文字 → 文本锚定。
    _REFRESH_BTN_DX: int = -100

    def _try_click_refresh(self) -> bool:
        """动态定位刷新圆钮(文本锚定;替 yml 固定坐标 VLM 猜测值)。无文本锚 → False。"""
        _pt = self._refresh_text_pt
        if _pt is None:
            return False
        target = Point(int(_pt.x + HandleInvestEnv._REFRESH_BTN_DX), int(_pt.y))
        log.info(f'[cw-env] 建议刷新(剩余={self._refresh_count})→ 圆钮@({target.x},{target.y})(文本锚定)')
        self.ctx.controller.mouse_move(target)   # bug#1 缓解
        self.ctx.controller.click(target)
        time.sleep(1.5)
        return True

    def _read_options(self, screen) -> list[tuple[str, int]]:
        """OCR 3 张卡的 ``(名字, 名字 center-x)``,按卡名行 y 过滤 + 左→右排序。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        self._ocr_map = ocr_map
        opts: list[tuple[str, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (HandleInvestEnv.NAME_CY_LO <= cy <= HandleInvestEnv.NAME_CY_HI
                    and 2 <= len(text) <= 8 and text not in HandleInvestEnv._EXCLUDE):
                opts.append((text, mrl.max.center.x))
        opts.sort(key=lambda t: t[1])
        return opts

    @operation_node(name='投资环境', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        _hit = self.round_by_find_area(screen, '货币战争-投资环境', '标识-投资环境').is_success
        log.info(f'[cw-env] enter find_area(标识-投资环境)={_hit}')
        if not _hit:
            return self.round_fail('非投资环境屏')

        opts = self._read_options(screen)

        # [采集钩子·临时,采完删(进度文件 2026-08-15 缺口1:环境屏刷新)]刷新 UI 标定:
        # 2026-08-15 M19 环境屏 OCR 实锤「剩余次数:1」可读,但全屏 OCR 无「刷新」按钮文字(疑图标按钮)
        # → ① 整屏 cw_shot_unique 存档(离线 VLM 定位按钮坐标);② 记次数文本坐标 → refresh_ui_samples.jsonl。
        cw_shot_unique(screen, 'env_refresh_ui')
        import re as _re

        for _t, _m in (self._ocr_map or {}).items():
            _mm = _re.search(r'剩余次数[：:]?\s*(\d+)', _t)
            if _mm and _m.max is not None:
                import json as _json
                from datetime import datetime as _dt
                from pathlib import Path as _P
                _p = _P('.debug/temp/currency_war/refresh_ui_samples.jsonl')
                _p.parent.mkdir(parents=True, exist_ok=True)
                with _p.open('a', encoding='utf-8') as _f:
                    _f.write(_json.dumps({
                        'ts': _dt.now().isoformat(timespec='seconds'),
                        'kind': 'env',
                        'count': int(_mm.group(1)),
                        'text_x': int(_m.max.center.x), 'text_y': int(_m.max.center.y),
                        'text': _t,
                    }, ensure_ascii=False) + '\n')
                self._refresh_count = int(_mm.group(1))   # ADR-0146 刷新流消费
                self._refresh_text_pt = Point(int(_m.max.center.x), int(_m.max.center.y))   # 按钮锚(动态定位)
                log.info(f'[cw-env] 刷新UI采集: 剩余次数={_mm.group(1)} @({_m.max.center.x:.0f},{_m.max.center.y:.0f})')
                break

        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _ in opts]
        # 见 od-dev-gameplay-automation 完成判据反馈)。可能是赛季新增 / OCR 误识 / 锁定未命名。
        for _n in names:
            if not is_known_env(_n):
                log.warning(f'[cw-env] 投资环境名不在注册表(数据缺口): {_n!r} → 该项 env_fit 走中性 fallback')
        # board 不可读 → 传空 GameState(decide_event 只用 board 判 DoT 克制,空 board = 不惩罚,安全)。
        match = self.ctx.cw_match
        if names:
            if match is not None:
                # ADR-0144:last_state(上次备战真实快照,含 hp/active_strategies)替空 stub ——
                # 环境屏 overlay 下 board 不可读,但 HP 分档/持有策略该用真值(空 stub hp=100 恒满血)。
                pick = match.strategy.decide_invest('env', names, match.session.last_state or GameState(), match.session, config)
            else:
                pick = decide_event(names, config, GameState())  # 防御:无 match(局外独立跑)。GameState 空态 hp=100(满血档):ADR-0141 品质难度惩罚读 state.hp,SimpleNamespace 缺字段曾致 AttributeError(M19 实锤)
        else:
            pick = None
        # ADR-0146(缺口1):建议刷新且剩余次数>0 → 点刷新 → 重读重选(一次性)。
        # [停机钩子·临时,用户 2026-08-16 指示] 刷新验证不通过(候选没变且次数没减)→ 停机存证:
        # env 刷新按钮是**图标**(全屏 OCR 无「刷新」文字,yml 坐标是 VLM 猜测未实锤)——
        # 与其静默 fallback(永远不知道刷新没生效),停机把真实按钮交互采下来。实锤后删钩子。
        if (pick is not None and getattr(pick, 'refresh', False)
                and self._refresh_count > 0
                and self._try_click_refresh()):
            _after = self.screenshot()
            _new = self._read_options(_after)
            _new_names = [n for n, _x in _new]
            if _new and _new_names != names:
                log.info(f'[cw-env] 刷新成功重读: {_new_names}')
                opts, names = _new, _new_names
                if match is not None:
                    pick = match.strategy.decide_invest('env', names, match.session.last_state or GameState(), match.session, config)
                else:
                    pick = decide_event(names, config, GameState())
            else:
                import re as _re2
                _cnt2 = None
                for _t, _m in self.ctx.ocr_service.get_ocr_result_map(
                        image=_after, crop_first=False).items():
                    _mm2 = _re2.search(r'剩余次数[::]\s*(\d+)', _t)
                    if _mm2 and _m.max is not None:
                        _cnt2 = int(_mm2.group(1))
                        break
                if _cnt2 is None or _cnt2 >= self._refresh_count:
                    _shot = self.save_screenshot(prefix='cw_env_refresh_fail')
                    from pathlib import Path as _P2
                    _fp = _P2('.debug/temp/currency_war/refresh_click_fail.flag')
                    _fp.parent.mkdir(parents=True, exist_ok=True)
                    _fp.write_text(
                        f'env count {self._refresh_count}->{_cnt2} candidates_same shot={_shot}',
                        encoding='utf-8')
                    log.warning('[cw!] [env] 刷新点击未生效(候选不变+次数未减)→ 停机存证待修准 shot=%s', _shot)
                    self.ctx.run_context.stop_running()
                    return self.round_fail(status='env 刷新点击未生效,停机存证')
                log.info('[cw-env] 刷新生效但候选同名(次数 %s→%s),按新决策继续', self._refresh_count, _cnt2)
        if pick is not None and 0 <= pick.option_idx < len(opts):
            chosen, choose_x = opts[pick.option_idx]
            reason = pick.reason
        elif opts:
            chosen, choose_x, reason = opts[0][0], opts[0][1], 'fallback(no-decision)'
        else:
            chosen, choose_x, reason = '?', 960, 'fallback(no-ocr)'
        log.info(f'[cw-env] options={names} chose={chosen!r}@x={choose_x} reason={reason}')
        # 原 bug:chosen 只点不存 → state.active_env 恒空 → env_fit 全 0.5 → T0 env 绑定静默失效。
        if match is not None and chosen != '?':
            match.session.active_env = chosen
        # ADR-0132 采集:候选全集 + 效果原文(描述带 y 410-900)按卡分桶 → invest_cards.jsonl
        # (kind=env;环境注册表虽全量,效果原文仍采 —— 对拍校验 + 版本变更感知)。
        _items = [(t, m.max.center.x, m.max.center.y)
                  for t, m in (self._ocr_map or {}).items() if m.max is not None]
        _anchors = [(i, x) for i, (_n, x) in enumerate(opts)]
        _buckets = cw_telemetry.bucket_card_texts(_anchors, _items,
                                                  HandleInvestEnv.NAME_CY_HI, 900)
        _cards = [{"idx": i, "name": n, "x": x,
                   "effect_text": " | ".join(_buckets.get(i, [])), "chosen": n == chosen}
                  for i, (n, x) in enumerate(opts)]
        cw_telemetry.record_invest_cards("env", _cards)

        # 点最优卡底(task#20:Y 从 screen_info「区域-卡牌描述行」center 读;缺失兜底 CARD_CLICK_Y)。
        # safe_click 带 bug#1 mouse_move 缓解(partner reset 根因同类)。
        _sel = area_center(self.ctx, '区域-卡牌描述行', HandleInvestEnv.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else HandleInvestEnv.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        safe_click(self, target, tag='cw-env')
        time.sleep(0.7)

        # 确认 + 验关(投资环境 消失 = overlay 关)。原「点了就 success」不验 → bug#1/卡未选中/隐藏多步 flat-loop
        # (partner reset 根因同类;write-operation「点了≠成了」)。确认 center 从 screen_info 读,缺失兜底。
        _confirm = area_center(self.ctx, '按钮-确认', HandleInvestEnv.SCREEN_NAME) or HandleInvestEnv.CONFIRM
        return confirm_and_verify(self, confirm_point=_confirm, entry_keyword='投资环境',
                                  tag='cw-env')
