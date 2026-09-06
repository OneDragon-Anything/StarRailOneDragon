"""货币战争 遥测序列化纯函数(自 kernel/cw_intention 迁入的权威副本)。

迁入出处:`docs/develop/currency_war/archive/redesign/03_legacy_cleanup_plan.md` 批 0
第 1 项——telemetry 保留层消费的序列化符号迁出死刑判据文件,作为
「telemetry → kernel 死刑文件 import 边归零」的解耦前置。

为何归位 knowledge 而非留在 cw_intention:本节序列化的是**判读口径保真
形状**——旧意向状态机(IntentionState,处死计划批 3 处死)删除后,历史
遥测档案(实机 decisions.jsonl / sim P2 改写回写行)仍必须可读,序列化
形状随本模块存活,不随 IntentionState 类死。序列化用 dataclass 反射
(``is_dataclass`` 鸭子类型),不 import 任何意向决策符号,依赖方向合法
(知识层不依赖决策层,设计 01_strategy_layer.md §1)。

零漂移契约:本模块与 ``kernel/cw_intention`` 尾部同名函数逐字同体;
cw_intention 侧副本仅为 sim/旧判据未迁消费点保留(sim import 本批禁动,
处死计划「sim 框架与旧策略 import 零改动」硬约束),随批 3 删除。
**新增消费一律 import 本模块**,禁再接旧位置。
"""
from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any


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


def serialize_intention(ist: Any) -> dict[str, Any] | None:
    """v3 意向状态(IntentionState)→ JSON-safe dict(遥测判读供给)。

    ADR-0336 后锁定真值在 ``strategy_state_of(session).v3_intention``,但 decisions 行
    只有恒空的 v1 遗留键(``v2_locked_line``/``v2_mode``)——实机判读
    「锁定时点/锁定目标」不可读,只能日志考古。本序列化把意向状态机
    全量落遥测(「锁定目标改过渡配方」判读依赖它)。

    - ``None`` = session 无意向状态机(default 栈/未初始化)——与
      「有意向未锁」(dict 且 ``phase='unlocked'``)显式区分,消费方
      不用猜;
    - dict 按字段全量序列化(dataclass fields 遍历,set→sorted list,
      嵌套 LineTrack 同构)——IntentionState 字段演进时自动跟上,
      不改本函数。

    **可变容器深拷贝(ADR-0378)**:dict/list 字段值经
    ``_to_jsonable`` 递归拷贝(嵌套 dataclass 走 asdict=深拷贝)——
    ``tracks: dict[str, LineTrack]`` 是**活引用**,旧版直接把引用
    落进账本行,session 后续轮原地改 LineTrack 会污染**已落账的
    早期行**(sim P2 段改写同局 P1 行的 tracks 即此类污染)。
    tuple/str 不可变,原样保留(类型不漂移)。

    只读不碰输入状态机;非 dataclass 输入退 None。
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
            # `w194_p2line/`/ADR-0378:可变容器深拷贝落账(活引用污染防线,
            # 见 docstring);tuple 不可变不辖(类型不漂移)
            out[f.name] = _to_jsonable(v)
        else:
            out[f.name] = v
    return out
