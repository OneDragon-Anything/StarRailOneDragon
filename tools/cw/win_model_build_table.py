"""win_model M1 训练表构建(ADR 草稿 §2):outcomes × decisions join。

本文件用途:把 replay 语料的战斗结算行(outcomes.jsonl,killed 已知的
battle/遭遇/boss 行)与同 run_id 的**最近战前** decisions 帧join 成
训练表 jsonl(每行 = 特征 dict + killed + run_id + round_num + node_type),
并实测 join 覆盖率(成功数 / 失败原因分类)。**只读 replay 语料,不写**。

运行命令(仓库根):
    $env:PYTHONPATH='src'; uv run python tools/cw/win_model_build_table.py
输出:``.debug/temp/currency_war/cw_dev/win_model_design/train_table.jsonl``
(gitignored 区,合法)。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from sr_od.application.currency_war.cw_win_features import features_from_deployed

REPLAY_DIR = Path('.debug/temp/currency_war/replay')
OUT_PATH = Path('.debug/temp/currency_war/cw_dev/win_model_design/train_table.jsonl')
BATTLE_NODE_TYPES = ('普通战斗', '遭遇', 'boss')


def _iter_jsonl(path: Path):
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def build(outcomes_path: Path, decisions_path: Path, out_path: Path) -> dict:
    """join 并落盘训练表,返回覆盖率统计 dict。"""
    # decisions 按 run_id 聚合,保持文件行序(后行=更晚帧)
    frames_by_run: dict[str, list[dict]] = {}
    for row in _iter_jsonl(decisions_path):
        frames_by_run.setdefault(row.get('run_id') or '', []).append(row)

    reasons: Counter[str] = Counter()
    n_battle = n_label = n_joined = n_neg = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as out:
        for o in _iter_jsonl(outcomes_path):
            if (o.get('node_type') or '') not in BATTLE_NODE_TYPES:
                continue
            n_battle += 1
            killed = o.get('killed')
            if not isinstance(killed, bool):
                # 语料里 killed 缺失形态 = null / 空串 / 缺键(实测三种并存)
                reasons['label_unknown_killed'] += 1
                continue
            n_label += 1
            run_id = o.get('run_id') or ''
            rnd = o.get('round_num')
            frames = frames_by_run.get(run_id)
            if not frames:
                reasons['no_decisions_for_run'] += 1
                continue
            # 最近战前帧:优先同 round_num 的最后一帧;否则 round_num 小于
            # 结算轮的最后一帧(与 board_before「最近战前观察」同口径)
            cand = [f for f in frames if f.get('round_num') == rnd]
            fallback = False
            if not cand:
                cand = [f for f in frames
                        if isinstance(f.get('round_num'), int)
                        and isinstance(rnd, int) and f['round_num'] < rnd]
                fallback = True
            if not cand:
                reasons['no_pre_battle_frame'] += 1
                continue
            frame = cand[-1]
            deployed = (frame.get('state') or {}).get('deployed') or []
            if not deployed:
                reasons['empty_deployed'] += 1
                # 空板仍是合法弱阵容样本,保留进表
            feats = features_from_deployed(deployed)
            n_joined += 1
            n_neg += 0 if killed else 1
            out.write(json.dumps({
                **feats,
                'killed': killed,
                'run_id': run_id,
                'round_num': rnd,
                'node_type': o.get('node_type'),
                'join_fallback_round': fallback,
            }, ensure_ascii=False) + '\n')

    return {
        'battle_rows_total': n_battle,
        'label_known': n_label,
        'joined': n_joined,
        'negative(killed=false)': n_neg,
        'negative_ratio': round(n_neg / n_joined, 4) if n_joined else None,
        'failure_reasons': dict(reasons),
    }


if __name__ == '__main__':
    stats = build(REPLAY_DIR / 'outcomes.jsonl',
                  REPLAY_DIR / 'decisions.jsonl', OUT_PATH)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f'written: {OUT_PATH}')
