"""时间经济台账 J0(redesign 45 号;ADR-0187):吞吐分解首产(零行为,纯离线)。

**诊断(45 号)**:wall-clock 是 44 轮以来唯一从未被定价的资源;「判死→照打完」是无人
决策过的隐式默认,死局时间被默认烧掉。局/小时应成为被管理资产。

**J0 落地**(零行为,离线;45 号判据第一条):
- ``run_wallclock``:单局 wall-clock + 节拍(节点间隔序列,来自 outcomes.jsonl ts);
- ``throughput_ledger``:台账首产——局时长分布/吞吐(局每小时)/死局打完份额(J1 供给
  审计的锚:死局占挂机 wall-clock ≥15% 预测,<5% 主杠杆失效层降级报表);
- 交叉验证 44 J4「战斗占一半」估算(节点间隔 × 战斗占比近似)。

31 journal 落地前,导航/战斗/空闲的段级分解受限于 ts 粒度(节点级);段级精分解挂 v1。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class RunWallClock:
    """单局 wall-clock 充分统计(ts 粒度=节点级)。"""

    run_id: str
    start: datetime
    end: datetime
    n_nodes: int
    node_intervals: list[float]   # 秒;节点间间隔(战斗+备战+导航混合段)
    final_hp: int

    @property
    def duration_min(self) -> float:
        return (self.end - self.start).total_seconds() / 60.0

    @property
    def dead_run(self) -> bool:
        """死局(局终血 0;「打完」= 照常走到 run 结束 —— 死局打完份额的分子候选)。"""
        return self.final_hp <= 0


def run_wallclock(outcomes_rows: list[dict]) -> list[RunWallClock]:
    """outcomes.jsonl(逐节点 ts)→ 每局 wall-clock 记录。"""
    by_run: dict[str, list[dict]] = {}
    for r in outcomes_rows:
        by_run.setdefault(r.get('run_id', ''), []).append(r)
    out: list[RunWallClock] = []
    for rid, rows in by_run.items():
        rows = sorted((r for r in rows if _parse_ts(r.get('ts', ''))),
                      key=lambda r: r['ts'])
        if len(rows) < 2:
            continue
        ts = [_parse_ts(r['ts']) for r in rows]
        intervals = [(b - a).total_seconds()
                     for a, b in zip(ts, ts[1:], strict=False)   # 相邻对有意短 1
                     if (b - a).total_seconds() > 0]
        out.append(RunWallClock(rid, ts[0], ts[-1], len(rows), intervals,
                                int(rows[-1].get('hp_after') or 0)))
    return out


def throughput_ledger(runs: list[RunWallClock]) -> dict:
    """J0 台账首产:时长分布/吞吐/死局打完份额(J1 锚)+ 44 J4 交叉验证。"""
    if not runs:
        return {'n_runs': 0}
    durs = [r.duration_min for r in runs]
    total_min = sum(durs)
    dead = [r for r in runs if r.dead_run]
    dead_min = sum(r.duration_min for r in dead)
    all_intervals = [i for r in runs for i in r.node_intervals]
    return {
        'n_runs': len(runs),
        'duration_min': {'mean': round(total_min / len(runs), 1),
                         'min': round(min(durs), 1), 'max': round(max(durs), 1)},
        'throughput_runs_per_hour': round(60.0 / (total_min / len(runs)), 2),
        'dead_run_share': {'n': len(dead), 'share_of_runs': round(len(dead) / len(runs), 3),
                           'share_of_wallclock': round(dead_min / total_min, 3)},
        'j1_prediction': '主杠杆成立' if dead_min / total_min >= 0.15
                         else ('临界' if dead_min / total_min >= 0.05 else '主杠杆失效→层降级报表'),
        'node_interval_sec': {'mean': round(sum(all_intervals) / max(1, len(all_intervals)), 1),
                              'n': len(all_intervals)},
        # 44 J4 交叉验证锚:战斗≈间隔的主要成分(节点=备战+战斗+结算),≥60s/节点的间隔
        # 大概率战斗主导段(粗验;44 号 hook 落地后精确分解)
        'long_interval_share': round(
            sum(1 for i in all_intervals if i >= 60) / max(1, len(all_intervals)), 3),
    }


def load_outcomes(replay_dir: Path | str) -> list[dict]:
    """读 outcomes.jsonl(telemetry 三路之一)。"""
    p = Path(replay_dir) / 'outcomes.jsonl'
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
