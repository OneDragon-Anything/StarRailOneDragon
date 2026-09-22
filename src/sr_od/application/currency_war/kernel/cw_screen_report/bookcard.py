"""星徽秘典屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口门判定 + 卡阵营名 OCR(「X星徽」去后缀,x 升序;标准化
生产半住观察侧——读数经 FACTIONS 注册表两段转换 + 候选点解算后组装
obs,op-layer.md §1.1 观察标准化门/选择坐标观察上报)。report 摄入点 =
operations/cw_screen/cw_screen_bookcard.py::
``CwScreenBookcard.observe``(观察 node);辖域边界:动作事实
``chosen_tome`` 不收编,留守重入裁决点。
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
class CwScreenBookcardObs:
    """星徽秘典屏观察结果(摄入口 = :func:`report_screen_bookcard_obs`)。

    [索引定义] ``options`` = 「X星徽」去后缀阵营名经 FACTIONS 注册表两段
    转换的标准注册名(观察标准化门,任一候选转换失败/多候选命中同一
    注册名 = 观察失败,report 不达);列表序 = 画面物理卡位序(x 升序
    左→右,恒稳);空 = OCR 未读得,report 不写(双域一体)。

    [索引定义] ``option_points`` = 各候选卡槽位坐标,与 ``options`` 同序
    等长(x = OCR x 中心读数、y = x 近邻「星徽卡-N」建档中心,观察期一次
    解出);键 = ``options`` 列表下标 idx(0 起,左→右画面物理序,与策略器
    输出下标、动作词表 ``CwActionPickStarTomeParam.idx`` 同一坐标系零
    换算);取值时机 = 观察期快照(动作执行期恒稳,禁执行期现读现算);
    值形状 = 1080p 平铺元组 (x, y)(遥测 JSON 序列化安全形)。
    """

    on_screen: bool = False
    options: list[str] = field(default_factory=list)
    option_points: list[tuple[int, int]] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_bookcard_obs(gs: GameState, obs: CwScreenBookcardObs, *,
                               sig: ChannelSig | None = None) -> None:
    """星徽秘典屏观察上报:卡阵营名与候选点一并写 ``star_tome_opts`` /
    ``star_tome_opts_xy``(同门同写,op-layer.md §1.1 :35)。

    写点锚 = cw_screen_bookcard.py::``CwScreenBookcard.observe``(观察
    node 摄入);options 空 = OCR 未读得,不写(原写点「读得才写」闸逐位
    平移,双域一体);``chosen_tome`` 留守重入裁决点(动作事实边界)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenBookcard', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if not obs.options:
        return
    # 同序等长写端构造守卫(fields.md §3.4.5a):坐标域与名字域同一写门
    # 一并落容器,不等长 = 观察 bug,响亮暴露禁错位双写。
    if len(obs.option_points) != len(obs.options):
        raise AssertionError(
            '[cw][bookcard] 坐标域与名字域不同序等长(观察 bug): '
            f'len(option_points)={len(obs.option_points)} '
            f'len(options)={len(obs.options)}')
    gs.write_logic(gs.star_tome_opts, list(obs.options),
                   produced_by='CwScreenBookcard', sig=sig)
    gs.write_logic(gs.star_tome_opts_xy, list(obs.option_points),
                   produced_by='CwScreenBookcard', sig=sig)
