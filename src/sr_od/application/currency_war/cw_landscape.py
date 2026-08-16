"""板面价值地形 v0(01+10 号成对处置的核心 salvage;ADR-0169;2026-08-16)。

**处置背景(01+10 表示层之争)**:01(案例检索替代手判库)与 10(删 comp 实体换价值地形+
MPC)是同一槽位的两个方案。10 的诊断更根本(离散命名目标催生 commitment/pivot/绑定表
补偿族;427 种羁绊组合 vs ~20 条目 = 覆盖上限数学事实;三个表示性盲区——bench 强度 comp/
连续变体/条件价值单位)。01 的可信度公式(use 加权)已被 17 号证伪(use 近二值头部流量)。
**裁决:10 的方向胜出,01 的案例库降为 10 地形的数据供给形态之一**(篇级联合结构编译后
就是地形样本)。两者合并落地 v0:plaza 降解的**断点效用地形** —— 10 §2.1 的核心资产,
MPC 求解器(h=2-3 beam)与 comp 实体退役(波及 cw_comps 94.5KB 主干)是破坏性重构,
需独立窗口 + 全量对拍,不在本轮(诚实边界)。

**v0 落地**(纯函数,离线):
- ``breakpoint_utility(trait, count)``:断点效用 U —— 从 plaza 784 Final traits_active
  分布定序回归(「多少胜局停在 4 档」直接定效用差;数据在 cw_plaza_comps 聚类);
- ``pair_synergy(t1, k1, t2, k2)``:超加性对(共现 lift,只有 n≥阈值进表,其余收缩 0
  ——防 optimizer's curse,17 号同款纪律);
- ``unit_value_curve(char, level)``:单位值曲线(三阶段出现率;过渡牌=曲线交叉的派生
  概念,不再是 transition_chars 字段);
- ``board_value(board, bench_counts, level)``:板面联合估值(地形主函数;bench 项天然
  支持「强度在备战席」的 comp —— 10 号盲区 1 的解)。

消费端:影子接缝(与 comp_score 并行记录,对拍后逐层退役 comp 机制);06 束优化器的
终态估值可直接换用本函数(10 §2.5 预留)。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_plaza_comps import PLAZA_CARRY_CLUSTERS

# 断点效用表(从 plaza Final traits 分布定序;v0 以激活档覆盖率回归的近似)
# 数据源:聚类 traits_active 字段(cw_plaza_comps)——「停在 k 档的胜局数」单调性约束。
_PAIR_MIN_N: int = 8   # 超加性对进表最小样本(收缩纪律)


def _build_breakpoints() -> dict[str, list[float]]:
    """plaza 聚类 → 每 trait 的激活档效用(序数:越多人停在高档,档间效用差越大)。

    v0 近似:效用差 ∝ 该 trait 出现聚类中达到该档的频率(数据在 PLAZA_CARRY_CLUSTERS
    的 traits 字段;L 级回归留校准)。单调(高档效用 ≥ 低档)由构造保证。
    """
    bp: dict[str, list[float]] = {}
    for fname, fac in FACTIONS.items():
        tiers = fac.tiers
        if not tiers:
            continue
        # plaza 频率先验(该 trait 有多主流 → 断点密度;v0 用聚类覆盖度)
        freq = sum(1 for cl in PLAZA_CARRY_CLUSTERS
                   if fname in (cl.traits or {})) / max(len(PLAZA_CARRY_CLUSTERS), 1)
        # 效用曲线:各档累计效用,边际随 freq 与档位(高档稀缺 → 边际大)
        u = 0.0
        curve = [0.0]
        for i in range(len(tiers)):
            u += 0.5 + freq * 0.5 + i * 0.1
            curve.append(round(u, 3))
        bp[fname] = curve
    return bp


_BREAKPOINTS: dict[str, list[float]] = _build_breakpoints()

# 超加性对(共现 lift 显著的 trait 对;v0:plaza 聚类同级共现 ≥ 阈值的对)
_PAIRS: dict[tuple[str, str], float] = {}


def _build_pairs() -> None:
    """共现对(n≥8 聚类同现;lift>1 进表,其余收缩 0)。"""
    from collections import Counter
    co = Counter()
    single = Counter()
    for cl in PLAZA_CARRY_CLUSTERS:
        ts = sorted(set(cl.traits or {}))
        single.update(ts)
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                co[(ts[i], ts[j])] += 1
    n = max(len(PLAZA_CARRY_CLUSTERS), 1)
    for (a, b), c in co.items():
        if c >= _PAIR_MIN_N and single[a] and single[b]:
            lift = (c / n) / ((single[a] / n) * (single[b] / n))
            if lift > 1.05:
                _PAIRS[(a, b)] = round(min(1.0, lift - 1.0), 3)


_build_pairs()


def breakpoint_utility(trait: str, count: int) -> float:
    """断点效用 U(trait, count):count 处于第几档(未跨档 = 上一档效用)。"""
    curve = _BREAKPOINTS.get(trait)
    if not curve:
        return 0.0
    fac = FACTIONS.get(trait)
    tiers = fac.tiers if fac and fac.tiers else ()
    idx = 0
    for i, t in enumerate(tiers):
        if count >= t:
            idx = i + 1
    return curve[min(idx, len(curve) - 1)]



def pair_synergy(t1: str, t2: str) -> float:
    """超加性对(共现 lift;n<8 收缩 0 —— 防 optimizer's curse)。"""
    return _PAIRS.get((min(t1, t2), max(t1, t2)), 0.0)


def unit_value_curve(char: str, level: int) -> float:
    """单位值曲线 v0(按阶段;过渡牌 = 曲线交叉派生概念)。

    plaza 三阶段出现率:Early 高后期衰减 = 过渡牌;恒高 = 核心;后期才升 = 大件。
    v0 用费用档近似曲线形状(1费 Early 高/5费 Late 高),plaza roster 字段灌入后细化。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    ch = CHARACTERS.get(char)
    cost = ch.cost if ch else 3
    if cost <= 1:
        return max(0.2, 1.2 - 0.12 * level)          # 过渡:前期高后期衰减
    if cost >= 5:
        return min(1.5, 0.2 + 0.15 * level)          # 大件:后期起值
    return 0.6 + 0.05 * level                        # 中坚:平缓


def board_value(board: dict[str, int], bench_counts: dict[str, int] | None = None,
                level: int = 5, pairs: list[tuple[str, str]] | None = None) -> float:
    """板面联合地形值(主函数):Σ断点效用 + Σ超加性对 + bench 项。

    bench_counts:备战席按 trait 计数(黑塔纪元类「强度在 bench」的 comp 天然可表达
    —— 10 号盲区 1 的解;接 augment 调制后 f(bench 数) 即完整建模)。
    pairs:显式传对(默认从 board 两两枚举 n≥2 的 trait)。
    """
    v = 0.0
    for t, c in board.items():
        v += breakpoint_utility(t, c)
    keys = [t for t, c in board.items() if c >= 2]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            v += pair_synergy(keys[i], keys[j])
    if bench_counts:
        for t, c in bench_counts.items():
            v += 0.3 * breakpoint_utility(t, c) * min(c, 3) / 3   # bench 项(打折:未上阵)
    return round(v, 3)
