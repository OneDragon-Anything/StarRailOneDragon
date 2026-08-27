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
from sr_od.application.currency_war.cw_intention import (
    IntentionState,
)
from sr_od.application.currency_war.cw_line_switch import node_loss_kind
from sr_od.application.currency_war.cw_state import (
    BuyCard,
    GameState,
    LevelUp,
    RefreshShop,
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.candidates import Candidate
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
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
    from sr_od.application.currency_war.decision_v2.candidates import (
        _target_names,
    )
    return name in _target_names(state, session)


def is_emergency(state: GameState,
                 registry: DecisionV2Registry) -> bool:
    """应急触发(绝对 HP 档简版;redesign §5.4 Phase A 口径)。"""
    return state.hp <= registry.emergency_hp


def _next_battle_loss(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> float:
    """下一战期望损血(粗档查表;registry.dying_band_next_loss 单一源)。

    节点型映射单一源=``cw_line_switch.node_loss_kind``(boss/遭遇→同名
    档,奖励/补给→零损档,其余含缺读→normal 档——normal 为战斗节点
    频率最高档,触发宽度居中非最窄,方向声明见 registry 字段注释)。
    """
    node = getattr(session, 'node_type_current', None) or state.node_type or ''
    kind = node_loss_kind(node)
    return registry.dying_band_next_loss.get(kind, 0.0)


def _deploy_free(state: GameState) -> int:
    """当前可上阵空位数 = max(0, max_units − 上场占用)(ADR-0392 占用
    口径,与部署候选判据 deployed_occupied 同源)。"""
    from sr_od.application.currency_war.cw_state import deployed_occupied
    return max(0, state.max_units()
               - deployed_occupied(state.deployed or []))


def _refreshable_names(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> frozenset[str]:
    """R2 定向刷新存在性判据的名集(评分先验,非授权边界)。

    =目标件名集(``candidates._target_names``:意向载体目标∪体系卡引擎
    件)∪ 高费强件(费用 ≥ registry.dying_band_high_cost_floor 的注册表
    角色)。滤网只判「店内有无可买+上的名集件」这一存在性,买谁由 EV
    层定价——名单从授权边界降为评分先验(对抗审计 A1-β 修法,报告=
    `.debug/temp/currency_war/w363_c3c4_attack/ATTACK.md`)。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    from sr_od.application.currency_war.decision_v2.candidates import (
        _target_names,
    )
    names = set(_target_names(state, session))
    names |= {n for n, ch in CHARACTERS.items()
              if (getattr(ch, 'cost', 0) or 0)
              >= registry.dying_band_high_cost_floor}
    return frozenset(names)


def dying_band_active(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> bool:
    """濒死带:应急深带内「再输一场即死」的帧(纯收窄,只删不增,设计=
    `.debug/temp/currency_war/w373_c3c4_redesign/REDESIGN.md` §2)。

    四条件缺一不可:
    1. registry.dying_band_account_enabled(默认关=现行为零漂移,A/B 臂);
    2. ``state.hp_readable``(置信 0 帧 hp 是沿用值,假帧不评估——与
       posture_release.flip_hit 同款守卫);
    3. ``is_emergency``(触发线 emergency_hp 不动,本判据嵌套于应急深带
       内,不新增覆盖态触发线);
    4. hp ≤ 下一战期望损血(粗档查表)——「再输一场即死」帧。

    支出收窄的语义(REDESIGN §2.3 推导链):删除判据 = Δp_board(s) ≤ 0
    (本轮采纳支出 s 后、下一战开打前可完成的「上场位增加数」为 0)——
    板面不变则胜率不变,删除集支出满足对任意 V_continue≥0 期望为负,
    是可证明零期望的符号判定,不是「保守上界」;Δp_board>0 的支出交给
    既有 EV 层定价。逐动作判定见 filter_candidates 濒死段。辖域
    plane≥2(P2 生存批);与 release FLIP 辖区(hp>emergency_hp)零
    交集——濒死帧恒不在 release 辖区。
    """
    if not registry.dying_band_account_enabled:
        return False
    if state.plane < 2 or not state.hp_readable:
        return False
    if not is_emergency(state, registry):
        return False
    return state.hp <= _next_battle_loss(state, session, registry)


def c1_directed_active(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> bool:
    """C1 溢余必花定向辖域(P1 末窗投影安全带;FLIP 正交补集)。

    设计=唯一规格:`.debug/temp/currency_war/w382_c1_design/DESIGN.md`
    §2/§3(路线 B);总开关 registry.c1_directed_spend_enabled(默认关
    =零漂移锚)。五条件缺一不可:

    1. 开关开;
    2. hp 可信位(hp_readable or hp_trusted,与 posture_release.flip_hit
       同款守卫——兜底 100 帧不评估;shop 开态沿用真值帧放行,ADR-0428);
    3. P1(本通道批辖域;末窗投影语义的 boss 税锚为 P1 语料标定);
    4. 末窗=posture_release.boss_first_buy_phase(经 discipline.
       boss_window_active 统一口径)——**不重算末窗谓词**(ADR-0426
       死分支教训:下游消费必须挂活判定单一源);
    5. 投影安全带 d=hp−boss_tax_p75 ≥ emergency_hp ∧ 溢余段
       g>interest_floor——与 FLIP 末窗投影臂(d<emergency_hp)按 d
       一刀切互斥(辖域正交,非合并;d≥emergency_hp 时 hp≥59,应急态
       结构性不可达,无重叠面)。

    溢余段花金零息损(P11,成本恒 0),定向语义的期望账方向=只保留
    对 boss 战胜率有增量的支出(Δp≤0 支出确定性零收益);逐动作判定
    见 filter_candidates 的 C1 段(与濒死带同款 Δp_board 符号谓词)。
    破息分支(g≤50 跨档)不在本辖域——过账判据存档于 registry 注释,
    待 E[R̄] 标定后评估。
    """
    if not registry.c1_directed_spend_enabled:
        return False
    if not (state.hp_readable or state.hp_trusted):
        return False
    if state.plane != 1:
        return False
    if (state.hp - registry.boss_tax_p75) < registry.emergency_hp:
        return False    # d<25 投影必入应急带:FLIP 末窗投影臂辖区,C1 让位
    if (state.gold or 0) <= registry.interest_floor:
        return False    # 只辖溢余段(必花语义的成本恒 0 前提,P11)
    from sr_od.application.currency_war.decision_v2.posture_release import (
        boss_first_buy_phase,
    )
    return boss_first_buy_phase(state, session, registry)


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
        from sr_od.application.currency_war.cw_comps import get_comp
        comp = get_comp(ist.locked_comp)
        if comp is not None and comp.typical_form_round:
            min_round = max(comp.typical_form_round,
                            registry.formed_stop_min_round)
    if state.round_num < min_round:
        return False
    # W227/ADR-0400 承接维:缺口在 form_ok 之前算(观测字段无论成型
    # 与否都写——sim 账本 handoff_gap 的数据源);非末窗恒 0,
    # P1 非末窗零漂移(ADR-0411 起承接门无条件启用)。
    from sr_od.application.currency_war.decision_v2.handoff import (
        handoff_gate_gap,
    )
    gap = handoff_gate_gap(state, session, registry)
    session.v3_handoff_gap = gap
    from sr_od.application.currency_war.decision_v2.phase import form_ok
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

    濒死带支出收窄(设计=`.debug/temp/currency_war/w373_c3c4_redesign/
    REDESIGN.md` §2,registry.dying_band_account_enabled):濒死帧
    (dying_band_active)命中时按 Δp_board(本轮支出后、下一战开打前
    的上场位增加数)做符号判定——BuyCard:有空位(free≥1)或 3合1 即时
    合成(bench 对子买店同名牌升星上场,同 C1 侧判据)放行,其余无空位
    买删(原因 'hoard_buy',本轮不可能上场的纯 hoard 买,含
    final 目标件「买而不上」——濒死帧来不及按 [21] 兑现,设计内意图);
    LevelUp:bench 有可上件且空位不足时升完立刻多上 1 件放行,否则删
    (原因 'levelup_no_deploy'——可部署性谓词,不是动作类型黑名单,
    ADR-0302/0303 滤死升级反模式的结构性防复发);RefreshShop:店内有
    可买+上的名集件(目标∪高费强件,名单在此只作评分先验)放行定向
    刷新,否则删(原因 'blind_refresh');卖(变现)/部署非支出,不辖。
    链日志行带 'dying_band' 原因。默认关=逐位一致(零漂移)。

    C1 溢余必花定向收窄(registry.c1_directed_spend_enabled,默认关
    =零漂移;辖域=c1_directed_active,P1 末窗投影安全带 d≥emergency_hp
    ∧ 溢余段,与 FLIP/濒死带辖区零交集):命中间内对支出候选做与濒死带
    同款 Δp_board 符号判定(溢余段花金成本恒 0,只删对 boss 战胜率
    零增量的支出)——BuyCard:有空位可上或 3合1 即时合成(合成后上场
    星级即涨,本窗战力增量)放行,纯 hoard 买删(原因 'c1_hoard_buy');
    RefreshShop:店内有可买+上的名集件放行定向刷新,否则删(原因
    'c1_blind_refresh');LevelUp:升完立刻多上 1 件放行,否则删(原因
    'c1_levelup_no_deploy');卖/部署非支出不辖。链日志行带 'c1_directed'
    原因。贡献候选间的相对排序仍由 EV 评分层单一裁决,本通道不改分。
    """
    allowed, forbidden = _allowed_tags(state, session, registry)
    level = ('emergency' if is_emergency(state, registry)
             else 'mode')   # 追赶态已退场(W126/ADR-0349)
    formed_stop = formed_stop_active(state, session, registry)
    session.v3_formed_stop = formed_stop
    dying = dying_band_active(state, session, registry)
    c1 = c1_directed_active(state, session, registry)
    refreshable = frozenset()
    if dying or c1:
        # 濒死带/C1 两辖区的定向刷新存在性名集(同款判据复用;两辖区按
        # hp 结构互斥——濒死帧 hp≤25 恒不在 C1 辖区 hp≥59,不会同帧双评估)
        refreshable = _refreshable_names(state, session, registry)
    shop_has_play = (dying or c1) and _deploy_free(state) >= 1 and any(
        c.name in refreshable for c in (state.shop or []))
    bench_n = 0
    if dying or c1:
        from sr_od.application.currency_war.cw_state import bench_occupied
        bench_n = bench_occupied(state.bench or [])
    kept: list[Candidate] = []
    log: list[dict] = []
    for c in cands:
        ok = c.tag in allowed and c.tag not in forbidden
        fs_drop = False   # 本行是否被成型停手拦(W255:仅白名单外买)
        db_drop = ''   # 本行是否被濒死带收窄拦(Δp_board 符号判定)
        c1_drop = ''   # 本行是否被 C1 定向收窄拦(同款符号判定)
        if ok and formed_stop and isinstance(c.action, BuyCard):
            if not _formed_stop_buy_allowed(c.action.card.name,
                                            state, session):
                ok = False   # [13] 停过渡件(白名单外);W255/ADR-0410
                fs_drop = True
            # 白名单内:目标件照买照囤([21]/[22],放行=行为不变量)
        if ok and dying:
            if isinstance(c.action, BuyCard):
                # Δp_board = 1 if free≥1 或 3合1 即时合成 else 0(买后
                # 即可部署,部署由既有 deploy 候选免费完成;bench 对子
                # 买店同名牌即时合成 2★ 上场,可部署性同 C1 侧判据)
                if _deploy_free(state) < 1 and not c.merge:
                    ok = False
                    db_drop = 'hoard_buy'
            elif isinstance(c.action, RefreshShop):
                # Δp_board = 1 if ∃店牌可本轮买+上 else 0(存在性判据)
                if not shop_has_play:
                    ok = False
                    db_drop = 'blind_refresh'
            elif isinstance(c.action, LevelUp):
                # Δp_board = min(bench_n, free+1) − min(bench_n, free)
                # = 1 iff bench_n≥1 且 free<bench_n(升完立刻多上 1 件)
                if not (bench_n >= 1 and _deploy_free(state) < bench_n):
                    ok = False
                    db_drop = 'levelup_no_deploy'
        if ok and c1:
            # C1 定向收窄(与濒死带同款 Δp_board 符号判定,辖域不同):
            # 溢余段花金成本恒 0(P11),只删对 boss 战胜率零增量的支出
            if isinstance(c.action, BuyCard):
                # Δp_board = 1 if free≥1 或 3合1 即时合成 else 0
                # (合成候选买入即升星上场,本窗战力增量)
                if _deploy_free(state) < 1 and not c.merge:
                    ok = False
                    c1_drop = 'c1_hoard_buy'
            elif isinstance(c.action, RefreshShop):
                # Δp_board = 1 if ∃店牌可本轮买+上 else 0(存在性判据)
                if not shop_has_play:
                    ok = False
                    c1_drop = 'c1_blind_refresh'
            elif isinstance(c.action, LevelUp):
                # Δp_board = 1 iff 升完立刻多上 1 件(同濒死带公式)
                if not (bench_n >= 1 and _deploy_free(state) < bench_n):
                    ok = False
                    c1_drop = 'c1_levelup_no_deploy'
        entry = {'tag': c.tag, 'kept': ok, 'level': level,
                 'formed_stop': fs_drop,
                 **({'formed_stop_exempt': True}
                    if (formed_stop and isinstance(c.action, BuyCard)
                        and not fs_drop and c.tag in allowed
                        and c.tag not in forbidden) else {})}
        if db_drop:
            entry['dying_band'] = db_drop
        if c1_drop:
            entry['c1_directed'] = c1_drop
        log.append(entry)
        if ok:
            kept.append(c)
    return kept, log
