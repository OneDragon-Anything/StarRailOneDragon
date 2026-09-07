"""货币战争 op_journal.jsonl 薄流(T-113/ADR-0579:深度复盘遥测缺口②③)。

两个行型(独立于 decisions.jsonl 的薄流;体积红线 = 永不并入 decisions 行,
3.5KB 行基数上叠逐动作/逐 op 快照是体积爆炸路径):

- kind='action':商店单动作执行回执(唯一写点 = apply_action_outcome 回执位),
  expected_delta = 执行前后帧序列化的**全量展平叶级 diff**——投影之外的真实
  变化必须出现在 delta 里(「投影没算到但真变了」正是深度复盘要抓的投影残差);
- kind='op':非决策 op(战斗等待/入口链/位面切换)enter/exit 成对行。轮询
  内循环逐 tick 不落行(用户需求粒度 = 每次 op 调用;tick 级留日志)。孤儿
  enter 行(进程中断/停局导致 exit 丢失)= 进程中断证据,装配端标注
  ``outcome='orphan'`` 容缺非缺陷。

体积纪律:action 行 ≤400B(op 行 ≤250B),超限截断 + ``_trunc`` 标记。
行数**不设上限**(原「每局 500 行软上限超限停写」已由用户裁定 2026-09-07
整条删除):病态决策循环的停线防护已由哨兵层 STALL/LOOP 检测承接,
journal 侧静默触顶停写会让长局尾段 op 行无感丢失——复盘盲区的代价
远大于流体积风险(T-121 深局实测单 run 690 行即已越旧顶)。禁入决策
输入(守卫 = 键族命中锁,ADR-0571 §2.3 范式;决策输入一律走 TurnState
幂等投影)。
"""
from __future__ import annotations

import datetime
import json as _json
import time as _time
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_observe import LIVE_DIR
from sr_od.application.currency_war.telemetry.schema import (
    serialize_action,
    serialize_state,
)
from sr_od.application.currency_war.telemetry.state import current_run_id

#: journal 落盘位置(telemetry/live 实时流根,单一源 = kernel/cw_observe
#: 的根常量块;独立流,永不并入 decisions 行)
_JOURNAL = LIVE_DIR / 'op_journal.jsonl'

# ===== journal 根装配槽(T-120 批 1;T-129/T-130「sim 与 live 共写同一
# ===== journal 文件」混流设计注记的落地点)=====
# 机制裁决 = **写端根隔离**而非读端 run_id 过滤:假局(经根槽接指假局
# 档案根)的 action/op 行从写入时点就不进 live 流,读端无需维护
# 「run_id ∈ sim 集」过滤态(过滤态漏维护 = 静默混流,比写端漏接通更
# 难发现——写端漏接通表现为 live 流出现行,obs_conflict 式审计可见)。
# 行内 run_id 键保持不变,读端过滤能力不受影响(双保险,非双实现)。
# 缺省 None = LIVE_DIR(生产路径逐位不变);测试 harness 与 recorder 落盘
# 根槽(telemetry/state.set_recorder_replay_dir)同点接通,两根恒一致。
_JOURNAL_DIR: Path | None = None


def set_journal_dir(path: Path | None) -> None:
    """接通/复位 journal 落盘根(缺省 None = LIVE_DIR 生产路径)。

    与 :func:`telemetry.state.set_recorder_replay_dir` 同装配纪律:缺省关、
    测试显式接通、teardown 复位——进程全局槽,残留会把后续写的 journal
    行带去假局根。
    """
    global _JOURNAL_DIR
    _JOURNAL_DIR = Path(path) if path is not None else None


def _journal_path() -> Path:
    """journal 文件现算路径(根槽优先;槽是函数内读取,测试可 monkeypatch
    槽变量后立即生效,不经模块 import 绑定快照)。

    槽缺省回落模块常量 ``_JOURNAL``(非直接回落 LIVE_DIR):既有测试以
    monkeypatch ``_JOURNAL`` 作落盘重定向缝(test_cw_op_journal/
    test_cw_dispatch_wrapper 同款),常量保持活读=该缝不失效;根槽是
    追加缝,不改写既有缝语义。"""
    if _JOURNAL_DIR is not None:
        return _JOURNAL_DIR / 'op_journal.jsonl'
    return _JOURNAL

#: 行字节硬上限(超限截断 + ``_trunc`` 标记;方案 §共通-体积纪律 (a))
_ROW_CAP: int = 400

#: 决策帧关联键帧序(C6):每 run 当前段序号(shop 段计数同源,由
#: advance_frame_seq 在段边界推进;action 行读取当前值做精确 join)
_frame_seq_by_run: dict[str, int] = {}


def advance_frame_seq() -> int:
    """段边界推进帧序(shop 段循环起点调用;返回推进后的段序)。"""
    rid = current_run_id()
    if not rid:
        return 0
    _frame_seq_by_run[rid] = _frame_seq_by_run.get(rid, 0) + 1
    return _frame_seq_by_run[rid]


def current_frame_seq() -> int:
    """当前段序(动作行 frame_seq 关联键读取端;局外 = 0)。"""
    return _frame_seq_by_run.get(current_run_id(), 0)


def _flatten(obj: Any, prefix: str, out: dict[str, Any]) -> None:
    """全量展平叶级(方案 C3 写死):嵌套 dict 递归展开点号路径;列表叶 =
    整列表替换计一条(列表下标语义随内容漂移,逐元素对位产生假对应)。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(v, f'{prefix}.{k}' if prefix else str(k), out)
        return
    out[prefix or '<root>'] = obj


def flatten_diff(before: dict[str, Any], after: dict[str, Any],
                 cap: int) -> dict[str, Any]:
    """前后两序列化帧的全量叶级 diff(零漏报口径)。

    两侧都展平后做键集对称差 + 同键值比较;超 ``cap`` 条截断并置
    ``_trunc=True``(读端按「此帧 delta 不完整」分型)。
    """
    fb: dict[str, Any] = {}
    fa: dict[str, Any] = {}
    _flatten(before, '', fb)
    _flatten(after, '', fa)
    delta: dict[str, Any] = {}
    for k in fb:
        if k not in fa:
            delta[f'-{k}'] = fb[k]
    for k, v in fa.items():
        if k not in fb:
            delta[f'+{k}'] = v
        elif fb[k] != v:
            delta[f'~{k}'] = v
    if len(delta) > cap:
        kept = dict(list(delta.items())[:cap])
        kept['_trunc'] = True
        return kept
    return delta


def _emit(rec: dict[str, Any], row_cap: int) -> None:
    """best-effort 追加一行(局外无 run_id 不写假键;
    序列化超行帽截断 + ``_trunc``,obs_conflict 同款 try/except 兜底;
    行数不设上限——软上限删除裁决见模块 docstring 体积纪律节)。"""
    rid = rec.get('run_id', '')
    if not rid:
        return
    try:
        blob = _json.dumps(rec, ensure_ascii=False)
        if len(blob.encode('utf-8')) > row_cap:
            slim = {k: rec[k] for k in rec if k != 'expected_delta'}
            slim['_trunc'] = True
            blob = _json.dumps(slim, ensure_ascii=False)
        out = _journal_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('a', encoding='utf-8') as f:
            f.write(blob + '\n')
    except Exception:   # noqa: BLE001  journal best-effort,失败不阻塞业务流
        pass


def _base_row(plane: int, round_num: int) -> dict[str, Any]:
    return {'schema_version': 1,
            'ts': datetime.datetime.now().isoformat(timespec='seconds'),
            'run_id': current_run_id(),
            'plane': plane, 'round_num': round_num}


def record_action_journal(match: Any, action: Any, seq: int, exec_ok: bool,
                          pre_frame: Any, post_frame: Any) -> None:
    """缺口②写点:商店单动作执行回执行(apply_action_outcome 回执位调用)。

    :param match: 对局对象(session 载体;run_id 读取经 telemetry.state)
    :param action: 已执行的动作对象(BuyCard/RefreshShop/LevelUpShop/CloseShop)
    :param seq: 段内动作序(1 起;visit_actions 追加后长度)
    :param exec_ok: 执行落地与否(False 行照落,exec_ok=False 判读面)
    :param pre_frame: 动作执行前帧(GameState;序列化做 diff 左侧)
    :param post_frame: 动作执行后帧(GameState;None=终结/投影跳过,delta 省略)
    """
    try:
        rid = current_run_id()
        if not rid:
            return
        rec = _base_row(int(getattr(pre_frame, 'plane', 0) or 0),
                        int(getattr(pre_frame, 'round_num', 0) or 0))
        rec.update({'kind': 'action', 'op': '货币战争-买牌',
                    'seq': seq, 'frame_seq': current_frame_seq(),
                    'action': serialize_action(action), 'exec_ok': exec_ok})
        if post_frame is not None:
            delta = flatten_diff(serialize_state(pre_frame),
                                 serialize_state(post_frame), cap=12)
            if delta:
                rec['expected_delta'] = delta
            rec['gold'] = getattr(post_frame, 'gold', None)
            try:
                from sr_od.application.currency_war.kernel.cw_state import (
                    bench_occupied,
                )
                rec['bench_used'] = bench_occupied(post_frame.bench)
            except Exception:   # noqa: BLE001  观测 best-effort
                pass
        _emit(rec, _ROW_CAP)
    except Exception:   # noqa: BLE001  journal best-effort
        pass


def record_op_enter(op_name: str, plane: int, round_num: int,
                    obs: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """缺口③写点(enter):非决策 op 执行前调用,返回 exit 用的 token。

    局外(current_run_id 空)返回 None = 零行(不写假键,obs_conflict 同规)。
    """
    rid = current_run_id()
    if not rid:
        return None
    token = {'op': op_name, 't0': _time.monotonic(), 'plane': plane,
             'round_num': round_num, 'obs_enter': dict(obs or {})}
    rec = _base_row(plane, round_num)
    rec.update({'kind': 'op', 'op': op_name, 'event': 'enter',
                'obs': dict(obs or {})})
    _emit(rec, 250)
    return token


def record_op_exit(token: dict[str, Any] | None, outcome: str = 'ok',
                   detail: str = '', obs: dict[str, Any] | None = None) -> None:
    """缺口③写点(exit):op 执行后调用(token = enter 返回值;None = 局外静默)。"""
    if token is None:
        return
    rec = _base_row(int(token.get('plane', 0) or 0),
                    int(token.get('round_num', 0) or 0))
    rec.update({'kind': 'op', 'op': token.get('op', ''), 'event': 'exit',
                'duration_s': round(_time.monotonic() - token.get('t0', 0.0), 2),
                'outcome': outcome})
    if detail:
        rec['detail'] = detail
    if obs:
        rec['obs'] = dict(obs)
    _emit(rec, 250)
