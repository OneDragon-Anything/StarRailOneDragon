"""位面情报采集屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 采集收获转录(纯数据,由采集 op 装配);report 写门 =
接管补采真值落容器的唯一一份写门(编排单一源 = CwEntryPlaneIntel,
判断线住本屏文件):位面序 boss 全量写 + 已有真值不覆写(简报源先落
时实采不冲真值);敌人词缀幂等门(仅容器空时写,简报已供不重写)。
写门渠道签名按迭代设计(design §2.3,2026-09-20-takeover-intel-pipeline)
定死:采集真值落账属 logic_action 族(同简报写点族),screen = 实际
采集画面(本写点有明确宿主屏,非简报写点的空 screen),actor = 写者
本体;对账网已随死机制退役,不在本写门。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
)

#: 写门统一签名(定死值):family = logic_action(采集真值落账族),
#: actor = 写者本体,screen = 位面详情屏(实际采集画面),mode = compute。
_WRITE_SIG = ChannelSig(family='logic_action', actor='CwScreenPlaneIntel',
                        screen='货币战争-位面详情', mode='compute')


@dataclass
class CwScreenPlaneIntelObs:
    """位面情报采集屏观察结果(统一形态门判定 + 采集收获;纯数据)。

    - ``on_screen``/``screen``:门判定与稳定帧引用(统一形态面)。
    - ``plane_bosses``:三位面 boss 身份,3 槽保位(恒全采语义下元素
      非 None;容器槽位 None = 简报源未读得,仅简报写点产生)。
    - ``enemy_affixes``:词缀横条读数(空列表 = 无词缀;None = 本轮
      无此面,不进写门)。
    """

    on_screen: bool = False
    screen: Any = None
    plane_bosses: list[str] | None = None
    enemy_affixes: list[str] | None = None


def report_screen_plane_intel_obs(gs: GameState, obs: CwScreenPlaneIntelObs, *,
                                  sig: ChannelSig | None = None) -> None:
    """位面情报采集屏观察上报:采集真值落容器(写域唯一一份写门)。

    写门两件:

    - ``plane_bosses``:已有真值不覆写(简报源先落 = 真值已在,实采
      内容再新也只是重复或残留,不覆写);无真值时 3 槽保位全量写;
    - ``enemy_affixes``:幂等门(仅容器空时写;空读数 = 无词缀,不落
      写——空表覆写会把已有真值抹成「无数据」)。

    ``sig`` 形参为统一形态占位:本写域签名按设计定死值构造,不受形参
    影响(先例 = 备战接管域写门)。
    """
    if obs.plane_bosses and not gs.plane_bosses.value:
        gs.write_logic(gs.plane_bosses, list(obs.plane_bosses),
                       produced_by='CwScreenPlaneIntel',
                       evidence='plane_intel_row', sig=_WRITE_SIG)
    if obs.enemy_affixes and not gs.enemy_affixes.value:
        gs.write_logic(gs.enemy_affixes, list(obs.enemy_affixes),
                       produced_by='CwScreenPlaneIntel',
                       evidence='plane_intel_affixes', sig=_WRITE_SIG)
