"""损失预算引擎 v0(redesign 34 号;ADR-0190):四差距分解 + 可达域地板上界。

**诊断(34 号)**:33 轮各自论证「gap 存在」,零尺寸测量;四套审计量纲不通约(置信度/
违约数/悔恨值/失败率),没换算成同一货币「各值多少 pp 胜率」;A8 可达上限没人知道——
终点线不存在。

**v0 落地**(sim 内,全离线;34 号 §2 的 A/C/D 三臂——B 揭示臂在 sim 内天然免费,
真局版挂实机批次):
- ``loss_budget``:配对种子族跑 A(as-played 基线)vs C(DP 姿态接管)vs D(C+揭示
  姿态参数),四桶:决策差=C−A、地板=1−P(win|D)、跨种子配对差分;
- ``budget_report``:headroom 表(pp 量纲 + 配对符号检验 p 值粗估);
- 诚实边界(0181 同款):sim-relative——DP 与 sim 共享物理原语,绝对地板是上界;
  40 号保真度分区落地后按区分级。

E 臂(执行修复,真局限)不立项(45 号 J1 已证死局份额 0%——执行差在当前语料无测量面)。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from sr_od.application.currency_war.cw_sim_env import SimEnv, baseline_policy


def _dp_policy_factory():
    """C/D 臂策略 = DP 姿态(0181 A/B 同款,与 _horizon_node_goal 同源映射)。"""
    from sr_od.application.currency_war.cw_horizon import (
        NODES_PER_PLANE,
        _solved,
        clicks_to_level,
    )
    from sr_od.application.currency_war.cw_state import (
        BuyCard,
        DeployMove,
        LevelUp,
        RefreshShop,
    )

    def dp_posture_policy(st, env: SimEnv):
        t = (min(st.plane, 3) - 1) * NODES_PER_PLANE + min(st.round_num, NODES_PER_PLANE) - 1
        p = _solved().posture(max(0, t), st.gold, st.level, st.hp, env.rb)
        acts = []
        if p.level_up and st.level < 10:
            need = clicks_to_level(st.level)
            if st.gold >= need * 4:
                acts = [LevelUp(cost=4) for _ in range(need)]
        for _ in range(p.refresh_budget):
            if st.gold >= 2:
                acts.append(RefreshShop(cost=2))
                break
        for _i, c in enumerate(st.shop):
            if c.name and c.faction == env.target_faction and st.gold >= c.cost:
                acts.append(BuyCard(card=c))
                if len(st.bench) < 8:
                    acts.append(DeployMove(bench_idx=len(st.bench), to_row='back',
                                           faction=c.faction))
                break
        return acts
    return dp_posture_policy


@dataclass
class BudgetReport:
    """四差距预算表(sim-relative)。"""

    n: int
    win_a: float            # as-played 基线
    win_c: float            # DP 接管(决策差)
    decision_gap: float     # C − A(pp)
    floor_upper: float      # 1 − P(win|D)(%);sim 内 D=C(揭示免费)→ 与 C 同
    actionable_upper: float # D − A(主数字)
    sign_test_p: float      # 配对符号检验(二项,粗估)


def _sign_test(wins_a: list[bool], wins_c: list[bool]) -> float:
    """配对符号检验 p 值(双尾二项;只有分歧行计入)。"""
    disc = [(a, c) for a, c in zip(wins_a, wins_c, strict=True) if a != c]
    n = len(disc)
    if n == 0:
        return 1.0
    k = sum(1 for a, c in disc if c and not a)
    # 双尾:两侧概率和
    p = sum(math.comb(n, i) for i in range(min(k, n - k) + 1)) / 2 ** n * 2
    return min(1.0, p)


def loss_budget(n: int = 100, seed0: int = 2000) -> BudgetReport:
    """四臂配对(A vs C/D)重放:同种子族两臂(消除开局方差),产出预算表。"""
    dp_policy = _dp_policy_factory()
    wins_a, wins_c = [], []
    for i in range(n):
        a = SimEnv(seed0 + i).run(baseline_policy)
        c = SimEnv(seed0 + i).run(dp_policy)
        wins_a.append(a.survived)
        wins_c.append(c.survived)
    win_a = sum(wins_a) / n
    win_c = sum(wins_c) / n
    return BudgetReport(
        n=n, win_a=win_a, win_c=win_c,
        decision_gap=round(win_c - win_a, 4),
        floor_upper=round(1.0 - win_c, 4),
        actionable_upper=round(win_c - win_a, 4),
        sign_test_p=round(_sign_test(wins_a, wins_c), 4),
    )


if __name__ == '__main__':
    import json
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    rep = loss_budget(n=100)
    print(json.dumps(rep.__dict__, ensure_ascii=False, indent=1))
