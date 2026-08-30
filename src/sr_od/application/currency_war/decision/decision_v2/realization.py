"""锁线后兑现链 v2 机制模块(W802 实施批;策略开关生命周期第 1 态)。

设计单一源 = ``.debug/temp/currency_war/w795_realization_design/REPORT.md``
v2/v3(侧一搜牌/侧二买入/侧三合成时点/侧四部署+方向 + W797 D1/D2 并入);
开臂判据挂账 = 同目录 ``PREREG_兑现链A_B.md`` v3(M1-M4/G1-G7)。

全部函数在 ``registry.realization_chain_enabled``(伞)与对应子旗标同时
为真时才产生非零输出——默认关 = 逐位零漂移锚(生产默认行为不变)。
占位参数(κ/Δp_tier/R_min/γ/β/时点项单位)不做生产决策,开臂前 sim
扫描标定(§6 挂账;标定批前置依赖 board_next_tier 观测键归
W793 后继批,不阻塞开臂——W796 复核 N2)。

辖域边界声明:本模块只产「评分加项/键分量/辖域判定」等纯函数输入,
不直接发射动作、不碰金账——金地板/息账/copies_cap/bench 容量照常由
arbiter 约束链统一收口(与 ADR-0438 豁免通道「放行≠必买」同纪律)。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
from sr_od.application.currency_war.decision.cw_strategy import StrategySession
from sr_od.application.currency_war.decision.decision_v2.filters import (
    is_emergency,
)
from sr_od.application.currency_war.kernel.cw_discipline_rules import (
    star_weighted_copies,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    IntentionState,
    locked_buy_scope,
    locked_faction_scope,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BuyCard,
    GameState,
    bench_occupied,
)

#: 合成候选的持有份数权重(设计侧三:排序权重随持有份数 1/2→2/3
#: 递增;merge 候选构造性持有 2 份 → 2/3,常量非标定值而是份数比)。
_MERGE_HELD_FRAC: float = 2.0 / 3.0


def _chain_on(registry: DecisionV2Registry, sub: bool) -> bool:
    """伞开关 × 子旗标合取(全部消费点的统一进门判)。"""
    return registry.realization_chain_enabled and sub


def _ist(session: StrategySession | None) -> IntentionState | None:
    ist = getattr(session, 'v3_intention', None)
    return ist if isinstance(ist, IntentionState) else None


def missing_members(state: GameState, session: StrategySession,
                    registry: DecisionV2Registry,
                    cost_band: frozenset[int] | None = None,
                    ) -> dict[str, float]:
    """锁定帧缺件清单(W795 v2 侧一/侧二/侧三共用判据单一源)。

    缺件定义(设计 §2 侧一):该成员未上场 ∧ 名下某**锁定线羁绊**档位
    k→k+1 恰达(board 计数 +1 命中尚未达的档;已满档贡献记饱和——
    防囤满档件)。返回 {成员名: s},s = 当前档位填充率(cur/下一档,
    P29 的 (1−s) 折算输入)。与搜牌缺档加权/合成档位未满守卫同一函数,
    禁两侧各派生(W796 面 4.3「两侧不同步」缺口收口)。

    - ``cost_band``:费用域过滤(None=不过滤;搜牌侧传
      ``registry.realization_member_cost_band``,3-4 费有效域)。
    - 排除:已上场(上场份不新增档位计数,同名禁双)/ 加权副本达上限
      (第 4 份纯浪费)。
    """
    ist = _ist(session)
    if ist is None:
        return {}
    scope = locked_buy_scope(ist)
    if not scope:
        return {}
    bond_keys = locked_faction_scope(ist)
    if not bond_keys:
        return {}
    deployed_names = {getattr(d, 'char_id', '') or ''
                      for d in (state.deployed or [])}
    board = state.board or {}
    out: dict[str, float] = {}
    for name in sorted(scope):
        ch = CHARACTERS.get(name)
        if ch is None or name in deployed_names:
            continue
        if cost_band is not None and (ch.cost or 0) not in cost_band:
            continue
        if star_weighted_copies(name, state) >= registry.copies_cap:
            continue
        bonds = (set(ch.factions or ()) | set(ch.flows or ())) & bond_keys
        for b in sorted(bonds):
            info = FACTIONS.get(b)
            if info is None or not info.tiers:
                continue
            cur = int(board.get(b, 0) or 0)
            nxt = next((t for t in info.tiers if t == cur + 1), None)
            if nxt is None:
                continue   # 该羁绊不构成 k→k+1 恰达(已满档/跨档不辖)
            out[name] = cur / float(nxt)
            break
    return out


def refresh_search_term(state: GameState, session: StrategySession,
                        registry: DecisionV2Registry) -> float:
    """搜牌侧:缺件感知定向刷新评分加项(修断点①-b;锁 #8)。

        val += Δp_tier · P(本刷出缺件)

    - P = 1−Π(1−refresh_prob(level, cost))(缺件费用档去重;概率
      单一址 = cw_shop_odds);
    - **金水位辖域门(P5 自洽)**:花完仍 < 息线的帧预算≈0 → 加项为
      0(强制破息的账在血线恶化段为负 EV,[22]④;破息搜牌归止损
      支出既判辖域);
    - 有效域 = 3-4 费缺件(低费死支已删除,W796 面 2)。
    """
    if not _chain_on(registry, registry.realization_search_enabled):
        return 0.0
    refresh_cost = int(state.shop_refresh_cost or 2)
    if (state.gold or 0) - refresh_cost < registry.interest_floor():
        return 0.0   # 金水位辖域门:破息帧缺件感知不驱动刷新
    missing = missing_members(state, session, registry,
                              cost_band=registry.realization_member_cost_band)
    if not missing:
        return 0.0
    p_miss = 1.0
    for name in missing:
        ch = CHARACTERS.get(name)
        if ch is None or not ch.cost:
            continue
        p_miss *= (1.0 - refresh_prob(state.level, ch.cost))
    return registry.realization_delta_p_tier * (1.0 - p_miss)


def p29_priority_term(cand, state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> float:
    """买入侧:P29 羁绊感知囤牌优先级加项(修断点②-b;锁 #4 含反向锁)。

        val += Δp_tier · R_rest · (1−s)

    - 候选 = 锁定线缺档成员(缺件判据单一源,费用域不过滤——囤牌
      优先级不限 3-4 费,搜牌侧才是有效域收窄);
    - **事前辖域门(设计 v2 §2 侧二)**:hp ≥ 报警线
      (registry.blood_margin_low_hp)∨ R_rest ≥ R_min 才启用——局 6 型
      边流血段 EV 符号不稳健且每金的止损用途期望更高,本设计让位;
    - bench 挤占定性门([34]):占用 ≥ 容量−1 禁囤。
    """
    if not _chain_on(registry, registry.realization_buy_enabled):
        return 0.0
    a = getattr(cand, 'action', None)
    if not isinstance(a, BuyCard) or getattr(cand, 'merge', False):
        return 0.0
    if is_emergency(state, registry):
        return 0.0
    if bench_occupied(state.bench or []) >= registry.bench_capacity - 1:
        return 0.0   # bench 挤占:临近满栏禁囤([34] 定性先行)
    from sr_od.application.currency_war.decision.decision_v2.ev import (
        battles_left_plane,
    )
    r_rest = battles_left_plane(state, session, registry)
    if (state.hp < registry.blood_margin_low_hp
            and r_rest < registry.realization_p29_r_min):
        return 0.0   # 反向锁:血线辖域门未开 → 囤牌优先级不启用
    missing = missing_members(state, session, registry)
    name = getattr(getattr(a, 'card', None), 'name', '') or ''
    if name not in missing:
        return 0.0
    return registry.realization_delta_p_tier * r_rest * (1.0 - missing[name])


def merge_timing_term(cand, state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> float:
    """合成时点侧:merge 候选「合成后档位进度时点」排序显影
    (修断点③-a 重述;锁 #1 回归锁辖豁免通道,排序锁标定批后另落)。

        val += 时点项单位 · (2/3) · R_rest

    - **非新豁免**:ADR-0437/0438 merge 完成豁免(默认开)不动,本项
      只改排序;豁免注释的防双计声明继续辖(本项在评分层,豁免在
      arbiter 门层,作用面不相交);
    - 守卫(锁 #2):①档位未满——已满档贡献成员的第 3 份不获显影
      (缺件判据单一源,防「假合成正分」);②星级守卫——合成产物与
      deployed 同名不可上场(5.1.7)→ 零时点价值,混合星级态第 3 份
      1★ 同辖;
    - 份数权重 = 2/3(merge 候选构造性持有 2 份,设计「1/2→2/3」的
      端点;份数比非标定值)。
    """
    if not _chain_on(registry, registry.realization_merge_timing_enabled):
        return 0.0
    a = getattr(cand, 'action', None)
    if not isinstance(a, BuyCard) or not getattr(cand, 'merge', False):
        return 0.0
    name = getattr(getattr(a, 'card', None), 'name', '') or ''
    if not name:
        return 0.0
    if any(getattr(d, 'char_id', '') == name
           for d in (state.deployed or [])):
        return 0.0   # 星级守卫:合成产物上场不可达 → 零时点价值
    if name not in missing_members(state, session, registry):
        return 0.0   # 档位未满守卫:已满档第 3 份不显影
    from sr_od.application.currency_war.decision.decision_v2.ev import (
        battles_left_plane,
    )
    return (registry.realization_merge_timing_unit * _MERGE_HELD_FRAC
            * battles_left_plane(state, session, registry))


def sell_income_component(bc, registry: DecisionV2Registry) -> int | None:
    """D1:腾席弱序键的 income 分量(卖出回金+装备残值代理;锁 #10)。

    - 回金 = cw_state.sell_refund(star, cost)(单一源);装备残值 =
      每件 1 的代理(卖出回 owned 池非回金,残值无金真值——代理口径
      声明,量级标定挂账;升序键下高残值件后卖,局 6 p2r7「卖含装
      备 2★ 留 1★ 散件」反向消失);
    - 开关关 → None(键不含本分量,HEAD 行为逐位)。
    """
    if not _chain_on(registry, registry.realization_d1_enabled):
        return None
    from sr_od.application.currency_war.kernel.cw_state import sell_refund
    name = getattr(bc, 'char_id', '') or ''
    ch = CHARACTERS.get(name)
    if ch is None or not ch.cost:
        return None
    income = sell_refund(max(1, int(getattr(bc, 'star', 1) or 1)), ch.cost)
    return income + len(list(getattr(bc, 'equips', None) or []))


def d2_entry_frame(state: GameState, registry: DecisionV2Registry) -> bool:
    """D2:跨位面入口帧辖域判定(锁 #11 的窗口判定半边)。

    入口帧 = 位面切换首备战帧(round_num ≤ 1;谓词每位面至多真一帧 =
    「一次性」的结构保证)∧ hp 落死亡带(hp ≤ emergency_hp,与既有
    应急带同一状态源语义——W774⑤ 血线三带未落码,消费其上游共享源
    而非造第二血线判定)∧ 携金 > 息线(授权下限 = interest_floor
    单一源;局 6 P3r1 型 hp=1 携 92 金)。

    命中 → 分配器并入 DEATH 域(ADR-0474 账式复用,出清/约束链全部
    既有语义,不造第二分配器;W796 §二.2 辖域协调)。
    """
    if not _chain_on(registry, registry.realization_d2_enabled):
        return False
    return (int(state.round_num or 0) <= 1
            and state.hp <= registry.emergency_hp
            and (state.gold or 0) > registry.interest_floor())
