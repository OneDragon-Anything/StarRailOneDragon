"""奇遇对话屏观察契约与上报(kernel 纯数据;权威版本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口门后的伙伴名一次读(对话页)+ 奇遇选择卡选项一次读
(两段式 node 入口本段识别〔例外③〕同帧补写)。一类两构造点:
①观察 node(对话页,card_options 空)②两段式 node(卡页,card_options
填充)——同一 report 函数摄入,字段读缺跳写。
report 摄入点 = operations/cw_screen/cw_screen_adventure_dialog.py。
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
class CwScreenAdventureDialogObs:
    """奇遇对话屏观察结果(摄入口 = :func:`report_screen_adventure_dialog_obs`)。

    [索引定义] ``card_options`` = 奇遇选择卡 ``(文本, rect)`` 二元组列表;
    列表序 = 选项卡带内自上而下,0 基;``rect`` = 选项标题 OCR 命中框
    (观察期快照,点选中心派生自它——坐标唯一去处 =
    ``adventure_card_opts_xy``);卡未在场 = 空列表(report 对名字域跳写、
    对卡选项域跳写)。
    """

    on_screen: bool = False
    #: 伙伴名(读区-伙伴卡区 OCR,读不到 = None——跳写保持 None)。
    partner_name: str | None = None
    card_options: list[tuple[str, tuple[int, int, int, int]]] = field(
        default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_adventure_dialog_obs(
        gs: GameState, obs: CwScreenAdventureDialogObs, *,
        sig: ChannelSig | None = None) -> None:
    """奇遇对话屏观察上报:伙伴名写 ``adventure_partner_name``(读缺跳写);
    奇遇选择卡选项在场时写 ``adventure_card_opts`` +
    ``adventure_card_opts_xy``(同门同帧同序等长,坐标 = 选项卡命中框中心)。

    写点定位 = cw_screen_adventure_dialog.py 观察与两段式两构造点;
    名字读不到 / 卡选项空 = 各自跳写(「读到空」与「未读到」同判);
    伙伴名整表覆盖(str 域),卡选项整表覆盖(list 域)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenAdventureDialog', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if obs.partner_name:
        gs.write_logic(gs.adventure_partner_name, obs.partner_name,
                       produced_by='CwScreenAdventureDialog', sig=sig)
    if obs.card_options:
        names = [text for text, _rect in obs.card_options]
        centers = [
            ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)
            for _text, rect in obs.card_options
        ]
        gs.write_logic(gs.adventure_card_opts, names,
                       produced_by='CwScreenAdventureDialog', sig=sig)
        gs.write_logic(gs.adventure_card_opts_xy, centers,
                       produced_by='CwScreenAdventureDialog', sig=sig)
