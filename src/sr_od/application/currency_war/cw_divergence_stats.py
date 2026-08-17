"""分歧频率统计器 v0(redesign 12 号预备;消费 decisions.jsonl 的 dp_posture 影子)。

12 号触发门 = 候选分歧度 × 不可逆度 × 注意力预算;其中「候选分歧」的数据源
= candidate_scores top-2 分差(r6 补齐)+ 影子 DP 姿态 vs 生产姿态差(本模块)。
问询卡/热键应答/GUI 挂实机批;本模块先积累**分歧频率分布**(下局起有语料)。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

DEFAULT_REPLAY = Path('.debug/temp/currency_war/replay')


def divergence_stats(replay_dir: Path | str = DEFAULT_REPLAY,
                     run_id: str | None = None) -> dict:
    """统计 decisions.jsonl 的分歧信号分布(12 号触发门的语料基础)。

    返回:{runs, decisions_total, with_candidates, close_calls(gap<0.10),
    with_dp_posture, dp_modes Counter, per_run: {run_id: close_call 轮次列表}}
    """
    p = Path(replay_dir) / 'decisions.jsonl'
    if not p.exists():
        return {'runs': 0, 'decisions_total': 0}
    total = close = with_cand = with_dp = 0
    modes: Counter[str] = Counter()
    per_run: dict[str, list[int]] = {}
    for line in p.open(encoding='utf-8'):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if run_id is not None and d.get('run_id') != run_id:
            continue
        total += 1
        scores = d.get('candidate_scores') or {}
        if len(scores) >= 2:
            with_cand += 1
            srt = sorted(scores.values(), reverse=True)
            if srt[0] - srt[1] < 0.10:
                close += 1
                per_run.setdefault(d.get('run_id', '?'), []).append(d.get('round_num', 0))
        dp = d.get('dp_posture') or {}
        if dp:
            with_dp += 1
            modes[dp.get('spend_mode', '?')] += 1
    return {'runs': len(per_run) or (1 if total else 0),
            'decisions_total': total, 'with_candidates': with_cand,
            'close_calls': close, 'with_dp_posture': with_dp,
            'dp_modes': dict(modes), 'per_run': per_run}
