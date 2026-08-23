"""决策框架 v2 层1:候选生成器(ADR-0290;纯函数 state→list[Candidate])。

枚举每个决策点的全部合法候选动作,无通道概念、无优先级语义
(标签仅作层2过滤域标记,ADR-0290 对抗修订③):

- 买:店内每张可识别卡 × 标签(line_carry / line_opportunistic /
  bridge_core / engine_seed[ADR-0299 过渡体系首块砖] /
  pair[ADR-0300 凑对搭档件] / copy[ADR-0300 同名副本素材] /
  bond_fallback[31] / carry_gate 腾位)+ 3合1 合成标记
  (同名第 3 张副本买入即合成,Candidate.merge=True);
- 卖:bench 每件 × 理由(off_target 常态死库存 / for_gold 应急态弱件
  / free_bench 腾位让位)——v1 卖通道豁免(engine_seed 年龄豁免
  ADR-0289 §5 / 3合1 素材豁免 / r408 同轮已买)全部在生成器层过滤
  (ADR-0296;别在评分层重复判);
- LevelUp / RefreshShop;
- Deploy:board∪bench→槽位组合的 top-K(K 与排序键在 registry 显式;
  排序键=围栏序 cw_deploy_logic.select_deployments,与生产 DeployBench
  同一源,不另造排序);
- 合成(3合1 独立通道,ADR-0296):bench∪deployed 同名同星 ≥3 份
  (cw_state._merge_bench 全场域口径的镜像)→ 每组一个 synthesize
  候选;另:店内第 3 张同名 1★ 副本买入即合成,买候选带
  Candidate.merge=True(两路共同构成 synthesize 动作类)。

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
    'engine_seed', 'pair', 'copy', 'bond_fallback', 'carry_gate',
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

    本类是层1 枚举完备性的载体:待合并态(全场域已有完整 3 份)
    显影为候选,评分交给 scoring 现有函数(升星形态增益;当前
    simulate 对本类型 no-op → 板面查表恒 0 分差 →「非正分」不执行,
    形态域批后继按需接消费)。执行侧双保险:sim 执行链按
    isinstance 分派(未知类型安全跳过);DecisionV2 非默认策略。
    """

    name: str                      # 同名组角色名
    star: int                      # 组内星级(合并后 star+1)
    copies: int = 3                # 组内份数(≥3)


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
        # ADR-0299:锁线期目标集并入当前位面全部桥的 fixed∪core
        # (与未锁分支同口径)——v1 _bridge_seed 不分锁线态,任何桥的
        # fixed 件(如飞霄)都是方向件;旧版只并 core → 锁线后 fixed
        # 件候选不生成(买入面缺口,seed 900003 r2 实证)+ 无保护
        # 被当 off_target 卖(v1 line1554「买进来的每一张都是方向件」)
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


def _star_weighted_copies(name: str, state: GameState) -> int:
    """同名星级加权副本数(bench+deployed;2★=2 份,3★=3 份)。"""
    n = sum(getattr(b, 'star', 1) or 1
            for b in (state.bench or []) if b.char_id == name)
    n += sum(getattr(d, 'star', 1) or 1
             for d in (state.deployed or [])
             if getattr(d, 'char_id', '') == name)
    return n


def _engine_seed_wants(card: ShopCard, state: GameState,
                       session: StrategySession) -> bool:
    """过渡体系种子件放行门(ADR-0299):v1 LineStrategy.
    _engine_seed_wants 的直通单一源(与 _seed_age_blocked 同式,
    不复制判据)。

    P1 过渡期,卡属过渡体系阵营(仙舟/列车同行/持续伤害)且未持有
    同名 → 候选(引擎乐高第一块砖)。v1 实弹判读(ADR-0260):
    凑档/锁线判据漏 21% 金够 cost1-3 引擎核心件——这正是 v2 买入
    面缺口的主导层(合流总验 buys 9.3 vs v1 15,解剖表 layer1
    21.6%,集中在 r1-r2)。金够/不破息档由层4 gold_floor/
    interest_rule 辖(v1 同:本门不加价)。
    """
    from sr_od.application.currency_war.strategies.line_strategy import (
        LineStrategy,
    )
    return LineStrategy._engine_seed_wants(card, state, session)


def _pair_wants(card: ShopCard, state: GameState,
                session: StrategySession) -> bool:
    """凑对搭档件放行门(ADR-0300):v1 LineStrategy._pair_wants 的
    直通单一源(与 _engine_seed_wants 同式,不复制判据)。

    v1 语义(判据全部在单一源内):冷启动首购只放行 桥名单 ∪
    引擎阵营 ∪ 同名副本(r368/r371b/r383b);方向期阵营门
    (r350:锁线=线形态羁绊,桥=引擎阵营);A5 spread 门
    (已有阵营 ≥3 不再开新阵营);常态=同阵营凑对;r408 同轮
    已卖不回买。解剖表残余 layer1 的 pair 桶(v1 reason=pair)
    由本通道清偿。金够/不破息档由层4 gold_floor 辖(v1 同)。
    """
    from sr_od.application.currency_war.strategies.line_strategy import (
        LineStrategy,
    )
    return LineStrategy._pair_wants(card, state, session)


def _copy_swap_useless(card: ShopCard, state: GameState,
                       session: StrategySession) -> bool:
    """同名跨副本无效换卡守卫(ADR-0300):v1 _buy_guards 的
    r410 臂直通单一源(保留判据镜像——在场副本会被 deploy 侧
    off-target 卖出时,买新副本=纯耗换卡,不生成候选)。

    True=无效换卡(拒);False=合法(在场副本被保留:core 显式
    保留或 bonds ∩ target_factions 凑对保留 → 买副本合法)。
    """
    from sr_od.application.currency_war.strategies.line_strategy import (
        LineStrategy,
    )
    return LineStrategy._copy_swap_useless(card, state, session)


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
    if not is_target and _engine_seed_wants(card, state, session):
        return 'engine_seed'    # ADR-0299:过渡体系首块砖(v1 ADR-0260 门镜像)
    # ADR-0300:pair/copy 通道(v1 _want_label 的 pair 臂镜像,
    # 序=engine_seed 之后、bond_fallback 之前,与 v1 OR 链一致)
    if not is_target and _pair_wants(card, state, session):
        from sr_od.application.currency_war.strategies.line_strategy import (
            LineStrategy,
        )
        # r383b 副本标签拆分(与 v1 _want_label 同式):同名副本素材
        # 打专属 'copy'(检查器按 reason 区分门失效与合法放行)
        if LineStrategy._has_same_name_copy(card, state) \
                and not LineStrategy._in_round_sold(card.name, state,
                                                    session):
            return 'copy'
        return 'pair'
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


def _seed_age_blocked(bc: BenchChar, state: GameState,
                      session: StrategySession) -> bool:
    """engine_seed 年龄豁免(ADR-0289 §5;单一源=line_strategy.

    _seed_age_blocked 的直通——买入 ≤2 轮且同轮份数 <2 的种子不进
    可卖集;生成器层过滤(ADR-0296),别在评分层重复判。
    """
    from sr_od.application.currency_war.strategies.line_strategy import (
        LineStrategy,
    )
    return LineStrategy._seed_age_blocked(bc, state, session)


def _sell_blocked(bc: BenchChar, state: GameState,
                  session: StrategySession) -> bool:
    """卖出豁免过滤(v1 卖通道语义对齐,ADR-0296;纯查询)。

    - r408(ADR-0267)同轮已买不卖(买→卖→买永动机拆解);
      3合1 让位豁免:同名星级加权 ≥3 份 = 合成后冗余件,放行;
    - engine_seed 年龄豁免(ADR-0289 §5):买入 ≤2 轮种子不卖;
    - 3合1 素材豁免:同名星级加权恰 3 份(完整合成份)不卖
      (卖一份 = 拆合成材料;v1 carry 腾位门 _cp==3 不动同语义)。
    """
    name = bc.char_id or ''
    if not name:
        return True    # 未识别件不卖(感知纪律)
    if (getattr(session, 'v2_round_key', None)
            == (state.plane, state.round_num)
            and name in (getattr(session, 'v2_round_bought', None) or ())
            and _star_weighted_copies(name, state) < 3):
        return True    # r408 同轮已买(<3 份非让位语境)
    if _seed_age_blocked(bc, state, session):
        return True    # 种子 2 轮窗(ADR-0289 §5)
    # 完整 3合1 份(素材豁免;>3 冗余可卖)
    return _star_weighted_copies(name, state) == 3


def _sell_tag(bc: BenchChar, state: GameState,
              session: StrategySession,
              registry: DecisionV2Registry) -> str | None:
    """bench 单件卖出理由(优先序=registry.sell_tag_priority;ADR-0296)。

    - off_target:常态非目标死库存(protect=_target_names 外);
    - for_gold:应急态弱件折现(应急判定 = hp≤registry.emergency_hp,
      与 filters.is_emergency 同式——模块内联防 import 环);
    - free_bench:bench 满时的腾位让位([32]:目标件也降保护集让位,
      v1 carry 腾位门语义;冗余份/杂件在此前标签先命中)。

    引擎件不另设保护(v1 无 engine 阵营级卖禁;件值经评分层板面形态
    显影——卖出后形态查表自然降分,非正分即拒,ADR-0290 层2 语义)。
    """
    if _sell_blocked(bc, state, session):
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
        if _star_weighted_copies(card.name, state) >= registry.copies_cap:
            continue    # 副本上限(第 4 份纯浪费)
        if _copy_swap_useless(card, state, session):
            continue    # r410 同名跨副本无效换卡(ADR-0300 镜像;
            # 在场副本会被 off-target 卖出 → 买新副本=换卡纯耗)
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
    # --- 合成(独立通道,ADR-0296:bench∪deployed 同名同星 ≥3)---
    out.extend(_synthesize_candidates(state))
    return out


def _synthesize_candidates(state: GameState) -> list[Candidate]:
    """3合1 合成候选:全场域同名同星 ≥3 份 → 每组一个候选。

    cw_state._merge_bench 语义镜像(生产同源):分组键=(char_id, star),
    合并域=bench∪deployed(3合1 是全场);组内 ≥3 → 合成 1 份升星。
    sim 里买入即自动合并 → 该通道常态零触发,服务**枚举完备性**
    (ADR-0290 层1 义务:live 重建态的待合并显影)与检查项覆盖。
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
