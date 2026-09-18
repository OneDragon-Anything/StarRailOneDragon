"""专家邀请函屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 弹窗门判定 + 四卡区羁绊解析 + 羁绊面板现读计数(弹窗帧一次
读)。report 写点转录来源 = operations/cw_screen/cw_screen_expert_
invite.py::``_handle_overlay`` 写槽(锚 :221);辖域边界 = design.md
§2.3(动作事实 ``chosen_expert`` 不收编,留守重入裁决点;羁绊面板
读数 helper 住 obs/ 桶,归观察侧,kernel 禁直依)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    ExpertInvitePayload,
    GameState,
    _validate_sig,
)


@dataclass
class CwScreenExpertInviteObs:
    """专家邀请函屏观察结果(摄入口 = :func:`report_screen_expert_invite_obs`)。

    [索引定义] ``card_bonds`` = 四卡区羁绊解析;[索引定义] 下标 = 画面
    「卡-1..卡-4」物理区序(0 基,与判据返回的卡下标同坐标系,恒稳);
    取值时机 = 弹窗帧 OCR 解析期快照。``board`` = 弹窗帧羁绊面板现读计数;
    读数失败 = {}(现金为王兜底语义由观察侧原样携带)。载体语义 =
    ``ExpertInvitePayload`` 双输入打包。
    """

    on_screen: bool = False
    card_bonds: list[str | None] = field(default_factory=list)
    board: dict[str, int] = field(default_factory=dict)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_expert_invite_obs(gs: GameState,
                                    obs: CwScreenExpertInviteObs, *,
                                    sig: ChannelSig | None = None) -> None:
    """专家邀请函屏观察上报:弹窗载体写 ``expert_invite``。

    写点锚 = cw_screen_expert_invite.py::``_handle_overlay`` 写槽
    (锚 :221;``ExpertInvitePayload(card_bonds, board)`` 双输入打包;
    board 读数失败 = {} 的现金为王兜底语义由观察侧原样携带);
    ``chosen_expert`` 留守重入裁决点(design.md §2.3 动作事实边界)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenExpertInvite', mode='compute')
    _validate_sig(sig, ('logic_action',))
    gs.write_logic(
        gs.expert_invite,
        ExpertInvitePayload(card_bonds=list(obs.card_bonds),
                            board=dict(obs.board)),
        produced_by='CwScreenExpertInvite', sig=sig)
