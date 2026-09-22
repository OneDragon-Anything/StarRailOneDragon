"""遥测采集保留面(删除波 1 后)。

旧 12 流中「策略源收编 9 流」(decisions/outcomes/exogenous/spend_ledger/
shop_snapshots/exec_events/invest_cards/obs_conflicts/runs)的写入端已随
用户 2026-09-10 直迁裁定整段删除(处置表单一源 =
docs/develop/sr_od/application/currency_war/game_state/retirement.md §2;历史档案只读,
判读唯一读面 = telemetry/journal_query 新账视图族——W3 删旧读面后
telemetry/query 只余纯函数单一源)。本模块保留:

- TelemetryRecorder:进程级落盘根槽载体(replay_dir/enabled;测试经
  telemetry.state.set_recorder_replay_dir 换根,装配面语义不变)+ 缺陷
  台账写入(record_defect;保留专用流,候裁面见处置表 defect_ledger 行)。
  (snapshot_expected_paths 挂起期望快照 helper 已随 两态制
  退役删除——expected_state 条目表拆除无快照可取。)

旧内存累积面(gold 轨迹/comps 序列/难度表)随 runs 流写入端一并退役——
其唯一消费方是局终 summary 派生列,退役后无写入消费方。
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_observe import DEFAULT_REPLAY_DIR
from sr_od.application.currency_war.kernel.cw_state_journal import (
    JOURNAL_NONLIVE_RETENTION_DAYS,
    JOURNAL_RETENTION_DAYS,
    REAL_RUN_ID_RE,
)
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

#: 缺陷台账文件名(写入与寿命联动清理同取一源,防字面量漂移分叉)。
DEFECT_LEDGER_NAME: str = 'defect_ledger.jsonl'

#: 台账段淘汰 manifest 文件名(台账同目录;journal.retirement.jsonl 同构
#: 显影面——判读者下钻台账行扑空时查本文件辨「清理 vs 丢数据」)。
DEFECT_LEDGER_RETIREMENT_MANIFEST_NAME: str = 'defect_ledger.retirement.jsonl'


class TelemetryRecorder:
    """落盘根槽载体 + 缺陷台账写入器。enabled=False 时写入 no-op(测试门)。

    生产单例经 telemetry.state.get_recorder()(enabled=True,写
    .debug/currency_war/telemetry/live/);唯一现役流 = 缺陷台账
    (record_defect;op_journal 工程诊断流已随 2026-09-15 用户裁定退役,
    op 调用流归宿 = server 主日志 [cw-op] 行;board_state_archive 写入点
    已退役、存量档案只读;cw4 计数流已随 R5 W4 流删退役,聚合归宿 =
    局终域行载荷 MatchFinal.cw4_counters,r5-migration-plan.md §2 W4)。
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
        self._append(DEFECT_LEDGER_NAME, _to_jsonable(rec))


# ===== 寿命联动:defect_ledger run 段清理(journal 段裁决的跟随者)=====
# 联动契约(寿命联动随 run 段同批淘汰;框架 =
# kernel.cw_state_journal 三道闸):defect_ledger 段随 journal run 段
# 生命周期同窗清理、同 manifest 显影,禁另起独立清理周期(双源漂移禁令)
# ——触发点唯一 = journal 装配趟(kernel install_state_telemetry),本侧
# 只做跟随,不自设周期。段裁决两分:
# - 共享段(run_id 在 journal 段名册内):**严格跟随** journal 归因,禁自评
#   段龄——台账行止于本局末次缺陷,段末 ts 早于 journal 段末行,自评恒比
#   journal 「老」,会把 journal 仍保留段的索引行先清掉(证据还在而索引
#   先丢,比双留更坏);journal 实际淘汰段以 summary.reasons 为准(与
#   retired 同生死,重写失败轮恒空 = 跟随者自动不跟)。
# - 孤儿段(journal 常开化前历史段,册外):同常量同窗自评补判
#   (REAL_RUN_ID_RE 分型 + JOURNAL_RETENTION_DAYS/JOURNAL_NONLIVE_
#   RETENTION_DAYS;2026-09-12 实测:现役台账 141 段 14.0MB 全为册外
#   实机形态段,纯跟随对其零作用,不补判龄则历史体积永不回落)。这不构成
#   第二清理周期——触发点/常量/reason 值域全承 journal 同一趟,仅对裁决源
#   无意见(册外)的段补判龄;journal 有意见的段一律以 journal 为准。

def enforce_defect_ledger_retention(
        ledger_path: Path | str, *,
        journal_retirement: dict[str, Any],
        now: datetime | None = None) -> dict[str, Any]:
    """按 journal 段裁决清理 defect_ledger 对应 run 段(整段单元)。

    - ``journal_retirement`` = :func:`kernel.cw_state_journal.
      enforce_journal_retention` 返回段账(``segments`` 段名册 +
      ``reasons`` 实际淘汰归因;缺键按空册/空归因处理);
    - 清理单元 = run 段整体(禁段内部分行删);坏行/无 run_id 行原样保留
      (宽容契约,清理面不判定);无 ts 册外段不判龄不清理(宁保留不误删);
    - 被清段逐段写 manifest(``defect_ledger.retirement.jsonl``,台账同
      目录)一行 ``{run_id, archived_out, reason, rows, first_ts, last_ts,
      retired_at}``(journal manifest 同构,reason 承 RETIRE_REASONS 值域)
      ——manifest 只增不改,写入失败 = 放弃本轮(宁不删,不可删了没记账);
    - 文件重写 = 临时文件 + ``os.replace`` 原子改名,3×0.5s 退避重试
      (Windows 读端短持句柄共享冲突,同 kernel 治本口径);重写失败 =
      顺延下趟,原文件未损;
    - 返回 ``{'checked': 段数, 'retired': [run_id...], 'rows_dropped': n}``。
    """
    path = Path(ledger_path)
    result: dict[str, Any] = {'checked': 0, 'retired': [], 'rows_dropped': 0}
    if not path.exists():
        return result
    roster = set(journal_retirement.get('segments') or [])
    decisions = dict(journal_retirement.get('reasons') or {})
    rows: list[Any] = []
    with path.open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                rows.append(line)   # 坏行原样保留(宽容契约,清理面不判定)
                continue
            rows.append(parsed if isinstance(parsed, dict) else parsed)
    seg_rows: dict[str, list[int]] = {}
    seg_last_ts: dict[str, str] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        rid = str(row.get('run_id') or '')
        if not rid:
            continue
        seg_rows.setdefault(rid, []).append(i)
        ts = str(row.get('ts') or '')
        if ts and ts > seg_last_ts.get(rid, ''):
            seg_last_ts[rid] = ts
    result['checked'] = len(seg_rows)
    if not seg_rows:
        return result
    now_epoch = (now or datetime.now()).timestamp()
    # epoch 归一基准与 kernel 同口径:naive 串按本地时区解释(生产写端 =
    # 本地 naive ISO 串),解析失败段不判龄不清理。
    cutoff_real = now_epoch - JOURNAL_RETENTION_DAYS * 86400.0
    cutoff_nonlive = now_epoch - JOURNAL_NONLIVE_RETENTION_DAYS * 86400.0
    retire_reason: dict[str, str] = {}
    for rid in seg_rows:
        if rid in roster:
            # 共享段:严格跟随 journal 归因(册内无归因 = journal 保留,不跟)
            if rid in decisions:
                retire_reason[rid] = str(decisions[rid])
            continue
        ts = seg_last_ts.get(rid, '')
        if not ts:
            continue
        try:
            age = datetime.fromisoformat(ts).timestamp()
        except ValueError:
            continue
        if REAL_RUN_ID_RE.match(rid):
            if age <= cutoff_real:
                retire_reason[rid] = 'age_real'
        elif age <= cutoff_nonlive:
            retire_reason[rid] = 'age_non_real'
    retired_ids = list(retire_reason)
    if not retired_ids:
        return result
    retired_idx: set[int] = set()
    for rid in retired_ids:
        retired_idx.update(seg_rows[rid])
    # manifest 显影(逐段一行;追加,历次淘汰记录累积)
    manifest_path = path.parent / DEFECT_LEDGER_RETIREMENT_MANIFEST_NAME
    retired_at = datetime.fromtimestamp(now_epoch).isoformat(timespec='seconds')
    try:
        with manifest_path.open('a', encoding='utf-8') as mf:
            for rid in retired_ids:
                idxs = seg_rows[rid]
                ts_list = sorted(str(rows[i].get('ts') or '')
                                 for i in idxs)
                mf.write(json.dumps({
                    'run_id': rid, 'archived_out': True,
                    'reason': retire_reason[rid],
                    'rows': len(idxs),
                    'first_ts': ts_list[0] if ts_list else '',
                    'last_ts': ts_list[-1] if ts_list else '',
                    'retired_at': retired_at,
                }, ensure_ascii=False) + '\n')
    except Exception as e:  # noqa: BLE001  显影失败 = 放弃本轮清理(宁不删
        # 不可发生「删了没记账」——manifest 是段存续的唯一判别面)
        log.warning('[cw!][defect-ledger] 淘汰 manifest 写入失败(本轮不清理): %s', e)
        return result
    # 原子重写(保留行 = 非淘汰段行 + 原样保留的坏行/无 run_id 行)
    keep = [row for i, row in enumerate(rows) if i not in retired_idx]
    result['retired'] = retired_ids
    result['rows_dropped'] = len(retired_idx)
    tmp_name: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent),
                                        suffix='.jsonl.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for row in keep:
                if isinstance(row, str):
                    f.write(row + '\n')
                else:
                    f.write(json.dumps(row, ensure_ascii=False) + '\n')
        # 原子改名退避重试:Windows 上读端以共享读短持句柄打开目标时
        # MoveFileEx 报 WinError 5——读端读完即关,0.5s 退避即可过
        # (kernel.cw_state_journal 同因同治本口径,实测)。
        last_err: Exception | None = None
        for _ in range(3):
            try:
                os.replace(tmp_name, path)
                last_err = None
                break
            except OSError as e:
                last_err = e
                time.sleep(0.5)
        if last_err is not None:
            raise last_err
    except Exception as e:  # noqa: BLE001  重写失败不阻塞装配(原文件未损,
        # 下一趟装配重试;manifest 已记账 → 消费方以文件实况为准);失败
        # tmp 清除(残留即占盘,kernel 同纪律)。
        log.warning('[cw!][defect-ledger] 台账重写失败(段清理顺延): %s', e)
        if tmp_name is not None:
            Path(tmp_name).unlink(missing_ok=True)
        result['retired'] = []
        result['rows_dropped'] = 0
        return result
    by_reason: dict[str, list[str]] = {}
    for rid in retired_ids:
        by_reason.setdefault(retire_reason[rid], []).append(rid)
    log.info('[cw][defect-ledger] 寿命联动清理:淘汰 %d 段 %d 行: %s',
             len(retired_ids), result['rows_dropped'],
             '; '.join(f'{reason}={ids}' for reason, ids in by_reason.items()))
    return result


def follow_journal_retirement(telemetry_root: Path,
                              summary: dict[str, Any]) -> None:
    """journal 段淘汰的台账联动跟随者(kernel ``set_retirement_follower``
    槽的注入实现;生产武装点 = ``telemetry.defects.install_exit_hooks``,
    与出口钩子/安灯同点显式接通,缺省关)。

    telemetry_root = journal 所在 state 目录的父目录(kernel 只识根,文件
    名归本域单一源 :data:`DEFECT_LEDGER_NAME`)——生产 = telemetry live 根;
    测试 tmp 装配即派生 tmp 根,缺文件零成本 no-op。异常上抛交 kernel
    install 口吞(log.warning,不阻塞装配)。
    """
    enforce_defect_ledger_retention(Path(telemetry_root) / DEFECT_LEDGER_NAME,
                                    journal_retirement=summary)

