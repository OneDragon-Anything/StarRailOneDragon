"""决策框架 v2 层2:三级硬过滤链(ADR-0290 对抗修订②)。

redesign §3/§5.4 覆盖态**严格优先序**:应急(HP 危急)→ 追赶修饰
(窗口约束)→ 模式(经济/战力象限过滤)。上级覆盖态命中即收窄候选集,
下级不再放宽;应急/追赶是**硬过滤器而非评分项**(可被经济项投票淹死
= 29 批「局部合法组合失明」病的镜像)。

过滤器=谓词列表进 registry(层名→放行标签集/禁标签集);本模块只做
链选择与谓词映射,不含数值——**例外**:ADR-0302 危机局修复批的应急集
补充标签/危机囤金常量暂驻本模块(registry 为攻坚批在飞域,合流批上移)。
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


#: ADR-0302 应急集补充标签( 卖弱件 for_gold + 升级 levelup)。
#: 依据(redesign §5.4 应急态语义 = 战力买+卖弱件+升级):批㉝ F4 实证
#: 旧 emergency_tags 缺 for_gold(应急态弱件卖出候选生成即被层2
#: 滤死——卖弱件通道在应急态整体死亡)与 levelup([17]「金>50 的
#: 每一分都没有存的意义,该升级升级」在应急态被滤出)。**待上移**:
#: registry 是攻坚批(ADR-0301)在飞域,本批不碰——合流批把本常量
#: 并入 registry.emergency_tags 后删除。
_EMERGENCY_EXTRA_TAGS: frozenset[str] = frozenset({
    'for_gold', 'levelup',
})

#: ADR-0302 危机囤金修复常量(批㉝ F3 指纹:hp≤25 且金≥40 只升
#: 不买——战力买候选板面差分恒 0.00 被仲裁器「非正分」拒,金囤
#: 85+ 板濒死零动作)。**待上移**:同上,合流批进 registry。
#: 囤金金线:应急态金 ≥ 此值时战力买加偏置(F3 指纹阈值 40)
_CRISIS_HOARD_GOLD: int = 40
#: 危机战力买偏置(量级=off_target_sell_bias 量级的买侧对偶;
#: 只把 0 分板面差分顶成正分——金 52→49 的息崖 -25 不被它翻越,
#: 危机花费止于满息平台,符合 [18]「不为苟住破息引擎」)
_CRISIS_BUY_BIAS: float = 1.0
#: 偏置辖的战力买标签(经济类买 pair/copy/bond_fallback 本就被
#: 应急滤出,此处显式枚举防未来标签集变化误伤)
_CRISIS_BUY_TAGS: frozenset[str] = frozenset({
    'line_carry', 'line_opportunistic', 'bridge_core',
    'engine_seed', 'carry_gate',
})


def crisis_hoard_active(state: GameState,
                        registry: DecisionV2Registry) -> bool:
    """危机囤金态(ADR-0302):应急态(hp≤emergency_hp)且金≥囤金线。

    消费点:scoring 战力买偏置(层3)/判读。检查网哨兵
    decision_v2_crisis_gold_hoard 锁该态零买入回归(批㉝ 5/100 局
    → 修复目标 0)。
    """
    return (is_emergency(state, registry)
            and (state.gold or 0) >= _CRISIS_HOARD_GOLD)


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
        # ADR-0302:应急集 = registry.emergency_tags ∪ 补充标签
        # (卖弱件+升级;见 _EMERGENCY_EXTRA_TAGS 注释)。危机囤金态
        # (金≥40)额外放行 refresh——金在手而店无战力件时搜牌补板是
        # 唯一变现通道([17]「>50 的每一分都没有存的意义,该D牌D牌」);
        # 金<40 的应急态 refresh 仍滤出(应急集收窄不变)
        allowed = registry.emergency_tags | _EMERGENCY_EXTRA_TAGS
        if crisis_hoard_active(state, registry):
            allowed = allowed | frozenset({'refresh'})
        return allowed, frozenset()
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
