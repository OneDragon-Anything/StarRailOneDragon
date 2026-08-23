"""决策框架 v2 层1:候选生成器(ADR-0290;纯函数 state→list[Candidate])。

枚举每个决策点的全部合法候选动作,无通道概念、无优先级语义
(标签仅作层2过滤域标记,ADR-0290 对抗修订③):

- 买:店内每张可识别卡 × 标签(line_carry / line_opportunistic /
  bridge_core / bond_fallback[31] / carry_gate 腾位)+ 3合1 合成标记
  (同名第 3 张副本买入即合成,Candidate.merge=True);
- 卖:bench 每件 × 理由(off_target / for_gold / free_bench 腾位让位);
- LevelUp / RefreshShop;
- Deploy:board∪bench→槽位组合的 top-K(K 与排序键在 registry 显式;
  排序键=围栏序 cw_deploy_logic.select_deployments,与生产 DeployBench
  同一源,不另造排序)。

纯函数(只读 state/session,不 mutate),sim 可测;层2/3/4 分别见
filters.py / scoring.py / arbiter.py。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_bridge_pool import (
    BRIDGE_POOL,
    BRIDGE_POOL_P2,
)
from sr_od.application.currency_war.cw_economy import xp_click_cost
from sr_od.application.currency_war.cw_line_defs import ENGINE_FACTIONS
from sr_od.application.currency_war.cw_line_library_v1 import line_of
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
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)

#: 买候选标签集 / 卖候选标签集 / 动作类枚举(检查项 coverage 消费)
BUY_TAGS: frozenset[str] = frozenset({
    'line_carry', 'line_opportunistic', 'bridge_core',
    'bond_fallback', 'carry_gate',
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


def _owned_factions(state: GameState) -> set[str]:
    """board∪bench 的已有阵营集合(bond_fallback 凑档判据输入)。"""
    out = {f for f, c in (state.board or {}).items() if c > 0}
    for b in (state.bench or []):
        if b.faction and b.faction != '?':
            out.add(b.faction)
    return out


def _target_names(state: GameState,
                  session: StrategySession) -> set[str]:
    """当前方向的目标件名集(锁线=carry+opportunistic+位面桥 core;
    未锁桥期=桥 fixed∪core;**无方向=当前位面全部桥的 fixed∪core
    并集**(种子语义,r234 镜像——桥选择要求 owned 已有 fixed 是
    鸡生蛋,种子件先入手才能成桥;漏此分支 = 方向永远锁不上,
    smoke 实证 dir_round=99 团灭)。"""
    names: set[str] = set()
    pool = BRIDGE_POOL if state.plane <= 1 else BRIDGE_POOL_P2
    if session.locked_line:
        line = line_of(session.locked_line)
        if line is not None:
            names.add(line.carry)
            names.update(line.opportunistic_cards)
        names.update(n for combo in pool for n in combo.core)
    elif session.bridge_id:
        for combo in pool:
            if combo.bridge_id == session.bridge_id:
                names.update(combo.fixed)
                names.update(combo.core)
    else:
        names.update(n for combo in pool
                     for n in set(combo.fixed) | set(combo.core))
    return names


def _star_weighted_copies(name: str, state: GameState) -> int:
    """同名星级加权副本数(bench+deployed;2★=2 份,3★=3 份)。"""
    n = sum(getattr(b, 'star', 1) or 1
            for b in (state.bench or []) if b.char_id == name)
    n += sum(getattr(d, 'star', 1) or 1
             for d in (state.deployed or [])
             if getattr(d, 'char_id', '') == name)
    return n


def _buy_tag(card: ShopCard, state: GameState,
             session: StrategySession, registry: DecisionV2Registry) -> str | None:
    """单卡标签裁决(优先序=registry.buy_tag_priority;纯查询)。

    carry_gate 是状态修饰:bench 满时的目标类买入(执行需先腾位,
    [32] 腾席需求优先用卖解决)。
    """
    targets = _target_names(state, session)
    bench_full = len(state.bench or []) >= registry.bench_capacity
    is_target = card.name in targets
    # [31] 凑档降级:锁线+目标件全缺,或**完全无方向**(未锁且无桥
    # ——无 top4 目标件时「用手上已有的其他羁绊先凑数,纯散件不买」)
    # +r≥3+1-2 费带+凑 2 档
    no_direction = not session.locked_line and not session.bridge_id
    if (not is_target and (session.locked_line or no_direction)
            and state.round_num >= registry.bond_fallback_min_round
            and 1 <= (card.cost or 3) <= registry.bond_fallback_max_cost
            and card.faction in _owned_factions(state)):
        return 'bond_fallback'
    if not is_target:
        return None    # 纯散件不生成([31] 反散件原则)
    # 目标类标签按 registry.buy_tag_priority 顺序裁决:
    # carry > opportunistic > bridge_core(fixed∪core 统称桥核心件)
    line = line_of(session.locked_line) if session.locked_line else None
    if 'line_carry' in registry.buy_tag_priority \
            and line is not None and card.name == line.carry:
        return 'line_carry'
    if 'line_opportunistic' in registry.buy_tag_priority \
            and line is not None and card.name in line.opportunistic_cards:
        return 'line_opportunistic'
    if 'bridge_core' in registry.buy_tag_priority:
        if bench_full and state.round_num <= registry.carry_gate_max_round \
                and 'carry_gate' in registry.buy_tag_priority:
            return 'carry_gate'
        return 'bridge_core'
    return None


def _sell_tag(bc: BenchChar, state: GameState,
              session: StrategySession,
              registry: DecisionV2Registry) -> str | None:
    """bench 单件卖出理由(优先序=registry.sell_tag_priority)。

    - off_target:非目标件且非引擎件(protect 集外);
    - for_gold:目标件但同名副本超额(星级加权 >3 份的冗余份);
    - free_bench:bench 满时的腾位让位([32]:腾席优先用卖解决)。
    """
    protect = _target_names(state, session)
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    ch = CHARACTERS.get(bc.char_id or '')
    bonds = (set(ch.factions) | set(ch.flows)) if ch else {bc.faction}
    is_engine = bool(bonds & set(ENGINE_FACTIONS))
    copies = _star_weighted_copies(bc.char_id or '', state)
    for tag in registry.sell_tag_priority:
        if tag == 'off_target':
            if bc.char_id not in protect and not is_engine:
                return tag
        elif tag == 'for_gold':
            if copies > registry.copies_cap:
                return tag
        elif tag == 'free_bench':
            if (len(state.bench or []) >= registry.bench_capacity
                    and bc.char_id not in protect):
                return tag
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
        if _star_weighted_copies(card.name, state) >= registry.copies_cap:
            continue    # 副本上限(第 4 份纯浪费)
        tag = _buy_tag(card, state, session, registry)
        if tag is None:
            continue
        # 3合1:买入后同名 1★ 副本恰达 3 份 → 合成候选
        will_merge = _star_weighted_copies(card.name, state) == 2 \
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
