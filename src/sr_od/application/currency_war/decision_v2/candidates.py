"""决策框架 v2 层1:候选生成器(ADR-0290;纯函数 state→list[Candidate])。

**载体批(W35)层1 换源**(裁决终版第三选项;不再 import line_strategy/
线库/桥池):

- 目标件 → ``session.v3_hoard``(``cw_intention.hoard_target_set`` 的
  char_targets——意向线骨架采购集/跨线骨架/兜底线,买侧唯一消费面);
- 体系方向件 → ``cw_system_cards.SYSTEM_CARDS`` 引擎件(铁三角+希儿,
  点3 见即买;``decision_v2.discipline.engine_seed_wants``);
- 插件消费 → ``cw_plugins.PLUGIN_LIBRARY``+``PLUGIN_DISABLE_MATRIX``
  (定义节 class5 四层过滤:机制冲突拒/过半线=骨架非插件/上场有位才买
  ——bench 不囤插件);
- pair/copy/carry_gate/bond_fallback 语义不变,谓词移植到
  ``decision_v2.discipline``(方向输入=意向分层,非 locked_line)。

枚举语义(与骨架版一致):买=店内每张可识别卡×标签;卖=bench 每件×理由
(生成器层过滤掉豁免件——engine_seed 年龄豁免 ADR-0289 §5/3合1 素材
豁免/r408 同轮已买);LevelUp/RefreshShop;Deploy=围栏序 top-K;合成=
3合1 独立通道。纯函数(只读 state/session,不 mutate),sim 可测。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_economy import xp_click_cost
from sr_od.application.currency_war.cw_plugins import (
    PLUGIN_LIBRARY,
    plugin_disabled,
)
from sr_od.application.currency_war.cw_state import (
    Action,
    BenchChar,
    BuyCard,
    DeployMove,
    GameState,
    LevelUp,
    RefreshShop,
    SellBench,
    ShopCard,
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.discipline import (
    copy_swap_useless,
    engine_char_names,
    engine_seed_wants,
    has_same_name_copy,
    in_round_sold,
    pair_wants,
    round_sell_blocked,
    seed_age_blocked,
    star_weighted_copies,
)
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)

#: 买候选标签集 / 卖候选标签集 / 动作类枚举(检查项 coverage 消费)
BUY_TAGS: frozenset[str] = frozenset({
    'line_carry', 'line_opportunistic', 'bridge_core', 'engine_seed',
    'plugin', 'pair', 'copy', 'bond_fallback', 'carry_gate',
})
SELL_TAGS: frozenset[str] = frozenset({
    'off_target', 'for_gold', 'free_bench',
})
#: 全部合法动作类(候选生成覆盖面检查的基准;ADR-0290 层1 枚举义务)
ACTION_CLASSES: frozenset[str] = frozenset({
    'buy', 'sell', 'levelup', 'refresh', 'deploy', 'synthesize',
})


@dataclass
class Candidate:
    """一个候选动作(层2过滤域标记 + 层4解释字段)。"""

    action: Action                 # 执行体(BuyCard/SellBench/…)
    tag: str                       # 标签(过滤域标记,无优先级语义)
    source: str                    # 生成器名(解释/判读)
    merge: bool = False            # 3合1 合成候选(买第 3 张同名副本)
    needs_slot: bool = False       # 买时 bench 满(需先腾位;[32])
    breakdown_hint: dict = field(default_factory=dict)   # 生成期注记


@dataclass
class Synthesize:
    """3合1 合成候选的执行体(候选层本地类型,ADR-0296;不进
    cw_state.Action 联合——合成在执行层是**自动机制**:
    simulate/_merge_bench 在同名同星 ≥3 时就地合并,无独立点击)。
    """

    name: str                      # 同名组角色名
    star: int                      # 组内星级(合并后 star+1)
    copies: int = 3                # 组内份数(≥3)


#: 检查网消费的模块级别名(cw_sim_checks 供给一致性探针;实现单一源
#: 在 discipline——载体批移植,别名保持检查网 import 面稳定)
_star_weighted_copies = star_weighted_copies
_copy_swap_useless = copy_swap_useless   # 检查网/锁测试的模块级别名(单一源在 discipline)


def _copy_swap_blocked(card: ShopCard, state: GameState,
                       session: StrategySession,
                       registry: DecisionV2Registry | None = None) -> bool:
    """r410 守卫×目标件豁免(ADR-0303/0304:默认关=守卫直通;
    豁免代码留作 A/B 通道——载体批沿用原裁决,开关语义不变)。"""
    if (registry is not None and registry.copy_swap_target_exempt
            and card.name in _target_names(state, session)):
        return False
    return copy_swap_useless(card, state, session)


def _owned_factions(state: GameState) -> set[str]:
    """board∪bench 的已有阵营集合(bond_fallback 凑档判据输入)。"""
    out = {f for f, c in (state.board or {}).items() if c > 0}
    for b in (state.bench or []):
        if b.faction and b.faction != '?':
            out.add(b.faction)
    return out


def _intention_family(session: StrategySession) -> str:
    """当前意向家族键(插件禁用矩阵/过半线判定的语境;空=不查)。"""
    ist = getattr(session, 'v3_intention', None)
    if ist is None:
        return ''
    locked = getattr(ist, 'locked_comp', '')
    if not locked:
        return ''
    from sr_od.application.currency_war.cw_comps import get_comp
    comp = get_comp(locked)
    return comp.family if comp is not None else ''


def _legacy_target_names(state: GameState,
                         session: StrategySession) -> set[str]:
    """旧本体论目标集(线库/桥池派生;**A/B 窗兼容垫片,步 5 锁迁移后删**)。

    仅当 session 呈旧载体形态(``v3_hoard`` 缺失且 ``locked_line``/
    ``bridge_id`` 已设——旧锁单测的直调形态)时被 ``_target_names`` 消费;
    生产新载体 ``update_target`` 每轮写 ``v3_hoard``,恒走意向源。
    """
    from sr_od.application.currency_war.cw_bridge_pool import (
        BRIDGE_POOL,
        BRIDGE_POOL_P2,
    )
    from sr_od.application.currency_war.cw_line_library_v1 import line_of
    names: set[str] = set()
    pool = BRIDGE_POOL if state.plane <= 1 else BRIDGE_POOL_P2
    if session.locked_line:
        line = line_of(session.locked_line)
        if line is not None:
            names.add(line.carry)
            names.update(line.opportunistic_cards)
        names.update(n for combo in pool
                     for n in set(combo.fixed) | set(combo.core))
    elif session.bridge_id:
        for combo in pool:
            if combo.bridge_id == session.bridge_id:
                names.update(combo.fixed)
                names.update(combo.core)
    else:
        names.update(n for combo in pool
                     for n in set(combo.fixed) | set(combo.core))
    return names


def _target_names(state: GameState,
                  session: StrategySession) -> set[str]:
    """当前方向的目标件名集(载体批换源:意向分层输入)。

    - 意向载体(``session.v3_hoard`` 由 ``update_target`` 每轮写):
      hoard char_targets(locked/weak/fallback 模式各自的目标集)+
      体系卡引擎件(铁三角+希儿——引擎件任何模式下都是方向件);
    - ``v3_hoard`` 缺失且旧载体字段已设:旧线库/桥池派生(A/B 窗
      兼容垫片,步 5 锁迁移后删——见 ``_legacy_target_names``);
    - 全缺(未走 update_target 的裸 session):引擎件全集(种子语义)。
    """
    hoard = getattr(session, 'v3_hoard', None)
    if hoard is not None:
        # 意向载体:hoard char_targets + 体系卡引擎件(任何模式下都是
        # 方向件,点3 见即买)
        return set(engine_char_names()) | set(
            getattr(hoard, 'char_targets', ()) or ())
    if session.locked_line or session.bridge_id:
        return _legacy_target_names(state, session)
    # 裸 session(未走 update_target):旧种子语义——当前位面全部桥的
    # fixed∪core 并集(方向永远锁得上的最小集;引擎件 ⊆ 桥名单)
    return _legacy_target_names(state, session)


def _core_names(session: StrategySession) -> set[str]:
    """意向核心名集('line_carry' 标签裁决;核心=一等公民)。"""
    cores = getattr(session, 'v3_core_names', None)
    if cores:
        return set(cores)
    return set()


def _plugin_ok(card: ShopCard, state: GameState,
               session: StrategySession) -> bool:
    """插件四层过滤(定义节 class5):机制冲突?/过半线=骨架/上场有位/
    都过=插件(bench 不囤——板上无空位不买,买了即上)。"""
    if card.name not in PLUGIN_LIBRARY:
        return False
    entry = PLUGIN_LIBRARY[card.name]
    family = _intention_family(session)
    if family and (family in entry.majority_lines
                   or plugin_disabled(card.name, family) is not None):
        return False   # ①机制冲突拒买 / ②过半线=骨架非插件
    # ③上场有位(bench 不囤插件:cap 内空位才买;替班核心例外不在买侧)
    return len(state.deployed or []) < state.max_units()


def _buy_tag(card: ShopCard, state: GameState,
             session: StrategySession, registry: DecisionV2Registry) -> str | None:
    """单卡标签裁决(纯查询;序=registry.buy_tag_priority 语义)。

    carry_gate 是状态修饰:bench 满时的目标类买入(执行需先腾位,
    [32] 腾席需求优先用卖解决)。
    """
    targets = _target_names(state, session)
    bench_full = len(state.bench or []) >= registry.bench_capacity
    is_target = card.name in targets
    v3_carrier = getattr(session, 'v3_hoard', None) is not None
    if not is_target and engine_seed_wants(card, state, session):
        return 'engine_seed'    # 点3:引擎件见即买(C2 名单)
    if not is_target and pair_wants(card, state, session):
        if has_same_name_copy(card, state) \
                and not in_round_sold(card.name, state, session):
            return 'copy'
        return 'pair'
    if not is_target and _plugin_ok(card, state, session):
        return 'plugin'         # class5:插件买来即上(有位才买)
    # [31] bond_fallback 门无方向约束(W47 清理:原 `has_direction or
    # no_direction` 恒真死条件——两变量互斥取或=永 True,删除后语义不变;
    # 锁测试见 test_cw_w47_unification 的双向触发用例)
    if (not is_target
            and state.round_num >= registry.bond_fallback_min_round
            and 1 <= (card.cost or 3) <= registry.bond_fallback_max_cost
            and card.faction in _owned_factions(state)):
        return 'bond_fallback'
    if not is_target:
        return None    # 纯散件不生成([31] 反散件原则)
    # 目标类标签裁决:核心(carry)> 其余目标件(新载体=
    # line_opportunistic 意向件;旧载体垫片=bridge_core 桥核心件)
    cores = _core_names(session)
    if card.name in cores:
        return 'line_carry'
    if bench_full and state.round_num <= registry.carry_gate_max_round:
        return 'carry_gate'
    return 'line_opportunistic' if v3_carrier else 'bridge_core'


def _sell_blocked(bc: BenchChar, state: GameState,
                  session: StrategySession) -> bool:
    """卖出豁免过滤(生成器层;v1 卖通道语义对齐,ADR-0296):
    r408 同轮已买(<3 份)/种子 2 轮窗/完整 3合1 份不卖。"""
    name = bc.char_id or ''
    if not name:
        return True    # 未识别件不卖(感知纪律)
    if (getattr(session, 'v2_round_key', None)
            == (state.plane, state.round_num)
            and name in (getattr(session, 'v2_round_bought', None) or ())
            and star_weighted_copies(name, state) < 3):
        return True
    if seed_age_blocked(bc, state, session):
        return True
    return star_weighted_copies(name, state) == 3


def _sell_tag(bc: BenchChar, state: GameState,
              session: StrategySession,
              registry: DecisionV2Registry) -> str | None:
    """bench 单件卖出理由(优先序=registry.sell_tag_priority)。

    - off_target:常态非目标死库存(protect=目标集外);
    - for_gold:应急态弱件折现(应急判定=hp≤registry.emergency_hp);
    - free_bench:bench 满时的腾位让位([32]:目标件也降保护集让位)。
    """
    if _sell_blocked(bc, state, session):
        return None
    if round_sell_blocked(bc, state, session):
        return None
    protect = _target_names(state, session)
    name = bc.char_id or ''
    is_target = name in protect
    emergency = state.hp <= registry.emergency_hp
    bench_full = len(state.bench or []) >= registry.bench_capacity
    for tag in registry.sell_tag_priority:
        if tag == 'off_target':
            if not is_target and not emergency:
                return tag
        elif tag == 'for_gold':
            if emergency and not is_target:
                return tag
        elif tag == 'free_bench':
            if bench_full:
                return tag    # 腾位让位:bench 满时目标件也降保护集
    return None


def generate_candidates(state: GameState, session: StrategySession,
                        registry: DecisionV2Registry) -> list[Candidate]:
    """层1:生成全部合法候选(纯函数;sim 可测)。

    覆盖面由检查项 decision_v2_candidate_coverage 锁(全部动作类)。
    """
    out: list[Candidate] = []
    # --- 买(店内每卡)---
    for card in (state.shop or []):
        if not card.name:
            continue    # 未识别卡不买(感知纪律)
        if star_weighted_copies(card.name, state) >= registry.copies_cap:
            continue    # 副本上限(第 4 份纯浪费)
        if copy_swap_useless(card, state, session) \
                and not (registry.copy_swap_target_exempt
                         and card.name in _target_names(state, session)):
            continue    # r410 同名跨副本无效换卡(ADR-0300 镜像;
            # 目标件豁免开关=ADR-0303/0304 裁决默认关,通道保留)
        tag = _buy_tag(card, state, session, registry)
        if tag is None:
            continue
        # 3合1:买入后同名 1★ 副本恰达 3 份 → 合成候选
        will_merge = star_weighted_copies(card.name, state) == 2 \
            and card.star == 1
        out.append(Candidate(
            action=BuyCard(card, reason=''),
            tag=tag, source='shop',
            merge=will_merge,
            needs_slot=(tag == 'carry_gate'),
            breakdown_hint={'cost': card.cost},
        ))
    # --- 卖(bench 每件)---
    for idx, bc in enumerate(state.bench or []):
        tag = _sell_tag(bc, state, session, registry)
        if tag is None:
            continue
        out.append(Candidate(
            action=SellBench(bench_idx=idx),
            tag=tag, source='bench',
            breakdown_hint={'name': bc.char_id},
        ))
    # --- LevelUp(单价=经验单击价;ADR-0129 语义)---
    if state.level < registry.level_max:
        out.append(Candidate(
            action=LevelUp(cost=xp_click_cost(state)),
            tag='levelup', source='xp',
        ))
    # --- RefreshShop ---
    out.append(Candidate(
        action=RefreshShop(cost=state.shop_refresh_cost or 2),
        tag='refresh', source='shop',
    ))
    # --- Deploy(top-K;排序键=围栏序,K=registry.deploy_top_k)---
    out.extend(_deploy_candidates(state, session, registry))
    # --- 合成(独立通道,ADR-0296:bench∪deployed 同名同星 ≥3)---
    out.extend(_synthesize_candidates(state))
    return out


def _synthesize_candidates(state: GameState) -> list[Candidate]:
    """3合1 合成候选:全场域同名同星 ≥3 份 → 每组一个候选。

    cw_state._merge_bench 语义镜像(生产同源):分组键=(char_id, star),
    合并域=bench∪deployed(3合1 是全场);组内 ≥3 → 合成 1 份升星。
    """
    groups: dict[tuple[str, int], int] = {}
    for it in list(state.bench or []) + list(state.deployed or []):
        name = getattr(it, 'char_id', '') or ''
        if not name:
            continue
        star = max(1, int(getattr(it, 'star', 1) or 1))
        groups[(name, star)] = groups.get((name, star), 0) + 1
    out: list[Candidate] = []
    for (name, star), cnt in sorted(groups.items()):
        if cnt < 3:
            continue
        out.append(Candidate(
            action=Synthesize(name=name, star=star, copies=cnt),
            tag='synthesize', source='merge_pool', merge=True,
            breakdown_hint={'name': name, 'star': star, 'copies': cnt},
        ))
    return out


def _deploy_candidates(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> list[Candidate]:
    """部署候选:围栏序 top-K(与生产 DeployBench/sim 部署块同一源)。"""
    from sr_od.application.currency_war import cw_deploy_logic as dl
    tc = getattr(session, 'target_comp', None)
    target_factions = frozenset(getattr(tc, 'factions', None) or ())
    target_cores = frozenset(getattr(tc, 'core_chars', None) or ())
    deployed_cids = {d.char_id for d in (state.deployed or [])
                     if getattr(d, 'char_id', '')}
    from sr_od.application.currency_war.cw_sim import _board_factions_of
    up_idx, _held = dl.select_deployments(
        list(state.bench or []),
        deployed_cids=deployed_cids,
        deployed_fac=_board_factions_of(state.deployed),
        board=dict(state.board or {}),
        cap=state.max_units(),
        target_factions=target_factions,
        target_cores=target_cores,
    )
    out: list[Candidate] = []
    for i in up_idx[:registry.deploy_top_k]:
        if i >= len(state.bench or []):
            continue
        bc = state.bench[i]
        out.append(Candidate(
            action=DeployMove(bench_idx=i,
                              to_row=bc.position_pref or 'back',
                              faction=bc.faction or '?'),
            tag='deploy', source='fence',
            breakdown_hint={'name': bc.char_id,
                            'sort_key': registry.deploy_sort_key},
        ))
    return out
