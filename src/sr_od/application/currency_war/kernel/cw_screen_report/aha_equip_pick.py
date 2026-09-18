"""顿悟装备选择屏观察契约(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口裁决:门判定 + 稳定帧引用。
**空决策形态,无 report 接口**(推进型屏无对账面/
无容器域,完备锁对本侧断言 report 函数不在场;辖域边界——本屏现役
零观察性容器写点,无可收编面)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CwScreenAhaEquipPickObs:
    """顿悟装备选择屏观察结果(统一形态:门判定 + 帧引用)。"""

    on_screen: bool = False
    screen: Any = None
