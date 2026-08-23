"""决策框架 v2 层2:三级硬过滤链(ADR-0290 对抗修订②)。

redesign §3/§5.4 覆盖态**严格优先序**:应急(HP 危急)→ 追赶修饰
(窗口约束)→ 模式(经济/战力象限过滤)。上级覆盖态命中即收窄候选集,
下级不再放宽;应急/追赶是**硬过滤器而非评分项**(可被经济项投票淹死
= 29 批「局部合法组合失明」病的镜像)。

过滤器=谓词列表进 registry(层名→放行标签集/禁标签集);本模块只做
链选择与谓词映射,不含数值。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.candidates import Candidate
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)


def is_emergency(state: GameState,
                 registry: DecisionV2Registry) -> bool:
    """应急触发(绝对 HP 档简版;redesign §5.4 Phase A 口径)。"""
    return state.hp <= registry.emergency_hp


def is_catchup(state: GameState, session: StrategySession,
               registry: DecisionV2Registry) -> bool:
    """追赶修饰态(等级门版:等级已够高仍低于位面基线才算追赶;
    P1 早期人口低于基线是常态非落后——r232)。"""
    pop = len(state.deployed or [])
    baseline = registry.pop_baseline.get(state.plane, 7)
    return (pop < baseline - 1
            and state.level >= registry.catchup_min_level)


def current_mode(session: StrategySession) -> str:
    """当前模式(economy/war;读 cw_phase_machine 状态机 mode 位)。"""
    v2 = getattr(session, 'v2_state', None)
    if not v2:
        return 'economy'
    return v2[0] if v2[0] in ('economy', 'war') else 'economy'


def _allowed_tags(state: GameState, session: StrategySession,
                  registry: DecisionV2Registry) -> tuple[frozenset[str],
                                                        frozenset[str]]:
    """按覆盖态优先序选 (放行标签集, 禁标签集)。

    应急 > 追赶 > 模式;上级命中即返回,下级不再参与。
    """
    if is_emergency(state, registry):
        return registry.emergency_tags, frozenset()
    if is_catchup(state, session, registry):
        return registry.catchup_tags, registry.catchup_forbidden_tags
    if current_mode(session) == 'economy':
        return registry.economy_tags, frozenset()
    return registry.war_tags, frozenset()


def filter_candidates(cands: list[Candidate], state: GameState,
                      session: StrategySession,
                      registry: DecisionV2Registry,
                      ) -> tuple[list[Candidate], list[dict]]:
    """层2 入口:按覆盖态过滤候选集;返回 (存活候选, 链日志)。

    链日志=判读可直接读的过滤记录(哪级命中、每个候选去留)。
    """
    allowed, forbidden = _allowed_tags(state, session, registry)
    level = ('emergency' if is_emergency(state, registry)
             else 'catchup' if is_catchup(state, session, registry)
             else 'mode')
    kept: list[Candidate] = []
    log: list[dict] = []
    for c in cands:
        ok = c.tag in allowed and c.tag not in forbidden
        log.append({'tag': c.tag, 'kept': ok, 'level': level})
        if ok:
            kept.append(c)
    return kept, log
