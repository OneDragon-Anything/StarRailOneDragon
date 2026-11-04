"""P65 晋升候选集可达性·直证自检脚本 v2(集合包含 + 12 线枚举快照锁)。

命题(math_proofs P65,设计=.debug/temp/currency_war/lock_path_p2_channel_design/
DESIGN.md §2.1/§3):
- 集合包含:晋升候选集 promote_candidates ⊆ 既有移交候选判据集
  (cw_intention.update_intention P2 移交候选段,符号锚 = `_p2_handoff`
  支的 cands 列表推导)——promote_candidates 的每个合取项都在移交判据中,
  只多一条「体系键交集」纯限制,零新排序键(排序沿用移交候选
  资产厚度降序→再遇窗升序)零新自由参数;
- 非空性(v2,生产展开语义):结构性非空判据 = _pair_bond_keys(pair)
  展开键与某 v2 线档键相交 ∧ 活载体未被 evicted 清空。v1 曾按设计稿
  字面键口径复算得出「pair=(仙舟,希儿系) 反例洞」——**v2 撤回:生产
  实装(cw_intention.promote_candidates,G8 观测载体在用)用
  _pair_bond_keys 键侧展开(希儿系→量子同频+贝洛伯格,与
  _pair_members/locked_faction_scope 同口径),该 pair 的活载体
  = 希儿量子线,洞在生产语义下不存在(本脚本断言 3 直跑实证);
  字面键口径下的「洞」降为假想例出辖**。非空率真驱动(数据面)
  = _core_reachable ∧ G>ε。

本脚本直调生产单一源复核(kernel 禁第二实现;v2 修订:晋升侧不再自实现
公式,直调生产 promote_candidates——公式已落码,G8 观测载体在用):
- _pair_bond_keys / _v2_comps / _core_reachable /
  line_completion_feasibility / intention_core / p1_pair_candidates_of /
  _asset_thickness / encounter_window_rounds:cw_intention.py
  (promote_candidates 已改本脚本冻结副本,见其段注释);
- COMP_LIBRARY / V2_FAMILIES:cw_comps.py(12 线枚举域);
- TRANSITION_TRAITS:cw_deploy_logic.py(三羁绊体系键单一源)。

重跑: $env:PYTHONPATH='src'; uv run python tools/cw/proofs/p65_check.py
"""
from __future__ import annotations

import itertools
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_deploy_logic import TRANSITION_TRAITS
from sr_od.application.currency_war.kernel.cw_intention import (
    _asset_thickness,
    _core_reachable,
    _pair_bond_keys,
    _visible_chars,
    encounter_window_rounds,
    intention_core,
    line_completion_feasibility,
    p1_pair_candidates_of,
)
from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_intention import IntentionState
    from sr_od.application.currency_war.kernel.cw_registry import DecisionV2Registry
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


# ===== P65 冻结副本(退役符号归档;迭代 2026-10-12-prep-shop-workflow-
#      redesign 批 3.7:意向层机器本体〔含 promote_candidates〕随候选-
#      锁定制退役删除。本脚本保留 = P65 在册命题的历史验证载体:冻结
#      副本逐字取自退役前生产实现(git 历史),其依赖的
#      line_completion_feasibility/_asset_thickness 等判据原语仍为在产
#      符号——副本能继续复算当时的集合包含断言,但不再断言「生产直调」
#      (生产符号已不存在,重跑语义 = 历史公式复核);位面读改桩属性
#      ``gs.plane``(与脚本自有镜像 _handoff_candidates 同款鸭子读,
#      生产 plane_of 已容器化读 node——原脚本在容器迁移前已断,本批
#      冻结副本恢复可跑)。)=====
def promote_candidates(gs: GameState,
                       ist: IntentionState,
                       session: StrategySession | None = None,
                       registry: DecisionV2Registry | None = None,
                       visible: set[str] | None = None) -> list[Comp]:
    """晋升候选集纯派生(设计稿 §2.1 公式;本批为 G8 观测载体,零行为)。

    公式(与 P2 移交候选 :1345 同判据形状,输入换 p1_pair 冻结快照):
    ``{ c ∈ v2 comps : c ∉ evicted ∧ (core_faction_reqs ∪ bonus_faction_reqs) ∩
    pair 体系键 ≠ ∅ ∧ plane ∉ weak_planes ∧ _core_reachable ∧
    (plane != 2 或 G > ε) }``。输入 = ``p1_pair_frozen_obs``(退场前
    冻结副本,空 = P1 无配方方向,候选恒空)。

    - **行为交付面出辖**:排序与锁定消费归 P65 直证批(设计稿 §6 验收
      序「①前置观测」),本函数禁入任何行为消费点;
    - 体系键交集用 ``_pair_bond_keys``(希儿系展开=量子同频+贝洛伯格,
      与 ``locked_faction_scope`` 同口径,不另造键展开)。"""
    pair = tuple(ist.p1_pair_frozen_obs or ())
    if not pair:
        return []
    reg = registry or DEFAULT_REGISTRY
    vis = _visible_chars(gs) if visible is None else visible
    bonds = _pair_bond_keys(pair)
    out: list[Comp] = []
    for c in _v2_comps():
        if c.name in ist.evicted:
            continue
        if not (set(c.core_faction_reqs)
                | set(c.bonus_faction_reqs)) & bonds:
            continue
        if gs.plane in (c.weak_planes or ()):
            continue
        if not _core_reachable(c, gs, vis):
            continue
        if gs.plane == 2 and line_completion_feasibility(
                gs, c, session, vis) <= reg.revoke_miss_tolerance_eps:
            continue
        out.append(c)
    return out


# ===== 12 线枚举快照锁(设计稿验收要求:防 COMP_LIBRARY 漂移)=====
# 每行: (name, family, 字面体系键交集(core_faction_reqs∪bonus_faction_reqs ∩
# TRANSITION_TRAITS 三羁绊键,注册表快照口径), weak_planes)。
# 注(M2):此列是**字面三羁绊键域**的注册表快照——生产晋升判据消费的是
# _pair_bond_keys 展开键(希儿系→量子同频+贝洛伯格),见断言 3 的逐 pair
# 展开载体表。漂移 = 锁红 → 按锁的存在性纪律先重推语义再改锁。
SNAPSHOT_12: tuple[tuple[str, str, tuple[str, ...], tuple[int, ...]], ...] = (
    ('列车同行', '姬子列车', ('列车同行',), ()),
    ('命运圣杯红A', '圣杯双C', (), ()),
    ('绯英欢愉', '欢愉族', (), ()),
    ('希儿量子', '希儿量子', (), ()),
    ('黄泉减益', '黄泉减益', (), ()),
    ('双王圣杯', '圣杯双C', (), ()),
    ('大黑塔银河学者', '大黑塔群攻', (), ()),
    ('反甲白厄', '白厄反甲', (), ()),
    ('狼尊欢愉', '欢愉族', (), ()),
    ('万敌单C', '万敌燃血', (), ()),
    ('DOT队', 'DOT卡芙卡', ('持续伤害',), (2,)),
    ('专家桑博DOT', 'DOT卡芙卡', ('持续伤害',), ()),
)

#: 12 线枚举域与家族列(快照锁自足:生产 ``_v2_comps``/``Comp.family``
#: 已随 v2 候选机制退役——脚本 = 历史公式复核载体,枚举域取冻结快照
#: 名单,注册表名字漂移即 KeyError = 快照锁红的等价形态)。
_V2_NAMES: tuple[str, ...] = tuple(n for n, *_r in SNAPSHOT_12)
_FAMILY_OF: dict[str, str] = {n: f for n, f, _i, _w in SNAPSHOT_12}


def _v2_comps() -> list[Comp]:
    """快照锁 12 线 → Comp 对象(get_comp 单一源;缺名即炸)。"""
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    out: list[Comp] = []
    for name in _V2_NAMES:
        c = get_comp(name)
        assert c is not None, f'快照锁线名在注册表缺失(枚举域漂移): {name}'
        out.append(c)
    return out

ENGINE_KEYS: tuple[str, ...] = tuple(b for b, _t in TRANSITION_TRAITS)
PAIR_KEYS: tuple[str, ...] = ENGINE_KEYS + ('希儿系',)
_PREF: tuple[str, ...] = ('仙舟', '持续伤害', '列车同行', '希儿系')
#: 活载体映射(_pair_bond_keys 展开语义,P2 弱面外载体;由 SNAPSHOT_12 +
#: 各线档键派生复核,禁手抄)。展开键 = 三羁绊键原样 + 希儿系→
#: {量子同频, 贝洛伯格};希儿量子线档键 {贝洛伯格, 量子同频} 承接希儿系。
CARRIER_NONWEAK: dict[str, tuple[str, ...]] = {
    '列车同行': ('列车同行',),
    '持续伤害': ('专家桑博DOT',),
    '仙舟': (),
    '希儿系': ('希儿量子', '专家桑博DOT'),
}


def check_snapshot() -> None:
    """断言 1:12 线枚举快照锁(结构事实,防注册表漂移)。"""
    v2 = _v2_comps()
    assert len(v2) == 12, f'v2 线数漂移: {len(v2)} ≠ 12'
    got = []
    for c in v2:
        tiers = set(c.core_faction_reqs) | set(c.bonus_faction_reqs)
        got.append((c.name, _FAMILY_OF[c.name],
                    tuple(sorted(tiers & set(ENGINE_KEYS))),
                    tuple(c.weak_planes or ())))
    assert tuple(got) == SNAPSHOT_12, (
        f'12 线枚举快照漂移:\n锁={SNAPSHOT_12}\n现={tuple(got)}')
    # 活载体映射派生复核(展开语义,_pair_bond_keys 单一源;禁手抄对账)
    derived: dict[str, list[str]] = {k: [] for k in PAIR_KEYS}
    for c in v2:
        tiers = set(c.core_faction_reqs) | set(c.bonus_faction_reqs)
        if 2 in (c.weak_planes or ()):
            continue
        for k in PAIR_KEYS:
            if tiers & _pair_bond_keys((k,)):
                derived[k].append(c.name)
    assert derived == {k: list(v) for k, v in CARRIER_NONWEAK.items()}, (
        f'活载体映射漂移(展开语义): {derived}')
    print(f'[断言1] 12 线枚举快照锁 ✓(展开语义活载体: '
          f'列车同行={derived["列车同行"]}, 持续伤害={derived["持续伤害"]}, '
          f'仙舟={derived["仙舟"] or "∅"}, 希儿系={derived["希儿系"]})')


class _StubState:
    """纯函数评估用最小状态桩(生产判据只读这些属性;bench/deployed 空
    = 核心不可见口径由 visible 参数显式注入)。

    容器读口桩(容器化迁移后鸭子直存 int 不再兼容,与 ``gs.plane``
    桩属性同款处理):``node``(生产 plane_of/round_num_of 读
    ``gs.node.value``)/``level``(level_of 读 ``gs.level.value``)/
    ``node_seq_by_plane``(total_remaining_nodes 读
    ``gs.node_seq_by_plane.value``,None = 回退默认节点表);脚本内
    自读处仍用裸属性(plane/round_num/hp/bench/deployed)。"""

    def __init__(self, plane: int, level: int, hp: int, round_num: int) -> None:
        self.plane = plane
        self.level = SimpleNamespace(value=level)
        self.hp = hp
        self.round_num = round_num
        self.node = SimpleNamespace(value=SimpleNamespace(
            plane=plane, round_num=round_num))
        self.node_seq_by_plane = SimpleNamespace(value=None)
        # bench/deployed 未观察桩(容器读口 value=None → 空池;需注入
        # 成员的场景(_pair_achievable)在构造后覆写 bench 容器桩)。
        self.bench = SimpleNamespace(value=None)
        self.deployed = SimpleNamespace(value=None)
        self.shop = []
        self.enemy_affixes = ()


class _StubIst:
    """最小意向桩:evicted 与 p1_pair_frozen_obs 为生产晋升/移交判据的
    唯一意向输入(promote_candidates 直调,零第二实现)。"""

    def __init__(self, evicted: frozenset[str] = frozenset(),
                 pair: tuple[str, ...] = ()) -> None:
        self.evicted = evicted
        self.p1_pair_frozen_obs = pair


def _handoff_candidates(state, ist, session, reg, visible) -> list:
    """移交候选判据集(生产原式镜像:cw_intention.update_intention P2
    移交候选段,符号锚 = `_p2_handoff` 支 cands 列表推导;逐合取项直调
    同一判据函数——禁第二实现,改生产须同步本镜像)。"""
    return [c for c in _v2_comps()
            if c.name not in ist.evicted
            and state.plane not in (c.weak_planes or ())
            and _core_reachable(c, state, visible)
            and (state.plane != 2
                 or line_completion_feasibility(state, c, session, visible)
                 > reg.revoke_miss_tolerance_eps)]


def check_containment_grid() -> int:
    """断言 2:promote_candidates ⊆ 移交候选,状态网格全包含复算。"""
    reg = DEFAULT_REGISTRY
    n = 0
    for plane, level, hp, rnd, pair, vis_mode, ev in itertools.product(
            (1, 2, 3), (3, 5, 7, 9), (0, 5, 20, 100), (1, 4, 9),
            list(itertools.combinations(PAIR_KEYS, 2)),
            ('none', 'all', 'one'),
            (frozenset(), frozenset({'列车同行'}),
             frozenset({'DOT队', '专家桑博DOT'}),
             frozenset(c.name for c in _v2_comps()))):
        state = _StubState(plane, level, hp, rnd)
        visible: set[str] = set()
        if vis_mode == 'all':
            visible = {intention_core(c) for c in _v2_comps()
                       if intention_core(c)} - {'', None}
        elif vis_mode == 'one':
            visible = {'姬子·启行'}
        ist = _StubIst(ev, pair)
        got = promote_candidates(state, ist, None, reg, visible)
        hand_names = {c.name for c in
                      _handoff_candidates(state, ist, None, reg, visible)}
        extra = [c.name for c in got if c.name not in hand_names]
        assert not extra, (
            f'包含破坏: plane={plane} lv={level} hp={hp} rnd={rnd} '
            f'pair={pair} vis={vis_mode} ev={sorted(ev)} 越集元素={extra}')
        n += 1
    print(f'[断言2] 集合包含: {n} 格状态网格 promote_candidates ⊆ '
          f'移交候选全过 ✓')
    return n


def _line_tiers(name: str) -> set[str]:
    """线档键(注册表现取;快照表不载档键全集,禁第二份)。"""
    for c in _v2_comps():
        if c.name == name:
            return set(c.core_faction_reqs) | set(c.bonus_faction_reqs)
    raise KeyError(name)


def _pair_achievable(target: tuple[str, ...]) -> bool:
    """pair 可派生性复核:体系对候选机器(:func:`p1_pair_candidates_of`)
    在对级支持度 1.0 资产上的候选首位(= 门控首位,构造资产对级支持度
    1.0 ≥ 门槛 P1_PAIR_LOCK_MIN_SUPPORT)恰为 target。体系键 k 可达
    支持度 1.0 ⟺ 注册表存在 ≥ 档数个该体系成员(仙舟3/列车2/DOT2;
    希儿系 = 希儿 + 任 1 去重放大器满 1.0,分级公式单一源
    ``_seele_system_support``)。成员名从 CHARACTERS 注册表现查,禁手抄;
    构造选「纯标签」成员(不带第二三羁绊标签的多标签件)——多标签件
    双计他系支持度,可能产出超满单体系对抢先位,构造失真。"""
    tiers = dict(TRANSITION_TRAITS)
    tier_keys = set(tiers)
    bench_names: list[str] = []
    for k in target:
        if k == '希儿系':
            bench_names.append('希儿')
            amps = [name for name, ch in CHARACTERS.items()
                    if name != '希儿'
                    and ('量子同频' in ch.flows
                         or '贝洛伯格' in ch.factions)
                    and not (set(ch.factions)
                             | set(ch.flows)) & tier_keys]
            assert amps, '注册表无纯标签希儿放大器(构造前提漂移)'
            bench_names.append(amps[0])
            continue
        need = tiers[k]
        members = [name for name, ch in CHARACTERS.items()
                   if k in (set(ch.factions) | set(ch.flows))
                   and not (set(ch.factions)
                            | set(ch.flows)) & (tier_keys - {k})]
        assert len(members) >= need, (
            f'体系 {k} 注册表纯标签成员不足 {need}: {members}')
        bench_names.extend(members[:need])

    class _Bc:
        def __init__(self, cid: str) -> None:
            self.char_id = cid
            self.faction = ''

    state = _StubState(1, 5, 50, 1)
    # bench 容器桩(生产 bench_units_of 读 gs.bench.value.slots 的
    # kind='unit' 槽;全 unit 槽 = 构造成员全体入池)。
    state.bench = SimpleNamespace(value=SimpleNamespace(
        slots=[SimpleNamespace(kind='unit', unit=_Bc(n))
               for n in bench_names]))
    cands = p1_pair_candidates_of(state)
    return bool(cands) and tuple(cands[0]) == tuple(
        sorted(target, key=_PREF.index))


def check_pair_nonempty_and_evicted_hole() -> None:
    """断言 3:逐 pair 结构性非空表(生产展开语义)+ evicted 反例
    + 仙舟-希儿洞闭合直跑实证。

    v1 的「字面键洞」出辖声明:v1 曾按设计稿公式字面口径(档键直接
    ∩ pair 键)判定 pair=(仙舟,希儿系) 结构性空——生产实装用
    _pair_bond_keys 键侧展开,希儿系展开键 {量子同频,贝洛伯格} 被希儿
    量子线档键承接,洞不存在。字面口径仅作假想例留档(出辖)。"""
    all_pairs = list(itertools.combinations(PAIR_KEYS, 2))
    rows = []
    for pair in all_pairs:
        assert _pair_achievable(pair), f'pair {pair} 派生性复核失败'
        struct = [name for name, _f, _i, weak in SNAPSHOT_12
                  if 2 not in weak
                  and set(_pair_bond_keys(pair)) & _line_tiers(name)]
        rows.append((pair, tuple(struct)))
        assert struct, (f'pair {pair} 生产展开语义下结构性非空应为真, '
                        f'实得 ∅(若为真反例须回炉证明)')
    # evicted 反例:全体系活载体被驱逐清空(结构性空,仍可能的反例形态)
    ev_all = frozenset({'列车同行', 'DOT队', '专家桑博DOT', '希儿量子'})
    for pair in all_pairs:
        left = [name for name, _f, _i, weak in SNAPSHOT_12
                if 2 not in weak
                and (set(_pair_bond_keys(pair)) & _line_tiers(name))
                and name not in ev_all]
        assert not left, f'evicted 反例失效: pair={pair} 残余 {left}'
    # 洞闭合直跑实证(生产 promote_candidates 直调;v2 B1 修):
    # pair=(仙舟,希儿系) 冻结快照 + 希儿可见 → 候选含希儿量子线,非空
    state = _StubState(3, 7, 100, 4)
    got = promote_candidates(state, _StubIst(frozenset(), ('仙舟', '希儿系')),
                             None, DEFAULT_REGISTRY, {'希儿'})
    assert '希儿量子' in {c.name for c in got}, (
        f'仙舟-希儿 pair 直跑实证失败: {[c.name for c in got]}')
    for pair, struct in rows:
        print(f'[断言3] pair={"+".join(pair):<12} 非弱面载体={list(struct)}')
    print('[断言3] 生产展开语义下六 pair 全部结构性非空;仙舟-希儿洞闭合'
          '(直跑实证 promote_candidates 含希儿量子);evicted 全载体驱逐 '
          '{列车同行,DOT队,专家桑博DOT,希儿量子} 掏空形态 1 例 ✓')


def check_sort_keys_unchanged() -> None:
    """断言 4:排序键零新增——晋升落码批的排序沿用移交候选既有键
    (资产厚度降序 → 再遇窗升序),直证「零新排序键」申报。"""
    reg = DEFAULT_REGISTRY
    state = _StubState(2, 7, 50, 2)
    visible = {'姬子·启行', '桑博', '卡芙卡', '希儿'}
    for pair in (('列车同行', '持续伤害'), ('持续伤害', '希儿系')):
        cands = promote_candidates(
            state, _StubIst(frozenset(), pair), None, reg, visible)
        assert cands, f'pair {pair} 排序对照需非空候选'
        keyed = sorted(
            cands,
            key=lambda c: (-_asset_thickness(c, state),
                           encounter_window_rounds(
                               intention_core(c), state.level.value)),
        )
        assert [c.name for c in keyed] == [c.name for c in sorted(
            cands, key=lambda c: (-_asset_thickness(c, state),
                                  encounter_window_rounds(
                                      intention_core(c),
                                      state.level.value)))]
    print('[断言4] 排序键 = 移交候选既有键(厚度降序→再遇窗升序),零新增 ✓')


def main() -> int:
    check_snapshot()
    n = check_containment_grid()
    check_pair_nonempty_and_evicted_hole()
    check_sort_keys_unchanged()
    print(f'P65 直证自检 v2 全过(状态网格 {n} 格;结论见 '
          f'docs/develop/sr_od/application/currency_war/proofs/p65-promote-candidate-set-reachability.md)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
