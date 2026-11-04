"""货币战争 策略遥测落盘 sink(DecisionRecord jsonl;capture-store §4)。

槽位与写盘分离:策略包零 I/O(wrapper 只经 ``set_decision_sink`` 注入槽
调本函数),run_id 补齐与局外零写判断都归本函数(策略包禁 import
telemetry——纯逻辑依赖矩阵,N3 攻击裁定)。落点 =
``<recorder 根>/strategy/<strategy_id>_<run_id>.jsonl`` 追加,行行自足;
逐行写后即 flush(决策频度低、行小,无性能面;防进程异常丢尾部记录
——journal ``flush_pending`` 漏行先例)。句柄缓存键含 recorder 根:
根变更(测试重定向 / sim 换根)= 缓存自然失效换新句柄,与
``state.set_recorder_replay_dir`` 换根重建单例语义对齐。
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import TextIO

from sr_od.application.currency_war.telemetry.state import (
    current_run_id,
    get_recorder,
)

# 追加句柄缓存:键 = (recorder 根, strategy_id, run_id)。根变更 = 键变 =
# 旧句柄自然弃用(不主动关闭:进程生命周期内换根次数个位数、残留句柄
# 量级可忽略;主动清理走下方测试复位口)。
_HANDLES: dict[tuple[Path, str, str], TextIO] = {}


def strategy_telemetry_sink(record: dict) -> None:
    """DecisionRecord 追加落盘(wrapper 经装配槽调用)。

    信封 ``run_id`` 由本函数补齐(wrapper 信封不含此键);局外
    (run_id 空)= 零写直接返回(回执域落盘同语义)。异常如实上抛,
    由 wrapper 的 best-effort 守卫吞掉(记录层故障不毒化决策返回值)。
    """
    run_id = str(current_run_id() or '')
    if not run_id:
        return   # 局外零写
    envelope = record.get('envelope') or {}
    # run_id 落盘前补齐进信封(design.md §2 键闭集:envelope 含 run_id,
    # wrapper 信封不含此键;wrapper 交付后不再复用信封,原地补齐无碍)。
    envelope['run_id'] = run_id
    strategy_id = str(envelope.get('strategy_id') or '')
    root = Path(get_recorder().replay_dir)
    key = (root, strategy_id, run_id)
    handle = _HANDLES.get(key)
    if handle is None or handle.closed:
        target = root / 'strategy' / f'{strategy_id}_{run_id}.jsonl'
        # 目录自建:首次落盘前 strategy/ 子目录可能不存在。
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = target.open('a', encoding='utf-8')
        _HANDLES[key] = handle
    handle.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')
    handle.flush()   # 逐行写后即 flush(防进程异常丢尾部记录)


def close_strategy_telemetry_handles() -> None:
    """关闭并清空句柄缓存(测试 teardown 复位口;生产零调用申报——
    生产句柄随进程生命周期,无需中途关闭)。"""
    for handle in _HANDLES.values():
        with contextlib.suppress(Exception):   # 复位口 best-effort
            handle.close()
    _HANDLES.clear()
