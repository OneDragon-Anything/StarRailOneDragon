"""货币战争对局档案 → markdown 深度复盘渲染器(带判定模板槽)。

## 用途

json 对局档案不便逐条阅读;本工具把单局档案(含内嵌流切片)渲染成一份
markdown 复盘稿:逐轮铺开「状态 → 决策 → 血账 → 对账 → 战斗 → 观测冲突」,
每个决策块尾留三个判定空槽,供审阅者(人/审查智能体)逐轮填写。

## 用法(主仓根目录)

    uv run python tools/cw/replay_to_md.py --match g_20260907_075840 \
        [--run run_20260907_075840] [--out 复盘.md] [--replay-dir <dir>]

- ``--match`` game_id(必填)。档案 = ``<replay-dir>/matches/match_<game_id>.json``。
- ``--run`` 只看某一段(run_id):流明细行按该 run_id 过滤。档案逐轮表是
  跨段合并产物,不带 run_id,故轮章节不过滤;run 不在段列表时打警告并
  按全段渲染(渲染器不因参数错而死)。
- ``--out`` 输出文件;缺省打印 stdout。
- ``--replay-dir`` 缺省 ``.debug/temp/currency_war/replay``(与生产
  ``kernel/cw_observe.DEFAULT_REPLAY_DIR`` 同值,此处独立声明:本工具
  刻意零 src 导入,保持纯 stdlib、免 PYTHONPATH 即可运行)。

## 数据源(全部只读)

1. 档案 ``replay/matches/match_<game_id>.json``:rounds/loss_nodes/segments/
   resume_reconciliation/cw4_counters/slices(六条流按 run_id 的切片)。
   直读 json,**不做**自动重装配——只读工具不改数据(需要补装配走判读 CLI
   ``assemble --game``)。
2. 流 ``replay/*.jsonl``:obs_conflicts 按设计不入档案切片,恒从流文件按
   run_id 过滤(老行无 run_id 键时按局时间窗兜底);slices 缺某条流时同法
   回源读文件。decisions 行字段口径见
   ``sr_od/application/currency_war/telemetry/schema.py``(DecisionTrace,
   state/candidate_scores/actions/sess_* 全家)。

## 渲染结构

- ① 局头:结算/位面进度/策略版本(code_commit)/连续性注记/开局投资卡/
  恢复态对账(含段界重锚差 unexplained_delta)。
- ② 逐轮章节:备战帧块(状态摘要表 → 决策动作表 → 血事件行 → 对账注记)
  → 判定三槽 → 战斗行(双方/掉血/胜负)→ 补给/升级事件 → 该轮
  obs_conflicts 汇总(冲突行无轮号,按 ts 归到「决策/结算行最早 ts」锚)。
- ③ 全局:金轨迹表 / pivot 链 / armed 与拒因分键统计(有则渲染)。
- ④ 本次未能渲染的字段(遥测缺口清单)。

判定模板槽:每个备战帧块尾固定三行引用块,留空待审阅者填::

    > 决策正确性:
    > 是否符合发展主线:
    > 备选与改进:

## 韧性口径(字段缺省容忍)

所有取值走 .get 型渲染:键缺/值 None 的槽打「(无此数据)」并记入缺口
清单;文档末尾「本次未能渲染的字段」即本次数据的遥测缺口清单。出现的
缺口 ≠ 工具坏,= 该字段没采到/档案版本旧(如 v8 档案无 hp_events 列)——
清单本身就是判读输入。渲染器对畸形行(非 dict、坏 json)跳过不炸。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

#: 缺省 replay 目录(与生产 kernel/cw_observe.DEFAULT_REPLAY_DIR 同值;
#: 独立声明理由见模块 docstring「零 src 导入」)
DEFAULT_REPLAY_DIR = Path('.debug/temp/currency_war/replay')

#: 字段缺槽的统一占位符
MISSING = '(无此数据)'

#: 判定模板槽(顺序与措辞固定,消费方按行匹配)
JUDGMENT_SLOTS: tuple[str, ...] = (
    '> 决策正确性:',
    '> 是否符合发展主线:',
    '> 备选与改进:',
)

#: cw4_counters 里「拒因/拦截」语义计数键的子串(分键统计的分组判据)
_REJECT_KEY_TOKENS: tuple[str, ...] = (
    'reject', 'blocked', 'skip', 'defer', 'held', 'fenced',
    'stale', 'exhausted', 'unavailable', 'abandon', 'truncat',
)

#: 每轮 obs_conflicts 明细表的行数上限(超出只给计数,防刷屏)
_CONFLICT_ROWS_CAP = 15

# ---------------------------------------------------------------------------
# 基础渲染件
# ---------------------------------------------------------------------------


class GapLog:
    """遥测缺口清单:记录「本次渲染中取不到的字段路径」及出现次数。

    field 传点分路径(如 ``rounds[].hp_delta``);同一路径多次缺只累计数。
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def miss(self, field: str) -> None:
        """记录一次字段缺口。"""
        self._counts[field] = self._counts.get(field, 0) + 1

    @property
    def fields(self) -> dict[str, int]:
        """缺口路径 → 出现次数(只读副本)。"""
        return dict(self._counts)

    def summary_lines(self) -> list[str]:
        """缺口清单 markdown 行;零缺口给一句「全部字段渲染成功」。"""
        if not self._counts:
            return ['全部字段渲染成功,无遥测缺口。']
        lines = []
        for field, n in sorted(self._counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f'- `{field}` ×{n}')
        return lines


def _fmt(v: Any) -> str:
    """值 → 单行字符串(bool 中文化,容器压成紧凑 json)。"""
    if isinstance(v, bool):
        return '是' if v else '否'
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, separators=(',', ':'))
    return str(v)


def _esc(s: str) -> str:
    """markdown 表格单元格转义(竖线是列分隔符,必须换掉)。"""
    return s.replace('|', '\\|').replace('\n', ' ')


def _short(v: Any, n: int = 48) -> str:
    """值 → 截断字符串(防长 payload 刷屏)。"""
    s = _fmt(v)
    return s if len(s) <= n else s[:n] + '…'


def _cell(d: dict[str, Any] | None, key: str, field: str, gaps: GapLog,
          *, none_ok: bool = False, dash_empty: bool = False) -> str:
    """.get 型取值渲染:键缺/值 None → ``(无此数据)`` 并记缺口。

    - ``none_ok=True``:None 是语义值(如首轮 hp_delta=None)→ 渲染 '—'
      不记缺口;键整个缺失仍记(缺键 = 遥测缺,值 None = 采集到但为空)。
    - ``dash_empty=True``:空串渲染 '—'(如 sess_p1_pair=''=未锁,是
      真实状态不是缺口)。
    """
    if not isinstance(d, dict):
        gaps.miss(field)
        return MISSING
    if key not in d:
        gaps.miss(field)
        return MISSING
    v = d[key]
    if v is None:
        if not none_ok:
            gaps.miss(field)
        return '—'
    if dash_empty and v == '':
        return '—'
    return _esc(_fmt(v))


def _sub(d: dict[str, Any] | None, key: str, field: str, gaps: GapLog
         ) -> dict[str, Any] | None:
    """安全取嵌套 dict;整体缺失只记一条缺口(防逐字段重复计数)。"""
    v = (d or {}).get(key)
    if isinstance(v, dict):
        return v
    gaps.miss(field)
    return None


def _trust_mark(d: dict[str, Any] | None, key: str) -> str:
    """可读位标记:字段存在且为 False → 不可信标记;缺失/True → 空串。

    缺失不记缺口(可信位是附带信息,主值缺已在主值槽记过)。
    """
    v = (d or {}).get(key)
    return ' [!不可信]' if v is False else ''


def _kv_table(rows: list[tuple[str, str]]) -> list[str]:
    """两列表格(项 | 值)。"""
    out = ['| 项 | 值 |', '|---|---|']
    out.extend(f'| {k} | {v} |' for k, v in rows)
    return out


def _read_jsonl_tolerant(p: Path) -> list[dict[str, Any]]:
    """容错读 jsonl(坏行/空行跳过;obs_conflicts journal 有截断行先例)。
    文件缺失 → 空列表(调用方负责记缺口)。"""
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


def _load_stream(archive: dict[str, Any], replay_dir: Path, name: str,
                 gaps: GapLog) -> list[dict[str, Any]]:
    """流行加载:档案切片优先,缺则回源 replay 目录读文件。"""
    slices = archive.get('slices')
    if isinstance(slices, dict) and name in slices:
        rows = slices.get(name)
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
        gaps.miss(f'slices.{name}(切片存在但非列表)')
        return []
    rows = _read_jsonl_tolerant(replay_dir / name)
    if not rows:
        gaps.miss(f'流 {name}(档案切片缺、流文件缺或空)')
    return rows


# ---------------------------------------------------------------------------
# 数据准备
# ---------------------------------------------------------------------------


def _segment_ids(archive: dict[str, Any]) -> list[str]:
    """段 run_id 列表(顺档案段序)。"""
    out = []
    for s in archive.get('segments') or []:
        if isinstance(s, dict) and s.get('run_id'):
            out.append(str(s['run_id']))
    return out


def _filter_by_run(rows: list[dict[str, Any]], allowed: set[str],
                   ts_lo: str, ts_hi: str) -> list[dict[str, Any]]:
    """按 run_id 过滤;无 run_id 键的行按局时间窗兜底(obs_conflicts 老行)。"""
    out = []
    for r in rows:
        rid = r.get('run_id')
        if rid:
            if str(rid) in allowed:
                out.append(r)
        elif ts_lo <= str(r.get('ts') or '') <= ts_hi:
            out.append(r)
    return out


def _round_anchors(rows: list[dict[str, Any]]
                   ) -> list[tuple[str, tuple[int, int]]]:
    """轮归属锚:每个 (plane, round) 的最早行 ts(决策+结算行)。

    冲突行(obs_conflicts)无轮号,归属 = 晚于本轮锚、早于下轮锚。
    """
    earliest: dict[tuple[int, int], str] = {}
    for r in rows:
        try:
            k = (int(r.get('plane') or 1), int(r.get('round_num') or 0))
        except (TypeError, ValueError):
            continue
        ts = str(r.get('ts') or '')
        if not ts:
            continue
        if k not in earliest or ts < earliest[k]:
            earliest[k] = ts
    return sorted((ts, k) for k, ts in earliest.items())


def _attr_round(anchors: list[tuple[str, tuple[int, int]]], ts: str
                ) -> tuple[int, int] | None:
    """ts → 所属轮键;早于首锚/无 ts → None(未归轮桶)。"""
    cur: tuple[int, int] | None = None
    for a_ts, k in anchors:
        if ts >= a_ts:
            cur = k
        else:
            break
    return cur


def _group_by_round(rows: list[dict[str, Any]]
                    ) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """行按 (plane, round_num) 分组(坏键行丢弃——渲染侧不猜轮号)。"""
    out: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for r in rows:
        try:
            k = (int(r.get('plane') or 0), int(r.get('round_num') or 0))
        except (TypeError, ValueError):
            continue
        out.setdefault(k, []).append(r)
    return out


# ---------------------------------------------------------------------------
# 局头
# ---------------------------------------------------------------------------


def _render_header(archive: dict[str, Any], seg_ids: list[str],
                   run_filter: str | None, gaps: GapLog) -> list[str]:
    """局头:标识行 + 结算/版本/连续性表 + 段列表 + 开局投资卡。"""
    gid = archive.get('game_id') or '?'
    schema_v = archive.get('schema_version')
    parts = [f'# 货币战争复盘 {gid}', '']
    note = (f'工具 tools/cw/replay_to_md.py · 档案 schema_version='
            f'{schema_v if schema_v is not None else MISSING} · 段数 '
            f'{len(seg_ids)}({"+".join(seg_ids) if seg_ids else MISSING})'
            f' · 时间窗 {_cell(archive, "start_ts", "start_ts", gaps, dash_empty=True)}'
            f' ~ {_cell(archive, "end_ts", "end_ts", gaps, dash_empty=True)}')
    parts += [f'> {note}', '']
    if run_filter and run_filter not in seg_ids:
        parts += [f'> [警告] --run {run_filter} 不在段列表,流过滤无命中,'
                  '已按全段渲染。', '']

    endgame = archive.get('endgame')
    endgame = endgame if isinstance(endgame, dict) else None
    if endgame is None:
        gaps.miss('endgame')
    seg0 = (archive.get('segments') or [{}])
    seg0 = seg0[0] if seg0 and isinstance(seg0[0], dict) else {}
    summary = _sub(seg0, 'summary', 'segments[0].summary', gaps) or {}
    abandoned = endgame.get('abandoned') if endgame else None
    result = _cell(endgame, 'result', 'endgame.result', gaps, dash_empty=True)
    if abandoned is True:
        result += '(弃局/中断)'
    ver = _sub(archive, 'strategy_version', 'strategy_version', gaps) or {}
    header_rows = [
        ('结局', result),
        ('到达位面 / 存活轮',
         f"{_cell(endgame, 'plane_reached', 'endgame.plane_reached', gaps, none_ok=True)}"
         f' / {_cell(endgame, "rounds_survived", "endgame.rounds_survived", gaps, none_ok=True)}'),
        ('终局 HP(结算真值)',
         _cell(endgame, 'final_hp', 'endgame.final_hp', gaps, none_ok=True)),
        ('难度', _cell(summary, 'difficulty', 'runs.summary.difficulty',
                       gaps, dash_empty=True)),
        ('策略版本 code_commit',
         _cell(ver, 'code_commit', 'strategy_version.code_commit', gaps,
               dash_empty=True)),
        ('注册表指纹',
         _cell(ver, 'registry_fingerprint', 'strategy_version.registry_fingerprint',
               gaps, dash_empty=True)),
        ('连续性注记', _cell(archive, 'continuity_note', 'continuity_note',
                            gaps, dash_empty=True)),
    ]
    parts += ['## 1. 局头', '']
    parts += _kv_table(header_rows)

    parts += ['', '### 段列表', '',
              '| 段 run_id | 首帧(位面,轮) | 结果 | 存活轮 | 终局 HP |',
              '|---|---|---|---|---|']
    for s in archive.get('segments') or []:
        if not isinstance(s, dict):
            continue
        sm = s.get('summary') if isinstance(s.get('summary'), dict) else {}
        ff = _fmt(s.get('first_frame')) if s.get('first_frame') is not None else '—'
        parts.append(
            f"| {_cell(s, 'run_id', 'segments[].run_id', gaps)} | {ff} "
            f"| {_cell(sm, 'result', 'segments[].summary.result', gaps, dash_empty=True)} "
            f"| {_cell(sm, 'rounds_survived', 'segments[].summary.rounds_survived', gaps, none_ok=True)} "
            f"| {_cell(sm, 'final_hp', 'segments[].summary.final_hp', gaps, none_ok=True)} |")

    parts += _render_opening(archive, gaps)
    parts += _render_recon(archive, gaps)
    return parts


def _render_opening(archive: dict[str, Any], gaps: GapLog) -> list[str]:
    """开局面:难度/已选投资卡全表(带选中位)。"""
    opening = _sub(archive, 'opening', 'opening', gaps)
    if opening is None:
        return ['### 开局面', '', MISSING, '']
    invest = opening.get('invest_cards')
    parts = ['### 开局面', '']
    if isinstance(invest, list) and invest:
        parts += ['投资卡(投资策略环境 + 策略卡,chosen=是否选中):', '',
                  '| kind | idx | 名称 | 选中 | 效果摘要 |', '|---|---|---|---|---|']
        for c in invest:
            if not isinstance(c, dict):
                continue
            parts.append(
                f"| {_cell(c, 'kind', 'opening.invest_cards[].kind', gaps, dash_empty=True)} "
                f"| {_cell(c, 'idx', 'opening.invest_cards[].idx', gaps, none_ok=True)} "
                f"| {_cell(c, 'name', 'opening.invest_cards[].name', gaps)} "
                f"| {_cell(c, 'chosen', 'opening.invest_cards[].chosen', gaps)} "
                f"| {_esc(_short(c.get('effect_text'), 80))} |")
        parts.append('')
    else:
        gaps.miss('opening.invest_cards')
        parts += [MISSING, '']
    chosen = opening.get('chosen_strategies')
    if isinstance(chosen, list) and chosen:
        parts.append('已选策略卡:' + '、'.join(_fmt(x) for x in chosen))
        parts.append('')
    return parts


def _render_recon(archive: dict[str, Any], gaps: GapLog) -> list[str]:
    """恢复态对账列(续局段恢复帧 vs 前段末帧;含段界重锚差)。"""
    recon = archive.get('resume_reconciliation')
    parts = ['### 恢复态对账(resume_reconciliation)', '']
    if recon is None:
        gaps.miss('resume_reconciliation')
        parts += [MISSING, '']
        return parts
    if not isinstance(recon, list) or not recon:
        parts += ['(空 = 单段局无续局段,无对账事件)', '']
        return parts
    parts += ['| 段 run_id | 恢复帧(位面,轮) | hp 恢复/前段末 | 金 | 等级 |'
              ' 重锚差 unexplained_delta |', '|---|---|---|---|---|---|']
    for row in recon:
        if not isinstance(row, dict):
            continue
        rf = row.get('resume_frame') if isinstance(row.get('resume_frame'), dict) else {}
        hp = row.get('hp') if isinstance(row.get('hp'), dict) else {}
        gold = row.get('gold') if isinstance(row.get('gold'), dict) else {}
        parts.append(
            f"| {_cell(row, 'run_id', 'resume_reconciliation[].run_id', gaps)} "
            f"| {_esc(_fmt(rf.get('plane')))}r{_esc(_fmt(rf.get('round_num')))} "
            f"| {_esc(_fmt(hp.get('resume')))} / {_esc(_fmt(hp.get('prev_final')))} "
            f"| {_esc(_fmt(gold.get('resume')))} / {_esc(_fmt(gold.get('prev_final')))} "
            f"| {_esc(_fmt(row.get('unexplained_delta')))} |")
    parts.append('')
    return parts


# ---------------------------------------------------------------------------
# 逐轮
# ---------------------------------------------------------------------------


def _hp_display(r: dict[str, Any], gaps: GapLog) -> str:
    """轮槽血量显示:值 + 来源 + 可信位。"""
    hp = _cell(r, 'hp', 'rounds[].hp', gaps, none_ok=True)
    if hp in ('—', MISSING):
        return hp
    src = r.get('hp_source')
    src_s = {'settlement': '结算', 'frame': '备帧', 'none': '无源'}.get(
        src if isinstance(src, str) else '', _fmt(src) if src else '')
    return f'{hp}({src_s}{_trust_mark(r, "hp_trusted")})' if src_s else hp


def _status_table(r: dict[str, Any], gaps: GapLog) -> list[str]:
    """备战帧块·状态摘要表(金/血/等级/锁线/目标配方/仓位/板面)。"""
    terminal = r.get('terminal')
    if isinstance(terminal, dict):
        def _q(v: Any) -> str:
            return _fmt(v) if v is not None else '?'
        pos = (f"场{_q(terminal.get('deployed_count'))}"
               f"/备{_q(terminal.get('bench_count'))}"
               f"/穿{_q(terminal.get('equips_worn'))}"
               f"/持{_q(terminal.get('equips_owned'))}")
        closure = r.get('terminal_closure')
        if closure == 'mid_prep':
            pos += ' [!mid_prep 收口,终态滞后一个动作]'
    else:
        gaps.miss('rounds[].terminal')
        pos = MISSING
    xp = r.get('xp_progress')
    xp_s = (f"{_fmt(xp[0])}/{_fmt(xp[1])}"
            if isinstance(xp, list) and len(xp) == 2 else '—')
    board = r.get('board')
    board_s = _esc(_short(board, 80)) if board else '—'
    rows = [
        ('金', _cell(r, 'gold', 'rounds[].gold', gaps, none_ok=True)
         + _trust_mark(r, 'gold_readable')),
        ('血(轮槽)', _hp_display(r, gaps)),
        ('血变化 hp_delta', _cell(r, 'hp_delta', 'rounds[].hp_delta', gaps,
                                  none_ok=True)),
        ('等级', _cell(r, 'level', 'rounds[].level', gaps, none_ok=True)),
        ('经验(xp/next)', xp_s),
        ('锁线 sess_p1_pair', _cell(r, 'sess_p1_pair', 'rounds[].sess_p1_pair',
                                    gaps, none_ok=True, dash_empty=True)),
        ('目标配方', _cell(r, 'target_comp', 'rounds[].target_comp', gaps,
                          none_ok=True, dash_empty=True)),
        ('仓位(终态 场/备/穿/持)', pos),
        ('板面羁绊档位(决策帧)', board_s),
    ]
    return ['**状态摘要**(决策帧口径;「执行后」看仓位行)', ''] + _kv_table(rows)


def _action_params(a: dict[str, Any]) -> str:
    """动作参数列:除 __type__ 外的键值;card 子对象取人读摘要。"""
    parts: list[str] = []
    for k, v in a.items():
        if k == '__type__':
            continue
        if k == 'card' and isinstance(v, dict):
            parts.append(f"card={v.get('name') or '?'}"
                         f"({ _fmt(v.get('star'))}★/{_fmt(v.get('cost'))}金)")
        elif k == 'reason' and not v:
            continue
        else:
            parts.append(f'{k}={_short(v, 40)}')
    return _esc('; '.join(parts)) or '—'


def _action_table(r: dict[str, Any], gaps: GapLog) -> list[str]:
    """备战帧块·决策动作表(全帧合并动作 + 逐动作 reason)。"""
    actions = r.get('actions')
    parts = ['**决策动作**(该轮全部决策帧动作合并,流内序):', '']
    if isinstance(actions, list) and actions:
        parts += ['| # | 动作 | 参数/reason |', '|---|---|---|']
        for i, a in enumerate(actions, 1):
            if not isinstance(a, dict):
                parts.append(f'| {i} | (非 dict 行: {_esc(_short(a))}) | |')
                continue
            t = a.get('__type__') or '?'
            parts.append(f'| {i} | {_esc(_fmt(t))} | {_action_params(a)} |')
        parts.append('')
    else:
        gaps.miss('rounds[].actions')
        parts += [MISSING, '']
    counts = r.get('action_counts')
    if isinstance(counts, dict) and counts:
        parts.append('动作计数:' + ' '.join(
            f'{k}×{v}' for k, v in sorted(counts.items())))
        parts.append('')
    detail = r.get('decision_detail')
    detail = detail if isinstance(detail, dict) else None
    if detail is None:
        gaps.miss('rounds[].decision_detail')
        return parts
    rejects = detail.get('shop_rejects')
    if isinstance(rejects, dict) and rejects:
        parts.append('商店拒因(shop_rejects:该轮波面未买牌及原因):'
                     + '、'.join(f'{k}={_esc(_short(v, 24))}'
                                 for k, v in rejects.items()))
        parts.append('')
    scores = detail.get('candidate_scores')
    if isinstance(scores, dict) and scores:
        parts.append('候选配方打分:' + '、'.join(
            f'{k}={_short(v, 8)}' for k, v in scores.items()))
        parts.append('')
    intent = detail.get('v3_intention')
    if isinstance(intent, dict):
        phase = intent.get('phase') or ''
        locked = intent.get('locked_comp') or ''
        forced = ' forced' if intent.get('forced') else ''
        if phase or locked:
            parts.append(f'意向状态机:v3_intention.phase={_esc(_fmt(phase))}'
                         f' locked={_esc(_fmt(locked))}{forced}')
            parts.append('')
    return parts


def _blood_events(r: dict[str, Any], ctx: dict[str, Any], key: tuple[int, int],
                  gaps: GapLog) -> list[str]:
    """备战帧块·血事件行:hp_pay 事件显影 + 补给合成行警告。"""
    parts: list[str] = []
    if ctx['has_hp_events_col']:
        events = [e for e in ctx['hp_events']
                  if (e.get('plane'), e.get('round')) == key]
        if events:
            parts.append('血购事件(hp_events,血购击数口径):')
            for e in events:
                parts.append(
                    f"- hp_delta={_fmt(e.get('hp_delta'))}"
                    f" mode={_fmt(e.get('mode'))}"
                    f" clicks={_fmt(e.get('clicks'))}"
                    f" basis={_fmt(e.get('basis'))} ts={_fmt(e.get('ts'))}")
            parts.append('')
    else:
        # v8 旧档无顶层 hp_events 列:由 exogenous 流 kind='hp_pay' 直接显影
        gaps.miss('顶层 hp_events 列(旧档案,由 exogenous 流兜底显影)')
        events = [e for e in ctx['exogenous']
                  if (e.get('kind') or '') == 'hp_pay'
                  and (e.get('choice') or {}).get('plane') == key[0]
                  and (e.get('choice') or {}).get('round_num') == key[1]]
        if events:
            parts.append('血购事件(旧档口径,exogenous.kind=hp_pay):')
            for e in events:
                ch = e.get('choice') or {}
                parts.append(f"- hp_delta={_fmt(ch.get('hp_delta'))}"
                             f" mode={_fmt(ch.get('mode'))} ts={_fmt(e.get('ts'))}")
            parts.append('')
    outcome = r.get('outcome')
    if isinstance(outcome, dict) and outcome.get('source') == 'synthetic_supply':
        parts.append('[!] 本轮结算行为补给合成行(快照合成非结算事件,'
                     'hp 先验「陈旧直到证伪」,判读降权)。')
        parts.append('')
    if not parts:
        parts = ['血事件:无(无血购事件、无合成行)。', '']
    return parts


def _recon_notes(r: dict[str, Any], ctx: dict[str, Any],
                 key: tuple[int, int], gaps: GapLog) -> list[str]:
    """备战帧块·对账注记:恢复对账/血购对账缺陷/对账留证截图。"""
    parts: list[str] = []
    for row in ctx['recon_rows']:
        rf = row.get('resume_frame') if isinstance(row.get('resume_frame'), dict) else {}
        if (rf.get('plane'), rf.get('round_num')) == key:
            parts.append(
                f"恢复对账:本帧为续局段恢复帧;unexplained_delta="
                f"{_fmt(row.get('unexplained_delta'))}"
                f"(负=停机间隙真掉血;consumed_by_chain="
                f"{_fmt(row.get('consumed_by_chain'))})")
            parts.append('')
    if ctx['has_defects_col']:
        defects = [d for d in ctx['hp_pay_defects']
                   if (d.get('plane'), d.get('round')) == key]
        if defects:
            parts.append('血购对账缺陷(hp_pay_defects,建模期望 vs 结算真值):')
            for d in defects:
                parts.append(
                    f"- expected={_fmt(d.get('expected_hp'))}"
                    f" actual={_fmt(d.get('actual_hp'))}"
                    f" gap={_fmt(d.get('gap'))}"
                    f" modeled_paid={_fmt(d.get('modeled_paid'))}")
            parts.append('')
    else:
        gaps.miss('顶层 hp_pay_defects 列(旧档案)')
    evidence = r.get('evidence')
    if isinstance(evidence, list) and evidence:
        parts.append(f'对账留证截图 ×{len(evidence)}:'
                     + '、'.join(_fmt(x) for x in evidence[:4])
                     + ('…' if len(evidence) > 4 else ''))
        parts.append('')
    if not parts:
        parts = ['对账:无注记(无恢复对账、无缺陷、无留证)。', '']
    return parts


def _battle_lines(r: dict[str, Any], ctx: dict[str, Any],
                  key: tuple[int, int], gaps: GapLog) -> list[str]:
    """战斗行:双方/掉血/胜负(结算行真值口径)。"""
    o = _sub(r, 'outcome', 'rounds[].outcome', gaps)
    if o is None:
        return ['#### 战斗行', '', MISSING, '']
    bosses = o.get('boss_names')
    enemy = ('、'.join(_fmt(b) for b in bosses)
             if isinstance(bosses, list) and bosses else '—')
    killed = o.get('killed')
    hp_after = o.get('hp_after')
    if killed is True:
        verdict = '胜(killed)'
    elif hp_after == 0:
        verdict = '败(战后 HP=0)'
    elif killed is False:
        verdict = '存活(killed=False)'
    else:
        gaps.miss('rounds[].outcome.killed')
        verdict = MISSING
    losses = ctx['loss_nodes'].get(key) or []
    loss_s = '、'.join(_fmt(ln.get('delta')) for ln in losses) if losses \
        else ('—' if r.get('hp_delta') is None else str(r.get('hp_delta')))
    rows = [
        ('节点', _cell(o, 'node_type', 'rounds[].outcome.node_type', gaps,
                      dash_empty=True)),
        ('我方配方', _cell(o, 'comp_tag', 'rounds[].outcome.comp_tag', gaps,
                          dash_empty=True)),
        ('敌方(boss)', _esc(enemy)),
        ('敌方战后 HP', _cell(o, 'enemy_hp_after',
                             'rounds[].outcome.enemy_hp_after', gaps,
                             none_ok=True)),
        ('我方战后 HP', f'{_esc(_fmt(hp_after))}'
         f'(置信 {_esc(_fmt(o.get("hp_confidence")))})'),
        ('掉血(战斗腿)', _esc(loss_s)),
        ('胜负', verdict),
        ('伤害', _cell(o, 'damage_dealt', 'rounds[].outcome.damage_dealt',
                       gaps, none_ok=True)),
        ('位面进度', _cell(o, 'progress_delta',
                          'rounds[].outcome.progress_delta', gaps, none_ok=True)),
        ('连胜', _cell(o, 'streak', 'rounds[].outcome.streak', gaps,
                       none_ok=True)),
        ('敌方词缀', _esc('、'.join(_fmt(x) for x in o.get('enemy_affixes') or [])
                        or '—')),
    ]
    return ['#### 战斗行', ''] + _kv_table(rows) + ['']


def _supply_upgrade(r: dict[str, Any], ledger_rows: list[dict[str, Any]],
                    gaps: GapLog) -> list[str]:
    """补给/升级事件:金账单元(spend_ledger)+ 升级/点经验计数 + 补给拾取。"""
    parts: list[str] = []
    if ledger_rows:
        parts.append('金账单元(spend_ledger,购买单元边界):')
        for s in ledger_rows:
            parts.append(
                f"- unit#{_fmt(s.get('unit_seq'))}"
                f" [{_fmt(s.get('boundary'))}]"
                f" {_esc(_fmt(s.get('duration_s')))}s"
                f" 金{_esc(_fmt(s.get('gold_before')))}"
                f"→{_esc(_fmt(s.get('gold_close')))}"
                f" | {_esc(_short(s.get('detail'), 90))}")
        parts.append('')
    counts = r.get('action_counts') if isinstance(r.get('action_counts'), dict) else None
    if counts is None:
        gaps.miss('rounds[].action_counts(升级/点经验计数)')
        parts.append('升级动作/点经验:(无此数据)')
    else:
        # 键缺席 = 该轮真没升级/没点经验(计数 0),不是遥测缺口
        parts.append(f"升级动作 ×{_fmt(counts.get('LevelUpShop') or 0)},"
                     f"点经验(扑满)×{_fmt(counts.get('ClickSpheres') or 0)}。")
    o = r.get('outcome')
    pick = o.get('supply_pick') if isinstance(o, dict) else None
    if pick:
        parts.append(f'补给拾取:{_esc(_short(pick, 60))}')
    if not parts:
        parts = ['补给/升级:无(无金账单元、无升级动作、无补给拾取)。']
    parts.append('')
    return parts


def _conflict_table(rows: list[dict[str, Any]]) -> list[str]:
    """obs_conflicts 明细表(带行数上限)。"""
    parts = [f'观测冲突 ×{len(rows)}(识别回读与账面不一致,采新对账纠漂):',
             '', '| ts | field | 判定 | 源 | 变化(old→新) |',
             '|---|---|---|---|---|']
    for c in rows[:_CONFLICT_ROWS_CAP]:
        parts.append(
            f"| {_esc(_fmt(c.get('ts')))} | {_esc(_fmt(c.get('field')))} "
            f"| {_esc(_short(c.get('verdict'), 30))} "
            f"| {_esc(_fmt(c.get('source')))} "
            f"| {_esc(_short(c.get('old'), 24))}→{_esc(_short(c.get('new'), 24))} |")
    if len(rows) > _CONFLICT_ROWS_CAP:
        parts.append(f'…另有 {len(rows) - _CONFLICT_ROWS_CAP} 条略(量 '
                     f'{len(rows)})。')
    parts.append('')
    return parts


def _render_round(idx: int, r: dict[str, Any], ctx: dict[str, Any],
                  gaps: GapLog) -> list[str]:
    """单轮章节:备战帧块 + 判定三槽 + 战斗行 + 补给/升级 + obs_conflicts。"""
    if not isinstance(r, dict):
        return [f'### 轮 #{idx}', '', f'(非 dict 轮行: {_esc(_short(r))})', '']
    plane = r.get('plane') if r.get('plane') is not None else '?'
    rnd = r.get('round') if r.get('round') is not None else '?'
    node = r.get('node_type') or '?节点'
    key = (plane, rnd) if isinstance(plane, int) and isinstance(rnd, int) \
        else None
    parts = [f'### {idx}. P{plane}·R{rnd}(节点:{_esc(_fmt(node))})', '']
    if key is None:
        gaps.miss('rounds[].plane/round(轮键非法,流明细无法归轮)')
    k = key or (-1, -1)

    parts += ['#### 备战帧块', '']
    parts += _status_table(r, gaps)
    parts += ['']
    parts += _action_table(r, gaps)
    parts += ['']
    parts += _blood_events(r, ctx, k, gaps)
    parts += _recon_notes(r, ctx, k, gaps)
    parts += list(JUDGMENT_SLOTS)
    parts += ['', '_(判定槽留空待审阅者填写;判据 = 玩法恒常标准:'
              '配方纪律/经济纪律/响应纪律)_', '']
    parts += _battle_lines(r, ctx, k, gaps)
    parts += ['#### 补给/升级事件', '']
    parts += _supply_upgrade(r, ctx['spend_by_round'].get(k, []), gaps)
    parts += ['#### 该轮 obs_conflicts 汇总', '']
    conflicts = ctx['conflicts_by_round'].get(k, [])
    parts += _conflict_table(conflicts) if conflicts \
        else ['无观测冲突记录。', '']
    return parts


# ---------------------------------------------------------------------------
# 全局
# ---------------------------------------------------------------------------


def _render_gold_traj(rounds: list[dict[str, Any]], archive: dict[str, Any],
                      gaps: GapLog) -> list[str]:
    """金轨迹表:逐轮轮槽金(带可信位)+ 段摘要 gold_trajectory 原始列。"""
    parts = ['### 金轨迹', '', '| 轮 | 金 | 可信 |', '|---|---|---|']
    for r in rounds:
        if not isinstance(r, dict):
            continue
        g = _cell(r, 'gold', 'rounds[].gold(金轨迹)', gaps, none_ok=True)
        trusted = '是' if r.get('gold_readable') is not False else '[!否]'
        parts.append(f'| P{r.get("plane")}·R{r.get("round")} | {g} | {trusted} |')
    parts.append('')
    for s in archive.get('segments') or []:
        sm = s.get('summary') if isinstance(s.get('summary'), dict) else {}
        traj = sm.get('gold_trajectory')
        if isinstance(traj, list) and traj:
            rid = s.get('run_id') if isinstance(s, dict) else '?'
            parts.append(f'段 {_esc(_fmt(rid))} gold_trajectory(段摘要):'
                         + ', '.join(_fmt(x) for x in traj))
            parts.append('')
    if not parts[-1].strip():
        parts.pop()
    return parts


def _render_pivot(rounds: list[dict[str, Any]], archive: dict[str, Any],
                  gaps: GapLog) -> list[str]:
    """pivot 链:目标配方的变更序列(换线即 pivot)+ 段摘要计数对账。"""
    parts = ['### pivot 链(目标配方变更序列)', '']
    chain: list[str] = []
    prev: Any = None
    for r in rounds:
        if not isinstance(r, dict):
            continue
        tc = r.get('target_comp')
        if not tc or tc == prev:
            continue
        chain.append(f"P{r.get('plane')}·R{r.get('round')} {_esc(_fmt(tc))}")
        prev = tc
    parts.append(' → '.join(chain) if chain
                 else '(无目标配方记录,pivot 链不可得)')
    parts.append('')
    for s in archive.get('segments') or []:
        sm = s.get('summary') if isinstance(s.get('summary'), dict) else {}
        committed = sm.get('comps_committed')
        if isinstance(committed, list) and committed:
            rid = s.get('run_id') if isinstance(s, dict) else '?'
            parts.append(f'段 {_esc(_fmt(rid))} comps_committed(段摘要):'
                         + '、'.join(_fmt(x) for x in committed)
                         + f'(pivot_count={_esc(_fmt(sm.get("pivot_count")))})')
            parts.append('')
        elif sm:
            gaps.miss('segments[].summary.comps_committed')
    if not parts[-1].strip():
        parts.pop()
    return parts


def _render_counters(archive: dict[str, Any], gaps: GapLog) -> list[str]:
    """armed 与拒因分键统计(cw4_counters 有则渲染;None=无计数流)。"""
    parts = ['### armed 与拒因分键统计(cw4_counters 行为观测计数)', '']
    counters = archive.get('cw4_counters')
    if counters is None:
        gaps.miss('cw4_counters(无计数流:本批改动前落的局/流缺失)')
        parts += [MISSING, '']
        return parts
    if not isinstance(counters, dict):
        gaps.miss('cw4_counters(非 dict)')
        parts += [MISSING, '']
        return parts
    if not counters:
        parts += ['(局内真实零计数。)', '']
        return parts
    armed = {k: v for k, v in counters.items() if 'armed' in k}
    rejects = {k: v for k, v in counters.items()
               if any(t in k for t in _REJECT_KEY_TOKENS)}
    rest = {k: v for k, v in counters.items() if k not in armed and k not in rejects}
    for title, group in (('armed(臂位/武装类)', armed),
                         ('拒因/拦截类', rejects), ('其他计数', rest)):
        parts.append(f'**{title}**' + (f' ×{len(group)}' if group else '(无)'))
        parts.append('')
        if group:
            for k, v in sorted(group.items()):
                parts.append(f'- {k}: {v}')
            parts.append('')
    return parts


def _render_round_continuity(rounds: list[dict[str, Any]]) -> list[str]:
    """轮号连续性检查:逐轮键 (plane, round) 在位面内断档 = 该轮数据缺失。

    断档不是渲染器跳过,是源数据里就没有该轮的任何决策/结算行——
    复盘前先知道「少了一轮」,免得把轮序列误读成连续叙事。
    """
    by_plane: dict[int, set[int]] = {}
    for r in rounds:
        if not isinstance(r, dict):
            continue
        try:
            by_plane.setdefault(int(r.get('plane') or 0), set()).add(
                int(r.get('round') or 0))
        except (TypeError, ValueError):
            continue
    holes: list[str] = []
    for p, rounds_set in sorted(by_plane.items()):
        missing = sorted(set(range(min(rounds_set), max(rounds_set) + 1))
                         - rounds_set)
        if missing:
            holes.append(f'P{p} 缺轮 {missing}')
    parts = ['### 轮号连续性', '']
    parts.append('、'.join(holes) if holes else '各位面轮号连续,无断档。')
    parts.append('')
    return parts


def _render_global(archive: dict[str, Any], rounds: list[dict[str, Any]],
                   gaps: GapLog) -> list[str]:
    """全局段:金轨迹/pivot 链/armed 与拒因分键统计。"""
    parts = ['## 3. 全局', '']
    parts += _render_round_continuity(rounds)
    parts += _render_gold_traj(rounds, archive, gaps)
    parts += _render_pivot(rounds, archive, gaps)
    parts += _render_counters(archive, gaps)
    return parts


def _unattributed_conflicts(ctx: dict[str, Any]) -> list[str]:
    """未归轮冲突(早于首锚/无 ts)集中显影,防静默丢行。"""
    rows = ctx['conflicts_by_round'].get((-1, -1), [])
    if not rows:
        return []
    return ['### 未归轮 obs_conflicts(早于首锚/缺 ts)', ''] \
        + _conflict_table(rows)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def render_match(archive: dict[str, Any], replay_dir: Path,
                 run_filter: str | None = None) -> str:
    """渲染单局档案 → markdown 全文(含文末缺口清单)。

    archive = 档案 json dict;replay_dir = replay 目录(obs_conflicts 与
    切片缺失流的回源处);run_filter = 可选段 run_id 过滤。
    """
    gaps = GapLog()
    seg_ids = _segment_ids(archive)
    rounds_all = [r for r in (archive.get('rounds') or []) if isinstance(r, dict)]
    if archive.get('rounds') is None:
        gaps.miss('rounds')

    # 流明细:切片优先,回源文件;--run 过滤只作用于流行
    allowed = {run_filter} if run_filter else set(seg_ids)
    ts_lo = str(archive.get('start_ts') or '')
    # end_ts 缺 → 9999 兜底:ISO 串字典序比较下放行全部无 run_id 老行
    ts_hi = str(archive.get('end_ts') or '9999-12-31')
    decisions = _filter_by_run(_load_stream(archive, replay_dir,
                                            'decisions.jsonl', gaps),
                               allowed, ts_lo, ts_hi)
    outcomes = _filter_by_run(_load_stream(archive, replay_dir,
                                           'outcomes.jsonl', gaps),
                              allowed, ts_lo, ts_hi)
    exogenous = _filter_by_run(_load_stream(archive, replay_dir,
                                            'exogenous.jsonl', gaps),
                               allowed, ts_lo, ts_hi)
    spend = _filter_by_run(_load_stream(archive, replay_dir,
                                        'spend_ledger.jsonl', gaps),
                           allowed, ts_lo, ts_hi)

    # obs_conflicts:恒走流文件(按设计不入切片)
    conflict_path = replay_dir / 'obs_conflicts.jsonl'
    conflicts_raw = _read_jsonl_tolerant(conflict_path)
    if not conflict_path.exists():
        gaps.miss('obs_conflicts.jsonl(文件缺失)')
    conflicts = _filter_by_run(conflicts_raw, allowed, ts_lo, ts_hi)

    anchors = _round_anchors(decisions + outcomes)
    conflicts_by_round: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for c in conflicts:
        k = _attr_round(anchors, str(c.get('ts') or '')) or (-1, -1)
        conflicts_by_round.setdefault(k, []).append(c)

    hp_events = archive.get('hp_events')
    has_hp_events_col = isinstance(hp_events, list)
    defects = archive.get('hp_pay_defects')
    has_defects_col = isinstance(defects, list)
    recon_rows = [r for r in (archive.get('resume_reconciliation') or [])
                  if isinstance(r, dict)]
    ctx = {
        'exogenous': exogenous,
        'hp_events': hp_events if has_hp_events_col else [],
        'has_hp_events_col': has_hp_events_col,
        'hp_pay_defects': defects if has_defects_col else [],
        'has_defects_col': has_defects_col,
        'recon_rows': recon_rows,
        'loss_nodes': _group_by_round(archive.get('loss_nodes')
                                      if isinstance(archive.get('loss_nodes'),
                                                    list) else []),
        'spend_by_round': _group_by_round(spend),
        'conflicts_by_round': conflicts_by_round,
    }
    if archive.get('loss_nodes') is None:
        gaps.miss('loss_nodes')

    parts = _render_header(archive, seg_ids, run_filter, gaps)
    parts += ['## 2. 逐轮复盘', '']
    for i, r in enumerate(rounds_all, 1):
        parts += _render_round(i, r, ctx, gaps)
    if not rounds_all:
        parts += ['(档案无逐轮数据:rounds 为空/缺失——零决策帧或装配失败,'
                  '判读先查装配。)', '']
    parts += _unattributed_conflicts(ctx)
    parts += _render_global(archive, rounds_all, gaps)
    parts += ['---', '']
    parts += ['## 4. 本次未能渲染的字段(遥测缺口清单)', '']
    parts += gaps.summary_lines()
    parts += ['', '_(缺口 = 该字段本次数据没采到或档案版本旧,不是渲染器'
              '故障;出现的路径即遥测缺口清单。)_', '']
    return '\n'.join(parts) + '\n'


def main(argv: list[str] | None = None) -> int:
    """CLI 入口;返回进程退出码(0=成功,2=档案缺/坏)。"""
    ap = argparse.ArgumentParser(
        description='货币战争对局档案 → markdown 深度复盘渲染器')
    ap.add_argument('--match', required=True, help='game_id(档案名 match_<id>.json)')
    ap.add_argument('--run', default=None, help='只渲染某段 run_id 的流明细')
    ap.add_argument('--out', default=None, help='输出 markdown 文件(缺省 stdout)')
    ap.add_argument('--replay-dir', default=str(DEFAULT_REPLAY_DIR),
                    help='replay 目录(缺省 .debug/temp/currency_war/replay)')
    args = ap.parse_args(argv)

    replay_dir = Path(args.replay_dir)
    archive_path = replay_dir / 'matches' / f'match_{args.match}.json'
    if not archive_path.exists():
        print(f'(档案不存在: {archive_path}——先装配:'
              f' uv run python -m sr_od.application.currency_war.telemetry.cli'
              f' assemble --game {args.match})', file=sys.stderr)
        return 2
    try:
        archive = json.loads(archive_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        print(f'(档案不可读: {archive_path}: {e})', file=sys.stderr)
        return 2
    md = render_match(archive, replay_dir, run_filter=args.run)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding='utf-8')
        print(f'(已写出: {out} 共 {len(md.splitlines())} 行)', file=sys.stderr)
    else:
        sys.stdout.write(md)
    return 0


if __name__ == '__main__':
    sys.exit(main())
