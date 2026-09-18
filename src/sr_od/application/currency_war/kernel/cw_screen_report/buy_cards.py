"""买牌屏观察契约与上报(kernel 纯数据)。

观察面 = 重型屏薄包装:入口观察回执同面镜像(现役
``obs/cw_observation.GameStateReadReceipt`` 逐位镜像——kernel 禁依
obs/ 包,同面自持;装配点 = cw_screen_buy_cards 观察段读链,语义与
回执同源)。容器写端在 read_game_state 漏斗,本函数不重复承接,
report 保持占位。

op 层观察写点勘察结论(重型屏迁移批):唯一候选 =
cw_screen_buy_cards 段头 gold 救援补写(首读假 0 救回后
``gs.observe(gs.gold, ..., evidence='gold_rescue:shop_first_read_fake_zero')``)
——属入口观察链内的纠正补写(救援读循环 + obs_conflict 留证三元组的
同点写半),非独立观察域,本批不收编零行为改道;是否收编交后续批裁决。
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
    占位——容器写端在 read_game_state 漏斗)。

    字段面 = 入口观察回执 ``obs/cw_observation.GameStateReadReceipt``
    逐位镜像(kernel 禁依 obs/ 包,同面自持;语义与回执同源:gold 失读
    raw 0 带 readable 位、hp = 对账层决策值、level 三源解析值、shop =
    遗留 ShopCard 形态原始读牌列表)。
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
    """买牌屏观察上报:容器写端在 read_game_state 漏斗,本函数不重复
    承接;op 层观察写点勘察结论见模块头(gold 救援补写不收编,交后续批
    裁决)。接口为统一形态占位(占位不构造不校验 sig——无写即无渠道面)。"""
