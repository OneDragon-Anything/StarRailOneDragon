"""武装箱选择屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口锚复验(标识-请选择)+ OCR 卡名行(2-8 字过滤,x 升序;
标准化生产半住观察侧——读数经装备注册表两段转换 + 坐标解点后组装 obs,
op-layer.md §1.1 观察标准化门/选择坐标观察上报)。report 摄入点 =
operations/cw_screen/cw_screen_box_pick.py::``CwScreenBoxPick.observe``
(观察 node);辖域边界:本屏选卡即终结,无 chosen 写端;选错不可逆的
「卡名空交回重派」闸留守观察侧。
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
class CwScreenBoxPickObs:
    """武装箱选择屏观察结果(摄入口 = :func:`report_screen_box_pick_obs`)。

    [索引定义] ``card_names`` = 标准注册装备名(OCR 卡名行 2-8 字过滤后
    经装备注册表两段转换标准化,任一候选转换失败 = 观察失败,report 不
    达);列表序 = 画面物理卡位序(x 升序左→右,恒稳);重复名合法
    (四卡可能同名,同装备多张,逐候选独立归一);空 = 变体字型/动画帧
    读缺,观察侧交回外循环重派,report 不调(禁盲点首卡)。

    [索引定义] ``points`` = 各卡点击坐标(卡名带下方避让几何,观察期
    一次解出);键 = ``card_names`` 列表下标 idx(0 起,左→右画面物理序,
    与策略器输出下标/动作词表 param.idx 同一坐标系零换算);取值时机 =
    观察期快照(动作执行期恒稳);值形状 = 1080p 平铺元组 (x, y);
    与 ``card_names`` 同序等长(写端构造守卫,读端不做长度调和)。
    """

    on_screen: bool = False
    card_names: list[str] = field(default_factory=list)
    points: list[tuple[int, int]] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_box_pick_obs(gs: GameState, obs: CwScreenBoxPickObs, *,
                               sig: ChannelSig | None = None) -> None:
    """武装箱选择屏观察上报:标准卡名写 ``box_card_names``、点击坐标写
    ``box_card_names_xy``(同一调用同一写门一并写;坐标单一真相源 =
    观察上报,op-layer.md §1.1 :35)。

    写点锚 = cw_screen_box_pick.py::``CwScreenBoxPick.observe``(观察 node;
    调用方「卡名空 = round_fail 交回重派」闸已保证非空到达,原写点无
    空门——防线逐位平移不加强不减弱)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenBoxPick', mode='compute')
    _validate_sig(sig, ('logic_action',))
    # 同序等长写端构造守卫(fields.md §3.4.5a):坐标域与名字域同一写门
    # 一并落容器,不等长 = 观察 bug,响亮暴露禁错位双写。
    if len(obs.points) != len(obs.card_names):
        raise AssertionError(
            '[cw][boxpick] 坐标域与名字域不同序等长(观察 bug): '
            f'len(points)={len(obs.points)} '
            f'len(card_names)={len(obs.card_names)}')
    gs.write_logic(gs.box_card_names, list(obs.card_names),
                   produced_by='CwScreenBoxPick', sig=sig)
    gs.write_logic(gs.box_card_names_xy, list(obs.points),
                   produced_by='CwScreenBoxPick', sig=sig)
