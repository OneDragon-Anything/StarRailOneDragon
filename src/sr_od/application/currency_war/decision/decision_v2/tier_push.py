"""P1 档位推进目标函数(W803 实施批;策略开关生命周期第 1 态)。

设计单一源 = ``.debug/temp/currency_war/w803_tier_push_design/REPORT.md``
v2(缺口差分项 §3①/r7 死线 §3②/与既有机制关系 §3③/散装板守门 §3④/
r6 建档轮预算前移 §3⑤)+ 同目录 ``PREREG_tier_push_AB.md`` v2(判前锁;
锁清单 §5)。命题 = ``docs/game/currency_war/research/proofs/p32-p1-tier-
push-ev.md``(P32:档≥3 → 出口 59-72 / 档≤2 → 9-48 的阶跃实证 + EV 下界
+19 血当量)。

伞开关 ``p1_tier_push_enabled`` + 三子旗标(gate/deadline/r6_budget,仅
A/B 归因必需),全部默认关 = 第 1 态零漂移锚(生产默认行为逐位不变)。
占位参数(W(r) 形状/V_tier 线分权/报警线)不做生产决策之外的解读,开臂
前 sim 标定批消偿(设计 §6/§8 挂账);开臂判据挂账 = PREREG v2 主判据
M1-M3 + 机制判 G0-G5,不过则删码留 ADR,禁悬置默认关。

**与 W802 realization(位面 2 侧兑现链)的正交声明(设计 §3③)**:本模
块辖位面 1 侧、锁线前后全程的评分目标函数补项;off-lock 罚分本体 =
W802 单一实现(``scoring.score_candidate`` 末段 κ 折扣通道),本模块只
消费不落改——缺口差分项加在 off-lock 降级之前,线外候选经既有 κ 通道
获得「降级非禁绝」语义,零新增罚分机制。Δp_tier 标定单一源共享:刷新
超几何项复用 ``registry.realization_delta_p_tier``,禁第二源。

边界声明:本模块只产「评分加项/门判定/授权判定」纯函数输入,不发射
动作、不碰金账——金地板/息账/bench 容量照常由 arbiter 约束链统一收口
(与 W802 同纪律)。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
from sr_od.application.currency_war.decision.cw_strategy import StrategySession
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    SEELE_AMP_FACTIONS,
    TRANSITION_TRAITS,
)
from sr_od.application.currency_war.kernel.cw_discipline_rules import (
    star_weighted_copies,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    IntentionState,
    locked_faction_scope,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BuyCard,
    DeployMove,
    GameState,
    LevelUp,
    bench_occupied,
)

#: 过渡体系档位阈值(单一源 = cw_deploy_logic.TRANSITION_TRAITS,经
#: FACTIONS 注册表 tiers[0] 派生:仙舟 3 / 列车同行 2 / 持续伤害 2)。
_TIER_OF: dict[str, int] = dict(TRANSITION_TRAITS)

#: 希儿系放大器计数档(engines_count 同语义:希儿在场 ∧ 任一放大器 ≥2)。
_SEELE_AMP_TIER: int = 2

#: 线键(设计 §1.2 成型档组三线:仙舟线 / 列车∧DOT 线 / 列车∧希儿系线)。
_LINE_XIANZHOU = '仙舟线'
_LINE_TRAIN_DOT = '列车DOT线'
_LINE_TRAIN_SEELE = '列车希儿线'

#: 列车线共享前件羁绊键。
_TRAIN_KEY = '列车同行'
_DOT_KEY = '持续伤害'
_XIANZHOU_KEY = '仙舟'

#: 探索期(无锁定帧)意向辖域 = 四体系全部注册羁绊键(设计 §1.2:
#: transition_combos 封闭裁定;[31]① 空窗期四体系全集是方向)。
_EXPLORE_KEYS: frozenset[str] = frozenset(_TIER_OF) | SEELE_AMP_FACTIONS


def _on(registry: DecisionV2Registry) -> bool:
    """伞开关统一进门判(默认关 = 逐位零漂移锚)。"""
    return registry.p1_tier_push_enabled


def _ist(session: StrategySession | None) -> IntentionState | None:
    ist = getattr(session, 'v3_intention', None)
    return ist if isinstance(ist, IntentionState) else None


def intended_bond_keys(state: GameState,
                       session: StrategySession | None) -> frozenset[str]:
    """激活档口径的羁绊辖域(设计 §1.2;防面板滞后,注册表自算)。

    - 锁定帧 = ``cw_intention.locked_faction_scope``(p1_pair ∪
      transition_pair ∪ locked_comp 档键;希儿系展开为量子/贝放大器键,
      与该单一源同口径);
    - 探索期(未锁) = 四体系全部键(TRANSITION_TRAITS ∪ 希儿放大器)。
    """
    keys = locked_faction_scope(_ist(session))
    if keys:
        return keys
    return _EXPLORE_KEYS


def _deployed_counts(state: GameState,
                     keys: frozenset[str]) -> dict[str, int]:
    """deployed 域注册表自算的羁绊计数(设计 §1.2:不用游戏面板快照
    ——面板滞后一拍,W789 问题 0 实证;bench 件不计入当帧档,经部署
    才兑现——这是缺口差分项给部署侧加权的理由)。"""
    counts = dict.fromkeys(keys, 0)
    for d in (state.deployed or []):
        ch = CHARACTERS.get(getattr(d, 'char_id', '') or '')
        if ch is None:
            continue
        for b in (set(ch.factions or ()) | set(ch.flows or ())) & keys:
            counts[b] = counts.get(b, 0) + 1
    return counts


def _seele_formed(names: set[str], counts: dict[str, int]) -> bool:
    """希儿系成型(cw_deploy_logic.engines_count 同语义:希儿在场 ∧
    任一放大器计数 ≥2;单一源语义镜像,计数域由调用方声明)。"""
    if '希儿' not in names:
        return False
    return any(counts.get(a, 0) >= _SEELE_AMP_TIER
               for a in SEELE_AMP_FACTIONS)


def line_gaps_from_counts(names: set[str], counts: dict[str, int],
                          keys: frozenset[str]) -> dict[str, float]:
    """按羁绊计数算三线缺口 ``G``(设计 §3①:dist(deployed, 最近成型
    档组) = 距成型档组的最小缺件数;只辖意向键内的线)。

    - 仙舟线:仙舟 ≥3 → 缺 max(0, 3−n_仙舟);
    - 列车DOT线:列车≥2 ∧ DOT≥2 → 两段缺件数之和;
    - 列车希儿线:列车≥2 ∧ 希儿系成型 → 列车缺件 + 希儿系缺件
      (希儿系缺口二值占位:未成型记 1——伤害在希儿技能层,羁绊只是
      放大器,阶跃位置判前未证(设计 §1.2 判定力声明),首版粗粒度,
      sim 标定批细化)。
    """
    out: dict[str, float] = {}
    if _XIANZHOU_KEY in keys:
        t = _TIER_OF.get(_XIANZHOU_KEY, 3)
        out[_LINE_XIANZHOU] = float(max(0, t - counts.get(_XIANZHOU_KEY, 0)))
    if _TRAIN_KEY in keys and _DOT_KEY in keys:
        tt = _TIER_OF.get(_TRAIN_KEY, 2)
        td = _TIER_OF.get(_DOT_KEY, 2)
        out[_LINE_TRAIN_DOT] = float(
            max(0, tt - counts.get(_TRAIN_KEY, 0))
            + max(0, td - counts.get(_DOT_KEY, 0)))
    if _TRAIN_KEY in keys and bool(keys & SEELE_AMP_FACTIONS):
        tt = _TIER_OF.get(_TRAIN_KEY, 2)
        gap = float(max(0, tt - counts.get(_TRAIN_KEY, 0)))
        if not _seele_formed(names, counts):
            gap += 1.0
        out[_LINE_TRAIN_SEELE] = gap
    return out


def line_gaps(state: GameState,
              session: StrategySession | None) -> dict[str, float]:
    """当前帧三线缺口(deployed 域;空 dict = 无辖线/非 P1)。"""
    keys = intended_bond_keys(state, session)
    if not keys:
        return {}
    counts = _deployed_counts(state, keys)
    names = {getattr(d, 'char_id', '') or ''
             for d in (state.deployed or [])}
    return line_gaps_from_counts(names, counts, keys)


def _v_of(line: str, registry: DecisionV2Registry) -> float:
    """V_tier 按线分权首版(设计 §1.2:仙舟锚定 P32.2 +19 血当量;
    列车/DOT 占位降权 0.5;希儿系最低 0.25——首版权值不做生产决策之外
    的解读,全部 sim 标定批重标,标定挂账 = 设计 §8-3/§8-6)。"""
    if line == _LINE_XIANZHOU:
        return registry.tier_push_v_anchor
    if line == _LINE_TRAIN_DOT:
        return (registry.tier_push_v_anchor
                * registry.tier_push_v_train_dot_scale)
    return registry.tier_push_v_anchor * registry.tier_push_v_seele_scale


def nearest_line(state: GameState, session: StrategySession | None,
                 registry: DecisionV2Registry | None = None,
                 ) -> tuple[str, float] | None:
    """最近成型档组的 (线, 缺口);并列取 V 高者,再按键名稳定排序。"""
    gaps = line_gaps(state, session)
    if not gaps:
        return None
    reg = registry if registry is not None else _registry_of(session)
    return min(gaps.items(),
               key=lambda kv: (kv[1],
                               -_v_of(kv[0], reg) if reg else 0.0,
                               kv[0]))


def _registry_of(session: StrategySession | None) -> DecisionV2Registry | None:
    reg = getattr(session, 'registry', None) if session else None
    return reg if isinstance(reg, DecisionV2Registry) else None


def deadline_weight(state: GameState, registry: DecisionV2Registry) -> float:
    """r7 死线权重 W(r)(设计 §3②;单调递增,r7 帧后坍缩 boss 残差)。

    - r1-r5 平缓 = ``tier_push_w_early``(占位);r6-r7 陡升 =
      ``tier_push_w_r6``(掉血帧 71% 集中 r7+r9,W801 §3,r6/r7 是
      真实备战窗——r7 备战帧购买直接作用于 r7 遭遇战,属陡升段);
      r8+ 残差 = ``tier_push_w_late``(设计 §3②「r7 帧后新增档位只经
      r8-r9 两个购买窗、只对 r9 boss 兑现」——坍缩自 r8 起,不是硬
      截止,是评分的时效折价);
    - 子旗标关 = 恒 1.0(消融归因:纯缺口差分,无时间整形);
    - 形状参数全部占位,sim 标定批标定(设计 §8-3)。
    """
    if not registry.p1_tier_push_deadline_enabled:
        return 1.0
    if state.plane != 1:
        return 1.0
    r = int(state.round_num or 0)
    if r >= 8:   # r7 遭遇的备战帧享陡升权重(设计 §3②「r7 帧后」坍缩)
        return registry.tier_push_w_late
    if r >= 6:
        return registry.tier_push_w_r6
    return registry.tier_push_w_early


def candidate_gap_term(cand, state: GameState, after_state: GameState | None,
                       session: StrategySession,
                       registry: DecisionV2Registry) -> float:
    """缺口差分项(设计 §3①;评分加项,买/升级/部署共用)。

        val += ΔG · W(r) · V_tier(线)

    - ΔG = G(before) − G(after),**逐帧存量差分**(设计 v2 定稿:每帧
      重算存量缺口,无跨帧累计账本——同帧重复计算幂等,锁 #2);线级
      口径 = 各意向线缺口差分取「差分·V_tier」最大者(候选推进哪条线,
      按该线的 V_tier 计值——比「最近线单差分」更忠实于按线分权;线序
      稳定排序保确定性);
    - 只辖 BuyCard/LevelUp/DeployMove(只加不卸;卖侧不辖——2★ 强力单
      卡不会被卖,设计 §3④);G 用 deployed 域(囤 bench 不计入当帧档
      ——买入候选的板面兑现经 apply_for_score 的部署管线显影,bench 满
      时 ΔG=0,与部署侧加权互补);候选使缺口变大的线 ΔG≤0 不罚(卸档
      语义归卖侧守卫族,本项只做正向标尺);
    - 消费点在 ``score_candidate`` 的 off-lock 降级**之前**:线外候选
      的本项随既有 W802 κ 折扣通道被比例折扣(降级非禁绝语义,零新增
      罚分机制——正交声明见模块头)。
    """
    if not _on(registry) or state.plane != 1 or after_state is None:
        return 0.0
    if not isinstance(cand.action, (BuyCard, LevelUp, DeployMove)):
        return 0.0
    keys = intended_bond_keys(state, session)
    if not keys:
        return 0.0
    names_before = {getattr(d, 'char_id', '') or ''
                    for d in (state.deployed or [])}
    gaps_before = line_gaps_from_counts(
        names_before, _deployed_counts(state, keys), keys)
    if not gaps_before:
        return 0.0
    names_after = {getattr(d, 'char_id', '') or ''
                   for d in (after_state.deployed or [])}
    gaps_after = line_gaps_from_counts(
        names_after, _deployed_counts(after_state, keys), keys)
    best = 0.0
    for line in sorted(gaps_before):
        dg = gaps_before[line] - gaps_after.get(line, gaps_before[line])
        if dg <= 0:
            continue
        best = max(best, dg * _v_of(line, registry))
    if best <= 0:
        return 0.0
    return best * deadline_weight(state, registry)


def tier_missing_members(state: GameState, session: StrategySession,
                        registry: DecisionV2Registry,
                        cost_band: frozenset[int] | None = None,
                        ) -> dict[str, float]:
    """最近线缺档成员清单(刷新超几何项的缺件判据)。

    成员定义:羁绊 ∈ 最近线辖键 ∧ 未上场 ∧ 加权副本未达 cap ∧ 其所在
    羁绊未满档(已满档贡献成员的第 4 份纯浪费,W802 ``missing_members``
    同语义);s = 当前档填充率(cur/下一档)。``cost_band`` = 有效费用域
    (None=不过滤;缺省沿 W802 搜牌侧 3-4 费单一语义,低费死支不落)。
    """
    near = nearest_line(state, session, registry)
    if near is None:
        return {}
    _line, gap = near
    if gap <= 0:
        return {}
    keys = intended_bond_keys(state, session)
    if _line == _LINE_XIANZHOU:
        line_keys = frozenset({_XIANZHOU_KEY})
    elif _line == _LINE_TRAIN_DOT:
        line_keys = frozenset({_TRAIN_KEY, _DOT_KEY})
    else:
        line_keys = frozenset({_TRAIN_KEY}) | SEELE_AMP_FACTIONS
    line_keys &= keys
    counts = _deployed_counts(state, keys)
    deployed_names = {getattr(d, 'char_id', '') or ''
                      for d in (state.deployed or [])}
    out: dict[str, float] = {}
    for name, ch in CHARACTERS.items():
        if name in deployed_names:
            continue
        if cost_band is not None and (ch.cost or 0) not in cost_band:
            continue
        if star_weighted_copies(name, state) >= registry.copies_cap:
            continue
        bonds = (set(ch.factions or ()) | set(ch.flows or ())) & line_keys
        for b in sorted(bonds):
            if b not in _TIER_OF:
                continue    # 希儿放大器键无独立档(经 _seele_formed 二值)
            t = _TIER_OF[b]
            cur = counts.get(b, 0)
            if cur >= t:
                continue    # 该羁绊已满档,成员非缺档
            out[name] = cur / float(t)
            break
    return out


def refresh_term(state: GameState, session: StrategySession,
                 registry: DecisionV2Registry) -> float:
    """刷新超几何项(设计 §3①:缺档成员的 ``Δp_tier·P(本刷出缺件)``,
    沿 W795 侧一机制不另造)。

        val += Δp_tier · P_miss · W(r)

    - Δp_tier 单一源 = ``registry.realization_delta_p_tier``(W803/W802/
      P29 三处共享标定,禁第二源——设计 §3③ 重叠面清单①);
    - **金水位辖域门(P5「花完仍≥息线」边界,沿 W795 侧一同款,不另造)**:
      花完 < 息线的帧预算 ≈ 0 → 加项为 0;
    - 有效费用域 = W802 搜牌侧同款 3-4 费(``realization_member_cost_band``
      单一源);
    - 伞关恒 0(off 臂零漂移)。
    """
    if not _on(registry) or state.plane != 1:
        return 0.0
    refresh_cost = int(state.shop_refresh_cost or 2)
    if (state.gold or 0) - refresh_cost < registry.interest_floor():
        return 0.0   # 金水位辖域门:破息帧缺档感知不驱动刷新
    missing = tier_missing_members(
        state, session, registry,
        cost_band=registry.realization_member_cost_band)
    if not missing:
        return 0.0
    p_miss = 1.0
    for name in missing:
        ch = CHARACTERS.get(name)
        if ch is None or not ch.cost:
            continue
        p_miss *= (1.0 - refresh_prob(state.level, ch.cost))
    return (registry.realization_delta_p_tier * (1.0 - p_miss)
            * deadline_weight(state, registry))


def _max_bond_tier(names: set[str], counts: dict[str, int],
                   keys: frozenset[str]) -> int:
    """deployed 域最大意向羁绊档(散装门判据;希儿系成型记 2 档——
    其引擎语义=单卡+放大器组合,不进三羁绊计数,与 engines_count 同)。"""
    m = max((counts.get(k, 0) for k in keys if k in _TIER_OF), default=0)
    if _seele_formed(names, counts):
        m = max(m, 2)
    return m


def gate_active(state: GameState, session: StrategySession,
                registry: DecisionV2Registry) -> bool:
    """散装板硬门辖域(设计 §3④):伞 ∧ 门子旗标 ∧ P1 ∧ **r4 起**
    (r1-r3 空窗期豁免,[31]①「手上有什么先上什么」——开局自由买战力件
    是唯一正确策略,门不生效)∧ ``max_bond_tier(deployed) < 2``(无任何
    ≥2 意向羁绊;deployed 域注册表自算,与缺口差分同一计数函数)。"""
    if not (_on(registry) and registry.p1_tier_push_gate_enabled):
        return False
    if state.plane != 1:
        return False
    if int(state.round_num or 0) < registry.tier_push_gate_min_round:
        return False
    keys = intended_bond_keys(state, session)
    if not keys:
        return False
    counts = _deployed_counts(state, keys)
    names = {getattr(d, 'char_id', '') or ''
             for d in (state.deployed or [])}
    return _max_bond_tier(names, counts, keys) < 2


def _counts_with(counts: dict[str, int], ch) -> dict[str, int]:
    """候选卡计入后的计数副本(豁免判据的虚拟增量,不改输入)。"""
    out = dict(counts)
    bonds = (set(ch.factions or ()) | set(ch.flows or ())) & set(out)
    for b in bonds:
        out[b] = out.get(b, 0) + 1
    return out


def _gap_advance_exempt(state: GameState, session: StrategySession,
                        name: str) -> bool:
    """豁免判据(设计 §3④ 单一句化):候选使 deployed∪bench 任一意向
    体系向其成型档组前进的最小增量 > 0——与缺口差分消费**同一 dist 函数**
    (line_gaps_from_counts,单一源);域 = deployed∪bench(买入落 bench
    也是「向档组前进」——首张豁免防自锁:档 0 板买某体系第一张也使缺口
    减小);门拒的是「对任何意向线缺口都零增量」的纯散件。"""
    keys = intended_bond_keys(state, session)
    if not keys:
        return False
    names = {getattr(d, 'char_id', '') or ''
             for d in (state.deployed or [])}
    names |= {b.char_id for b in (state.bench or []) if b is not None}
    counts = _deployed_counts(state, keys)
    for b in (state.bench or []):
        if b is None:
            continue
        ch = CHARACTERS.get(b.char_id or '')
        if ch is not None:
            counts = _counts_with(counts, ch)
    before = line_gaps_from_counts(names, counts, keys)
    ch = CHARACTERS.get(name)
    if ch is None:
        return False
    after = line_gaps_from_counts(names | {name}, _counts_with(counts, ch),
                                  keys)
    if not before:
        return bool(after)
    return min(after.values()) < min(before.values())


def _press_exempt_granted(state: GameState, session: StrategySession,
                          registry: DecisionV2Registry) -> bool:
    """压库豁免(设计 §3④ 收口):费用档 ≤2 硬上界 + 每帧 ≤2 张上限。

    **豁免不穿透 bench 挤占门**:needs_slot(bench 满需先腾位,[32])的
    候选不获豁免——「买什么」的豁免不改变「还能不能买」的挤占判定
    (挤占门在散装门之前判定,arbiter bench_capacity 约束照常辖);
    轮内计数 lazy 重置(轮键,filter 每决策段调用,含刷后 re-decide
    段——上限语义=每备战帧 ≤2,跨段累计更严,取严侧)。"""
    key = (state.plane, state.round_num)
    if getattr(session, 'v2_round_tp_press_key', None) != key:
        session.v2_round_tp_press_key = key
        session.v2_round_tp_press = 0
    if getattr(session, 'v2_round_tp_press', 0) \
            >= registry.tier_push_press_round_cap:
        return False
    session.v2_round_tp_press = \
        getattr(session, 'v2_round_tp_press', 0) + 1
    return True


def gate_verdict(cand, state: GameState, session: StrategySession,
                 registry: DecisionV2Registry) -> tuple[bool, str]:
    """散装门单候选裁决:(True, '')=放行;(False, 原因)=拒。

    判定序(设计 §3④):缺口前进豁免 → 压库豁免(费用档 ≤2 ∧ 每帧
    ≤2 ∧ 不穿透 bench 挤占门);两豁免皆不中 → 拒(『tier_push_gate_
    scatter』/『tier_push_gate_press_cap』)。只辖 BuyCard(守门只拒
    买入,不拒卖出/部署——设计 §3④)。"""
    if not isinstance(cand.action, BuyCard):
        return True, ''
    name = getattr(cand.action.card, 'name', '') or ''
    if name and _gap_advance_exempt(state, session, name):
        return True, ''
    ch = CHARACTERS.get(name)
    if ch is not None and (ch.cost or 3) <= registry.tier_push_press_cost_max \
            and not cand.needs_slot \
            and _press_exempt_granted(state, session, registry):
        return True, ''
    if ch is not None and (ch.cost or 3) <= registry.tier_push_press_cost_max:
        return False, 'tier_push_gate_press_cap'
    return False, 'tier_push_gate_scatter'


def r6_budget_authorized(cand, working: GameState, state: GameState,
                         session: StrategySession,
                         registry: DecisionV2Registry,
                         val: float, bd: dict,
                         auth: dict | None) -> bool:
    """r6 建档轮预算承诺授权(设计 §3⑤;W801 §3③ r6 备战帧量级失配)。

    - 辖域:伞 ∧ r6 子旗标 ∧ P1 r6 备战帧 ∧ 常态经济态(非应急/boss 窗/
      war——纪律态地板优先,本臂不越权);
    - **血线辖域门(最小实现,设计 §3⑤ v2)**:消费存活 ``state.hp`` +
      报警线(registry.blood_margin_low_hp = 40,[18] 纯语义阈值占位,
      sim 标定挂账;hp 不可信帧沿用 posture_release.hp_decision_trusted
      单一守卫,兜底帧不评估——防陈旧高 hp 伪授权);hp < 报警线 →
      r6 预算授权否决(授权否决,非「让位止损辖域」——W774⑤ 已删码,
      ADR-0487;概念重建批若落码则切换状态源,接缝挂账 = 设计 §8-5);
    - EV 门式(引 P26/P32.2 形态):EV = V − C > 0 即放行——V = 层3 分
      剥离息分量(含缺口差分项,与买侧 V 同单一源),买侧与组合跳变金
      账取大;C = interest_cost(回档折中口径,与 interest_rule 买侧
      同式);Δstreak 分量由板面差分 win/power 维承载(评分单一源),
      不另造第二账;面值金流已在 V 内,不重复扣;
    - 只辖 BuyCard/LevelUp(建档支出;刷新走 V_D/搜牌既有通道);
    - 授权依据 trace ``auth['tier_push_r6']`` 进执行 log(判读)。
    """
    if not (_on(registry) and registry.p1_tier_push_r6_budget_enabled):
        return False
    if state.plane != 1 or int(state.round_num or 0) != 6:
        return False
    if not isinstance(cand.action, (BuyCard, LevelUp)):
        return False
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        boss_window_active,
    )
    from sr_od.application.currency_war.decision.decision_v2.filters import (
        current_mode,
        is_emergency,
    )
    from sr_od.application.currency_war.decision.decision_v2.posture_release import (
        hp_decision_trusted,
    )
    if is_emergency(state, registry) \
            or boss_window_active(state, session, registry) \
            or current_mode(session) != 'economy':
        return False
    if not hp_decision_trusted(state):
        return False   # hp 不可信帧不评估(防陈旧高 hp 伪授权)
    if state.hp < registry.blood_margin_low_hp:
        return False   # 血线恶化段:授权否决([18] 报警线辖域)
    # 档位推进关联:买件使意向线缺口前进(deployed∪bench 域,与散装门
    # 豁免同一判据);升级须「有引擎件等上场」(bench 有件 ∧ 升完可多上,
    # [33] 人口位语义——纯人口战力增量不在本项辖域,设计 §3① 捆绑声明)。
    if isinstance(cand.action, BuyCard):
        name = getattr(cand.action.card, 'name', '') or ''
        if not name or not _gap_advance_exempt(state, session, name):
            return False
    else:
        from sr_od.application.currency_war.kernel.cw_state import (
            deployed_occupied,
        )
        if not (bench_occupied(state.bench or []) >= 1
                and deployed_occupied(state.deployed or [])
                < state.max_units()):
            return False
    from sr_od.application.currency_war.decision.decision_v2.arbiter import (
        _cost_of,
    )
    from sr_od.application.currency_war.decision.decision_v2.ev import (
        interest_cost,
    )
    cost = _cost_of(cand, working)
    if cost <= 0:
        return False
    v = val - (bd or {}).get('int_emb', 0.0)
    if isinstance(cand.action, BuyCard):
        fg = (bd or {}).get('form_gold') or 0.0
        if fg > v:
            v = fg
    c = interest_cost(working.gold or 0, cost, state,
                      recovery_rounds=registry.interest_recovery_rounds)
    ev = v - c
    if ev <= 0:
        return False
    if auth is not None:
        auth['tier_push_r6'] = round(ev, 1)
    return True
