"""祈愿试炼屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = overlay 门判定 + 各卡 objective 文本 OCR 桶 join + 各卡槽位
坐标观察期一次解析(入口帧一次读)。report 摄入点 =
operations/cw_screen/cw_screen_wish_trial.py::
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
    无空门,决策侧无兜底:决策无有效输出 = 守卫 fail 零盲发,申报见
    screens/wish_trial.md §8)。

    [索引定义] ``option_points`` = 各卡槽位坐标(x = 桶锚 ``CARD_XS``、
    y = 卡身 ``CARD_Y``,观察期一次解析);键 = ``options`` 列表下标 idx
    (0 起,左→右画面物理序,与策略器输出下标、动作词表
    ``CwActionPickWishTrialParam.idx`` 同一坐标系零换算);取值时机 =
    观察期快照(动作执行期恒稳,禁执行期现读现算);值形状 = 1080p
    平铺元组 (x, y)(遥测 JSON 序列化安全形);与 ``options`` 同序等长
    (写端构造守卫,读端不做长度调和)。
    """

    on_screen: bool = False
    options: list[str] = field(default_factory=list)
    option_points: list[tuple[int, int]] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_wish_trial_obs(gs: GameState, obs: CwScreenWishTrialObs, *,
                                 sig: ChannelSig | None = None) -> None:
    """祈愿试炼屏观察上报:objective 与槽位坐标一并写 ``wish_trial_opts``
    / ``wish_trial_opts_xy``(同门同写,op-layer.md §1.1 :35)。

    写点锚 = cw_screen_wish_trial.py::``CwScreenWishTrial.observe``(观察
    node 摄入;段内直写,无空门——OCR 空桶照写,决策侧无兜底:决策无
    有效输出 = 守卫 fail 零盲发(申报见 screens/wish_trial.md §8),防线
    逐位平移);``chosen_wish`` 留守重入裁决点(动作事实边界)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenWishTrial', mode='compute')
    _validate_sig(sig, ('logic_action',))
    # 同序等长写端构造守卫(fields.md §3.4.5a):坐标域与名字域同一写门
    # 一并落容器,不等长 = 观察 bug,响亮暴露禁错位双写。
    if len(obs.option_points) != len(obs.options):
        raise AssertionError(
            '[cw][wish] 坐标域与名字域不同序等长(观察 bug): '
            f'len(option_points)={len(obs.option_points)} '
            f'len(options)={len(obs.options)}')
    gs.write_logic(gs.wish_trial_opts, list(obs.options),
                   produced_by='CwScreenWishTrial', sig=sig)
    gs.write_logic(gs.wish_trial_opts_xy, list(obs.option_points),
                   produced_by='CwScreenWishTrial', sig=sig)
