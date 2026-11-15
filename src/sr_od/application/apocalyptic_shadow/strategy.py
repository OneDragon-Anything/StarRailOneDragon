"""末日幻影选人策略(占位):随机抽队。

用户裁定(2026-11-16):选人策略暂时乱选,先把流程串起来——本模块即占位
接缝,未来换真策略(按弱点/练度/体系配队)时替换实现,app 编排不变。
"""
from __future__ import annotations

import random


def pick_random_teams(pool: list[str], team_count: int) -> list[str]:
    """从候选池无放回随机抽 ``team_count`` 行 × 4 人的名单,按行序拼接。

    Args:
        pool: 候选角色中文名列表(须与编队屏列表卡识别名同口径)
        team_count: 节点行数(2 = 01-03 双节点,3 = 星启 04;执行期实读)

    Returns:
        长度 ``team_count*4`` 的名字列表,前 4 个 = 节点一队伍,以此类推。

    Raises:
        ValueError: 池人数不足(调用方转节点失败,消息可直接展示)。
    """
    need = team_count * 4
    if len(pool) < need:
        raise ValueError(
            f'角色池 {len(pool)} 人不足 {team_count} 节点所需 {need} 人,'
            f'请在配置 character_pool 补充')
    return random.sample(pool, need)
