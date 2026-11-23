"""遥测采集保留面。

旧 12 流中「策略源并入 9 流」(decisions/outcomes/exogenous/spend_ledger/
shop_snapshots/exec_events/invest_cards/obs_conflicts/runs)的写入端已随
用户直迁裁定整段删除(逐流处置表归 git 历史;历史档案只读,
判读唯一读面 = telemetry/journal_query 新账视图族——删旧读面后
telemetry/query 只余纯函数单一源)。本模块保留:

- TelemetryRecorder:进程级落盘根槽载体(replay_dir/enabled;测试经
  telemetry.state.set_recorder_replay_dir 换根,装配面语义不变)。
  缺陷台账(defect_ledger.jsonl)写入面已随缺陷台账废弃拆除
  (用户裁定 2026-11-24;历史台账文件在 .debug 运行产物区留置不迁移),
  recorder 不再承载任何流写入;现存价值 = 落盘根槽(replay_dir 供给
  档案装配/计数快照)。
  (snapshot_expected_paths 挂起期望快照 helper 已随两态制
  停用删除——expected_state 条目表拆除无快照可取。)

旧内存累积面(gold 轨迹/comps 序列/难度表)随 runs 流写入端一并停用——
其唯一消费方是局终 summary 派生列,停用后无写入消费方。
"""

from __future__ import annotations

from pathlib import Path

from sr_od.application.currency_war.kernel.cw_observe import DEFAULT_REPLAY_DIR


class TelemetryRecorder:
    """落盘根槽载体。enabled=False 时写入 no-op(测试门)。

    生产单例经 telemetry.state.get_recorder(enabled=True,写
    .debug/currency_war/telemetry/live/)。缺陷台账流已废弃拆除;
    本类现存职责 = replay_dir 载体(档案装配/计数快照供给口)。
    """

    def __init__(self, replay_dir: Path | str = DEFAULT_REPLAY_DIR, enabled: bool = False) -> None:
        self.replay_dir: Path = Path(replay_dir)
        self.enabled: bool = enabled
