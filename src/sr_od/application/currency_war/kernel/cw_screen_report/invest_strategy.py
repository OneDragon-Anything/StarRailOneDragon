"""投资策略屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口锚命中与稳定窗 + 一次读全(逐卡读数 (卡名, x, y) + 逐卡
刷新剩余次数配对)。report 摄入点 = operations/cw_screen/
cw_screen_invest_strategy.py::``CwScreenInvestStrategy.observe``(观察
node);辖域边界:选择事实(active_strategies)经动作落地链写(动作 op
立即自上报 → gain_invest_strategy,正本 = gain-chain.md);``strategy_
refresh_left`` 观察写端在本 report(读缺键跳写)。
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

    - ``entry_ok``:入口锚命中且在窗内(True 才进决策;False = 复探
      超窗,观察侧 round_retry,report 不调)。
    - ``options``:(卡名, x, y) 元组列表;[索引定义] 列表序 = 画面物理
      卡位序(左→右,刷新建议 slots 与此序同坐标系);取值时机 = 入口
      帧一次读全 OCR 快照。report 提取名序列写 ``invest_strategy_opts``。
    - ``refresh_slots``:逐卡刷新剩余次数配对,[索引定义] 列表序与
      ``options`` 同下标(0 基画面卡位序);元素 = (剩余次数, 计数文本
      center-x, center-y) 或 None(该槽读缺);取值时机 = 同一稳定帧
      一次读全后 ``pair_refresh_counts_to_slots`` 配对(标准化转换住
      观察侧)。report 逐槽摄入 ``strategy_refresh_left``(键 = 规范
      卡名;None 槽跳写)。决策环零识别,直接消费本载荷。
    - ``first_ocr_map``:观察段首帧 OCR 存底(payload 契约保留,链内
      不消费)。
    """

    entry_ok: bool = False
    options: list[tuple[str, int, int]] = field(default_factory=list)
    refresh_slots: list[tuple[int, int, int] | None] = field(
        default_factory=list)
    first_ocr_map: dict | None = None
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_invest_strategy_obs(gs: GameState,
                                      obs: CwScreenInvestStrategyObs, *,
                                      sig: ChannelSig | None = None) -> None:
    """投资策略屏观察上报:逐卡名写 ``invest_strategy_opts`` + 逐卡刷新
    剩余次数合并写 ``strategy_refresh_left``(观察写端;读缺键跳写、
    已观察键覆盖——屏上数字即真值,用户裁定 2026-09-21)。

    写点锚 = cw_screen_invest_strategy.py::``CwScreenInvestStrategy.
    observe``(观察 node 摄入)。names 空 = OCR 未读得,不写(原写点
    「读得才写」闸逐位平移)。刷新键 = ``normalize_invest_name`` 归一
    (容器字段键口径申报,免双坐标系换算)。
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
    # 刷新剩余次数观察写端(与 options 同帧一次读全;键 = 规范卡名)
    from sr_od.application.currency_war.kernel.cw_investments import (
        normalize_invest_name,
    )
    left_map = dict(gs.strategy_refresh_left.value or {})
    wrote = False
    for i, (name, _x, _y) in enumerate(obs.options):
        slot = obs.refresh_slots[i] if i < len(obs.refresh_slots) else None
        if slot is None:
            continue   # 该槽读缺 = 跳写,值留观察覆盖
        left_map[normalize_invest_name(name)] = int(slot[0])
        wrote = True
    if wrote:
        gs.write_logic(gs.strategy_refresh_left, left_map,
                       produced_by='CwScreenInvestStrategy', sig=sig)
