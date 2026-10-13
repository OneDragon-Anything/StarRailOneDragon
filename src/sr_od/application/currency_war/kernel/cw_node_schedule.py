"""货币战争节点日程真值表(kernel 纯数据件;零依赖)。

设计正本 = ``docs/develop/sr_od/application/currency_war/sim/sim-design.md``
(§3.3 位面过渡/节点序列)现役口径:

- 节点身份唯一表示 = ``(位面, 轮)`` 序位元组(:data:`NodePos`,1 基,
  字典序即节点全序);「推进 +1」后继 = :func:`sequence_next`(全仓
  唯一后继实现,位面切换在此发生),``None`` 返回 = 超出建模域,
  调用方按局终处理;
- P1 = 9 节点、P2 = 7 节点,序列 = 默认环境地面真值表
  (``docs/game/currency_war/research/plane_schedule_observed.md``,
  P1 42 局零反例);**默认环境**序列与地面真值一致;改节点序列的
  投资环境经 :func:`resolve_plane_node_seqs` 修饰(首个 = 「人身意外险」
  boss 前插补给,修饰结果落 GameState 场字段 ``node_seq_by_plane``,
  运行时消费面读场字段,本模块不逐点重推);
- 序列本身不随机:旧 ``sample_node_sequence`` 的 0.92/0.96 变异掷点
  按 U19 删除(42 局零反例强证据优先,变异位存在性候实机数据);
- P3 无完整观测 → 补采前 P3 **不运行**:进场即 game_over 并披露
  ``p3_unobserved``(U19;禁设回退先验,禁插值)。

**模块归属**:真值表住 kernel(依赖方向架构锁:``node_advance`` 声明的
``next_screen`` 推导权威源 = 本表 + ``effective_node_ord``,推导在
``report_node_advance``(kernel),kernel 禁 import sim
(``cw_deploy_logic`` 在册);sim 后端同源 import 本表。
"""
from __future__ import annotations

from typing import TypeAlias

#: 节点序位(位面, 轮次),二元素整数元组,1 基。节点身份唯一表示:
#: 字典序 = 有效节点序列按位面拼接展平的全序(位面主序下前缀和单调恒等)。
NodePos: TypeAlias = tuple[int, int]

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

#: 「首领节点前插入补给阶段」环境白名单(id 107 原文直读,
#: PlazaPortal('107'));规则单一 = 每个 'boss' 位前插一个 'supply'
#: (P1/P2 各一;P3 补采后自动适用)。替换型改节点环境(战争边疆,
#: dag T-18)是映射非插入的另一形状,不入本表(T-8 设计裁决点 1);
#: 键 = 归一名(cw_investments.normalize_invest_name 口径)。
ENV_NODE_SUPPLY_BEFORE_BOSS: frozenset[str] = frozenset({'人身意外险'})


class P3UnobservedError(RuntimeError):
    """P3 序列无完整观测时的显式停机(设计稿 §2.2 M03:补采前 sim 只
    支持 P1+P2 段运行;补采归实机批,禁回退先验)。"""


def resolve_plane_node_seqs(env_name: str) -> dict[int, tuple[str, ...]]:
    """环境名 → 逐位面节点序列(**修饰规则唯一计算点**,只在环境注册写
    场字段时执行一次——运行时消费面读 GameState 场字段
    ``node_seq_by_plane``,不逐点重推;T-8 设计 §2.1 用户裁定:修饰结果
    落逻辑态,插入的补给节点是备战画面可观察的真实节点,场字段为观察
    对账正本)。

    归一名 ∈ 白名单 → 遍历默认表、每个 ``'boss'`` 位前插一个
    ``'supply'`` 返回新表;否则原样返回默认表(默认表 = 不可变元组,
    原样复用,禁原地改)。P3 不在默认表 → 修饰不产出 P3 键
    (p3_unobserved 拦截现状不变,补采后按同规则自动适用)。
    """
    if str(env_name or '') not in ENV_NODE_SUPPLY_BEFORE_BOSS:
        return dict(PLANE_NODE_TABLES)
    out: dict[int, tuple[str, ...]] = {}
    for plane, seq in PLANE_NODE_TABLES.items():
        mods: list[str] = []
        for kind in seq:
            if kind == 'boss':
                mods.append('supply')
            mods.append(kind)
        out[plane] = tuple(mods)
    return out


def node_sequence_of(plane: int,
                     seqs: dict[int, tuple[str, ...]] | None = None
                     ) -> tuple[str, ...]:
    """位面节点类型序列真值(P3 → :class:`P3UnobservedError`)。

    ``seqs`` 给定(= GameState 场字段现值)→ 字段即权威,返回
    ``seqs[plane]``(缺键 = 位面 3 等,仍 :class:`P3UnobservedError`);
    None → 默认表(未注册读回退;P1 内修饰制与默认制逐值同,回退无窗)。
    """
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    seq = tables.get(int(plane))
    if seq is None:
        raise P3UnobservedError(
            f'位面 {plane} 节点序列无完整观测(p3_unobserved;补采归实机批,'
            '重做设计稿 §2.2 M03/U19:禁回退先验)')
    return seq


def sequence_next(pos: NodePos,
                  seqs: dict[int, tuple[str, ...]] | None = None,
                  ) -> NodePos | None:
    """节点序位的后继(「推进 +1」全仓唯一实现,位面切换在此发生)。

    四态契约:

    - 位面内 ``pos[1] < len(seq)`` → 同位面下一轮 ``(p, r+1)``;
    - 位面末 → 下一位面首 ``(p+1, 1)``;
    - pos 自身位面不在序列表,或位面末的下一位面无序列表(P3 未观测,
      含 P2 末)→ ``None`` = 超出建模域,调用方按局终处理;
    - modeled 位面内 ``pos[1] > len(seq)``(损坏坐标)→ ``ValueError``
      响亮,禁静默跨位面。

    ``seqs`` 给定(= GameState 场字段现值)→ 字段即权威;None → 默认表
    (未注册读回退;与 :func:`node_sequence_of` 同参约定)。
    """
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    plane, r = int(pos[0]), int(pos[1])
    seq = tables.get(plane)
    if seq is None:
        return None
    if r > len(seq):
        raise ValueError(
            f'节点序位 {plane}-{r} 超出位面 {plane} 序列长度 {len(seq)}'
            '(modeled 位面内损坏坐标,禁静默跨位面)')
    if r < len(seq):
        return (plane, r + 1)
    if plane + 1 in tables:
        return (plane + 1, 1)
    return None


def node_pos_of(ordinal: int,
                seqs: dict[int, tuple[str, ...]] | None = None
                ) -> tuple[int, int]:
    """节点线性序 → (位面, 轮次)(1 基;按序列表变长累加反解)。

    ``seqs`` 给定(= 场字段现值)→ 按修饰制逐位面长度累加(与正解
    :func:`node_ordinal_of` 同表互逆);None → 默认表(变长累加,非
    固定位面长度——固定 9 仅在 P1=9 时与变长重合,非通用前提)。
    超界(位面 3 等)= :class:`P3UnobservedError` 响亮,调用方先行
    拦截局终。
    """
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    acc = 0
    for plane in sorted(tables):
        length = len(tables[plane])
        if ordinal <= acc + length:
            return plane, ordinal - acc
        acc += length
    raise P3UnobservedError(
        f'节点线性序 {ordinal} 超出序列表辖域(P1+P2;P3 未观测,'
        '调用方须先行拦截为局终)')


def node_round_cap(plane: int,
                   seqs: dict[int, tuple[str, ...]] | None = None) -> int:
    """位面 round 读数上限(观察值域守卫单一源;T-8 设计 §2.5 用户裁定:
    正常按位面固定上限,随环境调整——cap 与序列同源 = 有效序列长度,
    序列修则 cap 随动,零第二真相源、零独立常量表)。三态:

    - ``seqs`` 给定且含该位面 → ``len(seqs[plane])``(场字段现值,
      修饰局 P1=10/P2=8);
    - ``seqs`` 给定但缺该位面(场字段恒只含键 {1,2},P3 必落此态)
      → 12 余量(与 P3 未观测口径一致;余量数值单一源 = 本 helper,
      不另设常量);
    - ``seqs`` None → 默认表长度(未注册读回退;默认表缺该位面 = P3,
      同落 12 余量)。注意与现役恒 9 守卫不是逐位等价:P1 同为 9;
      P2 收紧 7 < 9(修饰局 P2 真长 8 由场字段覆盖,不受此回退影响);
      P3 放宽 12 > 9 余量(P3 补采批复核)。
    """
    if seqs is not None:
        seq = seqs.get(int(plane))
        return len(seq) if seq is not None else 12
    seq = PLANE_NODE_TABLES.get(int(plane))
    return len(seq) if seq is not None else 12


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

# 环境白名单结构卫生(模块自检;键归属校验 ⊆ INVESTMENT_ENVS 住
# cw_investments._validate_env_node_seq——本模块零依赖,反向校验不落
# 此,T-8 设计 §2.2)。
if not ENV_NODE_SUPPLY_BEFORE_BOSS \
        or any(not name for name in ENV_NODE_SUPPLY_BEFORE_BOSS):
    raise ValueError('ENV_NODE_SUPPLY_BEFORE_BOSS 结构卫生失败'
                     '(空表或空串元素)')
