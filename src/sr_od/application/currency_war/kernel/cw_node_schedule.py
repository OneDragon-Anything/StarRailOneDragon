"""货币战争节点日程真值表(kernel 纯数据件;零依赖)。

设计正本 = ``docs/develop/sr_od/application/currency_war/sim/sim-design.md``
(§3.3 位面过渡/节点序列)现役口径:

- 节点身份唯一表示 = ``(位面, 轮)`` 序位元组(:data:`NodePos`,1 基,
  字典序即节点全序);「推进 +1」后继 = :func:`sequence_next`(全仓
  唯一后继实现,位面切换在此发生),``None`` 返回 = 超出序列表,
  调用方按局终处理(现役 = 位面 3 末节点之后 = 对局胜利终局);
- P1 = 9、P2 = 7、P3 = 7 节点,序列 = 默认环境地面真值表
  (``docs/game/currency_war/research/plane_schedule_observed.md``,
  P1 42 局零反例;P3 = 2026-10-15 用户裁定入码,证据等级低于 P1/P2);
  **默认环境**序列与地面真值一致;改节点序列的投资环境经
  :func:`resolve_plane_node_seqs` 修饰(统一注册表
  :data:`ENV_NODE_REWRITE_RULES`,规则解释器单点,修饰结果落
  GameState 场字段 ``node_seq_by_plane``,运行时消费面读场字段,
  本模块不逐点重推);
- 序列本身不随机:旧 ``sample_node_sequence`` 的 0.92/0.96 变异掷点
  按 U19 删除(42 局零反例强证据优先,变异位存在性待实机数据);
- 三位面全序列均在表:推进超 P3 末节点(P3-7 boss 结算存活)后继 =
  ``None`` = 胜利终局(sim 侧披露 ``run_complete``);hp 归零 = 败局,
  语义归结算腿不经后继原语。

**模块归属**:真值表住 kernel(依赖方向架构锁:``node_advance`` 声明的
``next_screen`` 推导权威源 = 本表 + ``effective_node_pos``,推导在
``report_node_advance``(kernel),kernel 禁 import sim
(``cw_deploy_logic`` 已登记);sim 后端同源 import 本表。
"""
from __future__ import annotations

from typing import TypeAlias

#: 节点序位(位面,轮次),二元素整数元组,1 基。节点身份唯一表示:
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

#: P3 默认序列(7 节点;战斗→战斗→补给→战斗→遭遇→奖励→boss,与 P2 同型;
#: 来源 = plane_schedule_observed.md「裁定记录(用户,2026-10-15):位面 3
#: 默认序列」——单局实盘截图节点条全列 + 前缀结算实证,3-4 格结算标注
#: 冲突按裁决取节点条读法 = battle;证据等级低于 P1/P2 两行,后续实机局
#: 逐格复核义务见该文档「位面 3 观测现状」)。
P3_NODE_SEQUENCE: tuple[str, ...] = (
    'battle', 'battle', 'supply', 'battle', 'encounter', 'reward', 'boss',
)

#: 逐位面真值表(键 = 位面 1 基;三位面全序列在表)。
PLANE_NODE_TABLES: dict[int, tuple[str, ...]] = {
    1: P1_NODE_SEQUENCE,
    2: P2_NODE_SEQUENCE,
    3: P3_NODE_SEQUENCE,
}

#: 节点改写规则(两类封闭集):
#: - ``('insert_supply_before_boss',)`` 插入型:每个 ``'boss'`` 位前插一个
#:   ``'supply'``(「人身意外险」id 107 原文直读);
#: - ``('replace', 位面, 旧kind, 新kind)`` 替换型:指定位面把旧 kind 槽位
#:   换为新 kind(位面 = :data:`PLANE_NODE_TABLES` 键,1 基)。
NodeRewriteRule: TypeAlias = tuple[str] | tuple[str, int, str, str]

#: 统一节点改写注册表(改节点序列环境的单一户口;键 = 归一名,
#: cw_investments.normalize_invest_name 口径;值 = 规则元组的元组,按序
#: 应用,多规则正交可同 env 共存)。表外环境 = 无节点改写(白名单制,
#: 禁从效果原文自动猜规则;归属校验 = cw_investments._validate_env_node_seq)。
ENV_NODE_REWRITE_RULES: dict[str, tuple[NodeRewriteRule, ...]] = {
    # 「所有首领节点前都加入一个额外补给阶段」:插入型,P1/P2/P3 各一
    # (修饰后 P1=10/P2=8/P3=8)。
    '人身意外险': (('insert_supply_before_boss',),),
    # 「第三位面的所有战斗节点都替换为遭遇节点」(id 117):替换型;
    # 「战斗节点」= 类型读法仅普通战斗,奖励/首领/补给/遭遇四类不换
    # (词义边界四轴论证与用户裁定 = 投资环境迭代设计 T-18 §2.3/§8)。
    '战争边疆': (('replace', 3, 'battle', 'encounter'),),
}


class PlaneSeqMissingError(RuntimeError):
    """序列直查缺键的显式停机(序列表缺键防御:三位面默认序列均已在表,
    本异常仅拦损坏半态字段或越界位面的直查,禁静默回退)。"""


def resolve_plane_node_seqs(env_name: str) -> dict[int, tuple[str, ...]]:
    """环境名 → 逐位面节点序列(**修饰规则唯一计算点**,只在环境注册写
    场字段时执行一次——运行时消费面读 GameState 场字段
    ``node_seq_by_plane``,不逐点重推;设计 §2.1 用户裁定:修饰结果
    落逻辑态,插入/替换的节点是备战画面可观察的真实节点,场字段为
    观察对账正本)。

    统一规则解释器:注册表(:data:`ENV_NODE_REWRITE_RULES`)命中环境 →
    逐位面按序应用其规则元组;未命中 → 原样返回默认表(默认表 =
    不可变元组,原样复用,禁原地改)。规则语义:插入型 = 逐 ``'boss'``
    位前插一个 ``'supply'``;替换型 = 指定位面把旧 kind 槽位换为新 kind。
    未被任何规则触达的位面原样复用默认表元组(对象同一性,消费侧
    「修饰表与默认表逐值同」断言不因解释器重建而失真)。
    """
    rules = ENV_NODE_REWRITE_RULES.get(str(env_name or ''))
    if not rules:
        return dict(PLANE_NODE_TABLES)
    out: dict[int, tuple[str, ...]] = {}
    for plane, seq in PLANE_NODE_TABLES.items():
        mods: list[str] | None = None
        for rule in rules:
            if rule[0] == 'insert_supply_before_boss':
                src = seq if mods is None else mods
                mods = []
                for kind in src:
                    if kind == 'boss':
                        mods.append('supply')
                    mods.append(kind)
            else:
                _, tgt_plane, old_kind, new_kind = rule
                if int(tgt_plane) != plane:
                    continue
                src = seq if mods is None else mods
                mods = [new_kind if k == old_kind else k for k in src]
        out[plane] = tuple(mods) if mods is not None else seq
    return out


def node_sequence_of(plane: int,
                     seqs: dict[int, tuple[str, ...]] | None = None
                     ) -> tuple[str, ...]:
    """位面节点类型序列真值(缺键 → :class:`PlaneSeqMissingError`)。

    ``seqs`` 给定(= GameState 场字段现值)→ 字段即权威,返回
    ``seqs[plane]``(缺键 = 损坏半态或越界位面,仍
    :class:`PlaneSeqMissingError`);None → 默认表(未注册读回退;
    P1 内修饰制与默认制逐值同,回退无窗)。
    """
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    seq = tables.get(int(plane))
    if seq is None:
        raise PlaneSeqMissingError(
            f'位面 {plane} 不在节点序列表中(表键 {sorted(tables)};'
            '序列直查缺键禁静默回退)')
    return seq


def sequence_next(pos: NodePos,
                  seqs: dict[int, tuple[str, ...]] | None = None,
                  ) -> NodePos | None:
    """节点序位的后继(「推进 +1」全仓唯一实现,位面切换在此发生)。

    四态契约:

    - 位面内 ``pos[1] < len(seq)`` → 同位面下一轮 ``(p, r+1)``;
    - 位面末 → 下一位面首 ``(p+1, 1)``;
    - pos 自身位面不在序列表,或位面末的下一位面无序列表(现役 =
      位面 3 末,即对局走完)→ ``None`` = 超出序列表,调用方按局终
      处理(sim 侧 = 胜利终局);
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


def sequence_prev(pos: NodePos,
                  seqs: dict[int, tuple[str, ...]] | None = None,
                  ) -> NodePos | None:
    """节点序位的前驱(:func:`sequence_next` 的镜像逆原语,位面切换在此
    发生;现役消费面 = 环境发放锁的完胜提前改写,cw_env_grants)。

    四态契约(与 :func:`sequence_next` 逐态镜像):

    - 位面内 ``pos[1] > 1`` → 同位面上一轮 ``(p, r-1)``;
    - 位面首 → 前一位面末 ``(p-1, len(seq of p-1))``;
    - pos 自身位面不在序列表,或位面首的前一位面无序列表(现役 =
      位面 1 首 = 全序列起点)→ ``None``,调用方按「无前驱不回退」处理;
    - modeled 位面内 ``pos[1] > len(seq)``(损坏坐标)→ ``ValueError``
      响亮,禁静默跨位面(与后继原语同判)。

    ``seqs`` 给定(= GameState 场字段现值)→ 字段即权威;None → 默认表
    (与 :func:`node_sequence_of` 同参约定)。修饰域注意:前一位面长度取
    当前 ``seqs`` 现值——解锁序位按发放刻日程写入而前驱按改写刻日程
    回退,同窗追加修饰环境产生的长度差 = 已申报的修饰日程后到偏差
    (cw_investments 披露键 env_deploy_lock_modified_schedule_drift,
    一次登记有界)。"""
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    plane, r = int(pos[0]), int(pos[1])
    seq = tables.get(plane)
    if seq is None:
        return None
    if r > len(seq):
        raise ValueError(
            f'节点序位 {plane}-{r} 超出位面 {plane} 序列长度 {len(seq)}'
            '(modeled 位面内损坏坐标,禁静默跨位面)')
    if r > 1:
        return (plane, r - 1)
    prev_seq = tables.get(plane - 1)
    if prev_seq is None:
        return None
    return (plane - 1, len(prev_seq))


def node_round_cap(plane: int,
                   seqs: dict[int, tuple[str, ...]] | None = None) -> int:
    """位面 round 读数上限(观察值域守卫单一源;设计 §2.5 用户裁定:
    正常按位面固定上限,随环境调整——cap 与序列同源 = 有效序列长度,
    序列修则 cap 随动,零第二真相源、零独立常量表)。三态:

    - ``seqs`` 给定且含该位面 → ``len(seqs[plane])``(场字段现值,
      修饰局 P1=10/P2=8/P3=8);
    - ``seqs`` 给定但缺该位面(损坏半态)→ 12 余量(余量数值单一源 =
      本 helper,不另设常量);
    - ``seqs`` None → 默认表长度(未注册读回退;默认表含 P3=7)。
      注意与现役恒 9 守卫不是逐位等价:P1 同为 9;P2 收紧 7 < 9
      (修饰局 P2 真长 8 由场字段覆盖,不受此回退影响)。
    """
    if seqs is not None:
        seq = seqs.get(int(plane))
        return len(seq) if seq is not None else 12
    seq = PLANE_NODE_TABLES.get(int(plane))
    return len(seq) if seq is not None else 12


def validate_sequences() -> None:
    """真值表结构守卫(模块自检;长度=位面轮数、类型词表已登记)。

    消费面 = 模块导入期与测试;P1=9/P2=7/P3=7 的轮数真值
    (plane_schedule_observed.md)在此显式钉住,序列错位在导入期炸错
    而非局中静默漂移。
    """
    expected_lengths: dict[int, int] = {1: 9, 2: 7, 3: 7}
    for plane, seq in PLANE_NODE_TABLES.items():
        if len(seq) != expected_lengths[plane]:
            raise ValueError(
                f'P{plane} 序列长度 {len(seq)} ≠ 地面真值 '
                f'{expected_lengths[plane]}(plane_schedule_observed.md)')
        unknown = set(seq) - NODE_KINDS
        if unknown:
            raise ValueError(f'P{plane} 序列含集外节点类型: {sorted(unknown)}')


def validate_rewrite_rules() -> None:
    """改写注册表结构守卫(模块自检,import 即炸):规则形状封闭集——
    插入型单元素 / 替换型四元素(位面在真值表、kind ∈ NODE_KINDS、
    替换 old≠new);键非空、规则元组非空。非法形状在导入期炸错而非
    环境注册时静默失义。"""
    if not ENV_NODE_REWRITE_RULES:
        raise ValueError('ENV_NODE_REWRITE_RULES 空表(注册表必须显式留白'
                         '为空 dict 字面量,禁缺声明)')
    for name, rules in ENV_NODE_REWRITE_RULES.items():
        if not name:
            raise ValueError('ENV_NODE_REWRITE_RULES 含空串键')
        if not rules:
            raise ValueError(f'ENV_NODE_REWRITE_RULES[{name!r}] 空规则元组')
        for rule in rules:
            if not isinstance(rule, tuple) or not rule:
                raise ValueError(
                    f'规则形状非法({name!r}): {rule!r}(须为非空元组)')
            if rule[0] == 'insert_supply_before_boss':
                if len(rule) != 1:
                    raise ValueError(
                        f'插入型规则形状非法({name!r}): {rule!r}(单元素)')
            elif rule[0] == 'replace':
                if len(rule) != 4:
                    raise ValueError(
                        f'替换型规则形状非法({name!r}): {rule!r}'
                        '(四元素 = replace/位面/旧kind/新kind)')
                _, tgt_plane, old_kind, new_kind = rule
                if int(tgt_plane) not in PLANE_NODE_TABLES:
                    raise ValueError(
                        f'替换型规则位面 {tgt_plane} 不在真值表({name!r};'
                        f'表键 {sorted(PLANE_NODE_TABLES)})')
                if old_kind not in NODE_KINDS or new_kind not in NODE_KINDS:
                    raise ValueError(
                        f'替换型规则 kind 集外({name!r}): {old_kind!r}→'
                        f'{new_kind!r}(词表 {sorted(NODE_KINDS)})')
                if old_kind == new_kind:
                    raise ValueError(
                        f'替换型规则 old=new 无义({name!r}): {old_kind!r}')
            else:
                raise ValueError(
                    f'未知节点改写规则种类({name!r}): {rule[0]!r}'
                    '(封闭集 = insert_supply_before_boss / replace)')


validate_sequences()
validate_rewrite_rules()
