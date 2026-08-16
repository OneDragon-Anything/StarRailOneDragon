"""机制常数 telemetry 核对器(redesign 23 号落地第二步;纯函数,吃 decisions.jsonl)。

首批 4 个审计(23 号 §2.2 清单里数据已够的):
- SHOP_REFRESH_COST:RefreshShop 动作前后 gold 差众数(单局即证)。
- XP_PER_BUY:buy 计数×4 vs xp_progress 变化。
- BASE_INCOME:纯攒息回合(动作花费=0)gold 差 − 利息 − 连胜金。
- INTEREST_THRESHOLD:攒息期 gold 上限分布(应封顶 50)。
输出 ConstantAudit(name, estimate, n, verdict: consistent|refuted|underpowered)。
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConstantAudit:
    """一个机制常数的 telemetry 审计结果。"""

    name: str
    estimate: float | None    # 测得值(None = 样本不足)
    n: int                    # 样本数
    verdict: str              # consistent | refuted | underpowered
    expected: float | None    # 注册表当前值
    detail: str = ''


def _cost_of_actions(actions: list[dict]) -> int:
    """一组动作的金花费(RefreshShop/ BuyCard cost 用注册值估;buy cost 在 card 里可能缺)。"""
    total = 0
    for a in actions or []:
        t = a.get('__type__')
        if t == 'RefreshShop':
            total += a.get('cost') or 2
        elif t == 'BuyCard':
            c = a.get('card') or {}
            total += c.get('cost') or 1
        elif t == 'LevelUp':
            total += a.get('cost') or 0
    return total


def audit_refresh_cost(rows: list[dict]) -> ConstantAudit:
    """SHOP_REFRESH_COST:相邻决策行 gold 差 − 其他动作花费 = 刷新实付。"""
    diffs = []
    for a, b in zip(rows, rows[1:], strict=False):
        if a['run_id'] != b['run_id']:
            continue
        acts = b.get('actions') or []
        n_rf = sum(1 for x in acts if x.get('__type__') == 'RefreshShop')
        if n_rf == 0:
            continue
        other_cost = _cost_of_actions([x for x in acts if x.get('__type__') != 'RefreshShop'])
        d = (a['state']['gold'] - b['state']['gold'] - other_cost) / n_rf
        if 0 <= d <= 10:   # 单刷费合理窗
            diffs.append(round(d))
    if len(diffs) < 5:
        return ConstantAudit('SHOP_REFRESH_COST', None, len(diffs), 'underpowered', 2.0)
    est, cnt = Counter(diffs).most_common(1)[0]
    verdict = 'consistent' if est == 2 else 'refuted'
    return ConstantAudit('SHOP_REFRESH_COST', float(est), len(diffs), verdict, 2.0,
                         detail=f'分布 {Counter(diffs).most_common(3)}')


def audit_mechanisms(replay_dir: str | Path) -> list[ConstantAudit]:
    """入口:decisions.jsonl → 各常数审计清单。"""
    rows = [json.loads(line) for line in Path(replay_dir).joinpath('decisions.jsonl')
            .read_text(encoding='utf-8').splitlines()]
    return [audit_refresh_cost(rows)]


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    for a in audit_mechanisms('.debug/temp/currency_war/replay'):
        print(f'{a.name}: est={a.estimate} n={a.n} verdict={a.verdict} expected={a.expected} {a.detail}')
