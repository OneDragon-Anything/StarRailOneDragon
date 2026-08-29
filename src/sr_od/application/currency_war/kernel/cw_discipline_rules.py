"""决策纪律·卖侧下界/种子年龄判据族(分包期 0b 自 decision_v2.discipline
下沉,§3.3-①e)。

下沉闭包 = cw_evolution 溢出卖出/种子豁免消费面:
``sole_engine_sell_floor_plan``(批量逐笔下界,ADR-0380)及其计数底座
(``_sell_floor_counts/_eval/_decrement``,ADR-0373/0375 单一源)、
``seed_age_blocked``(engine_seed 年龄豁免,ADR-0289/0339)及其计数
依赖 ``star_weighted_copies``。全部为纯谓词(不依赖线库/桥池;
registry 注解在 cw_registry 下沉 kernel 后 kernel 内自洽)——
discipline 余部(行为臂/纪律视图)留 decision 桶,经本模块消费同一
计数底座(单一源不破)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import GameState

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_strategy_session import (
        StrategySession,
    )

def star_weighted_copies(name: str, state: GameState) -> int:
    """同名星级加权副本数(bench+deployed;2★=2 份,3★=3 份)。"""
    n = sum(getattr(b, 'star', 1) or 1
            for b in (state.bench or []) if b is not None
            and b.char_id == name)
    n += sum(getattr(d, 'star', 1) or 1
             for d in (state.deployed or [])
             if getattr(d, 'char_id', '') == name)
    return n


def sole_engine_sell_floor_plan(bcs: list,
                                state: GameState,
                                registry: DecisionV2Registry | None = None,
                                ) -> list[bool]:
    """W197/ADR-0380:同批多笔卖出的逐笔下界判定(批量口径)。

    背景(136 r7 实证):arbitrate 同段可采纳多笔同名 TT 件卖候选——
    候选生成对**批前状态**计数(列车在手 3>tier 2),逐笔合法而批内
    聚合 3→1 跌破 tier。``sole_engine_sell_blocked`` 单件口径对同批
    前序卖出不可见——本函数按 ``bcs`` 顺序逐笔评估,**前序判定为
    「可卖」的件从计数扣减**(blocked 件不卖、不扣减);单笔输入时
    与单件谓词逐位一致(同一计数底座/同一辖域判据,ADR-0373/0375)。

    消费面:arbiter 卖候选采纳点(对 working 复检,前序扣减由 working
    前序采纳天然实现)/ execute_replacement 溢出卖出下界(ADR-0380
    件1,事务内多笔同序扣减)/ remediation 两补偿器卖件组发射前过滤
    (ADR-0384 ``_sell_floor_filter``,对 working 逐笔扣减)。
    """
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    counts = _sell_floor_counts(state, reg)
    out: list[bool] = []
    for bc in bcs:
        name = getattr(bc, 'char_id', '') or ''
        ch = CHARACTERS.get(name)
        if not reg.sell_sole_engine_guard_enabled or ch is None:
            out.append(False)
            continue
        bonds = set(ch.factions) | set(ch.flows)
        blocked = _sell_floor_eval(name, bonds, counts)
        out.append(blocked)
        if not blocked:
            _sell_floor_decrement(name, bonds, counts)
    return out


def _sell_floor_counts(state: GameState,
                       reg: DecisionV2Registry) -> dict:
    """下界守卫计数底座(ADR-0373/0375/0380 单一源)。

    返回可变计数 dict:
    - TT 三羁绊键 → {'tier': 门槛, 'count': 在手件数(bench∪deployed
      逐件计,全羁绊 factions∪flows 口径)};
    - '_seele_scope'(辖域开关)/'_seele_core'(希儿在手)/
      '_seele_core_copies'(希儿副本数)/'_seele_amp:{阵营}'(放大阵营
      在手件数)——希儿系核心条件辖(W192/ADR-0375 判据)。
    """
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        SEELE_AMP_FACTIONS,
        TRANSITION_TRAITS,
    )
    counts: dict = {b: {'tier': t, 'count': 0} for b, t in TRANSITION_TRAITS}
    pool = [p for p in (*state.bench, *state.deployed)
            if p is not None and p.char_id]
    core_copies = 0
    amp_counts = dict.fromkeys(SEELE_AMP_FACTIONS, 0)
    for p in pool:
        pc = CHARACTERS.get(p.char_id)
        if pc is None:
            continue
        pb = set(pc.factions) | set(pc.flows)
        for b in counts:
            if b in pb:
                counts[b]['count'] += 1
        if p.char_id == '希儿':
            core_copies += 1
        else:
            for f in amp_counts:
                if f in pb:
                    amp_counts[f] += 1
    counts['_seele_scope'] = reg.guard_seele_scope_enabled
    counts['_seele_core_copies'] = core_copies
    counts['_seele_core'] = core_copies > 0
    for f, c in amp_counts.items():
        counts[f'_seele_amp:{f}'] = c
    return counts


def _sell_floor_eval(name: str, bonds: set, counts: dict) -> bool:
    """单件下界判定(对计数底座;TT ≤tier + 希儿系条件辖,两判据取或)。"""
    blocked = any(v['count'] <= v['tier'] for b, v in counts.items()
                  if not b.startswith('_') and b in bonds)
    if not blocked and counts.get('_seele_scope'):
        if name == '希儿':
            blocked = counts.get('_seele_core_copies', 0) <= 1
        else:
            amp = {b for b in bonds
                   if f'_seele_amp:{b}' in counts}
            if amp and counts.get('_seele_core'):
                blocked = any(counts[f'_seele_amp:{f}'] <= 2 for f in amp)
    return blocked


def _sell_floor_decrement(name: str, bonds: set, counts: dict) -> None:
    """该件将卖出 → 计数底座扣减(批量口径的前序可见性)。"""
    for b, v in counts.items():
        if not b.startswith('_') and b in bonds:
            v['count'] -= 1
    if name == '希儿':
        counts['_seele_core_copies'] = counts.get('_seele_core_copies', 0) - 1
        counts['_seele_core'] = counts['_seele_core_copies'] > 0
    else:
        for f in bonds:
            k = f'_seele_amp:{f}'
            if k in counts:
                counts[k] -= 1


def seed_age_blocked(bc, state: GameState,
                     session: StrategySession | None) -> bool:
    """ADR-0289 §5:engine_seed 年龄豁免——买入 ≤2 轮且同轮份数 <2 的种子
    不进可卖集(跨轮窗;同轮 ≥2 份=3合1 素材语境豁免)。

    W88(ADR-0339 件3):cnt≥2 豁免加**实际持有对账**(star_weighted_
    copies≥2)——采纳处登记可能在同轮重复计数(采纳后被执行层否决的
    买入也留痕,seed16 姬子·启行单买 cnt=2 实证),幻影 cnt 会静默解除
    种子保护 → 买/卖互踩;以「真持有 ≥2 份」为素材语境判据。
    """
    name = getattr(bc, 'char_id', '')
    if not name or session is None:
        return False
    rec = (getattr(session, 'v2_seed_bought', None) or {}).get(name)
    if rec is None:
        return False
    key, cnt = rec
    if key[0] != state.plane:
        return False
    if not 0 <= state.round_num - key[1] <= 2:
        return False
    if cnt < 2:
        return True
    # cnt≥2:素材语境豁免仅当**真持有** ≥2 份;幻影计数(登记重复/
    # 执行层否决留痕)不解除保护
    return star_weighted_copies(name, state) < 2
