"""CW 遥测树一次性迁移工具(旧根 → 新根;重跑 = 有前提的补迁,非无条件幂等)。

2026-09-07 布局裁定(用户,T-125):遥测固定落点
``.debug/currency_war/telemetry/{live,matches,sim}``,深评报告固定落点
``.debug/currency_war/deep_review/``;旧根 ``.debug/temp/currency_war/replay``
(与 ``sim_runs``)退役。本工具把旧根存量搬进新树,搬完在旧根留
LEGACY 声明文件(旧路径此后无任何活跃写点——写端常量已全部改指新树)。

## 重跑语义与已知失效形态(诚实申报;曾申报「幂等可重跑」已被实证证伪)

流文件(decisions/outcomes 等追加型 jsonl)的重跑合并走记账协议:
manifest 记「当前 src 化身已消费到的字节偏移」;血缘判定按**内容锚**——
src 前缀与 dst 尾部同窗字节哈希一致 = 同一化身,接尾;不一致 =
move/unlink 后被旧代码进程重建的新化身,整份并入(2026-09-08 最近改动
三审 M2 治本:旧实现按 size 与 offset 的大小猜血缘——恰比旧 offset 长
的新化身被当「接尾」截头、恰等长被当残躯删除、比旧 offset 短的则被
防线②越界恒拒,申报的整份并入不可达;现按字节证据判血缘
布局迁移工具的申报契约与此实现一致)。
**实证失效形态(2026-09-07 22:2x,decisions.jsonl 尾 10 行逐字节重复,
已另行去重)**:某次运行 shutil.move 因源被占用删源失败,留下
「dst 已物化 / 台账无记账 / 旧根残躯仍在」三态;下一轮把残躯当新化身
整份再并入 → 重复行。现防线(merge 前查,任一不满足拒并报人工,
绝不盲并):
①台账无 entry 而 dst 已存在 → 拒并(dst 来源不可证);
②接尾路径(start>0)src[start-1] 必须是行边界(\n),撕裂偏移拒并
  (新化身从 0 整份并入无拼接点,不受此查;同源残躯无新字节可并,
  亦不受此查——二进制留证件的残躯清理靠这条路);
③dst 末非空行 == 待并段首非空行 → 判内容重叠,拒并。
**残余风险(工具不自动处理,须人工对账)**:三态残留;锚失配且③未
命中时(实为被外部改动的旧化身)按新化身整份并入可能引入重复;以及
偏移记账与实际内容的任何错位。唯一强前提 = 迁移执行窗口旧根无写入方
(实机静默局间);做不到时,重跑必须人工盯首跑报告,禁无人值守连跑。

其余对象的重跑规则:
- 按局档案(match_g_*.json)与深评报告(*.md):只搬新树没有的文件,
  同名冲突保留新树侧(新树是权威)——整搬无合并,无双份风险;
- 水位线 .watermark.json:旧根后来者更新则覆盖(archived_through
  单调推进,后来者即最新)。

非目标:不搬旧根里的一次性分析产物(临时脚本/.bak/审计 txt/md、
outcomes_backfilled 等)——它们不是任何活代码的消费对象,留在旧根作
legacy 封存;不动哨兵运行态文件(.pos/.lock,动了 = 双实例/误报事故)。

用法(项目根):
    uv run python tools/cw/migrate_telemetry_tree.py            # 执行
    uv run python tools/cw/migrate_telemetry_tree.py --dry-run  # 只报告
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

from one_dragon.utils.file_utils import get_project_root

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

_REPO = get_project_root()

# 旧根(退役对象;字面量是本工具的输入契约,唯一豁免点见
# sr-od-test test_cw_infra_locks 墓碑扫描)
_OLD_REPLAY = _REPO / '.debug' / 'temp' / 'currency_war' / 'replay'
_OLD_SIM = _REPO / '.debug' / 'temp' / 'currency_war' / 'sim_runs'

# 新根(与 src kernel/cw_observe 根常量块同值;本工具零 src 深依赖面
# 之外的路径,独立声明保持可独立运行)
_NEW_TELEMETRY = _REPO / '.debug' / 'currency_war' / 'telemetry'
_NEW_LIVE = _NEW_TELEMETRY / 'live'
_NEW_MATCHES = _NEW_TELEMETRY / 'matches'
_NEW_SIM = _NEW_TELEMETRY / 'sim'
_NEW_DEEP = _REPO / '.debug' / 'currency_war' / 'deep_review'

#: 迁移台账(流文件字节偏移记账,支撑可重跑尾接;放新树根随树生存)
_MANIFEST = _NEW_TELEMETRY / '_migration_manifest.json'

#: live 流根的追加型流文件(旧 replay 根 → 新 live 根;含跨局 journal)
_STREAM_FILES: tuple[str, ...] = (
    'decisions.jsonl', 'outcomes.jsonl', 'runs.jsonl',
    'shop_snapshots.jsonl', 'exogenous.jsonl', 'exec_events.jsonl',
    'invest_cards.jsonl', 'obs_conflicts.jsonl', 'spend_ledger.jsonl',
    'defect_ledger.jsonl', 'op_journal.jsonl', 'cw4_counters.jsonl',
)

#: 购买留证 webp(装配端 _evidence_links 按 live 根 glob,必须跟流同根)
_EVIDENCE_GLOB = 'buy_expect_*.webp'

#: 档案根的活跃布局文件(match_<game_id>.json + 索引 + 水位线;
#: matches 下其余——reviews 子目录单独走深评,杂件不搬)
_MATCH_MOVE_GLOB = 'match_g_*.json'
_MATCH_FILE_NAMES: tuple[str, ...] = ('index.jsonl', '.watermark.json')

#: INDEX 结论行提取(各期复盘格式有差:先取首个「结论:」行;无则取
#: 「总评/总结」节的首个内容行,截断展示;权威结论永远在报告正文,
#: 链接指向全文)
_CONCLUSION_RE = re.compile(r'^\s*(?:#{1,4}\s|[-*]\s|\*\*)?\*{0,2}结论\*{0,2}[::]\s*(?P<c>.+?)\s*$')
_SUMMARY_HEADING_RE = re.compile(r'^#{1,3}\s*(?:总评|总结|总结论)\s*$')


def _load_manifest() -> dict[str, int]:
    """读迁移台账(文件名 → 已迁移字节偏移;坏/缺 = 空)。"""
    try:
        raw = json.loads(_MANIFEST.read_text(encoding='utf-8'))
        return {str(k): int(v) for k, v in raw.items()}
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return {}


def _save_manifest(m: dict[str, int]) -> None:
    _MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=0),
                         encoding='utf-8')


def _last_nonempty_line(data: bytes) -> bytes:
    """字节块的最后一个非空行(重叠校验用;空块/全空行 → b'')。"""
    for ln in reversed(data.splitlines()):
        if ln.strip():
            return ln
    return b''


def _first_nonempty_line(data: bytes) -> bytes:
    """字节块的第一个非空行(重叠校验用;空块 → b'')。"""
    for ln in data.splitlines():
        if ln.strip():
            return ln
    return b''


def _refuse(report: list[str], name: str, why: str) -> str:
    report.append(f'  REFUSE {name}(拒并,需人工对账): {why}')
    return 'refused'


def _lineage_anchor(dst: Path, src: Path, offset: int, size: int) -> str | None:
    """血缘判定(内容锚哈希;2026-09-08 最近改动三审 M2 治本)。

    记账协议下,上次已消费的 src 前缀字节 = dst 尾部同窗字节:两边
    sha256 一致 = src 与上次消费的是同一化身(接尾/残躯清理,返回
    'same');不一致 = 旧化身之后被重建的新化身(整份并入,返回 'new')。
    返回 None = dst 现有字节不足锚窗(dst 被外部改动/截断,血缘不可证,
    调用方拒并)。旧实现按 size 与 offset 的大小猜血缘,三种恰巧尺寸的
    新化身分别被截头/误删/恒拒——内容锚把血缘钉在字节证据上,不再猜。
    """
    window = min(offset, size)
    dst_size = dst.stat().st_size
    if dst_size < window:
        return None
    with src.open('rb') as f:
        src_head = f.read(window)
    with dst.open('rb') as f:
        f.seek(dst_size - window)
        dst_tail = f.read()
    same = (hashlib.sha256(src_head).digest()
            == hashlib.sha256(dst_tail).digest())
    return 'same' if same else 'new'


def _move_or_merge(src: Path, dst: Path, manifest: dict[str, int],
                   key: str, report: list[str]) -> str:
    """流文件迁移:首次 move,重跑按内容锚血缘尾接/整并(协议见模块 docstring)。

    重跑判定:manifest entry = 「当前 src 化身已消费到的字节」。血缘按
    内容锚(_lineage_anchor):同源 = 接尾(start=offset,无新字节则残躯
    清理);异源 = 新化身,从 0 整份并入。merge 前查(防线①②③,任一
    不满足拒并报人工):
    ①dst 存在而台账无 entry → dst 来源不可证,拒并;
    ②接尾路径(start>0)src[start-1] 必须是 \\n(偏移落在行边界),
      撕裂拒并——新化身从 0 并入无拼接点,不受此查;
    ③dst 末非空行 == 待并段首非空行 → 内容重叠,拒并。

    返回动作标记:'moved'(首次整搬)/ 'appended'(尾接/并入 n 字节)/
    'locked'(源被占用——运行中进程握着句柄,留给下次重跑)/
    'refused'(防线拒并,需人工对账)/ 'clean'(无增量或残躯已清)。
    """
    if not src.exists():
        return 'clean'
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        try:
            shutil.move(str(src), str(dst))
            manifest[key] = dst.stat().st_size
            report.append(f'  moved  {src.name} -> {dst}')
            return 'moved'
        except PermissionError:
            report.append(f'  LOCKED {src.name}(文件被运行中进程占用,留待重跑)')
            return 'locked'
    offset = manifest.get(key)
    size = src.stat().st_size
    # —— 防线①:台账无 entry 而 dst 已存在 = dst 来源不可证 ——
    if offset is None:
        return _refuse(report, src.name,
                       'dst 已存在且台账无记账(疑似上次 copy+删源失败'
                       '的三态残留);盲并会整份重复,请人工比对后清理台账')
    # —— 血缘判定(内容锚,三审 M2 治本)——
    anchor = _lineage_anchor(dst, src, offset, size)
    if anchor is None:
        return _refuse(report, src.name,
                       f'dst 现有字节不足锚窗 {min(offset, size)}B'
                       '(dst 被外部改动/截断,血缘不可证)')
    start = offset if anchor == 'same' else 0   # 同源=接尾;异源=新化身整份
    if start == size:
        # 同源残躯:上次并入成功但 unlink 被占用,内容锚已证 src 全部
        # 字节都在 dst 里(恰等长的真新化身走 anchor='new' 分支整份并入,
        # 不再被当残躯误删);无新字节可并,顺手清掉。
        # 若进程仍握句柄,删除失败无害,留下次重跑
        with contextlib.suppress(OSError):
            src.unlink()
        report.append(f'  clean  {src.name}(同源残躯,内容锚证实无新字节)')
        return 'clean'
    # —— 防线②:偏移必须落在行边界(仅接尾路径——旧实现无条件执行,
    # 比记账小的新化身在此越界读空恒拒,申报的整份并入不可达)——
    if start > 0:
        with src.open('rb') as f:
            f.seek(start - 1)
            boundary = f.read(1)
        if boundary != b'\n':
            return _refuse(report, src.name,
                           f'记账偏移 {offset} 不在行边界(命中 {boundary!r}),'
                           '偏移与内容错位')
    # —— 防线③:内容重叠检测(dst 末行 vs 待并首行)——
    with src.open('rb') as f:
        f.seek(start)
        head = f.read(65536)
    tail = _first_nonempty_line(head)
    dst_size = dst.stat().st_size
    with dst.open('rb') as f:
        f.seek(max(0, dst_size - 65536))
        dst_tail = _last_nonempty_line(f.read())
    if tail and dst_tail and tail == dst_tail:
        return _refuse(report, src.name,
                       f'待并段首行与 dst 末行相同(内容重叠): {tail[:80]!r}')
    try:
        with src.open('rb') as fsrc, dst.open('ab') as fdst:
            fsrc.seek(start)
            shutil.copyfileobj(fsrc, fdst)
        manifest[key] = size
        src.unlink()
        report.append(f'  append {src.name} +{size - start}B'
                      f'({"尾接" if start else "新化身整份并入"})')
        return 'appended'
    except PermissionError:
        report.append(f'  LOCKED {src.name}(尾接失败:文件被占用,留待重跑)')
        return 'locked'


def _move_new_only(src_dir: Path, dst_dir: Path, globs: list[str],
                   report: list[str]) -> int:
    """整搬型迁移(档案/报告):只搬新树没有的文件,返回搬迁件数。"""
    n = 0
    if not src_dir.exists():
        return 0
    dst_dir.mkdir(parents=True, exist_ok=True)
    names: set[str] = set()
    for g in globs:
        names.update(p.name for p in src_dir.glob(g))
    for name in sorted(names):
        src = src_dir / name
        if not src.is_file():
            continue
        dst = dst_dir / name
        if dst.exists():
            continue
        shutil.move(str(src), str(dst))
        report.append(f'  moved  {name} -> {dst_dir.name}/')
        n += 1
    return n


def _copy_overwrite(src: Path, dst: Path) -> bool:
    """水位线类「后来者即最新」文件:旧根存在且更新则覆盖新树侧。"""
    if not src.exists():
        return False
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return True


def _extract_conclusion(md_path: Path) -> str:
    """报告结论一行(截 80 字;无 → 占位说明)。"""
    try:
        text_lines = md_path.read_text(encoding='utf-8').splitlines()
        for line in text_lines:
            m = _CONCLUSION_RE.match(line)
            if m:
                return _tidy(m.group('c'))
        # 回退:「总评/总结」节的首个内容行(新协议报告的收口格式)
        in_summary = False
        for line in text_lines:
            if _SUMMARY_HEADING_RE.match(line):
                in_summary = True
                continue
            if in_summary and line.strip() and not line.startswith('#'):
                return _tidy(line)
    except (OSError, UnicodeDecodeError):
        pass
    return '(未提取到结论行,见正文)'


def _tidy(text: str) -> str:
    """结论行整理:去 markdown 加粗,截 80 字。"""
    text = text.replace('**', '').strip()
    return (text[:80] + '…') if len(text) > 80 else text


_GAME_ID_RE = re.compile(r'^g_(\d{8})_(\d{6})$')


def build_index() -> Path:
    """深评分册 INDEX.md(局id/日期/结论一行/链接;按局 id 时间序)。"""
    rows: list[tuple[str, str, str]] = []
    for p in sorted(_NEW_DEEP.glob('*.md')):
        if p.name == 'INDEX.md':   # 分册自身不入册
            continue
        gid = p.stem
        m = _GAME_ID_RE.match(gid)
        date = (f'{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}'
                if m else time.strftime('%Y-%m-%d', time.localtime(p.stat().st_mtime)))
        rows.append((gid, date, _extract_conclusion(p)))
    rows.sort(key=lambda r: r[0])
    stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        '# 货币战争·单局深评分册(INDEX)',
        '',
        '> 深评固定落点:`.debug/currency_war/deep_review/<game_id>.md`'
        '(2026-09-07 布局裁定)。一局一份报告,本册 = 局 id / 日期 / 结论一行 /'
        ' 链接;结论行是索引便利摘要(自动提取首条「结论:」行),权威结论以'
        '报告全文为准。协议 = sr-od-currency-war-dev skill references/match-review.md。',
        '',
        f'更新:{stamp} · 共 {len(rows)} 篇',
        '',
        '| 局 id | 日期 | 结论一行 | 报告 |',
        '|---|---|---|---|',
    ]
    for gid, date, concl in rows:
        lines.append(f'| {gid} | {date} | {concl} | [{gid}.md]({gid}.md) |')
    lines.append('')
    out = _NEW_DEEP / 'INDEX.md'
    out.write_text('\n'.join(lines), encoding='utf-8')
    return out


def _write_legacy_note(path: Path, moved_to: str) -> None:
    """旧根退役声明(为什么还留着目录:legacy 封存 + 指路新树)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'# 此目录已退役(legacy;2026-09-07 布局裁定,T-125)\n\n'
        f'活跃数据已迁至 `{moved_to}`。本目录不再有任何活跃写点——\n'
        f'写端常量已全部改指新树(src `kernel/cw_observe` 根常量块单一源)。\n'
        f'余下文件 = 未迁移的一次性分析产物/备份封存,非任何活代码的消费对象。\n'
        f'重跑迁移补尾:`uv run python tools/cw/migrate_telemetry_tree.py`。\n',
        encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser(description='CW 遥测树迁移(旧根→新根,可重跑)')
    ap.add_argument('--dry-run', action='store_true', help='只报告不搬')
    args = ap.parse_args()

    manifest = _load_manifest()
    report: list[str] = []
    n_match = n_review = 0

    if args.dry_run:
        pend = [s for s in _STREAM_FILES
                if (_OLD_REPLAY / s).exists()]
        evid = list(_OLD_REPLAY.glob(_EVIDENCE_GLOB)) if _OLD_REPLAY.exists() else []
        n_match = (len(list((_OLD_REPLAY / 'matches').glob(_MATCH_MOVE_GLOB)))
                   if (_OLD_REPLAY / 'matches').exists() else 0)
        n_review = (len(list((_OLD_REPLAY / 'matches' / 'reviews').glob('*.md')))
                    if (_OLD_REPLAY / 'matches' / 'reviews').exists() else 0)
        n_sim = (len(list(_OLD_SIM.iterdir())) if _OLD_SIM.exists() else 0)
        print(f'[dry-run] 流文件待迁 {len(pend)} | 留证 webp {len(evid)} | '
              f'档案 {n_match} | 报告 {n_review} | sim 批条目 {n_sim}')
        return 0

    # ① live 流根:流文件 + 留证 webp
    for name in _STREAM_FILES:
        _move_or_merge(_OLD_REPLAY / name, _NEW_LIVE / name, manifest,
                       f'stream:{name}', report)
    for src in list(_OLD_REPLAY.glob(_EVIDENCE_GLOB)) if _OLD_REPLAY.exists() else []:
        _move_or_merge(src, _NEW_LIVE / src.name, manifest,
                       f'evidence:{src.name}', report)

    # ② 档案根:match_*.json + 索引;水位线后来者覆盖
    n_match = _move_new_only(_OLD_REPLAY / 'matches', _NEW_MATCHES,
                             [_MATCH_MOVE_GLOB], report)
    for name in _MATCH_FILE_NAMES[:-1]:
        _move_new_only(_OLD_REPLAY / 'matches', _NEW_MATCHES, [name], report)
    _copy_overwrite(_OLD_REPLAY / 'matches' / '.watermark.json',
                    _NEW_MATCHES / '.watermark.json')

    # ③ 深评:reviews/*.md → deep_review/(含非 g_ 命名的历史报告)
    reviews = _OLD_REPLAY / 'matches' / 'reviews'
    n_review = _move_new_only(reviews, _NEW_DEEP, ['*.md'], report)

    # ④ sim 批:sim_runs 全部条目 → telemetry/sim/(批账本与锚定批是
    # 复现链锚点,留旧处 = 锚点断链,故整体迁;取舍见任务批注)。
    # 逐文件走 move_or_merge:sim 常开下重跑时,旧代码进程仍在旧根写
    # 「迁移后才出现的批」或给已迁批接尾——文件级偏移合并两头都不丢。
    if _OLD_SIM.exists():
        for src in sorted(_OLD_SIM.rglob('*')):
            if not src.is_file() or src.name == 'LEGACY_RETIRED.md':
                continue
            rel = src.relative_to(_OLD_SIM)
            _move_or_merge(src, _NEW_SIM / rel, manifest,
                           f'sim:{rel.as_posix()}', report)
        # 清空后的空目录树顺手移除(目录内容已在新树)
        for d in sorted((p for p in _OLD_SIM.rglob('*') if p.is_dir()),
                        reverse=True):
            with contextlib.suppress(OSError):
                d.rmdir()

    # ⑤ INDEX(按当前 deep_review 全量重建,幂等)
    index_path = build_index()

    _save_manifest(manifest)
    _write_legacy_note(_OLD_REPLAY / 'LEGACY_RETIRED.md',
                       '.debug/currency_war/telemetry/{live,matches}')
    _write_legacy_note(_OLD_SIM / 'LEGACY_RETIRED.md',
                       '.debug/currency_war/telemetry/sim')

    print('\n'.join(report) if report else '(无可迁对象——旧根已清)')
    n_deep = len([p for p in _NEW_DEEP.glob('*.md') if p.name != 'INDEX.md'])
    print(f'[迁移对账] 按局档案 {n_match} 份 | 深评报告 {n_review} 篇 '
          f'| deep_review 现有 {n_deep} 篇')
    print(f'[INDEX] {index_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
