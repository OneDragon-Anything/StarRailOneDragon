"""遭遇节点屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 分支候选卡 + 「剩余次数」入口稳定帧读数(同一稳定帧一次读)。
report 写点转录来源 = operations/cw_screen/cw_screen_encounter.py::
``_decide_encounter_action`` 首写槽(锚 :207);辖域边界 = design.md
§2.3(动作事实 ``chosen_encounter``/``encounter_refreshed_in_visit`` 不
收编,留守决策与重入裁决面)与 §2.4(刷新计数记账全域出辖,
``refresh_left`` 只是观察 read)。
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

    - ``options``:候选卡读取(cw_node_obs.read_encounter_options 产物);
      空 = 读缺,report 不写容器(原写点早退闸逐位平移)。
    - ``refresh_left``:「剩余次数:N」入口稳定帧读数(分支刷新前置闸的
      语义事实;None = 读缺/未授予,失败安全按无刷新处理)。刷新计数
      记账出辖(design.md §2.4):本字段只是观察 read,不含计数写面。
    - ``screen``:稳定帧引用(刷新链执行半的文本锚定位同帧同源读)。
    """

    options: list[EncounterOption] = field(default_factory=list)
    refresh_left: int | None = None
    screen: Any = None


def report_screen_encounter_obs(gs: GameState, obs: CwScreenEncounterObs, *,
                                sig: ChannelSig | None = None) -> None:
    """遭遇屏观察上报:候选分支写 ``encounter`` 附加域。

    写点锚 = cw_screen_encounter.py::``_decide_encounter_action`` 首写槽
    (锚 :207;刷新链内的二次覆盖写同形,迁移批由「刷后重读 → 再调本
    函数」承载)。options 空 = 读缺不写(原写点早退闸逐位平移);
    ``encounter_refreshed_in_visit``/刷新计数/``chosen_encounter`` 均决策
    与动作事实面,不收编(design.md §2.3/§2.4)。
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
