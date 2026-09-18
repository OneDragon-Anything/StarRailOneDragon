"""骇入策划屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = overlay 门判定 + 左右两卡 OCR 桶 join(入口帧一次读)。
report 写点转录来源 = operations/cw_screen/cw_screen_planner.py::
``_handle_overlay`` 写槽(锚 :213);辖域边界 = design.md §2.3(本屏
无 chosen 写端,零动作事实面)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_events import PlannerOption
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    _validate_sig,
)


@dataclass
class CwScreenPlannerObs:
    """骇入策划屏观察结果(摄入口 = :func:`report_screen_planner_obs`)。

    [索引定义] ``options`` 恒两元素;列表序/``PlannerOption.idx`` = 画面
    物理卡位(0 = 左卡 / 1 = 右卡,与点卡 area 同坐标系,恒稳);取值
    时机 = 入口帧 OCR 桶 join 快照。
    """

    on_screen: bool = False
    options: list[PlannerOption] = field(default_factory=list)
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_planner_obs(gs: GameState, obs: CwScreenPlannerObs, *,
                              sig: ChannelSig | None = None) -> None:
    """骇入策划屏观察上报:两卡选项写 ``planner_opts``。

    写点锚 = cw_screen_planner.py::``_handle_overlay`` 写槽(锚 :213;
    原写点恒写两卡 OCR 桶,无空门直写——空桶照写,防线逐位平移)。
    """
    if sig is None:
        sig = ChannelSig(family='logic_action',
                         actor='CwScreenPlanner', mode='compute')
    _validate_sig(sig, ('logic_action',))
    gs.write_logic(gs.planner_opts, list(obs.options),
                   produced_by='CwScreenPlanner', sig=sig)
