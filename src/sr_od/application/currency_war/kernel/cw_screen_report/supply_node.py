"""补给节点屏观察契约与上报(kernel 纯数据;权威版本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 节点内门判定 + 逐列选项读取(每列角色+装备,列数动态)+
「剩余次数：N」同帧读数。report 摄入点 =
operations/cw_screen/cw_screen_supply_node.py::``CwScreenSupplyNode.observe``
(观察 node);适用范围边界:动作事实 ``chosen_supply`` 不并入;``supply_refresh_left``
观察写端在本 report(读缺跳写,剩余语义观察真值,机械先例 =
invest_env 的 ``env_refresh_left`` 摄入)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_events import SupplyOption
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    SupplyPayload,
    _validate_sig,
)


@dataclass
class CwScreenSupplyNodeObs:
    """补给节点屏观察结果(摄入口 = :func:`report_screen_supply_node_obs`)。

    [索引定义] ``options`` = 逐列选项(cw_node_obs.read_supply_options
    产物);列表序 = 画面物理列序(左→右,列数动态 3-5 禁写死,恒稳);
    空 = 读缺(画面 op 空候选分支 = 零点击终结交回),report 不写 ``supply``。元素类型 =
    ``SupplyOption``(kernel.cw_events;与 ``SupplyPayload.options`` 元素
    声明同型)。

    [索引定义] ``refresh_left`` = 刷新剩余次数(屏上「剩余次数：N」读数,
    取值时机 = 入口观察帧一次读,与选项同帧同源;None = 读缺,report
    跳写——状态容器留旧值由逐访问覆盖语义承接)。
    """

    in_node: bool = False
    options: list[SupplyOption] = field(default_factory=list)
    refresh_left: int | None = None
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_supply_node_obs(gs: GameState, obs: CwScreenSupplyNodeObs, *,
                                  sig: ChannelSig | None = None) -> None:
    """补给屏观察上报:选项写 ``supply`` 附加域 + 刷新剩余次数写
    ``supply_refresh_left``(观察写端;读缺跳写——屏上数字即真值,
    用户裁定 2026-09-21)。

    写点定位 = cw_screen_supply_node.py::``CwScreenSupplyNode.observe``
    (观察 node 摄入;原写点以「本分支将调用 decide」为前提取
    ``[o for o, _ in opts]``,元素类型对齐 ``SupplyPayload.options`` 声明)。
    options 空 = 读缺(画面 op 空候选分支 = 零点击终结交回),整函数早退不写(含 left,
    invest_env names 空先 return 同构);``chosen_supply`` 留在(动作事实
    边界)。

    函数体尾部挂打捞人才库族检查(check_strategy_supply_salvage,单点
    接入调用覆盖实机和模拟器两边:live op 直调 / sim 呈现与刷新 / sim op 观察改道链全过
    本口)——插入位置在早退**之后** = 读缺帧刻意不发放(无画面证据帧不发放),
    R-entry 实际触发时点 = 进入补给阶段后的首个成功观察帧,读缺局发放
    顺延(发放源 = 场字段 unchosen_supply 非 本帧状态容器 supply,时点顺延
    语义无害);同阶段观察上报多次由「消费即清」幂等承接。sim 局同过
    本口:未持卡/未选集 None 双门早退零发放(fail-closed)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenSupplyNode', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if not obs.options:
        return
    gs.write_logic(gs.supply, SupplyPayload(options=list(obs.options)),
                   produced_by='CwScreenSupplyNode', sig=sig)
    if obs.refresh_left is not None:
        gs.write_logic(gs.supply_refresh_left, int(obs.refresh_left),
                       produced_by='CwScreenSupplyNode', sig=sig)
    from sr_od.application.currency_war.kernel.cw_effect_inventory import (
        check_strategy_supply_salvage,
    )
    check_strategy_supply_salvage(gs, sig)
