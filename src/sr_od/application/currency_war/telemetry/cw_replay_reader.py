"""货币战争 遥测读端规范 loader(零生产行为变更)。

遥测判读脚本曾普遍直接消费裸 dict(decisions/outcomes.jsonl 的 json.loads
产物),字段名/形态写错全部静默——实证:dp_posture 写端 2026-08-26 起
dict→str 收窄后,读端 ``isinstance(dp, dict)`` 恒 False 结构性漏报;actions
元素只有 ``__type__`` 键、读 ``get('type')`` 恒 None;hp_trusted 位在 state
子字典(GameState 序列化)顶层不存在。

本模块是**读端的唯一规范入口**:

- ``decision_from_dict`` / ``outcome_from_dict``:dict → 复用写端
  ``cw_telemetry.DecisionTrace`` / ``OutcomeRecord`` dataclass(单一源,
  不另建平行类);未知键忽略、缺字段落 dataclass 默认值(历史帧容忍,
  含字段值为 None 的帧——schema_version 恒 1,未升版即同 schema 的
  历史形态差异全靠读端容忍)。
- ``load_decisions`` / ``load_outcomes``:规范 loader,返回类型化对象
  列表;坏行(JSON 解析失败/非 dict)跳过不抛。
- ``posture_tag``:dp_posture 的标准读法(判读脚本一律走它,禁再裸
  isinstance)。归一规则按实测证据(decisions.jsonl 7367 帧,2026-08-28):
  - dict 形态(3425 帧,历史 r620 自动附路径)键形状唯一 =
    ``{'spend_mode': str, 'target_level': int}`` → tag 取 ``spend_mode``;
  - str 形态:tag 是短串(实测 ≤7 字符,如 '存息'/'升级+D6'/'+D2'/
    'release'),而载体帧(strategy_id=='')的 dp_posture 是
    ``str(dict)`` 长串(实测 42-46 字符,以 ``'{'`` 开头)→ 以
    ``'{'`` 前缀区分,**不是**按长度分(长度阈值脆);
  - 仅决策帧(strategy_id 非空)返回 tag,载体帧/无姿态恒 None。
"""

from __future__ import annotations

import json
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any, TypeVar

from sr_od.application.currency_war.telemetry.cw_telemetry import (
    DEFAULT_REPLAY_DIR,
    DecisionTrace,
    OutcomeRecord,
)

_T = TypeVar('_T')


def from_dict(cls: type[_T], d: dict[str, Any]) -> _T:
    """dict → 写端 dataclass 实例(单一源复用)。

    只取 dataclass 已声明字段(未知键忽略——写端未来加字段时读端旧码
    不炸);缺字段落 dataclass 默认值。字段值为 None 不清洗(历史帧
    容忍,语义由消费端判)。
    """
    known = {f.name for f in dc_fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in known})


def _load_jsonl(path: Path | str, cls: type[_T], run_id: str | None) -> list[_T]:
    """逐行 json.loads → from_dict → 可选 run_id 过滤;坏行跳过。"""
    p = Path(path)
    out: list[_T] = []
    if not p.exists():
        return out
    for line in p.open(encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        if run_id is not None and d.get('run_id') != run_id:
            continue
        out.append(from_dict(cls, d))
    return out


def load_decisions(path: Path | str = DEFAULT_REPLAY_DIR / 'decisions.jsonl',
                   run_id: str | None = None) -> list[DecisionTrace]:
    """decisions.jsonl → ``DecisionTrace`` 列表(规范读端)。"""
    return _load_jsonl(path, DecisionTrace, run_id)


def load_outcomes(path: Path | str = DEFAULT_REPLAY_DIR / 'outcomes.jsonl',
                  run_id: str | None = None) -> list[OutcomeRecord]:
    """outcomes.jsonl → ``OutcomeRecord`` 列表(规范读端)。"""
    return _load_jsonl(path, OutcomeRecord, run_id)


def posture_tag(frame: DecisionTrace | dict[str, Any]) -> str | None:
    """dp_posture 的标准读法:仅决策帧返回 tag,其余 None。

    参数接受 ``DecisionTrace``(loader 产物)或裸 dict 行(渐进迁移期
    容忍)。归一规则见模块 docstring(证据:decisions.jsonl 实测分布)。

    边界:
    - 载体帧(strategy_id=='')恒 None——其 dp_posture 是 str(dict)
      长串,不是 tag;
    - str 形态以 ``'{'`` 开头 = str(dict) 泄漏形态,不当代 tag;
    - dict 形态取 ``spend_mode`` 键(实测唯一历史键形状),键缺/值空
      返回 None(不猜);
    - 空 tag/None 恒 None。
    """
    if isinstance(frame, dict):
        strategy_id = frame.get('strategy_id', '')
        dp = frame.get('dp_posture')
    else:
        strategy_id = frame.strategy_id
        dp = frame.dp_posture
    if not strategy_id:
        return None
    if isinstance(dp, dict):
        mode = dp.get('spend_mode')
        return str(mode) if mode else None
    if isinstance(dp, str):
        if not dp or dp.startswith('{'):
            return None
        return dp
    return None
