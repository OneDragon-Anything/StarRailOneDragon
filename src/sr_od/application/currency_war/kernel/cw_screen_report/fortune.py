"""命运卜者强化屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = overlay 门判定 + 三卡位 OCR 卡名(入口帧一次读)。
report 摄入点 = operations/cw_screen/cw_screen_fortune.py::
``CwScreenFortune.observe``(观察 node);辖域边界:本屏无 chosen 写端
(fortune 选择存证行已退役)。
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
class CwScreenFortuneObs:
    """命运卜者强化屏观察结果(摄入口 = :func:`report_screen_fortune_obs`)。

    [索引定义] ``options`` = OCR 卡名按三卡位 x 桶 join;列表序 = 画面
    物理卡位序(左→中→右,恒稳);取值时机 = 入口帧 OCR 快照。
    """

    on_screen: bool = False
    options: list[str] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_fortune_obs(gs: GameState, obs: CwScreenFortuneObs, *,
                              sig: ChannelSig | None = None) -> None:
    """命运卜者强化屏观察上报:三卡 OCR 写 ``fortune_opts``。

    写点锚 = cw_screen_fortune.py::``CwScreenFortune.observe``(观察 node;
    原写点无空门,直写——空表照写,防线逐位平移)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenFortune', mode='compute')
    _validate_sig(sig, ('logic_action',))
    gs.write_logic(gs.fortune_opts, list(obs.options),
                   produced_by='CwScreenFortune', sig=sig)
