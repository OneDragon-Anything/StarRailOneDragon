"""武装箱弹窗屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口裁决:门判定 + 稳定帧引用(推进型弹窗)。
report 写点转录来源 = 无——本屏现役零 op 层观察容器写点,接口为统一
形态占位,摄入面出现时落此处。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
)


@dataclass
class CwScreenArmoryBoxObs:
    """武装箱弹窗屏观察结果(统一形态:门判定 + 帧引用)。"""

    on_screen: bool = False
    screen: Any = None


def report_screen_armory_box_obs(gs: GameState, obs: CwScreenArmoryBoxObs, *,
                                 sig: ChannelSig | None = None) -> None:
    """武装箱弹窗屏观察上报:本屏观察无容器摄入面,接口为统一形态占位;
    摄入面出现时落此处(占位不构造不校验 sig——无写即无渠道面)。"""
