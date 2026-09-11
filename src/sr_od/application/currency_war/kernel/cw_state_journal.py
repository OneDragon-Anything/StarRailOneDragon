"""统一 state 状态流水落盘(R5 W1 起无条件常开)。

设计裁定正本 = ``docs/develop/sr_od/application/currency_war/decisions/0630-unified-state-journal.md``
(ADR-0630,含修订节)+ ``docs/develop/sr_od/application/currency_war/decisions/0634-state-journal-always-on.md``
(ADR-0634,影子双写推翻:journal 无条件常开,无开关无影子期;记录机制
as-built 正本面 = ``docs/develop/sr_od/application/currency_war/game_state/journal.md``)。
形态:流程侧唯一落盘流 ``state/journal.jsonl``,每次 state 写入一行,行 =
改了什么 + 渠道签名 + 版本 id + **写入后完整 state 快照**——行行自足,
查询直接读行(journal.md §1);无快照锚、无周期节奏、无对账自检、无前溯
推导(v2 增量账+快照锚+对账自检整套随 v3 根本性纠正作废,禁回归,
ADR-0630 裁定 1)。

落盘形态(journal.md §5):内存追加 + 规范化序列化,磁盘批量 flush(缓冲满
阈值落盘)——同步关键路径零逐行 open/write;崩溃丢失窗 = 未 flush 尾部,该窗
内时点无行 = 诚实缺失,无补建机制。

常开语义(ADR-0634):本模块无开关,生产装配单点 = ``currency_war_app``
装配段无条件调 :func:`install_state_telemetry`;写路径(字段写入/版本分配)
不因本模块存在与否分支,行落盘另以 sink 在场与 run_id 在场为准——缺实例
(单元测试/工具环境)= 行不落,诚实缺失。单文件 + 行内 run_id 列(per-run
分文件候选已否决,journal.md §1);局外写入拒绝(run_id 空 = 不写假行,
journal.md §5)。

寿命契约(R5 W3 装配端;retirement.md §6-5 直迁形态):滚动清理以 **run 段**
为整体单元(段 = 行内 run_id 归属,整段淘汰禁切半段),已淘汰段的 state_ref
钉 = 永久 unverified,淘汰动作在本模块 manifest(``journal.retirement.jsonl``,
journal 同目录)逐段显影(archived_out;判读者钉解析失败时查 manifest 可辨
「清理」与「丢数据」);保留窗下限 = 跨期语料窗(缺省常量,清理策略随真实
数据积累再调,无观察窗计时)。清理时点 = 装配(:func:`install_state_telemetry`
前置)——单进程写端未启动,零并发窗;活跃段(最新 run_id)永不清理。

本模块只管「行进了内存之后」的事(缓冲/序列化/落盘/装配/寿命);行的组装与
版本分配在写入口(kernel/cw_board_state ``BoardState._swap``,分配与状态
变更同临界区)。
"""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from one_dragon.utils.log_utils import log

#: 缺省批量 flush 阈值(行数;崩溃丢失窗上限 = 阈值;量级对齐 journal.md §5
#: 「批量 flush(阈值随实现批定)」——首版取 64,实测后随单局体积口径
#: (ADR-0630 后果节 M1 三口径)耦合调)。
DEFAULT_FLUSH_EVERY: int = 64

#: journal 段保留窗(天;寿命契约保留窗下限 = 跨期语料窗,retirement.md
#: §6-5。缺省 30 天 = 跨月对照语料窗的保守值;清理策略随常开化后真实数据
#: 积累定,无观察窗计时——R5 直迁口径,r5-migration-plan.md §4-5)。
JOURNAL_RETENTION_DAYS: int = 30

#: 段淘汰 manifest 文件名(journal 同目录;逐段一行 archived_out 显影,
#: 判读者 state_ref 钉解析失败时的「清理 vs 丢数据」判别面)。
RETIREMENT_MANIFEST_NAME: str = 'journal.retirement.jsonl'


class StateJournal:
    """状态流水单文件追加器(内存缓冲 + 批量 flush)。

    - :meth:`append` 接收写入口组装好的完整行 dict(自足快照行);
    - 缓冲满 :attr:`flush_every` 行自动落盘;局外行(run_id 空)在写入口
      已拒,此处再门一道(防御性,装配口可换);
    - 全链 best-effort:落盘失败不毒化业务流(log.warning 留痕)。
    """

    def __init__(self, path: Path | str, *, flush_every: int = DEFAULT_FLUSH_EVERY) -> None:
        self._path = Path(path)
        self._flush_every = max(int(flush_every), 1)
        self._buffer: list[dict] = []

    @property
    def path(self) -> Path:
        """落盘文件路径。"""
        return self._path

    @property
    def rows(self) -> list[dict]:
        """当前内存缓冲的行(测试/诊断读口;已 flush 的行不在此列)。"""
        return list(self._buffer)

    @property
    def buffered(self) -> int:
        """缓冲行数。"""
        return len(self._buffer)

    def append(self, row: dict[str, Any]) -> None:
        """追加一行(完整自足行 dict;局外行拒写)。"""
        if not str(row.get('run_id', '') or ''):
            return   # 局外写入拒绝(§3.2.3;写入口已门,防御性再门)
        self._buffer.append(row)
        if len(self._buffer) >= self._flush_every:
            self.flush()

    def flush(self) -> int:
        """把缓冲行批量落盘(追加 JSONL;返回本次落盘行数)。"""
        if not self._buffer:
            return 0
        pending = self._buffer
        self._buffer = []
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open('a', encoding='utf-8') as f:
                for row in pending:
                    f.write(json.dumps(row, ensure_ascii=False) + '\n')
            return len(pending)
        except Exception as e:  # noqa: BLE001  记录层 best-effort
            log.warning('[cw!][state-journal] flush 失败(丢 %d 行,业务流不受阻): %s',
                        len(pending), e)
            return 0

    def close(self) -> int:
        """收口 flush(局终/复位时点;丢失窗上界收敛到本时点)。"""
        return self.flush()


def enforce_journal_retention(journal_path: Path | str, *,
                              now: datetime | None = None,
                              retention_days: int = JOURNAL_RETENTION_DAYS,
                              ) -> dict[str, Any]:
    """run 段粒度滚动清理(寿命契约;装配前置时点调,单进程写端未启动)。

    契约(retirement.md §6-5 直迁形态):
    - 清理单元 = **run 段整体**(行内 run_id 归属;禁切半段——段内版本序
      完整性是 state_ref 钉解析的前提);
    - 段龄判据 = 段内最大行 ts 距 ``now`` 超过 ``retention_days`` 天;
    - **活跃段永不清理**(最新段 = 现役局,可能与进程内缓冲/下一局续写
      交叠,段龄判据对其无意义);
    - 被淘汰段逐段写 manifest(``journal.retirement.jsonl``,journal 同
      目录)一行 ``{run_id, archived_out: true, rows, first_ts, last_ts,
      retired_at}`` 显影——钉解析失败 = 查 manifest 辨「清理 vs 丢数据」;
    - 文件重写 = 临时文件 + ``os.replace`` 原子改名(中断读者不读半截);
    - 坏行/无 ts 行/无 run_id 行 = 原样保留(宽容契约:清理面不做判定,
      禁把半行当合法行删);
    - 返回 ``{'checked': 段数, 'retired': [run_id...], 'rows_dropped': n}``。

    为什么挂在装配前置而非收口:装配时点单进程写端未启动(零并发窗),
    收口时点进程可能即将续写下一局(缓冲/flush 交叠窗);滚动语义由每次
    进程装配触发承载(每次启动清一次,频率对「保留窗 = 天级」足够)。
    """
    path = Path(journal_path)
    summary: dict[str, Any] = {'checked': 0, 'retired': [],
                               'rows_dropped': 0}
    if not path.exists():
        return summary
    # epoch 归一基准:naive 串按本地时区解释(生产写端 = 本地 naive ISO 串),
    # aware 串自带时区正确转 epoch;两端同走 epoch 比较无 naive/aware 混算。
    now_epoch = (now or datetime.now()).timestamp()
    rows: list[dict[str, Any]] = []
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
    # 段账:run_id → 行下标集 + 段内最大 ts
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
    summary['checked'] = len(seg_rows)
    if not seg_rows:
        return summary
    # 活跃段 = 段末行 ts 最大的段(流内行序 = 版本序,段末行最新)
    active_seg = max(seg_rows, key=lambda r: (seg_last_ts.get(r, ''), r))
    cutoff = now_epoch - retention_days * 86400.0

    def _stale(rid: str) -> bool:
        ts = seg_last_ts.get(rid, '')
        if not ts:
            return False   # 无 ts 段不可判龄,不清理(宁保留不误删)
        try:
            age = datetime.fromisoformat(ts).timestamp()
        except ValueError:
            return False
        return age <= cutoff

    retired_ids = [rid for rid in seg_rows
                   if rid != active_seg and _stale(rid)]
    if not retired_ids:
        return summary
    retired_idx: set[int] = set()
    for rid in retired_ids:
        retired_idx.update(seg_rows[rid])
    # manifest 显影(逐段一行;追加,历次淘汰记录累积)
    manifest_path = path.parent / RETIREMENT_MANIFEST_NAME
    retired_at = datetime.fromtimestamp(now_epoch).isoformat(timespec='seconds')
    try:
        with manifest_path.open('a', encoding='utf-8') as mf:
            for rid in retired_ids:
                idxs = seg_rows[rid]
                ts_list = sorted(str(rows[i].get('ts') or '')
                                 for i in idxs if isinstance(rows[i], dict))
                mf.write(json.dumps({
                    'run_id': rid, 'archived_out': True,
                    'rows': len(idxs),
                    'first_ts': ts_list[0] if ts_list else '',
                    'last_ts': ts_list[-1] if ts_list else '',
                    'retired_at': retired_at,
                }, ensure_ascii=False) + '\n')
    except Exception as e:  # noqa: BLE001  显影失败 = 放弃本轮清理(宁不删
        # 不可发生「删了没记账」——manifest 是段存续的唯一判别面)
        log.warning('[cw!][state-journal] 淘汰 manifest 写入失败(本轮不清理): %s', e)
        return summary
    # 原子重写(保留行 = 非淘汰段行 + 原样保留的坏行)
    keep = [row for i, row in enumerate(rows) if i not in retired_idx]
    summary['retired'] = retired_ids
    summary['rows_dropped'] = len(retired_idx)
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
        os.replace(tmp_name, path)
    except Exception as e:  # noqa: BLE001  重写失败不阻塞装配(原文件未损,
        # 下一轮装配重试;manifest 已记账 → 判别面仍一致:记录了的段可能
        # 尚在,消费方以文件实况为准,manifest 只增不改)
        log.warning('[cw!][state-journal] journal 重写失败(段清理顺延): %s', e)
        summary['retired'] = []
        summary['rows_dropped'] = 0
        return summary
    log.info('[cw][state-journal] 寿命契约清理:淘汰 %d 段 %d 行'
             '(保留窗 %d 天): %s', len(retired_ids), summary['rows_dropped'],
             retention_days, ', '.join(retired_ids))
    return summary


#: 进程内单槽(装配口;缺省 None = 无落盘实例——写路径照常,仅行不落)。
_ACTIVE_JOURNAL: StateJournal | None = None


def state_journal_instance() -> StateJournal | None:
    """现役流水实例(无实例 = None)。"""
    return _ACTIVE_JOURNAL


def install_state_telemetry(path: Path | str | None = None, *,
                            flush_every: int = DEFAULT_FLUSH_EVERY,
                            run_id_provider: Callable[[], str] | None = None) -> StateJournal:
    """装配状态流水(幂等:重入先复位再装,防双槽叠加)。

    - R5 W1 常开化(ADR-0634):本口无开关语义,生产 = currency_war_app
      装配段无条件调用;影子双写/缺省关纪律已销案(ADR-0630 决策 6 被推翻);
    - path = 流水落盘路径;None = 生产缺省 ``<live 根>/state/journal.jsonl``
      (§3.0 落盘根:与旧流同根,哨兵/装配路径习惯延续);
    - run_id_provider = run 归属读取函数(必传,生产 = telemetry 现读口;
      kernel 禁依 telemetry——桶依赖矩阵锁,依赖倒置经本参数注入);
      None = 行全视为局外拒写(装配只启半,生产勿用);
    - 装配 = StateJournal 实例 + 注册为 BoardState 写入口的行外送钩子与
      run 归属供给槽(:func:`cw_board_state.set_state_journal_sink` /
      ``set_run_id_provider``)——写路径不因本槽分支,sink 缺席 = 行不落。
    """
    global _ACTIVE_JOURNAL
    reset_state_telemetry()
    if path is None:
        from sr_od.application.currency_war.kernel.cw_observe import LIVE_DIR
        path = LIVE_DIR / 'state' / 'journal.jsonl'
    # 寿命契约清理(R5 W3 装配端):写端未启动的零并发窗,每进程装配触发
    # 一次段粒度滚动清理(见 enforce_journal_retention 注);失败不阻塞装配。
    try:
        enforce_journal_retention(path)
    except Exception as e:  # noqa: BLE001  装配主路径不受清理面故障波及
        log.warning('[cw!][state-journal] 段清理失败(不阻塞装配): %s', e)
    journal = StateJournal(path, flush_every=flush_every)

    from sr_od.application.currency_war.kernel.cw_board_state import (
        set_run_id_provider,
        set_state_journal_sink,
    )
    set_state_journal_sink(journal.append)
    if run_id_provider is not None:
        set_run_id_provider(run_id_provider)
    _ACTIVE_JOURNAL = journal
    log.info('[cw][state-journal] journal 装配(常开):path=%s flush_every=%d',
             journal.path, journal._flush_every)
    return journal


def reset_state_telemetry() -> None:
    """复位流水实例(收口 flush + 摘钩子与 run 归属供给槽;测试 teardown 与
    重装前调)。

    为什么收口成单点:槽 = 进程级全局,残留会把后续局的流水行带进旧句柄
    (与 telemetry.state 复位簇同病理);生产重装经 install 的幂等口,
    本函数亦为其前置。
    """
    global _ACTIVE_JOURNAL
    journal = _ACTIVE_JOURNAL
    if journal is not None:
        journal.close()
        _ACTIVE_JOURNAL = None
    from sr_od.application.currency_war.kernel.cw_board_state import (
        set_run_id_provider,
        set_state_journal_sink,
    )
    set_state_journal_sink(None)
    set_run_id_provider(None)
