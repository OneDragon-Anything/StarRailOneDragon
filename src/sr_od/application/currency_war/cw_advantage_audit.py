"""决策级优势审计 v0(redesign 42 号;ADR-0182):影子分歧 × 真实结果的两层计量。

**诊断(42 号)**:切流证据 = run 级 A/B(~50 局/比较);每局几十个决策点只用了 1 bit 胜负。
「影子说的更好,结果上到底好不好」从未被计算 —— 影子 diff 在产生但从未对答案。

**v0 落地**(纯函数,离线;42 号 §2 的 T2 路线 + 覆盖记账):
- ``advantage_one_step``:T2 值函数一步差——A = [r(s,a_alt)+V(s'_alt)] − [r+V(s')](V 用 18 号
  p_win_projection 换算;40 号保真度分区当计分门,v0 用位面档近似);
- ``audit_decision_class``:决策类 × 状态桶聚合(均值优势 ± 简单 CI,白噪地板);
- ``CoverageLedger``:格子级覆盖记账(n_diff/n_scored/不可测原因显式路由 → 39/29 需求单);
- J0 注入恢复(测试):已知劣化决策类的正优势恢复 + 未劣化 ≈0。

T1(自然变异条件化)为 v1(需状态指纹分桶 × 多臂语料);v0 的 T2 已可对 13 号 38 例金零进展
做结果侧标定(J1,消费端批次)。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_first_passage import p_win_projection
from sr_od.application.currency_war.cw_state import simulate


@dataclass(frozen=True)
class DecisionPoint:
    """一个被审计的决策点(live 实选 vs 影子备选)。"""

    run_id: str
    round_num: int
    decision_class: str        # 决策类:refresh_cap / level_gate / deploy / sell / ...
    plane: int = 1
    level: int = 1
    hp: int = 100
    gold: int = 0
    live_action: object = None     # 实选 Action
    shadow_action: object = None   # 影子备选 Action(决策类不同语义)


def _bucket(dp: DecisionPoint) -> str:
    lv = 'early' if dp.level <= 5 else ('mid' if dp.level <= 8 else 'late')
    return f'{dp.decision_class}|p{dp.plane}|{lv}'


def advantage_one_step(dp: DecisionPoint, state, nodes_left: int = 6) -> float | None:
    """T2 值函数一步差:A = [V(做影子备选后)] − [V(实际后继)],V = P(win) 生存换算。

    live_action=None 语义 = 现状不动作(「该做没做」类劣化的自然对照);shadow=None = 无
    备选可评(不可计分)。两侧各 simulate 一步(不动作 = 原状态),掉血差经 hp 差进 P(win);
    金差暂不进 V(v0 生存单目标;经济多维进 v1 消费 35 号价格)。
    simulate 异常 → None(该点不可计分,显式,非静默 0)。
    """
    if dp.shadow_action is None:
        return None
    try:
        s_live = simulate(state, dp.live_action) if dp.live_action is not None else state
        s_alt = simulate(state, dp.shadow_action)
    except Exception:   # noqa: BLE001  simulate 失败 = 该点不可计分(显式,非静默 0)
        return None
    v_live = p_win_projection(s_live.level, max(1, s_live.hp), nodes_left, plane=s_live.plane)
    v_alt = p_win_projection(s_alt.level, max(1, s_alt.hp), nodes_left, plane=s_alt.plane)
    return v_alt - v_live


@dataclass
class ClassStat:
    """决策类 × 状态桶聚合。"""

    n_points: int = 0
    n_scored: int = 0
    advantages: list[float] = field(default_factory=list)

    @property
    def mean(self) -> float:
        return sum(self.advantages) / len(self.advantages) if self.advantages else 0.0

    @property
    def ci_half(self) -> float:
        """简单 95% CI 半宽(正态近似;优势近似有界,小样本保守够用)。"""
        if len(self.advantages) < 2:
            return float('inf')
        m = self.mean
        var = sum((a - m) ** 2 for a in self.advantages) / (len(self.advantages) - 1)
        return 1.96 * math.sqrt(var / len(self.advantages))


def audit_decision_class(points: list[DecisionPoint],
                         states: list | None = None,
                         noise_floor: float = 0.005) -> dict[str, dict]:
    """聚合:决策类 × 桶 → {mean, ci, n, verdict}。verdict:

    positive(影子显著更优,CI 下界 > 地板)/ negative(实选显著更优)/ noise(地板内,
    无证据)/ uncovered(可计分点 < 5)。"""
    out: dict[str, dict] = {}
    by_bucket: dict[str, ClassStat] = {}
    for i, dp in enumerate(points):
        st = ClassStat()
        key = _bucket(dp)
        by_bucket.setdefault(key, st)
        st.n_points += 1
        adv = advantage_one_step(dp, states[i] if states else None)
        if adv is not None:
            by_bucket[key].n_scored += 1
            by_bucket[key].advantages.append(adv)
    for key, st in by_bucket.items():
        if st.n_scored < 5:
            out[key] = {'n_points': st.n_points, 'n_scored': st.n_scored,
                        'verdict': 'uncovered', 'mean': 0.0}
            continue
        m, c = st.mean, st.ci_half
        if m - c > noise_floor:
            v = 'positive'
        elif m + c < -noise_floor:
            v = 'negative'
        else:
            v = 'noise'
        out[key] = {'n_points': st.n_points, 'n_scored': st.n_scored,
                    'mean': round(m, 5), 'ci_half': round(c, 5), 'verdict': v}
    return out


@dataclass
class CoverageCell:
    """覆盖记账一格(42 号 §2.3:不可测是一等输出)。"""

    n_diff: int = 0          # 该格总决策点数
    n_scored: int = 0        # 成功计分数
    reasons_unscorable: dict[str, int] = field(default_factory=dict)   # 原因 → 计数


class CoverageLedger:
    """格子级覆盖记账:证据缺口地图(→ 39 探针 / 29 实验需求单)。"""

    def __init__(self) -> None:
        self.cells: dict[str, CoverageCell] = {}

    def record(self, dp: DecisionPoint, scored: bool, reason: str = '') -> None:
        c = self.cells.setdefault(_bucket(dp), CoverageCell())
        c.n_diff += 1
        if scored:
            c.n_scored += 1
        elif reason:
            c.reasons_unscorable[reason] = c.reasons_unscorable.get(reason, 0) + 1

    def gap_map(self) -> dict[str, dict]:
        """证据缺口地图:uncovered 格子按不可测原因显式路由。"""
        out: dict[str, dict] = {}
        for key, c in self.cells.items():
            coverage = c.n_scored / max(1, c.n_diff)
            d: dict = {'n_diff': c.n_diff, 'n_scored': c.n_scored,
                       'coverage': round(coverage, 3)}
            if c.reasons_unscorable:
                d['unscorable_reasons'] = dict(c.reasons_unscorable)
                # 路由:no_shadow → 39 探针候选(要影子输出需重放);sim_untrusted → 40 dark 合流
                routes = []
                if 'no_shadow' in c.reasons_unscorable:
                    routes.append('probe@39(影子重放/实验局)')
                if 'sim_untrusted' in c.reasons_unscorable:
                    routes.append('dark@40(模型不可信合流)')
                if 'no_variation' in c.reasons_unscorable:
                    routes.append('experiment@29(需强制臂局)')
                d['routes'] = routes
            out[key] = d
        return out
