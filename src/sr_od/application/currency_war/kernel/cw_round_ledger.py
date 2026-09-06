"""货币战争 轮内买卖记账(r408 同轮互斥事实集;自 decision_v2.discipline
下沉——执行侧幂等防线的 kernel 单一源)。

「同轮已买/已卖集」是仲裁守卫(no_same_round_mutex)与执行侧幂等加固
共用的**事实账本**:带轮键自校验(跨轮误写防御;set 由决策层轮键重置
段清零)。执行侧唯一消费 = cw_op_buy_cards 卖出落地登记(执行成功是
卖出事实的权威);决策层消费点(arbiter 采纳处等)留 decision 桶经
discipline re-export 消费同一实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_state import GameState

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )


def register_round_sold(names, state: GameState,
                        session: StrategySession) -> None:
    """卖出件入同轮已卖集(r408 对称臂;带轮键自校验,防跨轮误写)。

    四卖件通道统一走本 helper(设计 §4):carry_gate ④/两补偿器/
    arbiter 主循环(采纳处,ADR-0328)/执行侧卖出落地加固。
    """
    key = (state.plane, state.round_num)
    if getattr(exec_state_of(session), 'v2_round_key', None) != key:
        return    # 轮键不匹配(跨轮误写防御;set 下轮重置)
    sold = getattr(exec_state_of(session), 'v2_round_sold', None)
    if sold is None:
        exec_state_of(session).v2_round_sold = sold = set()
    for n in names:
        if n:
            sold.add(n)
