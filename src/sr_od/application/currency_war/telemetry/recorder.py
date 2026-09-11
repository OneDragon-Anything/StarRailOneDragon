"""遥测采集保留面(删除波 1 后)。

旧 12 流中「策略源收编 9 流」(decisions/outcomes/exogenous/spend_ledger/
shop_snapshots/exec_events/invest_cards/obs_conflicts/runs)的写入端已随
用户 2026-09-10 直迁裁定整段删除(处置表单一源 =
docs/develop/currency_war/game_state/retirement.md §2;历史档案只读,
判读唯一读面 = telemetry/journal_query 新账视图族——W3 删旧读面后
telemetry/query 只余纯函数单一源)。本模块保留:

- TelemetryRecorder:进程级落盘根槽载体(replay_dir/enabled;测试经
  telemetry.state.set_recorder_replay_dir 换根,装配面语义不变)+ 缺陷
  台账写入(record_defect;保留专用流,候裁面见处置表 defect_ledger 行)。
  (snapshot_expected_paths 挂起期望快照 helper 已随 ADR-0651 两态制
  退役删除——expected_state 条目表拆除无快照可取。)

旧内存累积面(gold 轨迹/comps 序列/难度表)随 runs 流写入端一并退役——
其唯一消费方是局终 summary 派生列,退役后无写入消费方。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_observe import DEFAULT_REPLAY_DIR
from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
    SEVERITY_L2_RECORD,
)

# 符号解耦(处死计划批 0):序列化权威副本迁 knowledge/cw_serialize,
# 不再依赖 kernel/cw_intention(死刑判据文件)
from sr_od.application.currency_war.knowledge.cw_serialize import _to_jsonable
from sr_od.application.currency_war.telemetry.schema import (
    DefectRecord,
    append_jsonl,
)

# ===== TelemetryRecorder(落盘根槽载体 + 缺陷台账写入)=====


class TelemetryRecorder:
    """落盘根槽载体 + 缺陷台账写入器。enabled=False 时写入 no-op(测试门)。

    生产单例经 telemetry.state.get_recorder()(enabled=True,写
    .debug/currency_war/telemetry/live/);唯一现役流 = 缺陷台账
    (record_defect;op_journal/board_state_archive 两条保留面各有独立
    写入模块,不经本类;cw4 计数流已随 R5 W4 流删退役,聚合归宿 =
    局终域行载荷 MatchFinal.cw4_counters,ADR-0650)。
    """

    def __init__(self, replay_dir: Path | str = DEFAULT_REPLAY_DIR, enabled: bool = False) -> None:
        self.replay_dir: Path = Path(replay_dir)
        self.enabled: bool = enabled

    def _path(self, name: str) -> Path:
        return self.replay_dir / name

    def _append(self, name: str, payload: dict[str, Any]) -> None:
        """append 一行 JSON(name.jsonl)。enabled=False 时 no-op。"""
        if not self.enabled:
            return
        append_jsonl(self.replay_dir / name, payload)

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

