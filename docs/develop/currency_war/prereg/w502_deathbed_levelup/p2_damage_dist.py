"""W502 · P2 濒死段掉血轴语料统计(只读 replay outcomes)。

口径:
- 语料 = .debug/temp/currency_war/replay/outcomes.jsonl(实机局逐轮结算,只读)。
- 单场掉血 = 同 run 内上一条 outcome 的 hp_after − 本条 hp_after(正=掉血);
  hp_before 用前一条恢复后的真值(奖励节点回血自然进轴)。
- 战斗节点 = node_type 含 战斗/boss/遭遇;排除 奖励/补给/扑满(不掉血或不构成伤害轴)。
- 濒死段分桶按 hp_before(战斗开始前血量):≤10(命题主域 H0=10)、11-20(对照)、全量(无条件)。
- 只统计 plane==2(P2 濒死升级雨的发生位面);P1 全量一并列出作对照。

产出:stdout 表 + damage_dist.json(供 p21 证明单篇引用)。
"""
import json
import statistics
from collections import defaultdict
from pathlib import Path

REPLAY = Path('.debug/temp/currency_war/replay/outcomes.jsonl')
OUT = Path('.debug/temp/currency_war/w502_deathbed_levelup/damage_dist.json')

BATTLE_KEYS = ('战斗', 'boss', '遭遇')
EXCLUDE_KEYS = ('奖励', '补给', '扑满')


def is_battle(node_type: str) -> bool:
    if any(k in node_type for k in EXCLUDE_KEYS):
        return False
    return any(k in node_type for k in BATTLE_KEYS)


def main() -> None:
    records = [json.loads(line) for line in REPLAY.read_text(encoding='utf-8').splitlines() if line.strip()]
    # 逐 run 排序后差分出 hp_before
    by_run: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_run[r['run_id']].append(r)
    samples: list[dict] = []
    for run_id, rs in by_run.items():
        rs.sort(key=lambda r: (r['plane'], r['round_num']))
        prev_hp: int | None = None
        prev_plane: int | None = None
        for r in rs:
            hp_before = prev_hp if (prev_plane == r['plane']) else None
            if is_battle(r.get('node_type', '')) and hp_before is not None and r.get('hp_after') is not None:
                dmg = hp_before - r['hp_after']
                samples.append({
                    'run_id': run_id,
                    'plane': r['plane'],
                    'round': r['round_num'],
                    'node_type': r.get('node_type'),
                    'hp_before': hp_before,
                    'hp_after': r['hp_after'],
                    'damage': dmg,
                })
            prev_hp = r.get('hp_after')
            prev_plane = r['plane']

    def bucket(ss: list[dict]) -> dict:
        ds = [s['damage'] for s in ss]
        losses = [d for d in ds if d > 0]
        return {
            'n': len(ds),
            'loss_rate': round(1 - sum(1 for d in ds if d <= 0) / len(ds), 3) if ds else None,
            'loss_mean': round(statistics.mean(losses), 2) if losses else None,
            'loss_p50': round(statistics.median(losses), 1) if losses else None,
            'loss_p90': round(sorted(losses)[int(0.9 * len(losses)) - 1], 1) if losses else None,
            'loss_min': min(losses) if losses else None,
            'loss_max': max(losses) if losses else None,
        }

    report = {
        'corpus': str(REPLAY),
        'n_runs': len(by_run),
        'p2_hp_le_10': bucket([s for s in samples if s['plane'] == 2 and 0 < s['hp_before'] <= 10]),
        'p2_hp_le_20': bucket([s for s in samples if s['plane'] == 2 and 0 < s['hp_before'] <= 20]),
        'p2_all': bucket([s for s in samples if s['plane'] == 2]),
        'p1_all': bucket([s for s in samples if s['plane'] == 1]),
        'p2_deathbed_samples': [
            {k: s[k] for k in ('run_id', 'round', 'node_type', 'hp_before', 'hp_after', 'damage')}
            for s in samples if s['plane'] == 2 and 0 < s['hp_before'] <= 10
        ],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'p2_deathbed_samples'}, ensure_ascii=False, indent=2))
    print(f"\ndeathbed (P2, hp_before<=10) 逐样本 n={len(report['p2_deathbed_samples'])} -> {OUT}")


if __name__ == '__main__':
    main()
