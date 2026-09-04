
"""货币战争 投资环境 3 选 1 op(从主循环拆出)。

OCR 3 张投资环境卡名 → ``cw_events.decide_event`` 按事件白名单打分 → 点**最优**卡底
+ 确认。替代原"盲点中卡"(无策略)。

卡名按行过滤:标题「投资环境」在顶(y≈98)、卡名在中(y≈392)、描述在下(y≈432)、
「确认」在底(y≈982);取 y≈392 行的短文本(2-6 字)即 3 张卡名,按 center-x 排序
左→右。decide_event 仅用 ``state.board`` 做克制判定,投资环境常在开局/局内 overlay、
board 不可读 → 传空 board stub(dot_punish 为次要细化,白名单主策略不依赖 board)。

卡底 Y + 确认坐标进 screen_info(``currency_war_invest_env``):``区域-卡牌描述行``(给 Y)
+ ``按钮-确认``(给 center),task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,
缺失才用兜底常量。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_events import decide_event
from sr_od.application.currency_war.kernel.cw_investments import is_known_env
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    confirm_and_verify,
    safe_click,
)
from sr_od.application.currency_war.telemetry import recorder, schema
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenInvestEnv(SrOperation):
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
    # 变异窗宽限(秒):覆盖确认动画 + 节点行刷新重试窗;超时后三票校验恢复落账。
    ENV_GRACE_S: ClassVar[float] = 45.0
    # 确认按钮:screen_info「按钮-确认」center(task#20);常量=兜底。
    CONFIRM: ClassVar[Point] = Point(1082, 982)   # 兜底;首选 area_center('按钮-确认')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资环境')
        self._ocr_map: dict | None = None   # ADR-0132:效果采集复用同一帧 OCR

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
            if (CwScreenInvestEnv.NAME_CY_LO <= cy <= CwScreenInvestEnv.NAME_CY_HI
                    and 2 <= len(text) <= 8 and text not in CwScreenInvestEnv._EXCLUDE):
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

        # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
        # 「用户口述过场动画时序」#3,2026-09-02):「投资环境」标题出现后
        # 1s 内三卡才渲染稳定——入口帧可能在稳定期内,立即 OCR 读卡名有
        # 读缺/读半字风险(空候选 → fallback 盲点屏中)。等 1s 重截稳定帧
        # 再读再决策(与简报 0a0b 修复同型)。
        time.sleep(1.0)
        screen = self.screenshot()
        opts = self._read_options(screen)

        # 事件面刷新已退役(ADR-0519 C10:decide_event refresh 恒 False,
        # cw_events.py「refresh 恒 False」注)——原 ADR-0146 刷新流(OCR 剩余次数 +
        # _try_click_refresh + 刷新重读重选分支)永不可达,整段已删。

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
                pick = decide_event(names, config, GameState(hp=100, hp_readable=True))  # 防御:无 match(局外独立跑)。ADR-0519 C6/C9 后 decide_event 不读 hp/品质惩罚,hp 字段仅为 GameState 构造完整性
        else:
            pick = None
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
        _buckets = schema.bucket_card_texts(_anchors, _items,
                                                  CwScreenInvestEnv.NAME_CY_HI, 900)
        _cards = [{"idx": i, "name": n, "x": x,
                   "effect_text": " | ".join(_buckets.get(i, [])), "chosen": n == chosen}
                  for i, (n, x) in enumerate(opts)]
        recorder.record_invest_cards("env", _cards)

        # 点最优卡底(task#20:Y 从 screen_info「区域-卡牌描述行」center 读;缺失兜底 CARD_CLICK_Y)。
        # safe_click 带 bug#1 mouse_move 缓解(partner reset 根因同类)。
        _sel = area_center(self.ctx, '区域-卡牌描述行', CwScreenInvestEnv.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else CwScreenInvestEnv.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        safe_click(self, target, tag='cw-env')
        time.sleep(0.7)

        # 台账:确认前开「投资环境变异窗」豁免——环境选择是位面节点序列唯一
        # 变异源(用户口述),确认到节点行重读刷新之间查表与逐帧校验的不一致
        # 是合法变异,三票校验不得落缺陷台账。重读成功后关窗(置 0)。
        try:
            from sr_od.application.currency_war.kernel.cw_state import get_node_ledger
            _ledger = get_node_ledger(getattr(getattr(self.ctx, 'cw_match', None), 'session', None))
            if _ledger is not None:
                _ledger.env_grace_until = time.monotonic() + CwScreenInvestEnv.ENV_GRACE_S
        except Exception:   # noqa: BLE001  观测面 best-effort
            pass

        # 确认 + 验关(投资环境 消失 = overlay 关)。原「点了就 success」不验 → bug#1/卡未选中/隐藏多步 flat-loop
        # (partner reset 根因同类;write-operation「点了≠成了」)。确认 center 从 screen_info 读,缺失兜底。
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenInvestEnv.SCREEN_NAME) or CwScreenInvestEnv.CONFIRM
        _result = confirm_and_verify(self, confirm_point=_confirm, entry_keyword='投资环境',
                                     tag='cw-env')
        # 台账写点②:环境选择完成(overlay 真关)→ 重读备战节点行刷新权威表
        # (环境可能增删/改节点,表必须反映变异后序列)。失败不重试阻塞——
        # cw_screen_prep 每备战帧仍会逐帧识别,此处 miss 只延迟表刷新。
        if _result.is_success:
            self._refresh_node_ledger()
        return _result

    def _refresh_node_ledger(self) -> None:
        """台账写点②:重读备战节点行 → 按位合并进 session 权威表 + 关变异窗。

        读不到 clean 帧(转场动画)→ 1.5s 后重试一次,仍 miss 则保留窗口
        由下个写入端兜(不阻塞对局;合并语义 = None 位保旧,见 ledger_update_plane)。
        """
        from sr_od.application.currency_war.kernel.cw_state import (
            get_node_ledger,
            ledger_update_plane,
        )
        from sr_od.application.currency_war.obs.cw_observation import (
            read_node_sequence,
            read_phase_round,
        )
        _sess = getattr(getattr(self.ctx, 'cw_match', None), 'session', None)
        _ledger = get_node_ledger(_sess)
        if _sess is None or _ledger is None:
            return
        for _attempt in (1, 2):
            time.sleep(1.5 if _attempt == 1 else 0.0)
            screen = self.screenshot()
            slots = read_node_sequence(self.ctx, screen)
            if slots is None:
                continue
            _plane, _round = read_phase_round(self.ctx, screen)
            if not _plane:
                break
            _seq = [getattr(s, 'node_type', None) for s in slots]
            _changed = ledger_update_plane(_sess, int(_plane), _seq, 'prep_row')
            _ledger.env_grace_until = 0.0   # 表已刷新,关变异窗
            log.info('[cw-env] 台账重读刷新 p%d(轮%s)%s:%s',
                     _plane, _round, '(有变更)' if _changed else '(无变更)', _seq)
            return
        log.info('[cw-env] 台账重读 miss(非 clean 帧),变异窗保留等下个写入端')
