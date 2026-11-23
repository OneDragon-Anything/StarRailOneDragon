"""星级抖动门辖区与代价判读(活 journal + 缺陷台账只读;可观察量计数器,不做因果归因)。

定位:kernel/cw_reconcile.py 星级抖动门(``_gate_star_jitter``,门注释块第 3 层:
门只对 logic_rand 以外的基线保旧,随机态基线星差直采并落披露行)的实机量测
工具 —— 按 run 数出门的辖区是否越权、随机态基线帧的暴露面、直采后被采回 /
离槽的金币后果,以及 bench / deployed 真失配行的差异槽事实。只读活 journal
(状态流水 jsonl)与缺陷台账(jsonl),零写入、零网络、不进运行时链、不被 src/
导入。代价 / 回归的归因不在此脚本做(归因需要代码 + 现场 + 台账,归停机诊断);
本脚本给的是诊断的路由坐标。

**契约键**:三个 verdict 前缀与 ``cw_reconcile`` 的 ``STAR_ADOPT_RAND_BASELINE_PREFIX``
/ ``STAR_HOLD_JITTER_PREFIX`` / ``STAR_HOLD_WINDOW_PREFIX`` 交叉锁(测试 =
sr-od-test/test/skills/sr-od-dev-currency-war/scripts/test_cw_star_gate_monitor.py),
任一侧改措辞即测试红。证据常量 ``MERGE_EVIDENCE_MARKERS`` 只用于 ④(iii) 读低
标签二分(合成写证据串 = ``<前缀>proj_ore_merge#<n>#ore<k>``,前缀在「附着值缺失」
支为 ``ore_reward_attach_missing#``,kernel/cw_action_report/collect_ore.py 的
合成写端内联字面量;子串匹配)。**本脚本不枚举任何卖出证据串**:(iii) 的 sold
判定与 (iv) 锚走 journal 自带的动作批键 ``sig.group_id``(一次逻辑计算打包的组
标识,cw_game_state.ChannelSig.group_id;备战卖出 bench / gold 两写同组、场上卖出
同、投资卡全场出售三写同组)。

**行形状(输入)**:
- journal 行 ``rows``:单 run 按序。``row=write`` 行带 ``v / ts / field / after /
  same_value / state{values, prov} / sig{family, actor, mode, group_id}``;行行内嵌
  **写后** state 快照,故「某写行的写前账面」= 该写行前一行(同 run)的 ``state``;
  ``row=obs_event field=star`` 行带 ``observed{old, new, char, slot, domain} /
  verdict / state``(state = 门调用时点 = observe 之前 = 基线)。
- 缺陷台账行 ``defects``:``{kind, field, expected, actual, observed_evidence, ts,
  screen, actor, group_id, logic_evidence}``,无 run_id(cw_game_state._emit_defect)。

**口径**(按 run;函数内按 ``rows`` 首末行 ``ts`` 切台账):
① 真失配事实清单:``kind=observe_vs_logic_mismatch ∧ field∈{bench, deployed}``
   台账行,每行列出对齐的 heavy 写行(同 field、ts 最近 ±1s)、差异槽集(写行
   ``after`` 对前一行 ``state.values.<field>`` 逐槽)与 ``linked_adoptions``
   (此前同 run、char 命中差异槽的采新行,只作提示,无归因位);
② 门辖区双向违例:``保旧-星级抖动门`` 行的基线来源须 ≠ logic_rand(违例方向 =
   保旧于随机态基线);``采新-随机态基线`` 行的基线来源须 = logic_rand(违例方向 =
   采新于非随机态基线);``保旧-合成特效窗`` 行无来源约束(窗优先于来源判定)。
   star 行基线来源 = 该行前一行 ``state.prov.<field>.source``,映射 observed.domain
   bench → bench、front/back → deployed,条目缺失 = observation;
④(i) heavy 写行 = ``row=write ∧ field∈{bench, deployed} ∧ sig.family=obs ∧
   actor=CwScreenPrep ∧ mode=read``,按写行计(同帧两域各一行);基线来源 = 该写行
   前一行 ``state.prov.<field>.source``,条目缺失 = observation(不取「最后一次有
   条目的 prov」读法 —— 那会把已翻 observation 的写行误判回 logic_rand);基线证据
   前缀 ``seed:opening`` = 开局种子帧(门的新分支体不执行,单列);
④(ii) star 行按 verdict 前缀计数,各带基线来源;
④(iii) 采回:``采新-随机态基线`` 行 A 中被采回的 —— 自 A 起逐个该域 heavy 写行看
   该槽,**同时**满足「星 == A.old」与「该写行前一行 state.values 该槽 = (A.char,
   A.new, 同 kind)」(账面此刻仍停在采新值、本次写行才翻回)→ 采回;按上下文判、
   不设帧窗(基线保持非随机态时真值回来必先经一帧「登记候选 + 保旧」再采新,
   采回落在第 ≥ 3 个该域 heavy 写行;域被采晶矿「未变标记」翻回 logic_rand 则第
   2 个写行即经采新路径直采回真值)。``revert_via``:采回写行前一行 prov 该域
   logic_rand → rand_adopt(该帧同落的方向相反采新行 = 回翻行,单列不计入样本与
   标签),否则 two_frame。离槽:按**全部** journal 行扫该槽内容,首个使该槽 ≠
   (A.char, A.new) 的行关闭追踪,按槽内容先判、再看同组写金 —— char 同星异 →
   logic_overwritten;char 异 → identity_changed;槽空 / 占位件 → 该行为逻辑写行且
   与某 ``field=gold`` 逻辑写行同 ``sig.group_id`` → sold(同时作 (iv) 锚),否则
   emptied;至 run 末未采回未离槽 → adopt_open_at_run_end。标签(只贴采回行):
   直采星 > 基线星 → 读高·星读抖动;直采星 < 基线星 → 基线写证据串含
   MERGE_EVIDENCE_MARKERS 任一子串 → 读低·窗漏检嫌疑(合成写),否则 → 读低·缺星读
   或抖动(非合成写);
④(iv) 金币路径:自采新行 A 起到离槽写行 R(A 与 R 之间全部 journal 行该槽 char 恒 ==
   A.char,由离槽关闭规则结构保证)∧ R 为逻辑写行且与某 ``field=gold`` 逻辑写行同
   ``sig.group_id`` ∧ R 的 after 中 A 槽不再持有 A.char → R 之后、该域下一次 heavy
   写行之前的首条 ``kind=observe_vs_logic_mismatch, field=gold`` 台账行计 1(窗口 ts
   判据 = 台账行 ts > R.ts 且 ≤ 该域下一 heavy 写行 ts;无下一 heavy 写行则上界取
   run 末),不论 logic_evidence;按离槽锚计,同一台账行可被多锚命中(ts 相同即同一行)。

**坐标系与取值时机**(返回结构中索引类字段):``domain`` ∈ {bench, front, back}
= star 行 ``observed.domain``(或 heavy 写行 field 的子表拆分),``slot`` = 1 基
物理槽:bench = ``slots`` 下标 + 1,deployed = 子表 ``front_slots`` / ``back_slots``
下标 + 1(与 ``cw_reconcile._bench_read_entries`` / ``_deployed_read_entries`` 的
锚定义同构);取值时机 = 来自 journal 行(``observed`` 或写行 ``after``),不做任何
现读。deployed 子表空位 = None,bench 空位 kind='empty',占位件(unit=None)同腾空处理。

**返回结构** ``analyze_run(rows, defects) -> dict``:heavy_total / heavy_rand_baseline /
heavy_rand_seed;star_by_prefix{前缀: {total, by_baseline{来源: 数}}};adopt_reverted
[{v, domain, slot, char, baseline_star, adopted_star, baseline_evidence,
revert_frame_distance, revert_via, label}] + adopt_reverted_count;adopt_reverse
[{domain, slot, char, old, new, v, is_reverse_of}] + adopt_reverse_count;
adopt_sample_count(= 采新前缀行数 − 回翻行数);adopt_slot_changed [{v, domain, slot,
char, reason}] + adopt_slot_changed_count;adopt_open_at_run_end;gold_path_mismatch +
gold_path_rows [{ts, char, domain, depart_reason, depart_evidence, gold_evidence,
sell_frame_distance}];mismatch_rows [{ts, field, diff_slots[{domain, slot, char,
prev_char, prev_kind, prev_star, after_char, after_kind, after_star}], linked_adoptions
[{v, domain, slot, char, old, new}]}] + mismatch_count;hold_violations [{v, ts,
domain, slot, char, prefix, baseline_source, direction}] + hold_violation_count。
``v`` = journal 行版本号(star 行 ``v``,回查原文用)。
守恒:采新前缀行数 = 采回 + 离槽 + 局末未决 + 回翻行。

用法(仓库根下):uv run python skills/sr-od-dev-currency-war/scripts/cw_star_gate_monitor.py
    [--journal PATH] [--defects PATH] [--run RUN_ID ...] [--json]
缺省 journal = .debug/currency_war/telemetry/live/state/journal.jsonl,台账 =
.debug/temp/currency_war/gs_defect.jsonl;逐 run 打印 ①②④ 与行级清单,末尾合计。
固定披露(每 run 打印):(iii) 不覆盖采回前离槽的错星;策略消费后果无直接监控键,
以 (iii)/(iv) 计数与停机局的诊断定因为前兆。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# ===== 契约键(与 kernel/cw_reconcile.py 三个前缀常量交叉锁)=====
ADOPT_PREFIX: str = '采新-随机态基线'
HOLD_JITTER_PREFIX: str = '保旧-星级抖动门'
HOLD_WINDOW_PREFIX: str = '保旧-合成特效窗'
#: 合成写证据串子串(只用于 ④(iii) 读低标签二分;来源 = collect_ore.py 合成写端
#: 的内联字面量 ``proj_ore_merge#``,前缀 ``ore_reward_attach_missing#`` 为附着值缺失支)。
MERGE_EVIDENCE_MARKERS: tuple[str, ...] = ('proj_ore_merge',)

HEAVY_FIELDS: tuple[str, ...] = ('bench', 'deployed')
HEAVY_ACTOR: str = 'CwScreenPrep'
LOGIC_FAMILIES: tuple[str, ...] = ('logic_action', 'logic_hook')
SEED_EVIDENCE_PREFIX: str = 'seed:opening'
SOURCE_OBSERVATION: str = 'observation'
SOURCE_LOGIC_RAND: str = 'logic_rand'

REVERT_TWO_FRAME: str = 'two_frame'
REVERT_RAND_ADOPT: str = 'rand_adopt'
REASON_IDENTITY_CHANGED: str = 'identity_changed'
REASON_EMPTIED: str = 'emptied'
REASON_SOLD: str = 'sold'
REASON_LOGIC_OVERWRITTEN: str = 'logic_overwritten'

LABEL_READ_HIGH: str = '读高·星读抖动'
LABEL_READ_LOW_MERGE: str = '读低·窗漏检嫌疑(合成写)'
LABEL_READ_LOW_OTHER: str = '读低·缺星读或抖动(非合成写)'

VIOLATION_HOLD_ON_RAND: str = '保旧于随机态基线'
VIOLATION_ADOPT_ON_NON_RAND: str = '采新于非随机态基线'

MISMATCH_KIND: str = 'observe_vs_logic_mismatch'
OTHER_PREFIX: str = '(其他)'

#: 台账行与 heavy 写行的 ts 对齐容差(两侧同为秒级 isoformat;同一 observe 调用内
#: 台账行先于 journal 行落,同秒为常态)。
_TS_TOLERANCE = timedelta(seconds=1)

DEFAULT_JOURNAL = Path('.debug/currency_war/telemetry/live/state/journal.jsonl')
DEFAULT_DEFECTS = Path('.debug/temp/currency_war/gs_defect.jsonl')


# ============================================================ 行读取助手


def _parse_ts(ts) -> datetime | None:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _state(row: dict) -> dict:
    return (row.get('state') or {}) if isinstance(row, dict) else {}


def _prov_entry(row: dict, field: str) -> dict | None:
    """行内 ``state.prov.<field>`` 条目(dict)或 None(缺失 = observation 无证据)。"""
    p = (_state(row).get('prov') or {}).get(field)
    return p if isinstance(p, dict) else None


def _baseline_source(row: dict | None, field: str) -> str:
    """写行 / star 行的基线来源 = 该行前一行 prov;条目缺失 = observation。"""
    if row is None:
        return SOURCE_OBSERVATION
    p = _prov_entry(row, field)
    return str(p.get('source') or SOURCE_OBSERVATION) if p else SOURCE_OBSERVATION


def _baseline_evidence(row: dict | None, field: str) -> str | None:
    if row is None:
        return None
    p = _prov_entry(row, field)
    ev = p.get('evidence') if p else None
    return str(ev) if ev is not None else None


def _sig(row: dict) -> dict:
    return (row.get('sig') or {}) if isinstance(row, dict) else {}


def _is_heavy(row: dict) -> bool:
    """heavy 观察写行:row=write ∧ field∈{bench,deployed} ∧ obs/CwScreenPrep/read。"""
    if not isinstance(row, dict) or row.get('row') != 'write':
        return False
    if row.get('field') not in HEAVY_FIELDS:
        return False
    sig = _sig(row)
    return (sig.get('family') == 'obs' and sig.get('actor') == HEAVY_ACTOR
            and sig.get('mode') == 'read')


def _is_logic_write(row: dict) -> bool:
    return (isinstance(row, dict) and row.get('row') == 'write'
            and _sig(row).get('family') in LOGIC_FAMILIES)


def _is_star_row(row: dict) -> bool:
    return (isinstance(row, dict) and row.get('row') == 'obs_event'
            and row.get('field') == 'star')


def _field_of_domain(domain) -> str | None:
    """star 行 observed.domain → 状态容器字段(bench / front|back → deployed)。"""
    if domain == 'bench':
        return 'bench'
    if domain in ('front', 'back'):
        return 'deployed'
    return None


def _slot_content(value, domain: str, slot: int) -> tuple[str, str, int | None]:
    """某域某 1 基物理槽的内容 → ``(kind, char_id, star)``。

    kind ∈ {unit, empty, other}:bench 空位 kind='empty'、占位件(unit=None,
    supply_box/tome/bookcard)= other(门的语义 = 无身份,同腾空处理);deployed
    空位 None = empty。越界 / 值缺失 = empty(读不到 = 不持有)。"""
    if not isinstance(value, dict) or slot < 1:
        return ('empty', '', None)
    if domain == 'bench':
        slots = value.get('slots') or []
        if slot > len(slots):
            return ('empty', '', None)
        s = slots[slot - 1] or {}
        kind = s.get('kind', 'empty')
        u = s.get('unit')
        if kind == 'unit' and isinstance(u, dict):
            return ('unit', str(u.get('char_id') or ''), int(u.get('star') or 1))
        if kind == 'empty':
            return ('empty', '', None)
        return ('other', '', None)
    sub = value.get(f'{domain}_slots') or []
    if slot > len(sub):
        return ('empty', '', None)
    u = sub[slot - 1]
    if isinstance(u, dict):
        return ('unit', str(u.get('char_id') or ''), int(u.get('star') or 1))
    return ('empty', '', None)


def _values(row: dict) -> dict:
    return (_state(row).get('values') or {}) if isinstance(row, dict) else {}


def _slot_in_row(row: dict, field: str, domain: str, slot: int
                 ) -> tuple[str, str, int | None]:
    """行写后账面里该槽内容(写行的 after 与 state.values 同值,统一读 state)。"""
    return _slot_content(_values(row).get(field), domain, slot)


def _label(baseline_star: int, adopted_star: int, baseline_evidence: str | None) -> str:
    """采回行启发式标签(按方向二分,读低再按基线写证据串含合成标记二分)。"""
    if adopted_star > baseline_star:
        return LABEL_READ_HIGH
    ev = baseline_evidence or ''
    if any(m in ev for m in MERGE_EVIDENCE_MARKERS):
        return LABEL_READ_LOW_MERGE
    return LABEL_READ_LOW_OTHER


# ============================================================ 纯函数主体


def analyze_run(rows: list[dict], defects: list[dict]) -> dict:
    """单 run 判读(零 IO)。``rows`` = 单 run 的 journal 行按序;``defects`` =
    缺陷台账行(函数内按 ``rows`` 首末行 ts 切片)。口径与返回结构见模块 docstring。"""
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    ts_list = [t for t in (_parse_ts(r.get('ts')) for r in rows) if t is not None]
    run_start, run_end = (min(ts_list), max(ts_list)) if ts_list else (None, None)

    def _in_run(d: dict) -> bool:
        t = _parse_ts(d.get('ts'))
        return t is not None and run_start is not None and run_start <= t <= run_end

    # 台账行无序号,按 ts 稳定排序后「窗口内首条」才可判(落盘本就按时间追加,
    # 排序只兜底跨文件合并 / 同秒乱序)。
    defects_in = sorted(
        (d for d in (defects or []) if isinstance(d, dict) and _in_run(d)),
        key=lambda d: (_parse_ts(d.get('ts')) or run_start or datetime.min))

    heavy_idx: list[int] = [i for i, r in enumerate(rows) if _is_heavy(r)]
    heavy_by_field: dict[str, list[int]] = {f: [] for f in HEAVY_FIELDS}
    for i in heavy_idx:
        heavy_by_field[rows[i]['field']].append(i)

    def _next_heavy_ts(field: str, after_idx: int) -> datetime | None:
        for i in heavy_by_field[field]:
            if i > after_idx:
                return _parse_ts(rows[i].get('ts'))
        return run_end

    # ---- ④(i) heavy 写行成色 ----
    heavy_rand = 0
    heavy_seed = 0
    for i in heavy_idx:
        f = rows[i]['field']
        if _baseline_source(rows[i - 1] if i > 0 else None, f) == SOURCE_LOGIC_RAND:
            heavy_rand += 1
            ev = _baseline_evidence(rows[i - 1] if i > 0 else None, f) or ''
            if ev.startswith(SEED_EVIDENCE_PREFIX):
                heavy_seed += 1

    # ---- ④(ii) star 行按前缀 + ② 辖区违例 ----
    star_by_prefix: dict[str, dict] = {}
    hold_violations: list[dict] = []
    adopt_rows: list[dict] = []
    for i, r in enumerate(rows):
        if not _is_star_row(r):
            continue
        obs = r.get('observed') or {}
        domain = obs.get('domain')
        field = _field_of_domain(domain)
        prev = rows[i - 1] if i > 0 else None
        base = _baseline_source(prev, field) if field else SOURCE_OBSERVATION
        verdict = str(r.get('verdict') or '')
        if verdict.startswith(ADOPT_PREFIX):
            prefix = ADOPT_PREFIX
        elif verdict.startswith(HOLD_JITTER_PREFIX):
            prefix = HOLD_JITTER_PREFIX
        elif verdict.startswith(HOLD_WINDOW_PREFIX):
            prefix = HOLD_WINDOW_PREFIX
        else:
            prefix = OTHER_PREFIX
        bucket = star_by_prefix.setdefault(prefix, {'total': 0, 'by_baseline': {}})
        bucket['total'] += 1
        bucket['by_baseline'][base] = bucket['by_baseline'].get(base, 0) + 1
        if prefix == HOLD_JITTER_PREFIX and base == SOURCE_LOGIC_RAND:
            hold_violations.append({
                'v': r.get('v'), 'ts': r.get('ts'), 'domain': domain,
                'slot': obs.get('slot'), 'char': obs.get('char'),
                'prefix': prefix, 'baseline_source': base,
                'direction': VIOLATION_HOLD_ON_RAND})
        elif prefix == ADOPT_PREFIX and base != SOURCE_LOGIC_RAND:
            hold_violations.append({
                'v': r.get('v'), 'ts': r.get('ts'), 'domain': domain,
                'slot': obs.get('slot'), 'char': obs.get('char'),
                'prefix': prefix, 'baseline_source': base,
                'direction': VIOLATION_ADOPT_ON_NON_RAND})
        if prefix == ADOPT_PREFIX and field is not None:
            adopt_rows.append({
                'idx': i, 'v': r.get('v'), 'ts': r.get('ts'),
                'field': field, 'domain': domain, 'slot': int(obs.get('slot') or 0),
                'char': str(obs.get('char') or ''),
                'old': obs.get('old'), 'new': obs.get('new'),
                'baseline_evidence': _baseline_evidence(prev, field)})

    # ---- ④(iii) 采回 / 离槽 / 回翻 + (iv) 锚 ----
    gold_groups: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        if (isinstance(r, dict) and r.get('row') == 'write' and r.get('field') == 'gold'
                and _sig(r).get('family') in LOGIC_FAMILIES and _sig(r).get('group_id')):
            gold_groups.setdefault(str(_sig(r).get('group_id')), []).append(i)

    reverse_of: dict[int, int] = {}          # 回翻 star 行 idx → 原采新行 idx
    adopt_reverted: list[dict] = []
    adopt_slot_changed: list[dict] = []
    anchors: list[dict] = []                 # (iv) 锚:采新行 + 离槽写行
    open_at_end = 0
    for a in adopt_rows:
        if a['idx'] in reverse_of:
            continue                          # 回翻行不作为独立样本追踪
        f, dom, slot = a['field'], a['domain'], a['slot']
        want_new = (a['char'], a['new'])
        want_old = (a['char'], a['old'])
        frames = 0                            # 含采新写行起该域 heavy 写行数
        adopted = False                       # 已见到采新写行
        closed = False
        for i in range(a['idx'] + 1, len(rows)):
            r = rows[i]
            is_heavy_here = (r.get('row') == 'write' and r.get('field') == f
                             and _is_heavy(r))
            if is_heavy_here:
                frames += 1
                adopted = True
                prev_c = _slot_in_row(rows[i - 1], f, dom, slot) if i > 0 else ('empty', '', None)
                cur_c = _slot_in_row(r, f, dom, slot)
                if (cur_c[0] == 'unit' and cur_c[1:] == want_old
                        and prev_c[0] == cur_c[0] and prev_c[1:] == want_new):
                    # 采回:账面此刻仍停在采新值、本次写行才翻回基线值
                    via = (REVERT_RAND_ADOPT
                           if _baseline_source(rows[i - 1], f) == SOURCE_LOGIC_RAND
                           else REVERT_TWO_FRAME)
                    adopt_reverted.append({
                        'v': a['v'],
                        'domain': dom, 'slot': slot, 'char': a['char'],
                        'baseline_star': a['old'], 'adopted_star': a['new'],
                        'baseline_evidence': a['baseline_evidence'],
                        'revert_frame_distance': frames, 'revert_via': via,
                        'label': _label(int(a['old']), int(a['new']),
                                        a['baseline_evidence'])})
                    if via == REVERT_RAND_ADOPT:
                        # 回翻行 = 本帧(上一 heavy 写行之后、本写行之前)方向相反的采新行
                        for j in range(i - 1, a['idx'], -1):
                            rj = rows[j]
                            if (rj.get('row') == 'write' and rj.get('field') == f
                                    and _is_heavy(rj)):
                                break
                            if _is_star_row(rj):
                                oj = rj.get('observed') or {}
                                if (str(rj.get('verdict') or '').startswith(ADOPT_PREFIX)
                                        and oj.get('domain') == dom
                                        and int(oj.get('slot') or 0) == slot
                                        and oj.get('char') == a['char']
                                        and oj.get('old') == a['new']
                                        and oj.get('new') == a['old']):
                                    reverse_of[j] = a['idx']
                                    break
                    closed = True
                    break
            if not adopted:
                # 采新写行之前(同帧 star 行 → 写行之间)账面仍是基线值,不作离槽
                if _slot_in_row(r, f, dom, slot)[1:] == want_old:
                    continue
            cur_c = _slot_in_row(r, f, dom, slot)
            if cur_c[0] == 'unit' and cur_c[1:] == want_new:
                continue                     # 账面仍停在采新值
            # 离槽:按槽内容先判、再看同组写金
            if cur_c[0] == 'unit' and cur_c[1] == a['char']:
                reason = REASON_LOGIC_OVERWRITTEN
            elif cur_c[0] == 'unit':
                reason = REASON_IDENTITY_CHANGED
            else:
                gid = _sig(r).get('group_id')
                reason = (REASON_SOLD if (_is_logic_write(r) and gid
                                         and str(gid) in gold_groups)
                          else REASON_EMPTIED)
            adopt_slot_changed.append({
                'v': a['v'],
                'domain': dom, 'slot': slot, 'char': a['char'], 'reason': reason})
            if reason == REASON_SOLD:
                anchors.append({'adopt': a, 'row_idx': i, 'frames': frames})
            closed = True
            break
        if not closed:
            open_at_end += 1

    # ---- ④(iv) 金币路径 ----
    gold_path_rows: list[dict] = []
    hit_ts: set[str] = set()
    for anc in anchors:
        a, i = anc['adopt'], anc['row_idx']
        r = rows[i]
        f = a['field']
        r_ts = _parse_ts(r.get('ts'))
        upper = _next_heavy_ts(f, i)
        if r_ts is None:
            continue
        for d in defects_in:
            if d.get('kind') != MISMATCH_KIND or d.get('field') != 'gold':
                continue
            d_ts = _parse_ts(d.get('ts'))
            if d_ts is None or not (r_ts < d_ts):
                continue
            if upper is not None and d_ts > upper:
                continue
            gold_path_rows.append({
                'ts': d.get('ts'), 'char': a['char'], 'domain': a['domain'],
                'depart_reason': REASON_SOLD,
                'depart_evidence': _baseline_evidence(r, f),
                'gold_evidence': d.get('logic_evidence'),
                'sell_frame_distance': anc['frames']})
            hit_ts.add(str(d.get('ts')))
            break                            # 窗口内首条
    gold_path_mismatch = len(hit_ts)

    # ---- ① 真失配事实清单 ----
    mismatch_rows: list[dict] = []
    for d in defects_in:
        if d.get('kind') != MISMATCH_KIND or d.get('field') not in HEAVY_FIELDS:
            continue
        f = d.get('field')
        d_ts = _parse_ts(d.get('ts'))
        aligned = None
        if d_ts is not None:
            cands = []
            for i in heavy_by_field[f]:
                h_ts = _parse_ts(rows[i].get('ts'))
                if h_ts is not None and abs(h_ts - d_ts) <= _TS_TOLERANCE:
                    cands.append((abs(h_ts - d_ts), i))
            if cands:
                aligned = min(cands)[1]
        diff_slots: list[dict] = []
        if aligned is not None:
            prev_v = _values(rows[aligned - 1]).get(f) if aligned > 0 else None
            after_v = rows[aligned].get('after')
            if f == 'bench':
                keys = [('bench', k + 1) for k in range(max(
                    len((prev_v or {}).get('slots') or []),
                    len((after_v or {}).get('slots') or [])))]
            else:
                n = max(len((prev_v or {}).get('front_slots') or []),
                        len((after_v or {}).get('front_slots') or []))
                m = max(len((prev_v or {}).get('back_slots') or []),
                        len((after_v or {}).get('back_slots') or []))
                keys = ([('front', k + 1) for k in range(n)]
                        + [('back', k + 1) for k in range(m)])
            chars: set[str] = set()
            for dom, slot in keys:
                pc = _slot_content(prev_v, dom, slot)
                ac = _slot_content(after_v, dom, slot)
                if pc == ac:
                    continue
                for c in (pc[1], ac[1]):
                    if c:
                        chars.add(c)
                diff_slots.append({
                    'domain': dom, 'slot': slot,
                    'char': ac[1] or pc[1],
                    'prev_char': pc[1], 'prev_kind': pc[0], 'prev_star': pc[2],
                    'after_char': ac[1], 'after_kind': ac[0], 'after_star': ac[2]})
            linked = [{'v': a['v'], 'domain': a['domain'], 'slot': a['slot'],
                       'char': a['char'], 'old': a['old'], 'new': a['new']}
                      for a in adopt_rows
                      if a['idx'] < aligned and a['char'] in chars]
        else:
            linked = []
        mismatch_rows.append({
            'ts': d.get('ts'), 'field': f, 'diff_slots': diff_slots,
            'linked_adoptions': linked})

    adopt_reverse = [{'domain': rows[j].get('observed', {}).get('domain'),
                      'slot': int(rows[j].get('observed', {}).get('slot') or 0),
                      'char': str(rows[j].get('observed', {}).get('char') or ''),
                      'old': rows[j].get('observed', {}).get('old'),
                      'new': rows[j].get('observed', {}).get('new'),
                      'v': rows[j].get('v'), 'is_reverse_of': rows[orig].get('v')}
                     for j, orig in sorted(reverse_of.items())]

    return {
        'heavy_total': len(heavy_idx),
        'heavy_rand_baseline': heavy_rand,
        'heavy_rand_seed': heavy_seed,
        'star_by_prefix': star_by_prefix,
        'adopt_reverted': adopt_reverted,
        'adopt_reverted_count': len(adopt_reverted),
        'adopt_reverse': adopt_reverse,
        'adopt_reverse_count': len(adopt_reverse),
        'adopt_sample_count': sum(1 for a in adopt_rows if a['idx'] not in reverse_of),
        'adopt_slot_changed': adopt_slot_changed,
        'adopt_slot_changed_count': len(adopt_slot_changed),
        'adopt_open_at_run_end': open_at_end,
        'gold_path_mismatch': gold_path_mismatch,
        'gold_path_rows': gold_path_rows,
        'mismatch_rows': mismatch_rows,
        'mismatch_count': len(mismatch_rows),
        'hold_violations': hold_violations,
        'hold_violation_count': len(hold_violations),
    }


# ============================================================ 文件 IO(main 专属)


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    if not path.is_file():
        return out
    with path.open('r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _group_by_run(rows: list[dict]) -> dict[str, list[dict]]:
    by_run: dict[str, list[dict]] = {}
    for r in rows:
        rid = r.get('run_id')
        if isinstance(rid, str) and rid:
            by_run.setdefault(rid, []).append(r)
    return by_run


def _print_run(rid: str, res: dict) -> None:
    print(f'=== {rid} ===')
    print(f"④(i) heavy 写行 = {res['heavy_total']} | 随机态基线 = "
          f"{res['heavy_rand_baseline']} | 其中开局种子 = {res['heavy_rand_seed']}")
    for prefix in (ADOPT_PREFIX, HOLD_JITTER_PREFIX, HOLD_WINDOW_PREFIX, OTHER_PREFIX):
        b = res['star_by_prefix'].get(prefix)
        if b:
            print(f"④(ii) star 行[{prefix}] total={b['total']} "
                  f"by_baseline={b['by_baseline']}")
    if not res['star_by_prefix']:
        print('④(ii) star 行 = 0(② 未受测)')
    print(f"④(iii) 采回 = {res['adopt_reverted_count']} | 回翻行 = "
          f"{res['adopt_reverse_count']} | 新分支实机样本 N = "
          f"{res['adopt_sample_count']} | 采回前离槽 = "
          f"{res['adopt_slot_changed_count']} | 局末未决 = "
          f"{res['adopt_open_at_run_end']}")
    if res['adopt_reverted']:
        print('     采回行:', json.dumps(res['adopt_reverted'], ensure_ascii=False))
    if res['adopt_reverse']:
        print('     回翻行:', json.dumps(res['adopt_reverse'], ensure_ascii=False))
    if res['adopt_slot_changed']:
        print('     离槽行:', json.dumps(res['adopt_slot_changed'], ensure_ascii=False))
    print(f"④(iv) gold_path_mismatch = {res['gold_path_mismatch']}")
    if res['gold_path_rows']:
        print('     金币行:', json.dumps(res['gold_path_rows'], ensure_ascii=False))
    print(f"① bench/deployed 真失配行 = {res['mismatch_count']}")
    if res['mismatch_rows']:
        print('     事实清单:', json.dumps(res['mismatch_rows'], ensure_ascii=False))
    print(f"② 门辖区违例 = {res['hold_violation_count']}")
    if res['hold_violations']:
        print('     违例行:', json.dumps(res['hold_violations'], ensure_ascii=False))
    print('披露:(iii) 不覆盖采回前离槽的错星;策略消费后果无直接监控键,'
          '以 (iii)/(iv) 计数与停机局的诊断定因为前兆。')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('--journal', type=Path, default=DEFAULT_JOURNAL,
                    help=f'状态流水 jsonl(缺省 {DEFAULT_JOURNAL})')
    ap.add_argument('--defects', type=Path, default=DEFAULT_DEFECTS,
                    help=f'缺陷台账 jsonl(缺省 {DEFAULT_DEFECTS})')
    ap.add_argument('--run', nargs='*', default=None,
                    help='只看这些 run_id(缺省全部)')
    ap.add_argument('--json', action='store_true', help='逐 run 原样打印 analyze_run 返回')
    args = ap.parse_args()

    by_run = _group_by_run(_read_jsonl(args.journal))
    defects = _read_jsonl(args.defects)
    want = set(args.run or [])
    tot = Counter()
    star_tot: dict[str, Counter] = {}
    for rid in sorted(by_run):
        if want and rid not in want:
            continue
        res = analyze_run(by_run[rid], defects)
        _print_run(rid, res)
        if args.json:
            print(json.dumps(res, ensure_ascii=False))
        tot['heavy_total'] += res['heavy_total']
        tot['heavy_rand_baseline'] += res['heavy_rand_baseline']
        tot['heavy_rand_seed'] += res['heavy_rand_seed']
        for prefix, b in res['star_by_prefix'].items():
            c = star_tot.setdefault(prefix, Counter())
            c['total'] += b['total']
            for src, n in b['by_baseline'].items():
                c[src] += n
    print('--- 合计 ---')
    print(f"heavy 写行 = {tot['heavy_total']};随机态基线 = {tot['heavy_rand_baseline']};"
          f"其中开局种子 = {tot['heavy_rand_seed']}")
    print('star 行(前缀: total, by_baseline) 计数:',
          {p: dict(c) for p, c in star_tot.items()} or {})


if __name__ == '__main__':
    main()
