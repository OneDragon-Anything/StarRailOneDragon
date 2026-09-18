"""祈愿试炼屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = overlay 门判定 + 各卡 objective 文本 OCR 桶 join(入口帧一次
读)。report 摄入点 = operations/cw_screen/cw_screen_wish_trial.py::
``CwScreenWishTrial.observe``(观察 node);辖域边界:动作事实
``chosen_wish`` 不收编,留守重入裁决点。
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
class CwScreenWishTrialObs:
    """祈愿试炼屏观察结果(摄入口 = :func:`report_screen_wish_trial_obs`)。

    [索引定义] ``options`` = 各卡 objective 文本(OCR 桶 join);列表序 =
    画面物理卡位序(左→右,与点卡列同坐标系,恒稳);空桶照持(原写点
    无空门,决策侧 fallback 首卡)。
    """

    on_screen: bool = False
    options: list[str] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_wish_trial_obs(gs: GameState, obs: CwScreenWishTrialObs, *,
                                 sig: ChannelSig | None = None) -> None:
    """祈愿试炼屏观察上报:objective 写 ``wish_trial_opts``。

    写点锚 = cw_screen_wish_trial.py::``CwScreenWishTrial.observe``(观察
    node 摄入;段内直写,无空门——OCR 空桶照写,决策侧 fallback 首卡,
    防线逐位平移);``chosen_wish`` 留守重入裁决点(动作事实边界)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenWishTrial', mode='compute')
    _validate_sig(sig, ('logic_action',))
    gs.write_logic(gs.wish_trial_opts, list(obs.options),
                   produced_by='CwScreenWishTrial', sig=sig)
