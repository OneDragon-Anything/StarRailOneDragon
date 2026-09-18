"""星徽秘典屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 入口门判定 + 卡阵营名 OCR(「X星徽」去后缀,x 升序)。
report 写点转录来源 = operations/cw_screen/cw_screen_bookcard.py::
``_handle_overlay`` 写槽(锚 :163);辖域边界 = design.md §2.3(动作
事实 ``chosen_tome`` 不收编,留守重入裁决点)。
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
class CwScreenBookcardObs:
    """星徽秘典屏观察结果(摄入口 = :func:`report_screen_bookcard_obs`)。

    [索引定义] ``options`` = OCR「X星徽」去后缀阵营名;列表序 = 画面
    物理卡位序(x 升序左→右,恒稳);空 = OCR 未读得,report 不写
    ``star_tome_opts``。
    """

    on_screen: bool = False
    options: list[str] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_bookcard_obs(gs: GameState, obs: CwScreenBookcardObs, *,
                               sig: ChannelSig | None = None) -> None:
    """星徽秘典屏观察上报:卡阵营名写 ``star_tome_opts``。

    写点锚 = cw_screen_bookcard.py::``_handle_overlay`` 写槽(锚 :163);
    options 空 = OCR 未读得,不写(原写点「读得才写」闸逐位平移);
    ``chosen_tome`` 留守重入裁决点(design.md §2.3 动作事实边界)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenBookcard', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if not obs.options:
        return
    gs.write_logic(gs.star_tome_opts, list(obs.options),
                   produced_by='CwScreenBookcard', sig=sig)
