"""专家邀请函屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 弹窗门判定 + 四卡区羁绊解析 + 羁绊面板现读计数(弹窗帧一次
读)。report 摄入点 = operations/cw_screen/cw_screen_expert_invite.py::
``CwScreenExpertInvite.observe``(观察 node);辖域边界:动作事实
``chosen_expert`` 不收编,留守重入裁决点;羁绊面板读数 helper 住
obs/ 桶,归观察侧,kernel 禁直依。
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
    读数失败 = {}(现金为王兜底语义由观察侧原样携带)。

    [索引定义] ``card_points`` = 四卡区点击坐标,与 ``card_bonds`` 同序等长
    (坐标系 = 「卡-1..卡-4」区序,0 基下标 = ``card_bonds`` 同一卡下标
    坐标系,与选卡词表 ``CwActionPickExpertInviteParam.idx`` 同序零换算);
    取值时机 = 弹窗帧观察期快照(``area_center`` 现取,动作执行期恒稳);
    值形状 = 1080p 平铺元组 (x, y)(遥测 JSON 序列化安全形)。任一卡区
    建档缺失 = 坐标域转换失败,整域 None 随名字域同门照报(部分列表会
    错位 idx 坐标系,禁;:34 欠账清偿批同名同坐标一次落净)。

    [索引定义] ``cash_point`` = 「卡-现金为王」区中心(词表特形 idx=-1 的
    独立坐标,不进列表防 -1 负下标歧义);取值时机同 ``card_points``;
    缺失 = None 照报(同门)。

    载体语义 = ``ExpertInvitePayload`` 四字段打包(card_bonds/board/
    card_points/cash_point 同门一并上报)。
    """

    on_screen: bool = False
    card_bonds: list[str | None] = field(default_factory=list)
    board: dict[str, int] = field(default_factory=dict)
    # [索引定义] 坐标域(见类 docstring):写入端 = 专家邀请函观察上报
    # (与 card_bonds 同门一并写;op-layer.md §1.1 选择坐标观察上报,
    # fields.md §3.4.5a);sim 无画面识别不建模恒 None。
    card_points: list[tuple[int, int]] | None = None
    cash_point: tuple[int, int] | None = None
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_expert_invite_obs(gs: GameState,
                                    obs: CwScreenExpertInviteObs, *,
                                    sig: ChannelSig | None = None) -> None:
    """专家邀请函屏观察上报:弹窗载体写 ``expert_invite``。

    写点锚 = cw_screen_expert_invite.py::``CwScreenExpertInvite.observe``
    (观察 node;``ExpertInvitePayload`` 四字段同门一并写——card_bonds/
    board/card_points/cash_point,op-layer.md §1.1 :35 坐标随观察一并入
    容器;board 读数失败 = {} 的现金为王兜底语义由观察侧原样携带);
    ``chosen_expert`` 留守重入裁决点(动作事实边界)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenExpertInvite', mode='compute')
    _validate_sig(sig, ('logic_action',))
    # 同序等长写端构造守卫(fields.md §3.4.5a):坐标域与名字域同一写门
    # 一并落容器,不等长 = 观察 bug,响亮暴露禁错位双写(四卡区定长 4,
    # 卡 i ↔ card_points[i] 同序;读端不做长度调和)。
    if obs.card_points is not None \
            and len(obs.card_points) != len(obs.card_bonds):
        raise AssertionError(
            '[cw][expert_invite] 坐标域与名字域不同序等长(观察 bug): '
            f'len(card_points)={len(obs.card_points)} '
            f'len(card_bonds)={len(obs.card_bonds)}')
    gs.write_logic(
        gs.expert_invite,
        ExpertInvitePayload(card_bonds=list(obs.card_bonds),
                            board=dict(obs.board),
                            card_points=(None if obs.card_points is None
                                         else list(obs.card_points)),
                            cash_point=obs.cash_point),
        produced_by='CwScreenExpertInvite', sig=sig)
