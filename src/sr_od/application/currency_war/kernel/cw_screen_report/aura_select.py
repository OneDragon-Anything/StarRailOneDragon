"""主角光环选择屏观察契约与上报(kernel 纯数据;权威版本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口门后的光环名一次读(观察标准化门两段转换后上报,
注册表 = data/cw_spot_lights.py,转换失败 = 观察失败不上报)+
光环卡中心与预览卡拖拽源点(几何产点)。
report 摄入点 = operations/cw_screen/cw_screen_aura_select.py;
适用范围边界:确认/拖拽动作事实不并入(归 CwSelectProtagonist 域)。
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
class CwScreenAuraSelectObs:
    """主角光环选择屏观察结果(摄入口 = :func:`report_screen_aura_select_obs`)。

    [索引定义] ``aura_centers`` = 光环卡中心 ``(x, y)`` 固定二槽,列表序 =
    画面物理序(左, 右),0 基,左 = idx 0(与 ``aura_select_opts`` 同序);
    ``preview_points`` = 预览卡拖拽源点 ``(x, y)`` 列表,行主序 = 前排 y 带
    从左到右,随后后排 y 带(与 ``aura_select_preview_xy`` 同序,idx 0 =
    前排第一 = v1 决策选择位);产点含右半部抓取偏移(读法定义的一部分,
    动作零现算)。转换失败的光环名不上报(观察失败交外环,禁带病上报)。
    """

    on_screen: bool = False
    aura_left: str | None = None
    aura_right: str | None = None
    aura_centers: list[tuple[int, int]] = field(default_factory=list)
    preview_points: list[tuple[int, int]] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_aura_select_obs(gs: GameState, obs: CwScreenAuraSelectObs, *,
                                  sig: ChannelSig | None = None) -> None:
    """主角光环选择屏观察上报:光环名写 ``aura_select_opts``(标准化后
    标准名,固定二槽 [左, 右])、光环卡中心写 ``aura_select_opts_xy``
    (同门同帧同序等长)、预览卡拖拽源点写 ``aura_select_preview_xy``
    (行主序)。

    写点定位 = cw_screen_aura_select.py 观察 node;光环名任一槽转换失败
    = op 侧观察失败早退不达本口(禁带病上报);名与中心同序等长由写端
    构造守卫保证(读端不做长度调和);本屏读缺形态 = 名缺任一槽即失败,
    无「读到空」跳写分支(二槽结构缺一即观察失败,同判交外环)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenAuraSelect', mode='compute')
    _validate_sig(sig, ('logic_action',))
    names = [obs.aura_left or '', obs.aura_right or '']
    if not all(names):
        return
    gs.write_logic(gs.aura_select_opts, names,
                   produced_by='CwScreenAuraSelect', sig=sig)
    if len(obs.aura_centers) == len(names):
        gs.write_logic(gs.aura_select_opts_xy, list(obs.aura_centers),
                       produced_by='CwScreenAuraSelect', sig=sig)
    if obs.preview_points:
        gs.write_logic(gs.aura_select_preview_xy, list(obs.preview_points),
                       produced_by='CwScreenAuraSelect', sig=sig)
