"""或有契约定价台 v0(redesign 33 号;ADR-0193):结构化契约 + 三层定价(层 1/2)。

**诊断(33 号)**:游戏内「接受即生效的状态化 offer」(祈愿试炼/嘴硬/伟大征服/诅咒圣杯)
从「PICK_VALUE 静态分+naive 第一张」定价——价格不含 offer 对后续打法的扭曲、不含结果
条件流、不含违约态。代码实锤:EconomyEffect 把或有流压平成即时值(嘴硬只建 instant_gold=6,
切断「败→+5HP 保连胜」条件)。

**v0 落地**(纯函数,离线;33 号 C1+C2 层 1/2):
- ``Contract``:结构化工具字段(接受成本/或有流[条件+支付]/行为义务[谓词+计数]/诅咒
  [deadline+惩罚]/门控);
- ``price_contract``:层 1 经济流折算 + 层 2 结果条件流卷积(胜率/λ_hp 来自 18 号核);
- ``curse_deadline_floor``:诅咒截止点反解(剩余节点×完成速率);
- 层 3(行为义务 DP 影子重解 ΔV)挂消费批次(cw_horizon 重解一次的接缝已备)。

J1(测试):伟大征服连胜引擎局 vs 弱板局方向反转/嘴硬 streak≥2 转正/诅咒截止点落
「3-4 后别接」区间。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.cw_first_passage import (
    board_tier_of,
    p_win_lambda,
    p_win_projection,
)


@dataclass(frozen=True)
class ContingentFlow:
    """或有支付:条件触发才付。"""

    condition: str      # 'lose' | 'win' | 'streak_ge:2' | 'node_ge:3' ...
    pay_gold: float = 0.0
    pay_hp: float = 0.0


@dataclass(frozen=True)
class Obligation:
    """行为义务:接受后须满足的谓词(计数器型)。"""

    predicate: str      # 'refresh_ge:10' | 'difficulty3_encounter' ...
    deadline_nodes: int = 0   # 0 = 无硬期限
    penalty_gold: float = 0.0    # 诅咒未完成惩罚(0 = 非诅咒)


@dataclass(frozen=True)
class Contract:
    """一个状态化 offer(33 号 C1 统一表示)。"""

    name: str
    accept_cost: float = 0.0
    flows: tuple[ContingentFlow, ...] = ()
    obligation: Obligation | None = None
    instant_gold: float = 0.0    # 确定性即付(层 1)
    evidence: str = 'bracketed'


def _cond_prob(condition: str, *, p_win: float, streak: int) -> float:
    """条件发生概率(层 2 卷积的权;连胜档由结算观测更新,此处局面参数注入)。"""
    if condition == 'lose':
        return 1.0 - p_win
    if condition == 'win':
        return p_win
    if condition.startswith('streak_ge:'):
        k = int(condition.split(':')[1])
        return 1.0 if streak >= k else 0.25 * (k - streak)   # 粗先验:每差 1 档 25%
    if condition.startswith('node_ge:'):
        return 1.0    # 节点推进近确定(剩余节点注入时精确)
    return 0.5


def price_contract(c: Contract, *, level: int, hp: int, nodes_left: int,
                   streak: int = 0, plane: int = 1,
                   hp_floor_price: float | None = None) -> dict:
    """三层定价 v0(层 1+2):价格 = 即付 + Σ 条件概率×(金 + HP×λ_hp)。

    λ_hp 由 18 号核按局面解(层 2 的 P(win) 币种换算);连胜条件用 streak 注入。
    返回 {value, breakdown, layers};层 3(行为义务 ΔV)在 obligation 存在时显式
    标注「未含义务重解价」(消费批次接入后覆盖)。
    """
    tier = board_tier_of(level)
    lam = hp_floor_price if hp_floor_price is not None else max(
        0.0, p_win_lambda(tier, max(1, hp), max(1, nodes_left), plane))
    p_win = p_win_projection(level, max(1, hp), max(1, nodes_left), plane=plane)

    v1 = c.instant_gold - c.accept_cost
    v2 = 0.0
    breakdown: list[str] = [f'层1(经济流)={v1:+.1f}']
    for f in c.flows:
        p = _cond_prob(f.condition, p_win=p_win, streak=streak)
        pay = f.pay_gold + f.pay_hp * lam
        v2 += p * pay
        breakdown.append(f'层2({f.condition},p={p:.2f})={p * pay:+.1f}'
                         f'(金{f.pay_gold}+HP{f.pay_hp}×λ{lam:.3f})')
    total = v1 + v2
    if c.obligation is not None and c.obligation.penalty_gold > 0:
        breakdown.append(f'诅咒义务({c.obligation.predicate},deadline={c.obligation.deadline_nodes})'
                         '违约价未含(层 3 重解批次)')
    return {'value': round(total, 3), 'breakdown': breakdown,
            'layers': {'l1': round(v1, 3), 'l2': round(v2, 3)}}


def curse_deadline_floor(*, refresh_rate: float, required: int) -> int:
    """诅咒截止点反解:完成「required 次刷新」按平均速率需要多少节点 → 剩余节点
    少于此数的时刻 = 「别再接」的截止点(33 号 J1 第三条:应落 3-4 附近)。"""
    if refresh_rate <= 0:
        return 99
    import math
    return math.ceil(required / refresh_rate)


# ===== 实锤契约库(33 号 §1 代码实证三条;23 式证据状态) =====

GREAT_CONQUEST = Contract(
    '伟大征服',
    flows=(ContingentFlow('win', pay_gold=0.0),),   # 奖励×3 耦合连胜数——v0 以 streak 价近似
    evidence='bracketed')
# 奖励侧:v0 用 streak 条件流近似(×3 连胜金 = streak_ge:2 后高支付)
GREAT_CONQUEST_STREAK = Contract(
    '伟大征服(连胜引擎近似)',
    flows=(ContingentFlow('streak_ge:2', pay_gold=9.0),
           ContingentFlow('win', pay_gold=0.5)),
    evidence='bracketed')

STUBBORN_MOUTH = Contract(
    '嘴硬',
    flows=(ContingentFlow('lose', pay_hp=5.0),),
    instant_gold=6.0,
    evidence='bracketed')   # 33 号实锤:现码只建 instant_gold=6,条件流被切断
