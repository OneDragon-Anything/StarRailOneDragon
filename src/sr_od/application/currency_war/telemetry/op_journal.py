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

体积纪律:action 行 ≤400B(op 行 ≤250B),超限截断 + ``_trunc`` 标记;每局
500 行软上限(超限停写,防病态决策循环炸盘)。禁入决策输入(守卫 = 键族
命中锁,ADR-0571 §2.3 范式;决策输入一律走 TurnState 幂等投影)。
"""
from __future__ import annotations

import datetime
import json as _json
import time as _time
from typing import Any

from one_dragon.utils.file_utils import get_project_root
from sr_od.application.currency_war.telemetry.schema import (
    serialize_action,
    serialize_state,
)
from sr_od.application.currency_war.telemetry.state import current_run_id

#: journal 落盘位置(与 obs_conflicts 同目录;独立流,永不并入 decisions 行)
_JOURNAL = (get_project_root() / '.debug' / 'temp' / 'currency_war'
            / 'replay' / 'op_journal.jsonl')

#: 行字节硬上限(超限截断 + ``_trunc`` 标记;方案 §共通-体积纪律 (a))
_ROW_CAP: int = 400

#: 每局行数软上限(超 = 停写,方案 §共通-体积纪律 (d);病态循环炸盘保险丝)
_MATCH_ROWS_SOFT_CAP: int = 500

#: 每局行计数(run_id → 行数;进程内存态,跨局自然重置)
_row_counts: dict[str, int] = {}

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
    """best-effort 追加一行(局外无 run_id 不写假键;软上限超限停写;
    序列化超行帽截断 + ``_trunc``,obs_conflict 同款 try/except 兜底)。"""
    rid = rec.get('run_id', '')
    if not rid:
        return
    if _row_counts.get(rid, 0) >= _MATCH_ROWS_SOFT_CAP:
        return
    _row_counts[rid] = _row_counts.get(rid, 0) + 1
    try:
        blob = _json.dumps(rec, ensure_ascii=False)
        if len(blob.encode('utf-8')) > row_cap:
            slim = {k: rec[k] for k in rec if k != 'expected_delta'}
            slim['_trunc'] = True
            blob = _json.dumps(slim, ensure_ascii=False)
        _JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with _JOURNAL.open('a', encoding='utf-8') as f:
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
