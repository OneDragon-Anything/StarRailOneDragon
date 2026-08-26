"""货币战争 决策迹采集(telemetry;纯逻辑,可测,不碰游戏)。

**用户 2026-08-03 要求**:搜集足够数据支持后续策略优化。设计原则(贯彻):**ML 只采集、不主依赖**
—— debug 开关在关键决策点序列化(GameState + eval 特征分解 + 动作 + 下回合观测结果),给人肉眼
复盘 + 留作未来 ML 的 side door。**采集价值耐久(schema 稳定),训练价值版本短命**(V4.4 训的 V4.5 废)。
→ 采集管线现在就建,训练以后再说。永远采集,可能永远不训练。

**事件流三路 JSONL**(append-only,按 run_id+round_num join,标准 event-sourcing):
- ``decisions.jsonl``:每回合决策迹(state 快照 + target_comp + candidate_scores + eval_breakdown + actions)。
- ``outcomes.jsonl``:每回合观测结果(RoundOutcome 双侧)。
- ``runs.jsonl``:每局 summary(difficulty / result / plane_reached / pivots / gold 轨迹)。
  **写端三路径**(result 取值 win/loss/abandoned/stopped,ADR-0335):
  - 3c 回大厅 = 正常终局(win/loss);
  - ``battle_loop.after_operation_done`` 收口 = 停止/超时/异常退出
    (stopped/abandoned,hp/plane/round 取最后已知值);
  - ADR-0273 兜底:``start_run`` 先补 FAIL/崩溃/重启路径漏写的行(source=recovered)。

**schema 稳定**:字段名跨版本不变(``schema_version`` 标版本);数值随版本/实玩变。新增字段加在末尾、
可选,不破坏旧记录。复盘/ML 代码按 (run_id, round_num) join decisions ↔ outcomes。

**门控**:`enabled=False` 时 record 全 no-op(生产默认关,debug/复盘开)。路径默认
``.debug/temp/currency_war/replay/``(不入 git)。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from one_dragon.utils import log_utils  # 67-P1c 指纹哨兵日志
from sr_od.application.currency_war.cw_state import (
    Action,
    GameState,
    bench_occupied,
)

log = log_utils.log

# 默认 replay 目录(项目根 .debug/temp/currency_war/replay/;不入 git)
DEFAULT_REPLAY_DIR: Path = Path(".debug/temp/currency_war/replay")
SCHEMA_VERSION: int = 1   # 决策迹 schema 版本(字段名稳定;改 schema 升版本号)


# ===== 序列化(dataclass → JSON-safe dict)=====

def _to_jsonable(obj: Any) -> Any:
    """dataclass / 基础类型 → JSON 可序列化(递归)。"""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, set):
        return sorted(_to_jsonable(x) for x in obj)
    if isinstance(obj, Path):
        return str(obj)
    return obj


def serialize_state(state: GameState) -> dict[str, Any]:
    """GameState → JSON-safe dict(剔除大且无决策价值的字段由调用方按需;默认全量)。

    ADR-0392:``deployed`` 槽位表 → **紧缩占用序**落遥测(None 空槽剔除)——
    下游视图(rounds/win_features/replay)零迁移,占用数=len 语义不变。
    """
    out = _to_jsonable(state)
    _dep = getattr(state, 'deployed', None)
    if isinstance(_dep, list):
        out['deployed'] = _to_jsonable([d for d in _dep if d is not None])
    return out


def serialize_action(action: Action) -> dict[str, Any]:
    """单 Action → JSON-safe dict(带 type 标签,便于复盘识别)。"""
    d = _to_jsonable(action)
    d["__type__"] = type(action).__name__
    return d


def serialize_intention(ist: Any) -> dict[str, Any] | None:
    """v3 意向状态(IntentionState)→ JSON-safe dict(W146)。

    ADR-0336 后锁定真值在 ``session.v3_intention``,但 decisions 行
    只有恒空的 v1 遗留键(``v2_locked_line``/``v2_mode``)——实机判读
    「锁定时点/锁定目标」不可读,只能日志考古。本序列化把意向状态机
    全量落遥测(W145 锁定目标改过渡配方的实机验证依赖它)。

    - ``None`` = session 无意向状态机(default 栈/未初始化)——与
      「有意向未锁」(dict 且 ``phase='unlocked'``)显式区分,消费方
      不用猜;
    - dict 按字段全量序列化(dataclass fields 遍历,set→sorted list,
      嵌套 LineTrack 同构)——IntentionState 字段演进(如 W145 调整
      锁定语义)时自动跟上,不改本函数。

    **可变容器深拷贝(W194/ADR-0378)**:dict/list 字段值经
    ``_to_jsonable`` 递归拷贝(嵌套 dataclass 走 asdict=深拷贝)——
    ``tracks: dict[str, LineTrack]`` 是**活引用**,旧版直接把引用
    落进账本行,session 后续轮原地改 LineTrack 会污染**已落账的
    早期行**(sim P2 段改写同局 P1 行的 tracks,W193 对比门曾排除
    该字段)。tuple/str 不可变,原样保留(类型不漂移)。

    只读不碰 ``cw_intention``(并行批在改);非 dataclass 输入退 None。
    """
    if not is_dataclass(ist):
        return None
    out: dict[str, Any] = {}
    for f in fields(ist):
        v = getattr(ist, f.name)
        if isinstance(v, set):
            out[f.name] = sorted(v)
        elif is_dataclass(v):
            out[f.name] = _to_jsonable(v)
        elif isinstance(v, (dict, list)):
            # W194/ADR-0378:可变容器深拷贝落账(活引用污染防线,
            # 见 docstring);tuple 不可变不辖(类型不漂移)
            out[f.name] = _to_jsonable(v)
        else:
            out[f.name] = v
    return out


def append_jsonl(path: Path | str, payload: dict[str, Any]) -> None:
    """append 一行 JSON 到指定 .jsonl 文件(ADR-0273:兜底回填/常规写共用,不依赖 recorder 单例)。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


# ===== trace 数据结构(schema 稳定)=====

@dataclass
class DecisionTrace:
    """单回合决策迹(decisions.jsonl 一行)。schema 稳定,新字段末尾追加且可选。"""
    schema_version: int = SCHEMA_VERSION
    ts: str = ""                                  # ISO 时间戳(record 时填)
    run_id: str = ""                              # 一次 run 的 id(调用方传;join key)
    difficulty: str = ""                          # A1..A8(调用方传)
    round_num: int = 0                            # 位面内轮次
    plane: int = 0
    state: dict[str, Any] = field(default_factory=dict)        # GameState 快照
    target_comp: str = ""                         # 选中的 target comp 名
    candidate_scores: dict[str, float] = field(default_factory=dict)  # {comp_name: comp_score}
    eval_breakdown: dict[str, float] = field(default_factory=dict)    # target comp 的特征分解
    actions: list[dict[str, Any]] = field(default_factory=list)       # action plan(每项带 __type__)
    hp: int = 0                                   # 决策时 HP(冗余于 state,便于快速筛)
    hp_readable: bool = True                      # hp 真读到?(False=读不到;ADR-0282:此时 hp=沿用 last_hp_real,开局无真值才是 100 兜底)
    gold: int = 0                                 # 决策时 gold(冗余,便于 gold 轨迹)
    gold_readable: bool = True                    # gold 真读到?(ADR-0282:prep_director「gold 不可信」日志升级为字段,对齐 hp_readable)
    # —— live 观测扩容(strategy/05_observation;全部可选,回放/影子对齐)——
    active_strategies: list[str] = field(default_factory=list)   # 持卡(台账/效果解回放)
    dp_posture: dict[str, Any] = field(default_factory=dict)     # 影子 DP 姿态(tag/level_up/refresh_budget/v)
    ledger_fingerprint: str = ""                  # 台账指纹(效果感知解回放对齐)
    # —— r101 session 态快照(redesign/102 前提改造:回放 harness/快照回归库需要完整
    # 决策输入;缺这些,单帧重放 plan 会系统性偏差——session 态决定 decision_target
    # 走哪条路线/攒息门/定型判定)。全可选,旧记录缺省 None 不破坏 schema。
    sess_framework: str = ""                      # transition_framework(配方路线)
    sess_dual_track: bool | None = None           # 双轨期(定型与否)
    sess_drought: int | None = None               # target_drought(断供计数)
    sess_pivot_cooldown: int | None = None        # pivot_cooldown_until
    sess_commit_scores: dict[str, float] = field(default_factory=dict)  # CommitSignals 累积分
    sess_active_env: str = ""                     # 已选投资环境(portal 偏置源)
    # —— 策略 v2(LineStrategy)字段(r226;redesign §6 遥测扩展:
    # 模式/锁线/桥——AB 对拍与三层置信的数据源)——
    strategy_id: str = ""                          # 本局策略 id(B2:分组键)
    v2_mode: str = ""                             # economy/war(滞回当前模式)
    v2_locked_line: str = ""                      # 锁定线 id(""=未锁)
    v2_bridge: str = ""                           # 当前桥线 id(""=无)
    # r359(回放忠实化,ADR-0231):v2 相位机元组(应急/追赶 latch
    # 全量)——重放 decide_prep 分支忠实还原的缺失件。可选,旧记录
    # 缺省 None;list 形态 = v2_state 元组逐位。
    sess_v2_state: list | None = None
    # —— W114/ADR-0346 相位影子观测(经济循环总模型步①;零消费):
    # phase(FORM/HOARD/SPEND 派生相位)/form_ok(三件套谓词,裁决后
    # 无等级项)/form_score(上场阵容 rung 副指标,∈[0,1])。可选,
    # 旧记录缺省不破坏 schema。
    phase: str = ""
    form_ok: bool = False
    form_score: float = 0.0
    # ADR-0343 成型停手态(层2 写;检查器豁免/判读锚点)——补挂
    # DecisionTrace 字段:shop/prep_director 均已在 extra 传
    # 'formed_stop',但 recorder 映射缺失导致该键被静默丢弃
    # (W114 影子批接线时发现的既有缺口,随批补上;旧记录缺省 False)
    formed_stop: bool = False
    # —— W119/ADR-0347 授权依据 trace(经济循环总模型步②「切授权」):
    # dp_posture=当轮 DP 日程表姿态 tag(存息/升级/D 预算;""=查询
    # 失败/default 栈)。EV 放行值在 decisions 行 log 的 ev_auth 键
    # (arbiter 执行 log)。可选,旧记录缺省不破坏 schema。
    dp_posture: str = ""
    # ADR-0348 ↺:扑满节点识别(过热局 reward 帧;②b 观测/实机建档
    # 数据面——识别≠深花授权)。可选,旧记录缺省 False。
    piggy_reward: bool = False
    # —— W146 v3 意向状态(cw_intention.IntentionState 全量序列化;
    # ADR-0336 后 v2_locked_line/v2_mode 恒空,锁定真值在此)——
    # None=无意向状态机(default 栈);dict 且 phase='unlocked'=有意向
    # 未锁;phase='locked' 时 locked_comp=锁定目标(COMP_LIBRARY 套名)。
    # 可选,旧记录缺省 None 不破坏 schema。
    v3_intention: dict[str, Any] | None = None
    # —— W224/ADR-0399 P2 承接快照(纯观测;plane>=2 本位面首帧
    # decide_prep 入口算一次的七维向量+派生档位,decision_v2.handoff.
    # HandoffSnapshot.as_dict)。None=未进 P2/旧记录;仅 P2 首轮行非空。
    handoff: dict[str, Any] | None = None


@dataclass
class OutcomeRecord:
    """单回合观测结果(outcomes.jsonl 一行)。对应 cw_performance.RoundOutcome + join key。"""
    schema_version: int = SCHEMA_VERSION
    ts: str = ""
    run_id: str = ""
    round_num: int = 0
    plane: int = 0
    node_type: str = ""
    comp_tag: str = ""
    intentional_fold: bool = False
    hp_after: int = 0
    hp_confidence: float = 1.0
    enemy_hp_after: int | None = None
    damage_dealt: int | None = None
    killed: bool | None = None
    progress_delta: int | None = None   # 结算屏「挑战进度 ±N」(2026-08-18:胜负+扣血真值,输轮也记)
    streak: int | None = None           # 连胜/连败带符号(r68:RoundOutcome 有此字段但序列化丢弃 → 补)
    # —— r339 板深快照(板深→胜率模型校准数据源;复盘发现 sim
    # 天花板 8%>=60 vs 实机 3/3 达标的矛盾根因=模型缺板深机制,
    # 而逐轮板面×掉血对就是拟合数据):战前板面+上阵深度。
    board_before: dict[str, int] = field(default_factory=dict)   # 战前 {阵营:人数}
    bench_count: int = 0               # 战前 bench 数(板深第二维)
    # —— W28(行来源标记,镜像 RunSummary.source/ADR-0273 惯例):''=结算屏真值行;
    # 'recovered'=relaunch 残留结算屏(启动宽限内首见,round_num 已按屏面「X-Y」
    # 尽力校正,训练侧可剔);'synthetic_supply'=补给节点合成行(无结算屏节点的
    # 遥测补行,hp 用 last_state 快照非屏面真值)。
    source: str = ""


@dataclass
class RunSummary:
    """单局 summary(runs.jsonl 一行)。"""
    schema_version: int = SCHEMA_VERSION
    ts: str = ""
    run_id: str = ""
    difficulty: str = ""
    result: str = ""                # "win" / "loss" / "abandoned" / "stopped"(W75:停止路径,ADR-0335)
    plane_reached: int = 0          # 到达的最高位面
    rounds_survived: int = 0
    final_hp: int = 0
    comps_committed: list[str] = field(default_factory=list)   # commit 过的 comp 名序列(含 pivot)
    pivot_count: int = 0
    gold_trajectory: list[int] = field(default_factory=list)   # 每回合 gold(经济复盘)
    notes: str = ""
    # —— live 观测扩容(strategy/05_observation)——
    death_window: str = ""          # 39 号免费窗口登记:""=竞争局 / "must_die" / "free"(局终判定)
    strategies_held: list[str] = field(default_factory=list)   # 终局持卡(台账回放)
    # —— ADR-0273(批⑧ F2):行来源标记。''=正常终局/stop 路径写;'recovered'=
    # 兜底回填(从 outcomes/decisions 重算,盖 FAIL/崩溃/重启杀局路径)。
    source: str = ""


@dataclass
class ExecEvent:
    """执行事件(exec_events.jsonl;27 号能力画像数据源,2026-08-17)。

    prep_director 的 _fail_counts/_blocked/bail 原因本来局终即弃——落盘后跨局聚合
    出「动作族×画面×失败率」画像(能力层:实现缺陷 vs 固有难度分型)。
    """
    ts: str = ""
    run_id: str = ""
    round_num: int = 0
    action_family: str = ""         # 动作族(buy/deploy/equip/sell/levelup/refresh/...)
    screen: str = ""                # 画面/时相桶(battle_prep/supply/encounter/...)
    event: str = ""                 # "fail" / "blocked" / "bail" / "success_uncharged"
    reason: str = ""                # 原因码(识别 MISS/点击无效/状态不符/…)
    retry_count: int = 0


@dataclass
class ExogenousEvent:
    """外生事件(exogenous.jsonl;22 号预案触发频率 + 31 号 journal 外生族,2026-08-17)。

    节点类型转换/弹窗/简报/高利害条件触发——预案层的 trigger 频率统计与
    journal 常开的语料基础。
    """
    ts: str = ""
    run_id: str = ""
    round_num: int = 0
    kind: str = ""                  # node_enter/popup/briefing(r378b 收敛:仅这三种有生产者;
    # condition_trigger/user_action 从 schema 删——测量链 review B1 实锤零
    # 写入点,声明的 kind 无生产者=消费端等死链(node_type 同型病))
    detail: str = ""
    state_snapshot: dict[str, Any] = field(default_factory=dict)   # 触发时的关键字段(hp/gold/bench…)


# ===== TelemetryRecorder(写 JSONL;门控)=====

class TelemetryRecorder:
    """三路 JSONL 采集器。enabled=False 时全 no-op(生产默认关)。

    用法(阶段 4-5 OCR 接线后,在 battle_loop 关键决策点调):
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
        gold(经济复盘),每回合一采样;PrepDirector 逐步记录(_record_step)传 False
        防每回合混入 N 条步进值拉歪轨迹。
        """
        trace = DecisionTrace(
            ts=datetime.now().isoformat(timespec="seconds"),
            run_id=run_id, difficulty=difficulty,
            round_num=state.round_num, plane=state.plane,
            state=serialize_state(state),
            target_comp=target_comp,
            candidate_scores=dict(candidate_scores),
            eval_breakdown=dict(eval_breakdown),
            actions=[serialize_action(a) for a in actions],
            hp=state.hp, hp_readable=bool(getattr(state, 'hp_readable', True)), gold=state.gold,
            gold_readable=bool(getattr(state, 'gold_readable', True)),   # ADR-0282
        )
        if extra:
            trace.active_strategies = list(extra.get('active_strategies', []))
            # dp_posture 双契约容错(r620 自动附 dict / W119 shop.py 附 str;
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
            trace.sess_pivot_cooldown = extra.get('sess_pivot_cooldown')
            trace.sess_commit_scores = dict(extra.get('sess_commit_scores', {}))
            trace.sess_active_env = str(extra.get('sess_active_env', ''))
            trace.strategy_id = str(extra.get('strategy_id', ''))
            trace.v2_mode = str(extra.get('v2_mode', ''))
            trace.v2_locked_line = str(extra.get('v2_locked_line', ''))
            trace.v2_bridge = str(extra.get('v2_bridge', ''))
            _v2s = extra.get('sess_v2_state')
            trace.sess_v2_state = list(_v2s) if _v2s else None
            # W114/ADR-0346 相位影子观测 + ADR-0343 formed_stop 缺口补挂
            # + W119/ADR-0347 授权依据 trace(dp_posture)
            trace.phase = str(extra.get('phase', ''))
            trace.form_ok = bool(extra.get('form_ok', False))
            trace.form_score = float(extra.get('form_score', 0.0))
            trace.formed_stop = bool(extra.get('formed_stop', False))
            trace.dp_posture = str(extra.get('dp_posture', ''))
            trace.piggy_reward = bool(extra.get('piggy_reward', False))
            # W146 v3 意向状态(serialize_intention 产物直传)
            _ist = extra.get('v3_intention')
            trace.v3_intention = _ist if isinstance(_ist, dict) else None
            # W224/ADR-0399:P2 承接快照(session.v3_handoff 透传;
            # 非 dict(None)=未进 P2/缺省,旧 schema 不破坏)
            _ho = extra.get('handoff')
            trace.handoff = _ho if isinstance(_ho, dict) else None
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

    def record_outcome(self, run_id: str, outcome, source: str = "") -> None:
        """记一条观测结果(outcomes.jsonl)。outcome: cw_performance.RoundOutcome。

        r339:自动附战前板面快照(board_before/bench_count,从
        ctx.cw_match.session.last_state 取——板深→胜率模型
        校准数据源;miss 容错,缺省空)。ctx match 经
        set_ctx_match 注册(启动时),record 端无 ctx 参数
        侵入。
        source(W28):行来源标记(''/'recovered'/'synthetic_supply',
        见 OutcomeRecord.source 注)。
        """
        _board, _bench = {}, 0
        try:
            _m = _CTX_MATCH_REF[0]
            _st = getattr(getattr(_m, 'session', None), 'last_state', None) \
                if _m is not None else None
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
            board_before=_board, bench_count=_bench,
            source=source,
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
        self._append("runs.jsonl", _to_jsonable(summary))
        # 清理内存累积
        self._gold_trajectory.pop(run_id, None)
        self._comms.pop(run_id, None)
        self._difficulty.pop(run_id, None)
        # W109(ADR-0344):局终→Δ池快照自动再生(runs.jsonl 每新增
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

    def record_exogenous(self, run_id: str, round_num: int, kind: str,
                         detail: str = "",
                         state: GameState | None = None) -> None:
        """记外生事件(exogenous.jsonl;22 号预案触发频率 + 31 号 journal 外生族)。

        kind:node_enter/popup/briefing(r378b 收敛,见 ExogenousRecord);
        state 给定时记关键字段快照(hp/gold/bench 数——预案 trigger 语义)。
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
                             kind=kind, detail=detail, state_snapshot=snap)
        self._append("exogenous.jsonl", _to_jsonable(rec))


# ===== 模块级单例 + run_id 跟踪(ops 不改签名即可采集)=====
# telemetry 是横切关注点,用模块级 recorder + current_run_id,避免给 BuyShopCards / loop
# 线程传参。CurrencyWarRunLoop 在 __init__ 调 start_run(生成 run_id),BuyShopCards 用
# current_run_id() 取,loop 在战斗后 record_outcome、局终 record_run_summary。
# 默认 enabled=True(用户 2026-08-03 要数据调优;写 .debug/ 不入 git,I/O <1ms 不影响备战实时)。
_RECORDER: TelemetryRecorder | None = None
_CURRENT_RUN_ID: str = ""
_CURRENT_DIFFICULTY: str = ""
# r339:ctx.cw_match 弱引用槽(record_outcome 板深快照源;
# battle_loop 启动 run 时注册,None=离线/测试容错)
_CTX_MATCH_REF: list = [None]


def set_ctx_match(match) -> None:
    """注册当前 ctx.cw_match(板深快照源;run 边界换新)。"""
    _CTX_MATCH_REF[0] = match


def get_recorder() -> TelemetryRecorder:
    """模块级 recorder 单例(默认 enabled,写 .debug/temp/currency_war/replay/)。"""
    global _RECORDER
    if _RECORDER is None:
        _RECORDER = TelemetryRecorder(enabled=True)
    return _RECORDER


def start_run(difficulty: str = "") -> str:
    """开始一次 run:生成 run_id(时间戳)+ start_run。返回 run_id。loop __init__ 调。

    ADR-0273:开局先补上一局(们)缺的 summary 行 —— FAIL/崩溃/重启杀局路径
    不走 3c/stop 收口,此处在下一局起点从 outcomes/decisions 重算兜底(幂等)。
    """
    global _CURRENT_RUN_ID, _CURRENT_DIFFICULTY
    try:
        recover_dangling_run_summaries()
    except Exception as e:   # noqa: BLE001  兜底 best-effort,不阻塞开局
        log.warning('[cw][telemetry] summary 兜底回填失败(不阻塞开局): %s', e)
    _CURRENT_RUN_ID = datetime.now().strftime('run_%Y%m%d_%H%M%S')
    _CURRENT_DIFFICULTY = difficulty
    get_recorder().start_run(_CURRENT_RUN_ID, difficulty)
    return _CURRENT_RUN_ID


def current_run_id() -> str:
    return _CURRENT_RUN_ID


# ===== W103 件1/件2(ADR-0342):策略失活检测 =====
# 病灶实录(W98 两局 run_20260825_003757/011957):崩溃恢复局 decisions
# 全行 strategy_id='' 且零策略动作族(BuyCard/SellBench/CompTransaction/
# LevelUp 除 op 层兜底外),观测层活着(EnsureShopClosed 行照写)、店里
# 明明读到目标件——决策层整局未点火,兜底打满 40min 产出 0 买垃圾局。

_STRATEGY_LIVE_CACHE: dict[tuple[str, float], set[tuple[int, int]]] = {}


def _strategy_live_rounds(run_id: str) -> set[tuple[int, int]]:
    """该 run 中「存在带非空 strategy_id 决策行」的 (plane, round) 集。

    decisions.jsonl 按 mtime 缓存(每个写入窗口只全文扫一次;跨 run 追加
    文件随局数线性增长,逐 round 查询不该每次全扫)。
    """
    path = get_recorder().replay_dir / 'decisions.jsonl'
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return set()
    ck = (run_id, mtime)
    if ck in _STRATEGY_LIVE_CACHE:
        return _STRATEGY_LIVE_CACHE[ck]
    live: set[tuple[int, int]] = set()
    for d in read_jsonl(path):
        if d.get('run_id') == run_id and d.get('strategy_id'):
            live.add((int(d.get('plane') or 1), int(d.get('round_num') or 0)))
    # 缓存只留最新 mtime 条目(防长期运行膨胀)
    _STRATEGY_LIVE_CACHE.clear()
    _STRATEGY_LIVE_CACHE[ck] = live
    return live


def strategy_round_live(run_id: str, key: tuple[int, int]) -> bool:
    """(plane, round) 是否有带 strategy_id 的决策行(W103 件1 查询端)。"""
    return key in _strategy_live_rounds(run_id)


def dead_streak_transition(prev_key: tuple[int, int] | None,
                           key: tuple[int, int],
                           streak: int, live: bool) -> int:
    """策略失活连击状态机(W103 件1;纯函数,battle_loop 消费)。

    语义:进入新 round key 时对**上一轮** prev_key 的 live 结果结算——
    本轮的决策行还没写(检查点在备战入口,决策发生在本相位内),查本轮
    恒 False;查上一轮才是完整轮。同 key 重入(过渡帧/重试)不重复计数。
    live=True 复位;False 递增。
    """
    if prev_key is None or prev_key == key:
        return streak
    return 0 if live else streak + 1


def check_strategy_live_streak(all_rows: list[dict],
                               streak_threshold: int = 3) -> list[str]:
    """生产检查项(W103 件2;run_checks_on_replay 消费):策略失活局/失活段。

    判据:该 run 的 (plane, round) 全集中,「无任何带 strategy_id 决策行」
    的连续轮数 ≥ streak_threshold → 违规。W98 两局实录=整局恒空(全程
    57/61 轮),streak=轮数 → 必报;阈值取 3(整局空与 W98 形态远超;
    <3 的孤立空轮多为暂态/接管帧,不报警——非 sim 检查,生产局判栈用,
    与 sim 检查网(cw_sim_checks)分栈:sim 批 strategy 恒在,跑了也是
    恒绿,不进 _BATCH_CHECKS)。
    """
    rounds: dict[tuple[int, int], bool] = {}   # key → live
    for d in all_rows:
        k = (int(d.get('plane') or 1), int(d.get('round_num') or 0))
        rounds[k] = rounds.get(k, False) or bool(d.get('strategy_id'))
    streak = worst = 0
    for k in sorted(rounds):
        if k[0] != 1:
            continue   # P1 先辖(P2/P3 轮次恢复语义不同,语料不足不判)
        if not rounds[k]:
            streak += 1
            worst = max(worst, streak)
        else:
            streak = 0
    if worst >= streak_threshold:
        dead_n = sum(1 for k in rounds if k[0] == 1 and not rounds[k])
        return [f'P1 策略失活连续 {worst} 轮(共 {dead_n} 轮无 '
                f'strategy_id 决策行——W98 恢复兜底局形态,ADR-0342)']
    return []


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
    if not _CURRENT_RUN_ID:
        return
    _extra: dict[str, Any] = {}
    try:
        from sr_od.application.currency_war.cw_effect_ledger import (
            build_ledger,
            effects_from_strategies,
        )
        from sr_od.application.currency_war.cw_horizon import (
            _horizon_node_goal,
            ledger_fingerprint,
        )
        ng = _horizon_node_goal(state.plane, state.round_num, state.gold,
                                state.level, state.hp,
                                strategies=list(getattr(state, 'active_strategies', []) or []) or None)
        if ng is not None:
            _extra['dp_posture'] = {'spend_mode': getattr(ng, 'spend_mode', ''),
                                    'target_level': getattr(ng, 'target_level', None)}
        strategies = list(getattr(state, 'active_strategies', []) or [])
        _extra['active_strategies'] = strategies
        _extra['ledger_fingerprint'] = ledger_fingerprint(
            build_ledger(effects_from_strategies(strategies)))
        # 67-P1c(接线哨兵):指纹恒 'base' = ledger 重载接线仍断;修复后不同持卡
        # 组合应产生不同指纹(55-A1 对拍数据源)
        log.debug('[cw][ledger] fp=%s strategies=%s',
                  _extra['ledger_fingerprint'], strategies)
    except Exception:   # noqa: BLE001  观测 best-effort
        pass
    if extra:
        _extra.update(extra)   # 调用方显式字段(sess_* 快照)合并在自动字段上
    get_recorder().record_decision(_CURRENT_RUN_ID, _CURRENT_DIFFICULTY, state,
                                   target_comp, candidate_scores, eval_breakdown, actions,
                                   extra=_extra, gold_point=gold_point)


def record_outcome(outcome, source: str = "") -> None:
    """便捷:用 current_run_id 记一条观测结果。loop 战斗后调。

    source(W28):行来源标记(''/'recovered'/'synthetic_supply')。
    """
    if not _CURRENT_RUN_ID:
        return
    get_recorder().record_outcome(_CURRENT_RUN_ID, outcome, source=source)


def record_exogenous(round_num: int, kind: str, detail: str = '',
                     state: GameState | None = None) -> None:
    """便捷:用 current_run_id 记一条外生事件(r1 review#3:此前 battle_loop 调用
    模块级函数但只有类方法 → AttributeError 被吞,exogenous.jsonl 生产侧静默死)。

    注意签名与类方法不同(无 run_id 首参——模块级自动取 current_run_id)。
    """
    if not _CURRENT_RUN_ID:
        return
    get_recorder().record_exogenous(_CURRENT_RUN_ID, round_num, kind, detail, state)


def record_run_summary(result: str, plane_reached: int, rounds_survived: int,
                       final_hp: int, notes: str = "") -> None:
    """便捷:用 current_run_id 记局终 summary。loop 局终调。"""
    if not _CURRENT_RUN_ID:
        return
    get_recorder().record_run_summary(_CURRENT_RUN_ID, result, plane_reached,
                                      rounds_survived, final_hp, notes=notes)


# ===== 局终 summary 多路径兜底(ADR-0273;批⑧ F2 runs.jsonl 断流)=====
# 写端三路径:① 3c 回大厅(正常终局 win/loss);② W75 after_operation_done
# 收口(停止/超时/异常退出 result='stopped'/'abandoned',battle_loop.py 类注);
# ③ 本兜底(进程崩溃/重启杀局,start_run 每局起点补 source='recovered')。
# r363 曾在 loop() 顶查 is_context_stop —— 但 operation.execute() 每轮前
# (operation.py:408)先查 stop,stop 到达后 loop() 不再被调,原检查几乎永不
# 触发(MCP stop 四局 [RUNS-GAP] 实锤),故收口迁 after_operation_done(ADR-0335)。

def _runs_summarized(replay_dir: Path) -> set[str]:
    """runs.jsonl 已有 summary 行的 run_id 集(幂等判据单一源)。"""
    return {r.get('run_id') for r in read_jsonl(replay_dir / 'runs.jsonl')
            if r.get('run_id')}


def build_recovered_summary(replay_dir: Path, run_id: str) -> RunSummary | None:
    """从 outcomes/decisions 重建一局 summary(ADR-0273 数据治理:补算回填)。

    - 末条真值按 (plane, round) 排序取最后(round_num 是位面内编号,跨位面
      重建须按 (plane, round) 排序——批⑧边界声明);
    - final_hp 取 conf≥0.9 末条 hp_after(镜像 loop `_last_true_hp` 语义:
      死局 hp 读不到时兜底 100 毒化,高置信真值优先);final_hp≤0 → 'loss'
      (战败结算屏 hp=0 补录链),否则 'abandoned'(FAIL/崩溃/重启局无终局判定);
    - 无 outcomes → None(留缺口,不造伪值)。
    """
    outcomes = [o for o in read_jsonl(replay_dir / 'outcomes.jsonl')
                if o.get('run_id') == run_id]
    if not outcomes:
        return None
    outcomes.sort(key=lambda o: (o.get('plane') or 1, o.get('round_num') or 0,
                                 o.get('ts') or ''))
    last = outcomes[-1]
    plane_reached = max((o.get('plane') or 1) for o in outcomes)
    _conf_rows = [o for o in outcomes if (o.get('hp_confidence') or 0) >= 0.9]
    final_hp = int((_conf_rows[-1] if _conf_rows else last).get('hp_after') or 0)
    result = 'loss' if final_hp <= 0 else 'abandoned'
    decisions = [d for d in read_jsonl(replay_dir / 'decisions.jsonl')
                 if d.get('run_id') == run_id]
    difficulty = next((d.get('difficulty') for d in decisions if d.get('difficulty')), '')
    # gold 轨迹:每 (plane, round) 首采样(镜像 recorder 内存去重键 r363)
    gold_traj: list[int] = []
    _seen: set = set()
    for d in decisions:
        k = (d.get('plane'), d.get('round_num'))
        if k in _seen:
            continue
        _seen.add(k)
        gold_traj.append(int(d.get('gold') or 0))
    # pivot:target_comp 序列连续去重后的转移数(内存 _comms 同语义)
    comms: list[str] = []
    for d in decisions:
        t = d.get('target_comp') or ''
        if t and (not comms or comms[-1] != t):
            comms.append(t)
    return RunSummary(
        ts=datetime.now().isoformat(timespec='seconds'),
        run_id=run_id, difficulty=difficulty,
        result=result, plane_reached=plane_reached,
        rounds_survived=int(last.get('round_num') or 0),
        final_hp=final_hp, comps_committed=comms,
        pivot_count=max(0, len(comms) - 1),
        gold_trajectory=gold_traj,
        notes='recovered:FAIL/crash/restart 兜底(ADR-0273)',
        source='recovered',
    )


def recover_dangling_run_summaries(replay_dir: Path | str | None = None) -> list[str]:
    """补齐 runs.jsonl 缺行(幂等;start_run 每局起点调,盖 FAIL/崩溃/重启路径)。

    returns 本次补写的 run_id 列表(已 summaried 的不重复;无 outcomes 的跳过)。
    """
    d = Path(replay_dir) if replay_dir is not None else get_recorder().replay_dir
    if not (d / 'outcomes.jsonl').exists():
        return []
    known = _runs_summarized(d)
    ids: list[str] = []
    _seen: set = set()
    for o in read_jsonl(d / 'outcomes.jsonl'):
        rid = o.get('run_id')
        if rid and rid not in known and rid not in _seen:
            _seen.add(rid)
            ids.append(rid)
    rec = get_recorder()
    recovered: list[str] = []
    for rid in ids:
        summary = build_recovered_summary(d, rid)
        if summary is None:
            continue
        append_jsonl(d / 'runs.jsonl', _to_jsonable(summary))
        # 内存累积同步清理(防跨 run 泄漏;语义同 record_run_summary 尾部)
        rec._gold_trajectory.pop(rid, None)
        rec._comms.pop(rid, None)
        rec._difficulty.pop(rid, None)
        recovered.append(rid)
    if recovered:
        log.info('[cw][telemetry] summary 兜底回填 %d 局(ADR-0273):%s',
                 len(recovered), ','.join(recovered))
        # W109(ADR-0344):兜底行也是 runs.jsonl 新增——同样触发池再生
        # (崩溃恢复局的语料此刻才齐,不等到下一局正常局终)。
        _regenerate_delta_pool_after_run()
    return recovered


def _regenerate_delta_pool_after_run() -> None:
    """W109(ADR-0344):局终→Δ池快照自动再生 + 新鲜度自检。

    事故背景:2026-08-25 查实池快照停在凌晨(41 局),当天 4 局未入
    池——sim encounter/boss 零胜例把 P1 后段钉死全败,管线断 12
    小时无任何报警。治本 = 再生随 runs.jsonl 写入端走(正常局终
    record_run_summary + 崩溃兜底 recover_dangling_run_summaries),
    加新鲜度检查项双端挂(sim 批 + 生产自检)。

    best-effort 纪律:再生/自检失败只记日志,**绝不向局终收尾传播
    异常**(遥测基建故障不许影响对局本体)。
    """
    try:
        from sr_od.application.currency_war.cw_delta_pool_gen import (
            regenerate_snapshot,
        )
        fp = regenerate_snapshot(quiet=True)
    except Exception as e:   # noqa: BLE001
        log.warning('[cw][pool-pipeline] Δ池再生失败(不阻塞局终,ADR-0344): %s', e)
        return
    log.info('[cw][pool-pipeline] 局终自动再生 Δ池快照: %s', fp)
    try:
        from sr_od.application.currency_war.cw_sim_checks import (
            check_pool_freshness,
        )
        verdict = check_pool_freshness()
        if verdict.get('violations'):
            # 再生刚成功却仍滞后 = 新局语料没进池(如 outcomes 缺行)
            # ——正是新鲜度检查要抓的病态,留痕不抛。
            log.warning('[cw][pool-pipeline] 再生后池新鲜度仍滞后'
                        '(ADR-0344): %s', verdict)
    except Exception as e:   # noqa: BLE001
        log.warning('[cw][pool-pipeline] 新鲜度自检异常(不阻塞): %s', e)


def check_summary_write_path_coverage(replay_dir: Path, recent: int = 10) -> list[str]:
    """检查项 ``summary_write_path_coverage``(批⑧设计,ADR-0273 入栈)。

    判据 = 最近 N 个(有 outcomes 的)run 全部有 summary 行(含 source=recovered
    兜底行)。违规行带 run_id 溯源;连续 10 局 100% = 修复验收线。
    """
    ids: list[str] = []
    for o in read_jsonl(replay_dir / 'outcomes.jsonl'):
        rid = o.get('run_id')
        if rid and (not ids or ids[-1] != rid):
            ids.append(rid)
    recent_ids = ids[-recent:]
    if not recent_ids:
        return ['[coverage] ⊘ 无 outcomes 语料,无法判']
    known = _runs_summarized(replay_dir)
    missing = [rid for rid in recent_ids if rid not in known]
    if missing:
        return [f'[coverage] ⚠ summary_write_path_coverage {len(missing)}/{len(recent_ids)} 局缺行:'
                + ','.join(missing)]
    return [f'[coverage] ✓ summary_write_path_coverage 最近 {len(recent_ids)} 局 100%']


def bucket_card_texts(anchors: list[tuple[int, int]], items: list[tuple[str, int, int]],
                      y_min: int, y_max: int) -> dict[int, list[str]]:
    """投资卡 OCR 文本按卡分桶(ADR-0132;纯函数可测)。

    anchors: [(card_idx, 锚点x)](卡名行 center-x);items: [(文本, cx, cy)] 全图 OCR 条目。
    每条 item 归 **x 最近**的锚点卡;y 不在 [y_min, y_max] 描述带 → 不归。
    桶内按 y 升序(自然阅读序)。返回 {card_idx: [文本...]}。
    """
    if not anchors:
        return {}
    out: dict[int, list[tuple[int, str]]] = {i: [] for i, _x in anchors}
    for text, cx, cy in items:
        if not text or not (y_min <= cy <= y_max):
            continue
        idx = min(anchors, key=lambda a: abs(a[1] - cx))[0]
        out[idx].append((cy, text))
    return {i: [t for _y, t in sorted(v)] for i, v in out.items()}


def record_invest_cards(kind: str, cards: list[dict[str, Any]]) -> None:
    """投资策略/环境卡**候选全集 + 效果原文** → invest_cards.jsonl(ADR-0132 采集)。

    cards 元素:{idx, name, x, effect_text, chosen}(每卡一行,带 ts/run_id/kind)。
    效果原文 = 卡面描述区 OCR 按卡分桶拼接 —— 注册表效果的 **ground truth 回流源**
    (ADR-0131 发现 T0 12 条里 8 条描述错,即因无采集;离线对拍本文件校注册表/补 315 长尾)。
    """
    if not _CURRENT_RUN_ID:
        return
    rec = get_recorder()
    ts = datetime.now().isoformat(timespec="seconds")
    for c in cards:
        rec._append("invest_cards.jsonl", {
            "schema_version": 1, "ts": ts, "run_id": _CURRENT_RUN_ID, "kind": kind, **c,
        })



def record_shop_snapshot(event: str, shop: list, gold: int,
                         plane: int = 0, round_num: int = 0) -> None:
    """商店牌面快照(shop_snapshots.jsonl;r97;供给复盘的真值源)。

    event:``offer``(进店首见)/ ``refresh``(刷新后新牌面)—— 买牌回合里 bot 会 refresh,
    只记进店帧会丢中间 4-5 波牌 → 「配方件来没来」复盘断章取义(局18:据此误判
    「仙舟 8 轮断供」实为 r2 爻光×3 在店没买)。shop 元素为 ShopCard(或已序列化 dict)。
    """
    if not _CURRENT_RUN_ID:
        return
    rec = get_recorder()
    rec._append("shop_snapshots.jsonl", {
        "schema_version": 1,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "run_id": _CURRENT_RUN_ID,
        "plane": plane, "round_num": round_num,
        "event": event, "gold": gold,
        "shop": [{k: getattr(c, k, None) for k in ('name', 'faction', 'cost', 'star')}
                 for c in shop],
    })


def record_shop_snapshot_raw(event: str, shop: list, gold: int,
                             plane: int = 0, round_num: int = 0) -> None:
    """shop 已是序列化 dict 列表时的 record_shop_snapshot 变体。"""
    if not _CURRENT_RUN_ID:
        return
    rec = get_recorder()
    rec._append("shop_snapshots.jsonl", {
        "schema_version": 1,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "run_id": _CURRENT_RUN_ID,
        "plane": plane, "round_num": round_num,
        "event": event, "gold": gold,
        "shop": list(shop),
    })



# ===== 复盘读取(给人肉眼复盘 / 未来 ML)=====

def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    """读一个 JSONL 文件 → list[dict]。文件不存在 → []。"""
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def join_decisions_outcomes(replay_dir: Path | str) -> list[dict[str, Any]]:
    """按 (run_id, plane, round_num) join decisions ↔ outcomes → 每回合一条合并记录(复盘/ML 用)。

    decisions 主表,outcomes 左 join(无 outcome 的决策 outcome 字段为 None)。
    ⚖️ r68 review:join 键加 plane —— round_num 是位面内序(1-9),P1r3 与 P2r3 旧键撞行
    (跨位面 outcome 错配);两侧均含 plane 字段,旧记录缺 plane 时 get 返 None 仍一致配对。
    """
    decisions = read_jsonl(Path(replay_dir) / "decisions.jsonl")
    outcomes = read_jsonl(Path(replay_dir) / "outcomes.jsonl")
    out_by_key = {(o["run_id"], o.get("plane"), o["round_num"]): o for o in outcomes}
    joined: list[dict[str, Any]] = []
    for d in decisions:
        key = (d.get("run_id"), d.get("plane"), d.get("round_num"))
        merged = dict(d)
        merged["outcome"] = out_by_key.get(key)
        joined.append(merged)
    return joined


# ===== 复盘查询(query CLI;telemetry 的读出端,r97)=====
# 设计:数据与判读同源 —— 查询视图(逐轮演进/供给对照/异常标记)读的就是本模块落盘的
# JSONL,schema 变更查询同步;新复盘问题 = 新视图/参数,不是新脚本(一次性脚本时代终结)。
# 用法:
#   uv run python -m sr_od.application.currency_war.cw_telemetry query [--run ID] [--recent N] [--view rounds|supply|anomalies|all]

def _load_decisions_rounds(replay_dir: Path, run_id: str) -> dict:
    """该 run 的 decisions 按 (plane,round) 取 actions 最多的一条(plan 真值)。

    r363(审计 P1-8):并列(同 action 数)时取 **ts 最晚**(末帧)——
    旧严格大于让最早的行胜出,轮末 state(买后 board/gold)被首帧
    (空板)代表,收入/执行判读失真。
    """
    best: dict = {}
    for d in read_jsonl(replay_dir / "decisions.jsonl"):
        if run_id and d.get("run_id") != run_id:
            continue
        k = (d.get("plane"), d.get("round_num"))
        n = len(d.get("actions") or [])
        if k not in best or n > len(best[k].get("actions") or []) or (
                n == len(best[k].get("actions") or [])
                and (d.get("ts") or '') > (best[k].get("ts") or '')):
            best[k] = d
    return best


def run_checks_on_replay(replay_dir: Path, recent: int = 5) -> list[str]:
    """生产遥测接 checks(决策项 1):对最近 N 局跑栈适配的检查集。

    - 判栈(逐局):strategy_id∈{'line_v2'[历史,ADR-0336 已删],
      'decision_v2'} 或开局轮 BuyCard reason 含 v2 词表
      (line/bridge_seed/engine/pair/off) → v2 栈(reason 词表与
      coldstart 检查集同辖);
      reason 全 'plan'/空 → default 栈(cw_plan,不辖 r368 门);
      非空未知 sid → 显式跳过(未来新栈不盲跑,审查#5);
    - **开局轮逐行全检**(审查#3:_load_decisions_rounds 的
      max-actions 单行选取是有损投影——生产开局轮实测 5-6 行,
      pre-refresh 波的违规买牌可被 post-refresh 大行静默挤掉;
      checks 只聚合开局轮 r≤2 的**全部行**的 BuyCard);
    - **可判性声明**(审查#2:开局轮买牌 reason 缺失=打标不全
      时代数据,输出 ⊘ 无法判 而非 ✓——不把不可判伪装成健康);
    - ledger_consistency 不跑(需 sim 键;生产金对账归
      econ_reconcile 工具链,不重复造轮子);
    - 输出行化(判读 CLI 风格),违规局带 run_id 可溯源;
    - ADR-0273:头部附 ``summary_write_path_coverage``(runs.jsonl 断流守卫,
      与逐局检查正交——它是「分母完整性」,先于一切逐局判读)。
    """
    from sr_od.application.currency_war.cw_sim_checks import (
        check_coldstart_seed_squander,
    )
    lines: list[str] = list(check_summary_write_path_coverage(replay_dir))
    # ADR-0260:engine_seed=P1 未持有引擎件放行通道(v2 栈
    # [line_v2/decision_v2] 合法词)
    _V2_REASONS = {'line', 'bridge_seed', 'engine', 'engine_seed', 'pair',
                   'off', 'p2_core', 'board_focus', 'emergency', 'swap'}
    runs = _list_runs(replay_dir)[-recent:]
    for rid in runs:
        # 开局轮逐行(plane1 r≤2;不走 max-actions reducer——审查#3)
        rows = [d for d in read_jsonl(replay_dir / 'decisions.jsonl')
                if d.get('run_id') == rid
                and (d.get('plane') or 1) == 1
                and (d.get('round_num') or 9) <= 2]
        rows.sort(key=lambda d: ((d.get('round_num') or 0),
                                 (d.get('ts') or '')))
        all_rows = [d for d in read_jsonl(replay_dir / 'decisions.jsonl')
                    if d.get('run_id') == rid]
        # W103 件2(ADR-0342):策略失活检查先行(不依赖判栈——失活局
        # 恰恰 strategy_id='' 无法判栈,不能被栈跳过逻辑连坐)。
        _dead = check_strategy_live_streak(all_rows)
        if _dead:
            lines.append(f'{rid}: [策略失活] ⚠ {"; ".join(_dead)}')
        # 判栈:strategy_id 字段优先,退开局 reason 词表(逐行)
        sid = next((d.get('strategy_id') for d in all_rows
                    if d.get('strategy_id')), '')
        early_buys = [a for d in rows for a in (d.get('actions') or [])
                      if a.get('__type__') == 'BuyCard']
        early_reasons = {(a.get('reason') or '') for a in early_buys}
        if sid in ('line_v2', 'decision_v2'):
            stack = 'v2'
        elif sid and sid != 'default':
            lines.append(f'{rid}: [未知栈 {sid}] coldstart 跳过'
                         '(ADR-0245:新栈不盲跑)')
            continue
        elif early_reasons & _V2_REASONS:
            stack = 'v2'
        elif early_reasons & {'plan'}:
            stack = 'default'
        elif early_buys:
            stack = 'v2'   # 有买但 reason 全空(旧栈时代?);可判性另行声明
        else:
            stack = '?'    # 开局轮零买牌,无法判栈;跑检查无害(无买=无违规)
        if stack == 'default':
            lines.append(f'{rid}: [default 栈] coldstart 跳过(cw_plan '
                         '不辖 r368 门)')
            continue
        # 可判性:开局轮买牌 reason 缺失数(审查#2——✓ 必须真可判)
        untagged = sum(1 for a in early_buys
                       if not (a.get('reason') or '').strip())
        v = check_coldstart_seed_squander(rows)
        tag = f'[{stack} 栈]' if stack != 'v2' else '[v2]'
        if untagged and not v:
            lines.append(f'{rid}: {tag} coldstart ⊘ 无法判'
                         f'({untagged} 笔开局买未打标——旧数据;'
                         f'ba7ce6f3 后新局可判)')
            continue
        lines.append(f'{rid}: {tag} coldstart '
                     + ('✓ 无违规' if not v else f'⚠ {len(v)} 条'))
        for item in v:
            lines.append(f'    {item}')
    return lines


def _list_runs(replay_dir: Path) -> list[str]:
    ids: list[str] = []
    for d in read_jsonl(replay_dir / "outcomes.jsonl"):
        rid = d.get("run_id")
        if rid and (not ids or ids[-1] != rid):
            ids.append(rid)
    return ids


def query_rounds(replay_dir: Path, run_id: str) -> list[str]:
    """视图:逐轮演进(hp/gold/买/升/D/board;v2 模式/锁线/桥)。"""
    best = _load_decisions_rounds(replay_dir, run_id)
    lines = []
    for k in sorted(best):
        d = best[k]
        st = d.get("state") or {}
        acts = d.get("actions") or []
        buys = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "BuyCard")
        lvs = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "LevelUp")
        rfs = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "RefreshShop")
        board = " ".join(f"{k2}×{v}" for k2, v in (st.get("board") or {}).items()) or "(空)"
        # sim 批次:board 恒空 → 显示账本代理维度(深/核;判读不断档)
        _simd = d.get('sim')
        if _simd is not None:
            board = f"(sim 深={_simd.get('depth')} 核={_simd.get('core_count')})"
        act_s = f"买{buys}" + (f"/升{lvs}" if lvs else "") + (f"/D{rfs}" if rfs else "")
        # r226 v2 字段读出(策略 v2 对拍视图;空则省略——default 局全空)
        v2 = d.get("v2_mode") or ""
        lock = d.get("v2_locked_line") or ""
        bridge = d.get("v2_bridge") or ""
        v2_s = f" v2=[{v2}|{lock or '-'}|{bridge or '-'}]" if (v2 or lock or bridge) else ""
        # W146 v3 意向状态直读(锁定时点/锁定目标;None/default 局省略)
        _ist = d.get('v3_intention')
        ist_s = ''
        if isinstance(_ist, dict):
            ist_s = (f" ist=[{_ist.get('phase', '')}"
                     f"|{_ist.get('locked_comp', '') or '-'}]"
                     + ('/降格' if _ist.get('demoted_endgame') else ''))
        # W114/ADR-0346 相位影子观测(空则省略——旧局/影子代码前全空)
        _ph = d.get("phase") or ""
        _fok = d.get("form_ok")
        _fsc = d.get("form_score")
        ph_s = (f" ph={_ph}" + ("/ok" if _fok else "")
                + (f"/{_fsc:.2f}" if isinstance(_fsc, (int, float)) else "")
                ) if _ph else ""
        # W119/ADR-0347 授权依据 trace:DP 姿态 tag(空则省略)
        _dpp = d.get("dp_posture") or ""
        dpp_s = f" dp={_dpp}" if _dpp else ""
        # ADR-0348 ↺:扑满节点识别标记
        if d.get("piggy_reward"):
            dpp_s += " P=扑满"
        # r358c(用户定调「复盘要全面」):xp 进度/站位(前排数)入 rounds 主视图
        # ——升级节奏与站位分流的直读维度(旧视图不可见,须直查 jsonl)。
        # ⚠️ 判读语义(W229 分型,勿再误判为「前排未满编」缺陷):
        # - 前后分拆按 position_pref(角色命途定位)计数,deploy 按它路由落排
        #   (ADR-0392 deployed_place);「前排固定 4」是槽位可用性不是放置目标;
        # - 「满编」判据 = deployed 总数 = cap(=level),**不是前排占满 4**;
        #   队伍含 N 个 back 定位角色时,位=(cap-N)前/N后 且前排留空槽 = 合法布局
        #   (实证:run 25/28「位=3前/2后」与 deploy_bench CV 实读逐轮吻合,总数恒=cap)。
        _xp = st.get("xp_progress")
        xp_s = f" xp={_xp[0]}/{_xp[1]}" if _xp else ""
        _dep = st.get("deployed") or []
        _front = sum(1 for c in _dep if c.get("position_pref") == "front")
        pos_s = f" 位={_front}前/{len(_dep) - _front}后" if _dep else ""
        lines.append(f"  p{k[0]}r{k[1]} hp={d.get('hp')} g={d.get('gold')} lv={st.get('level')}"
                      f"{xp_s} {act_s:<10} | {board}{pos_s}{v2_s}{ist_s}{ph_s}{dpp_s}")
    return lines


def query_supply(replay_dir: Path, run_id: str) -> list[str]:
    """视图:供给对照(shop_snapshots 全波牌面 vs 买了什么;配方件出现即标 ★)。"""
    snaps: dict = {}
    for s in read_jsonl(replay_dir / "shop_snapshots.jsonl"):
        if run_id and s.get("run_id") != run_id:
            continue
        snaps.setdefault((s.get("plane"), s.get("round_num")), []).append(s)
    best = _load_decisions_rounds(replay_dir, run_id)
    # 配方框架(cw_transition;import 失败退空 = 全牌不标)
    try:
        from sr_od.application.currency_war.cw_transition import TRANSITION_PACK
        recipe_names = set(TRANSITION_PACK.keys())
    except Exception:   # noqa: BLE001
        recipe_names = set()
    lines = []
    for k in sorted(set(list(snaps.keys()) + list(best.keys()))):
        d = best.get(k)
        acts = (d.get("actions") or []) if d else []
        buys = [a.get("card", {}).get("name") for a in acts
                if isinstance(a, dict) and a.get("__type__") == "BuyCard"]
        lines.append(f"  p{k[0]}r{k[1]} tgt={(d or {}).get('target_comp', '?')}")
        for s in snaps.get(k, []):
            cards = [(c.get('name'), c.get('faction'), c.get('cost')) for c in (s.get('shop') or [])]
            star = [f"★{n}({f})" for n, f, _c in cards
                    if n in recipe_names or (f in ('仙舟', '列车同行') and n)]
            mark = ('  ' + ' '.join(star)) if star else ''
            lines.append(f"    [{s.get('event')}] g={s.get('gold')} {cards}{mark}")
        if not snaps.get(k):
            lines.append("    (无 shop 快照——旧数据只记进店帧,refresh 波丢失)")
        lines.append(f"    买了: {buys}")
    return lines


ABN_GOLD: int = 40     # 金 ≥ 此且该轮 0 买 0 升 = 钱变不成板
ABN_DROP: int = 25     # 单轮掉血 ≥ 此 = 战力断层


def query_anomalies(replay_dir: Path, run_id: str) -> list[str]:
    """视图:异常标记(钱变不成板/战力断层/plan_error)。"""
    best = _load_decisions_rounds(replay_dir, run_id)
    abn: list[str] = []
    for k in sorted(best):
        d = best[k]
        acts = d.get("actions") or []
        buys = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "BuyCard")
        lvs = sum(1 for a in acts if isinstance(a, dict) and a.get("__type__") == "LevelUp")
        if (d.get("gold") or 0) >= ABN_GOLD and buys == 0 and lvs == 0:
            abn.append(f"p{k[0]}r{k[1]} 金{d.get('gold')} 0买0升(钱变不成板)")
        if (d.get("eval_breakdown") or {}).get("plan_error"):
            abn.append(f"p{k[0]}r{k[1]} plan_error(决策崩溃,见 log)")
    prev_hp = None
    for o in read_jsonl(replay_dir / "outcomes.jsonl"):
        if run_id and o.get("run_id") != run_id:
            continue
        hp = o.get("hp_after")
        if prev_hp is not None and hp is not None and prev_hp - hp >= ABN_DROP:
            abn.append(f"p{o.get('plane')}r{o.get('round_num')} 单轮掉血 {prev_hp}→{hp}(战力断层)")
        if hp is not None:
            prev_hp = hp
    return abn


def query_hp(replay_dir: Path, run_id: str) -> list[str]:
    """视图(r339):掉血分解——逐轮 (node, delta, 板深, 方向态)。

    与 sim hp_events 同构(对拍 sim 校准模型的直接读出端);
    board_before/bench_count 为 r339 起记录(旧数据缺省显示 -)。
    """
    lines = []
    prev_hp: int | None = None
    for o in read_jsonl(replay_dir / "outcomes.jsonl"):
        if run_id and o.get("run_id") != run_id:
            continue
        hp = o.get("hp_after")
        delta = (prev_hp - hp) if (prev_hp is not None and hp is not None) else None
        _b = o.get("board_before") or {}
        depth = sum(_b.values())
        # sim 批次:board 恒空(设计如此)→ 回退账本深度(sim.depth
        # = _deployable_depth 口径,与生产 board 语义同源 r343)
        _sim = o.get("sim") or {}
        # sim 行板深带 *(审查#4:sim depth=可部署潜力/生产=已部署
        # 事实,跨 run 并排判读需可辨)
        depth_s = str(depth) if _b else (
            f"{_sim.get('depth', '-')}*" if _sim else '-')
        bench = o.get("bench_count")
        delta_s = f'{-delta:+d}' if delta is not None else '-'
        lines.append(
            f"  p{o.get('plane')}r{o.get('round_num')} {o.get('node_type') or '?':8s}"
            f" hp={hp} Δ={delta_s}"
            f" 板深={depth_s} bench={bench if bench is not None else '-'}")
        if hp is not None:
            prev_hp = hp
    return lines


def query_economy(replay_dir: Path, run_id: str) -> list[str]:
    """视图(r339):金轨迹/滞留——逐轮 (gold, 收入, 花出, 息)。

    「金花不出去」异常的量化端:滞留轮(金≥20 且花=0)标 ⚠。
    """
    best = _load_decisions_rounds(replay_dir, run_id)
    lines = []
    prev_gold: int | None = None
    for k in sorted(best):
        d = best[k]
        acts = d.get("actions") or []
        spend = sum((a.get("card", {}).get("cost") or 0)
                    for a in acts if isinstance(a, dict)
                    and a.get("__type__") == "BuyCard")
        spend += 4 * sum(1 for a in acts
                         if isinstance(a, dict) and a.get("__type__") == "LevelUp")
        spend += sum((a.get("cost") or 0) for a in acts
                     if isinstance(a, dict) and a.get("__type__") == "RefreshShop")
        # 卖牌回金(⑤:此前漏计——含卖轮的 income 系统性偏负;
        # sim 账本行带 income 字段,生产行暂无(卖值不在动作里,
        # 补采前按 0 = 与旧口径一致,不回归)
        sell_in = sum((a.get("income") or 0) for a in acts
                      if isinstance(a, dict) and a.get("__type__") == "SellBench")
        g = d.get("gold") or 0
        income = ((g - prev_gold + spend - sell_in)
                  if prev_gold is not None else None)
        flag = ' ⚠滞留' if (g >= 20 and spend == 0) else ''
        sell_s = f' 卖+{sell_in}' if sell_in else ''
        lines.append(
            f"  p{k[0]}r{k[1]} g={g}"
            f" 花={spend}{sell_s} 收={'-' if income is None else income}{flag}")
        prev_gold = g
    return lines


def query_tiers(replay_dir: Path, run_id: str) -> list[str]:
    """视图:羁绊激活档逐轮 + 角色构成(星级) + 装备分配(r358 三维同屏;
    配方成型判读的硬指标;恒 0 = 配方没真正上场)。"""
    from sr_od.application.currency_war.cw_factions import FACTIONS
    best = _load_decisions_rounds(replay_dir, run_id)
    lines: list[str] = []
    prev_tgt = None
    for k in sorted(best):
        d = best[k]
        # 换线标记(审查#6:核= 随 tgt 切换定义,跨线时间序列
        # 判读需可辨「数字跳水=换线非丢核心」)
        _tgt = d.get('target_comp') or ''
        mark = ' ↹' if (prev_tgt is not None and _tgt != prev_tgt) else ''
        prev_tgt = _tgt
        # sim 批次:board 恒空(档位恒 0 误导)→ 三维同屏换账本代理
        # 维度(深度/核心在场/方向态;core_count 按 target 路由,
        # **跨线不可比**——核心定义随 tgt 切换,↹ 标换线轮)
        _simd = d.get('sim')
        if _simd is not None:
            _cc = _simd.get('core_count')
            _cc_s = '-' if _cc is None else str(_cc)
            lines.append(
                f"  p{k[0]}r{k[1]} 深={_simd.get('depth')}"
                f" 核={_cc_s}"
                f"{' ✓方向' if _simd.get('dir_established') else ''}"
                f" tgt={_tgt or '-'}{mark}")
            _dep = _simd.get('deployed') or []
            if _dep:
                lines.append(f"    deployed={' '.join(_dep)}")
            continue
        board = (d.get('state') or {}).get('board') or {}
        activated = {}
        for fac, cnt in board.items():
            tiers = getattr(FACTIONS.get(fac), 'tiers', ()) or ()
            tier = next((t for t in tiers if cnt >= t), 0)
            if tier > 0:
                activated[fac] = tier
        total = sum(activated.values())
        mark = '' if total else '  ← 档0'
        lines.append(f"  p{k[0]}r{k[1]} 激活档={total} {activated if activated else ''}{mark}")
        # r358(用户点题「看羁绊忽略角色/装备乱用不可见」):阵容质量三维
        # 同屏——角色构成(名字+星级)+ 装备分配(谁穿了什么)。不再截断
        # [:7](后期 9-10 人,截断藏人);未知名(身份 miss)保留槽位计数。
        _deployed = (d.get('state') or {}).get('deployed') or []
        dep_str = ' '.join(
            f"{c.get('char_id') or '?'}{'★' * (c.get('star') or 1)}"
            for c in _deployed) or '(空板)'
        lines.append(f"    deployed={dep_str}")
        _eq_pairs = [(c.get('char_id') or '?', c.get('equips') or [])
                     for c in _deployed if (c.get('equips'))]
        if _eq_pairs:
            lines.append('    装备=' + ' '.join(
                f"{n}[{','.join(eq)}]" for n, eq in _eq_pairs))
        _owned = (d.get('state') or {}).get('equips') or []
        if _owned:
            lines.append(f"    owned装备={len(_owned)}件(滞留未穿判读): "
                         f"{','.join(_owned[:8])}{'…' if len(_owned) > 8 else ''}")
    return lines


def query_plan_vs_exec(replay_dir: Path, run_id: str) -> list[str]:
    """视图:plan 动作 vs 实际执行对拍(步进 decisions 里的 plan 序列 vs 次轮
    board/bench 变化;r126 发现「plan 买白厄在首位但实跑只买 1 张」类执行
    缺口的判读入口)。

    方法:每轮末条决策的 plan buys/refresh/level vs 下一轮首条决策的
    gold 差(金没花=买没执行/金花了板没变=点了没生效)。"""
    rows = [d for d in read_jsonl(replay_dir / 'decisions.jsonl')
            if d.get('run_id') == run_id]
    rows.sort(key=lambda d: (d.get('plane') or 0, d.get('round_num') or 0,
                             d.get('ts') or ''))
    lines: list[str] = []
    # 按轮聚合
    by_round: dict = {}
    for d in rows:
        by_round.setdefault((d.get('plane'), d.get('round_num')), []).append(d)
    keys = sorted(by_round)
    for i, k in enumerate(keys[:-1]):
        cur = by_round[k]
        nxt = by_round[keys[i + 1]]
        # 轮内累计 plan 动作
        buys = lvl = rf = 0
        for d in cur:
            for a in (d.get('actions') or []):
                t = a.get('__type__')
                if t == 'BuyCard':
                    buys += 1
                elif t == 'LevelUp':
                    lvl += 1
                elif t == 'RefreshShop':
                    rf += 1
        g_end = cur[-1].get('state', {}).get('gold')
        g_next = nxt[0].get('state', {}).get('gold')
        if g_end is None or g_next is None:
            continue
        # 期望:下轮金 ≈ 本轮末 - 花费 + 收入(5±) ;偏差大 = 执行缺口
        delta = g_next - g_end
        # 收入 ~5-8(利息+基础);delta 显著大于收入 = plan 没花出去
        suspicious = (buys + rf + lvl) > 0 and delta > 12
        mark = '  ← 疑似未执行(金几乎没花)' if suspicious else ''
        lines.append(f"  p{k[0]}r{k[1]} plan:买{buys} 升{lvl} 刷{rf} | 金 {g_end}→{g_next}"
                     f"(Δ{delta:+d}){mark}")
    return lines


def _cli_main() -> None:
    import argparse
    import sys
    if hasattr(sys.stdout, 'reconfigure'):   # GBK 控制台遇 ⚠/★ 崩
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(prog='cw_telemetry',
                                 description='货币战争遥测查询(复盘判读单一入口)')
    ap.add_argument('cmd', choices=['query', 'checks'])
    ap.add_argument('--run', default='', help='run_id(缺省=最近一局)')
    ap.add_argument('--recent', type=int, default=0, help='最近 N 局概览')
    ap.add_argument('--view', default='rounds',
                    choices=['rounds', 'supply', 'anomalies', 'tiers', 'planexec',
                             'hp', 'economy', 'all'])
    ap.add_argument('--replay-dir', default=str(DEFAULT_REPLAY_DIR))
    ap.add_argument('--sim-batch', default='', metavar='BATCH',
                    help='查 sim 批次账本:BATCH=批次目录名(缺省=最新;'
                         '根目录 sim_runs;"latest" 同缺省)。sim 语义差异:'
                         'board 系字段恒空(hp/tiers/rounds 视图自动回退'
                         '账本深度/核心维度);planexec 不适用(sim 无'
                         '执行层分离);ts=轮序号(生产 ISO 串)')
    args = ap.parse_args()
    if args.sim_batch:
        # ⑤:sim 批次便捷入口——批次目录结构与生产 replay 同构
        # ({decisions,outcomes,shop_snapshots}.jsonl),视图零分叉
        from sr_od.application.currency_war.cw_sim import SIM_RUNS_DIR
        if args.sim_batch == 'latest':
            batches = sorted(p for p in SIM_RUNS_DIR.iterdir()
                             if p.is_dir())
            if not batches:
                print('(无 sim 批次——先跑 simulate_p1_batch)')
                return
            replay_dir = batches[-1]
        else:
            replay_dir = SIM_RUNS_DIR / args.sim_batch
        print(f"[sim 批次] {replay_dir.name}")
    else:
        replay_dir = Path(args.replay_dir)
    runs = _list_runs(replay_dir)
    if args.cmd == 'checks':
        print('[checks] 生产遥测栈适配检查(coldstart)')
        print('\n'.join(run_checks_on_replay(replay_dir,
                                             args.recent or 5)))
        return
    if not runs:
        print('(无 replay 数据)')
        return
    if args.recent:
        print(f"—— 最近 {args.recent} 局 ——")
        for rid in runs[-args.recent:]:
            best = _load_decisions_rounds(replay_dir, rid)
            abn = query_anomalies(replay_dir, rid)
            outs = read_jsonl(replay_dir / 'outcomes.jsonl')
            mine = [o for o in outs if o.get('run_id') == rid]
            deepest = max(((o.get('plane') or 1, o.get('round_num') or 1) for o in mine),
                          default=(1, 1))
            last = mine[-1] if mine else {}
            print(f"{rid}: P{deepest[0]}r{deepest[1]} | 决策{len(best)}轮 | 异常 {len(abn)} 条"
                  f" | 末态 hp={last.get('hp_after')} comp={last.get('comp_tag')}")
        return
    rid = args.run or runs[-1]
    print(f"=== {rid} ===")
    if args.view in ('rounds', 'all'):
        print('[rounds]')
        print('\n'.join(query_rounds(replay_dir, rid)))
    if args.view in ('supply', 'all'):
        print('[supply]')
        print('\n'.join(query_supply(replay_dir, rid)))
    if args.view in ('tiers', 'all'):
        print('[tiers]')
        print('\n'.join(query_tiers(replay_dir, rid)))
    if args.view in ('planexec', 'all'):
        print('[planexec]')
        print('\n'.join(query_plan_vs_exec(replay_dir, rid)))
    if args.view in ('anomalies', 'all'):
        print('[anomalies]')
        abn = query_anomalies(replay_dir, rid)
        print('\n'.join(abn) if abn else '  ✓ 无异常标记')
    if args.view in ('hp', 'all'):
        print('[hp]')
        print('\n'.join(query_hp(replay_dir, rid)))
    if args.view in ('economy', 'all'):
        print('[economy]')
        print('\n'.join(query_economy(replay_dir, rid)))


if __name__ == '__main__':
    _cli_main()
