"""伙伴选择屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = overlay 门判定 + 候选(立绘识别真身,失败回落 label 名)。
report 写点转录来源 = operations/cw_screen/cw_screen_partner.py::
``_handle_overlay`` 写槽(锚 :281);辖域边界 = design.md §2.3(动作
事实 ``chosen_partner`` 不收编,留守选择点)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_events import PartnerOption
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    _validate_sig,
)


@dataclass
class CwScreenPartnerObs:
    """伙伴选择屏观察结果(摄入口 = :func:`report_screen_partner_obs`)。

    [索引定义] ``options`` = 候选(立绘识别真身,失败回落 label 名);
    列表序/``PartnerOption.idx`` = 画面物理候选位序(左→右,恒稳);空 =
    OCR 未读得,report 不写 ``partner_opts``。
    """

    on_screen: bool = False
    options: list[PartnerOption] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_partner_obs(gs: GameState, obs: CwScreenPartnerObs, *,
                              sig: ChannelSig | None = None) -> None:
    """伙伴选择屏观察上报:候选写 ``partner_opts``。

    写点锚 = cw_screen_partner.py::``_handle_overlay`` 写槽(锚 :281);
    options 空 = OCR 未读得,不写(原写点「读得才写」闸逐位平移);
    ``chosen_partner`` 留守选择点(design.md §2.3 动作事实边界)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenPartner', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if not obs.options:
        return
    gs.write_logic(gs.partner_opts, list(obs.options),
                   produced_by='CwScreenPartner', sig=sig)
