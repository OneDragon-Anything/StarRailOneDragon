"""货币战争动作上报:商店屏升级意图(report_action_level_up_shop_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。

本动作 = level_up 同字段双类型别名(一行委托),独立文件保持「文件名 = snake」均一。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_action_report.level_up import (
    report_action_level_up_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
)


def report_action_level_up_shop_param(gs: GameState, param: Any, sig: ChannelSig,
                                      executed: ShopActionExecuted | None = None) -> LogicOutcome:
    """商店屏升级意图上报(CwActionLevelUpShopParam,同字段双类型)——
    一行委托 :func:`report_action_level_up_param`(命名规约完备锁要求
    每词表类恰有一个同名上报函数;语义单一源 = LevelUp 函数)。"""
    return report_action_level_up_param(gs, param, sig, executed)

