"""R-B 三信号商店件定价(W920 设计件批B;策略开关生命周期第 1 态)。

设计单一源 = ``.debug/temp/currency_war/w920_rb_design/DESIGN.md``
(判据面=商店件定价全件,线内囤牌+线外件 §2-D1;三信号命题 §3-D3;
接口声明 §2-D4)。命题:P20(激活边际,proofs/p20-transition-
activation-vs-starup.md)/ stage_transitions Q1(逐卡 E→F 留存,
docs/game/currency_war/research/stage_transitions.md)/ P1+P16(费级
再遇窗口,窗口单一源=registry.remeet_window_rounds)。决策 why 挂账
ADR 由批C 补(本批文件面不含 decisions/)。

**与 piece_value 的结构区别(W902 终裁禁复活加权黑盒)**:三信号各自
独立披露(``bd['rb_s1/rb_s2/rb_s3']``),各自可单独否决(权重=0 即关),
不合成任何「件总价值」。

伞开关 ``rb_signal_pricing_enabled`` 默认关 = 零漂移锚;开臂判据挂账
= docs/develop/currency_war/prereg/w947_rb_signal_pricing_prereg.md。

边界声明:本模块只产「评分加项」纯函数输入,不发射动作、不碰金账;
息成本不进新信号(既有 int_emb/息崖平滑照旧全额计入,买不买由
「正项−息成本」代数和过非正分门裁决——DESIGN §2-D4 息律接口:新定价
永远不为买外件建议破息)。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.decision.cw_strategy import StrategySession
from sr_od.application.currency_war.decision.decision_v2.candidates import (
    Candidate,
)
from sr_od.application.currency_war.decision.decision_v2.tier_push import (
    intended_bond_keys,
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    TRANSITION_TRAITS,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    IntentionState,
    locked_buy_scope,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BuyCard,
    GameState,
)

#: 过渡体系档位阈值(单一源 = cw_deploy_logic.TRANSITION_TRAITS,与
#: tier_push._TIER_OF 同派生)。
_TIER_OF: dict[str, int] = dict(TRANSITION_TRAITS)

#: 再遇窗口归一基准(P1 已证 5 费@7-8 级窗口 60-180 轮的拟合中值;
#: 单一源 = registry.remeet_window_rounds[5],此处只取归一分母)。
_S3_WINDOW_NORM: int = 120


def _bond_counts(state: GameState) -> dict[str, int]:
    """deployed∪bench 闭包的过渡体系羁绊计数(P19 计数语义;DESIGN
    §2-D4:凑档判定必须基于当前 deployed+bench 闭包)。"""
    counts: dict[str, int] = {}
    units: list[str] = [getattr(d, 'char_id', '') or ''
                        for d in (state.deployed or [])]
    units += [b.char_id for b in (state.bench or []) if b is not None]
    for name in units:
        ch = CHARACTERS.get(name)
        if ch is None:
            continue
        for b in (set(ch.factions or ()) | set(ch.flows or ())) & set(_TIER_OF):
            counts[b] = counts.get(b, 0) + 1
    return counts


def _seen_count(state: GameState, session: StrategySession,
                name: str) -> int:
    """该卡的本局轮级见次(含当次;S3 计次衰减输入)。

    粒度=备战轮:每轮首次评分时把当轮店内卡名并入计数,轮内刷新
    (店换牌)不重复计次(计次口径=「第几轮见到」,取严侧为轮)。计数
    挂 session(惰性初始化,轮键换挡时并入;伞关时不进入本函数=零
    副作用)。
    """
    key = (state.plane, state.round_num)
    if getattr(session, 'rb_seen_round_key', None) != key:
        session.rb_seen_round_key = key
        counts = getattr(session, 'rb_seen_counts', None)
        if not isinstance(counts, dict):
            counts = {}
            session.rb_seen_counts = counts
        for c in (state.shop or []):
            n = getattr(c, 'name', '') or ''
            if n:
                counts[n] = counts.get(n, 0) + 1
    counts = getattr(session, 'rb_seen_counts', {})
    return counts.get(name, 1)


def _s1_activation(cand: Candidate, state: GameState,
                   after_state: GameState,
                   session: StrategySession,
                   registry: DecisionV2Registry) -> float:
    """S1 激活信号(可激活钥匙件;P20 唯一消费面,DESIGN §3-D3 S1)。

    开火条件(全部满足才计,任一不满足=0):
    - 候选羁绊(=_cand_system_bonds 同源名集口径,经 CHARACTERS 派生)
      中某过渡体系跨其最低档:闭包计数从 档位下界−1 → ≥下界;
    - 该体系 ∉ 意向键集(锁定线体系;线内凑档由 tp_gap 缺口差分计值,
      本项只补「线外凑档」避免同档双计);
    - P20 辖域 e<2:跨档前达成档的体系数 <2(达成后再激活边际衰减,
      P20 辖域声明「严格限 e<2」)。
    """
    a = cand.action
    name = getattr(getattr(a, 'card', None), 'name', '') or ''
    ch = CHARACTERS.get(name)
    if ch is None:
        return 0.0
    cand_bonds = ((set(ch.factions or ()) | set(ch.flows or ()))
                  & set(_TIER_OF))
    if not cand_bonds:
        return 0.0
    keys = intended_bond_keys(state, session)
    cand_bonds -= set(keys)
    if not cand_bonds:
        return 0.0
    before = _bond_counts(state)
    formed_before = sum(1 for b, t in _TIER_OF.items()
                        if before.get(b, 0) >= t)
    if formed_before >= 2:
        return 0.0
    after = _bond_counts(after_state)
    n = 0
    for b in cand_bonds:
        t = _TIER_OF[b]
        if before.get(b, 0) == t - 1 and after.get(b, 0) >= t:
            n += 1
    return n * registry.rb_s1_unit


def _s2_retention(cand: Candidate,
                  registry: DecisionV2Registry) -> float:
    """S2 贯穿信号(通用贯穿件;Q1 留存字段化,DESIGN §3-D3 S2)。

    贯穿性是卡的属性不随 target 变(F3 千冶·刃/F2 姬子·启行同根病灶);
    注册表逐卡字段(rb_retention_q1)≥ 阈值时持正价 = unit×留存率。
    表外卡无字段 = 0(不猜)。不做逐卡手写名单(DESIGN §5-3)。
    """
    name = getattr(getattr(cand.action, 'card', None), 'name', '') or ''
    ret = registry.rb_retention_q1.get(name)
    if ret is None or ret < registry.rb_s2_threshold:
        return 0.0
    return registry.rb_s2_unit * ret


def _s3_option(cand: Candidate, state: GameState,
               session: StrategySession,
               registry: DecisionV2Registry) -> float:
    """S3 囤牌期权信号(费级再遇窗口;P1/P16,DESIGN §3-D3 S3)。

    期权价 = unit × 窗口占比 × 计次衰减:窗口取费级单一源
    (registry.remeet_window_rounds,候选费的再遇期望轮数)归一到 5 费
    中值 120 轮(窗口短价趋零:1 费 11/120≈0.09);同卡每多见一次,
    期权折半(1/见次——再遇兑现过的期权不该重复全额支付)。上限小
    (P4:不为压库花息),表内由 unit 占位 0.5 承载。子旗标
    rb_s3_enabled=False 时恒 0(W947 批C 拆臂:S3 关臂)。
    """
    if not registry.rb_s3_enabled:
        return 0.0
    a = cand.action
    name = getattr(getattr(a, 'card', None), 'name', '') or ''
    ch = CHARACTERS.get(name)
    cost = (ch.cost if ch is not None else None) \
        or getattr(getattr(a, 'card', None), 'cost', 0) or 0
    window = registry.remeet_window_rounds.get(cost)
    if not window:
        return 0.0
    seen = _seen_count(state, session, name)
    return registry.rb_s3_unit * (window / _S3_WINDOW_NORM) / max(seen, 1)


def rb_offpiece_term(cand: Candidate, state: GameState,
                     after_state: GameState | None,
                     session: StrategySession,
                     registry: DecisionV2Registry) -> tuple[float, dict]:
    """三信号定价加项(DESIGN §3 落点:tp_gap 之后、off_lock 降级之前
    ——线外候选经既有 W802 κ 折扣通道比例折扣,零新增罚分机制)。

    返回 (加项总值, 披露键 dict);伞关/未锁线帧/非买候选/非 P1 恒
    (0.0, {})。辖域声明:锁定帧
    (``locked_buy_scope`` 非 None)内全部 BuyCard(线内囤牌+线外件同
    一判据面,DESIGN §2-D1);未锁线帧不存在「线外」概念,信号=0。
    病灶样本(F1/F2/F3/13-4)均在 P1 锁定帧,本版辖 P1(P2+ 挂账批C
    按开火面数据裁定)。
    """
    keys: dict[str, float] = {}
    if not registry.rb_signal_pricing_enabled:
        return 0.0, keys
    if state.plane != 1 or after_state is None:
        return 0.0, keys
    if not isinstance(cand.action, BuyCard):
        return 0.0, keys
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState) or locked_buy_scope(ist) is None:
        return 0.0, keys
    s1 = _s1_activation(cand, state, after_state, session, registry)
    s2 = _s2_retention(cand, registry)
    s3 = _s3_option(cand, state, session, registry)
    fires = getattr(session, 'rb_signal_fires', None)
    if not isinstance(fires, dict):
        fires = {}
        session.rb_signal_fires = fires
    if s1:
        keys['rb_s1'] = round(s1, 4)
        fires['s1'] = fires.get('s1', 0) + 1
    if s2:
        keys['rb_s2'] = round(s2, 4)
        fires['s2'] = fires.get('s2', 0) + 1
    if s3:
        keys['rb_s3'] = round(s3, 4)
        fires['s3'] = fires.get('s3', 0) + 1
    fires['n'] = fires.get('n', 0) + 1
    return s1 + s2 + s3, keys
