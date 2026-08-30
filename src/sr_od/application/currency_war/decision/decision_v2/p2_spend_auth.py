"""位面 2 支出授权(W757 v3.2 设计落码;决策 why=ADR-0480/0481/0483)。

设计对象(W754 立案 B):P2 板面冻结在过渡形态、带金血崩死、血线恶化
无支出响应、锁线后目标核心卡不买。v3 起为**两通道**结构(W762 A/B 机制
归因的覆盖修复:金堆积发生在授权谓词不触发的帧,单通道 T1∧T2 合取把
死亡窗系统性排除——248 个高金死亡局死前 3 轮内仅 38 局有授权帧):

- **通道 A 定向授权**(v2 原语义保留):T1 线锁定 ∧ T2 形态缺口 ∧ T4
  → 店内授权目标必入买序列(优先级 1 核心卡经非正分门豁免);T3 命中
  升格加急层(破息预算放宽);
- **通道 B 止血授权**(v3 新增;[18] 响应义务直译):T3 ∧ T4 ∧ 帧资格
  即触发,**与 T1 锁定位/T2 形态缺口解耦**——锁不锁定次要,血线恶化
  ∧溢余在手即授权;支出方向取既有机制现成输出(方向梯级见
  ``_channel_b_direction``),**只消费方向、不生产方向**(与换线摇摆域
  的切分 =「决策权 vs 出手权」,选线判据一颗不动)。

**预算带对齐(v3;W762 G1-A 破息反降的修正)——「只开门不收门」**:
授权通道的预算判定复用既有息账门谓词,不得额外收紧——常授权层
**不设独立地板**(既有门放行的笔授权不拒,既有门拒绝的笔授权不改判,
判定语义 =「与既有门同判」;v2 的贴线带证成前保守不买子句废除,它是
比既有 [22]④ 门更严的收门);加急层(通道 A 加急 / 通道 B)预算放宽
= 破息至保留金占位下限([18] 止损机械化,P25 待证标注见 registry)。
授权臂在门侧只做**额外放行**,从不拒绝——返回 False 即回落既有裁决。

**双通道同帧合并语义(v3.1)**:T1∧T2∧T3∧T4 同帧双触发时,授权谓词
**取或**、预算**取同值交集**(两通道放宽档 = 同一数值同一谓词,授权是
许可不是资金池,无可叠)、方向**同源**(锁定帧 hoard 输出即通道 A 优先
级 1 的同一目标集)、动作**去重**(单门单裁决,结构性成立)。

**血预算门层归属机械化(v3.1)**:血预算门(ADR-0448 停升级线 /
ADR-0451 刷新停付降格)一律为 discipline 层谓词,**不受任何姿态让位
条款影响**——本授权辖的是 economy/存息姿态结论的让位序(授权帧内
授权出手权优先于存息结论,帧资格不再要求 economy 模式),discipline
谓词照常拦截。本模块对 LevelUp 恒不辖(结构性:授权谓词对升级恒
False,P21 濒死禁 / ADR-0448 停升级线 AND 既有单一源不动)。

**末窗豁免收窄(v3)**:v2 的「P2 末窗(boss 窗)整体不触发」废除;
豁免统一归**分配器接管帧谓词本身**——``alloc_domain`` 现值(停手窗/
死亡域)非 None 的帧授权禁出手(单帧锁⑨,帧归属二选一);非接管的
末窗帧通道 B 可达、通道 A 照常判定(单帧锁⑦改写)。覆盖纪律态的
独立豁免(应急/war 模式/boss 窗)随两通道重构一并撤销——死亡窗帧
恰是止血授权的目标人群,W762 归因的「交界豁免系统性排除」即此。

**通道 B 方向梯级(v3.1 基础;v3.2 重排为 L1/L2/L3)**:方向源梯级
hoard 集(投影成功 ∧ 非空)→ 桥池方向件(``cw_bridge_pool.
BRIDGE_POOL_P2`` 现成输出)→ [31]① 空窗期语义(现有牌能凑的羁绊填充
件,以过渡体系键非空为「非纯散件」下界,排序归评分层)。**纯散件恒
不授权**([31] 反散件原则);**hoard 投影失败帧跳过 hoard 级直落桥池/
[31]①,禁用整库保守域作方向源**(该保守域语义是 prep_brain 既有买侧
D1 用的,整库含散件,与反散件原则直接冲突;单帧锁⑬)。

**v3.2 梯级重排(W772 A/B V3 分支 2:M0b=4.1% 出手失效——v3.1 梯级
给出的买目标太便宜,513 授权帧 503 帧毛支出>0 却低于当轮收入,金账
不降、囤金原样带到死)**:
- **L1 高价值定向**:①锁定线核心卡(贵价 3-5 费);②2★ 升级凑档件
  (为已在板/已在 bench 的同名件买第 2/3 副本,3合1 跳档,合成机制
  经 ``merge_buy_completes`` 单一源);③线内 3-5 费终局件(方向源集
  ∩ 费用 3-5)。**「高价值」无新魔数**——由净支出闸(下条)按单笔
  预期支出降序累计机械化排序;
- **L2 定向 D 找 L1 目标**:RefreshShop 照旧(P12 批账 j≥1 翻正才付,
  j=0 负例不变;通道 B 的 D 消费 [31]②「保血急救」合法用途,T3 触发
  即语境锚);
- **L3 低价兜底**:仅当 L1 全部过不了净支出闸(净支出闸选中集为空)
  时,v3.1 原梯级输出照旧放行(兜底层接受小额净支出);L1 过闸存在
  时 L3 件不获授权放行(单帧锁⑮)。

**净支出闭环闸(v3.2;W772 修订方向③,单帧锁⑭)**:通道 B 授权帧
的买候选须过净支出闸——本轮预期收入 = 基础奖励 + 连胜档 + 息
(economy §10 口径,备战帧可算,单一源 = ``BASE_INCOME``/
``streak_gold``/``cw_plane_table.interest``);授权放行的 L1 选中集
按单笔预期支出降序累计,累计 Σ支出 > 预期收入的前缀才放行——
「净支出 ≤0 的候选不出手,直接上更强目标」。校验是**目标选择器不
是新收门**:既有息账门放行的笔授权不拒(False 即回落既有裁决),
只在「同样合法的多个方向」中选净支出>0 的——与「只开门不收门」
相容;L3 兜底帧仍接受小额净支出(W772 空转形态的修正点在 L1 过闸
存在时的方向选择,不在兜底层)。**bench 保留槽(v3.1)**:通道 B 买入后备战席须保留
≥1 空槽([22]② 机械化;防连续止血买入填满 bench → 线锁定后核心卡
无槽可进的挤出回声),不足则本帧授权降额(回落既有裁决;卖出腾槽归
既有补偿/演进机制,授权通道只开门不发射动作)。

拦断面普查(v3;设计 §3.5,协议 M0 分层消费):金堆积候选帧逐帧记录
拦截原因枚举(``p2_spend_auth_intercept``:t1_locked/t2_form/no_t3/
t4_gold/v6_active/authorized/hoard_invalid),经 session 披露键接出
telemetry 决策迹;纯观测义务,不加任何决策行为。

辖域=plane==2 only(P3 扩辖不在本批;A/B 协议工况同口径)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.decision.cw_strategy import (
    StrategySession,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BuyCard,
    GameState,
    RefreshShop,
)

#: 授权买侧候选标签集(通道 A 优先级 2「凑档件与压库件」的辖域映射;
#: [34] 购买序三层语义由候选/评分既有通道承载,本集只定「哪些买候选在
#: 授权门与预算带的辖域内」)。= remedy_buy_tags 去 engine_seed/carry_gate:
#: engine_seed 是 P1 过渡引擎语义非 P2 授权目标;carry_gate 腾位买有
#: 独立门。定向 D(RefreshShop)不经标签集(全刷新候选辖)。
P2_AUTH_BUY_TAGS: frozenset[str] = frozenset({
    'line_carry', 'line_opportunistic', 'bridge_core', 'plugin',
    'copy_press',
})


@dataclass
class P2SpendAuth:
    """授权帧快照(每帧一次派生;纯观测判据,无跨轮状态)。

    ``urgent`` = 加急预算带命中(T3;通道 A 加急与通道 B 共用同一放宽
    档——双通道合并语义「预算同值交集」的载体)。``channel_a``/
    ``channel_b`` 为通道归属明细(判读/遥测面);``notes`` 带 T1-T3
    命中位与通道 B 方向源投影位(拦断面审计数据源)。
    """

    urgent: bool = False       # True=加急预算带(T3 命中;两通道同档)
    channel_a: bool = False    # 通道 A 定向授权(T1∧T2∧T4∧帧资格)
    channel_b: bool = False    # 通道 B 止血授权(T3∧T4∧帧资格)
    #: 判读注记(T1-T3 命中位/方向源投影失败位;「为什么授权/哪一层/
    #: 方向落在梯级哪一级」可复算)
    notes: dict = field(default_factory=dict)


def _frame_verdict(state: GameState, session: StrategySession,
                   registry: DecisionV2Registry,
                   ) -> tuple[P2SpendAuth | None, str]:
    """授权辖域判定核(帧/拦截原因二元组;frame 与 telemetry 同一推导)。

    返回 ``(None, 原因)`` = 本帧不授权零行为;``(auth, 'authorized'|
    'hoard_invalid')`` = 授权触发。原因枚举(拦断面普查,协议 M0 分层
    消费;优先序 = v6_active > t4_gold > authorized/hoard_invalid >
    t1_locked > t2_form > no_t3——t1/t2 细位另存 notes,T2 死亡窗失真
    审计按 notes.t2 复算):
    """
    if not registry.p2_spend_auth_enabled:
        return None, ''
    if state.plane != 2:
        return None, ''
    # 交界⑨(帧资格):分配器接管帧(v6 active,停手窗/死亡域)授权
    # 禁出手——帧归属二选一,不并存;末窗豁免统一归本谓词(锁⑨+锁⑦
    # 合取,ALL IN/降格语义所在帧由此闭合)。
    from sr_od.application.currency_war.decision.decision_v2.allocator import (
        alloc_domain,
    )
    if alloc_domain(state, session, registry) is not None:
        return None, 'v6_active'
    # T4:金水位 g ≥ 息线(边界点取 ≥;[17]/P13;g<50 守息不破,锁④)。
    if (state.gold or 0) < registry.interest_floor():
        return None, 't4_gold'
    # T1:线锁定(P16 滞回后 v3 状态机位,禁原始意向位)。
    ist = getattr(session, 'v3_intention', None)
    t1 = (getattr(ist, 'phase', '') == 'locked'
          and bool(getattr(ist, 'locked_comp', '')))
    # T2:形态缺口(锁定线 form_ok 单一源取反;Q5 口径,不立第二口径)。
    from sr_od.application.currency_war.decision.decision_v2.phase import (
        form_ok,
    )
    t2 = not form_ok(state, session, registry)
    # T3:血线恶化(连败口径 = 带符号 streak 单一源;hp 占位警戒带按
    # 可信位守卫——兜底 100 帧不作报警依据,ADR-0282 口径)。
    loss_streak = max(0, -(state.streak or 0))
    hp_alert = ((state.hp_readable or state.hp_trusted)
                and state.hp <= registry.p1_exit_blood_target)
    t3 = loss_streak >= registry.p2_spend_auth_fail_streak_n or hp_alert
    channel_a = t1 and t2
    channel_b = t3
    if not channel_a and not channel_b:
        # 拦截原因取通道 A 首个被拦谓词(t1/t2 细位另存 notes):t2_form
        # 仅在锁定帧内出现 = Q5 判据(锁定线形态)失真率审计的真人群。
        if not t1:
            return None, 't1_locked'
        if not t2:
            return None, 't2_form'
        return None, 'no_t3'
    hoard_invalid = False
    if channel_b:
        _, hoard_readable = _hoard_projection(state, session)
        hoard_invalid = not hoard_readable
    auth = P2SpendAuth(urgent=t3, channel_a=channel_a, channel_b=channel_b,
                       notes={
                           't1_locked': t1, 't2_form': t2, 't3': t3,
                           'loss_streak': loss_streak,
                           'hp_alert': hp_alert, 'hp': state.hp,
                           'gold': state.gold,
                           'hoard_invalid': hoard_invalid,
                       })
    # 拦断面:通道 B 独占帧且方向源投影失败 → hoard_invalid(锁⑬观测位;
    # 该帧授权仍触发,仅方向降级到桥池/[31]①)。
    return auth, ('hoard_invalid'
                  if hoard_invalid and not channel_a else 'authorized')


def _hoard_projection(state: GameState,
                      session: StrategySession) -> tuple[frozenset[str],
                                                         bool]:
    """通道 B 梯级 1:hoard 集投影(只读;返回 (目标集, 投影成功位))。

    消费 ``cw_intention.hoard_target_set`` 全模式总函数——locked 输出
    锁定线采购集(= 通道 A 优先级 1 同一目标集,方向同源);P2 未锁定
    帧输出兜底档/跨线骨架(**恒定方向,不随 pivot 振荡**,W758-v3 面①
    攻击 A 代码级核实)。经模块属性调用(非 from-import 绑定)以便
    投影失败注入测试;失败帧返回 (空集, False),消费侧跳 hoard 级。
    """
    ist = getattr(session, 'v3_intention', None)
    if ist is None:
        return frozenset(), False
    from sr_od.application.currency_war.kernel import cw_intention
    try:
        ht = cw_intention.hoard_target_set(state, ist)
    except Exception:   # noqa: BLE001  投影失败显式暴露(D1 同口径)
        return frozenset(), False
    s = frozenset(ht.char_targets) | frozenset(ht.equip_targets)
    return s, True


def _channel_b_direction(state: GameState,
                         session: StrategySession) -> frozenset[str] | None:
    """通道 B 方向梯级(v3.1;返回授权目标名集,None=[31]① 逐候选判)。

    梯级:① hoard 集(投影成功 ∧ 非空)→ ② 桥池方向件
    (``BRIDGE_POOL_P2`` fixed∪core∪flex,plane==2 硬门下即 P2 桥)
    → ③ [31]① 空窗期语义(现有牌能凑的羁绊填充件)——逐候选以
    ``scoring._cand_system_bonds`` 非空为「非纯散件」下界(排序归评分
    层,授权只定辖域)。**hoard 投影失败帧跳过 ① 级直落 ②/③,禁用
    prep_brain 整库保守域作方向源**(锁⑬;该保守域含散件,与「纯散件
    恒不授权」直接冲突)。
    """
    hoard, readable = _hoard_projection(state, session)
    if readable and hoard:
        return hoard
    from sr_od.application.currency_war.kernel.cw_bridge_pool import (
        BRIDGE_POOL_P2,
    )
    pieces: set[str] = set()
    for combo in BRIDGE_POOL_P2:
        pieces |= set(combo.fixed) | set(combo.core) | set(combo.flex)
    if pieces:
        return frozenset(pieces)
    return None    # 梯级 3:[31]① 逐候选(非纯散件)判


def _bench_reserve_ok(working: GameState, a: BuyCard) -> bool:
    """通道 B bench 保留槽(v3.1;[22]② 机械化):买入后备战席保留
    ≥1 空槽。合成触发买净腾槽(3合1 买入即合成 −1 净增量)豁免;
    不足 → 本帧授权降额(回落既有裁决;卖出腾槽归既有补偿机制)。"""
    from sr_od.application.currency_war.kernel.cw_state import (
        BENCH_CAPACITY,
        bench_occupied,
        merge_buy_completes,
    )
    occupied = bench_occupied(working.bench or [])
    free = BENCH_CAPACITY - occupied
    if free - 1 >= 1:
        return True
    return merge_buy_completes(a.card.name, a.card.star or 1,
                               working.bench, working.deployed,
                               working.shop)


def p2_spend_auth_frame(state: GameState, session: StrategySession,
                        registry: DecisionV2Registry) -> P2SpendAuth | None:
    """授权辖域判定(两通道取或;None=本帧不授权,零行为)。

    纯函数,每消费点现算(派生量模式,同 phase.form_ok;session 丢失
    → 下帧现算,天然免疫)。返回 None 的帧一切既有裁决不变。
    """
    return _frame_verdict(state, session, registry)[0]


def p2_spend_auth_intercept(state: GameState, session: StrategySession,
                            registry: DecisionV2Registry) -> str:
    """拦断面普查(设计 §3.5;纯观测,零决策行为):本帧拦截原因枚举。

    取值 = ''(开关关/非 P2,无授权语义)/ t1_locked / t2_form /
    no_t3 / t4_gold / v6_active / authorized / hoard_invalid。经
    decide_prep 每轮写 session 披露键,telemetry 决策迹统一接出
    (协议 M0 分层归因唯一数据源;死亡窗 T2 失真率审计按 notes 细位)。
    """
    return _frame_verdict(state, session, registry)[1]


def _reserve_floor(state: GameState, session: StrategySession,
                   registry: DecisionV2Registry) -> int:
    """加急层保留金下限(v3.2 公式化;取代常数占位,单帧锁组「放宽有
    界」的界)。

    **下限 = 5 × min(本位面剩余备战轮数, cap)**——P13 息流式的直接
    截断:保留金的收益上限 = 每轮息 5 金、封顶 ``cap`` 轮(位面末守息
    无意义,P13「r9 C=0」同源截断),取值域 [5, 15]。剩余备战轮数含
    当前帧(末轮帧仍保 5)。公式输入异常(日程表缺/轮数越界)回落
    ``p2_spend_auth_reserve_floor`` **绝对异常地板**(常数 20 的 v3.2
    语义:只防负值/公式输入异常,不再参与常态判定)。W772 实证(1462
    加急帧/破息仅 53)证明常数下限把出手力度卡死;权衡账 = T3 帧
    多保金的息收益 ≤5 金/轮 vs 救活一场败局 15.39(P2 条件败局伤害)。
    """
    from sr_od.application.currency_war.kernel.cw_plane_table import (
        schedule_of,
    )
    try:
        plen = schedule_of(session)[state.plane - 1]
        remaining = int(plen) - int(state.round_num or 0) + 1
    except Exception:   # noqa: BLE001  公式输入异常显式回落异常地板
        return registry.p2_spend_auth_reserve_floor
    if remaining < 1:
        return registry.p2_spend_auth_reserve_floor
    return 5 * min(remaining,
                   max(1, registry.p2_spend_auth_reserve_rounds_cap))


def _expected_round_income(working: GameState) -> int:
    """本轮预期收入(economy §10 备战帧口径;净支出闸的分母单一源)。

    = 基础奖励(BASE_INCOME)+ 连胜档(streak_gold,连败/无连胜取
    counter0 档 1)+ 息(interest,g 按**花前**金账——与结算息同源)。
    三分量全部为既有单一源转发,零新常量。"""
    from sr_od.application.currency_war.kernel.cw_economy import (
        BASE_INCOME,
        streak_gold,
    )
    from sr_od.application.currency_war.kernel.cw_plane_table import (
        interest,
    )
    streak = max(0, working.streak or 0)
    return BASE_INCOME + streak_gold(streak) + interest(working.gold or 0)


def _channel_b_l1_selected(working: GameState,
                           session: StrategySession) -> frozenset[str]:
    """净支出闸 L1 选中名集(v3.2;空集 = L1 全败/无 L1 目标 → 落 L3)。

    L1 成员(§模块 docstring 三子句):①核心名 ∩ 费 3-5;②同名副本
    买入即完成 3合1(``merge_buy_completes`` 单一源);③方向源集 ∩
    费 3-5。选中规则 = 按单笔预期支出**降序**累计,累计 Σ支出 > 本轮
    预期收入的前缀全部入选(W772 修订方向③:净支出 ≤0 的候选不出手;
    「高价值」无新魔数,由本闸机械化排序)。收入读 ``_expected_round_
    income``;店读 ``working.shop``(帧快照,与仲裁同一工作态)。
    """
    income = _expected_round_income(working)
    core = _core_names(session)
    direction = _channel_b_direction(working, session)
    from sr_od.application.currency_war.kernel.cw_state import (
        merge_buy_completes,
    )
    cands: list[tuple[int, str]] = []
    for sc in working.shop or []:
        name = getattr(sc, 'name', '')
        cost = int(getattr(sc, 'cost', 0) or 0)
        if not name or cost <= 0:
            continue
        l1 = ((name in core and 3 <= cost <= 5)
              or merge_buy_completes(name, getattr(sc, 'star', 1) or 1,
                                     working.bench, working.deployed,
                                     working.shop)
              or (direction is not None and name in direction
                  and 3 <= cost <= 5))
        if l1:
            cands.append((cost, name))
    if not cands:
        return frozenset()
    cands.sort(reverse=True)
    selected: set[str] = set()
    acc = 0
    for cost, name in cands:
        selected.add(name)
        acc += cost
        if acc > income:
            return frozenset(selected)
    return frozenset()   # L1 全部过不了净支出闸 → L3 兜底


def _budget_band_ok(auth: P2SpendAuth, working: GameState, cost: int,
                    registry: DecisionV2Registry,
                    session: StrategySession) -> bool:
    """单笔花费是否落在当前授权层预算带内(层强度唯一裁决点)。

    - **加急层(urgent)**:花完 ≥ 保留金下限(v3.2 公式化:
      ``_reserve_floor``;[18] 止损机械化,破息放宽的唯一档);
    - **常授权层:无独立地板**(v3 预算带对齐——既有息账门放行的笔
      授权不拒、拒绝的笔不改判,「与既有门同判」;v2 的「花完仍≥息线
      +贴线带保守不买」是比既有门更严的收门,G1-A 破息反降 0.93%→
      0.14% 的机制,废除;P25 分带核验数学义务保留,判定语义同既有门)。
    """
    if not auth.urgent:
        return True
    return ((working.gold or 0) - cost
            >= _reserve_floor(working, session, registry))


def _in_scope(a, cand, state: GameState, session: StrategySession,
              auth: P2SpendAuth) -> bool:
    """授权目标辖域判定(双通道取或;动作去重=单裁决点)。"""
    if isinstance(a, RefreshShop):
        return True    # 定向 D 全辖(评分 V_D 批账不动,j=0 负例保持;
        # 通道 B 的 D 消费 [31]②「保血急救」合法用途,T3 触发即语境锚)
    if not isinstance(a, BuyCard):
        return False
    if getattr(a.card, 'name', '') in _core_names(session):
        return True    # 优先级 1:锁定线核心卡([31]② 唯一最高优先级)
    if getattr(cand, 'tag', '') in P2_AUTH_BUY_TAGS:
        return True    # 通道 A 优先级 2 标签集
    if auth.channel_b:
        direction = _channel_b_direction(state, session)
        if direction is not None:
            return getattr(a.card, 'name', '') in direction
        # [31]① 级:过渡体系键非空 = 非纯散件(空键 = 纯散件恒不授权)
        from sr_od.application.currency_war.decision.decision_v2.scoring import (
            _cand_system_bonds,
        )
        return bool(_cand_system_bonds(cand))
    return False


def p2_spend_auth_spend_authorized(cand, working: GameState,
                                   state: GameState,
                                   session: StrategySession,
                                   registry: DecisionV2Registry,
                                   auth_trace: dict | None = None) -> bool:
    """arbiter 门侧消费:本笔花费的**加急预算放宽**是否放行。

    消费契约:本函数只在**加急层**(T3 命中,通道 A 加急 / 通道 B 共
    档)放行破息至保留金下限的授权目标买/定向 D——常授权层恒 False =
    既有息账门全权裁决(「与既有门同判」,不叠加独立地板;授权臂只做
    额外放行,从不拒绝,False 即回落既有裁决,零收门)。升级(LevelUp)
    永不在辖;通道 B 买入受**净支出闸 L1 梯级选择**(v3.2,锁⑭⑮:净支
    出闸选中集非空时仅选中名获放行,空集=L1 全败落 L3 兜底照旧)与
    bench 保留槽约束(不足降额);授权帧 None(开关关/条件不合/接管帧)
    恒 False=零行为。
    """
    auth = p2_spend_auth_frame(state, session, registry)
    if auth is None or not auth.urgent:
        return False
    a = getattr(cand, 'action', cand)
    from sr_od.application.currency_war.kernel.cw_state import LevelUp
    if isinstance(a, LevelUp):   # 升级永不在辖(P21/ADR-0448 discipline 层)
        return False
    if not _in_scope(a, cand, state, session, auth):
        return False
    cost = int(getattr(a, 'cost', 0) or (a.card.cost if isinstance(a, BuyCard)
                                         else 2) or 0)
    if cost <= 0:
        return False
    # 净支出闸 L1 梯级选择(v3.2;锁⑭⑮):通道 B 帧的买候选,选中集非
    # 空时仅选中名获授权放行(高价值优先,兜底件不获放行——回落既有裁
    # 决,非收门);空集 = L1 全败/无 L1 目标 → L3 兜底照旧(接受小额
    # 净支出)。D(L2)不经本闸(P12 批账不动)。
    l1_selected: frozenset[str] | None = None
    if auth.channel_b:
        l1_selected = _channel_b_l1_selected(working, session)
        if l1_selected and isinstance(a, BuyCard) \
                and getattr(a.card, 'name', '') not in l1_selected:
            return False
    if not _budget_band_ok(auth, working, cost, registry, session):
        return False
    if isinstance(a, BuyCard) and auth.channel_b \
            and not _bench_reserve_ok(working, a):
        return False    # 锁⑫:保留槽不足,本帧授权降额
    if auth_trace is not None:
        tier = ('L1' if l1_selected else 'L3兜底') \
            if (auth.channel_b and l1_selected is not None) else ''
        auth_trace['p2_spend_auth'] = (
            f"加急层放行(金{working.gold}-费{cost};"
            f"通道{'A' if auth.channel_a else ''}"
            f"{'B' if auth.channel_b else ''}"
            f"{'·' + tier if tier else ''};"
            f'保留金下限{_reserve_floor(working, session, registry)};'
            f'连败{auth.notes["loss_streak"]}/hp报警{auth.notes["hp_alert"]})')
    return True


def p2_spend_auth_core_must_buy(cand, working: GameState, state: GameState,
                                session: StrategySession,
                                registry: DecisionV2Registry) -> bool:
    """优先级 1 必买判定(非正分门豁免消费;[31]② 唯一最高优先级)。

    授权帧 ∧ 核心卡在店 → 该买候选越过非正分门进入约束链。v3 对齐:
    本豁免**不做预算带预判**(金/息账由约束链既有门按「与既有门同判」
    裁决——加急层的破息放宽在门侧授权臂;常授权层既有门结论即终局),
    豁免≠无条件采纳:金地板/息账/bench/copies_cap 照常辖。买进
    bench/凑档,不无脑上板([21] 窗口语义,部署管线不动)。
    """
    from sr_od.application.currency_war.kernel.cw_state import BuyCard as _B
    a = getattr(cand, 'action', None)
    if not isinstance(a, _B):
        return False
    if a.card.name not in _core_names(session):
        return False
    return p2_spend_auth_frame(state, session, registry) is not None


def _core_names(session: StrategySession) -> set[str]:
    """意向核心名集(candidates._core_names 单一源转发,防循环导入)。"""
    from sr_od.application.currency_war.decision.decision_v2.candidates import (
        _core_names as _names,
    )
    return _names(session)
