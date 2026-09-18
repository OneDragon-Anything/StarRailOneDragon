"""货币战争动作上报:关店(report_action_close_shop_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
)


def report_action_close_shop_param(gs: GameState, param: Any, sig: ChannelSig) -> LogicOutcome:
    """关店上报(结构离屏):shop payload 离屏(离屏写渠道 = obs 族,
    内部按 sig.actor 转造 obs 签名);离屏态 = 结构性离屏,零内容写。"""
    _validate_sig(sig, ('logic_action',))
    if gs.shop.value is not None:
        _off_sig = ChannelSig(family='obs', actor=sig.actor,
                              mode='read', group_id=sig.group_id)
        gs.leave_screen(gs.shop, sig=_off_sig)
    return LogicOutcome(applied=True)

