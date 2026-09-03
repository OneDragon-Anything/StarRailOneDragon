"""Ī(净收入率):收入日程逐节点现算(R09 收入三表;TUNING#3 消参路径)。

旧 i_bar=7 常量已处死(NMF §5.4 处死名单):收入按日程逐节点现算
net_income = base(r) + streak(决策前相) + 败轮底金;值全部来自
cw_economy 注册表(【注】机制真值:REWARD_BASE_GOLD_BY_ROUND / BASE_INCOME /
STREAK_GOLD_TABLE / LOSS_GOLD_BY_NODE),本模块零数值字面量。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_economy import (
    BASE_INCOME,
    LOSS_GOLD_BY_NODE,
    REWARD_BASE_GOLD_BY_ROUND,
    streak_gold,
)


def round_base_income(round_num: int) -> int:
    """基础奖励金:1-1 轮 3 / 1-2 轮 4 / 其余 BASE_INCOME(R09 表一;
    cw_economy.REWARD_BASE_GOLD_BY_ROUND 单一源)。"""
    return REWARD_BASE_GOLD_BY_ROUND.get(round_num, BASE_INCOME)


def net_income(round_num: int, streak_pre: int,
               lost_node_type: str | None = None) -> int:
    """逐节点净收入 Ī(NMF §2「Ī」行)。

    - ``round_num``:日程轮号(1 基;开局两轮基础金折半段);
    - ``streak_pre``:**决策前相**连胜数(进轮连胜,奖励轮照发不动计数,
      ADR-0439 引擎口径);
    - ``lost_node_type``:上一轮若为败掉的战斗类节点,其败轮底金在本轮轮首
      补发(battle/encounter/boss → LOSS_GOLD_BY_NODE);非败轮接续传 None。
    """
    inc = round_base_income(round_num) + streak_gold(streak_pre)
    if lost_node_type is not None:
        inc += LOSS_GOLD_BY_NODE.get(lost_node_type, 0)
    return inc


__all__ = ['net_income', 'round_base_income']
