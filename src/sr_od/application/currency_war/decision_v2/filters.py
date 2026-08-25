"""决策框架 v2 层2:三级硬过滤链(ADR-0290 对抗修订②)。

redesign §3/§5.4 覆盖态**严格优先序**:应急(HP 危急)→ 追赶修饰
(窗口约束)→ 模式(经济/战力象限过滤)。上级覆盖态命中即收窄候选集,
下级不再放宽;应急/追赶是**硬过滤器而非评分项**(可被经济项投票淹死
= 29 批「局部合法组合失明」病的镜像)。

过滤器=谓词列表进 registry(层名→放行标签集/禁标签集);本模块只做
链选择与谓词映射,不含数值(ADR-0302 暂驻本模块的应急集补充标签/
危机囤金常量已由合流批 ADR-0303 上移 registry)。

成型停手(ADR-0343)是覆盖态之后的**动作级后置步**(非第四覆盖态):
formed_stop_active 五项判定([13] 三件套+r7+辖域)命中时丢弃全部
BuyCard 候选——语义是「不再买牌」而非「收窄某域」,按动作类型拦
(对标签表漂移稳健);标志落 session.v3_formed_stop 供遥测/检查器。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_intention import (
    IntentionState,
    intention_core,
)
from sr_od.application.currency_war.cw_state import BuyCard, GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.candidates import Candidate
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)


def is_emergency(state: GameState,
                 registry: DecisionV2Registry) -> bool:
    """应急触发(绝对 HP 档简版;redesign §5.4 Phase A 口径)。"""
    return state.hp <= registry.emergency_hp


def formed_stop_active(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> bool:
    """成型停手态([13] 停手线;ADR-0343)。

    判定=五项全过(每一项映射 [13] 三件套 + 证据窗 + 位面辖域):
    1. P1 ∧ r≥formed_stop_min_round(7)——[13] 是位面 1 过渡语义,
       W97/W105 晚买有害证据窗=r7-r9;P2/P3 终局线恢复要买,不辖;
    2. level≥formed_stop_min_level(5)——[13]「lv5-6」下界(等级到位);
    3. 意向 locked 且锁定线可解析——[13] 的「过渡阵容」预设配方
       (unlocked/兜底局「羁绊凑够」无定义,保守不辖);
    4. 羁绊凑够——锁定线 form_tiers 全键满足(board 计数≥tier 下限;
       cw_comps form_tiers 文档「几人激活算成型」,成型判定读下限);
    5. 过渡核心 2 星——intention_core 在 bench∪deployed 最大 star≥2
       (与 discipline carry_gate 同一核心单一源)。

    命中后层2 后置步丢弃全部 BuyCard 候选(应急态亦不豁免——
    W105 指认的「低血→应急强制买」反因正是本纪律的对象;[13] 板面
    已成的处置梯度=deploy 优化+refresh 搜牌,不需要继续囤件);
    levelup([12]/[33] 人口位例外)/refresh(保血通道)/卖/合装不辖。
    """
    if not registry.formed_stop_enabled:
        return False
    if state.plane != 1 or state.round_num < registry.formed_stop_min_round:
        return False
    if state.level < registry.formed_stop_min_level:
        return False
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState) or ist.phase != 'locked':
        return False
    from sr_od.application.currency_war.cw_comps import get_comp
    comp = get_comp(ist.locked_comp)
    if comp is None or not comp.form_tiers:
        return False   # 线不可解析/无羁绊线(反甲类):保守不辖
    board = state.board or {}
    if any((board.get(f) or 0) < t for f, t in comp.form_tiers.items()):
        return False
    core = intention_core(comp)
    if not core:
        return False
    pool = [bc for bc in list(state.bench or []) + list(state.deployed or [])
            if bc is not None and bc.char_id == core]
    return any((getattr(bc, 'star', 1) or 1) >= 2 for bc in pool)


def crisis_hoard_active(state: GameState,
                        registry: DecisionV2Registry) -> bool:
    """危机囤金态(ADR-0302):应急态(hp≤emergency_hp)且
    金≥registry.crisis_hoard_gold。

    消费点:scoring 战力买偏置(层3)/判读。检查网哨兵
    decision_v2_crisis_gold_hoard 锁该态零买入回归(批㉝ 5/100 局
    → 修复目标 0)。
    """
    return (is_emergency(state, registry)
            and (state.gold or 0) >= registry.crisis_hoard_gold)


def is_catchup(state: GameState, session: StrategySession,
               registry: DecisionV2Registry) -> bool:
    """追赶修饰态(等级门版:等级已够高仍低于位面基线才算追赶;
    P1 早期人口低于基线是常态非落后——r232)。"""
    pop = len(state.deployed or [])
    baseline = registry.pop_baseline.get(state.plane, 7)
    return (pop < baseline - 1
            and state.level >= registry.catchup_min_level)


def current_mode(session: StrategySession) -> str:
    """当前模式(economy/war;载体批 W35:新载体读 session.v3_mode——
    纪律族 assess_discipline 每轮写;旧 v2_state 兜底随 ADR-0336 删除)。"""
    v3 = getattr(session, 'v3_mode', None)
    if v3 in ('economy', 'war'):
        return v3
    return 'economy'


def _allowed_tags(state: GameState, session: StrategySession,
                  registry: DecisionV2Registry) -> tuple[frozenset[str],
                                                        frozenset[str]]:
    """按覆盖态优先序选 (放行标签集, 禁标签集)。

    应急 > 追赶 > 模式;上级命中即返回,下级不再参与。
    """
    if is_emergency(state, registry):
        # ADR-0302/0303:应急集=registry.emergency_tags(已含卖弱件
        # for_gold+升级 levelup)。危机囤金态(金≥crisis_hoard_gold)
        # 额外放行 refresh——金在手而店无战力件时搜牌补板是唯一变现
        # 通道([17]「>50 的每一分都没有存的意义,该D牌D牌」);
        # 金<crisis_hoard_gold 的应急态 refresh 仍滤出(应急集收窄不变)
        allowed = registry.emergency_tags
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
    成型停手(ADR-0343)为**覆盖态之后的动作级后置步**:五项判定
    (见 formed_stop_active)命中时丢弃全部 BuyCard 候选——含
    应急态(反因路径正是本纪律对象);标志写 session.v3_formed_stop
    供遥测行/检查器豁免消费(单次调用=单轮决策,策略主循环唯一入口)。
    """
    allowed, forbidden = _allowed_tags(state, session, registry)
    level = ('emergency' if is_emergency(state, registry)
             else 'catchup' if is_catchup(state, session, registry)
             else 'mode')
    formed_stop = formed_stop_active(state, session, registry)
    session.v3_formed_stop = formed_stop
    kept: list[Candidate] = []
    log: list[dict] = []
    for c in cands:
        ok = c.tag in allowed and c.tag not in forbidden
        if ok and formed_stop and isinstance(c.action, BuyCard):
            ok = False   # [13] 停手:成型后 P1 r7+ 不再买牌(动作级)
        log.append({'tag': c.tag, 'kept': ok, 'level': level,
                    'formed_stop': formed_stop and isinstance(c.action, BuyCard)})
        if ok:
            kept.append(c)
    return kept, log
