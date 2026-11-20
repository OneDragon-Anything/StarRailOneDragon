"""茶歇奖励屏观察契约(kernel 纯数据;权威版本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

**无 report 形态**(推进型空决策,先例 = prep_locked_return:本屏零
game state 写点,obs 构造即弃零保留——门判定布尔直接驱动节点流转;
完备测试分侧断言 = report 函数不在场)。观察类住本文件,
import 构造即可(先例 = cw_screen_report/prep_locked_return.py)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CwScreenTeaBreakRewardObs:
    """茶歇奖励屏观察结果(推进型空决策:构造即弃,零 game state 写点)。

    ``on_screen`` = 入口门判定布尔(标识-奖励标题命中);消费点 = op 的
    观察 node(直接驱动节点流转,不留实例副本)。
    """

    on_screen: bool = False
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None
