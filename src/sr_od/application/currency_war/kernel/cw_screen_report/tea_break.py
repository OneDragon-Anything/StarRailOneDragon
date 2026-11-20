"""幕后茶歇屏观察契约与上报(kernel 纯数据;权威版本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口门后的选项一次读(首页双卡态 / 分支态两构造点共用本类,
同 visit 内分支态读覆盖首页态读——整表覆盖写语义)。
report 摄入点 = operations/cw_screen/cw_screen_tea_break.py;
适用范围边界:交互确认与奖励领取的事实面不并入(归茶歇奖励屏)。
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
class CwScreenTeaBreakObs:
    """幕后茶歇屏观察结果(摄入口 = :func:`report_screen_tea_break_obs`)。

    [索引定义] ``options`` = 选项 ``(文本, rect)`` 二元组列表;列表序 =
    画面物理序(选项卡带内自上而下 / 自左而右),0 基;``rect`` = 选项卡
    OCR 命中框(观察期快照,点击中心派生自它——坐标唯一去处 =
    ``tea_break_opts_xy``,经 report 同门写入);空 = 读缺,report 不写
    (「读到空」与「未读到」同判保持 None)。
    """

    on_screen: bool = False
    options: list[tuple[str, tuple[int, int, int, int]]] = field(
        default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_tea_break_obs(gs: GameState, obs: CwScreenTeaBreakObs, *,
                                sig: ChannelSig | None = None) -> None:
    """幕后茶歇屏观察上报:选项文本写 ``tea_break_opts``、选项卡中心写
    ``tea_break_opts_xy``(同门同帧同序等长,坐标 = 选项卡 OCR 命中框中心,
    1080p 游戏空间平铺元组)。

    写点定位 = cw_screen_tea_break.py 观察与首页前置两构造点;options 空 =
    读缺跳写(沿 partner「读得才写」闸逐位平移);交互/领取事实不并入。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenTeaBreak', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if not obs.options:
        return
    names = [text for text, _rect in obs.options]
    centers = [
        ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)
        for _text, rect in obs.options
    ]
    gs.write_logic(gs.tea_break_opts, names, produced_by='CwScreenTeaBreak',
                   sig=sig)
    gs.write_logic(gs.tea_break_opts_xy, centers,
                   produced_by='CwScreenTeaBreak', sig=sig)
