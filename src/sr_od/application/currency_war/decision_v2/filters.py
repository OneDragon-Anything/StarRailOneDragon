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


def _deploy_free(state: GameState) -> int:
    """当前可上阵空位数 = max(0, max_units − 上场占用)(ADR-0392 占用
    口径,与部署候选判据 deployed_occupied 同源)。"""
    from sr_od.application.currency_war.cw_state import deployed_occupied
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
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    from sr_od.application.currency_war.decision_v2.candidates import (
        _target_names,
    )
    names = set(_target_names(state, session))
    names |= {n for n, ch in CHARACTERS.items()
              if (getattr(ch, 'cost', 0) or 0)
              >= registry.directed_refresh_high_cost_floor}
    return frozenset(names)


def c1_directed_active(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> bool:
    """C1 溢余必花定向辖域(P1 末窗投影安全带;FLIP 正交补集)。

    设计=唯一规格:`.debug/temp/currency_war/w382_c1_design/DESIGN.md`
    §2/§3(路线 B);总开关 registry.c1_directed_spend_enabled(默认关
    =零漂移锚)。五条件缺一不可:

    1. 开关开;
    2. hp 决策可信位(posture_release.hp_decision_trusted 单一源,与
       posture_release.flip_hit 同款守卫——兜底 100 帧不评估;shop 开态
       沿用真值帧放行,ADR-0428);
    3. P1(本通道批辖域;末窗投影语义的 boss 税锚为 P1 语料标定);
    4. 末窗=posture_release.boss_first_buy_phase(经 discipline.
       boss_window_active 统一口径)——**不重算末窗谓词**(ADR-0426
       死分支教训:下游消费必须挂活判定单一源);
    5. 投影安全带 d=hp−boss_tax_p75 ≥ emergency_hp ∧ 溢余段
       g>interest_floor——与 FLIP 末窗投影臂(d<emergency_hp)按 d
       一刀切互斥(辖域正交,非合并;d≥emergency_hp 时 hp≥59,应急态
       结构性不可达,无重叠面)。

    溢余段花金零息损(P11,成本恒 0),定向语义的期望账方向=只保留
    对 boss 战胜率有增量的支出;逐动作判定见 filter_candidates 的 C1 段。
    判据性质(``w382_c1_design`` DESIGN §2 同款推导,资产臂通道已定谳
    清理见 ADR-0444):默认配置下为
    Δp_board 符号谓词(可证明零期望,W373 推导链在本辖域成立;同款判据
    的首用方 C3 濒死带已定谳清理,否决与清理裁决见 ADR-0426 增补节,
    C1 辖域内推导链独立成立不受其否决波及)。
    破息分支(g≤50 跨档)不在本辖域——概念已定谳否决,永不实现
    (定谳判据与证据链=ADR-0443;registry 留定谳注记)。
    """
    if not registry.c1_directed_spend_enabled:
        return False
    from sr_od.application.currency_war.decision_v2.posture_release import (
        boss_first_buy_phase,
        hp_decision_trusted,
    )
    if not hp_decision_trusted(state):
        return False
    if state.plane != 1:
        return False
    if (state.hp
            - registry.boss_tax_p75_by_plane[state.plane]) \
            < registry.emergency_hp:
        return False    # d<25 投影必入应急带:FLIP 末窗投影臂辖区,C1 让位
    if (state.gold or 0) <= registry.interest_floor:
        return False    # 只辖溢余段(必花语义的成本恒 0 前提,P11)
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


def recipe_fence_active(state: GameState, session: StrategySession,
                        registry: DecisionV2Registry) -> bool:
    """配方围栏辖域(方向一「购买围栏硬排序」;设计单一源=
    ``.debug/temp/currency_war/w415_form_design/DESIGN.md`` §1,决策
    why=ADR-0432;开臂判据挂账见 registry.recipe_fence_enabled 注释)。

    三条件缺一不可:
    1. 开关 ``registry.recipe_fence_enabled``(默认关=零漂移锚);
    2. P1(形态达标是 [13]/[28] 的位面 1 语义);
    3. ``form_ok`` 为假(decision_v2.phase 单一源)——成型后由 ADR-0343
       成型停手接手,散件自然不买,本围栏自动退出,零重叠(两谓词以
       form_ok 真假互斥,不存在同帧双辖)。

    动作级规则在 ``filter_candidates``(同轮存在性围栏:存在配方件
    买候选时删全部散件买候选,删因 'recipe_fence_scatter');与 C1 的
    正交声明(时窗不相交,C1 先行)见 filter_candidates docstring。
    """
    if not registry.recipe_fence_enabled:
        return False
    if state.plane != 1:
        return False
    from sr_od.application.currency_war.decision_v2.phase import form_ok
    return not form_ok(state, session, registry)


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

    C1 溢余必花定向收窄(registry.c1_directed_spend_enabled,默认关
    =零漂移;辖域=c1_directed_active,P1 末窗投影安全带 d≥emergency_hp
    ∧ 溢余段,与 FLIP 辖区零交集):命中间内对支出候选做 Δp_board 符号
    判定(本轮支出后、下一战开打前的上场位增加数;溢余段花金成本恒 0,
    只删对 boss 战胜率零增量的支出)——BuyCard:有空位可上或 3合1 即时
    合成且合成后可上(完备式=c.merge ∧ _deploy_free_after_merge≥1:
    「会发生合成」不等于「Δp≥1」,板满+合成 2★ 落 bench 无位可上仍删)
    放行,纯 hoard 买删(原因 'c1_hoard_buy');
    RefreshShop:店内有可买+上的名集件放行定向刷新,否则删(原因
    'c1_blind_refresh');LevelUp:升完立刻多上 1 件放行,否则删(原因
    'c1_levelup_no_deploy');卖/部署非支出不辖。链日志行带 'c1_directed'
    原因。贡献候选间的相对排序仍由 EV 评分层单一裁决,本通道不改分。

    (C1 资产臂/跨位面资产通道 V_asset 已定谳清理,删码留档:
    开臂前置触发面实测为零——C1 辖域帧上意向从不处于锁线态,m 表结构性
    无定义,通道构造性恒不激活;决策 why=ADR-0444。)

    配方围栏(方向一,registry.recipe_fence_enabled 默认关=零漂移;
    辖域=recipe_fence_active,P1 ∧ form_ok 为假;ADR-0432):成型停手/
    C1 之后的**第二遍动作级后置步**——同轮 survivors 中存在配方件
    (scoring._cand_system_bonds 名集单一源)买候选时,删除全部非配方件
    (散件)买候选,删因 'recipe_fence_scatter'(链日志行
    entry['recipe_fence'])。与 C1 正交声明(DESIGN §1.4):时窗不相交
    ——C1 只辖 P1 末窗溢余段,本围栏辖 P1 全程未成型段;都开时 C1 先行
    (上级覆盖态语义,主循环内先评),C1 未删的候选再过本围栏;两开关
    默认值独立,互不为开臂前提;删因链日志分列(c1_directed 与
    recipe_fence 独立字段),A/B 分通道记账互不污染。与成型停手零重叠
    (form_ok 真假互斥)。金账/息账单一源不动,只重排同一笔预算内买谁。
    """
    allowed, forbidden = _allowed_tags(state, session, registry)
    level = ('emergency' if is_emergency(state, registry)
             else 'mode')   # 追赶态已退场(W126/ADR-0349)
    formed_stop = formed_stop_active(state, session, registry)
    session.v3_formed_stop = formed_stop
    # 配方围栏帧级预处理(方向一;与成型停手以 form_ok 真假互斥,同帧
    # 至多其一;动作级规则在主循环后的第二遍后置步)
    fence = recipe_fence_active(state, session, registry)
    c1 = c1_directed_active(state, session, registry)
    refreshable = frozenset()
    if c1:
        # C1 辖区的定向刷新存在性名集(存在性判据的评分先验)
        refreshable = _refreshable_names(state, session, registry)
    shop_has_play = c1 and _deploy_free(state) >= 1 and any(
        c.name in refreshable for c in (state.shop or []))
    bench_n = 0
    if c1:
        from sr_od.application.currency_war.cw_state import bench_occupied
        bench_n = bench_occupied(state.bench or [])
    kept: list[Candidate] = []
    kept_pos: list[int] = []   # [索引定义] kept[i] 的链日志下标(log 容器
    #             0 起;与 kept 同轮同序生成,取值时机=主循环内同步追加)
    log: list[dict] = []
    for c in cands:
        ok = c.tag in allowed and c.tag not in forbidden
        fs_drop = False   # 本行是否被成型停手拦(W255:仅白名单外买)
        c1_drop = ''   # 本行是否被 C1 定向收窄拦(Δp_board 符号判定)
        if ok and formed_stop and isinstance(c.action, BuyCard):
            if not _formed_stop_buy_allowed(c.action.card.name,
                                            state, session):
                ok = False   # [13] 停过渡件(白名单外);W255/ADR-0410
                fs_drop = True
            # 白名单内:目标件照买照囤([21]/[22],放行=行为不变量)
        if ok and c1:
            # C1 定向收窄(Δp_board 符号判定):
            # 溢余段花金成本恒 0(P11),只删对 boss 战胜率零增量的支出。
            if isinstance(c.action, BuyCard):
                # Δp_board = 1 if free≥1 或(3合1 即时合成 ∧ 合成后可上)
                # else 0(合成豁免取完备式:板满+合成落 bench 无位可上
                # 时 Δp_board=0)
                if _deploy_free(state) < 1 and not (
                        c.merge
                        and _deploy_free_after_merge(c, state) >= 1):
                    ok = False
                    c1_drop = 'c1_hoard_buy'
            elif isinstance(c.action, RefreshShop):
                # Δp_board = 1 if ∃店牌可本轮买+上 else 0(存在性判据)
                if not shop_has_play:
                    ok = False
                    c1_drop = 'c1_blind_refresh'
            elif isinstance(c.action, LevelUp):
                # Δp_board = 1 iff 升完立刻多上 1 件(bench_n≥1 且
                # free<bench_n)
                if not (bench_n >= 1 and _deploy_free(state) < bench_n):
                    ok = False
                    c1_drop = 'c1_levelup_no_deploy'
        entry = {'tag': c.tag, 'kept': ok, 'level': level,
                 'formed_stop': fs_drop,
                 **({'formed_stop_exempt': True}
                    if (formed_stop and isinstance(c.action, BuyCard)
                        and not fs_drop and c.tag in allowed
                        and c.tag not in forbidden) else {})}
        if c1_drop:
            entry['c1_directed'] = c1_drop
        log.append(entry)
        if ok:
            kept.append(c)
            kept_pos.append(len(log) - 1)
    if fence and kept:
        # 配方围栏第二遍后置步(方向一,ADR-0432):同轮存在性围栏——
        # 过滤链 survivors 中存在配方件买候选(scoring._cand_system_bonds
        # 名集单一源)时,删除全部非配方件(散件)买候选。存在性按
        # survivors 计:C1/成型停手已删的候选不计(删无可买=空转面);
        # 成型停手与本围栏以 form_ok 真假互斥,实际前序只有 C1。
        # 店为空配方件时散件照旧(空窗期语义 [31]);只重排同一笔预算内
        # 「买谁」,配方件之间的相对序仍归 EV 层单一裁决。
        from sr_od.application.currency_war.decision_v2.scoring import (
            _cand_system_bonds,
        )
        has_recipe = any(
            isinstance(c2.action, BuyCard) and _cand_system_bonds(c2)
            for c2 in kept)
        if has_recipe:
            still: list[Candidate] = []
            for i, c2 in enumerate(kept):
                if (isinstance(c2.action, BuyCard)
                        and not _cand_system_bonds(c2)):
                    entry = log[kept_pos[i]]
                    entry['kept'] = False
                    entry['recipe_fence'] = 'recipe_fence_scatter'
                else:
                    still.append(c2)
            kept = still
    return kept, log
