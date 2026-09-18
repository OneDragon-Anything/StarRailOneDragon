"""盛会之星屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 巨星 overlay 门判定 + 候选(懒读语义,字段注写明)。
report 写点转录来源 = operations/cw_screen/cw_screen_megastar.py::
``_do_action`` 写槽(锚 :170);辖域边界 = design.md §2.3(动作事实
``chosen_megastar`` 不收编,留守选择点)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_events import MegastarOption
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    _validate_sig,
)


@dataclass
class CwScreenMegastarObs:
    """盛会之星屏观察结果(摄入口 = :func:`report_screen_megastar_obs`)。"""

    #: 巨星 overlay 在场(标识-盛会之星门判定;一局可多次触发,门逐访问
    #: 现判,不跨访问保持)。
    in_node: bool = False
    #: 巨星候选。**懒读保真**(design.md §2.2):仅「本访问将选择」时由
    #: 观察侧填充(确认访问不重读候选,迁移不增加读屏);空 = 本访问
    #: 未读候选,report 不写 ``megastar_opts``。
    options: list[MegastarOption] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_megastar_obs(gs: GameState, obs: CwScreenMegastarObs, *,
                               sig: ChannelSig | None = None) -> None:
    """盛会之星屏观察上报:候选写 ``megastar_opts``。

    写点锚 = cw_screen_megastar.py::``_do_action`` 写槽(锚 :170)。
    懒读保真(design.md §2.2):obs.options 仅「本访问将选择」时由观察
    侧填充,空 = 本访问未读候选,不写(原写点「读得才写」闸逐位平移);
    ``chosen_megastar`` 留守选择点(design.md §2.3 动作事实边界)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenMegastar', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if not obs.options:
        return
    gs.write_logic(gs.megastar_opts, list(obs.options),
                   produced_by='CwScreenMegastar', sig=sig)
