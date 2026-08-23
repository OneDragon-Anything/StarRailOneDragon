"""货币战争 · Δ池快照生成器(生产 replay → 主仓提交快照数据层)。

数据源:.debug/temp/currency_war/replay/{decisions,outcomes}.jsonl
(生产遥测 append 流)。配对口径与 cw_sim._pool_from_replay 同源:
decisions 每轮取末行板深,outcomes 同 run 相邻轮 hp 差分。
桶键(ADR-0279,批⑬):battle=成型度 rung(结算前 board_before +
decisions deployed join);encounter/boss=深度桶。

产出:src/sr_od/application/currency_war/cw_delta_pool_data.py ——
SNAPSHOT {节点: {深度桶: [Δ]}} + META(构成/过滤/指纹)。
主仓提交(先例:REFRESH_PROB 实测概率表在 cw_shop_odds);CI 与
跨机可复现基准靠它(裸 .debug 池随实机追加漂移,不可作基准)。

防自中毒(对抗审查定谳):**源目录断言 ≠ sim_runs** —— sim 批量
落盘(sim_runs)若混进池源即「sim 校准 sim」回路;生成器是池的
唯一入口,防线落在这里,不靠调用方自觉。

半写行容错:生产 append 进行中尾行可能撕裂(JSONDecodeError)——
跳过+计数告警,不中断、不静默(计数进 META)。

用法: uv run python tools/cw/gen_delta_pool_snapshot.py
      [--runs id1,id2] [--export-json PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[2]
REPLAY_DIR = REPO / '.debug/temp/currency_war/replay'
SIM_RUNS_DIR = REPO / '.debug/temp/currency_war/sim_runs'
DATA_PY = REPO / 'src/sr_od/application/currency_war/cw_delta_pool_data.py'

# 写目标白名单守卫(同 gen_factions 范式):本生成器只允许写
# _data.py 数据层文件;判断层/策略文件永不在此列。
WRITABLE_TARGETS = (DATA_PY,)

# 节点类型归一(与 cw_sim._pool_from_replay 同表)
NT_MAP = {'普通战斗': 'battle', '遭遇': 'encounter', '奖励': 'reward',
          '首领': 'boss', '补给': 'supply'}
DEPTH_BUCKET_W = 3   # 与 cw_sim._DEPTH_BUCKET_W 同值(指纹输入)


def _assert_guards(src_dir: Path) -> None:
    """写目标白名单 + 源目录 ≠ sim_runs(防 sim 数据回灌校准池)。"""
    for t in WRITABLE_TARGETS:
        if t.suffix == '.py' and not t.name.endswith('_data.py'):
            raise RuntimeError(f'生成器写目标非法: {t}(只写 _data.py 数据层)')
    src_resolved = src_dir.resolve()
    sim_resolved = SIM_RUNS_DIR.resolve()
    if src_resolved == sim_resolved or sim_resolved in src_resolved.parents:
        raise RuntimeError(
            f'池源目录非法: {src_resolved} 位于 sim_runs 下——'
            'sim 产出回灌校准池 = 自中毒回路(对抗审查定谳);'
            '池源只能是生产 replay 目录')


# r378b(测量链 review B3):事故局隔离清单——这些 run 的遥测被判定
# 不可信(双进程写侧竞争/观测链断),生成器**默认物理排除**防回灌
# (只「作废判读信任」不排池,下次全量重生成会悄悄流回快照)。
# 增删条目在此登记(带一句事故原因),源头治理靠 daemon 修复。
QUARANTINED_RUNS: dict[str, str] = {
    # 2026-08-22 双进程事故(r377):18:56 restart orphan 残留,两代
    # server 并行写 outcomes(killed 全 None=写侧竞争表征)。
    'run_20260822_185613': 'r377 双进程写竞争(局55)',
    'run_20260822_191028': 'r377 双进程写竞争(局56/57 重启交错)',
}


def _iter_jsonl(path: Path, skipped: dict) -> list[dict]:
    """逐行解析 jsonl;半写行(撕裂尾行)跳过+计数,不静默。"""
    out: list[dict] = []
    if not path.exists():
        skipped[str(path.name)] = skipped.get(str(path.name), 0)
        return out
    for ln in path.read_text(encoding='utf-8').splitlines():
        if not ln.strip():
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            skipped[path.name] = skipped.get(path.name, 0) + 1
    return out


def _engines_count_of(bf: dict, names: frozenset) -> int:
    """rung = _engines_count 单一源(cw_sim;ADR-0279)——battle 桶键。"""
    sys.path.insert(0, str(REPO / 'src'))
    from sr_od.application.currency_war.cw_sim import (  # noqa: E402
        _engines_count,
    )
    return _engines_count(bf, names)


def build_pool(src_dir: Path, runs_filter: set[str] | None):
    """构建 {节点: {桶键: [Δ]}} + 构成 meta(与 cw_sim 同配对口径)。

    桶键语义(ADR-0279,批⑬):battle=成型度 rung(结算前
    board_before + decisions deployed join 算希儿系);encounter/
    boss=深度桶(批⑬ F1 encounter rung 样本不足暂沿用)。

    守卫在函数体内生效(审查#4:只在 main 锁不住 import 复用)。
    """
    _assert_guards(src_dir)
    skipped: dict[str, int] = {}
    quarantined_hits: set[str] = set()
    boards: dict = {}
    deployed_names: dict = {}
    for d in _iter_jsonl(src_dir / 'decisions.jsonl', skipped):
        if runs_filter and d.get('run_id') not in runs_filter:
            continue
        if d.get('run_id') in QUARANTINED_RUNS:
            quarantined_hits.add(d.get('run_id'))
            continue
        st = d.get('state') or {}
        b = st.get('board') or {}
        k = (d.get('run_id'), d.get('plane'), d.get('round_num'))
        boards[k] = sum(b.values())
        deployed_names[k] = frozenset(
            x.get('char_id') or '' for x in (st.get('deployed') or [])
            if isinstance(x, dict))
    seqs: dict[str, list] = {}
    for o in _iter_jsonl(src_dir / 'outcomes.jsonl', skipped):
        if o.get('hp_after') is None:
            continue
        if runs_filter and o.get('run_id') not in runs_filter:
            continue
        if o.get('run_id') in QUARANTINED_RUNS:
            quarantined_hits.add(o.get('run_id'))
            continue
        seqs.setdefault(o.get('run_id'), []).append(o)
    pool: dict = {}
    per_run_rounds: dict[str, int] = {}
    unlabeled_dropped = 0
    for run, seq in seqs.items():
        seq.sort(key=lambda o: (o.get('plane') or 0, o.get('round_num') or 0))
        per_run_rounds[str(run)] = len(seq)
        for a, b2 in zip(seq, seq[1:], strict=False):
            raw_nt = b2.get('node_type') or ''
            nt = NT_MAP.get(raw_nt, raw_nt)
            if not nt:
                # 2026-08-22 retrofix(ADR-0239 配套):历史 node_type
                # 为死链产物已置 None——无标签行**不可入池**(标签
                # 不可信的"经验分布"是幻觉地基),计数披露。
                unlabeled_dropped += 1
                continue
            k = (run, b2.get('plane'), b2.get('round_num'))
            dep = boards.get(k)
            if dep is None:
                continue
            delta = b2['hp_after'] - a['hp_after']
            if nt == 'battle':
                # ADR-0279(批⑬):battle 按 rung 一维分桶(结算前
                # board_before + deployed join;depth 维弃用,F3)。
                bucket = _engines_count_of(
                    b2.get('board_before') or {},
                    deployed_names.get(k, frozenset()))
            else:
                # encounter/boss 暂沿用 depth 分桶(批⑬ F1)。
                bucket = min(dep // DEPTH_BUCKET_W, 5) * DEPTH_BUCKET_W
            pool.setdefault(nt, {}).setdefault(bucket, []).append(delta)
    meta = {
        'source_dir': str(src_dir),
        'runs': per_run_rounds,
        'runs_filter': (sorted(runs_filter) if runs_filter else 'all'),
        'skipped_lines': skipped,
        'unlabeled_dropped': unlabeled_dropped,
        # r378b:隔离清单实际命中的 run(没命中=清单过期,该清理)
        'quarantined_hits': sorted(quarantined_hits),
        'depth_bucket_w': DEPTH_BUCKET_W,
        # ADR-0279(批⑬):battle 桶键=rung(真值表随重生成锁定;
        # cw_sim_checks.BATTLE_RUNG_TRUTH 漂移报警消费此表口径)
        'battle_rung': {
            str(b): {'n': len(v), 'mean': round(sum(v) / len(v), 2)}
            for b, v in sorted((pool.get('battle') or {}).items())},
        'note': 'v2 只收可信标签行(2026-08-22 retrofix 后:死链'
                '历史 node_type 置 None 已丢弃计数);事故局物理排除'
                '(QUARANTINED_RUNS,r378b);跨策略版本混杂'
                '已知(一轮#10),过滤走 --runs 重生成;'
                'v3(ADR-0279,批⑬)battle 桶键 depth→rung'
                '(成型度一维分桶),encounter/boss 维持 depth 桶',
    }
    return pool, meta


def main() -> None:
    ap = argparse.ArgumentParser(description='Δ池快照生成器')
    ap.add_argument('--runs', default='',
                    help='逗号分隔 run_id 白名单(默认全部)')
    ap.add_argument('--export-json', default='',
                    help='另存 JSON 快照(cw_sim.resolve_pool(Path) 重放用)')
    args = ap.parse_args()
    src_dir = REPLAY_DIR
    _assert_guards(src_dir)
    runs_filter = {r.strip() for r in args.runs.split(',') if r.strip()} or None
    pool, meta = build_pool(src_dir, runs_filter)
    if not pool:
        raise RuntimeError(f'池为空: {src_dir} 无可配对样本(decisions 板深 × outcomes 差分)')

    sys.path.insert(0, str(REPO / 'src'))
    from sr_od.application.currency_war.cw_sim import (  # noqa: E402
        _SAMPLER_VERSION,
        pool_fingerprint,
    )
    meta['sampler_version'] = _SAMPLER_VERSION
    fp = pool_fingerprint(pool)
    meta['fingerprint'] = fp

    lines = [
        '"""Δ池快照(生成产物——勿手编)。',
        '',
        '本文件由 tools/cw/gen_delta_pool_snapshot.py 生成;重跑:',
        '    uv run python tools/cw/gen_delta_pool_snapshot.py',
        '手改会被下次生成覆盖,且指纹校验(resolve_pool)会拒绝失配数据。',
        '消费方:cw_sim.resolve_pool(\'snapshot\')(CI/跨机可复现基准);',
        '判断层勿直接 import 本模块。',
        '"""',
        'from __future__ import annotations',
        '',
        f'META: dict = {json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True)}',
        '',
        f'SNAPSHOT: dict = {json.dumps(pool, ensure_ascii=False, sort_keys=True)}',
        '',
    ]
    DATA_PY.write_text('\n'.join(lines), encoding='utf-8')
    n = sum(len(v) for b in pool.values() for v in b.values())
    print(f'快照已写 {DATA_PY.name}: 节点×{len(pool)} 样本×{n} '
          f'指纹 {fp} 跳过行 {meta["skipped_lines"]}')
    if args.export_json:
        ej = Path(args.export_json)
        if ej.suffix != '.json':
            raise RuntimeError(f'--export-json 只接受 .json: {ej}')
        ej.write_text(json.dumps(
            {'meta': meta, 'snapshot': pool}, ensure_ascii=False, indent=1,
            sort_keys=True), encoding='utf-8')
        print(f'JSON 快照已导出: {ej}')


if __name__ == '__main__':
    main()
