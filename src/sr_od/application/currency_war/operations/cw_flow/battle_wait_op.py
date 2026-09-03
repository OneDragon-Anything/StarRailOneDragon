"""货币战争 战斗等待 op(W971 05-battle §1;P4 收编)。

接 「出战 op 交回循环」之后的战斗/结算窗口:等结算画面 → 结算处理(遥测读点 →
点「继续挑战」)→ 完成判据白名单任一出现(备战系/补给/遭遇/投资策略/强敌来袭/
位面过渡锚)→ round_success 交回主循环分发;「前往结算」链的团灭终局(多页 →
返回货币战争 → 大厅)= 第三出口,round_success(status='terminal_lobby') 交整局
退出(主循环 3c 收口)。决策记录 = DD-019(docs/develop/currency_war/redesign/
decisions/dd-019)。

结构判据(od-dev-write-operation「循环驱动玩法」):本 op = node-per-op 的
**逻辑单元生命周期 owner**——战斗+结算是一个单元(开始=出战,结束=白名单锚/
团灭终局),单元内多阶段(等待/页1 动画/结算页/败局链),节点作用域预算 =
未知帧 bail 上界 + 出战宽限(ADR-0250)收编。外循环只回答「在不在战斗窗口」
(驻留闩 + 帧锚双入口),不进单元内部分类。

收编来源(cw_loop 分支随迁;语义逐条保真,遥测写端调用原样平移):
- 分支 1f(失败结算页:进度符号闩/面板延迟门/页1 三项暂存/败局补录/翻页);
- 分支 2(「点击空白加速」页1 动画帧:progress/三项暂存 + 点空白加速);
- 分支 3(挑战成功结算:读点前等 1.5s(#25 用户裁定)/C-1 新帧计数/
  M39 长按兜底/备战相位机复位);
- 分支 3b(前往结算链:前往结算/下一页/下一步/返回货币战争 + 挑战失败
  hp=0 补录);
- 分支 6(战斗/过场屏总伤害/数据统计 → 点空白推进)。

遥测连续性红线(W971 05-battle §1):decisions.jsonl / outcomes / match_archive
的写入调用自 cw_loop 原样平移(见各方法注),字段面零变更。

自动战斗检测(W971 05-battle §2):**本批不做**(采集未完成)。接口预留 =
本 op ①段(等结算画面)轮询中消费「自动战斗未开启」信号(画面右下角
「我方行动中」文本,待建档)→ 自愈/报警;接通前战斗段依赖自动战斗已开。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_performance import (
    HP_CONFIDENCE_THRESHOLD,
)
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.obs.cw_observation import read_phase_round
from sr_od.application.currency_war.obs.cw_settlement_obs import (
    parse_progress_fill_ratio,
    parse_settlement_progress,
    parse_settlement_round,
    read_round_outcome,
    read_settle_damage_breakdown,
    settle_page1_progress_sign,
)
from sr_od.application.currency_war.telemetry import defects, recorder
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


@dataclass
class SettlementState:
    """战斗/结算链跨迭代状态机(原 cw_loop 散挂属性收拢;随迁不改语义)。

    [字段定义] 生命周期 = 每局(handle_init 随 RunLoop 新建),不是每场战斗
    ——页间暂存/防重指纹都是「本局内跨场」语义(残留屏判定/败局页防重按局
    记忆)。坐标系:
    - last_outcome_hp = outcomes 内存轨迹末条真 hp(summary final_hp 真值源;
      conf≥0.9 才更新,r3 live 修);
    - saw_defeat_settlement = 败局闩(DD-006):本局见过任一显式败局结算帧
      (3c 假 win 守卫消费);
    - last_outcome_t = 上一结算真值轮全局节点号(killed hp 对比兜底的轮次
      邻接门);
    - rounds_done = 已完成战斗轮数(C-1 新结算帧计数;轮锚点 = 挑战成功结算);
    - settle_page1_progress / settle_page1_settle = 结算页1 三项遥测暂存
      (DD-006;页2 记录时合并消费,用后清);
    - settle_p1_ts = 结算页1 面板渲染延迟门计时(SETTLE_PANEL_WAIT_S);
    - settle_stay = 结算屏停留计数(M39 长按兜底触发器,≥3 长按);
    - last_settle_fp / last_loss_fp = 同屏指纹防重(C-1 计数/败局行防重);
    - first_settlement_seen / run_start_ts / is_new_match = relaunch 残留
      结算屏判据三件(迁移审计 w28;run_start_ts/is_new_match 由 RunLoop
      handle_init 注入);
    - battle_ts = 出战时刻(RunLoop ADR-0250 战斗窗口开窗点注入;op 据此
      判「战斗进行中合法静止」宽限);
    - saw_settlement = 本窗口已见结算屏(RunLoop 据此关战斗 watch 宽限)。
    """
    last_outcome_hp: int | None = None
    saw_defeat_settlement: bool = False
    last_outcome_t: int | None = None
    rounds_done: int = 0
    settle_page1_progress: int | None = None
    settle_page1_settle: dict = field(default_factory=dict)
    settle_p1_ts: float | None = None
    settle_stay: int = 0
    last_settle_fp: tuple | None = None
    last_loss_fp: tuple | None = None
    first_settlement_seen: bool = False
    run_start_ts: float = 0.0
    is_new_match: bool = True
    battle_ts: float | None = None
    saw_settlement: bool = False


class BattleWaitOp(SrOperation):
    """战斗等待 op:等结算 → 结算处理 → 白名单完成判据 / 团灭终局分叉。"""

    #: 结算页1 掉血说明 tooltip 渲染延迟门(随迁自 cw_loop,注释原文见
    #: 该处 git 历史):面板进页 ~2-4s 才出现;门语义 = 面板 visible 或超时
    #: 才放行推进。超时兜底覆盖胜轮(面板整块不出现,帧实证)。
    SETTLE_PANEL_WAIT_S: ClassVar[float] = 4.0
    #: 败局闩次级证据裁决的轮次下限(DD-006 裁决 5 二轮审计,随迁):
    #: t = (plane-1)*9+round 过中位 + 面板负分量 双证据才置闩。
    SETTLE_DEFEAT_LATCH_MIN_T: ClassVar[int] = 14
    #: relaunch 残留结算屏判据宽限(随迁自 cw_loop RELAUNCH_SETTLE_GRACE_S)。
    RELAUNCH_SETTLE_GRACE_S: ClassVar[float] = 30.0
    #: M39 长按兜底(2026-08-16 3-1 实证):「继续挑战」点击不响应 → 结算屏
    #: 停留 ≥3 轮 → 长按 (960,898) 兜底推进。
    SETTLE_STAY_LONG_PRESS: ClassVar[int] = 3
    #: 出战宽限(ADR-0250 随迁口径):战斗进行中合法静止,不进未知帧计数。
    BATTLE_WATCH_GRACE_S: ClassVar[float] = 600.0
    #: 未知帧 bail 上界(节点作用域预算;超限 = 留证 + bail 交主循环未知
    #: 画面分支,W971 05-battle §1 超时兜底)。战斗特效长帧期宽限已由
    #: BATTLE_WATCH_GRACE_S 挡在计数外,本值只辖「结算后卡死」形态。
    UNKNOWN_BAIL_N: ClassVar[int] = 10
    # 点空白区(加速战斗/关叠层;避开中央内容;随迁自 cw_loop.BLANK)
    BLANK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)
    # 结算「前进」按钮恒在底部中央(随迁自 cw_loop.SETTLEMENT_NEXT,
    # 坐标出处见该处 git 历史:下一页/返回货币战争实测中心)。
    SETTLEMENT_NEXT: ClassVar[Point] = Point(960, 898)

    def __init__(self, ctx: SrContext, st: SettlementState,
                 config: CurrencyWarConfig):
        SrOperation.__init__(self, ctx, op_name='货币战争-战斗等待')
        self._st = st
        self._cw_config = config
        self._unknown_streak: int = 0

    # ===== ①段:等结算画面 =====
    #
    # 自动战斗检测接口(W971 05-battle §2;本批不做,采集未完成):
    # 战斗进行中宽限轮询处(下方 _in_battle_grace 分支)是本检测的消费点——
    # 采到「我方行动中」帧并建档后,在此判别未开自动战斗 → 自愈(点开关,
    # 倾向)/报警,二选一按采集后的裁决定。

    def _in_battle_grace(self, now: float) -> bool:
        """战斗进行中宽限判定(ADR-0250 随迁):未见过结算屏且出战未超
        宽限 → 合法静止,不进未知帧计数。"""
        return (not self._st.saw_settlement
                and self._st.battle_ts is not None
                and now - self._st.battle_ts < BattleWaitOp.BATTLE_WATCH_GRACE_S)

    # ===== ③段:完成判据白名单(W971 05-battle §1 裁决集)=====
    # 白名单语义 = 「已回备战系画面」的到达判定(宽;面板就位判定由循环
    # 判定序承接,不在本 op 承诺内——05-battle §1 架构修正条)。位面简报
    # 不在切换链上(仅入场出现一次,用户裁决 2026-09-02),不列。
    COMPLETION_ANCHORS: ClassVar[tuple[tuple[str, str], ...]] = (
        ('货币战争-备战', '备战标识-购买经验'),
        ('货币战争-补给', '标识-补给阶段'),
        ('货币战争-遭遇节点', '标识-遭遇节点'),
        ('货币战争-投资策略', '标识-请选择投资策略'),
        ('货币战争-BOSS简报', '标识-强敌来袭'),
    )

    def _hit_completion_anchor(self, screen) -> bool:
        """完成判据白名单任一命中(纯判定)。备战用单锚(宽到达判定;
        「按钮-出战」双锚精判是循环备战分支的职责,此处重复即双源)。
        P4R3:BOSS简报项补「强敌」片段 OCR 兜底(area 锚可被误读击穿,
        「强敌来袭」→「强敌米」实测帧);位面过渡项加 boss 排他——共享
        文案「点击空白处继续」不作跨画面判据(判别单一源见 boss_briefing_op)。"""
        for _scr, _area in BattleWaitOp.COMPLETION_ANCHORS:
            if self.round_by_find_area(screen, _scr, _area,
                                       crop_first=False).is_success:
                return True
        from sr_od.application.currency_war.operations.cw_flow.boss_briefing_op import (
            is_boss_briefing_texts,
            read_ocr_texts,
        )
        _texts = read_ocr_texts(self.ctx, screen)
        if is_boss_briefing_texts(_texts):
            return True   # boss 简报帧(含 area 锚误读形态)→ 交回循环 0p 接管
        # 位面过渡锚(boss 局每位面开始出现一次;不在切换链上的位面简报不列;
        # boss 简报帧已在上方排他——共享文案不误判为本白名单项)
        return self.round_by_ocr(screen, '点击空白处继续',
                                 lcs_percent=0.8).is_success

    # ===== 结算链遥测(自 cw_loop 原样平移;写端调用零变更)=====

    def _record_round_outcome(self, screen, telemetry_only: bool = False) -> None:
        """P1.5 观测回路:结算屏 → read_round_outcome → strategy.on_round_end。

        (自 cw_loop._record_round_outcome 平移;方法级注释与判定链逐条
        保真,详见原处 git 历史。差异仅两处载体:循环态挂 SettlementState、
        ADR-0250 窗口关由 saw_settlement 承载。)
        """
        if self.ctx.cw_match is None:
            return
        if not telemetry_only:
            self._st.saw_settlement = True   # ADR-0250:见结算屏 → 窗口关
        _st = self._st
        _residual = False if telemetry_only else self._mark_relaunch_residual()
        _source = 'recovered' if _residual else ('loss_page' if telemetry_only else '')
        try:
            _session = self.ctx.cw_match.session
            _plane, _round = read_phase_round(self.ctx, screen)
            _ocr_texts = [r.data for r in self.ctx.ocr_service.get_ocr_result_list(
                image=screen, rect=None, color_range=None, crop_first=False)]
            # plane 归属修复(W239):结算屏头部「X-Y」屏面真值 + 单调门,
            # 逻辑原样平移(注释详见原处)。
            _scr = parse_settlement_round(_ocr_texts)
            if _scr is not None:
                if _residual:
                    log.warning('[cw][bwait] relaunch 残留结算屏:round 按「%s-%s」校正'
                                '(原兜底 P%s-r%s)', _scr[0], _scr[1], _plane, _round)
                    _plane, _round = _scr
                else:
                    _t_new = (_scr[0] - 1) * 9 + _scr[1]
                    _t_old = (_plane - 1) * 9 + _round if (_plane and _round) else None
                    if _t_old is None or _t_new >= _t_old:
                        if (_scr[0], _scr[1]) != (_plane, _round):
                            log.info('[cw-bwait] plane/round 结算屏真值「%s-%s」覆盖 '
                                     'last-known「%s-%s」(W239)', _scr[0], _scr[1],
                                     _plane, _round)
                            defects.record_defect(
                                'phase_round', 'perception_conflict',
                                expected=f'备战缓存 {_plane}-{_round}',
                                observed=f'结算屏 {_scr[0]}-{_scr[1]}',
                                plane=_plane, round_num=_round,
                                verdict='留证-结算屏真值覆盖 last-known',
                                reader_source='settlement_vs_prep_round',
                                gap_large=False, auto_resolved=True,
                                refs=[{'stream': 'outcomes',
                                       'key': f'plane={_plane}|round={_round}'}],
                                note='观测自检框架设计 §2.7:同轮双读不等留证;'
                                     '残留屏豁免')
                        _plane, _round = _scr
                    else:
                        log.warning('[cw-bwait] 结算屏「%s-%s」落后 last-known「%s-%s」'
                                    '= OCR 假阳 → 拒(W239 单调门)',
                                    _scr[0], _scr[1], _plane, _round)
                        defects.record_defect(
                            'phase_round', 'perception_conflict',
                            expected=f'备战缓存 {_plane}-{_round}',
                            observed=(f'结算屏 {_scr[0]}-{_scr[1]}(落后 last-known'
                                      '=OCR 假阳,单调门拒)'),
                            plane=_plane, round_num=_round,
                            verdict='留证-结算屏读数落后 last-known 判 OCR 假阳拒',
                            reader_source='settlement_vs_prep_round',
                            gap_large=False, auto_resolved=True,
                            refs=[{'stream': 'outcomes',
                                   'key': f'plane={_plane}|round={_round}'}],
                            note='观测自检框架设计 §2.7;残留屏豁免')
            _comp_tag = _session.target_comp.name if _session.target_comp else '?'
            _is_boss = self.round_by_find_area(
                screen, '货币战争-结算', '标识-首领').is_success
            _node = 'boss' if _is_boss else self._normalize_node_type(
                getattr(_session, 'node_type_current', None)
                or self._node_type_from_table(_session, _plane, _round)
                or '普通战斗')
            _obs = read_round_outcome(self.ctx, screen, plane=_plane, round_num=_round,
                                      comp_tag=_comp_tag, node_type=_node)
            if telemetry_only and _obs.killed is not False:
                log.info('[cw-bwait] loss_page 行不落:killed=%s 非显式败局(W239)',
                         _obs.killed)
                return
            # r68 页1 progress 合并(DD-006;暂存源 = SettlementState)
            if _obs.progress_delta is None:
                _pg1 = _st.settle_page1_progress
                if _pg1 is not None:
                    _obs.progress_delta = _pg1
                    log.info('[cw-bwait] progress 合并(第一页暂存):%s', _pg1)
                _st.settle_page1_progress = None
            # boss 胜局 win 真值(DD-006):进度符号先于 hp 对比兜底
            if _obs.killed is None and _obs.progress_delta is not None:
                _obs.killed = _obs.progress_delta > 0
                log.info('[cw-bwait] killed 进度符号判定:progress=%s → %s',
                         _obs.progress_delta, _obs.killed)
            # killed 文本兜底(双侧置信度门 + 轮次邻接门;DD-006)
            _now_t = (_plane - 1) * 9 + _round if (_plane and _round) else None
            if not telemetry_only and _obs.hp_confidence >= 0.9 and _now_t is not None:
                if _obs.killed is None:
                    _prev_hp = getattr(_session, 'last_hp', None)
                    _prev_t = _st.last_outcome_t
                    if (_prev_hp is not None and _prev_t is not None
                            and _now_t - _prev_t == 1):
                        _obs.killed = _obs.hp_after >= _prev_hp
                        log.info('[cw-bwait] killed 兜底(hp 对比):上轮 %s → 本轮 %s → %s',
                                 _prev_hp, _obs.hp_after,
                                 '赢' if _obs.killed else '输')
                _st.last_outcome_t = _now_t
            # 结算三项遥测页1 暂存合并(同 progress 合并法;暂存值优先于页2 同帧读数)
            _st1 = _st.settle_page1_settle
            if _st1:
                for _k in ('progress_fill_ratio', 'damage_base',
                           'damage_unfinished_progress'):
                    if _st1.get(_k) is not None:
                        setattr(_obs, _k, _st1[_k])
                if _st1.get('damage_breakdown_visible'):
                    _obs.damage_breakdown_visible = True
            _st.settle_page1_settle = {}
            _st.settle_p1_ts = None
            if not telemetry_only:
                self.ctx.cw_match.strategy.on_round_end(
                    GameState(), _session, self._cw_config, _obs)
                if _obs.hp_confidence >= HP_CONFIDENCE_THRESHOLD and _now_t is not None:
                    _session.last_hp_t = _now_t
            recorder.record_outcome(_obs, source=_source)
            if not telemetry_only:
                if _obs.hp_confidence >= 0.9:
                    _st.last_outcome_hp = _obs.hp_after
                recorder.record_exogenous(
                    _round, 'node_enter',
                    detail=f'battle_done:{_obs.node_type}',
                    state=_session.last_state)
                # 结算屏覆盖点(EXPECTED_STATE §2:hp/gold/streak/level 全可信
                # + 05-battle §1「结算屏 hp/gold/level 写 session」):hp 真值
                # 链走 on_round_end→last_hp(上);gold/level/经验经
                # parse_settlement_assets 写 last_state 并做覆盖点对账
                # (expected vs actual diff → 留证)。best-effort,失败不阻塞。
                try:
                    from sr_od.application.currency_war.kernel.cw_expected_state import (
                        reconcile_expected,
                    )
                    from sr_od.application.currency_war.obs.cw_settlement_obs import (
                        parse_settlement_assets,
                    )
                    _assets = parse_settlement_assets(_ocr_texts)
                    _lst = _session.last_state
                    if _lst is not None:
                        if _assets.get('gold') is not None:
                            _lst.gold = _assets['gold']
                            _lst.gold_readable = True
                        if _assets.get('level') is not None:
                            _lst.level = _assets['level']
                            _lst.level_readable = True
                        if (_assets.get('xp_cur') is not None
                                and _assets.get('xp_next') is not None):
                            _lst.xp_progress = (_assets['xp_cur'],
                                                _assets['xp_next'])
                    _act = {
                        'gold': (_assets.get('gold'),
                                 _assets.get('gold') is not None),
                        'xp_ledger': (
                            f'lv{_assets.get("level") or 0} '
                            f'xp{_assets.get("xp_cur") or 0}',
                            _assets.get('level') is not None),
                    }
                    reconcile_expected(_session, 'settlement', _act)
                except Exception as e:  # noqa: BLE001  观测面不阻塞对局
                    log.warning('[cw-bwait] 结算覆盖点对账失败(不阻塞): %s', e)
            log.info('[cw-bwait] on_round_end plane=%s round=%s hp_after=%s conf=%s '
                     'comp=%s node=%s%s',
                     _plane, _round, _obs.hp_after, _obs.hp_confidence, _comp_tag,
                     _obs.node_type,
                     ' [loss_page telemetry-only]' if telemetry_only else '')
        except Exception as e:  # noqa: BLE001  观测回路失败不阻塞对局
            log.warning('[cw-bwait] on_round_end 失败(不阻塞): %s', e)

    def _record_loss_page(self, screen, pre_fp: tuple | None = None) -> None:
        """失败结算页 → telemetry-only 补一行 outcome + 同屏指纹防重
        (自 cw_loop._record_loss_page 平移,逻辑零变更)。"""
        try:
            if pre_fp is not None:
                _fp = pre_fp
            else:
                _fp = tuple(sorted((r.data, r.y) for r in
                                   self.ctx.ocr_service.get_ocr_result_list(
                                       image=screen, rect=None, color_range=None,
                                       crop_first=False)))
            if self._st.last_loss_fp == _fp:
                return
            self._st.last_loss_fp = _fp
            self._record_round_outcome(screen, telemetry_only=True)
        except Exception as e:  # noqa: BLE001  补录失败不阻塞对局
            log.warning('[cw-bwait] loss_page 补录失败(不阻塞): %s', e)

    def _defeat_latch_by_secondary(self, pnl: dict) -> None:
        """进度符号漏读帧的败局闩次级证据裁决(DD-006 二轮审计②,随迁)。"""
        _neg = ((pnl.get('damage_base') is not None and pnl['damage_base'] < 0)
                or (pnl.get('damage_unfinished_progress') is not None
                    and pnl['damage_unfinished_progress'] < 0))
        _t = None
        _match = self.ctx.cw_match
        _lst = getattr(getattr(_match, 'session', None), 'last_state', None) \
            if _match else None
        if _lst is not None and getattr(_lst, 'plane', None) \
                and getattr(_lst, 'round_num', None):
            _t = (_lst.plane - 1) * 9 + _lst.round_num
        _min_t = BattleWaitOp.SETTLE_DEFEAT_LATCH_MIN_T
        if _neg and _t is not None and _t >= _min_t:
            self._st.saw_defeat_settlement = True
            log.info('[cw-bwait] 败局闩次级证据:面板负分量 + t=%s≥%s → 置闩'
                     '(DD-006 二轮审计)', _t, _min_t)
        else:
            log.info('[cw-bwait] 败局闩次级证据不足(负分量=%s, t=%s, 门限=%s)→ '
                     '不置闩留证(DD-006 二轮审计)', _neg, _t, _min_t)

    def _mark_relaunch_residual(self) -> bool:
        """relaunch 残留结算屏判据(迁移审计 w28,随迁;只标记不改行为)。"""
        _res = (not self._st.first_settlement_seen and self._st.is_new_match
                and time.monotonic() - self._st.run_start_ts
                < BattleWaitOp.RELAUNCH_SETTLE_GRACE_S)
        self._st.first_settlement_seen = True
        return _res

    @staticmethod
    def _normalize_node_type(raw: str) -> str:
        """节点类型词汇表统一(r363 审计 P0-1,随迁;表与语义见原处)。"""
        _MAP = {'battle': '普通战斗', 'reward': '奖励', 'encounter': '遭遇',
                'supply': '补给', 'boss': 'boss', 'megastar': '巨星',
                '战斗': '普通战斗', '奖励': '奖励', '遭遇': '遭遇',
                '补给': '补给', '首领': 'boss', '巨星': '巨星',
                '普通战斗': '普通战斗', '精英': '精英'}
        return _MAP.get((raw or '').strip(), raw or '普通战斗')

    @staticmethod
    def _node_type_from_table(_session, plane: int | None,
                              round_num: int | None) -> str | None:
        """首节点冷启动兜底:r362 槽序表查节点类型(随迁,逻辑零变更)。"""
        try:
            _table = getattr(_session, 'plane_node_table', None) or []
            _r = int(round_num or 0)
            if _table and 1 <= _r <= len(_table):
                return str(_table[_r - 1])
        except Exception:   # noqa: BLE001  best-effort 兜底
            pass
        return None

    # ===== 主节点(flat 分类;单元作用域预算 = UNKNOWN_BAIL_N)=====

    @operation_node(name='战斗等待', is_start_node=True, node_max_retry_times=400)
    def wait(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # ③出口 B:团灭终局链终点 = 回到大厅(「返回货币战争」落点)→
        # terminal 交回主循环 3c 收口(runs summary/分配器/存档在彼处,遥测
        # 连续性红线:收口点不随 op 化迁移)。
        if self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南',
                                   crop_first=False).is_success:
            log.info('[cw-bwait] 终局分叉:已回大厅 → terminal_lobby(交整局退出收口)')
            return self.round_success('terminal_lobby')

        # ③出口 A:完成判据白名单任一命中 → 交回循环分发
        if self._hit_completion_anchor(screen):
            log.info('[cw-bwait] 完成判据白名单命中 → 交回循环分发')
            return self.round_success('back_to_loop')

        # ②段:挑战成功结算(读点 → 继续挑战;#25 读点前等 1.5s)
        if self.round_by_find_area(screen, '货币战争-结算', '按钮-继续挑战').is_success:
            self._unknown_streak = 0
            log.info('[cw-bwait][battle_end] 结算屏首见(战斗结束锚点)')
            from sr_od.application.currency_war.operations.settle_collect_hooks import (
                settle_frame_collect,
            )
            settle_frame_collect(screen)
            # #25 用户裁定:按钮出现后结算数据 ~1.5s 才渲染完,读点前等 1.5s
            # + 重截(交接文件 REAL_MACHINE_EFFICIENCY_HANDOFF.md damage 0/15
            # 事故时序根因);采集钩子仍抓首见帧(时序价值在动画帧)。
            time.sleep(1.5)
            screen = self.screenshot()
            self._record_round_outcome(screen)
            # C-1:新结算帧才计数(点击不生效循环不虚增 rounds_done)
            _fp = tuple(sorted((r.data, r.y) for r in
                               self.ctx.ocr_service.get_ocr_result_list(
                                   image=screen, rect=None, crop_first=False)))
            if self._st.last_settle_fp != _fp:
                self._st.rounds_done += 1
                self._st.last_settle_fp = _fp
            time.sleep(0.2)
            if self.round_by_find_and_click_area(
                    self.screenshot(), '货币战争-结算', '按钮-继续挑战',
                    success_wait=1).is_success:
                # 备战相位机复位(结算点 = 新备战相位入口;W971 P3b 平移语义)
                if self.ctx.cw_match is not None:
                    _ps = self.ctx.cw_match.session
                    if _ps.prep_phase or _ps.prep_phase_retry or _ps.defer_count:
                        _ps.prep_phase = 0
                        _ps.prep_phase_retry = 0
                        _ps.defer_count = 0
                        log.info('[cw-bwait] 新备战相位(结算点)→ 相位机复位')
                # M39:停留 ≥3 轮 = 点击未生效 → 长按兜底推进 + 留证观察
                self._st.settle_stay += 1
                if self._st.settle_stay >= BattleWaitOp.SETTLE_STAY_LONG_PRESS:
                    log.info('[cw-bwait] 结算屏停留 %s 轮(点击未生效)→ 长按 '
                             '(960,898) 兜底推进', self._st.settle_stay)
                    self.ctx.controller.click(
                        BattleWaitOp.SETTLEMENT_NEXT, press_time=0.5)
                    self.park_cursor(after_wait=0.1)
                    self._st.settle_stay = 0
                return self.round_wait(wait=1.0)
            return self.round_wait(wait=1.0)
        self._st.settle_stay = 0   # 离开结算屏重置(随迁)

        # ①段:失败结算页(分支 1f 随迁:模板组合门 + 进度符号闩 + 面板延迟门
        # + 页1 三项暂存 + 败局补录 + 翻页/点空白)
        _1f_tpl_hit = (
            self.round_by_find_area(screen, '货币战争-结算-失败', '标识-挑战进度',
                                    crop_first=False).is_success
            and self.round_by_find_area(screen, '货币战争-结算-失败', '标识-挑战结束',
                                        crop_first=False).is_success
            and not self.round_by_find_area(
                screen, '货币战争-结算', '按钮-继续挑战', crop_first=False).is_success)
        _1f_items: list | None = None
        _1f_sign: str | None = None
        if _1f_tpl_hit:
            try:
                _1f_items = self.ctx.ocr_service.get_ocr_result_list(
                    image=screen, rect=None, color_range=None, crop_first=False)
                _1f_sign = settle_page1_progress_sign([r.data for r in _1f_items])
            except Exception as e:  # noqa: BLE001  判定失败按漏读处理(fail-open)
                log.warning('[cw-bwait] 结算页1 进度符号判定失败: %s', e)
                _1f_items = None
        if _1f_tpl_hit and _1f_sign != 'pos':
            self._unknown_streak = 0
            if _1f_sign == 'neg':
                self._st.saw_defeat_settlement = True
            from sr_od.application.currency_war.operations.settle_collect_hooks import (
                settle_frame_collect,
            )
            settle_frame_collect(screen)
            # 面板渲染延迟门(SETTLE_PANEL_WAIT_S;1f 是失败页主通道)
            _pnl = read_settle_damage_breakdown(self.ctx, screen)
            if (self.round_by_ocr(screen, '点击空白加速').is_success
                    and not _pnl['visible']):
                _now = time.monotonic()
                if self._st.settle_p1_ts is None:
                    self._st.settle_p1_ts = _now
                if _now - self._st.settle_p1_ts < BattleWaitOp.SETTLE_PANEL_WAIT_S:
                    return self.round_wait(wait=0.5)
            self._st.settle_p1_ts = None
            if _1f_sign is None:
                self._defeat_latch_by_secondary(_pnl)
            # 页1 三项遥测暂存(DD-006;填充率后帧覆盖语义随迁)
            try:
                _on_p1_1f = _1f_items is not None and any(
                    '点击空白加速' in (r.data or '') for r in _1f_items)
                if _1f_items is not None:
                    _pg1f = parse_settlement_progress([r.data for r in _1f_items])
                    if _pg1f is not None:
                        self._st.settle_page1_progress = _pg1f
                _fr_1f = parse_progress_fill_ratio(screen) if _on_p1_1f else None
                _st_1f = self._st.settle_page1_settle or {}
                for _k, _v in (('damage_base', _pnl['damage_base']),
                               ('damage_unfinished_progress',
                                _pnl['damage_unfinished_progress'])):
                    if _st_1f.get(_k) is None and _v is not None:
                        _st_1f[_k] = _v
                if _pnl['visible']:
                    _st_1f['damage_breakdown_visible'] = True
                if _fr_1f is not None:
                    _st_1f['progress_fill_ratio'] = _fr_1f
                self._st.settle_page1_settle = _st_1f
            except Exception as e:  # noqa: BLE001  暂存 best-effort
                log.warning('[cw-bwait] 结算页1(1f)三项暂存失败(不阻塞): %s', e)
            _pre_fp = (tuple(sorted((r.data, r.y) for r in _1f_items))
                       if _1f_items is not None else None)
            self._record_loss_page(screen, pre_fp=_pre_fp)
            for _btn in ('前往结算', '下一页', '下一步', '返回货币战争'):
                if self.round_by_ocr(screen, _btn, lcs_percent=0.8).is_success:
                    self.ctx.controller.click(BattleWaitOp.SETTLEMENT_NEXT)
                    self.park_cursor(after_wait=0.1)
                    return self.round_wait(wait=1)
            self.ctx.controller.click(BattleWaitOp.BLANK.center)
            self.park_cursor(after_wait=0.1)
            return self.round_wait(wait=1)

        # ②段:点空白加速(结算页1 动画帧/强敌来袭横幅;分支 2 随迁)
        _accel_hit = self.round_by_ocr(screen, '点击空白加速')
        if _accel_hit.is_success:
            self._unknown_streak = 0
            from sr_od.application.currency_war.operations.settle_collect_hooks import (
                settle_frame_collect,
            )
            settle_frame_collect(screen)
            try:
                _texts1 = [r.data for r in self.ctx.ocr_service.get_ocr_result_list(
                    image=screen, rect=None, crop_first=False)]
                _pg1 = parse_settlement_progress(_texts1)
                if _pg1 is not None:
                    self._st.settle_page1_progress = _pg1
            except Exception as e:   # noqa: BLE001  暂存 best-effort
                log.warning('[cw-bwait] 结算页1 progress 暂存失败(不阻塞): %s', e)
            _panel_now = None
            try:
                _panel_now = read_settle_damage_breakdown(self.ctx, screen)
                _fr = parse_progress_fill_ratio(screen)
                _stash = self._st.settle_page1_settle or {}
                for _k, _v in (('damage_base', _panel_now['damage_base']),
                               ('damage_unfinished_progress',
                                _panel_now['damage_unfinished_progress'])):
                    if _stash.get(_k) is None and _v is not None:
                        _stash[_k] = _v
                if _panel_now['visible']:
                    _stash['damage_breakdown_visible'] = True
                if _fr is not None:
                    _stash['progress_fill_ratio'] = _fr
                self._st.settle_page1_settle = _stash
            except Exception as e:   # noqa: BLE001  暂存 best-effort
                log.warning('[cw-bwait] 结算页1 三项暂存失败(不阻塞): %s', e)
            if _accel_hit.is_success and not (
                    _panel_now is not None and _panel_now['visible']):
                _now = time.monotonic()
                if self._st.settle_p1_ts is None:
                    self._st.settle_p1_ts = _now
                if _now - self._st.settle_p1_ts < BattleWaitOp.SETTLE_PANEL_WAIT_S:
                    return self.round_wait(wait=0.5)
            self._st.settle_p1_ts = None
            self.ctx.controller.click(BattleWaitOp.BLANK.center)
            return self.round_wait(wait=0.8)

        # ②段:前往结算链(分支 3b 随迁:轮败/位面结束/团灭多页 → 逐页点进;
        # 「前往结算」帧补 outcome 行,「挑战失败」帧 hp=0 补录置闩)
        for btn in ('前往结算', '下一页', '下一步', '返回货币战争'):
            if self.round_by_ocr(screen, btn, lcs_percent=0.8).is_success:
                self._unknown_streak = 0
                if btn == '前往结算':
                    _fp = tuple(sorted((r.data, r.y) for r in
                                       self.ctx.ocr_service.get_ocr_result_list(
                                           image=screen, rect=None, crop_first=False)))
                    if self._st.last_loss_fp != _fp:
                        self._st.last_loss_fp = _fp
                        self._record_round_outcome(screen)
                if btn == '下一步' and self.round_by_ocr(screen, '挑战失败').is_success:
                    self._st.last_outcome_hp = 0
                    self._st.saw_defeat_settlement = True
                    log.info('[cw-bwait] 战败结算屏 → hp=0 补录 outcomes 真值源')
                from sr_od.application.currency_war.operations.settle_collect_hooks import (
                    settle_frame_collect,
                )
                settle_frame_collect(screen)
                self.ctx.controller.click(BattleWaitOp.SETTLEMENT_NEXT)
                self.park_cursor(after_wait=0.1)
                return self.round_wait(wait=1)

        # ①段:战斗/过场屏(总伤害/数据统计;分支 6 随迁)→ 点空白推进
        if (self.round_by_ocr(screen, '总伤害').is_success
                or self.round_by_find_area(screen, '货币战争-结算', '标识-数据统计').is_success):
            self._unknown_streak = 0
            self.ctx.controller.click(BattleWaitOp.BLANK.center)
            return self.round_wait(wait=1.0)

        # ①段:等待结算画面出现。战斗进行中 = 合法静止(ADR-0250 宽限);
        # 自动战斗检测消费点(见 _in_battle_grace 注,本批不做)。
        if self._in_battle_grace(time.monotonic()):
            return self.round_wait(wait=2)
        # 节点作用域预算:宽限外连续未知帧 → 留证 + bail 交主循环未知画面分支
        # (W971 05-battle §1 超时兜底;不停机——兜底链裁决权留外循环)。
        self._unknown_streak += 1
        if self._unknown_streak >= BattleWaitOp.UNKNOWN_BAIL_N:
            try:
                _shot = self.save_screenshot(prefix='battle_wait_bail')
                _ev = (get_project_root() / '.debug' / 'temp' / 'currency_war'
                       / 'battle_wait_bail.flag')
                _ev.parent.mkdir(parents=True, exist_ok=True)
                _ev.write_text(
                    f'[BATTLE-WAIT-BAIL] 战斗等待 op 连续 {self._unknown_streak} '
                    f'轮未识别 → bail 交主循环兜底链(05-battle §1 超时兜底;留证)\n'
                    f'补判据的依据:本截图即卡点帧。处理:建档/加分支后删本 flag。\n'
                    f'shot={_shot}', encoding='utf-8')
                log.warning('[cw!][bwait] 连续 %s 轮未识别 → bail(留证 '
                            'battle_wait_bail.flag, shot=%s)',
                            self._unknown_streak, _shot)
            except Exception as e:  # noqa: BLE001  留证失败不阻塞 bail
                log.warning('[cw-bwait] bail 留证失败: %s', e)
            return self.round_fail('战斗等待连续未识别,bail 交主循环兜底')
        return self.round_wait(wait=1.5)
