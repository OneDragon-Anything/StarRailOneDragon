"""影子价格总线 v0(redesign 35 号;ADR-0188):DP 值差分提取 + 兑换环无套利审计。

**诊断(35 号)**:全栈 10 个定价点、≥4 种定价哲学(跨期求解/手写权重/期望值/分布感知),
零对账机制——同一次「买 vs 攒 vs 升」决策里各点用各自为政的汇率相遇。
INTEREST_WEIGHT 2→4 手调 = 未对账汇率调整的化石(下游 06/07 未跟随)。

**v0 落地**(纯函数,离线):
- ``shadow_price``:锚定状态 × 资源 → 边际价(value_fn 差分注入——生产用 cw_horizon
  值函数,测试用 mock;DP 解一次后查表便宜);
- ``anchor_states``:分层代表状态集(位面 × 节点 × 金档 × HP 档 × 等级档);
- ``arb_cycle_buy_sell``:H2 兑换环——买→卖回环积 refund/cost(应 ≤1,亏手续费=合理带;
  >1 = 系统性漏价值报警);gold→refresh→card 期望环挂 16 号(消费端批次);
- ``price_shape_contracts``:H3 形状合约——gold 边际效用递减 / HP 价三区对齐 18 号
  (进 13 号 CI 的合约族候选,v0 输出布尔报告)。

J1 注入回收(测试):注入已知错价(环积 >1)→ 检出;健康价 → 零误报。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

# 资源维:v0 三资源(金/HP/等级)——卡/槽/刷新挂消费端批次
RESOURCES = ('gold', 'hp', 'level')


@dataclass(frozen=True)
class AnchorState:
    """锚定状态(分层代表;值函数查询键)。"""

    t: int          # 节点序(0-26)
    gold: int
    level: int
    hp: int

    def key(self) -> tuple:
        return (self.t, self.gold, self.level, self.hp)


def anchor_states(n_per_band: int = 3) -> list[AnchorState]:
    """分层代表状态集(35 号 §3.1:~10² 量级;v0 取 27 态代表网格)。

    分层:3 位面段(节点 4/13/22)× 金档(10/30/60)× HP 档(20/50/80)× 等级(4/7)。
    """
    out = []
    for t in (4, 13, 22):
        for gold in (10, 30, 60):
            for hp in (20, 50, 80):
                for level in (4, 7):
                    out.append(AnchorState(t, gold, level, hp))
                    if len([a for a in out if a.t == t]) >= n_per_band * 9:
                        break
    return out


def shadow_price(state: AnchorState, resource: str,
                 value_fn: Callable[[int, int, int, int], float],
                 delta: int | None = None) -> float:
    """锚定状态 × 资源 → 边际价 V(s+δ)−V(s)。

    value_fn(t, gold, level, hp) → float(注入;生产 = cw_horizon 解的 posture().v)。
    δ 默认:gold=5(格)/hp=5(桶)/level=1。
    """
    d = delta or {'gold': 5, 'hp': 5, 'level': 1}[resource]
    base = value_fn(state.t, state.gold, state.level, state.hp)
    if resource == 'gold':
        alt = value_fn(state.t, min(110, state.gold + d), state.level, state.hp)
    elif resource == 'hp':
        alt = value_fn(state.t, state.gold, state.level, min(100, state.hp + d))
    else:
        alt = value_fn(state.t, state.gold, min(10, state.level + d), state.hp)
    return alt - base


def price_matrix(states: list[AnchorState],
                 value_fn: Callable[[int, int, int, int], float]) -> dict:
    """锚定集 × 资源 → 价格矩阵(报告形态)。"""
    out: dict[tuple, dict[str, float]] = {}
    for s in states:
        out[s.key()] = {r: round(shadow_price(s, r, value_fn), 4) for r in RESOURCES}
    return out


def arb_cycle_buy_sell(cost: int, star: int, *, fee_tolerance: int = 1) -> dict:
    """H2 兑换环:gold→card(买)→gold(卖回)。环积 = refund/cost。

    机制精确(ADR-0111/0121):1 星全额退(环积 1.0=无损循环,手续费 0);≥2 费 2★+ 亏 1。
    报警条件:环积 > 1 + fee_tolerance/cost(系统性正反馈 = 价值生成器 bug)。
    """
    from sr_od.application.currency_war.cw_state import sell_refund
    refund = sell_refund(star, cost)
    cycle = refund / max(1, cost)
    tol = 1 + fee_tolerance / max(1, cost)
    return {'cycle_ratio': round(cycle, 4), 'tolerance': round(tol, 4),
            'verdict': 'arb' if cycle > tol else 'ok'}


def price_shape_contracts(matrix: dict) -> dict:
    """H3 形状合约(布尔报告;进 13 号 CI 候选):
    - gold 递减:同状态其余维固定,gold 档走高 → gold 边际价不升(抽样代表对);
    - hp 三区:低血档 hp 价 > 高血档(与 18 号 λ_hp 峰形定性对齐)。
    """
    gold_violations = 0
    hp_violations = 0
    n_pair = 0
    keys = sorted(matrix)
    for k in keys:
        t, gold, lv, hp = k
        # gold 递减对:(同 t/lv/hp,gold 10 vs 60)
        k_hi = (t, 60, lv, hp)
        if gold == 10 and k_hi in matrix:
            n_pair += 1
            if matrix[k_hi]['gold'] > matrix[k]['gold'] + 1e-9:
                gold_violations += 1
        # hp 三区对:(同 t/lv/gold,hp 20 vs 80)
        k_hi_hp = (t, gold, lv, 80)
        if hp == 20 and k_hi_hp in matrix:
            if matrix[k]['hp'] < matrix[k_hi_hp]['hp'] - 1e-9:
                hp_violations += 1
    return {'n_gold_pairs': n_pair, 'gold_monotone_violations': gold_violations,
            'hp_zone_violations': hp_violations,
            'verdict': 'pass' if gold_violations == 0 and hp_violations == 0 else 'fail'}
