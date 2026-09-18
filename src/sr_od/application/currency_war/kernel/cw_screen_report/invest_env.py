"""投资环境屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 画面锚命中 + 环境卡读数(环境名, 卡 x 中心;入口稳定帧
OCR 快照)。report 摄入点 = operations/cw_screen/cw_screen_invest_env.py::
``CwScreenInvestEnv.observe``(观察 node);辖域边界:同函数尾段
``active_env`` 选卡时点写/portal 登记/授予置闩是决策与选卡落地语义面,
留守画面 op 不收编;刷新计数出辖。
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
class CwScreenInvestEnvObs:
    """投资环境屏观察结果(摄入口 = :func:`report_screen_invest_env_obs`)。

    - ``hit``:画面锚命中(标识-投资环境;False = 非本屏,观察侧早退,
      report 不调)。
    - ``options``:(环境名, 卡 x 中心) 元组列表;[索引定义] 列表序 =
      画面物理卡位序(左→右,与原 OCR x 近邻分流序一致,恒稳);取值
      时机 = 入口稳定帧 OCR 快照。report 提取名序列写 ``invest_env_opts``;
      ``active_env`` 选卡时点写为决策面,留守画面 op(动作事实边界)。
    """

    hit: bool = False
    options: list[tuple[str, int]] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_invest_env_obs(gs: GameState, obs: CwScreenInvestEnvObs, *,
                                 sig: ChannelSig | None = None) -> None:
    """投资环境屏观察上报:环境名写 ``invest_env_opts``。

    写点锚 = cw_screen_invest_env.py::``CwScreenInvestEnv.observe``(观察
    node 摄入)。决策面写点留守画面 op(``_decide_and_act`` 尾段:
    ``active_env`` 选卡时点写/portal 登记/授予置闩——选卡落地语义,非观察
    记账)。names 空 = OCR 未读得,不写(原写点「读得才写」闸逐位平移)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenInvestEnv', mode='compute')
    _validate_sig(sig, ('logic_action',))
    names = [n for n, _x in obs.options]
    if not names:
        return
    gs.write_logic(gs.invest_env_opts, list(names),
                   produced_by='CwScreenInvestEnv', sig=sig)
