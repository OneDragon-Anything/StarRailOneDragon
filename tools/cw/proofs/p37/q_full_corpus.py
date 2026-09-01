"""P37v2.1 q_full 语料现算 + run 级 cluster bootstrap(入库可复跑,数据锁单一源)。

口径 = 证明文档 docs/game/currency_war/research/proofs/p37-late-xp-conversion-cost.md §2A:
  - 语料:.debug/temp/currency_war/replay/{decisions,outcomes}.jsonl(原始遥测,非 match 归档);
  - 健康带帧:r4-r7 ∧ 该轮决策时 hp>25;
  - 行末金 = 下一轮决策前金(截尾轮用末行 gold);
  - q_full = 健康带中行末金>=50 的轮占比;
  - CI = run 级 cluster bootstrap(轮按局聚簇,resample 单元=run,2000 次,seed=37)
    —— Wilson 区间按二项独立假设偏窄,不采(证明 §2A 已声明)。

用途:
  1) p37v2_ev_closure.py 的数据锁从这里现算 Q_K/Q_N/CI(语料追加即漂移可见,不再锁文档转录值);
  2) 独立复跑:uv run python tools/cw/proofs/p37/q_full_corpus.py

窗口披露:当前语料 outcomes 最早 run=2026-08-22(更早 runs 已在 08-22 清理,
bak-pre-purge-20260822 目录为证)——文档旧写「08-16 起」已过期,以本脚本现算为准。
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[4]
REP = BASE / '.debug/temp/currency_war/replay'

N_BOOT = 2000
SEED = 37
CI = (0.025, 0.975)


def load_health_rows(rep: Path = REP) -> list[dict]:
    """健康带逐轮行(含 run 聚簇键与行末金);语料缺失时抛 FileNotFoundError。"""
    dec_fp, out_fp = rep / 'decisions.jsonl', rep / 'outcomes.jsonl'
    if not dec_fp.exists() or not out_fp.exists():
        raise FileNotFoundError(f'语料缺失:{dec_fp} / {out_fp}')
    dec: dict[str, dict] = defaultdict(dict)
    for ln in dec_fp.read_text(encoding='utf-8').splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        dec[r['run_id']][(r.get('plane'), r.get('round_num'))] = r
    out: dict[str, list] = defaultdict(list)
    for ln in out_fp.read_text(encoding='utf-8').splitlines():
        if not ln.strip():
            continue
        o = json.loads(ln)
        out[o['run_id']].append(o)
    rows = []
    for k, orows in out.items():
        orows.sort(key=lambda o: (o.get('plane') or 0, o.get('round_num') or 0))
        for i, o in enumerate(orows):
            if not (4 <= (o.get('round_num') or 0) <= 7):
                continue
            d1 = dec[k].get((o.get('plane'), o.get('round_num')))
            if d1 is None:
                continue
            d2 = (dec[k].get((orows[i + 1].get('plane'), orows[i + 1].get('round_num')))
                  if i + 1 < len(orows) else None)
            g_end = d2.get('gold') if d2 else d1.get('gold')
            rows.append({'run': k, 'g_end': g_end, 'hp': d1.get('hp'),
                         'plane': o.get('plane'), 'date': (d1.get('ts') or '')[:10]})
    return [r for r in rows if (r['hp'] or 0) > 25]


def q_full_point(rows: list[dict]) -> tuple[int, int]:
    k = sum(1 for r in rows if (r['g_end'] or 0) >= 50)
    return k, len(rows)


def q_full_cluster_boot(rows: list[dict], n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float]:
    """run 级重抽(轮按局聚簇);返回 95%CI 下/上端。"""
    by_run: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        by_run[r['run']].append(r['g_end'] or 0)
    runs = list(by_run)
    rng = random.Random(seed)
    boot = []
    for _ in range(n_boot):
        tot = n = 0
        for _ in range(len(runs)):
            gs = by_run[runs[rng.randrange(len(runs))]]
            tot += sum(1 for g in gs if g >= 50)
            n += len(gs)
        if n:
            boot.append(tot / n)
    boot.sort()
    if not boot:
        return float('nan'), float('nan')
    return boot[int(CI[0] * len(boot))], boot[int(CI[1] * len(boot)) - 1]


def compute(rep: Path = REP) -> dict:
    rows = load_health_rows(rep)
    k, n = q_full_point(rows)
    lo, hi = q_full_cluster_boot(rows)
    dates = sorted(r['date'] for r in rows if r['date'])
    return {'k': k, 'n': n, 'pt': k / n if n else float('nan'),
            'ci': (lo, hi), 'n_runs': len({r['run'] for r in rows}),
            'window': (dates[0], dates[-1]) if dates else None}


def main() -> None:
    r = compute()
    print(f'q_full 语料现算:健康带 {r["n"]} 轮(贡献 run {r["n_runs"]}),满息 {r["k"]} 轮')
    print(f'  点估计 = {r["pt"]:.4f};run 级 cluster bootstrap 95%CI(N={N_BOOT},seed={SEED})'
          f' = [{r["ci"][0]:.3f}, {r["ci"][1]:.3f}]')
    print(f'  语料窗口(健康带行 ts):{r["window"][0]} ~ {r["window"][1]}')
    print('  文档转录基准(v2.1 定稿):125/465=0.269 [0.212, 0.328](语料追加容差内漂移)')


if __name__ == '__main__':
    sys.exit(main())
