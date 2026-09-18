"""补给节点屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 节点内门判定 + 逐列选项读取(每列角色+装备,列数动态)。
report 写点转录来源 = operations/cw_screen/cw_screen_supply_node.py::
``_do_action`` 写槽(锚 :228);辖域边界 = design.md §2.3(动作事实
``chosen_supply`` 不收编)与 §2.4(刷新面出辖,``supply_refresh_used``
写端不转录)。
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
    空 = 读缺(CARD_BODY 兜底路径),report 不写 ``supply``。元素类型 =
    ``SupplyOption``(kernel.cw_events;与 ``SupplyPayload.options`` 元素
    声明同型)。
    """

    in_node: bool = False
    options: list[SupplyOption] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_supply_node_obs(gs: GameState, obs: CwScreenSupplyNodeObs, *,
                                  sig: ChannelSig | None = None) -> None:
    """补给屏观察上报:选项写 ``supply`` 附加域。

    写点锚 = cw_screen_supply_node.py::``_do_action`` 写槽(锚 :228;
    原写点以「本分支将调用 decide」为前提取 ``[o for o, _ in opts]``,
    元素类型对齐 ``SupplyPayload.options`` 声明)。options 空 = 读缺
    (CARD_BODY 兜底路径),不写(原写点「读得才写」闸逐位平移);
    ``chosen_supply``/刷新计数留守(design.md §2.3/§2.4)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenSupplyNode', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if not obs.options:
        return
    gs.write_logic(gs.supply, SupplyPayload(options=list(obs.options)),
                   produced_by='CwScreenSupplyNode', sig=sig)
