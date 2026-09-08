"""遥测采集:TelemetryRecorder 与 record_* 记录 API(自 cw_telemetry 拆出,分包期6)。"""

from __future__ import annotations

import contextlib
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_observe import (
    DEFAULT_REPLAY_DIR,
    stage_pending_strategy_pick,
)
from sr_od.application.currency_war.kernel.cw_state import (
    Action,
    GameState,
    bench_occupied,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
    SEVERITY_L2_RECORD,
)

# 符号解耦(处死计划批 0):序列化权威副本迁 knowledge/cw_serialize,
# 不再依赖 kernel/cw_intention(死刑判据文件)
from sr_od.application.currency_war.knowledge.cw_serialize import _to_jsonable
from sr_od.application.currency_war.sim.ledger_hooks import (
    _regenerate_delta_pool_after_run,
)
from sr_od.application.currency_war.telemetry import state as _telstate
from sr_od.application.currency_war.telemetry.defects import bypass_exec_event_to_defect
from sr_od.application.currency_war.telemetry.schema import (
    DecisionTrace,
    DefectRecord,
    ExecEvent,
    ExogenousEvent,
    OutcomeRecord,
    RunSummary,
    SpendUnitRecord,
    append_jsonl,
    p1_pair_label,
    rho_shop_obs,
    salvageable_1star_value,
    serialize_action,
    serialize_state,
)
from sr_od.application.currency_war.telemetry.state import (
    _buffer_briefing_row,
    _consume_unit_exec_facts,
    _consume_unit_gold_close,
)
from sr_od.application.currency_war.telemetry.version_stamp import (
    current_version_stamp,
)

# ===== TelemetryRecorder(写 JSONL;门控)=====


class TelemetryRecorder:
    """三路 JSONL 采集器。enabled=False 时全 no-op(生产默认关)。

    用法(阶段 4-5 OCR 接线后,在 cw_loop 关键决策点调):
        rec = TelemetryRecorder(replay_dir, enabled=config.debug_telemetry)
        rec.start_run(run_id, difficulty)
        # 每回合:
        rec.record_decision(run_id, difficulty, state, target, scores, breakdown, actions)
        # 战斗后:
        rec.record_outcome(run_id, outcome)
        # 局终:
        rec.record_run_summary(run_id, difficulty, "win", plane_reached=3, ...)
    """

    def __init__(self, replay_dir: Path | str = DEFAULT_REPLAY_DIR, enabled: bool = False) -> None:
        self.replay_dir: Path = Path(replay_dir)
        self.enabled: bool = enabled
        # 内存累积(便于 record_run_summary 取 gold 轨迹 / comps;不依赖读回文件)
        self._gold_trajectory: dict[str, list[int]] = {}
        self._comms: dict[str, list[str]] = {}
        self._difficulty: dict[str, str] = {}
        # r363(审计 P1-7):gold 采样的回合去重键(见 record_decision)
        self._gold_last_key: tuple | None = None

    def _path(self, name: str) -> Path:
        return self.replay_dir / name

    def _append(self, name: str, payload: dict[str, Any]) -> None:
        """append 一行 JSON(name.jsonl)。enabled=False 时 no-op。"""
        if not self.enabled:
            return
        append_jsonl(self.replay_dir / name, payload)

    def start_run(self, run_id: str, difficulty: str) -> None:
        """登记一次 run(difficulty 记录,便于后续 summary)。"""
        if not self.enabled:
            return
        self._difficulty[run_id] = difficulty
        self._gold_trajectory.setdefault(run_id, [])
        self._comms.setdefault(run_id, [])

    def record_decision(self, run_id: str, difficulty: str, state: GameState,
                        target_comp: str, candidate_scores: dict[str, float],
                        eval_breakdown: dict[str, float], actions: list[Action],
                        extra: dict[str, Any] | None = None,
                        gold_point: bool = True) -> None:
        """记一条决策迹(decisions.jsonl)。target_comp='' 表示 reactive 无 target。

        extra(strategy/05 live 观测):dp_posture/active_strategies/ledger_fingerprint
        等扩容字段(便捷函数自动填;直接调方可传 None 走旧 schema)。
        gold_point(r68 review):是否作为 ``gold_trajectory`` 采样点 —— 语义是**每回合**
        gold(经济复盘),每回合一采样;CwScreenPrep 逐步记录(_record_step)传 False
        防每回合混入 N 条步进值拉歪轨迹。
        """
        # hp None 化(W823,ADR-0491):对账层已不再产 100 兜底——无真值帧
        # state.hp 本身即 None,直通写入即可(r1 特例臂退役);沿用/结算/
        # 真读帧的值照旧。sim 帧恒真读,不受影响。
        _hp_out: int | None = state.hp
        trace = DecisionTrace(
            ts=datetime.now().isoformat(timespec="seconds"),
            run_id=run_id, difficulty=difficulty,
            round_num=state.round_num, plane=state.plane,
            state=serialize_state(state),
            target_comp=target_comp,
            candidate_scores=dict(candidate_scores),
            eval_breakdown=dict(eval_breakdown),
            actions=[serialize_action(a) for a in actions],
            hp=_hp_out, hp_readable=bool(getattr(state, 'hp_readable', True)), gold=state.gold,
            gold_readable=bool(getattr(state, 'gold_readable', True)),   # ADR-0282
            level_readable=bool(getattr(state, 'level_readable', True)),  # level 保真位透传(False=启发式兜底帧)
        )
        if extra:
            trace.active_strategies = list(extra.get('active_strategies', []))
            # dp_posture 双契约容错(r620 自动附 dict / 迁移审计 w119(git 历史) shop.py 附 str;
            # 2026-08-26 run13 实机:dict(str) 对 str 炸 ValueError——统一收窄到
            # str 契约,dict 值序列化兜底;326 行的 str 赋值是权威契约)
            _dpp_raw = extra.get('dp_posture', '')
            if isinstance(_dpp_raw, dict):
                _dpp_raw = str(_dpp_raw)
            trace.dp_posture = _dpp_raw
            trace.ledger_fingerprint = str(extra.get('ledger_fingerprint', ''))
            # r101 session 态快照(redesign/102 前提改造)
            trace.sess_framework = str(extra.get('sess_framework', ''))
            trace.sess_dual_track = extra.get('sess_dual_track')
            trace.sess_drought = extra.get('sess_drought')
            trace.sess_commit_scores = dict(extra.get('sess_commit_scores', {}))
            trace.sess_active_env = str(extra.get('sess_active_env', ''))
            trace.strategy_id = str(extra.get('strategy_id', ''))
            trace.ev_arm = str(extra.get('ev_arm', ''))
            trace.v2_mode = str(extra.get('v2_mode', ''))
            trace.v2_locked_line = str(extra.get('v2_locked_line', ''))
            trace.v2_bridge = str(extra.get('v2_bridge', ''))
            _v2s = extra.get('sess_v2_state')
            trace.sess_v2_state = list(_v2s) if _v2s else None
            # 迁移审计 w114(git 历史)/ADR-0346 相位影子观测 + ADR-0343 formed_stop 缺口补挂
            # + 迁移审计 w119(git 历史)/ADR-0347 授权依据 trace(dp_posture)
            trace.phase = str(extra.get('phase', ''))
            trace.form_ok = bool(extra.get('form_ok', False))
            trace.form_score = float(extra.get('form_score', 0.0))  # 已退役,历史只读
            trace.b_t = int(extra.get('b_t', 0) or 0)   # form_score 替代披露口径
            trace.formed_stop = bool(extra.get('formed_stop', False))
            trace.dp_posture = str(extra.get('dp_posture', ''))
            trace.piggy_reward = bool(extra.get('piggy_reward', False))
            # 迁移审计 w146(git 历史) v3 意向状态(serialize_intention 产物直传)
            _ist = extra.get('v3_intention')
            trace.v3_intention = _ist if isinstance(_ist, dict) else None
            # `w224_handoff/`/ADR-0399:P2 承接快照(strategy_state_of(session).v3_handoff 透传;
            # 非 dict(None)=未进 P2/缺省,旧 schema 不破坏)。
            # P10④ 口径补齐(挂账落码):handoff.gold(出口金)旁补
            # 「可回收 1★ 值」读端字段——判读防「袋穷板富」误读,两字段
            # 并读判据见 p10-exit-gold-floor.md §④/检验点3。富化只改本行
            # 遥测 dict 副本,不动 strategy_state_of(session).v3_handoff 本体(与 sim
            # SimResult.p2_handoff 的键集差异 = 本字段,读端容忍缺键)。
            # 取值时点 = 本 record 调用时点(decide_prep 之后、动作执行前,
            # deployed/bench 域与 P1 出口同帧;gold 域与 handoff.gold 同轮)。
            _ho = extra.get('handoff')
            if isinstance(_ho, dict):
                _ho = dict(_ho)
                with contextlib.suppress(Exception):   # 观测 best-effort
                    _ho['salvageable_1star_value'] = salvageable_1star_value(state)
            trace.handoff = _ho if isinstance(_ho, dict) else None
            # P1 配方对平铺观测(空 extra 时字段保持默认空串)
            trace.sess_p1_pair = str(extra.get('sess_p1_pair', ''))
            # 补给轮决策行采集:选定快照透传(写入端=RunSupplyNode 合成帧;
            # 非 dict 缺省 None,旧 schema 不破坏)
            _spk = extra.get('supply_pick')
            trace.supply_pick = dict(_spk) if isinstance(_spk, dict) else None
        # 决策时点挂起期望态快照(期望态 infra 遥测批;session 自取 = w603
        # 汇点先例,全部决策面一次覆盖:备战步进行/买牌行/补给合成行/sim 行)。
        # 恒写([] = 无挂起);旧行无此键 = 迁移前数据(读端三态,schema 注)。
        # 离线/无 match 注册 = session None → []。
        with contextlib.suppress(Exception):   # 观测 best-effort
            _em = _telstate._CTX_MATCH_REF[0]
            _esess = getattr(_em, 'session', None) if _em is not None else None
            trace.expected_paths = snapshot_expected_paths(_esess)
        # `w603_telemetry_wiring/` 披露键统一接出(session 自取,extra 通道外的固定尾巴;
        # 缺 match 注册=离线/测试,字段保持 None 缺省)。
        _m = _telstate._CTX_MATCH_REF[0]
        _sess = getattr(_m, 'session', None) if _m is not None else None
        # 刷新触发源分键(g_20260906_021859 起连续两局零产出,接线缺
        # 证实):sim 账本行键 refresh_trigger = 刷新动作 reason 计数
        #(engine_p1 轮内累计);生产端本行自 actions 现算(RefreshShop
        # 已带 reason,如 must_spend_r1_yielded),键语义与 sim 同源、
        # 空 = 本行无刷新动作(非缺写)。只依赖 actions,置于 session
        # 汇点块外(离线/无 match 注册行同样产出)。
        _rt: dict[str, int] = {}
        for _a in actions:
            if type(_a).__name__ == 'RefreshShop':
                _k = str(getattr(_a, 'reason', '') or 'other')
                _rt[_k] = _rt.get(_k, 0) + 1
        trace.refresh_trigger = _rt
        if _sess is not None:
            with contextlib.suppress(Exception):   # 观测 best-effort
                trace.sess_blood_budget_rejects = int(
                    getattr(strategy_state_of(_sess), 'v3_blood_budget_rejects', 0) or 0)
                trace.sess_blood_budget_refresh_rejects = int(
                    getattr(strategy_state_of(_sess), 'v3_blood_budget_refresh_rejects', 0) or 0)
                # 商店波未买牌拒因串(生产端=cw4/shop.shop_unbought_reasons
                # 经 session 汇点;session 汇点先例=w603,全部决策面一次覆盖)
                trace.shop_rejects = dict(
                    getattr(strategy_state_of(_sess), 'cw4_shop_rejects', {}) or {})
                # 末窗终止豁免位透传(sim/checks/segments.terminal_release_bit
                # docstring 声明的实机遥测透传位;写入侧单一源 = 该谓词,
                # 禁复算)。旧「写入面随 v2 退役」缺省在此接回——判读面 =
                # P1 末窗血预算不足带帧是否放行终止,连续缺省零产出恢复。
                with contextlib.suppress(Exception):
                    from sr_od.application.currency_war.sim.checks.segments import (
                        terminal_release_bit as _tr_bit,
                    )
                    _tr_st = getattr(_sess, 'last_state', None)
                    if _tr_st is not None:
                        trace.sess_terminal_release = bool(
                            _tr_bit(_sess, _tr_st))
                # (血预算停手·终止分支 sess_terminal_release 透传已在上方
                #  接回 sim/checks/segments.terminal_release_bit 单一源——
                #  旧 v2 决策位写面退役后本键改挂该谓词,接线批恢复产出;
                #  schema 字段语义不变。)
                # `w611_econ_cycle/` 储备/义务披露(写端 = assembly.
                # _disclose_budget 每 prep 装配帧 + 商店执行回执位 spent/
                # shop 必花域 reason,T-88/ADR-0571;读口 = strategy_state_of
                # 访问函数——状态字段已迁策略器状态对象,读 session 动态属性
                # 恒 miss = 遥测断流(session.md §7.2-2 点名风险形态,
                # ADR-0563 决策-6);sim engine_p1 轮快照 = 读端非写端。
                # default 栈帧无写点 → attr 缺省 None,字段保持 None 语义)
                def _w611_int(attr: str) -> int | None:
                    _v = getattr(strategy_state_of(_sess), attr, None)
                    return None if _v is None else int(_v)
                trace.sess_reserve_cap = _w611_int('v3_reserve_cap')
                trace.sess_reserve_overflow = _w611_int('v3_reserve_overflow')
                trace.sess_release_budget = _w611_int('v3_release_budget')
                _rs = getattr(strategy_state_of(_sess), 'v3_release_reason', None)
                trace.sess_release_reason = None if _rs is None else str(_rs)
                # 实花面(v3_release_spent;写点 = cw_op_buy_cards 执行
                # 回执位,首版只计刷新实花——「宁窄勿虚」收窄申报,扩口径
                # 待裁归 ADR-0571;每轮入口清零,承载 = v3_disclosure_key
                # 键戳):ADR-0503 开臂判据②「危机帧实花分项账非全零」的
                # 生产观测源,记账面(budget)不作兑现证据。
                trace.sess_release_spent = _w611_int('v3_release_spent')
                # P26 备战帧无条件采集(math_proofs P26 双挂账采集批;19 号稿
                # §2.3-4 裁定的另立采集点——每备战决策帧无条件采样,非 D-D
                # 尾部帧计数位):下一节点类型标签 = 位面节点台账同源读链
                # (单一源 = ``cw_state.ledger_node_type``,与 flow 掉血回落
                # 同表;原始 token 不映射,查不到 = '' 不猜)。键面单一源 =
                # schema.P26_PREP_OBS_FIELDS。纯观测零行为:best-effort,
                # 台账缺失/异常 → 字段缺省 None,决策行其余面零漂移。
                # hp 边界(00_framework §3):本钩子不采任何 hp/战力量,
                # L_node 分位口径走既有结算三项遥测授权面离线 join。
                from sr_od.application.currency_war.kernel.cw_state import (
                    ledger_node_type as _p26_lnt,
                )
                _p26_nt = _p26_lnt(_sess, state.plane, state.round_num)
                trace.p26_prep_obs = {'node_type_next': str(_p26_nt or '')}
                # W937 预算-回执契约(ADR-0504):姿态授权未兑现回执透传
                # (extra 键不泛化透传,缺此映射行则 shop 端装配静默丢弃)
                _pu = getattr(strategy_state_of(_sess), 'v3_posture_unfulfilled', None)
                trace.posture_unfulfilled = dict(_pu) if _pu else None
                # (W829 支出门拒因枚举计数 sess_spend_gate_block 透传已随
                #  spend_gate 开关族删除——旧方案清退批,清查报告
                #  OLD_MIX_AUDIT §1.3;v3_sg_block session 键同批删。)
                # (w919 方向重估决策面观测 sess_dir_candidate/switch/
                #  supply_drought 已随兑现链方向侧开关族删除——旧方案清退
                #  批,清查报告 OLD_MIX_AUDIT §1.3;_direction_obs_fields
                #  与 ist.supply_drought 同批删,schema 字段按历史数据
                #  只读口径保留,新数据恒 None。)
                # (位面 2 支出授权 sess_p2_auth_intercept/water 写入面已随
                # 定谳清理删除,ADR-0492;schema 字段按历史数据只读口径保留,
                # 新数据恒 None。)
            _led = getattr(exec_state_of(_sess), 'xp_expect_ledger', None)
            if _led is not None and is_dataclass(_led):
                with contextlib.suppress(Exception):
                    trace.xp_expect_ledger = _to_jsonable(asdict(_led))
        with contextlib.suppress(Exception):
            # (P1 末窗支出降格 trace 字段 p1_downgrade_active 写入面已随
            #  v2 退役链退役——mandate_v1 无对应实现,统一迁移批按底稿
            #  MAP ⓪ A7 退役;schema 字段按历史数据只读口径保留,新数据
            #  恒缺省。)
            pass
        if self.enabled:
            # r363(审计 P1-7:gold_point 只修了一半):调用方(shop 循环
            # 每次迭代)默认 True → 每轮 3-11 个采样拉歪轨迹。改
            # **recorder 内部按 (run_id, plane, round) 去重**——每回合
            # 只收首个 gold_point=True 采样;调用方参数语义保留(显式
            # False 仍全跳)。同轮后续步进值不再进 gold_trajectory。
            if gold_point:
                _gk = (run_id, state.plane, state.round_num)
                if _gk != self._gold_last_key:
                    self._gold_last_key = _gk
                    self._gold_trajectory.setdefault(run_id, []).append(state.gold)
            # _comms 不受 gold_point 连坐(r69 review):gold 采样按回合、target 序列按变化,
            # 语义不同 —— director 步进记录(gold_point=False)产生的换线也要落账,否则
            # 「同节点双 pivot」只记终态 1 次,churn 被记账低估一半。
            if target_comp:
                comms = self._comms.setdefault(run_id, [])
                if not comms or comms[-1] != target_comp:
                    comms.append(target_comp)
        self._append("decisions.jsonl", _to_jsonable(trace))

    def record_outcome(self, run_id: str, outcome, source: str = "",
                       supply_pick: dict[str, Any] | None = None) -> None:
        """记一条观测结果(outcomes.jsonl)。outcome: cw_performance.RoundOutcome。

        r339:自动附战前板面快照(board_before/bench_count,从
        ctx.cw_match.session.last_state 取——板深→胜率模型
        校准数据源;miss 容错,缺省空)。ctx match 经
        set_ctx_match 注册(启动时),record 端无 ctx 参数
        侵入。
        source(迁移审计 w28(git 历史)):行来源标记(''/'recovered'/'synthetic_supply',
        见 OutcomeRecord.source 注)。
        supply_pick(迁移审计 w306(git 历史)):补给选择快照,透传 OutcomeRecord.supply_pick;
        仅 synthetic_supply 行传入。
        """
        _board, _bench = {}, 0
        _bosses = None
        _diff = ''
        _affixes: list[str] = []
        try:
            _m = _telstate._CTX_MATCH_REF[0]
            _sess = getattr(_m, 'session', None) if _m is not None else None
            _st = getattr(_sess, 'last_state', None)
            if _sess is not None:
                # 迁移审计 w253(git 历史):boss 身份/难度/词缀快照(与板深快照同源同容错;迁移审计 w244(git 历史) 数据缺口)。
                # briefing_bosses 元素可为 None(徽章态),保位透传不滤。
                _bb = getattr(_sess, 'briefing_bosses', None)
                if isinstance(_bb, (list, tuple)) and len(_bb) > 0:
                    _bosses = [str(b) if b is not None else None for b in _bb]
                _diff = str(getattr(_sess, 'selected_difficulty', '') or '')
                _ax = getattr(_sess, 'briefing_affixes', None)
                if isinstance(_ax, (list, tuple)):
                    _affixes = [str(a) for a in _ax]
            if _st is not None:
                _board = dict(getattr(_st, 'board', None) or {})
                # ADR-0316:bench 槽位表 len 恒 9,计数=占用数
                _bench = bench_occupied(getattr(_st, 'bench', None) or [])
                # r339c(review B:语义注)——last_state 是**最近一次
                # 备战观察**(结算前最后一读≈战前;P2 后段可能隔一
                # 轮旧值:结算触发在下次备战观察前)。字段名
                # board_before 语义成立,精度=「最近战前观察」。
        except Exception:   # noqa: BLE001  快照 best-effort
            pass
        rec = OutcomeRecord(
            ts=datetime.now().isoformat(timespec="seconds"),
            run_id=run_id,
            round_num=outcome.round_num, plane=outcome.plane,
            node_type=outcome.node_type, comp_tag=outcome.comp_tag,
            intentional_fold=outcome.intentional_fold,
            hp_after=outcome.hp_after, hp_confidence=outcome.hp_confidence,
            enemy_hp_after=outcome.enemy_hp_after,
            damage_dealt=outcome.damage_dealt, killed=outcome.killed,
            progress_delta=outcome.progress_delta,
            streak=outcome.streak,
            # 结算三项遥测透传(docs/develop/currency_war/strategy/05_observation.md §3.1(迭代工作面原稿 SETTLE_OCR_DESIGN §3 落点 2:recorder 字段白名单式
            # 构造,此处是 outcomes.jsonl 新字段的唯一写入口)
            progress_fill_ratio=getattr(outcome, 'progress_fill_ratio', None),
            damage_base=getattr(outcome, 'damage_base', None),
            damage_unfinished_progress=getattr(outcome, 'damage_unfinished_progress', None),
            damage_breakdown_visible=getattr(outcome, 'damage_breakdown_visible', False),
            board_before=_board, bench_count=_bench,
            source=source,
            boss_names=_bosses, selected_difficulty=_diff,
            enemy_affixes=_affixes,
            supply_pick=dict(supply_pick) if supply_pick else None,
        )
        self._append("outcomes.jsonl", _to_jsonable(rec))

    def record_run_summary(self, run_id: str, result: str, plane_reached: int,
                           rounds_survived: int, final_hp: int,
                           pivot_count: int | None = None, notes: str = "") -> None:
        """记一条局终 summary(runs.jsonl)。comms/gold 轨迹从内存累积取。

        pivot_count=None(r68 review)→ 从 ``_comms`` target 序列推导(转移数 = len−1;
        初选不算 pivot,含信号1/3/定型/drought 的一切换线)。旧默认 0 恒假 —— 实测一局 6 换
        而 pivot_count=0,粘性/审判层对 churn 完全失明。
        """
        comms = list(self._comms.get(run_id, []))
        if pivot_count is None:
            pivot_count = max(0, len(comms) - 1)
        summary = RunSummary(
            ts=datetime.now().isoformat(timespec="seconds"),
            run_id=run_id,
            difficulty=self._difficulty.get(run_id, ""),
            result=result, plane_reached=plane_reached, rounds_survived=rounds_survived,
            final_hp=final_hp,
            comps_committed=comms,
            pivot_count=pivot_count,
            gold_trajectory=list(self._gold_trajectory.get(run_id, [])),
            notes=notes,
        )
        # 策略版本戳(match archive 二期②):局终写时点打戳——决策明细语义
        # 随版本解读,戳必须是「跑这局的版本」而非装配时点版本。
        _stamp = current_version_stamp()
        summary.code_commit = _stamp['code_commit']
        summary.registry_fingerprint = _stamp['registry_fingerprint']
        self._append("runs.jsonl", _to_jsonable(summary))
        # 清理内存累积
        self._gold_trajectory.pop(run_id, None)
        self._comms.pop(run_id, None)
        self._difficulty.pop(run_id, None)
        # 迁移审计 w109(git 历史)(ADR-0344):局终→Δ池快照自动再生(runs.jsonl 每新增
        # 一行即触发;管线断 12 小时零报警事故的治本)。best-effort。
        _regenerate_delta_pool_after_run()

    def record_exec_event(self, run_id: str, round_num: int, action_family: str,
                          screen: str, event: str, reason: str = "",
                          retry_count: int = 0) -> None:
        """记执行事件(exec_events.jsonl;27 号能力画像:正在蒸发的失败数据落盘)。

        action_family:动作族(buy/deploy/equip/…);event:fail/blocked/bail;
        reason:原因码(识别 MISS/点击无效/…;实现缺陷 vs 固有难度由消费端分型)。
        """
        rec = ExecEvent(ts=datetime.now().isoformat(timespec="seconds"),
                        run_id=run_id, round_num=round_num,
                        action_family=action_family, screen=screen,
                        event=event, reason=reason, retry_count=retry_count)
        self._append("exec_events.jsonl", _to_jsonable(rec))
        # 统一缺陷台账旁路(纯观测):失败类执行事件同步归一落 defect_ledger
        #(refs 指回本行;调用方零改动,旁路失败不影响本流落盘)
        with contextlib.suppress(Exception):
            bypass_exec_event_to_defect(_to_jsonable(rec))

    def record_exogenous(self, run_id: str, round_num: int, kind: str,
                         detail: str = "",
                         state: GameState | None = None,
                         choice: dict[str, Any] | None = None) -> None:
        """记外生事件(exogenous.jsonl;22 号预案触发频率 + 31 号 journal 外生族)。

        kind:node_enter/popup/briefing/event_choice/level_up(迁移审计 w312(git 历史),见 ExogenousEvent);
        state 给定时记关键字段快照(hp/gold/bench 数——预案 trigger 语义);
        choice(迁移审计 w312(git 历史)):overlay 选项选择快照,仅 kind='event_choice' 行携带。
        """
        snap: dict[str, Any] = {}
        if state is not None:
            snap = {'hp': getattr(state, 'hp', None),
                    'gold': getattr(state, 'gold', None),
                    'level': getattr(state, 'level', None),
                    'plane': getattr(state, 'plane', None),
                    'round_num': getattr(state, 'round_num', None),
                    'bench_count': bench_occupied(getattr(state, 'bench', []) or [])}   # ADR-0316 占用数(r68 review:旧 tracked_bench 字段 GameState 没有(恒 0))
        rec = ExogenousEvent(ts=datetime.now().isoformat(timespec="seconds"),
                             run_id=run_id, round_num=round_num,
                             kind=kind, detail=detail, state_snapshot=snap,
                             choice=choice)
        self._append("exogenous.jsonl", _to_jsonable(rec))

    def record_spend_unit(self, run_id: str, plane: int, round_num: int,
                          unit_seq: int, boundary: str, progressed: bool,
                          duration_s: float, detail: str = "",
                          gold_before: int | None = None,
                          gold_before_trusted: bool = False,
                          gold_close: int | None = None,
                          gold_close_trusted: bool = False,
                          plan_truncated: bool = False,
                          refresh_skipped: str | None = None,
                          refresh_attempted: bool = False,
                          refresh_board_changed: bool | None = None) -> None:
        """记购买单元账框架行(spend_ledger.jsonl;纯观测零行为)。

        字段语义见 SpendUnitRecord;调用方 = cw_screen_prep 的 RunBuyPhase
        执行边界。gold_close 来自 shop.py 关店对拍点暂存(模块级便捷入口
        消费填充;未挂钩的调用路径恒 None,读端记 unknown 不猜)。
        plan_truncated/refresh_* 来自 shop.py 执行循环暂存(同槽模式)。
        """
        rec = SpendUnitRecord(
            ts=datetime.now().isoformat(timespec="seconds"),
            run_id=run_id, plane=plane, round_num=round_num,
            unit_seq=unit_seq, boundary=boundary, progressed=progressed,
            duration_s=round(float(duration_s), 2),
            detail=(detail or '')[:240],
            gold_before=gold_before, gold_before_trusted=gold_before_trusted,
            gold_close=gold_close, gold_close_trusted=gold_close_trusted,
            plan_truncated=plan_truncated, refresh_skipped=refresh_skipped,
            refresh_attempted=refresh_attempted,
            refresh_board_changed=refresh_board_changed)
        self._append("spend_ledger.jsonl", _to_jsonable(rec))

    def record_defect(self, surface: str, kind: str, expected: str,
                      observed: str, *, run_id: str = '', plane: int = 0,
                      round_num: int = 0, unit_seq: int | None = None,
                      gap: float | None = None, severity: str = '',
                      verdict: str = '', shot: str | None = None,
                      refs: list[dict[str, str]] | None = None,
                      reader_source: str = '', note: str = '',
                      confidence: float | None = None) -> None:
        """记一条缺陷台账(defect_ledger.jsonl;纯观测索引层,字段语义见 DefectRecord)。

        severity 空时保守缺省 L2 留证(正经初判走模块级 record_defect,
        那里有分级纯函数与复现计数);evidence.refs 由调用方给原流行定位,
        本方法不复制观测数据。confidence(可空):识别置信度快照,语义见
        DefectRecord.confidence。
        """
        evidence: dict[str, Any] = {'refs': list(refs or [])}
        if shot:
            evidence['shot'] = shot
        rec = DefectRecord(
            ts=datetime.now().isoformat(timespec="seconds"),
            run_id=run_id, plane=plane, round_num=round_num,
            unit_seq=unit_seq, surface=surface, kind=kind,
            expected=str(expected), observed=str(observed),
            gap=gap, severity=severity or SEVERITY_L2_RECORD,
            verdict=verdict, evidence=evidence,
            reader_source=reader_source, note=note,
            confidence=confidence)
        self._append("defect_ledger.jsonl", _to_jsonable(rec))



def snapshot_expected_paths(session) -> list[dict[str, Any]]:
    """决策时点挂起期望态摘要(W971 期望态 infra 遥测批;读 infra 接口,
    本函数不修改期望态本体)。

    exec_state_of(session).expected_state = 未确认条目表(kernel/cw_expected_state.
    ExpectedEntry);摘要 = path/value/produced_by/at_round/kind(kind 供判读
    分型:merge_group=合成链模型错 / tracked=识别缺陷 等,五分类语义见
    cw_expected_state.reconcile_expected)。value 非标量(BuyExpect 载体等)
    str 化防序列化炸;无容器/空表 = []。sim 引擎与生产 decisions 行共用本
    单一源(sim/runner.py 落盘与 recorder.record_decision 同构)。"""
    out: list[dict[str, Any]] = []
    store = getattr(exec_state_of(session), 'expected_state', None) or {}
    for path, e in store.items():
        try:
            v = getattr(e, 'value', None)
            if not isinstance(v, (int, float, bool, str, type(None))):
                v = str(getattr(v, 'summary', None) or v)
            out.append({'path': str(getattr(e, 'path', path) or path),
                        'value': v,
                        'produced_by': str(getattr(e, 'produced_by', '')),
                        'at_round': str(getattr(e, 'at_round', '')),
                        'kind': str(getattr(e, 'kind', ''))})
        except Exception:  # noqa: BLE001  单条目异常不拖垮整行快照
            continue
    return out


def record_decision(state: GameState, target_comp: str,
                    candidate_scores: dict[str, float], eval_breakdown: dict[str, float],
                    actions: list[Action], gold_point: bool = True,
                    extra: dict[str, Any] | None = None) -> None:
    """便捷:用 current_run_id 记一条决策迹。BuyShopCards plan 后调。

    live 观测扩容(strategy/05):自动附影子 DP 姿态(12 号分歧频率数据源)与
    持卡/台账指纹(效果感知解回放对齐)——查表 ~2µs,零成本。
    gold_point:gold_trajectory 采样点开关(每回合一采样;步进记录传 False)。
    extra(r101 session 快照/r112 修复):调用方显式传入的扩容字段(sess_*
    六字段)——**合并**(非覆盖)自动附的 dp_posture/ledger;局30 实证:
    shop.py 传 extra= 时本函数签名没有该参数 → TypeError → 买牌 op 全程
    异常 → 金 3→110 全程闲置,整局报废。教训:便捷函数签名必须与 recorder
    方法对齐。
    """
    if not _telstate._CURRENT_RUN_ID:
        return
    _extra: dict[str, Any] = {}
    try:
        # 预算收权批(ADR-0465):影子姿态改确定性预算核投影(get_node_goal 三档
        # spend_mode 单一供给);台账指纹随 DP 世界模型退役删除(原指纹
        # = DP 求解 memo 键,查表核无求解面,无指纹语义)。
        from sr_od.application.currency_war.kernel.cw_economy import get_node_goal
        ng = get_node_goal(state.plane, state.round_num, gold=state.gold,
                           level=state.level, hp=state.hp,
                           strategies=list(getattr(state, 'active_strategies', []) or []) or None)
        _extra['dp_posture'] = {'spend_mode': getattr(ng, 'spend_mode', ''),
                                'target_level': getattr(ng, 'target_level', None)}
        strategies = list(getattr(state, 'active_strategies', []) or [])
        _extra['active_strategies'] = strategies
    except Exception:   # noqa: BLE001  观测 best-effort
        pass
    if extra:
        _extra.update(extra)   # 调用方显式字段(sess_* 快照)合并在自动字段上
    _telstate.get_recorder().record_decision(_telstate._CURRENT_RUN_ID, _telstate._CURRENT_DIFFICULTY, state,
                                   target_comp, candidate_scores, eval_breakdown, actions,
                                   extra=_extra, gold_point=gold_point)



def record_outcome(outcome, source: str = "",
                   supply_pick: dict[str, Any] | None = None) -> None:
    """便捷:用 current_run_id 记一条观测结果。loop 战斗后调。

    source(迁移审计 w28(git 历史)):行来源标记(''/'recovered'/'synthetic_supply')。
    supply_pick(迁移审计 w306(git 历史)):补给选择快照,仅 synthetic_supply 行传入(透传)。
    """
    if not _telstate._CURRENT_RUN_ID:
        return
    _telstate.get_recorder().record_outcome(_telstate._CURRENT_RUN_ID, outcome, source=source,
                                  supply_pick=supply_pick)



def record_exogenous(round_num: int, kind: str, detail: str = '',
                     state: GameState | None = None,
                     choice: dict[str, Any] | None = None) -> None:
    """便捷:用 current_run_id 记一条外生事件(r1 review#3:此前 cw_loop 调用
    模块级函数但只有类方法 → AttributeError 被吞,exogenous.jsonl 生产侧静默死)。

    注意签名与类方法不同(无 run_id 首参——模块级自动取 current_run_id)。

    `w603_telemetry_wiring/` 简报归属:简报屏在 loop ``__init__``(start_run)**之前**读,此刻
    _CURRENT_RUN_ID 为空(进程首局→行被丢)或指向上局(→行带旧 run_id,ts 却
    落在下局窗口,判读归属滞后)。修法=写入时点带正确归属:live run 存在照写;
    否则 kind='briefing' 行暂存模块槽,start_run 建新 run_id 后以新 id 补写
    (ts 保留采集时点)。其余 kind 维持原 no-op 门(局外事件族不归属下一局,
    防行为面外溢)。
    """
    if kind == 'briefing' and (not _telstate._CURRENT_RUN_ID or _telstate._RUN_CLOSED):
        _buffer_briefing_row(round_num, detail, state)
        return
    if not _telstate._CURRENT_RUN_ID:
        return
    _telstate.get_recorder().record_exogenous(_telstate._CURRENT_RUN_ID, round_num, kind, detail, state,
                                    choice=choice)



def record_event_choice(event: str, options: list | None, pick_idx: int,
                        reason: str = '') -> None:
    """迁移审计 w312(git 历史)(遥测审计 G1):overlay 选项选择族统一落盘(exogenous.jsonl,
    kind='event_choice',结构化载荷在 ExogenousEvent.choice)。

    七个 handler(遭遇/巨星/伙伴/策划事件/命运卜者/装备选卡/祈愿)在
    **选项确认时点**各调一行:此前该族只 log.info 不进账本,「当时提供了
    什么选项、bot 选了哪个、为什么」在遥测上断链(对照:invest 族全量
    落盘、迁移审计 w306(git 历史) supply_pick——证明是漏接不是做不了)。

    参数:
        event: 事件名短码(如 'encounter'/'megastar'),写入 choice['event'];
        options: 候选清单(可序列化元素——str/dict;调用方按自身读端形态给,
                 禁自造第二套包装),None/空=识别失败路径也照记(留证据);
        pick_idx: 实际选择下标(0 基,按调用方 options 序);
        reason: 策略决策依据原文(decide_*.reason / 文本规则描述)。
    round_num 从 ctx match 的 last_state 兜底解析(overlay 时 board 不可读,
    last_state=最近一次备战快照;离线/测试无 match → 0)。run_id 空直接 no-op
    (与 record_exogenous 同门控)。best-effort:观测失败不阻断业务流。
    """
    if not _telstate._CURRENT_RUN_ID:
        return
    round_num = 0
    try:
        _m = _telstate._CTX_MATCH_REF[0]
        _st = getattr(getattr(_m, 'session', None), 'last_state', None)
        if _st is not None:
            round_num = int(getattr(_st, 'round_num', 0) or 0)
    except Exception:   # noqa: BLE001  观测 best-effort
        round_num = 0
    opts = list(options) if options else []
    choice = {'event': str(event),
              'options': opts,
              'n_options': len(opts),
              'pick_idx': int(pick_idx),
              'reason': str(reason or '')}
    _telstate.get_recorder().record_exogenous(
        _telstate._CURRENT_RUN_ID, round_num, 'event_choice',
        detail=f'{event} pick=idx{pick_idx} {reason}', choice=choice)



def record_sell_income(state: GameState, slot: int, char_id: str,
                       gold_before: int | None, gold_after: int | None) -> None:
    """迁移审计 w323(git 历史)(遥测审计 G2):卖牌执行点实收回金落盘(exogenous.jsonl,
    kind='sell_income')。

    生产者 = shop.py SellBench 执行分支(拖拽卖出成功后):gold_before 取
    拖拽前 gold OCR 读数,gold_after 取卖出入账后读数,差值即实收回金。
    为什么不记进 decisions 行的 actions:actions 是执行前 plan 快照,序列化
    时卖出尚未发生;sim 行的 income 字段是计划值,生产行只有执行点能拿到
    实际值。economy 视图(query_economy)按 (plane, round) 聚合本行补
    「卖回」格——此前卖牌收入只能靠 gold 差分倒推,混入利息/连胜金噪声。

    参数:
        state: 卖出时点的备战 GameState(round_num/plane/gold 进快照);
        slot: bench 槽位下标 0-8(ADR-0316,与 SellBench.bench_idx 同坐标系);
        char_id: 被卖角色名(生成期快照,守卫通过的那件);
        gold_before/gold_after: 执行前后 gold OCR 读数;任一读不到(OCR miss,
        stylized 漏读)传 None → gold_delta=None(视图计 0 并标 ? 提示有偏),
        旧数据(无本行)视图回退 actions income 口径,不回归。
    run_id 空直接 no-op(与 record_exogenous 同门控);best-effort 由调用方
    try/except 兜底,观测失败不阻断业务流。
    """
    if not _telstate._CURRENT_RUN_ID:
        return
    delta = ((gold_after - gold_before)
             if (gold_before is not None and gold_after is not None) else None)
    round_num = int(getattr(state, 'round_num', 0) or 0)
    _telstate.get_recorder().record_exogenous(
        _telstate._CURRENT_RUN_ID, round_num, 'sell_income',
        detail=(f'sell slot={slot} {char_id or "?"} '
                f'+{delta if delta is not None else "?"}金'),
        state=state,
        choice={'slot': int(slot), 'char': str(char_id or ''),
                'gold_delta': delta})



def record_modality_gold(node: str, plane: int, round_num: int,
                         gold_before: int | None,
                         gold_after: int | None,
                         detail: str = '') -> None:
    """模态期金变动对账行(exogenous.jsonl, kind='modality_gold';纯观测)。

    - 背景(第9局悬案「金 33→0」复盘立案):商店期外的金变动(遭遇/
      奖励/boss 节点的进账出账)此前无逐笔通道——economy 视图的「收」
      格是决策帧金差分的残差(利息/连胜/卖回/模态全混在一起),残差
      异常时无法下钻到具体节点。本行把模态期的可观测金变动按
      「来源节点 × 轮号 × 前后金」逐笔记账,查询侧 query_gold_flow
      用它分解 economy 残差(口径同源:同一 exogenous 流、同一
      (plane, round) join 键,与 sell_income 行同法)。
    - 生产者 = 模态期金变动可读的操作点。**当前零喂点(ADR-0601 §4
      如实登记缺口)**:唯一历史喂点 cw_op_collect_spheres(奖励球
      收取)已随该 op 下线删除(零调用死代码,合规清查实例 S1/S2;
      职能由分发层 ClickSpheres 动作接管)——'spheres' 分键断喂,模态金
      进账暂回流 economy 残差;补喂点候选 = PrepActionExecutor.
      _click_spheres(收取前后金现读),是否接通属观测面排期裁决,
      不随 op 下线擅自重接。overlay
      事件屏(策划/命运卜者等)金区被覆盖不可读,不设钩——其金效应
      仍留在 economy 残差里,本通道只承诺「有钩处逐笔、无钩处显残差」。
    - 参数:
        node: 来源节点短码(如 'spheres');plane/round_num: 归属轮号
        (调用方自 session.last_state 取,overlay 期 board 不可读的
        兜底口径与 record_event_choice 同);gold_before/gold_after:
        变动前后金读数,任一 miss(OCR 漏)传 None → gold_delta=None
        (读端按不可信分型,不猜)。
    - run_id 空直接 no-op(与 record_exogenous 同门控);best-effort:
    调用方 try/except 兜底,观测失败不阻断业务流。
    """
    if not _telstate._CURRENT_RUN_ID:
        return
    delta = ((gold_after - gold_before)
             if (gold_before is not None and gold_after is not None) else None)
    _telstate.get_recorder().record_exogenous(
        _telstate._CURRENT_RUN_ID, int(round_num), 'modality_gold',
        detail=(f'{node} {delta if delta is not None else "?"}金 '
                f'({gold_before}->{gold_after}){(" " + detail) if detail else ""}'),
        choice={'node': str(node or ''), 'plane': int(plane or 0),
                'gold_before': gold_before, 'gold_after': gold_after,
                'gold_delta': delta})


def record_spend_unit(plane: int, round_num: int, unit_seq: int,
                      boundary: str, progressed: bool, duration_s: float,
                      detail: str = "", gold_before: int | None = None,
                      gold_before_trusted: bool = False) -> None:
    """便捷:用 current_run_id 记购买单元账框架行(spend_ledger.jsonl)。

    生产者 = cw_screen_prep 的 RunBuyPhase 执行边界。run_id 空直接 no-op
    (与 record_exogenous 同门控);best-effort 由调用方 try/except 兜底。
    gold_close 在此消费 shop 关店对拍点的暂存实读金(消费即清;无暂存
    = 该单元 shop 未挂钩/未走到关店对拍段,恒 None 不猜)。
    """
    if not _telstate._CURRENT_RUN_ID:
        return
    _gc, _gc_trusted = _consume_unit_gold_close()
    _exec = _consume_unit_exec_facts()
    _telstate.get_recorder().record_spend_unit(
        _telstate._CURRENT_RUN_ID, plane, round_num, unit_seq, boundary, progressed,
        duration_s, detail=detail, gold_before=gold_before,
        gold_before_trusted=gold_before_trusted,
        gold_close=_gc, gold_close_trusted=_gc_trusted,
        plan_truncated=bool(_exec.get('plan_truncated')),
        refresh_skipped=_exec.get('refresh_skipped'),
        refresh_attempted=bool(_exec.get('refresh_attempted')),
        refresh_board_changed=_exec.get('refresh_board_changed'))



def record_invest_cards(kind: str, cards: list[dict[str, Any]]) -> None:
    """投资策略/环境卡**候选全集 + 效果原文** → invest_cards.jsonl(ADR-0132 采集)。

    cards 元素:{idx, name, x, effect_text, chosen}(每卡一行,带 ts/run_id/kind)。
    效果原文 = 卡面描述区 OCR 按卡分桶拼接 —— 注册表效果的 **ground truth 回流源**
    (ADR-0131 发现 T0 12 条里 8 条描述错,即因无采集;离线对拍本文件校注册表/补 315 长尾)。
    """
    if not _telstate._CURRENT_RUN_ID:
        return
    # `w512_obs_surfaces/`(观测自检设计 §2.9/§5-B6 策略激活态对拍,生产侧):strategy 类
    # 投资卡落盘时暂存「声明选中」的名字,由下一次备战观察构建 state 时消费
    #(cw_observation),对拍 session.active_strategies——选了 X 而持卡里没有
    # X = 写链断或选择落空(原审计缺口:策略误选/漏选无法发现)。槽本体自分包期 4
    # 迁 kernel/cw_observe(obs 消费零直依 telemetry;生产→消费紧邻、消费即清)。
    if kind == 'strategy':
        _chosen = next((c.get('name') for c in cards
                        if isinstance(c, dict) and c.get('chosen')), None)
        if _chosen and _chosen != '?':
            stage_pending_strategy_pick(str(_chosen))
    rec = _telstate.get_recorder()
    ts = datetime.now().isoformat(timespec="seconds")
    for c in cards:
        rec._append("invest_cards.jsonl", {
            "schema_version": 1, "ts": ts, "run_id": _telstate._CURRENT_RUN_ID, "kind": kind, **c,
        })



# —— `w512_obs_surfaces/`:策略激活对拍暂存槽已迁 kernel/cw_observe(分包期 4,
# 消费者 obs 零直依 telemetry;生产者经 stage_pending_strategy_pick 写入)——



def record_shop_snapshot(event: str, shop: list, gold: int,
                         plane: int = 0, round_num: int = 0) -> None:
    """商店牌面快照(shop_snapshots.jsonl;r97;供给复盘的真值源)。

    event:``offer``(进店首见)/ ``refresh``(刷新后新牌面)—— 买牌回合里 bot 会 refresh,
    只记进店帧会丢中间 4-5 波牌 → 「配方件来没来」复盘断章取义(局18:据此误判
    「仙舟 8 轮断供」实为 r2 爻光×3 在店没买)。shop 元素为 ShopCard(或已序列化 dict)。

    w919(R-A 批1):行附 ``rho_obs``(ρ 实测单帧分子;键面=RHO_SHOP_OBS_FIELDS,
    口径见 rho_shop_obs)。pair 取当前意向方向(session 自取;dict/object 两形态
    兼容);采集失败 → rho_obs=None,行照写(静默跳过不炸主链)。
    """
    if not _telstate._CURRENT_RUN_ID:
        return
    _pair = ''
    _rho: dict[str, Any] | None = None
    with contextlib.suppress(Exception):   # 观测 best-effort
        _m = _telstate._CTX_MATCH_REF[0]
        _ist = getattr(getattr(_m, 'session', None), 'v3_intention', None)
        _pair = p1_pair_label(_ist)
    with contextlib.suppress(Exception):   # 观测 best-effort
        _rho = rho_shop_obs(shop, pair=_pair)
    rec = _telstate.get_recorder()
    rec._append("shop_snapshots.jsonl", {
        "schema_version": 1,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "run_id": _telstate._CURRENT_RUN_ID,
        "plane": plane, "round_num": round_num,
        "event": event, "gold": gold,
        "shop": [{k: getattr(c, k, None)
                  for k in ('name', 'faction', 'cost', 'star', 'merge_preview')}
                 for c in shop],
        "rho_obs": _rho,
    })



