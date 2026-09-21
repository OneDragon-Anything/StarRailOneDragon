"""简报屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口门判定 + 三读数(敌人词缀/位面序 boss/敌人难度;读数
在观察侧读取,字段进即写)。report 摄入点 =
operations/cw_screen/cw_screen_briefing.py::``CwScreenBriefing.observe``
(观察 node 三写点)。写语义 = 三字段统一「读到非空恒覆写 / 读空跳过
写」:简报三读数一局内恒定,覆写无信息损失,重读自愈首次误读;瞬时
OCR 失手不擦同局已读真值(读缺 = 跳过写项目口径);跨局残留由每局
容器冷建/丢弃挡死,不靠本写点清场。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    _validate_sig,
)


@dataclass
class CwScreenBriefingObs:
    """简报屏观察结果(摄入口 = :func:`report_screen_briefing_obs`;三读数
    字段为本屏 report 所需——读数在观察侧读取,字段进即写)。"""

    on_screen: bool = False
    #: 敌人词缀名单(OCR 原名;空 = 读缺,report 跳过写)。
    enemy_affixes: list[str] = field(default_factory=list)
    #: 位面序 boss 名(LCS 清洗后;None = 读空,report 跳过写)。
    plane_bosses: list[str] | None = None
    #: 敌人难度数值(简报「敌人难度N」;None = 读缺,report 跳过写)。
    enemy_difficulty: int | None = None
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_briefing_obs(gs: GameState, obs: CwScreenBriefingObs, *,
                               sig: ChannelSig | None = None) -> None:
    """简报屏观察上报:三字段统一写语义落容器(写点锚 =
    cw_screen_briefing.py::``CwScreenBriefing.observe``(观察 node 三写点))。

    - 读到非空恒覆写:三读数一局内恒定,覆写无信息损失,重读自愈
      首次误读;
    - 读空跳过写(读缺 = 跳过写项目口径):瞬时 OCR 失手不擦同局
      已读真值;跨局残留由每局容器冷建/丢弃挡死,不靠本写点清场。
    """
    if sig is None:
        # screen='' 沿原写点(简报三写点 sig 均带空画面标识,照抄现役原值)。
        sig = ChannelSig(family='logic_action', actor='CwScreenBriefing',
                         screen='', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if obs.enemy_affixes:
        gs.write_logic(gs.enemy_affixes, list(obs.enemy_affixes),
                       produced_by='CwScreenBriefing', sig=sig)
    if obs.plane_bosses:
        gs.write_logic(gs.plane_bosses, list(obs.plane_bosses),
                       produced_by='CwScreenBriefing', sig=sig)
    if obs.enemy_difficulty is not None:
        gs.write_logic(gs.enemy_difficulty, obs.enemy_difficulty,
                       produced_by='CwScreenBriefing', sig=sig)
