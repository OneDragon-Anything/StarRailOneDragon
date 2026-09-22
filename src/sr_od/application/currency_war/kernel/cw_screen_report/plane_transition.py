"""位面过渡屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 提示门判定 + 底部全亮行读数构造的链值(行读数与 TokenCell
构造归观察侧)。report 摄入点 = operations/cw_screen/
cw_screen_plane_transition.py::``CwScreenPlaneTransition.observe``
(观察 node);辖域边界:纯观测写点,调用方的 best-effort 抑制
contextlib.suppress 留守观察侧,本函数不吞异常。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    NodeChain,
    _validate_sig,
    maybe_emit_chain_diff,
)


@dataclass
class CwScreenPlaneTransitionObs:
    """位面过渡屏观察结果(摄入口 = :func:`report_screen_plane_transition_obs`)。

    ``chain`` = 过渡屏底部全亮行读数构造的链值(行读数与 TokenCell 构造
    归观察侧;None = 行空/读缺,report 不写,诚实缺位)。
    """

    on_screen: bool = False
    chain: NodeChain | None = None
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_plane_transition_obs(gs: GameState,
                                       obs: CwScreenPlaneTransitionObs, *,
                                       sig: ChannelSig | None = None) -> None:
    """位面过渡屏观察上报:链观察写 ``node_path``/``node_path_baseline``。

    写点锚 = cw_screen_plane_transition.py::``CwScreenPlaneTransition.observe``
    (观察 node;行读数与 TokenCell 构造归观察侧,obs.chain 进即写)。
    防御逐位平移:chain 缺 = 行空/读缺不写(诚实缺位);非开局且
    节点镜像缺 = 行归属位面不可知禁猜跳写;基线幂等门(基线已有不覆写)。
    离场快照链 diff 触发(snapshot=True 豁免两帧门)随写点同迁。纯观测
    写点:调用方的 best-effort 抑制(contextlib.suppress)由观察侧保留,
    本函数不吞异常。
    """
    if sig is None:
        # family='obs'/screen=画面建档名/mode='read' 沿原写点(观察渠道①)。
        sig = ChannelSig(family='obs', actor='CwScreenPlaneTransition',
                         screen='货币战争-位面过渡', mode='read')
    _validate_sig(sig, ('obs',))
    if obs.chain is None:
        return
    mirror = gs.node.value
    opening = mirror is None and gs.node_hist_ord is None
    if not opening and mirror is None:
        return   # 非开局且镜像缺:行归属位面不可知,禁猜跳写
    gs.observe(gs.node_path, obs.chain, evidence='transition_snapshot',
               sig=sig)
    if opening and gs.node_path_baseline.value is None:
        gs.observe(gs.node_path_baseline, obs.chain,
                   evidence='transition_row', sig=sig)
    # 链 diff 触发:离场快照豁免两帧门(单帧即终审,链正本 §4)
    maybe_emit_chain_diff(gs, snapshot=True, in_mutation_window=False,
                          sig=sig)
