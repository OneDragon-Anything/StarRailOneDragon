"""sim 局产物对照脚本(出战域原子化重整 T-1 交付,3.5 同 seed 复跑复用)。

对照载体 = 本迭代 landing 3.1 对照协议四针第 3 条的操作定义:
- **画面广播序列**:`state/journal.jsonl` 中 `field` 为 `prev_screen` /
  `current_screen` 的写行,按行序取 `(field, after)` 值对摊平成序列——
  ts / run_id / v 号等元字段不进序列(行序即序,两行一对的播报语义
  保持为序列相邻项);prev/current 交替节律破坏不阻断比对(仍按摊平
  序列逐位比),但会附结构警告行供判读;
- **终局摘要**:`matches/match_<game_id>.json` 的 `endgame` 对象整取
  (嵌套同处理),外加 `schema_version` / `strategy_version` 两个稳定
  头字段;元字段(``_META_KEYS``:时间类 + run_id)任意深度剔除,`game_id`
  内嵌
  运行时刻戳、两跑天然不同,不进比对。

用法(任意工作目录;纯标准库,零 src 导入):

    uv run python compare_sim.py <局产物目录A> <局产物目录B>

退出码:0 = 恒等(打印两局载体摘要);1 = 有分歧(打印首个分歧点与
两则值);2 = 结构性错误(目录/产物文件缺失、match 档案不唯一)。
摘要 = 两载体各自 JSON 规范形(SHA-256 前 16 位)——3.5 复跑后先对
摘要,摘要相同即恒等,免逐行读输出。
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

#: 任意深度剔除的元字段:时间类(墙钟时刻)+ 运行标识(run_id),两跑天然
#: 不同,进比对必假阳性——协议原文「剔除 ts/run_id 等元字段」。
_META_KEYS: frozenset[str] = frozenset(
    {'ts', 'start_ts', 'end_ts', 'archived_at', 'archived_through', 'run_id'})

#: 画面广播行 field 白名单(协议载体;journal 其余 field 一律不入序列)
_SCREEN_FIELDS: frozenset[str] = frozenset({'prev_screen', 'current_screen'})


def _fail(msg: str) -> NoReturn:
    """结构性错误统一出口(退出码 2)。"""
    print(f'[compare-sim] 结构错误: {msg}')
    raise SystemExit(2)


def _strip_ts(obj: Any) -> Any:
    """递归剔除元字段(键命中 ``_META_KEYS`` 的条目整体移除)。"""
    if isinstance(obj, dict):
        return {k: _strip_ts(v) for k, v in obj.items() if k not in _META_KEYS}
    if isinstance(obj, list):
        return [_strip_ts(v) for v in obj]
    return obj


def extract_screen_sequence(batch_dir: Path) -> list[tuple[str, str]]:
    """提取画面广播序列(journal 写行 ``(field, after)`` 摊平,保行序)。"""
    journal = batch_dir / 'state' / 'journal.jsonl'
    if not journal.is_file():
        _fail(f'journal 缺失: {journal}')
    seq: list[tuple[str, str]] = []
    with journal.open(encoding='utf-8') as fh:
        for line in fh:
            row = json.loads(line)
            if row.get('row') != 'write':
                continue
            field = row.get('field')
            if field in _SCREEN_FIELDS:
                seq.append((field, row.get('after') or ''))
    return seq


def extract_terminal(batch_dir: Path) -> dict[str, Any]:
    """提取终局摘要(match 档案 endgame 对象 + 两个稳定头字段)。"""
    matches_dir = batch_dir / 'matches'
    if not matches_dir.is_dir():
        _fail(f'matches 目录缺失: {matches_dir}')
    archives = sorted(matches_dir.glob('match_*.json'))
    if len(archives) != 1:
        _fail(f'match 档案不唯一({len(archives)} 个): {matches_dir}')
    with archives[0].open(encoding='utf-8') as fh:
        data = json.load(fh)
    out: dict[str, Any] = {
        'schema_version': data.get('schema_version'),
        'strategy_version': data.get('strategy_version'),
        'endgame': _strip_ts(data.get('endgame')),
    }
    return out


def _digest(obj: Any) -> str:
    """载体 JSON 规范形摘要(SHA-256 前 16 位;比对面的紧凑指纹)。"""
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


def _first_dict_diff(a: Any, b: Any, path: str = '',
                     ) -> tuple[str, Any, Any] | None:
    """两规范化值的首个分歧(深度优先,键序一致;返回 (路径, A值, B值))。"""
    if type(a) is not type(b):
        return (path or '<root>', a, b)
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return (f'{path}.{k}' if path else k,
                        a.get(k, '<缺>'), b.get(k, '<缺>'))
            found = _first_dict_diff(a[k], b[k], f'{path}.{k}' if path else k)
            if found is not None:
                return found
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return (f'{path}[len]', len(a), len(b))
        for i, (av, bv) in enumerate(zip(a, b, strict=False)):
            found = _first_dict_diff(av, bv, f'{path}[{i}]')
            if found is not None:
                return found
        return None
    return None if a == b else (path or '<root>', a, b)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('用法: uv run python compare_sim.py <局产物目录A> <局产物目录B>')
        return 2
    dir_a, dir_b = Path(argv[0]), Path(argv[1])
    for d in (dir_a, dir_b):
        if not d.is_dir():
            _fail(f'产物目录不存在: {d}')

    seq_a = extract_screen_sequence(dir_a)
    seq_b = extract_screen_sequence(dir_b)
    term_a = extract_terminal(dir_a)
    term_b = extract_terminal(dir_b)

    digest_a = _digest(seq_a)
    digest_b = _digest(seq_b)
    term_digest_a = _digest(term_a)
    term_digest_b = _digest(term_b)

    print(f'[compare-sim] A = {dir_a}')
    print(f'[compare-sim] B = {dir_b}')
    print(f'[compare-sim] A 画面广播 {len(seq_a)} 行 digest={digest_a} | '
          f'终局 digest={term_digest_a}')
    print(f'[compare-sim] B 画面广播 {len(seq_b)} 行 digest={digest_b} | '
          f'终局 digest={term_digest_b}')

    exit_code = 0
    if seq_a != seq_b:
        exit_code = 1
        n = min(len(seq_a), len(seq_b))
        idx = next((i for i in range(n) if seq_a[i] != seq_b[i]), n)
        print(f'[compare-sim] ✗ 画面广播序列首个分歧 @ 行序 {idx} '
              f'(A {len(seq_a)} 行 / B {len(seq_b)} 行):')
        for j in range(max(0, idx - 2), min(max(len(seq_a), len(seq_b)),
                                            idx + 3)):
            va = seq_a[j] if j < len(seq_a) else '<越界>'
            vb = seq_b[j] if j < len(seq_b) else '<越界>'
            mark = '  ' if va == vb else '>>'
            print(f'  {mark} [{j}] A={va} | B={vb}')
    else:
        print('[compare-sim] ✓ 画面广播序列恒等')
    # prev/current 交替节律检查(播报语义 = 两行一对;破坏附警告不阻断)
    for tag, seq in (('A', seq_a), ('B', seq_b)):
        expect_prev = True
        for i, (field, _v) in enumerate(seq):
            want = 'prev_screen' if expect_prev else 'current_screen'
            if field != want:
                print(f'[compare-sim] ⚠ {tag} 行序 {i} 破坏 prev/current '
                      f'交替节律(实为 {field})——播报对不完整,判读注意')
                break
            expect_prev = not expect_prev

    if term_a != term_b:
        exit_code = 1
        diff = _first_dict_diff(term_a, term_b)
        path, va, vb = diff if diff else ('<unknown>', None, None)
        print(f'[compare-sim] ✗ 终局摘要首个分歧 @ {path}: A={va!r} | B={vb!r}')
    else:
        print('[compare-sim] ✓ 终局摘要恒等')

    if exit_code == 0:
        print('[compare-sim] 结论: 恒等(退出码 0)')
    else:
        print('[compare-sim] 结论: 有分歧(退出码 1;仅列首个分歧点)')
    return exit_code


if __name__ == '__main__':
    # GBK 控制台容错:画面名/分歧值为中文,stdout 切 UTF-8(老解释器无此 API 则维持原样)
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
