"""战斗等待屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 入口裁决:门判定 + 稳定帧引用。
report 写点转录来源 = 无——本屏现役零 op 层观察容器写点(design.md
§2.3 辖域边界:结算覆盖写端在 ``apply_settlement_cover`` 动作/结算链,
非画面观察记账),接口为统一形态占位,摄入面出现时落此处。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
)


@dataclass
class CwScreenBattleWaitObs:
    """战斗等待屏观察结果(统一形态:门判定 + 帧引用)。"""

    on_screen: bool = False
    screen: Any = None


def report_screen_battle_wait_obs(gs: GameState, obs: CwScreenBattleWaitObs, *,
                                  sig: ChannelSig | None = None) -> None:
    """战斗等待屏观察上报:本屏观察无容器摄入面(结算覆盖写端在
    ``apply_settlement_cover`` 动作/结算链,非画面观察记账),接口为统一
    形态占位;摄入面出现时落此处(design.md §2.3;占位不构造不校验
    sig——无写即无渠道面)。"""
