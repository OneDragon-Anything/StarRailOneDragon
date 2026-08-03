"""货币战争 决策迹采集(telemetry;纯逻辑,可测,不碰游戏)。

**用户 2026-08-03 要求**:搜集足够数据支持后续策略优化。设计原则(贯彻):**ML 只采集、不主依赖**
—— debug 开关在关键决策点序列化(GameState + eval 特征分解 + 动作 + 下回合观测结果),给人肉眼
复盘 + 留作未来 ML 的 side door。**采集价值耐久(schema 稳定),训练价值版本短命**(V4.4 训的 V4.5 废)。
→ 采集管线现在就建,训练以后再说。永远采集,可能永远不训练。

**事件流三路 JSONL**(append-only,按 run_id+round_num join,标准 event-sourcing):
- ``decisions.jsonl``:每回合决策迹(state 快照 + target_comp + candidate_scores + eval_breakdown + actions)。
- ``outcomes.jsonl``:每回合观测结果(RoundOutcome 双侧)。
- ``runs.jsonl``:每局 summary(difficulty / result / plane_reached / pivots / gold 轨迹)。

**schema 稳定**:字段名跨版本不变(``schema_version`` 标版本);数值随版本/实玩变。新增字段加在末尾、
可选,不破坏旧记录。复盘/ML 代码按 (run_id, round_num) join decisions ↔ outcomes。

**门控**:`enabled=False` 时 record 全 no-op(生产默认关,debug/复盘开)。路径默认
``.debug/temp/currency_war/replay/``(不入 git)。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.cw_state import Action, GameState

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
    """GameState → JSON-safe dict(剔除大且无决策价值的字段由调用方按需;默认全量)。"""
    return _to_jsonable(state)


def serialize_action(action: Action) -> dict[str, Any]:
    """单 Action → JSON-safe dict(带 type 标签,便于复盘识别)。"""
    d = _to_jsonable(action)
    d["__type__"] = type(action).__name__
    return d


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
    gold: int = 0                                 # 决策时 gold(冗余,便于 gold 轨迹)


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


@dataclass
class RunSummary:
    """单局 summary(runs.jsonl 一行)。"""
    schema_version: int = SCHEMA_VERSION
    ts: str = ""
    run_id: str = ""
    difficulty: str = ""
    result: str = ""                # "win" / "loss" / "abandoned"
    plane_reached: int = 0          # 到达的最高位面
    rounds_survived: int = 0
    final_hp: int = 0
    comps_committed: list[str] = field(default_factory=list)   # commit 过的 comp 名序列(含 pivot)
    pivot_count: int = 0
    gold_trajectory: list[int] = field(default_factory=list)   # 每回合 gold(经济复盘)
    notes: str = ""


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

    def _path(self, name: str) -> Path:
        return self.replay_dir / name

    def _append(self, name: str, payload: dict[str, Any]) -> None:
        """append 一行 JSON(name.jsonl)。enabled=False 时 no-op。"""
        if not self.enabled:
            return
        self.replay_dir.mkdir(parents=True, exist_ok=True)
        with self._path(name).open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def start_run(self, run_id: str, difficulty: str) -> None:
        """登记一次 run(difficulty 记录,便于后续 summary)。"""
        if not self.enabled:
            return
        self._difficulty[run_id] = difficulty
        self._gold_trajectory.setdefault(run_id, [])
        self._comms.setdefault(run_id, [])

    def record_decision(self, run_id: str, difficulty: str, state: GameState,
                        target_comp: str, candidate_scores: dict[str, float],
                        eval_breakdown: dict[str, float], actions: list[Action]) -> None:
        """记一条决策迹(decisions.jsonl)。target_comp='' 表示 reactive 无 target。"""
        trace = DecisionTrace(
            ts=datetime.now().isoformat(timespec="seconds"),
            run_id=run_id, difficulty=difficulty,
            round_num=state.round_num, plane=state.plane,
            state=serialize_state(state),
            target_comp=target_comp,
            candidate_scores=dict(candidate_scores),
            eval_breakdown=dict(eval_breakdown),
            actions=[serialize_action(a) for a in actions],
            hp=state.hp, gold=state.gold,
        )
        if self.enabled:
            self._gold_trajectory.setdefault(run_id, []).append(state.gold)
            if target_comp:
                comms = self._comms.setdefault(run_id, [])
                if not comms or comms[-1] != target_comp:
                    comms.append(target_comp)
        self._append("decisions.jsonl", _to_jsonable(trace))

    def record_outcome(self, run_id: str, outcome) -> None:
        """记一条观测结果(outcomes.jsonl)。outcome: cw_performance.RoundOutcome。"""
        rec = OutcomeRecord(
            ts=datetime.now().isoformat(timespec="seconds"),
            run_id=run_id,
            round_num=outcome.round_num, plane=outcome.plane,
            node_type=outcome.node_type, comp_tag=outcome.comp_tag,
            intentional_fold=outcome.intentional_fold,
            hp_after=outcome.hp_after, hp_confidence=outcome.hp_confidence,
            enemy_hp_after=outcome.enemy_hp_after,
            damage_dealt=outcome.damage_dealt, killed=outcome.killed,
        )
        self._append("outcomes.jsonl", _to_jsonable(rec))

    def record_run_summary(self, run_id: str, result: str, plane_reached: int,
                           rounds_survived: int, final_hp: int,
                           pivot_count: int = 0, notes: str = "") -> None:
        """记一条局终 summary(runs.jsonl)。comms/gold 轨迹从内存累积取。"""
        summary = RunSummary(
            ts=datetime.now().isoformat(timespec="seconds"),
            run_id=run_id,
            difficulty=self._difficulty.get(run_id, ""),
            result=result, plane_reached=plane_reached, rounds_survived=rounds_survived,
            final_hp=final_hp,
            comps_committed=list(self._comms.get(run_id, [])),
            pivot_count=pivot_count,
            gold_trajectory=list(self._gold_trajectory.get(run_id, [])),
            notes=notes,
        )
        self._append("runs.jsonl", _to_jsonable(summary))
        # 清理内存累积
        self._gold_trajectory.pop(run_id, None)
        self._comms.pop(run_id, None)
        self._difficulty.pop(run_id, None)


# ===== 模块级单例 + run_id 跟踪(ops 不改签名即可采集)=====
# telemetry 是横切关注点,用模块级 recorder + current_run_id,避免给 BuyShopCards / loop
# 线程传参。CurrencyWarRunLoop 在 __init__ 调 start_run(生成 run_id),BuyShopCards 用
# current_run_id() 取,loop 在战斗后 record_outcome、局终 record_run_summary。
# 默认 enabled=True(用户 2026-08-03 要数据调优;写 .debug/ 不入 git,I/O <1ms 不影响备战实时)。
_RECORDER: TelemetryRecorder | None = None
_CURRENT_RUN_ID: str = ""
_CURRENT_DIFFICULTY: str = ""


def get_recorder() -> TelemetryRecorder:
    """模块级 recorder 单例(默认 enabled,写 .debug/temp/currency_war/replay/)。"""
    global _RECORDER
    if _RECORDER is None:
        _RECORDER = TelemetryRecorder(enabled=True)
    return _RECORDER


def start_run(difficulty: str = "") -> str:
    """开始一次 run:生成 run_id(时间戳)+ start_run。返回 run_id。loop __init__ 调。"""
    global _CURRENT_RUN_ID, _CURRENT_DIFFICULTY
    _CURRENT_RUN_ID = datetime.now().strftime('run_%Y%m%d_%H%M%S')
    _CURRENT_DIFFICULTY = difficulty
    get_recorder().start_run(_CURRENT_RUN_ID, difficulty)
    return _CURRENT_RUN_ID


def current_run_id() -> str:
    return _CURRENT_RUN_ID


def record_decision(state: GameState, target_comp: str,
                    candidate_scores: dict[str, float], eval_breakdown: dict[str, float],
                    actions: list[Action]) -> None:
    """便捷:用 current_run_id 记一条决策迹。BuyShopCards plan 后调。"""
    if not _CURRENT_RUN_ID:
        return
    get_recorder().record_decision(_CURRENT_RUN_ID, _CURRENT_DIFFICULTY, state,
                                   target_comp, candidate_scores, eval_breakdown, actions)


def record_outcome(outcome) -> None:
    """便捷:用 current_run_id 记一条观测结果。loop 战斗后调。"""
    if not _CURRENT_RUN_ID:
        return
    get_recorder().record_outcome(_CURRENT_RUN_ID, outcome)


def record_run_summary(result: str, plane_reached: int, rounds_survived: int,
                       final_hp: int, notes: str = "") -> None:
    """便捷:用 current_run_id 记局终 summary。loop 局终调。"""
    if not _CURRENT_RUN_ID:
        return
    get_recorder().record_run_summary(_CURRENT_RUN_ID, result, plane_reached,
                                      rounds_survived, final_hp, notes=notes)



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
    """按 (run_id, round_num) join decisions ↔ outcomes → 每回合一条合并记录(复盘/ML 用)。

    decisions 主表,outcomes 左 join(无 outcome 的决策 outcome 字段为 None)。
    """
    decisions = read_jsonl(Path(replay_dir) / "decisions.jsonl")
    outcomes = read_jsonl(Path(replay_dir) / "outcomes.jsonl")
    out_by_key = {(o["run_id"], o["round_num"]): o for o in outcomes}
    joined: list[dict[str, Any]] = []
    for d in decisions:
        key = (d.get("run_id"), d.get("round_num"))
        merged = dict(d)
        merged["outcome"] = out_by_key.get(key)
        joined.append(merged)
    return joined
