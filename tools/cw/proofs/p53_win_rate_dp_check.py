"""win_rate_dp_by_plane 注册表值的只读复算自检(增量 B,ADR-0515)。

复算对象 = ``cw_registry.win_rate_dp_by_plane``(Δp(e0→e1) 成型档条件
胜率边际,分位面):对 p15 冻结语料(``tools/cw/proofs/p15/
corpus_battle_loss.jsonl``,sha 848dc1aa)按 battle-only + killed 结算屏
权威口径(killed=True=胜)分桶,局聚类 bootstrap(n=2000,seed=20260910)
重算 P1/P2 的 rung0/rung1 胜率与 Δp 点估计,与注册表登记值对账。

只读自检(零写入;P2 注册值为 fail-closed 钳 0,对账点估计而非登记值):
``uv run python tools/cw/proofs/p53_win_rate_dp_check.py``
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / 'src'))

CORPUS = Path(__file__).resolve().parent / 'p15' / 'corpus_battle_loss.jsonl'
N_BOOT = 2000
SEED = 20260910


def win_rates(rows: list[dict], plane: int) -> dict[int, list[int]]:
    buckets: dict[int, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r['plane'] != plane or r['node_type'] != 'battle' or r['rung'] > 1:
            continue
        buckets[r['rung']][r['game_id']].append(1 if r['killed'] else 0)
    return {k: [v for g in sorted(gids) for v in games[g]]
            for k, games in buckets.items()
            for gids in [sorted(games)]} if buckets else {}


def _flat(buckets: dict[int, dict[str, list[int]]], rung: int) -> list[int]:
    return [v for g in sorted(buckets[rung]) for v in buckets[rung][g]]


def main() -> int:
    sys.stdout.reconfigure(encoding='utf-8')
    rows = [json.loads(l) for l in CORPUS.read_text(encoding='utf-8').splitlines() if l.strip()]
    problems: list[str] = []
    for plane, reg_dp in ((1, 0.450), (2, -0.197)):
        buckets: dict[int, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
        for r in rows:
            if r['plane'] != plane or r['node_type'] != 'battle' or r['rung'] > 1:
                continue
            buckets[r['rung']][r['game_id']].append(1 if r['killed'] else 0)
        if not buckets or 0 not in buckets or 1 not in buckets:
            problems.append(f'P{plane}: 桶缺 rung0/rung1')
            continue
        gids = sorted(set(buckets[0]) | set(buckets[1]))
        f0, f1 = _flat(buckets, 0), _flat(buckets, 1)
        w0, w1 = sum(f0) / len(f0), sum(f1) / len(f1)
        dp = w1 - w0

        def dp_of(sample: list[str]) -> float | None:
            def wr(b: int) -> float | None:
                vals = [v for g in sample for v in buckets[b].get(g, ())]
                return sum(vals) / len(vals) if vals else None
            a, b_ = wr(0), wr(1)
            return None if a is None or b_ is None else b_ - a

        rng = random.Random(SEED)
        diffs = sorted(d for d in (dp_of([rng.choice(gids) for _ in gids])
                                   for _ in range(N_BOOT)) if d is not None)
        lo = diffs[int(0.025 * len(diffs))]
        hi = diffs[int(0.975 * len(diffs)) - 1]
        print(f'P{plane} battle: rung0 win={w0:.3f} n={len(f0)} / '
              f'rung1 win={w1:.3f} n={len(f1)} -> dp={dp:.3f} CI=[{lo:.3f},{hi:.3f}]'
              f' (registry={"%.3f" % reg_dp}{" 钳0" if plane == 2 else ""})')
        if abs(dp - reg_dp) > 0.005:
            problems.append(f'P{plane}: 重算 dp={dp:.3f} vs 登记 {reg_dp:.3f}')
    if problems:
        print(f'自检 FAIL({len(problems)} 项):')
        for p in problems:
            print(' -', p)
        return 1
    print('自检 PASS: Δp 点估计与注册表登记值对账(bootstrap CI 的 RNG 流'
          '差异 ±0.01 内属预期,登记值以点估计为准)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
