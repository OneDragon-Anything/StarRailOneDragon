"""开局投资选卡遥测行 run 归属重算(ADR-0588;S12 历史档案治理)。

## 背景

run_id 曾在 ``CwLoop.__init__`` 才铸造,而入口链(简报/投资环境/投资策略屏)
的遥测行早于铸造产生:``record_invest_cards`` 的「run_id 空则丢,否则盖
``_CURRENT_RUN_ID``」门把开局 env/strategy 行盖到**上一局** run 戳上(冷启动
首局则零行)。治本修复 = 铸造前移到入口链(ADR-0588,ensure_run_started);
本工具治历史:按 runs.jsonl 收口时间线把 invest_cards.jsonl 逐行重归属
「首个收口时刻 ≥ 行 ts 的 run」,再对受影响档案重建。

## 重算判定规则(ADR-0588 方案 §2.2;判据与检出互逆)

runs.jsonl 每行 ts = 收口时刻;run 生存期 = (上一收口, 本收口](单跑道一次
一 run,顺序无交叠)。对 invest_cards.jsonl 每行 R(ts=t)::

    owner = 收口时刻 ≥ t 的最早收口行
    无 owner(t 晚于最后一收口,活局尾部)→ 保持原 run_id(申报,靠重跑自愈)
    owner == R.run_id                    → 不改(窗内合法行:局中 0s 选卡 + 已正确行)
    否则                                 → R.run_id ← owner.run_id(污染行重归属)

**疑似串门-人工审(先于自动重归属;保持原 run_id,只点名)**——所盖 run S
的收口状态存在两种失真形态,任一命中即入人工审清单:

1. S 收口行 ``source='recovered'``(ADR-0273 兜底回填:ts=回填时刻而非真实
   终局时刻)且 R.ts 早于 S 自身流行(名下各流 + 收口行)的最晚 ts——回填
   时刻是名义窗尾而非真实窗尾,owner 规则对 S 名下的行失真。实践中即 S
   名义窗内全部行(超集保守,清单不改数据)。
2. S 无收口行(硬崩且未被回填):归属时间线缺锚,owner 规则会把其名下行
   自动改判给下一收口(可能隔了一个丢失局)——S 名下全部行不自动改。

## 安全三件

① 首次 ``--apply`` 前 ``invest_cards.jsonl`` → ``invest_cards.jsonl.bak-<yyyymmdd>``
(已存在则拒绝覆盖 = 真原始流保底);② 变更 journal 落
``.debug/temp/currency_war/t109_telemetry_gaps/repair_journal-<ts>.json``;
③ 整文件重写走 tempfile + ``os.replace`` 原子替换,只改 run_id 字段,行序与
其余字段逐字节保留(重序列化与写端 ``append_jsonl`` 同参数,恒等自检见
dry-run 报告)。

**执行前置:无 run 在跑**(单写者;本脚本不并行于 bot)。建议先 ``--replay-dir``
指向整个 live 流根的拷贝演练 dry-run + --apply,再对真库执行。

## 用法(项目根,PYTHONPATH=src)

    uv run python tools/cw/repair_invest_attribution.py             # dry-run(默认)
    uv run python tools/cw/repair_invest_attribution.py --apply     # 落盘
    uv run python tools/cw/repair_invest_attribution.py --replay-dir <副本目录>

幂等:重归属后每行满足 owner == stamped,重跑 = 零改动;备份只建一次。
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from one_dragon.utils.file_utils import get_project_root
from sr_od.application.currency_war.kernel.cw_observe import DEFAULT_REPLAY_DIR
from sr_od.application.currency_war.telemetry.match_archive import (
    assemble_game,
    matches_dir,
)
from sr_od.application.currency_war.telemetry.query import read_jsonl

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

_REPO = get_project_root()

#: 变更 journal 落点(ADR-0588 方案 §2.1 安全三件②;批报告目录,不入 git)
_JOURNAL_DIR = (_REPO / '.debug' / 'temp' / 'currency_war'
                / 't109_telemetry_gaps')

#: 入「所盖 run 自身流行最晚 ts」扫描的流(op_journal 行也带 run_id,一并入扫;
#: 与 match_archive 切片流同面 + runs 收口行)
_STREAM_FILES: tuple[str, ...] = (
    'decisions.jsonl', 'outcomes.jsonl', 'shop_snapshots.jsonl',
    'exogenous.jsonl', 'invest_cards.jsonl', 'spend_ledger.jsonl',
    'op_journal.jsonl',
)

#: 兜底回填行的来源标记(ADR-0273;ledger_hooks.build_recovered_summary)
_RECOVERED_SOURCE: str = 'recovered'


@dataclass
class _CloseRow:
    """runs.jsonl 一行收口锚(ts=收口时刻;idx=文件行序,并列 tie-break 用)。"""
    ts: str
    run_id: str
    source: str
    idx: int


@dataclass
class _RowVerdict:
    """单行判定结果(计划/journal 的最小单元)。"""
    line_no: int          # invest_cards.jsonl 内 1 基行号(原始行序坐标系)
    ts: str
    kind: str
    old_run_id: str
    new_run_id: str       # 等于 old = 不改
    action: str           # reattribute/keep_window/keep_live_tail/manual_review/bad_row
    reason: str


@dataclass
class _RepairPlan:
    """全库重算计划(判定纯函数的产物;dry-run 打印、--apply 消费)。"""
    verdicts: list[_RowVerdict] = field(default_factory=list)
    #: 恒等自检失败的 1 基行号(重序列化 ≠ 原行 = 非本仓写端产物,拒绝 --apply)
    roundtrip_mismatch: list[int] = field(default_factory=list)
    #: 人工审清单元素:(行号, ts, kind, stamped_run, 原因)
    manual_review: list[tuple[int, str, str, str, str]] = field(default_factory=list)


def _load_closes(runs_rows: list[dict[str, Any]]) -> list[_CloseRow]:
    """runs.jsonl → 收口锚列表(保留文件行序;「最早」在消费侧按 (ts, idx) 取)。"""
    closes: list[_CloseRow] = []
    for i, r in enumerate(runs_rows):
        rid = str(r.get('run_id') or '')
        if not rid:
            continue
        closes.append(_CloseRow(ts=str(r.get('ts') or ''), run_id=rid,
                                source=str(r.get('source') or ''), idx=i))
    return closes


def _find_owner(closes: list[_CloseRow], row_ts: str) -> _CloseRow | None:
    """「收口时刻 ≥ 行 ts」的最早收口行(无 → None = 活局尾部)。

    ISO 秒级字符串字典序 = 时间序;并列按文件行序取先(min 的稳定 tie-break)。
    """
    candidates = [c for c in closes if c.ts and c.ts >= row_ts]
    if not candidates:
        return None
    return min(candidates, key=lambda c: (c.ts, c.idx))


def _latest_ts_by_run(replay_dir: Path) -> dict[str, str]:
    """每个 run_id 名下各流行 + 收口行的最晚 ts(人工审形态①的判据输入)。

    不假设行 ts 单调(回填/补写行 ts 可能滞后于真实终局),逐行取 max。
    """
    latest: dict[str, str] = {}
    for name in (*_STREAM_FILES, 'runs.jsonl'):
        for r in read_jsonl(replay_dir / name):
            rid = str(r.get('run_id') or '')
            ts = str(r.get('ts') or '')
            if not rid or not ts:
                continue
            if rid not in latest or ts > latest[rid]:
                latest[rid] = ts
    return latest


def _close_status_by_run(closes: list[_CloseRow]) -> dict[str, list[_CloseRow]]:
    """run_id → 其全部收口行(判「有收口/收口来源」;同名多行全保留)。"""
    out: dict[str, list[_CloseRow]] = {}
    for c in closes:
        out.setdefault(c.run_id, []).append(c)
    return out


def plan_repair(invest_rows: list[dict[str, Any]],
                closes: list[_CloseRow],
                latest_ts: dict[str, str]) -> _RepairPlan:
    """重算判定纯函数(行集 × 收口时间线 → 计划;同输入同输出,幂等根基)。"""
    plan = _RepairPlan()
    close_status = _close_status_by_run(closes)
    for line_no, row in enumerate(invest_rows, start=1):
        ts = str(row.get('ts') or '')
        kind = str(row.get('kind') or '')
        stamped = str(row.get('run_id') or '')
        if not ts or not stamped:
            plan.verdicts.append(_RowVerdict(
                line_no=line_no, ts=ts, kind=kind, old_run_id=stamped,
                new_run_id=stamped, action='bad_row',
                reason='行缺 ts/run_id,无法判定,保持原样交人工'))
            plan.manual_review.append(
                (line_no, ts, kind, stamped, '行缺 ts/run_id'))
            continue
        # 人工审先行(方案 §2.2:先于自动重归属;命中不改数据只点名)
        s_closes = close_status.get(stamped, [])
        if not s_closes:
            plan.verdicts.append(_RowVerdict(
                line_no=line_no, ts=ts, kind=kind, old_run_id=stamped,
                new_run_id=stamped, action='manual_review',
                reason=f'所盖 run {stamped} 无收口行(硬崩未回填),归属时间线缺锚'))
            plan.manual_review.append(
                (line_no, ts, kind, stamped, '所盖 run 无收口行'))
            continue
        s_latest = max([latest_ts.get(stamped, '')] + [c.ts for c in s_closes])
        if any(c.source == _RECOVERED_SOURCE for c in s_closes) and ts < s_latest:
            plan.verdicts.append(_RowVerdict(
                line_no=line_no, ts=ts, kind=kind, old_run_id=stamped,
                new_run_id=stamped, action='manual_review',
                reason=(f'所盖 run {stamped} 收口为 recovered 回填'
                        f'(回填 ts={s_latest} 是名义窗尾),行 ts={ts} 早于它')))
            plan.manual_review.append(
                (line_no, ts, kind, stamped, '所盖 run 收口为 recovered 回填'))
            continue
        owner = _find_owner(closes, ts)
        if owner is None:
            plan.verdicts.append(_RowVerdict(
                line_no=line_no, ts=ts, kind=kind, old_run_id=stamped,
                new_run_id=stamped, action='keep_live_tail',
                reason=f'行 ts={ts} 晚于最后一收口(活局尾部),保持原样(重跑自愈)'))
            continue
        if owner.run_id == stamped:
            plan.verdicts.append(_RowVerdict(
                line_no=line_no, ts=ts, kind=kind, old_run_id=stamped,
                new_run_id=stamped, action='keep_window',
                reason=f'窗内合法行(owner={owner.run_id} 收口 {owner.ts})'))
            continue
        plan.verdicts.append(_RowVerdict(
            line_no=line_no, ts=ts, kind=kind, old_run_id=stamped,
            new_run_id=owner.run_id, action='reattribute',
            reason=f'首个 close≥ts: {owner.run_id}(收口 {owner.ts})'))
    return plan


def _canonical(row: dict[str, Any]) -> str:
    """行的规范序列化(与写端 ``append_jsonl`` 同参数:ensure_ascii=False +
    默认分隔符)。json.loads 保键序,重序列化与原行逐字节恒等——这是
    「只动 run_id、其余逐字节保留」的实现前提,dry-run 有恒等自检兜底。"""
    return json.dumps(row, ensure_ascii=False)


def _read_raw_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """读原始行文本 + 解析行(1:1 对齐;空行跳过且不占行号)。"""
    raw: list[str] = []
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return raw, rows
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            s = line.rstrip('\n')
            if not s.strip():
                continue
            raw.append(s)
            rows.append(json.loads(s))
    return raw, rows


def _atomic_rewrite(path: Path, lines: list[str]) -> None:
    """整文件原子重写(tempfile + os.replace;同 match_archive._atomic_write_json 模式)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                               prefix=path.name + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            for ln in lines:
                f.write(ln + '\n')
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _rows_after_plan(rows: list[dict[str, Any]],
                     plan: _RepairPlan) -> list[dict[str, Any]]:
    """计划投影到行集(reattribute 行换 run_id;其余原样)——档案影响面/V3/V6
    对账一律吃投影态,不吃原态(否则 dry-run 永远报「零影响」失真)。"""
    by_line = {v.line_no: v for v in plan.verdicts}
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        v = by_line.get(i)
        if v is not None and v.action == 'reattribute':
            out.append({**row, 'run_id': v.new_run_id})
        else:
            out.append(row)
    return out


def _check_roundtrip(raw: list[str], rows: list[dict[str, Any]],
                     plan: _RepairPlan) -> None:
    """恒等自检:重序列化必须逐字节复现原行(换戳位除外)。不满足 = 行不是
    本仓写端产物(手工编辑/异构工具),盲重写会破坏字节保真承诺。"""
    by_line = {v.line_no: v for v in plan.verdicts}
    for i, (ln_text, row) in enumerate(zip(raw, rows, strict=True), start=1):
        v = by_line.get(i)
        if v is None:
            continue
        probe = {**row, 'run_id': v.new_run_id}
        if v.action == 'keep_window' and _canonical(probe) != ln_text:
            plan.roundtrip_mismatch.append(i)
        if v.action == 'reattribute' and _canonical(probe) == ln_text:
            # 换戳后与原行相同 = 判定与数据矛盾(owner≠stamped 才会到这),防御
            plan.roundtrip_mismatch.append(i)


def _load_archive(path: Path) -> dict[str, Any] | None:
    """读单档案 JSON(损坏/缺档 → None,调用方跳过;半截档案概率极低——原子写)。"""
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _affected_archives(replay_dir: Path,
                       new_rows: list[dict[str, Any]]) -> list[str]:
    """受影响档案清单:档案内存量 invest 切片 ≠ 按投影态重算切片 → 入列。

    既涵盖「被抽走行」的污染档案,也涵盖「补进行」的真主档案。"""
    md = matches_dir(replay_dir)
    affected: list[str] = []
    for p in sorted(md.glob('match_*.json')):
        archive = _load_archive(p)
        if archive is None:
            continue
        segs = {s.get('run_id') for s in (archive.get('segments') or [])}
        projected = [r for r in new_rows if r.get('run_id') in segs]
        existing = (archive.get('slices') or {}).get('invest_cards.jsonl') or []
        if _canonical(existing) != _canonical(projected):
            affected.append(str(archive.get('game_id') or p.stem))
    return affected


def _chosen_names(rows: list[dict[str, Any]], kind: str) -> list[str]:
    """opening.chosen_env/chosen_strategies 同口径提取(非空 name;match_archive._build_opening)。"""
    return [str(r.get('name')) for r in rows
            if r.get('kind') == kind and r.get('chosen') and r.get('name')]


def _v3_cross_check(replay_dir: Path,
                    new_rows: list[dict[str, Any]]) -> tuple[list[str], int]:
    """V3 跨源真值对拍(投影态):非空 chosen_env == segments 内最早带非空
    ``state.active_env`` 的 decisions 行值(开局选卡先于 p1r1 首帧,最早帧即
    开局真值;位面过渡改选只会动更晚帧,故只对最早帧);chosen_strategies
    同法对拍首个非空 ``trace.active_strategies``(集合等价)。mismatch 暴露
    为真交人工裁决,预期来源两类:OCR fallback 类 + 前局硬崩串门形态。

    真值源 = **档案内嵌 decisions 切片**(落地审 F2):原始 decisions 流有
    轮转,活行只剩窗口尾部,读原始流会让对拍空转(checked=0 假阴);切片
    随档案自包含且 decisions 行不被本工具改写,是稳定真值源。

    对拍口径:env 轴 = 首个 chosen_env == 最早 active_env;strategy 轴 =
    首个 chosen_strategies ∈ 最早 active_strategies 集合——位面过渡改选
    会让 chosen 序列合法累积多值(cw_loop 0e/0s 局中分支),真值锚只取最早
    帧,故只对拍「开局那次选择」。返回 (mismatch 行, env 轴对拍数, strategy
    轴对拍数)。
    """
    md = matches_dir(replay_dir)
    lines: list[str] = []
    checked_env = 0
    checked_strat = 0
    for p in sorted(md.glob('match_*.json')):
        archive = _load_archive(p)
        if archive is None:
            continue
        segs = {s.get('run_id') for s in (archive.get('segments') or [])}
        invest = [r for r in new_rows if r.get('run_id') in segs]
        dec = sorted(
            (r for r in (archive.get('slices') or {}).get('decisions.jsonl')
             or [] if r.get('run_id') in segs),
            key=lambda r: str(r.get('ts') or ''))
        env_truth = next((str((r.get('state') or {}).get('active_env') or '')
                          for r in dec
                          if str((r.get('state') or {}).get('active_env') or '')),
                         '')
        strat_truth: set[str] = set()
        for r in dec:
            as_ = r.get('active_strategies') or []
            if as_:
                strat_truth = {str(x) for x in as_}
                break
        gid = str(archive.get('game_id') or p.stem)
        chosen_env = _chosen_names(invest, 'env')
        chosen_strats = _chosen_names(invest, 'strategy')
        if chosen_env and env_truth:
            checked_env += 1
            if chosen_env[0] != env_truth:
                lines.append(f'  [V3-env] {gid}: 开局 chosen_env={chosen_env[0]!r} != '
                             f'最早 active_env={env_truth!r}(全序列 {chosen_env!r})')
        if chosen_strats and strat_truth:
            checked_strat += 1
            if chosen_strats[0] not in strat_truth:
                lines.append(f'  [V3-strat] {gid}: 开局 chosen_strategies={chosen_strats[0]!r} '
                             f'∉ 最早 active_strategies={sorted(strat_truth)!r}'
                             f'(全序列 {chosen_strats!r})')
    return lines, checked_env, checked_strat


def _v6_reconciliation(replay_dir: Path,
                       new_rows: list[dict[str, Any]],
                       manual_runs: set[str]) -> dict[str, Any]:
    """V6 前后计数对账表(验收的诚实性门槛)。剩余空 chosen_env 档案按可计算
    信号归因:① 恢复局合法空(首段首帧非 (p1,r1),入口无选卡屏);④ 前局
    硬崩串门嫌疑(其名下行源自人工审清单 run);其余归 ②冷启动零行不可修复
    ∨ ③真无选卡屏(两者离线不可分,留人工判读,不静默混进「已修复」)。"""
    md = matches_dir(replay_dir)
    total = 0
    changed_env = 0
    changed_strat = 0
    nonempty_env_after = 0
    empty_restore_like: list[str] = []
    empty_manual_review: list[str] = []
    empty_other: list[str] = []
    for p in sorted(md.glob('match_*.json')):
        archive = _load_archive(p)
        if archive is None:
            continue
        total += 1
        segs = {s.get('run_id') for s in (archive.get('segments') or [])}
        projected = [r for r in new_rows if r.get('run_id') in segs]
        existing = (archive.get('slices') or {}).get('invest_cards.jsonl') or []
        if _chosen_names(existing, 'env') != _chosen_names(projected, 'env'):
            changed_env += 1
        if (_chosen_names(existing, 'strategy')
                != _chosen_names(projected, 'strategy')):
            changed_strat += 1
        if _chosen_names(projected, 'env'):
            nonempty_env_after += 1
            continue
        gid = str(archive.get('game_id') or p.stem)
        segs_info = archive.get('segments') or []
        first_fk = (segs_info[0] or {}).get('first_frame') if segs_info else None
        stamped_runs = {str(r.get('run_id') or '') for r in existing}
        # JSON 反序列化的 first_frame 是 list,与 tuple (1,1) 直接比较恒不等
        # (落地审 F1:恒真 bug 曾把全部空档案误归①)——先 list 归一再比。
        if first_fk is not None and list(first_fk) != [1, 1]:
            empty_restore_like.append(gid)
        elif stamped_runs & manual_runs:
            empty_manual_review.append(gid)
        else:
            empty_other.append(gid)
    return {
        '总档案数': total,
        'chosen_env 变化档案数': changed_env,
        'chosen_strategies 变化档案数': changed_strat,
        '修后非空 chosen_env 档案数': nonempty_env_after,
        '剩余空 chosen_env 档案数': (len(empty_restore_like)
                                     + len(empty_manual_review)
                                     + len(empty_other)),
        '  ①恢复局合法空(首段非(p1,r1))': empty_restore_like,
        '  ④前局硬崩串门嫌疑(行入人工审)': empty_manual_review,
        '  ②冷启动零行∨③真无选卡屏(离线不可分,人工判读)': empty_other,
    }


def _print_plan(replay_dir: Path, plan: _RepairPlan,
                new_rows: list[dict[str, Any]], apply_mode: bool) -> None:
    """dry-run/apply 共用报告:计划行 + 分类计数 + 档案清单 + V2/V3/V6 对账。"""
    verb = '将重写' if apply_mode else 'dry-run(零落盘)'
    print(f'== invest 归属重算计划({verb}) ==')
    print(f'live 流根: {replay_dir}')
    v_re = [v for v in plan.verdicts if v.action == 'reattribute']
    v_keep = [v for v in plan.verdicts if v.action == 'keep_window']
    v_tail = [v for v in plan.verdicts if v.action == 'keep_live_tail']
    v_bad = [v for v in plan.verdicts if v.action == 'bad_row']
    print(f'行数: {len(plan.verdicts)}(V1:重写前后行数与分 kind 计数不变,只换 run_id)')
    print(f'重归属行: {len(v_re)}'
          f'(env={sum(1 for v in v_re if v.kind == "env")}'
          f' / strategy={sum(1 for v in v_re if v.kind == "strategy")})')
    print(f'窗内合法行(不改): {len(v_keep)};活局尾部(不改): {len(v_tail)};'
          f'异常行: {len(v_bad)}')
    for v in v_re:
        print(f'  L{v.line_no} [{v.kind}] ts={v.ts} '
              f'{v.old_run_id} -> {v.new_run_id}  # {v.reason}')
    if plan.roundtrip_mismatch:
        print(f'!! 恒等自检失败行号(重序列化 ≠ 原行,禁止 --apply,先人工排查): '
              f'{plan.roundtrip_mismatch}')
    if plan.manual_review:
        print(f'疑似串门-人工审({len(plan.manual_review)} 行,不自动改):')
        for line_no, ts, kind, stamped, why in plan.manual_review:
            print(f'  L{line_no} [{kind}] ts={ts} stamped={stamped}  # {why}')
    else:
        print('疑似串门-人工审: 0 行')
    affected = _affected_archives(replay_dir, new_rows)
    print(f'受影响档案(重建清单,{len(affected)} 个): '
          f'{", ".join(affected) if affected else "(无)"}')
    if plan.roundtrip_mismatch:
        return   # 自检不过不做投影对账(投影基于失真序列会误导)
    print('== V2 污染签名(行 ts > 所盖 run 收口;判定域=有正常收口归属的行,'
          '活局尾部与人工审行天然除外) ==')
    print(f'  本次重归属(=签名命中) {len(v_re)} 行 → apply 后归零')
    print('== V3 跨源真值对拍(投影态;真值源=档案内嵌 decisions 切片;'
          'mismatch 暴露为真,交人工裁决) ==')
    v3_lines, v3_env_n, v3_strat_n = _v3_cross_check(replay_dir, new_rows)
    print(f'  对拍执行: env={v3_env_n} 处 / strategy={v3_strat_n} 处'
          '(只对拍开局选择;位面过渡改选合法累积不计)')
    print('\n'.join(v3_lines) if v3_lines else '  mismatch: 0 条')
    v6 = _v6_reconciliation(
        replay_dir, new_rows,
        {stamped for (_, _, _, stamped, _) in plan.manual_review})
    print('== V6 前后计数对账表 ==')
    for k, val in v6.items():
        if isinstance(val, list):
            print(f'  {k}: {len(val)}{(" " + ", ".join(val)) if val else ""}')
        else:
            print(f'  {k}: {val}')


def _run(replay_dir: Path, apply_mode: bool) -> int:
    """主流程:读 → 判定 → 报告(dry-run)/ 备份+重写+重建+journal(apply)。"""
    invest_path = replay_dir / 'invest_cards.jsonl'
    raw, rows = _read_raw_rows(invest_path)
    closes = _load_closes(read_jsonl(replay_dir / 'runs.jsonl'))
    latest_ts = _latest_ts_by_run(replay_dir)
    plan = plan_repair(rows, closes, latest_ts)
    _check_roundtrip(raw, rows, plan)
    new_rows = _rows_after_plan(rows, plan)
    if not apply_mode:
        _print_plan(replay_dir, plan, new_rows, apply_mode=False)
        return 0
    if plan.roundtrip_mismatch:
        print('恒等自检失败,--apply 拒绝执行(见上方行号清单)。')
        return 2
    to_apply = [v for v in plan.verdicts if v.action == 'reattribute']
    if not to_apply:
        print('0 行待改,0 档案待重建(--apply 幂等 no-op)。')
        return 0
    bak = invest_path.with_name(
        invest_path.name + '.bak-' + datetime.now().strftime('%Y%m%d'))
    if bak.exists():
        print(f'备份 {bak.name} 已存在,拒绝覆盖(真原始流保底);'
              f'如确需重跑,先人工处置备份文件。')
        return 2
    shutil.copy2(invest_path, bak)
    # 只换 run_id:重序列化与写端同参数,恒等自检已过 → 除戳位外逐字节保留
    by_line = {v.line_no: v for v in plan.verdicts}
    new_lines: list[str] = []
    for i, (ln_text, row) in enumerate(zip(raw, rows, strict=True), start=1):
        v = by_line.get(i)
        new_lines.append(_canonical({**row, 'run_id': v.new_run_id})
                         if v is not None and v.action == 'reattribute'
                         else ln_text)
    _atomic_rewrite(invest_path, new_lines)
    affected = _affected_archives(replay_dir, new_rows)
    rebuilt: list[str] = []
    for gid in affected:
        archive = assemble_game(replay_dir, gid)
        if archive is not None:
            rebuilt.append(gid)
    _JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    journal_path = _JOURNAL_DIR / (
        'repair_journal-' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
    journal = {
        'tool': 'tools/cw/repair_invest_attribution.py',
        'adr': 'ADR-0588',
        'replay_dir': str(replay_dir),
        'backup': str(bak),
        'changed_rows': [
            {'line_no': v.line_no, 'ts': v.ts, 'kind': v.kind,
             'old_run_id': v.old_run_id, 'new_run_id': v.new_run_id,
             'reason': v.reason} for v in to_apply],
        'manual_review': [
            {'line_no': ln, 'ts': ts, 'kind': kind, 'stamped_run': rid,
             'reason': why} for ln, ts, kind, rid, why in plan.manual_review],
        'rebuilt_archives': rebuilt,
    }
    with journal_path.open('w', encoding='utf-8') as f:
        json.dump(journal, f, ensure_ascii=False, indent=2)
    print(f'--apply 完成:重归属 {len(to_apply)} 行(备份 {bak.name});'
          f'重建档案 {len(rebuilt)} 个;journal={journal_path.name}')
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI 入口(dry-run 默认;--apply 显式落盘)。"""
    ap = argparse.ArgumentParser(
        description='开局投资选卡遥测行 run 归属重算(ADR-0588;默认 dry-run)')
    ap.add_argument('--replay-dir', default=str(DEFAULT_REPLAY_DIR),
                    help='live 流根(默认生产新树 telemetry/live;演练传副本目录)')
    ap.add_argument('--apply', action='store_true',
                    help='落盘(默认 dry-run 只打印;备份+journal 见模块 docstring)')
    args = ap.parse_args(argv)
    apply_mode: bool = bool(args.apply)
    rd = Path(str(args.replay_dir))
    if not rd.exists():
        print(f'live 流根不存在: {rd}')
        return 1
    if apply_mode:
        print('提示:执行前置 = 无 run 在跑(单写者;脚本不并行于 bot)。')
    return _run(rd, apply_mode)


if __name__ == '__main__':
    sys.exit(main())
