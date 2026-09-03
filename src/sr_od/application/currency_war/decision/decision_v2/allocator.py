"""死亡窗支出分配器(W684 v6 正式模型落码;设计单一源 =
``.debug/temp/currency_war/w684_p1_v3_design/DESIGN.md`` v6 §2-§3,
数学基础 = ``docs/game/currency_war/research/proofs/p23-death-window-
allocation-ev.md``(P23.1/P23.2 停手窗域 + P23.3/P23.4 死亡域),
终审瑕疵清单 = ``.debug/temp/currency_war/w706_allocator_attack_final/
REPORT.md`` §8 六条——本模块逐条落点见各符号 docstring 的 §8-N 标注)。

正式模型:辖域帧 t 上分配问题 ``P_t = ⟨Π_t, R_t, O, D⟩``:

- **Π_t 提案集**(结构化,非扁平列表):每提案供三元组
  ``(Δp_eff, m_eff, c)``——每场金当量增量/视界(场)/当帧边际金流出;
  不供三元组的量不进模型(W706 §8-1 定义补全:Δp_eff := 每场金当量
  增量 Δp·L_c + w,**不是**裸胜率增量——量纲闭合由本定义式保证)。
  交互边集:①破坏边 refresh→buy(选中 refresh 终结本轮分配,后继
  店态重derive——帧内不与买共存);②前置边 buy→lu(生成期闭合为
  Π_comp 复合提案,复合账不可拆选);③实体争用边(bench/deploy/copies
  cap → R_t 可行性约束)。
- **R_t 资源约束**:整数金 E_t = max(0, gold − reserve)(W635-F1
  储备消费不改写,§5 不动面);bench 槽位;copies_cap;刷新单提案粒度
  (当帧一次 RefreshShop,禁整条计划入键)。
- **O 目标函数**(分域出清算子,§4-P5):
      V(π) = m_eff(π) × Δp_eff(π) − 机会成本项
  停手窗域机会成本 = c + I(W690 账,I=破息损,ev.interest_cost 单一源);
  死亡域机会成本 = c + I(面值;ADR-0493 重标定——原 P23.4(ii) 的
  S0×(c+I) 折价前提「金必死」被 W810 死亡域审查反事实实测证伪:
  死亡域帧携金进 P2 三局 3/3 到达可支出语境、1 局转 +2 轮存活,
  金的真实边际价值=带金存活增益,不支持任何折扣系数 → S0 加权
  退役,金按面值计;S0 本体仍辖 discipline.terminal_release 谓词,
  不在本层改动)。
  出清:V ≤ 0 的提案出局。
- **D 辖域**(稳态断言,§0 核实降级):辖域谓词(former_stop ∨
  terminal_release)**现值直用,无迟滞**——W703 攻击 4 的振荡前提已被
  门感知滞回闩(kernel/cw_intention)结构性砍断;残余通路由锁面断言
  核验(test_cw_w715 稳态断言锁),不为死场景设计机制。

三渠道臂=向 Π_t 供给提案的具体化(§3):升级臂(P21 硬停域不生成
提案,先于模型)/买卡臂(过滤层后置救回:deployed 同名副本死库存
完备式)/刷新臂(当帧一次粒度;停付豁免域 ALL IN/应急带直通不进
Π_refresh——豁免域保血语义不经 O 裁)。

零新常数铁律(§8):本模块全部数值 = 既有单一源符号
(registry.vd_p1_loss_*/vd_p2_loss/h3_win_rate/hp_to_gold/battles_left_est/
interest_recovery_rounds/copies_cap/bench_capacity、cw_economy.
STREAK_GOLD_TABLE、cw_state.XP_TO_NEXT_LEVEL、cw_shop_odds.refresh_prob);
弱标定带 [−97,+19] 与 Δp 带 [0.03,0.117] **不进任何决策分支**,
只作为 ``ALLOC_PARAM_SET`` 数据结构的登记字段承载(P23.2 复判条款
的机制化,W690 §4-4)。

分包期 5 移动注记:当前物理布局 = decision_v2/ 桶;期 5 桶归位时
本文件随 decision 桶整体迁移(机械移动,无语义变更)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from sr_od.application.currency_war.decision.cw_strategy import StrategySession
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    Action,
    BuyCard,
    GameState,
    LevelUp,
    RefreshShop,
)

#: 分配器总开关(W684 v6 终审定稿实施批;策略开关生命周期第 3 态=
#: 开臂——本批随 sim 绝对指标验证通过落默认开,验证记录见
#: .debug/temp/currency_war/w715_allocator_impl/REPORT.md)。关=零漂移锚
#: (行为回退到既有四层管线)。
ALLOCATOR_ENABLED: bool = True

#: W690 参数集版本(承 P23.2 复判条款/W690 §4-4:参数集版本变更必须
#: 伴随 Δp 标定来源登记——``ALLOC_PARAM_SET.recheck`` 字段;版本化
#: 复判的机制化载体,复判登记锁消费)。ADR-0493 死亡域机会成本
#: 重标定随版本升 P23.4R;W956 死亡域刷新估计器保底(w)与 w-only
#: 拒供退役随版本升 P23.5R。
ALLOC_PARAM_SET_VERSION: str = 'P23.5R'


@dataclass(frozen=True)
class AllocParamSet:
    """W690 两域门参数集(版本化;数据结构承载复判条款,§4-P5)。

    ``delta_p_band``/``ev_band`` 是 P23.2 的**弱标定带登记**(如实分级
    纪律):它们只作复判对照数据,**禁进任何决策分支**——决策只消费
    三元组与 O 出清式,不消费带端点。版本变更纪律:改任何字段必须
    同步更新 ``version`` 与 ``recheck``(标定来源登记),复判登记锁
    (test_cw_w715)锁此契约。
    """

    version: str
    #: Δp 单人口胜率边际弱标定带(无量纲;P23 符号表单一源 = W690 §3)
    delta_p_band: tuple[float, float]
    #: 停手窗大额升级 EV 弱标定带(金/笔;P23.2,[−97,+19] 不固化)
    ev_band: tuple[float, float]
    #: 复判条款登记(重开条件+标定来源;版本变更必须更新)
    recheck: str


#: 唯一实例(模块级单例;P23.4R = ADR-0493 死亡域机会成本重标定批)。
ALLOC_PARAM_SET = AllocParamSet(
    version=ALLOC_PARAM_SET_VERSION,
    delta_p_band=(0.03, 0.117),
    ev_band=(-97.0, 19.0),
    recheck=('Δp 单人口边际实采(sim 放开 LEVEL_CAP 臂同池 A/B 反推)返回 '
             '≥0.35 时 P23.2 重开;死亡域机会成本折价系数标定来源='
             'W810 死亡域审查反事实三局对拍(携金进 P2 三局 3/3 到达可'
             '支出语境、1 局转 +2 轮存活/出口 hp +4,「金必死」前提实测'
             '证伪 → 现按面值计,系数=1;实测出「带金存活增益<面值」的'
             '分布证据时可重开下调);P23.5R 变更登记=W956 治本设计'
             '(.debug/temp/currency_war/w956_death_allocator/DESIGN.md)'
             '死亡域刷新估计器结构零保底取 w + w-only 拒供退役'
             '(E1=P23.4(i) 推论可证,A′ 非应急子带编排者指令直落;'
             'W810 缺陷②的「金免费伪影」顾虑由面值机会成本 c+I 与'
             'm_eff 视界截断共同兜底);标定来源=proofs/p23 符号表'
             '(W690 §3);弱标定带不固化,复判=参数集版本变更+来源登记'),
)


class AllocDomain(StrEnum):
    """分配器两域(O 的参数集选择键,§4-P5)。"""

    STOP_WINDOW = 'stop_window'   # 停手窗域:机会成本按 W690 账(c+I)
    DEATH = 'death'               # 死亡域:机会成本=S0 加权,视界截断


@dataclass
class AllocProposal:
    """Π_t 提案(三元组 + 执行体;量纲单位:金/场/金,§4-P1)。"""

    kind: str                     # 'buy' | 'levelup' | 'refresh' | 'comp'
    dpeff: float                  # Δp_eff:每场金当量增量 Δp·L_c + w(W706 §8-1)
    m_eff: float                  # 视界(场)
    cost: int                     # 当帧边际金流出 c(金)
    v: float = 0.0                # O 出清值(金;>0 放行)
    actions: tuple[Action, ...] = ()   # 执行体(comp=复合动作组,原子采纳)
    name: str = ''                # 判读用名(买件名/通道名)
    bench_slots: int = 1          # 实体边:本提案占用的 bench 槽(merge=0)
    note: dict = field(default_factory=dict)


@dataclass
class AllocResult:
    """分配器帧产物(策略接线消费 + 记账帧位披露)。"""

    active: bool = False              # 本帧是否辖域帧
    domain: str = ''                  # AllocDomain 值(辖域帧非空)
    actions: list[Action] = field(default_factory=list)
    #: 分配器帧位(记账扩展,v6 §6:辖域帧披露各渠道获配金;决策位
    #: 记账与既有单闩/tier 位同族,session 载体)
    frame: dict = field(default_factory=dict)


def alloc_domain(state: GameState, session: StrategySession,
                 registry: DecisionV2Registry) -> AllocDomain | None:
    """辖域谓词 D(现值直用,§0 核实①/§4-P3;**禁加迟滞**)。

    - 死亡域优先:``discipline.terminal_release`` 为真(Tier-2,S0≤ε
      守钱世界存活上界判据;其位面内闩是该谓词自身设计,非本层新增
      状态)→ DEATH;
    - 停手窗域:``filters.formed_stop_active`` 为真(former_stop,
      [13] 成型停手判据)→ STOP_WINDOW;
    - 都不真 → None(P_t 不被构造,常规管线全权)。

    T,T,F 振荡残余(W706 §8-4):谓词现值直用 = 2/3 帧接管、1/3 帧
    回现状,行为有界;稳态断言锁核验,断言实测违约才按预注册条件
    升级机制,本层不预置防振荡结构。
    """
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        terminal_release,
    )
    from sr_od.application.currency_war.decision.decision_v2.filters import (
        formed_stop_active,
    )
    # (兑现链 D2·跨位面入口帧转化授权臂已随 realization_chain 开关族
    #  删除——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3。)
    if terminal_release(state, session, registry):
        return AllocDomain.DEATH
    if formed_stop_active(state, session, registry):
        return AllocDomain.STOP_WINDOW
    return None


def must_die_band(state: GameState, session: StrategySession,
                  registry: DecisionV2Registry) -> bool:
    """必死子带谓词(W956 治本设计 §3.2 定档;设计单一源 =
    ``.debug/temp/currency_war/w956_death_allocator/DESIGN.md``):

        hp ≤ L_c(单场败局伤害估计,``_l_c`` 单一源)——「再败一场必死」

    是 E1 推论(P23.4(i) 极限形式:此带内 P(活过剩余战斗)≈0,金终端
    价值 ≈0,任何非负板面提案弱优于攥金)的前提带。候选判据二选一定档
    (E[bleed]≥hp 或 hp≤L_c):取 hp≤L_c——病灶帧同真(标定探针见
    w956 目录 calibration 产物),L_c 版零新常数且复用分配器既名符号。
    hp 缺读/已死(≤0)不辖(无可辩护前提)。"""
    hp = state.hp
    if hp is None or hp <= 0:
        return False
    return float(hp) <= _l_c(state, registry)


def _w_per_battle(state: GameState, session: StrategySession) -> float:
    """w(金/场):胜负金收入差 = 连胜金表的相邻档差(cw_economy.
    STREAK_GOLD_TABLE 单一源,零新常数)。

    P23.2 的 w∈[0,3] 弱带不固化——本式是「按当前连胜位的下一胜收入
    增量」的机制常量推导,不是第二份标定。streak 未知(0/缺)→ 表
    首两档差(保守侧:连胜越高 w 越大,取低端低估收益,对停手窗
    负判稳健)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import streak_gold
    s = int(getattr(session, 'last_streak', 0) or 0)
    lo = max(0, min(s, 4))
    return float(max(0, streak_gold(lo + 1) - streak_gold(lo)))


def _l_c(state: GameState, registry: DecisionV2Registry) -> float:
    """L_c(条件败局伤害,hp/场·败):P1 = scoring.p1_battle_loss_est
    (vd_p1_loss_* 拟合单一源);P2 = registry.vd_p2_loss。P23 符号表
    口径「1 hp≈1 金」在代码中经 registry.hp_to_gold 折算(单一源
    0.5;P23 证明内取 1 是 hp_to_gold=1 的特例,落码用注册表值)。"""
    from sr_od.application.currency_war.decision.decision_v2.scoring import (
        p1_battle_loss_est,
    )
    if state.plane >= 2:
        return float(registry.vd_p2_loss)
    return p1_battle_loss_est(state, registry)


def _m_horizon(state: GameState, session: StrategySession,
               registry: DecisionV2Registry) -> float:
    """兑现长(场):本位面剩余战斗 + 后续位面战斗估计。

    本位面 = ``ev.battles_left_plane``(槽序表推导单一源);后续位面
    缺表 → ``registry.battles_left_est`` 骨架缺省(保守侧,与表缺失
    兜底同源)。位面总数 3 的既有用法 = cw_intention P3 强制锁线
    (state.plane >= 3);P23 符号表 m∈[5,19] 的跨位面持久语义由此
    承载。零新常数:battles_left_est 是唯一引入的估计符号。"""
    from sr_od.application.currency_war.decision.decision_v2.ev import (
        battles_left_plane,
    )
    rest = battles_left_plane(state, session, registry)
    future = max(0, 3 - int(state.plane)) * registry.battles_left_est
    return rest + future


def _engines_now(state: GameState, registry: DecisionV2Registry) -> int:
    from sr_od.application.currency_war.decision.decision_v2.scoring import (
        _engines_formed,
    )
    return _engines_formed(state, registry)


def _win_eq(state: GameState, registry: DecisionV2Registry) -> float:
    """板面胜率当量(连续;层3 成型进度同一函数族的单源插值):

        win_eq = h3_win_rate[e] + frac × (h3_win_rate[e+1] − h3_win_rate[e])

    e = _engines_formed(整数档单一源),frac = _engine_frac_remainder
    (小数进度单一源,formation_gold_account 同源消费)。零新常数:
    只消费注册表成型档表与进度函数。"""
    from sr_od.application.currency_war.decision.decision_v2.scoring import (
        _engine_frac_remainder,
    )
    hr = registry.h3_win_rate
    e = min(2, max(0, _engines_now(state, registry)))
    frac = min(1.0, max(0.0, _engine_frac_remainder(state, registry)))
    cur = float(hr.get(e, 0.0))
    nxt = float(hr.get(min(2, e + 1), cur))
    return cur + frac * (nxt - cur)


def _apply_with_pipeline(state: GameState, actions: tuple[Action, ...],
                         session: StrategySession) -> GameState:
    """提案 apply(轻量):simulate + 部署管线(与 scoring.apply_for_score
    同一显影链——「买入→上场」的板面价值经管线可见,单一源复用)。"""
    from sr_od.application.currency_war.decision.decision_v2.scoring import (
        _deploy_pipeline,
    )
    from sr_od.application.currency_war.kernel.cw_state import simulate
    s = state
    for a in actions:
        s = simulate(s, a)
    _deploy_pipeline(s, session)
    return s


def _dpeff_from_states(state: GameState, after: GameState,
                       registry: DecisionV2Registry, w: float,
                       l_c: float) -> float:
    """每场金当量增量(W690 同式整账的逐场口径;§4-P1/W706 §8-1):

        Δp_eff = max(0, win_eq(after) − win_eq(before)) × L_c
                 × hp_to_gold + w

    Δp = 板面胜率当量增量(win_eq 单源插值,跨档与小数进度统一
    承载——跨档件吃满档差、进度件按份额,与 formation_gold_account
    的「小数进度×下一级跳变」组合计值同构)。"""
    dwin = _win_eq(after, registry) - _win_eq(state, registry)
    return max(0.0, dwin) * l_c * registry.hp_to_gold + w


def _salvage_ok(cand, state: GameState, registry: DecisionV2Registry,
                session: StrategySession) -> bool:
    """买卡臂供给修正(T 臂救回,§3):deployed 同名副本死库存完备式

        [merge=True ∧ _deploy_free_after_merge≥1]
        ∨ [bench 有空位 ∧ deploy 空位≥1]

    判据单一源 = filters._deploy_free/_deploy_free_after_merge(W703
    攻击 5.1 的救回算子)。**已知不完备声明(§4-P4,诚实不假装)**:
    救回后 Π_buy 仍限于「当视界内有上场路径」的命中面,非同名件围栏
    面不供给——外生约束,完备性声明带在报告与稳态锁,不在本层假装。"""
    from sr_od.application.currency_war.decision.decision_v2.filters import (
        _deploy_free,
        _deploy_free_after_merge,
    )
    from sr_od.application.currency_war.kernel.cw_state import bench_occupied
    a = cand.action
    if not isinstance(a, BuyCard):
        return False
    if cand.merge and _deploy_free_after_merge(cand, state) >= 1:
        return True
    return (bench_occupied(state.bench or []) < registry.bench_capacity
            and _deploy_free(state) >= 1)


def _comp_feasible(card_name: str, state: GameState,
                   registry: DecisionV2Registry) -> bool:
    """Π_comp 前置边闭合条件(§2.1 ②):店内目标件买得起(占 1 bench
    槽)∧ 买后升级能把该件送上场(该件即升级的 pop 位受益件)。

    语义 = 「先买等待件、再升级放人口」的复合:单看买(缺 deploy 位)
    或单看升(bench 无受益件)都不成立,合并后账不可拆选(§4-P2)。"""
    from sr_od.application.currency_war.decision.decision_v2.filters import (
        _deploy_free,
    )
    from sr_od.application.currency_war.kernel.cw_state import bench_occupied
    if bench_occupied(state.bench or []) >= registry.bench_capacity:
        return False
    # deploy 有空位:买后直接上场,无需升级 → 非复合
    return _deploy_free(state) < 1


def _refresh_dpeff_estimate(state: GameState, session: StrategySession,
                            registry: DecisionV2Registry,
                            domain: AllocDomain = AllocDomain.STOP_WINDOW,
                            ) -> float:
    """Π_refresh 的 Δp_eff 估计器(W706 §8-2 实现级补全;单样本代理):

        Δp_eff(refresh) = P(一刷店内出现可上场目标件)
                          × max(目标件部署的每场金当量增量)

    - P = Σ refresh_prob(level, cost)(cw_shop_odds 单一源),封顶 1;
    - 目标件部署增量 = 「买入目标件 + 部署管线」假想 apply 的
      win_eq 差(与买卡臂同一三元组供给式,口径一致)。
    **标定声明带**:单样本代理,精度未审计(设计 §8-2 预留两选项中的
    「单样本代理」);估计器语义与常量随 ALLOC_PARAM_SET 版本化,精度
    标定挂账(刷新估计器锁 test_cw_w715 锁可手算性,不锁精度)。

    **DEATH 域保底(W956 治本,A′ 件)**:死亡域内结构零(板满/目标
    集空致 p_hit=0)时保底取 w(连胜金表相邻档差)——死亡域刷新的
    真实价值是「找任意可上阵件加当场战力」,win_eq 对该增量测得 0
    (量化盲区,W956 §1.2 F3),零估值 = 刷新在死亡域恒负 V = 分配器
    刷新臂结构性哑火;保底 w 使 V = m_eff·w − (c+I),与买臂同式,
    面值机会成本仍门控(小 c 才可正,金非免费)。停手窗域无保底
    (W956 证据面仅覆盖死亡域)。"""
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    from sr_od.application.currency_war.decision.decision_v2.candidates import (
        _target_names,
    )
    from sr_od.application.currency_war.decision.decision_v2.filters import (
        _deploy_free,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        BuyCard,
        ShopCard,
        bench_occupied,
    )
    w = _w_per_battle(state, session)
    l_c = _l_c(state, registry)
    # 可上场前提:bench 有空位(买得进)∧ deploy 有空位(上得场);
    # 板满帧刷新买件落 bench 不构成当视界增量(P23 兑现前提)——
    # 死亡域按保底语义取 w(见 docstring;W956 A′ 件)。
    if bench_occupied(state.bench or []) >= registry.bench_capacity \
            or _deploy_free(state) < 1:
        return w if domain is AllocDomain.DEATH else 0.0
    p_hit = 0.0
    best = 0.0
    for name in sorted(_target_names(state, session)):
        ch = CHARACTERS.get(name)
        if ch is None or not ch.cost:
            continue
        p = refresh_prob(state.level, ch.cost)
        if p <= 0:
            continue
        p_hit += p
        after = _apply_with_pipeline(
            state, (BuyCard(ShopCard(x=0, name=name, cost=ch.cost)),),
            session)
        best = max(best, _dpeff_from_states(state, after, registry, w,
                                            l_c))
    est = min(1.0, p_hit) * best
    if est <= 0.0 and domain is AllocDomain.DEATH:
        return w   # 目标集空/全零增量:死亡域同保底(W956 A′ 件)
    return est


def supply_proposals(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry,
                     domain: AllocDomain) -> list[AllocProposal]:
    """三渠道臂 → Π_t(W684 v6 §3;提案三元组按 O 分域参数集计值)。

    - 升级臂:P21 硬停域(discipline.blood_budget_levelup_blocked)不
      生成提案(§5 不动面,先于模型);升级提案的 dpeff 按「升级解锁
      的 bench 等待件上场」的跨档账整账(无等待件 → 无提案:升完
      没有能上场的强单位是 [32] 病例注,不供给空账)。
    - 买卡臂:_salvage_ok 完备式过滤;merge 候选 bench_slots=0。
    - 刷新臂:停付域直通不进 Π_refresh——单一址 = discipline.
      blood_budget_refresh_blocked(其 False 域恰 = v6 §3 三个直通域
      ALL IN/应急带/终止豁免;W733 修复①,与管线/段级检查同谓词);
      估计器见上。
    - Π_comp:前置边闭合(buy 目标件 + levelup 原子合并)。
    """
    return _supply_impl(state, session, registry, domain)


def _supply_impl(state: GameState, session: StrategySession,
                 registry: DecisionV2Registry,
                 domain: AllocDomain) -> list[AllocProposal]:
    from sr_od.application.currency_war.decision.decision_v2.candidates import (
        generate_candidates,
    )
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        blood_budget_levelup_blocked,
    )
    from sr_od.application.currency_war.decision.decision_v2.filters import (
        _deploy_free,
    )
    from sr_od.application.currency_war.kernel.cw_state import bench_occupied
    w = _w_per_battle(state, session)
    l_c = _l_c(state, registry)
    horizon = _m_horizon(state, session, registry)
    m_eff = (min(horizon, float(_deploy_free_battles(state, session,
                                                     registry)))
             if domain is AllocDomain.DEATH else horizon)
    # 刷新臂停付豁免域单一址(W733 修复①):discipline.
    # blood_budget_refresh_blocked 与管线刷新收尾/段级检查同谓词——
    # 其 False 域恰 = v6 §3 的三个直通域(ALL IN/应急带/终止豁免),
    # True 域 = 血预算停付(641025 r8/641056 r7 绕过形态的回归闸)。
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        blood_budget_refresh_blocked,
    )
    refresh_exempt = blood_budget_refresh_blocked(state, session, registry)

    cands = generate_candidates(state, session, registry)
    props: list[AllocProposal] = []
    lu_cand = None
    for c in cands:
        a = c.action
        if isinstance(a, LevelUp):
            lu_cand = c
        elif isinstance(a, RefreshShop):
            if refresh_exempt:
                continue   # 豁免域直通不进 Π_refresh
            d = _refresh_dpeff_estimate(state, session, registry, domain)
            props.append(AllocProposal(
                kind='refresh', dpeff=d, m_eff=m_eff, cost=int(a.cost or 2),
                actions=(a,), name='refresh', bench_slots=0,
                note={'estimator': 'single_sample_proxy'}))
        elif isinstance(a, BuyCard):
            if not _salvage_ok(c, state, registry, session):
                continue   # 已知不完备面(§4-P4 声明,不假装供给)
            after = _apply_with_pipeline(state, (a,), session)
            props.append(AllocProposal(
                kind='buy', dpeff=_dpeff_from_states(state, after,
                                                     registry, w, l_c),
                m_eff=m_eff, cost=int(a.card.cost or 3),
                actions=(a,), name=a.card.name,
                bench_slots=0 if c.merge else 1))
    # 升级臂:pop 位受益件 = bench 等待件(deploy 判据与 [33] 人口位同源:
    # bench 有件 ∧ deploy 无空位);P21 硬停域不生成
    if lu_cand is not None and not blood_budget_levelup_blocked(
            state, session, registry):
        # W718 修复(辖域冲突裁决落码):Π_up 继承上游 [12]/[33] 授权
        # 白名单——供给层过滤,非出清层特判。升级授权单一源 =
        # ev.levelup_ev_basis(pop_slot/dp/static_ev 三臂,与 arbiter
        # 升级门/段级检查白名单同谓词);白名单拒('')的帧分配器不出
        # 升级提案——「豁免后重估」豁免的是濒死止损,不越过白名单。
        from sr_od.application.currency_war.decision.decision_v2.candidates import (
            _target_names,
        )
        from sr_od.application.currency_war.decision.decision_v2.ev import (
            levelup_ev_basis,
        )
        _lu_cost = int(lu_cand.action.cost)
        _lu_basis = levelup_ev_basis(
            state, session, registry, state.gold or 0, _lu_cost,
            _target_names(state, session))
        if _lu_basis:
            lu_cand.action.auth_basis = _lu_basis   # 观测字段(检查器对账)
        from sr_od.application.currency_war.kernel.cw_state import (
            deployed_occupied,
        )
        has_waiter = (bench_occupied(state.bench or []) > 0
                      and deployed_occupied(state.deployed or [])
                      >= state.max_units())
        if _lu_basis and has_waiter:
            after = _apply_with_pipeline(state, (lu_cand.action,), session)
            props.append(AllocProposal(
                kind='levelup', dpeff=_dpeff_from_states(
                    state, after, registry, w, l_c),
                m_eff=m_eff, cost=_lu_cost,
                actions=(lu_cand.action,), name='levelup',
                bench_slots=0))
        # Π_comp:店内目标件 × 升级的前置边闭合(生成期合并,§2.1;
        # 复合含升级,同受白名单门辖)
        if _lu_basis and not has_waiter and _deploy_free(state) < 1 \
                and bench_occupied(state.bench or []) \
                < registry.bench_capacity:
            tset = _target_names(state, session)
            for c in cands:
                a = c.action
                if not isinstance(a, BuyCard) or a.card.name not in tset:
                    continue
                if c.merge or not _comp_feasible(a.card.name, state,
                                                 registry):
                    continue
                after = _apply_with_pipeline(
                    state, (a, lu_cand.action), session)
                props.append(AllocProposal(
                    kind='comp', dpeff=_dpeff_from_states(
                        state, after, registry, w, l_c),
                    m_eff=m_eff,
                    cost=int(a.card.cost or 3) + int(lu_cand.action.cost),
                    actions=(a, lu_cand.action), name=a.card.name,
                    bench_slots=1))
                break   # 取首条目标件(复合账同 V 并列按生成序,§4-P1)
    return props


def _deploy_free_battles(state: GameState, session: StrategySession,
                         registry: DecisionV2Registry) -> float:
    """死亡域截断上限的既名直读(ev.battles_left_plane;P23.3
    m_eff = min(兑现长, battles_left_plane))。

    表缺失保守下界(ADR-0493;W810 死亡域审查缺陷①):表缺失时
    battles_left_plane 退 registry.battles_left_est(骨架缺省 5)——
    对死亡域是系统性高估(位面末轮真实剩余战场实测 1-3 场,m_eff
    虚高 2-5 倍,V 同倍高估,视界截断形同虚设)。表缺失**或本位面
    剩余窗口为空**(表耗尽,同样只能落骨架回退)时,唯一确知的战场
    = 当轮本场(备战帧必有其后继战斗节点)→ 保守下界 1.0;表在且
    有剩余窗口则走真实槽序推导(位面末轮自然得 1-3)。"""
    from sr_od.application.currency_war.decision.decision_v2.ev import (
        NON_BATTLE_NODE_TOKENS,
    )
    from sr_od.application.currency_war.kernel.cw_plane_table import (
        NODES_PER_PLANE,
    )
    table = getattr(session, 'plane_node_table', None) or []
    if table:
        r = state.round_num
        window = [str(t) for t in
                  table[max(0, r - 1):min(len(table), NODES_PER_PLANE)]]
        if window:
            return float(sum(
                1 for t in window if t not in NON_BATTLE_NODE_TOKENS))
    return 1.0


def _opportunity_cost(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry, p: AllocProposal,
                      domain: AllocDomain) -> float:
    """机会成本项(§4-P5 分域参数集;W706 §8-1 落点;死亡域重标定
    = ADR-0493;必死子带收窄 = ADR-0510)。

    - 停手窗域:c + I(W690 账;I = ev.interest_cost,买侧回档折中
      口径与 arbiter.interest_rule 消费同源——recovery_rounds 只对
      买/复合开,刷新保持平面上界,双源互斥条款)。
    - 死亡域·必死子带(``must_die_band``,hp ≤ L_c):c(面值,I 退役)
      ——论证链 = P23.4(i) 极限形式(带内 P(存活)≈0 → 金终端价值≈0,
      攥金弱劣)→ W907(应急带金生存价值≈0)→ ADR-0503 → P36-a′
      (R*_crisis≡0)→ E1(拒供退役)→ 本步:息档保护对象(未来
      收入流)被死亡截断,I 无保护语义;c 面值保留(金不为负的记账
      下界 + 出清仍需 Δp 侧正贡献,非免费)。谓词单一源复用
      ``must_die_band``,标定 = w956 目录 CALIBRATION.md(n=60 零带外)。
    - 死亡域·子带外:c + I(面值,ADR-0493 现状语义不变;W810 反事实
      「携金进 P2 有用」覆盖的正是带外帧)。"""
    from sr_od.application.currency_war.decision.decision_v2.ev import interest_cost
    if domain is AllocDomain.DEATH and must_die_band(state, session,
                                                     registry):
        return float(p.cost)   # 必死子带:I 退役(ADR-0510;见 docstring)
    recovery = registry.interest_recovery_rounds \
        if p.kind in ('buy', 'comp') else None
    i = interest_cost(state.gold or 0, p.cost, state,
                      recovery_rounds=recovery)
    return float(p.cost) + i


def _feasible(subset: list[AllocProposal], gold_budget: int,
              bench_free: int, registry: DecisionV2Registry,
              state: GameState) -> bool:
    """R_t 可行性(整数金 + bench 槽 + copies_cap;实体争用边,§2.1 ③)。"""
    if sum(p.cost for p in subset) > gold_budget:
        return False
    if sum(p.bench_slots for p in subset) > bench_free:
        return False
    if any(p.kind == 'buy' for p in subset):
        from sr_od.application.currency_war.decision.decision_v2.discipline import (
            star_weighted_copies,
        )
        per_name: dict[str, int] = {}
        for p in subset:
            if p.kind != 'buy':
                continue
            per_name[p.name] = per_name.get(p.name, 0) + 1
        for name, added in per_name.items():
            if star_weighted_copies(name, state) + added \
                    > registry.copies_cap:
                return False
    return True


def allocate(proposals: list[AllocProposal], gold_budget: int,
             bench_free: int, registry: DecisionV2Registry,
             state: GameState) -> list[AllocProposal]:
    """帧内分配 = 依赖感知的整数金有界组合选择(§2.2;**精确枚举**,
    W706 §8-3 实现注记:子集全枚举 + 金/槽/不相容可行性检查——提案
    ≤15 时 2^n 平凡,禁落成单维金背包)。

    - 出清负判先行:V ≤ 0 的提案不进组合(§2.2 ①);
    - 破坏边语义化(§2.2 ③):refresh 是「轮终结者」——选中即独占
      本帧(买方账对当前店面估值的记账=兑现,后继店态下帧重derive);
      与非刷新组合互斥取 max(V_refresh, 最优非刷新组合),并列偏
      非刷新(保已见店面价值);
    - 同 V 并列按生成序(buy_tag_priority 字典序 refinement 的承载,
      §4-P1;不参与量纲)。"""
    positives = [p for p in proposals if p.v > 0]
    refresh = [p for p in positives if p.kind == 'refresh']
    others = [p for p in positives if p.kind != 'refresh']
    n = len(others)
    best: list[AllocProposal] = []
    best_v = 0.0
    for mask in range(1 << n):
        subset = [others[i] for i in range(n) if mask >> i & 1]
        if not subset:
            continue
        if not _feasible(subset, gold_budget, bench_free, registry, state):
            continue
        sv = sum(p.v for p in subset)
        if sv > best_v + 1e-9:
            best_v = sv
            best = subset
    if refresh and refresh[0].v > best_v + 1e-9 \
            and _feasible([refresh[0]], gold_budget, bench_free, registry,
                          state):
        # W718 修复:刷新臂同受 R_t 预算约束(budget=0 帧禁出手——
        # 此前只比 V 值绕过 _feasible,实锤 640564 把金花成负数;
        # cost ≤ E_t ≤ gold 保证花后金 ≥ reserve ≥ 0)。
        return [refresh[0]]
    return best


def allocator_run(state: GameState, session: StrategySession,
                  registry: DecisionV2Registry,
                  pipeline_spent: bool = False) -> AllocResult:
    """分配器帧入口(策略接线唯一消费面;每 decide_shop_screen 调一次)。

    非辖域帧 / 开关关 / 常规管线本帧已支出(``pipeline_spent``)→
    不接管(frame 披露原因),支出分配由既有四层管线全权——分配器
    只接管「管线没花出去」的坐息/攥金帧(W676 攥金死锁的矫正面),
    与在飞管线零重叠(同帧双花结构性排除)。"""
    res = AllocResult()
    if not ALLOCATOR_ENABLED:
        res.frame = {'active': False, 'reason': 'disabled'}
        return res
    domain = alloc_domain(state, session, registry)
    if domain is None:
        res.frame = {'active': False, 'reason': 'out_of_scope'}
        return res
    res.active = True
    res.domain = domain.value
    if pipeline_spent:
        res.frame = {'active': True, 'domain': domain.value,
                     'reason': 'pipeline_spent', 'gold': state.gold}
        return res
    props = _supply_impl(state, session, registry, domain)
    for p in props:
        opp = _opportunity_cost(state, session, registry, p, domain)
        p.v = p.m_eff * p.dpeff - opp
    from sr_od.application.currency_war.kernel.cw_economy import reserve_cap
    from sr_od.application.currency_war.kernel.cw_state import bench_occupied
    budget = max(0, (state.gold or 0)
                 - reserve_cap(state, session, registry))
    bench_free = max(0, registry.bench_capacity
                     - bench_occupied(state.bench or []))
    chosen = allocate(props, budget, bench_free, registry, state)
    # 状态推进语义(§2.2 ④)在组合选择层已等价覆盖:精确枚举按同一
    # R_t 预算逐子集可行性检查,选中的组合成本和 ≤ E_t——帧内无需
    # 再逐笔模拟推进(单帧静态账;执行序=动作组列表序)。
    res.actions = [a for p in chosen for a in p.actions]
    res.frame = {
        'active': True,
        'domain': domain.value,
        'param_set': ALLOC_PARAM_SET_VERSION,
        'gold': state.gold,
        'budget': budget,
        'proposals': len(props),
        'chosen': [{'kind': p.kind, 'name': p.name, 'v': round(p.v, 2),
                    'dpeff': round(p.dpeff, 3), 'm_eff': p.m_eff,
                    'cost': p.cost} for p in chosen],
        'alloc_gold': {k: sum(p.cost for p in chosen if p.kind == k)
                       for k in ('buy', 'levelup', 'refresh', 'comp')},
    }
    return res
