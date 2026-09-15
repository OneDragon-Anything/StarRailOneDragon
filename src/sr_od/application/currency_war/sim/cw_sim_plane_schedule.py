"""sim 重做·位面结构与节点序列(M03)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M03 / U19 定稿口径:

- P1 = 9 节点、P2 = 7 节点,序列 = 默认环境地面真值表
  (``docs/game/currency_war/research/plane_schedule_observed.md``,
  P1 42 局零反例);有投资策略环境的局序列与默认一致(7 局对照);
- 序列本身不随机:旧 ``sample_node_sequence`` 的 0.92/0.96 变异掷点
  按 U19 删除(42 局零反例强证据优先,变异位存在性候实机数据);
- P3 无完整观测 → 补采前 P3 **不运行**:进场即 game_over 并披露
  ``p3_unobserved``(U19;禁设回退先验,禁插值)。
"""
from __future__ import annotations

#: 节点类型词表(NodeKey.kind 合法值;与容器/日程表同域)。
NODE_KINDS: frozenset[str] = frozenset({
    'reward', 'battle', 'supply', 'encounter', 'boss',
})

#: P1 地面真值序列(9 节点;奖励→奖励→战斗→战斗→补给→战斗→遭遇→奖励→boss,
#: plane_schedule_observed.md 42 局零反例)。
P1_NODE_SEQUENCE: tuple[str, ...] = (
    'reward', 'reward', 'battle', 'battle', 'supply',
    'battle', 'encounter', 'reward', 'boss',
)

#: P2 地面真值序列(7 节点;战斗→战斗→补给→战斗→遭遇→奖励→boss,同上)。
P2_NODE_SEQUENCE: tuple[str, ...] = (
    'battle', 'battle', 'supply', 'battle', 'encounter', 'reward', 'boss',
)

#: 逐位面真值表(键 = 位面 1 基;P3 无完整观测不入表,§2.2 M03)。
PLANE_NODE_TABLES: dict[int, tuple[str, ...]] = {
    1: P1_NODE_SEQUENCE,
    2: P2_NODE_SEQUENCE,
}


class P3UnobservedError(RuntimeError):
    """P3 序列无完整观测时的显式停机(设计稿 §2.2 M03:补采前 sim 只
    支持 P1+P2 段运行;补采归实机批,禁回退先验)。"""


def node_sequence_of(plane: int) -> tuple[str, ...]:
    """位面节点类型序列真值(地面真值表;P3 → :class:`P3UnobservedError`)。"""
    seq = PLANE_NODE_TABLES.get(int(plane))
    if seq is None:
        raise P3UnobservedError(
            f'位面 {plane} 节点序列无完整观测(p3_unobserved;补采归实机批,'
            '重做设计稿 §2.2 M03/U19:禁回退先验)')
    return seq


def validate_sequences() -> None:
    """真值表结构守卫(模块自检;长度=位面轮数、类型词表在册)。

    消费面 = 模块导入期与测试;P1=9/P2=7 的轮数真值
    (plane_schedule_observed.md)在此显式钉住,序列错位在导入期炸错
    而非局中静默漂移。
    """
    expected_lengths: dict[int, int] = {1: 9, 2: 7}
    for plane, seq in PLANE_NODE_TABLES.items():
        if len(seq) != expected_lengths[plane]:
            raise ValueError(
                f'P{plane} 序列长度 {len(seq)} ≠ 地面真值 '
                f'{expected_lengths[plane]}(plane_schedule_observed.md)')
        unknown = set(seq) - NODE_KINDS
        if unknown:
            raise ValueError(f'P{plane} 序列含集外节点类型: {sorted(unknown)}')


validate_sequences()
