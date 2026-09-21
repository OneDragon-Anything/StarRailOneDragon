"""遭遇节点屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 分支候选卡 + 「剩余次数」入口稳定帧读数(同一稳定帧一次读)。
report 摄入点 = operations/cw_screen/cw_screen_encounter.py::
``CwScreenEncounter.observe``(观察 node);辖域边界:动作事实
``chosen_encounter`` 不收编,留守重入裁决面;``encounter_refresh_left``
观察写端在本 report(读缺跳写,剩余语义观察真值,机械先例 =
invest_env 的 ``env_refresh_left`` 摄入)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_events import EncounterOption
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    EncounterPayload,
    GameState,
    _validate_sig,
)


@dataclass
class CwScreenEncounterObs:
    """遭遇节点屏观察结果(现役 ``cw_screen_encounter.EncounterObservation``
    平移;摄入口 = :func:`report_screen_encounter_obs`)。

    [索引定义] ``options``:候选卡读取(cw_node_obs.read_encounter_options
    产物);列表序 = 画面物理卡位序(左→右,恒稳);空 = 读缺,report
    整函数早退不写(含 left,invest_env names 空先 return 同构)。

    [索引定义] ``refresh_left``:「剩余次数:N」入口稳定帧读数(取值
    时机 = 入口观察帧一次读,与候选同帧同源;None = 读缺,report
    跳写——容器留旧值由逐访问覆盖语义承接)。

    - ``screen``:稳定帧引用(实机识别域载体,与现役观察类一致)。
    """

    options: list[EncounterOption] = field(default_factory=list)
    refresh_left: int | None = None
    screen: Any = None


def report_screen_encounter_obs(gs: GameState, obs: CwScreenEncounterObs, *,
                                sig: ChannelSig | None = None) -> None:
    """遭遇屏观察上报:候选分支写 ``encounter`` 附加域 + 刷新剩余次数写
    ``encounter_refresh_left``(观察写端;读缺跳写——屏上数字即真值,
    用户裁定 2026-09-21)。

    写点锚 = cw_screen_encounter.py::``CwScreenEncounter.observe``(观察
    node 摄入;刷新链终结化后本函数零二次覆盖写调用点)。options 空 =
    读缺,整函数早退不写(含 left,invest_env names 空先 return 同构);
    ``chosen_encounter`` 留守(动作事实边界)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenEncounter', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if not obs.options:
        return
    gs.write_logic(gs.encounter,
                   EncounterPayload(options=list(obs.options)),
                   produced_by='CwScreenEncounter', sig=sig)
    if obs.refresh_left is not None:
        gs.write_logic(gs.encounter_refresh_left, int(obs.refresh_left),
                       produced_by='CwScreenEncounter', sig=sig)
