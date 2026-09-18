"""选择装备屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = overlay 门判定 + 三卡位 OCR 卡名(入口帧一次读)。
report 写点转录来源 = operations/cw_screen/cw_screen_equip_pick.py::
``_handle_overlay`` 写槽(锚 :154);辖域边界 = design.md §2.3(动作
事实不收编;本屏无 chosen 写端)。
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
class CwScreenEquipPickObs:
    """选择装备屏观察结果(摄入口 = :func:`report_screen_equip_pick_obs`)。

    [索引定义] ``options`` = OCR 卡名按三卡位 x 桶 join;列表序 = 画面
    物理卡位序(左→中→右,与点卡列 CARD_XS 同坐标系,恒稳);取值时机
    = 入口帧 OCR 快照。
    """

    on_screen: bool = False
    options: list[str] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_equip_pick_obs(gs: GameState, obs: CwScreenEquipPickObs, *,
                                 sig: ChannelSig | None = None) -> None:
    """选择装备屏观察上报:OCR 卡名写 ``equip_pick_opts``。

    写点锚 = cw_screen_equip_pick.py::``_handle_overlay`` 写槽(锚 :154;
    原写点无候选空门,直写——空表照写,防线逐位平移不加强不减弱)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenEquipPick', mode='compute')
    _validate_sig(sig, ('logic_action',))
    gs.write_logic(gs.equip_pick_opts, list(obs.options),
                   produced_by='CwScreenEquipPick', sig=sig)
