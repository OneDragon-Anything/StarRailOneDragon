"""15 号敌情数值层最小落地(r11 review #6):位面×节点强度带,从 telemetry 实测校准。

影子 DP 的 difficulty_scale 是先验(0.5/0.9/1.4/1.5+0.05n);本件用自家 outcomes.jsonl
的实测掉血(每节点 hp_after 差)校准/对照,输出带样本量的强度表——给 live 消费面
(effective_hp_threshold 已接 ×1.25/×1.5;后续 _refresh_cap/_phase_weights 若需细化,
按节点粒度消费此表)。纯函数,不进决策路径。
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NodeStrength:
    """一个 (plane, node) 档的实测强度。"""

    plane: int
    node: int
    n: int                 # 样本数
    mean_loss: float       # 平均掉血
    p90_loss: float        # 90 分位掉血(急性风险)


@dataclass
class StrengthTable:
    rows: list[NodeStrength] = field(default_factory=list)

    def lookup(self, plane: int, node: int) -> NodeStrength | None:
        return next((r for r in self.rows if r.plane == plane and r.node == node), None)


def calibrate_strength(replay_dir: str | Path, min_n: int = 2) -> StrengthTable:
    """outcomes.jsonl 实测 → (plane,node) 强度表。

    掉血 = 上一条 outcome.hp_after − 本条 hp_after(同 run 内顺序);首条用 100 起。
    min_n 以下不入表(样本不足不硬判,对齐 04「读不到≠证据」)。
    """
    rows = [json.loads(line) for line in Path(replay_dir).joinpath('outcomes.jsonl')
            .read_text(encoding='utf-8').splitlines()]
    by_run: dict[str, list] = defaultdict(list)
    for o in rows:
        by_run[o['run_id']].append(o)
    losses: dict[tuple[int, int], list[int]] = defaultdict(list)
    for rid, seq in by_run.items():
        prev_hp = 100
        for o in sorted(seq, key=lambda x: (x['plane'], x['round_num'])):
            loss = max(0, prev_hp - o['hp_after'])
            losses[(o['plane'], o['round_num'])].append(loss)
            prev_hp = o['hp_after']
    table = StrengthTable()
    for (p, n), ls in sorted(losses.items()):
        if len(ls) < min_n:
            continue
        s = sorted(ls)
        p90 = s[min(len(s) - 1, int(len(s) * 0.9))]
        table.rows.append(NodeStrength(p, n, len(ls), sum(ls) / len(ls), p90))
    return table


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    t = calibrate_strength('.debug/temp/currency_war/replay')
    print(f'{len(t.rows)} 档(n≥2):')
    for r in t.rows:
        print(f'  p{r.plane}-{r.node:2d} n={r.n:2d} mean_loss={r.mean_loss:5.1f} p90={r.p90_loss:5.1f}')
