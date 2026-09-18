"""开商店原子观察契约(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2)。

观察面 = 入口裁决:门判定 + 稳定帧引用(商店框 op,推进型只读/导航
变体)。**空决策形态,无 report 接口**(design.md §2.2:推进型无对账面/
无容器域,完备锁对本侧断言 report 函数不在场;design.md §2.3 辖域
边界——本 op 现役零观察性容器写点,商店容器的容器写端在
read_game_state 漏斗)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CwOpOpenShopObs:
    """开商店原子观察结果(商店框 op,推进型只读/导航变体:门判定 +
    帧引用)。"""

    on_screen: bool = False
    screen: Any = None
