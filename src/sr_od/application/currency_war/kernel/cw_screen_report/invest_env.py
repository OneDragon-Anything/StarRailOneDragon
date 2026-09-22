"""投资环境屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 画面锚命中 + 一次读全(环境卡读数 (环境名, 卡 x 中心) + 全局
刷新剩余次数)。report 摄入点 = operations/cw_screen/cw_screen_invest_env.py::
``CwScreenInvestEnv.observe``(观察 node);辖域边界:选择事实
(active_env)经动作落地链写(动作 op 立即自上报 → gain_invest_env,
正本 = gain-chain.md);``env_refresh_left`` 观察写端在本 report
(读缺跳写)。
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
      时机 = 入口帧一次读全 OCR 快照。report 提取名序列写
      ``invest_env_opts``。
    - ``refresh``:全局刷新剩余次数读数(屏上「剩余次数：N」,整组重掷
      单钮单计数);元素 = (剩余次数, 计数文本 center-x, center-y) 或
      None(读缺);取值时机 = 同一帧一次读全。report 摄入写
      ``env_refresh_left``(None = 跳写)。决策环零识别,直接消费本载荷。
    """

    hit: bool = False
    options: list[tuple[str, int]] = field(default_factory=list)
    refresh: tuple[int, int, int] | None = None
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_invest_env_obs(gs: GameState, obs: CwScreenInvestEnvObs, *,
                                 sig: ChannelSig | None = None) -> None:
    """投资环境屏观察上报:环境名写 ``invest_env_opts`` + 全局刷新剩余
    次数写 ``env_refresh_left``(观察写端;读缺跳写——屏上数字即真值,
    正本 = game_state/fields.md §3.4.3 / screens/op-layer.md §1.4 剩余
    语义写端)。

    写点锚 = cw_screen_invest_env.py::``CwScreenInvestEnv.observe``(观察
    node 摄入)。选择事实不在本 report(active_env 经动作落地链获得链写,
    正本 = game_state/gain-chain.md)。names 空 = OCR 未读得,整函数早退
    不写(含 env_refresh_left,摄入序 = 候选先于计数)。
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
    if obs.refresh is not None:
        gs.write_logic(gs.env_refresh_left, int(obs.refresh[0]),
                       produced_by='CwScreenInvestEnv', sig=sig)
