"""统一 state 状态流水落盘(R5 W1 起无条件常开)。

设计裁定正本 = ``docs/develop/currency_war/decisions/0630-unified-state-journal.md``
(ADR-0630,含修订节)+ ``docs/develop/currency_war/decisions/0634-state-journal-always-on.md``
(ADR-0634,影子双写推翻:journal 无条件常开,无开关无影子期;记录机制
as-built 正本面 = ``docs/develop/currency_war/game_state/journal.md``)。
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

本模块只管「行进了内存之后」的事(缓冲/序列化/落盘/装配);行的组装与
版本分配在写入口(kernel/cw_board_state ``BoardState._swap``,分配与状态
变更同临界区)。
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from one_dragon.utils.log_utils import log

#: 缺省批量 flush 阈值(行数;崩溃丢失窗上限 = 阈值;量级对齐 journal.md §5
#: 「批量 flush(阈值随实现批定)」——首版取 64,实测后随单局体积口径
#: (ADR-0630 后果节 M1 三口径)耦合调)。
DEFAULT_FLUSH_EVERY: int = 64


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
