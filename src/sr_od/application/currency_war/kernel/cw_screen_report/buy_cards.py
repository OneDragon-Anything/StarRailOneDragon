"""买牌屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 重型屏薄包装:入口观察回执同面镜像(现役
``obs/cw_observation.GameStateReadReceipt`` 逐位镜像——kernel 禁依
obs/ 包,同面自持;装配归重型屏迁移批读链,语义与回执同源)。
report 写点转录来源 = 无——漏斗边界(design.md §2.3):容器写端在
read_game_state 漏斗,op 层观察写点收编归重型屏迁移批(design.md
§2.6 重型屏行)。接口为统一形态占位。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
)


@dataclass
class CwScreenBuyCardsObs:
    """买牌屏观察结果(重型屏薄包装;摄入口 = :func:`report_screen_buy_cards_obs`
    占位——容器写端在 read_game_state 漏斗,漏斗边界见 design.md §2.3)。

    字段面 = 入口观察回执 ``obs/cw_observation.GameStateReadReceipt``
    逐位镜像(kernel 禁依 obs/ 包,同面自持;装配归迁移批读链,语义与
    回执同源:gold 失读 raw 0 带 readable 位、hp = 对账层决策值、
    level 三源解析值、shop = 遗留 ShopCard 形态原始读牌列表)。
    """

    gold: int = 0
    gold_readable: bool = False
    hp: int | None = None
    hp_readable: bool = False
    hp_trusted: bool = False
    level: int = 1
    level_readable: bool = True
    plane: int = 1
    round_num: int = 1
    node_type: str | None = None
    board: dict[str, int] = field(default_factory=dict)
    shop: list = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_buy_cards_obs(gs: GameState, obs: CwScreenBuyCardsObs, *,
                                sig: ChannelSig | None = None) -> None:
    """买牌屏观察上报:漏斗边界(design.md §2.3)——容器写端在
    read_game_state 漏斗,本函数不重复承接;op 层观察写点收编归重型屏
    迁移批。接口为统一形态占位(占位不构造不校验 sig——无写即无
    渠道面)。"""
