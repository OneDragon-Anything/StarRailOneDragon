"""投资策略屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口锚命中与稳定窗 + 逐卡读数(卡名, x, y;入口稳定帧
OCR 快照)。report 摄入点 = operations/cw_screen/cw_screen_invest_strategy.py::
``CwScreenInvestStrategy.observe``(观察 node);辖域边界:
``active_strategies`` 追加写点留守重入裁决;``strategy_refresh_used``
逐卡刷新计数出辖动作侧。
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
class CwScreenInvestStrategyObs:
    """投资策略屏观察结果(摄入口 = :func:`report_screen_invest_strategy_obs`)。

    - ``entry_ok``:入口锚命中且稳定窗内(True 才进决策;False = 复探
      超窗,观察侧 round_retry,report 不调)。
    - ``options``:(卡名, x, y) 元组列表;[索引定义] 列表序 = 画面物理
      卡位序(左→右,刷新建议 slots 与此序同坐标系);取值时机 = 入口
      稳定帧 OCR 快照。report 提取名序列写 ``invest_strategy_opts``;
      ``active_strategies`` 追加写点与逐卡刷新计数留守(动作事实与出辖
      边界)。
    - ``first_ocr_map``:观察段首帧 OCR 存底(G10 域;现役刷新链零重读后
      本域仅保留 payload 契约,链内不消费)。
    """

    entry_ok: bool = False
    options: list[tuple[str, int, int]] = field(default_factory=list)
    first_ocr_map: dict | None = None
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_invest_strategy_obs(gs: GameState,
                                      obs: CwScreenInvestStrategyObs, *,
                                      sig: ChannelSig | None = None) -> None:
    """投资策略屏观察上报:逐卡名写 ``invest_strategy_opts``。

    写点锚 = cw_screen_invest_strategy.py::``CwScreenInvestStrategy.observe``
    (观察 node 摄入)。决策与动作事实面留守:``active_strategies`` 追加写点
    (重入裁决点)/``strategy_refresh_used`` 逐卡刷新计数(出辖动作侧)
    均不收编。names 空 = OCR 未读得,不写(原写点「读得才写」闸
    逐位平移)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenInvestStrategy', mode='compute')
    _validate_sig(sig, ('logic_action',))
    names = [n for n, _x, _y in obs.options]
    if not names:
        return
    gs.write_logic(gs.invest_strategy_opts, list(names),
                   produced_by='CwScreenInvestStrategy', sig=sig)
