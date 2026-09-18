"""备战屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 重型屏薄包装:现役 ``PrepObservation`` 整包(kernel.cw_prep_
actions,阶段 3.5 瘦身后仅控制信号与识别元信息)。
report 写点转录来源 = 无——漏斗边界(design.md §2.3):容器写端在
read_game_state 漏斗与外循环开局链,本函数不重复承接;接管补采写点
(takeover)/``plane_bosses``/``enemy_affixes``/``node_path`` 等 op 层写点
的收编归重型屏迁移批(design.md §2.6 重型屏行)。接口为统一形态占位。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepObservation,
)


@dataclass
class CwScreenPrepObs:
    """备战屏观察结果(重型屏薄包装;摄入口 = :func:`report_screen_prep_obs`
    占位——漏斗边界见 design.md §2.3,容器写端在 read_game_state 漏斗与
    外循环开局链,接管补采写点归重型屏迁移批再裁)。

    ``prep`` = 现役 ``PrepObservation`` 整包(kernel.cw_prep_actions;
    事件 overlay 面 = ``prep.event_overlay``,bail 控制信号住整包内,
    不另立顶层字段防双源漂移)。
    """

    prep: PrepObservation = field(default_factory=PrepObservation)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_prep_obs(gs: GameState, obs: CwScreenPrepObs, *,
                           sig: ChannelSig | None = None) -> None:
    """备战屏观察上报:漏斗边界(design.md §2.3)——容器写端在
    read_game_state 漏斗与外循环开局链,本函数不重复承接;接管补采
    写点归重型屏迁移批再裁。接口为统一形态占位(占位不构造不校验
    sig——无写即无渠道面)。"""
