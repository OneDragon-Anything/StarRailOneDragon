"""sim 重做·轮首收入与连胜经济(M04/M15)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M04/M15:

- 每节点收入 = 基础奖励 + 利息 + 连胜奖励,全部经 kernel
  ``round_start_income`` 三分支单一源消费(补给/奖励/败补/常规;禁
  引擎内手搓第二份分支);
- **U04 已裁决**:败轮实发 = 被败节点的基础奖励 + 利息(平面感知取
  键)——经 kernel ``lost_node`` 败补支承载;旧 ``LOSS_GOLD_BY_NODE``
  类型表替换路径(ADR-0439)随重做废除(常量本体保留,决策侧活消费
  另批清理,重做设计稿 §2.4.1 kernel 侧残留申报);
- **U05 定稿口径**:补给轮照发基础奖励 + 利息(kernel supply 支);
- **U06 定稿口径**:无「事件金」——收入面由查表 + 奖励球承载,本模块
  无任何随机分量;
- 连胜:引擎内无符号计数(收入侧,``streak_gold`` 键)+ 容器带符号
  (obs,正=连胜/负=连败)双账并存;战斗类胜 +1/败归零(带符号取负),
  奖励/补给轮不动;
- 投资修正 = ``aggregate_economy`` 聚合(连胜倍率取最大不叠乘/息帽
  覆写取宽/每节点固定息求和),平移现行 T-64/win_reward_mult/息帽链。

随机量与流键:无(全部查表,M04)。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.kernel.cw_economy import (
    LostNodeRef,
    RoundStartIncome,
    round_start_income,
)
from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.kernel.cw_investments import (
    aggregate_economy,
)
from sr_od.application.currency_war.sim.cw_sim_base import obs_sig, sim_evidence

#: 战斗类节点词表(连胜转移与败态归宿的判据域;补给/奖励轮不动连胜,
#: M15;奖励节点结算走战斗框架但收入分支仍为 reward,M12/M17)。
COMBAT_NODE_TYPES: frozenset[str] = frozenset({'battle', 'encounter', 'boss'})

#: 非战斗收入分支节点词表(分支优先级:supply/reward 先于败补,kernel
#: 分支序;败态在这些轮保留待下一战斗轮消费)。
INCOME_BRANCH_NODE_TYPES: frozenset[str] = frozenset({'supply', 'reward'})


@dataclass(frozen=True)
class IncomeApplied:
    """轮首收入应用回声(账面分解 + 落账后金;sim 局内披露/判读消费)。"""

    row: RoundStartIncome
    gold_before: int
    gold_after: int


def income_modifiers_of(bs: GameState) -> tuple[float, int, int | None]:
    """持卡聚合的收入修饰 ``(win_reward_mult, interest_flat, cap_override)``。

    单一源 = ``aggregate_economy``(倍率取最大不叠乘/flat 求和/cap 取宽;
    cap None = 无覆写,由 ``interest_cap_resolved`` 归一链回默认)。
    """
    eff = aggregate_economy(list(bs.active_strategies.value or []))
    return eff.win_reward_mult, eff.interest_flat_per_node, \
        eff.interest_cap_override


def apply_round_start_income(bs: GameState, *, plane: int, round_num: int,
                             node_type: str, streak: int,
                             pending_loss: LostNodeRef | None = None,
                             ) -> IncomeApplied:
    """轮首收入结算并 obs 写金(引擎每节点推进调用一次)。

    - ``streak`` = 收入侧无符号连胜计数(进轮连胜;``streak_gold`` 键,
      奖励/补给轮分支语义由 kernel 单一源承载);
    - ``pending_loss`` = 上一败掉的战斗类节点引用(单挂账):非
      supply/reward 节点传入触发 kernel 败补支(U04 口径);supply/reward
      轮不传(分支优先级 + 败态跨轮保留,仅下一战斗轮消费——与 kernel
      分支序一致,归宿语义见模块 docstring);
    - 消费后败态清理由引擎负责(本函数不持有引擎态)。
    """
    mult, flat, cap = income_modifiers_of(bs)
    gold_before = int(bs.gold.value or 0)
    effective_loss = (pending_loss
                      if node_type not in INCOME_BRANCH_NODE_TYPES else None)
    row = round_start_income(
        plane, round_num, node_type, gold_before, streak,
        lost_node=effective_loss, win_reward_mult=mult,
        interest_flat=flat, interest_cap=cap)
    gold_after = gold_before + row.total
    tag = f'income:p{plane}r{round_num}'
    bs.observe(bs.gold, gold_after, evidence=sim_evidence(tag),
               sig=obs_sig(group_id=f'sim:{tag}'))
    return IncomeApplied(row=row, gold_before=gold_before,
                         gold_after=gold_after)


def streak_income_after(streak: int, *, node_type: str,
                        won: bool) -> int:
    """收入侧无符号连胜计数转移(战斗类胜 +1/败归零;奖励/补给不动;
    M15 转移规则)。"""
    if node_type not in COMBAT_NODE_TYPES:
        return streak
    return streak + 1 if won else 0


def streak_signed_after(streak_signed: int, *, node_type: str,
                        won: bool) -> int:
    """容器带符号连胜转移(生产口径:连胜 +/连败 −;战斗类胜 +1/败取
    负向计数;奖励/补给轮不动;M15,与旧引擎逐位同式)。"""
    if node_type not in COMBAT_NODE_TYPES:
        return streak_signed
    if won:
        return streak_signed + 1 if streak_signed > 0 else 1
    return streak_signed - 1 if streak_signed < 0 else -1
