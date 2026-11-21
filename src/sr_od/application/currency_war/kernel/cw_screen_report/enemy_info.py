"""敌人信息浮层观察契约与上报(kernel 纯数据;权威版本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口裁决:门判定 + 稳定帧引用。
report 写点转录来源 = 无——本屏现役零 op 层观察字段写点,接口为统一
形态占位,摄入面出现时落此处。浮层读数域(词缀 chips/波次列表)的
结构化采集归遭遇域词缀读数通道(遭遇节点 op 死输入申报),不归本 op。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
)


@dataclass
class CwScreenEnemyInfoObs:
    """敌人信息浮层观察结果(统一形态:门判定 + 帧引用)。"""

    on_screen: bool = False
    screen: Any = None


def report_screen_enemy_info_obs(gs: GameState,
                                 obs: CwScreenEnemyInfoObs, *,
                                 sig: ChannelSig | None = None) -> None:
    """敌人信息浮层观察上报:本屏观察无状态容器摄入面,接口为统一形态
    占位;摄入面出现时落此处(占位不构造不校验 sig——无写即无渠道面)。"""
