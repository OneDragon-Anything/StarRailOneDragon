"""BOSS 简报屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 入口裁决:门判定 + 稳定帧引用。
report 写点转录来源 = 无——本屏现役零 op 层观察容器写点(design.md
§2.3 辖域边界;boss 真值写端在简报屏 report_briefing 的 ``plane_bosses``
恒覆写面),接口为统一形态占位,摄入面出现时落此处。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
)


@dataclass
class CwScreenBossBriefingObs:
    """BOSS 简报屏观察结果(统一形态:门判定 + 帧引用)。"""

    on_screen: bool = False
    screen: Any = None


def report_screen_boss_briefing_obs(gs: GameState,
                                    obs: CwScreenBossBriefingObs, *,
                                    sig: ChannelSig | None = None) -> None:
    """BOSS 简报屏观察上报:本屏观察无容器摄入面,接口为统一形态占位;
    摄入面出现时落此处(design.md §2.3;占位不构造不校验 sig——无写即
    无渠道面)。"""
