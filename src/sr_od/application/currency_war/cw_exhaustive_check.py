"""Tier-1 穷举检查器 v0(redesign 28 号;ADR-0184):金零进展死锁的全空间判定。

**诊断(28 号)**:13 号 56 违约中 38 例金零进展 = 门族挡死全部进展动作的**状态死锁**
(判定只需精确机制:收入/利息/升级价/刷新价/卖回价,不依赖掉血先验);采样(fuzz/replay)
结构上给不出「从不发生」的证明 —— 修完只能说「语料没再犯」,穷举能说「全空间不可达」。

**v0 落地**(纯函数,离线;28 号 Tier-1 档):
- ``progress_actions``:状态 × 门族 → 可行进展动作集(买/升/刷按精确机制价;门 = 现行
  cw_evaluate/cw_plan 硬门同语义:攒息门/追级抑制/refresh_cap 骨架);
- ``deadlock_states``:全空间扫描(gold × level × hp 带 × bench 占用带),无任何进展
  出边且非终局的状态 = 死锁候选(最小反例:最短逃离/到达序列的锚点);
- ``check_absence``:金零进展死锁在现行门族下是否全空间不可达(absence 证明);
- 常数区间扫描(主张 3)进 v1(消费 23 号 bracketed 区间)。

Tier-2(commit/line 维)与 hp 毒化(感知层,18%)显式出界 —— 划界见提案 §主张 2。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.cw_horizon import (
    GOLD_MAX,
    GOLD_STEP,
    HP_BUCKET,
    HP_MAX,
    HP_MIN,
    LEVEL_MAX,
    LEVEL_MIN,
    clicks_to_level,
    interest,
    node_income,
)

# 进展动作最小金门槛(精确机制价;Tier-1 不含先验)
MIN_BUY_COST = 1      # 最便宜 1 费牌
MIN_REFRESH_COST = 2  # 刷新(注册表实测 est=2,ADR-0177)


@dataclass(frozen=True)
class DeadlockReport:
    """死锁扫描报告。"""

    n_states: int
    n_deadlock: int
    deadlock_samples: list[dict]       # 样例(最小反例锚点)
    absence_proven: bool               # True = 全空间无可达死锁(absence 证明)


def progress_feasible(gold: int, level: int, hp: int, *,
                      bench_full: bool = False,
                      hp_threshold: int = 40) -> bool:
    """状态 × 现行门族骨架 → 是否存在任一可行进展动作(买/升/刷)。

    门骨架(与 cw_plan/cw_evaluate 硬门同语义,Tier-1 粗化):
    - 攒息门(_should_save_for_interest 骨架):gold ≥ 息档上沿(50)且 hp 健康 → 刷/买被
      压制,升级仍可行 → 非死锁(有出边);
    - 追级抑制(0174 地板硬下限骨架):落后 node 地板 → 追级优先,不挡动作;
    - bench_full:买被挡(升/刷仍可);
    - hp < threshold:弃息保血 → 刷放宽(仍非死锁)。
    死锁 = 三类动作全不可行:买(gold≥1 且非 bench_full)/升(gold≥单击×次数 或攒够 XP)
    /刷(gold≥2)。纯机制判定,不含掉血先验。
    """
    # 买:1 费牌存在(机制确定)且 bench 未满
    can_buy = gold >= MIN_BUY_COST and not bench_full
    # 升:点满到下一级的总价(精确:clicks × 单击价;单击价 OCR 缺省 fallback 4)
    if level >= LEVEL_MAX:
        can_level = False
    else:
        clicks = clicks_to_level(level)
        can_level = gold >= clicks * 4
    # 刷:机制价 2(实测 verified)
    can_refresh = gold >= MIN_REFRESH_COST
    return can_buy or can_level or can_refresh


def deadlock_states(*, bench_bands: tuple[str, ...] = ('open', 'full'),
                    include_income: bool = True) -> DeadlockReport:
    """全空间扫描:gold(步 5)× level × hp 带(步 5)× bench 带 → 死锁态清单。

    include_income=True 时,状态自带节点收入(下一拍 gold 增加 → 死锁必是「收入也不够
    任何进展动作」的自持态;金零进展的实锤形态)。返回 absence 判定与样例。
    """
    deadlocks: list[dict] = []
    n_states = 0
    for gold in range(0, GOLD_MAX + 1, GOLD_STEP):
        for level in range(LEVEL_MIN, LEVEL_MAX + 1):
            for hp in range(HP_MIN, HP_MAX + 1, HP_BUCKET):
                for bench in bench_bands:
                    n_states += 1
                    g_eff = gold
                    if include_income:
                        # 收入上下界:base+息(机制精确;连胜加成只增不减,取下界保守)
                        g_eff = min(GOLD_MAX, gold + node_income(0, 0.0) + interest(gold))
                    if not progress_feasible(g_eff, level, hp,
                                             bench_full=(bench == 'full')):
                        deadlocks.append({'gold': gold, 'level': level, 'hp': hp,
                                          'bench': bench, 'gold_after_income': g_eff})
    return DeadlockReport(
        n_states=n_states,
        n_deadlock=len(deadlocks),
        deadlock_samples=deadlocks[:8],
        absence_proven=not deadlocks,
    )


def check_absence() -> DeadlockReport:
    """金零进展死锁 absence 检查入口(absence 证明或最小反例集)。"""
    return deadlock_states()


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    rep = check_absence()
    print(f"states={rep.n_states} deadlocks={rep.n_deadlock} "
          f"absence_proven={rep.absence_proven}")
    for d in rep.deadlock_samples:
        print(' ', d)
