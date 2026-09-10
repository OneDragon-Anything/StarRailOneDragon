"""统一 state 账本判读读面(R3-1 消费方迁移第一批:离线工具族读新账)。

设计正本 = ``.debug/temp/currency_war/流程侧遥测-设计v3.3.md`` §3.3/§3.6.2
(消费方迁移清单·判读 CLI 行):判读/装配/策略回溯 = 按行直接读(单行自足);
跨行对照 = 行间差分(人读/离线),**零机制化重放**。本模块 = 旧 12 流读面
(:mod:`telemetry.query` 十三视图)之外的「读新账」读面,两读面并存(§3.7.1
并存期:旧视图只读保留至 M5);判读 CLI 经 ``--source journal`` 选择本读面。

行模型(§3.2.3 两行型,写端 = kernel/cw_board_state ``_swap``/``note_obs_event``,
落盘 = kernel/cw_state_journal 批量 flush 追加 JSONL):
- 行型 1 ``row='write'``:v/ts/run_id/row/field/after/same_value/state/sig/
  note/evidence_refs;
- 行型 2 ``row='obs_event'``:v/ts/run_id/row/event/field/observed/verdict/
  obs_phase/state/sig/note/evidence_refs。

**宽容读取契约**(本批验收门):核心字段 = ``v``/``ts``/``run_id``/``row``/
``sig``/``state`` 快照;细节字段(field/after/note/event/verdict/observed/
obs_phase/evidence_refs)缺位不炸——取值口回退行内快照或显式「缺失」形态,
不抛不猜。为什么宽容而非严格:行行自足 + 批量 flush 的落盘形态下,读取面
面对的是崩溃截断尾、跨版本行与未来字段演进;判读工具炸在坏行上会让整段
语料不可读(obs_conflicts journal 截断行容错读先例,replay_to_md 同判据)。

消费方迁移覆盖清单(逐消费方 = 已迁/候 v3.4/不适用)单一源 = 批交付报告
``.debug/temp/currency_war/统一state-R3.1-交付报告.md`` §5(易失产物域,
持久指针 = 本段);sim 账本/复测批判读与校准脚本读入口清单亦载该节。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: 新账相对 replay 根的路径(与旧流同根,落盘布局单一源 =
#: kernel/cw_observe 根常量块;写端缺省落点 = kernel/cw_state_journal)。
JOURNAL_REL: str = 'state/journal.jsonl'

#: 行型 1 的 row 值(状态写入行)。
ROW_WRITE: str = 'write'

#: 行型 2 的 row 值(观察事件行,零状态变更)。
ROW_OBS_EVENT: str = 'obs_event'


def journal_path(replay_dir: Path | str) -> Path:
    """replay 根 → 新账文件路径(单一路径拼装点,切片物化/CLI 共用)。"""
    return Path(replay_dir) / JOURNAL_REL


# ============================================================ 宽容读取


def read_journal(replay_dir: Path | str) -> list[dict[str, Any]]:
    """读新账 → 行 dict 列表(宽容:文件缺 = [];坏行/非 dict 行跳过)。

    为什么不走 query.read_jsonl:那边 json.loads 失败直接抛(旧流是本框架
    自己写的行,坏行 = 事故);新账按设计就是「截断尾合法存在」的流
    (§3.3 flush 纪律:崩溃丢失窗 = 未 flush 尾部),读面必须容忍。
    """
    p = journal_path(replay_dir)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def rows_of(rows: list[dict[str, Any]], run_id: str = '') -> list[dict[str, Any]]:
    """按 run_id 过滤(空 = 不过滤,跨段聚合;行序保持文件序 = 版本序)。"""
    if not run_id:
        return list(rows)
    return [r for r in rows if r.get('run_id') == run_id]


def journal_runs(rows: list[dict[str, Any]]) -> list[str]:
    """首现序 run 列表(新账没有 runs.jsonl 摘要流,run 清单 = 行扫描)。"""
    ids: list[str] = []
    seen: set[str] = set()
    for r in rows:
        rid = str(r.get('run_id') or '')
        if rid and rid not in seen:
            seen.add(rid)
            ids.append(rid)
    return ids


def row_v(row: dict[str, Any]) -> int | None:
    """版本 id(核心字段;缺失/非整数 = None,不猜)。"""
    v = row.get('v')
    return v if isinstance(v, int) else None


def row_ts(row: dict[str, Any]) -> str:
    """行时间戳(核心字段;缺失回空串)。"""
    return str(row.get('ts') or '')


def row_kind(row: dict[str, Any]) -> str:
    """行型('write'/'obs_event';缺失/未知 = 空串)。"""
    return str(row.get('row') or '')


def row_sig(row: dict[str, Any]) -> dict[str, Any]:
    """渠道签名(核心字段;缺位 = 空 dict——影子过渡期合成签名恒在,
    显式缺位只在手工构造/未来演进行出现,读面不设门槛)。"""
    sig = row.get('sig')
    return sig if isinstance(sig, dict) else {}


def state_values(row: dict[str, Any]) -> dict[str, Any]:
    """行内快照的 values 面(核心字段;state 缺失/畸形 = 空 dict)。"""
    st = row.get('state')
    if isinstance(st, dict) and isinstance(st.get('values'), dict):
        return st['values']
    return {}


def field_value(row: dict[str, Any], name: str) -> tuple[bool, Any]:
    """字段现值读取(宽容取值口):优先行内快照 values[name](两行型统一,
    行行自足);快照缺该字段时回退 write 行的 ``after``;两处皆缺 =
    (False, None)。

    回退顺序为什么快照优先:obs_event 行的 ``field`` 指「观察对象」非写入
    字段且无 after 键,统一走快照可免行型分支;after 回退只为覆盖
    「快照面被裁剪的精简行」形态(宽容契约的实战面)。
    """
    vals = state_values(row)
    if name in vals:
        return True, vals[name]
    if str(row.get('field') or '') == name and 'after' in row:
        return True, row['after']
    return False, None


def node_key_of(row: dict[str, Any]) -> tuple[int, int] | None:
    """(plane, round_num) 节点键(宽容):读快照 values['node']——NodeKey
    序列化形态 {plane, round_num, kind};缺/畸形 = None(不猜)。"""
    node = state_values(row).get('node')
    if not isinstance(node, dict):
        return None
    try:
        return int(node['plane']), int(node['round_num'])
    except (KeyError, TypeError, ValueError):
        return None


def node_ordinal_of(row: dict[str, Any]) -> int | None:
    """节点序(设计 §3.4.1 坐标系 ord=(plane-1)*9+round,基 1;宽容 =
    读不到 None)。判读概览/分段排序用。"""
    key = node_key_of(row)
    if key is None:
        return None
    return (key[0] - 1) * 9 + key[1]


# ============================================================ 视图族
# 返回形态与 query.py 视图同构(list[str] 判读行);输入 = 行列表(纯函数,
# 便于对任意切片——live 全账/档案切片物化目录——复用同一实现)。


def _v_s(row: dict[str, Any]) -> str:
    v = row_v(row)
    return str(v) if v is not None else '?'


def _actor_s(row: dict[str, Any]) -> str:
    actor = row_sig(row).get('actor')
    return str(actor) if actor else '-'


def _int_or_none(v: Any) -> int | None:
    """快照值 → int(bool 不是数;None/畸形 = None)。"""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return int(v)


def _value_chain(rows: list[dict[str, Any]], run_id: str,
                 name: str) -> list[str]:
    """单字段值链(行间差分,零重放):逐行读快照值,只显「变化行」;
    跨 run 段界链重开(跨段 Δ 是两局账,混算 = 判读毒化)。"""
    out = [f'[{name} 链] run={run_id or "(全部段)"} '
           f'(来源={JOURNAL_REL} 行间差分;只列变化行)']
    prev: int | None = None
    prev_run: str | None = None
    seen = 0
    for r in rows_of(rows, run_id):
        rid = str(r.get('run_id') or '')
        if prev_run is not None and rid != prev_run:
            prev = None
        prev_run = rid
        ok, val = field_value(r, name)
        cur = _int_or_none(val) if ok else None
        if cur is None:
            continue
        seen += 1
        if prev is None:
            out.append(f'  v={_v_s(r)} {row_ts(r)} {name}={cur} (首值)')
        elif cur != prev:
            out.append(f'  v={_v_s(r)} {row_ts(r)} {name} {prev}→{cur}'
                       f' (Δ{cur - prev:+d}) field={r.get("field") or "-"}'
                       f' actor={_actor_s(r)}')
        prev = cur
    if seen == 0:
        out.append(f'  (无 {name} 读数行——影子面未开、字段未写入或行被裁剪)')
    return out


def view_gold(rows: list[dict[str, Any]], run_id: str = '') -> list[str]:
    """金账(设计 §3.6.2 判读 CLI 行「金账 = 按行读+行间差分」)。"""
    return _value_chain(rows, run_id, 'gold')


def view_hp(rows: list[dict[str, Any]], run_id: str = '') -> list[str]:
    """hp 链(同上;写入闸语义下快照 hp 均为真读值,备帧假值防线在写端)。"""
    return _value_chain(rows, run_id, 'hp')


def view_rounds(rows: list[dict[str, Any]], run_id: str = '') -> list[str]:
    """逐轮表(按节点分段;段界 = 行内快照 node 键,§3.3「跨行对照 = 行间
    差分」)。段内 hp/gold 取该段首末快照读数(末值 = 段末账面,与旧视图
    「代表帧 = 轮末账面」同语义)。开局链段(尚无 node 读数)标「未定节点段」,
    不猜节点身份。"""
    out = [f'[逐轮表] run={run_id or "(全部段)"} '
           f'(来源={JOURNAL_REL} 按节点分段;段内 hp/gold=首→末快照)']
    segs: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    cur_key: tuple[int, int] | None | str = 'unset'
    for r in rows_of(rows, run_id):
        key = node_key_of(r)
        if key != cur_key or cur is None:
            cur = {'key': key, 'n': 0, 'first_ts': row_ts(r), 'last_ts': '',
                   'hp_first': None, 'hp_last': None,
                   'gold_first': None, 'gold_last': None, 'kinds': set()}
            segs.append(cur)
            cur_key = key
        cur['n'] += 1
        cur['last_ts'] = row_ts(r)
        vals = state_values(r)
        node = vals.get('node')
        if isinstance(node, dict) and node.get('kind'):
            cur['kinds'].add(str(node['kind']))
        for name in ('hp', 'gold'):
            v = _int_or_none(vals.get(name))
            if v is not None:
                fk, lk = f'{name}_first', f'{name}_last'
                if cur[fk] is None:
                    cur[fk] = v
                cur[lk] = v
    if not segs:
        out.append('  (无行)')
        return out
    for s in segs:
        key = s['key']
        seg_id = (f'P{key[0]}r{key[1]}' if key is not None
                  else 'P?r?(未定节点段·开局链)')
        kind_s = ('/'.join(sorted(s['kinds'])) if s['kinds'] else '?')
        hp_s = _pair_s(s['hp_first'], s['hp_last'])
        gold_s = _pair_s(s['gold_first'], s['gold_last'])
        ts_s = f"{s['first_ts']}→{s['last_ts']}" if s['last_ts'] else s['first_ts']
        out.append(f'  {seg_id} kind={kind_s} | 行={s["n"]} | {ts_s}'
                   f' | hp {hp_s} | gold {gold_s}')
    return out


def _pair_s(first: int | None, last: int | None) -> str:
    """首末读数显示(缺失 = ?;首末同值只显示一个)。"""
    f_s = str(first) if first is not None else '?'
    l_s = str(last) if last is not None else '?'
    return f_s if first == last else f'{f_s}→{l_s}'


def view_events(rows: list[dict[str, Any]], run_id: str = '') -> list[str]:
    """观察事件行显影(行型 2;obs_conflicts 收编后的证据面在账内直读)。"""
    out = [f'[obs_event] run={run_id or "(全部段)"} (行型 2,零状态变更证据)']
    evs = [r for r in rows_of(rows, run_id) if row_kind(r) == ROW_OBS_EVENT]
    if not evs:
        out.append('  (无 obs_event 行)')
        return out
    for r in evs:
        observed = ('(缺)' if 'observed' not in r
                    else json.dumps(r.get('observed'), ensure_ascii=False))
        out.append(f'  v={_v_s(r)} {row_ts(r)} event={r.get("event") or "?"}'
                   f' field={r.get("field") or "?"} observed={observed}'
                   f' verdict={r.get("verdict") or "-"}'
                   f' actor={_actor_s(r)}')
    return out


def view_snapshot(rows: list[dict[str, Any]], run_id: str = '') -> list[str]:
    """末行快照摘要(局内最新账面;行行自足,最末行即当前 state)。"""
    seg = rows_of(rows, run_id)
    out = [f'[快照] run={run_id or "(全部段)"} (最末行内嵌 state)']
    if not seg:
        out.append('  (无行)')
        return out
    last = seg[-1]
    vals = state_values(last)
    node = vals.get('node')
    node_s = (f"P{node.get('plane')}r{node.get('round_num')}({node.get('kind')})"
              if isinstance(node, dict) else '?')

    def _n(field: str) -> str:
        v = vals.get(field)
        return str(len(v)) if isinstance(v, list) else '?'

    bench = vals.get('bench')
    bench_n = ('?' if not isinstance(bench, dict)
               else str(sum(1 for s in (bench.get('slots') or [])
                            if isinstance(s, dict) and s.get('kind') == 'unit')))
    xp = vals.get('xp')
    xp_s = (f'{xp[0]}/{xp[1]}' if isinstance(xp, (list, tuple)) and len(xp) == 2
            else '?')
    effects = vals.get('effects')
    eff_n = str(len(effects)) if isinstance(effects, list) else '?'
    st = last.get('state')
    pend = (st.get('pending_expected') if isinstance(st, dict) else None)
    pend_n = str(len(pend)) if isinstance(pend, list) else '?'
    out.append(f'  v={_v_s(last)} {row_ts(last)} '
               f"hp={vals.get('hp', '?')} gold={vals.get('gold', '?')}"
               f" level={vals.get('level', '?')} xp={xp_s}"
               f" node={node_s}")
    out.append(f'  front={_n("front_row")} back={_n("back_row")}'
               f' bench={bench_n} equips={_n("equips")}'
               f' effects={eff_n} pending_expected={pend_n}')
    return out
