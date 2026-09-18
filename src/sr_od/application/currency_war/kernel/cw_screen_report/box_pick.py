"""武装箱选择屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口锚复验(标识-请选择)+ OCR 卡名行(2-8 字过滤,x 升序)。
report 摄入点 = operations/cw_screen/cw_screen_box_pick.py::
``CwScreenBoxPick.observe``(观察 node);辖域边界:本屏选卡即终结,
无 chosen 写端;选错不可逆的「卡名空交回重派」闸留守观察侧。
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
class CwScreenBoxPickObs:
    """武装箱选择屏观察结果(摄入口 = :func:`report_screen_box_pick_obs`)。

    [索引定义] ``card_names`` = OCR 卡名行(2-8 字过滤);列表序 = 画面
    物理卡位序(x 升序左→右,恒稳);空 = 变体字型/动画帧读缺,观察侧
    交回外循环重派,report 不调(禁盲点首卡)。
    """

    on_screen: bool = False
    card_names: list[str] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_box_pick_obs(gs: GameState, obs: CwScreenBoxPickObs, *,
                               sig: ChannelSig | None = None) -> None:
    """武装箱选择屏观察上报:OCR 卡名写 ``box_card_names``。

    写点锚 = cw_screen_box_pick.py::``CwScreenBoxPick.observe``(观察 node;
    调用方「卡名空 = round_fail 交回重派」闸已保证非空到达,原写点无
    空门——防线逐位平移不加强不减弱)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenBoxPick', mode='compute')
    _validate_sig(sig, ('logic_action',))
    gs.write_logic(gs.box_card_names, list(obs.card_names),
                   produced_by='CwScreenBoxPick', sig=sig)
