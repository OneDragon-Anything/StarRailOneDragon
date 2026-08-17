"""03 号 HORIZON 影子离线验证(redesign 消化终态「切流待 V3 离线 A/B」兑现;ADR-0181)。

两件(全离线,不碰游戏):
1. **规模化 sim A/B**:baseline(现状栈骨架)vs DP 姿态策略(get_node_goal 同源映射),
   各 n 局,配对种子族;胜率/位面到达/终局资源;
2. **语料影子 diff**:decisions.jsonl 各回合 state → DP 姿态 NodeGoal vs 现表 NodeGoal
   (get_node_goal 表),分歧率按位面分解 = 切流影响面预估。

用法:uv run python src/sr_od/application/currency_war/cw_shadow_ab.py [--n 200]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sr_od.application.currency_war.cw_horizon import (
    NODES_PER_PLANE,
    _horizon_node_goal,
    _solved,
)
from sr_od.application.currency_war.cw_sim_env import (
    SimEnv,
    baseline_policy,
    run_batch,
)
from sr_od.application.currency_war.cw_state import (
    BuyCard,
    DeployMove,
    LevelUp,
    RefreshShop,
)


def dp_posture_policy(st, env: SimEnv):
    """DP 姿态策略(与 _horizon_node_goal 同源映射;ADR-0168 V3 预演策略的规模化版)。

    姿态 → 动作:level_up=点满到下一级;refresh_budget=D 刷;余金买 target 牌(与 baseline
    同款买/deploy,隔离「节奏差异」变量——两臂只有节奏不同)。"""
    from sr_od.application.currency_war.cw_horizon import clicks_to_level
    t = (min(st.plane, 3) - 1) * NODES_PER_PLANE + min(st.round_num, NODES_PER_PLANE) - 1
    p = _solved().posture(max(0, t), st.gold, st.level, st.hp, env.rb)
    acts = []
    if p.level_up and st.level < 10:
        one = 4
        need = clicks_to_level(st.level)
        if st.gold >= need * one:
            acts = [LevelUp(cost=one) for _ in range(need)]
    for _ in range(p.refresh_budget):
        if st.gold >= 2:
            acts.append(RefreshShop(cost=2))
            break   # sim 两阶段:刷新后重采 shop,本步只发首刷(与 baseline 口径一致)
    for _i, c in enumerate(st.shop):
        if c.name and c.faction == env.target_faction and st.gold >= c.cost:
            acts.append(BuyCard(card=c))
            if len(st.bench) < 8:
                acts.append(DeployMove(bench_idx=len(st.bench), to_row='back', faction=c.faction))
            break
    return acts


def shadow_diff(replay_dir: Path | str, limit: int = 2000) -> dict:
    """语料影子对拍:DP NodeGoal vs 现表 NodeGoal(get_node_goal 表源)分歧率。"""
    from sr_od.application.currency_war.cw_decision_replay import state_from_row
    from sr_od.application.currency_war.cw_economy import get_node_goal

    rows = [json.loads(line) for line in
            Path(replay_dir).joinpath('decisions.jsonl').read_text(encoding='utf-8').splitlines()]
    rows = rows[:limit]
    n = diff = 0
    by_plane: dict[int, dict[str, int]] = {}
    for row in rows:
        st = state_from_row(row)
        try:
            table_goal = get_node_goal(st.plane, st.round_num)
        except Exception:   # noqa: BLE001
            continue
        dp_goal = _horizon_node_goal(st.plane, st.round_num, st.gold, st.level, st.hp)
        if dp_goal is None or table_goal is None:
            continue
        n += 1
        pl = st.plane
        by_plane.setdefault(pl, {'n': 0, 'diff': 0})
        by_plane[pl]['n'] += 1
        # 语义级 diff:目标等级差 >1 或 spend_mode 不同
        if (abs(dp_goal.target_level - table_goal.target_level) > 1
                or dp_goal.spend_mode != table_goal.spend_mode):
            diff += 1
            by_plane[pl]['diff'] += 1
    return {'n': n, 'diff': diff, 'diff_rate': diff / max(1, n), 'by_plane': by_plane}


def main(n: int = 200) -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'== V3 规模化 sim A/B(n={n}/臂,配对种子)==')
    base = run_batch(baseline_policy, n=n, seed0=1000)
    dp = run_batch(dp_posture_policy, n=n, seed0=1000)
    for k in ('survival_rate', 'p3_rate', 'mean_plane', 'mean_level_end', 'mean_gold_end'):
        print(f'{k:>18}: baseline={base[k]:.3f}  dp={dp[k]:.3f}')
    print('\n== 语料影子 diff(DP NodeGoal vs 现表)==')
    sd = shadow_diff('.debug/temp/currency_war/replay')
    print(f"n={sd['n']} diff={sd['diff']} rate={sd['diff_rate']:.1%}")
    for pl, d in sorted(sd['by_plane'].items()):
        print(f"  plane{pl}: {d['diff']}/{d['n']} = {d['diff'] / max(1, d['n']):.1%}")


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=200)
    main(**{'n': ap.parse_args().n})
