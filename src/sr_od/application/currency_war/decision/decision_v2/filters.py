"""决策框架 v2 层2:三级硬过滤链(ADR-0290 对抗修订②)。

redesign §3/§5.4 覆盖态**严格优先序**:应急(HP 危急)→ 追赶修饰
(窗口约束)→ 模式(经济/战力象限过滤)。上级覆盖态命中即收窄候选集,
下级不再放宽;应急/追赶是**硬过滤器而非评分项**(可被经济项投票淹死
= 29 批「局部合法组合失明」病的镜像)。

过滤器=谓词列表进 registry(层名→放行标签集/禁标签集);本模块只做
链选择与谓词映射,不含数值(ADR-0302 暂驻本模块的应急集补充标签/
危机囤金常量已由合流批 ADR-0303 上移 registry)。

成型停手(ADR-0343;W119/ADR-0347 收编 form_ok;W255/ADR-0410 目标件
白名单)是覆盖态之后的**动作级后置步**(非第四覆盖态):formed_stop 判定
(P1 ∧ comp 派生辖轮 ∧ form_ok)命中时丢弃 BuyCard 候选——**但目标件
白名单例外**([13] 正确语义:停的是过渡件,目标阵容件照买照囤,[21]/
[22] 成型后的正常行为);标志落 session.v3_formed_stop 供遥测/检查器。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.decision.cw_strategy import StrategySession
from sr_od.application.currency_war.decision.decision_v2.candidates import Candidate
from sr_od.application.currency_war.kernel.cw_intention import (
    IntentionState,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BuyCard,
    GameState,
)


def _formed_stop_buy_allowed(name: str | None, state: GameState,
                             session: StrategySession) -> bool:
    """成型停手态的买侧白名单判据(W255/ADR-0410)。

    [13] 正确语义:成型停的是「过渡件」——目标阵容件照买照囤
    ([21] final 件买而不上/[22] 有用先囤正是成型后阶段的正常行为)。
    判据单一源 = ``candidates._target_names``(意向载体 hoard 目标采购集
    ∪ 体系卡引擎件——[31] 三级羁绊梯队的目标层);白名单外的买(过渡件/
    散件/填充层)照旧拒。
    """
    if not name:
        return False
    from sr_od.application.currency_war.decision.decision_v2.candidates import (
        _target_names,
    )
    return name in _target_names(state, session)


def is_emergency(state: GameState,
                 registry: DecisionV2Registry) -> bool:
    """应急触发(单一源重定向,分包期 0b 单元2):本体下沉 kernel 桶
    cw_economy.is_emergency(refresh_ev_budget 合法 0 帧契约同源消费);
    本名保留为委托,消费方调用零改。"""
    from sr_od.application.currency_war.kernel.cw_economy import is_emergency
    return is_emergency(state, registry)


def _deploy_free(state: GameState) -> int:
    """当前可上阵空位数 = max(0, max_units − 上场占用)(ADR-0392 占用
    口径,与部署候选判据 deployed_occupied 同源)。"""
    from sr_od.application.currency_war.kernel.cw_state import deployed_occupied
    return max(0, state.max_units()
               - deployed_occupied(state.deployed or []))


def _deploy_free_after_merge(c: Candidate, state: GameState) -> int:
    """3合1 买入合成后的可上阵空位(合成豁免完备式的「合成后可上」判据)。

    c.merge=True 的 BuyCard 买入即触发全场域合成(cw_state._merge_bench:
    分组键=同名同星,合成载体=场上优先;被消份按槽位置 None 腾槽,
    ADR-0392)。合成腾出的上阵位只来自**场上**(deployed)同名同星份
    被消:场上份 ≥2 → 载体落场上、消 2 份占 1 份,净腾 1 位;场上份
    ≤1 → 净腾 0(1 份载体落场上占原位;0 份 2★ 落 bench——板满时
    无位可上,Δp_board=0,不构成战力增量)。
    """
    card = c.action.card
    star = max(1, int(getattr(card, 'star', 1) or 1))
    dep_copies = sum(
        1 for d in (state.deployed or [])
        if d is not None and (getattr(d, 'char_id', '') or '') == card.name
        and max(1, int(getattr(d, 'star', 1) or 1)) == star)
    return _deploy_free(state) + (1 if dep_copies >= 2 else 0)


def _refreshable_names(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> frozenset[str]:
    """C1 定向刷新存在性判据的名集(评分先验,非授权边界)。

    =目标件名集(``candidates._target_names``:意向载体目标∪体系卡引擎
    件)∪ 高费强件(费用 ≥ registry.directed_refresh_high_cost_floor 的
    注册表角色)。滤网只判「店内有无可买+上的名集件」这一存在性,买谁
    由 EV 层定价——名单从授权边界降为评分先验(对抗审计 A1-β 修法,
    报告=`.debug/temp/currency_war/w363_c3c4_attack/ATTACK.md`)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.decision.decision_v2.candidates import (
        _target_names,
    )
    names = set(_target_names(state, session))
    names |= {n for n, ch in CHARACTERS.items()
              if (getattr(ch, 'cost', 0) or 0)
              >= registry.directed_refresh_high_cost_floor}
    return frozenset(names)


# (C1 溢余必花定向辖域谓词 c1_directed_active 已随 c1_directed_spend
#  开关族删除——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3。)


def formed_stop_active(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> bool:
    """成型停手态([13] 停手线;ADR-0343,W119/ADR-0347 收编 form_ok)。

    判定(W114 交接注记落地——谓词族单一源,删本函数内重复实现):
    1. P1([13] 是位面 1 过渡语义;P2/P3 终局线恢复要买,不辖);
    2. r ≥ max(锁定线 typical_form_round, formed_stop_min_round)——
       comp 派生辖轮(W115-B1:固定 r≥7 与自家 typical_form_round 4-8
       矛盾,早成型阵容不必多买两轮、晚成型不提前停;typical 缺读取
       全局下界);
    3. form_ok(state, session, registry)——成型谓词本体在
       decision_v2.phase(意向锁×羁绊凑够×核心上场 2★;裁决后无
       等级项——等级通过上场完整性进入判定)。与 W114 前差异:
       核心必须上场 2★(旧 bench∪deployed);lv≥5 项删除(Q2 裁决)。
    4. (W227/ADR-0400 承接维)r ≥ handoff_gate_min_round(末窗)时
       还需投影承接档位达标(handoff.handoff_gate_gap==0)——form_ok
       是 P1 语义「能不能过 P1」,承接维补「带进 P2 够不够活」:
       末窗承接缺口>0 → 不停手继续投资([18] 位面末 ALL IN 的承接
       扩展);非末窗 gap 恒 0,零漂移)。

    命中后层2 后置步丢弃全部 BuyCard 候选(应急态亦不豁免——
    W105 指认的「低血→应急强制买」反因正是本纪律的对象;[13] 板面
    已成的处置梯度=deploy 优化+refresh 搜牌,不需要继续囤件);
    levelup([12]/[33] 人口位例外)/refresh(保血通道)/卖/合装不辖。
    """
    if not registry.formed_stop_enabled:
        return False
    if state.plane != 1:
        return False
    min_round = registry.formed_stop_min_round
    ist = getattr(session, 'v3_intention', None)
    if isinstance(ist, IntentionState) and ist.phase == 'locked':
        from sr_od.application.currency_war.kernel.cw_comps import get_comp
        comp = get_comp(ist.locked_comp)
        if comp is not None and comp.typical_form_round:
            min_round = max(comp.typical_form_round,
                            registry.formed_stop_min_round)
    if state.round_num < min_round:
        return False
    # W227/ADR-0400 承接维:缺口在 form_ok 之前算(观测字段无论成型
    # 与否都写——sim 账本 handoff_gap 的数据源);非末窗恒 0,
    # P1 非末窗零漂移(ADR-0411 起承接门无条件启用)。
    from sr_od.application.currency_war.decision.decision_v2.handoff import (
        handoff_gate_gap,
    )
    gap = handoff_gate_gap(state, session, registry)
    session.v3_handoff_gap = gap
    from sr_od.application.currency_war.decision.decision_v2.phase import form_ok
    if not form_ok(state, session, registry):
        return False
    if gap > 0:
        # 末窗承接未达标:不停手继续投资(设计件 08 §4.2 Phase 1
        # 挂载点 a;[18] 位面末最后一战是损失最小 ALL IN 时机的承接
        # 扩展——低血/全1★板带差资产进 P2,存金无意义,换板面战力)
        log.info('[cw][d2] 承接门:r%d 承接缺口 %d(总档位<%d),'
                 '不停手继续投资(ADR-0400)',
                 state.round_num, gap, registry.handoff_gate_tier_target)
        return False
    return True


# (配方围栏辖域谓词 recipe_fence_active 已随形态达标方向一开关族删除
#  ——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3;证据链留档 ADR-0432。)


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

    应急 > 模式(追赶态已随 W126/ADR-0349 退场);上级命中即返回,
    下级不再参与。
    """
    if is_emergency(state, registry):
        # ADR-0302/0303:应急集=registry.emergency_tags(已含卖弱件
        # for_gold+升级 levelup)。危机囤金态(金≥crisis_hoard_gold)
        # 额外放行 refresh——金在手而店无战力件时搜牌补板是唯一变现
        # 通道([17]「>50 的每一分都没有存的意义,该D牌D牌」);
        # 金<crisis_hoard_gold 的应急态 refresh 仍滤出(应急集收窄不变)。
        # 评分侧:危机 D 与常态同走 V_D 批口径金账(W126/ADR-0349
        # E7 应急 D 变现 EV 化——同一本账,不是另一个门;本解锁只管
        # 候选在场,放行由 V_D>0 决定)
        allowed = registry.emergency_tags
        if crisis_hoard_active(state, registry):
            allowed = allowed | frozenset({'refresh'})
        return allowed, frozenset()
    if current_mode(session) == 'economy':
        return registry.economy_tags, frozenset()
    return registry.war_tags, frozenset()


def filter_candidates(cands: list[Candidate], state: GameState,
                      session: StrategySession,
                      registry: DecisionV2Registry,
                      ) -> tuple[list[Candidate], list[dict]]:
    """层2 入口:按覆盖态过滤候选集;返回 (存活候选, 链日志)。

    链日志=判读可直接读的过滤记录(哪级命中、每个候选去留)。
    成型停手(ADR-0343;W255/ADR-0410 目标件白名单)为**覆盖态之后的
    动作级后置步**:五项判定(见 formed_stop_active)命中时丢弃
    BuyCard 候选——**目标件白名单例外**(_formed_stop_buy_allowed:
    [13] 停过渡件不停目标件,[21]/[22]);标志写 session.v3_formed_stop
    供遥测行/检查器豁免消费(单次调用=单轮决策,策略主循环唯一入口);
    白名单放行的链日志行带 'formed_stop_exempt'=True。

    (C1 溢余必花定向收窄臂、配方围栏第二遍后置步(方向一)与散装板
    硬门(tier_push gate)已随各自开关族删除——旧方案清退批,清查
    报告 OLD_MIX_AUDIT §1.3;C1 资产臂定谳清理见 ADR-0444。)
    """
    allowed, forbidden = _allowed_tags(state, session, registry)
    level = ('emergency' if is_emergency(state, registry)
             else 'mode')   # 追赶态已退场(W126/ADR-0349)
    formed_stop = formed_stop_active(state, session, registry)
    session.v3_formed_stop = formed_stop
    kept: list[Candidate] = []
    log: list[dict] = []
    for c in cands:
        ok = c.tag in allowed and c.tag not in forbidden
        fs_drop = False   # 本行是否被成型停手拦(W255:仅白名单外买)
        if ok and formed_stop and isinstance(c.action, BuyCard):
            if not _formed_stop_buy_allowed(c.action.card.name,
                                            state, session):
                ok = False   # [13] 停过渡件(白名单外);W255/ADR-0410
                fs_drop = True
            # 白名单内:目标件照买照囤([21]/[22],放行=行为不变量)
        entry = {'tag': c.tag, 'kept': ok, 'level': level,
                 'formed_stop': fs_drop,
                 **({'formed_stop_exempt': True}
                    if (formed_stop and isinstance(c.action, BuyCard)
                        and not fs_drop and c.tag in allowed
                        and c.tag not in forbidden) else {})}
        log.append(entry)
        if ok:
            kept.append(c)
    return kept, log
