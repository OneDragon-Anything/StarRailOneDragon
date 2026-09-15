"""sim 重做·随机种子流键子流(重做设计稿 §2.0.4 全局语义)。

动机(设计稿 §2.0.4):旧引擎单 rng 实例按消耗序耦合,任何模块加/删
一次采样就扰动全流(回归门被迫锁「rng 消耗序不变」);流键化后各模块
随机序独立,模块规格可独立演化。

硬约束:
- 全部随机量按 ``random.Random(f'{seed}#{stream_key}')`` 派生子流,
  流键 = 模块号 + 局内坐标(如 ``M05/p1/r3`` 发牌、``M13/p1/r7`` 战斗);
- 禁模块间共享 rng 实例;禁策略器读 sim 流(策略自带随机时用独立
  流键 ``strategy/*``)。
"""
from __future__ import annotations

import random


def stream_rng(seed: int, stream_key: str) -> random.Random:
    """按流键派生子流(全 sim 随机量的唯一取流口;禁绕过自建 rng)。"""
    return random.Random(f'{int(seed)}#{stream_key}')
