r"""经济循环总模型:储备制(R*/义务/通道容量)(ADR-0445)。

设计=唯一规格:`.debug/temp/currency_war/w471_economy_cycle/DESIGN.md`
(W481 对抗审计修复项 A-1/A-2 内建)。核心语义:金账从「地板制」(只
规定花后下限)改为「储备制」——任何时刻金 g 与储备上限 R* 的差
``(g − R*)+`` 是负有转化义务的死钱,每轮必须经三条转化通道(升级/
刷新/买牌)之一转成战力,义务 = max(既有臂义务, min(溢余, C_t))。

- **R\* = 息线 + 窗口(≤3 轮)排程升级费**:息线(50)以内持有弱占优
  (0.1/轮 无风险收益 vs 战力链 ≤0.012,ADR-0443 同一笔账反向使用);
  排程升级是价格/时点已知的确定性转化,为其持金不是死钱。窗口 h =
  min(3, 到本位面末节点轮数)——h>3 的升级应即时执行而非长期储蓄。
  排程判据 = ``schedule_upgrade`` 确定性费用查表核(批 3 预算收权,
  W615 §1.3 R4 规则集;原 DP 姿态 level_up 供给退役);升级费逐帧现读
  (state.level_up_cost OCR 优先,缺省 XP_CLICK_COST_FLAT;W481 A-4:
  不用粗估表)。
- **C_t 通道容量**(结构上限,由既有层逐帧算出):升级计划费 +
  可买非期权件账(bench 余量约束)+ 刷价×刷新预算(refresh_ev_budget
  预算式,值域 [0,6])。
  **A-1 修复**:formation_gold_account 对未跨档件给
  ``d_rem × engine_jump_gold`` 的正账是「按兑现价卖期权」(W469 已
  实测死法),这类期权件**不计入容量**——容量只计当帧跨档件
  (买入后四体系达成数 +1,``_crosses_engine_tier`` 结构性判定)与
  3合1 合成件(买入即 2★ 完成);**A-2 修复(声明+约束)**:每买
  一件占一个 bench 槽,槽位是下一轮跨档件的物理前置——容量按 bench
  空槽逐件扣减计入该机会成本(合成件净腾槽不占)。
- **义务帧兑现**:release 臂(posture_release)消费 overflow/obligation
  作为预算下界;g≥0 硬钳制在 authorize_release_refresh(W477 披露的
  执行层透支修复)。
- **息基守卫收窄**:息线以内的常态帧(g≤R*)行为零漂移(义务只在
  溢余段激活;I-1 锚)。

P2 刷新容量 12 < 收入 13-19 的扩容评估 = 披露面(判读层义务帧兑现率
分布),本模块不改刷新帽(设计 §4 风险声明③)。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)

#: 储备窗口上界(轮;设计 §1.3:h = min(到下一 boss 节点轮数, 3)——
#: 更远的排程升级应即时执行而非长期储蓄,结构界非拍值)。
RESERVE_WINDOW_ROUNDS: int = 3

#: 刷新通道容量上界(刷数;原 DP 求解面动作上限 6 刷
#: 同源(git prior art),不另造第二把尺)。
REFRESH_ROLL_CAP: int = 6


def _upgrade_scheduled(state: GameState, session: StrategySession) -> bool:
    """排程升级判据(兼容旧名;单一实现=``schedule_upgrade``)。"""
    return schedule_upgrade(state, session)


def _registry_of(session: StrategySession) -> DecisionV2Registry:
    """接缝函数的注册表解析(A/B 注入面:session.v3_registry 显式注入
    优先,缺省落 DEFAULT_REGISTRY——缺省栈无注入臂,P6 契约同 prep_brain
    装配签名)。"""
    reg = getattr(session, 'v3_registry', None)
    return reg if isinstance(reg, DecisionV2Registry) else DEFAULT_REGISTRY


def _interest_floor_of(session: StrategySession,
                       registry: DecisionV2Registry | None = None) -> int:
    """息线(守息线,interest_cap×10 同源派生,W611 §2.2 恒等式;
    接缝函数族共用的单一取址)。"""
    return (registry or _registry_of(session)).interest_cap * 10


def schedule_upgrade(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry | None = None) -> bool:
    """排程升级判据(确定性费用查表核;蓝图 §3.4 R4 接缝,批 3 预算收权)。

    ``registry``:显式注入优先(A/B 注入面,P6 契约:同一调用链全部接缝
    必须传**同一个** registry 实例——prep_brain._budget 单源装配);
    缺省落 _registry_of(session) → DEFAULT_REGISTRY。
    规则集 = W615 §1.3/§2-R4(机制常量直算,零标定权重);**预告态契约**
    (W623 D1):排程只回答「要不要开始攒」,不以当帧可负担为前置——
    付不付得起是执行层的事(``ev.levelup_ev_basis`` 可负担性入口门),
    排程判据若收窄成「付得起才排」会造成 R* 塌缩 → 义务花光 → 更排不上
    的自我强化升级迟到循环(DP 无此失败模式:其 level_up 判定不依赖当帧
    是否看得见目标)。

    触发(任一,判据单一址=R4:本函数被 R* 储蓄分量(reserve_cap)、
    arbiter 金地板授权、EV 升级授权 ② 臂三处共调):
    ① 人口位([33]):cap 满 ∧ bench 有成型件(2★)等上场——升级后能
       立即部署,当轮兑现战力,为最高义务;
    ② 概率级([3]/[7]):目标核心概率峰值级 > 当前级 ∧ 息引擎已立
       (g ≥ 息线,[12] 息引擎前置)。
    禁升条件([12]/[32]):息引擎未立不追级(② 的前置即此);空升级
    不升(① 触发本身即「有件可上」,无空升级面;② 是概率抬档语义,
    不涉部署)。
    **规则文本偏差披露(W635 F2)**:W615 §2-R4 规则 2 原文有第三合取
    「花完升级费后 g′ ≥ interest_floor」,与其 §1.3 伪码矛盾(伪码无此
    项);本实现**取伪码侧**(预告态,不设该合取——保留它会让
    g∈[息线, 息线+费) 帧不排程,恰造 D1 塌缩循环)。可负担性/平台未破
    由执行层收口:ev.levelup_ev_basis 可负担性入口门 + ② 臂花后 ≥息线。

    目标级解析:意向锁定核心 → 兜底 comp 核心 → 缺省 3 费档(meta
    「7 级搜牌」主流带);费用档 → 峰值级查表
    (``cw_plane_table.peak_refresh_level``)。comp 空帧不缺供给——
    兜底链保证 L_target 恒可解(D1:target 级判定迟疑帧返回 False 是
    塌缩循环的入口,禁)。
    """
    from sr_od.application.currency_war.cw_investments import (
        refresh_invest_active,
    )
    if refresh_invest_active(state):
        return False    # 淘金客姿态:升级通道退役(W621;谓词单一址)
    from sr_od.application.currency_war.cw_state import (
        deployed_occupied,
    )
    reg = registry or _registry_of(session)
    # ① 人口位:cap 满 ∧ bench 有成型件(2★)等上场([33]/[32](a))
    if deployed_occupied(state.deployed or []) >= state.max_units() \
            and any(b is not None and (getattr(b, 'star', 1) or 1) >= 2
                    for b in (state.bench or [])):
        return True
    # ② 概率级:息引擎已立 ∧ 目标峰值级在当前级之上
    if (state.gold or 0) < reg.interest_cap * 10:
        return False
    return _target_peak_level(state, session) > (state.level or 1)


def _target_peak_level(state: GameState, session: StrategySession) -> int:
    """目标核心费用档 → 概率峰值级(解析链:意向锁定核心 → 兜底 comp
    核心 → 缺省 3 费;核心解析单一源 = ev._vd_core_of 与其兜底扩展)。"""
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    from sr_od.application.currency_war.cw_plane_table import (
        peak_refresh_level,
    )
    core = _schedule_target_core(session)
    ch = CHARACTERS.get(core) if core else None
    cost = ch.cost if ch is not None and ch.cost else 3
    return peak_refresh_level(cost)


def _schedule_target_core(session: StrategySession) -> str:
    """排程目标核心解析(ev._vd_core_of 锁定核单一源;未锁帧落意向
    ⑤兜底 comp 的核心——方向层 FALLBACK_COMP_NAME 单一源;再缺='' →
    调用方缺省 3 费档,供给不断)。"""
    from sr_od.application.currency_war.cw_intention import (
        FALLBACK_COMP_NAME,
    )
    from sr_od.application.currency_war.decision_v2.ev import _vd_core_of
    core = _vd_core_of(session)
    if core:
        return core
    from sr_od.application.currency_war.cw_comps import get_comp
    fb = get_comp(FALLBACK_COMP_NAME)
    if fb is not None:
        from sr_od.application.currency_war.cw_intention import intention_core
        return intention_core(fb)
    return ''


def refresh_ev_budget(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry | None = None) -> int:
    """刷新 EV 授权刷数(确定性预算式;蓝图 §3.4 R4 接缝,批 3 预算收权)。

    ``registry``:显式注入优先(P6 契约,同 schedule_upgrade);缺省落
    _registry_of(session) → DEFAULT_REGISTRY。
    预算 = min(6, ⌊(g − R*)/刷价⌋)——只花溢余(W615 §2-R3 预算式:
    刷新后仍守储备线;6 刷帽单一源 = REFRESH_ROLL_CAP,原 DP 求解面
    _ACTION_ROLLS 的 DP 上限同源,不另造第二把尺)。

    合法 0 帧契约(W623 D2,判前锁;**辖域=应急带**,W635 F1 收口):
    - 应急帧(``filters.is_emergency`` 单一源,hp≤emergency_hp)→ 0:
      应激通道根本不产指令(release 让位结构,合并无从放大);
    - g ≤ R* 常态帧(息线以内/储备段持有,0.1/轮 真实收益)→ 0:这个 0
      流过 scoring P2 窗判据(``refresh_budget<=0 → 让位``)与存息
      准入门,「>0 即行动授权」的语义在预算函数口径下成立。
    **血预算带(应急线以上,ADR-0448/0451)不在本函数辖域**:预算字段
    依公式照发,停手由 arbiter 拒付层兜底(discipline.
    blood_budget_levelup_blocked 停升级 / blood_budget_refresh_blocked
    搜索型刷新停付)——防线在拒付层不在预算层;原「血预算帧→0」为
    虚标契约,已随 W635 F1 如实收窄(穿透锁=test_cw_w633_migration_b3)。
    定向刷新授权(directed_refresh_budget)是独立车道(arbiter E2,
    1 次/轮),与本预算不相交、不合并——披露面,非 0 帧契约的一部分。
    """
    from sr_od.application.currency_war.decision_v2.filters import (
        is_emergency,
    )
    reg = registry or _registry_of(session)
    if is_emergency(state, reg):
        return 0
    over = (state.gold or 0) - reserve_cap(state, session, reg)
    if over <= 0:
        return 0
    cost = state.shop_refresh_cost or 2
    return min(REFRESH_ROLL_CAP, over // cost)


def upgrade_plan_fee(state: GameState) -> int:
    """下一级升级总费(逐帧现读:OCR 单击价优先,缺省 flat 常量)。"""
    from sr_od.application.currency_war.cw_plane_table import clicks_to_level
    from sr_od.application.currency_war.cw_state import (
        XP_CLICK_COST_FALLBACK,
    )
    click = state.level_up_cost or XP_CLICK_COST_FALLBACK
    return clicks_to_level(state.level) * click


def _rounds_to_plane_end(state: GameState, session: StrategySession) -> int:
    """到本位面末节点(= boss 节点)的剩余轮数(含当前轮;缺读兜底 0
    =不储蓄,保守侧:R* 退化为息线,义务面变宽但方向安全)。
    nodes_of_plane 自带缺表回退(先验 9+一次性告警),此处不再兜层。"""
    from sr_od.application.currency_war.cw_plane_table import nodes_of_plane
    total = nodes_of_plane(session)
    return max(0, total - state.round_num)


def reserve_cap(state: GameState, session: StrategySession,
                registry: DecisionV2Registry) -> int:
    r"""R\*(t) = interest_floor + Σ 窗口内排程升级费(设计 §1.3)。

    窗口 h = min(3, 到本位面末节点轮数);只储蓄下一级费用——多级
    排程在逐帧重算下自愈(升级完成一轮后 R* 自然滚动到下一级;W481
    A-4:误估最坏=一个升级费量级 ≤50 金,双向有界)。
    排程判据单一址 = ``schedule_upgrade``(确定性查表核,批 3 预算
    收权;与 arbiter 授权/EV 授权 ② 臂共调同一函数,R4)。

    守息线取 `interest_cap × 10`(息帽同源派生,W611 §2.2 恒等式):
    基参数下 5×10=50==interest_floor,行为零漂移;写法保证「守息线
    ≤ 封顶线」结构性成立——两者同源,不可能出现守息线高于持有增益
    归零点(息帽截断点)的态。策略级息帽 override(interest_cap_override)
    走 ledger/DP 通道,registry 息帽与之分离时以封顶线为准(设计 §2.2
    规则原文);分离面=已知缺口,如实挂账。
    """
    h = min(RESERVE_WINDOW_ROUNDS,
            _rounds_to_plane_end(state, session))
    floor = registry.interest_cap * 10
    if h <= 0 or not schedule_upgrade(state, session):
        return floor
    return floor + upgrade_plan_fee(state)


def overflow(state: GameState, session: StrategySession,
             registry: DecisionV2Registry) -> int:
    """溢余段 (g − R*)+(义务压力的原料;≤0 = 无义务帧)。"""
    return max(0, (state.gold or 0) - reserve_cap(state, session, registry))


def _crosses_engine_tier(state: GameState, name: str) -> bool:
    """店内件「当帧跨档」判定(结构性:买入后四体系达成数 +1)。

    判据单一源=cw_deploy_logic.engines_count(与 deploy/形态维同一把
    尺);板面羁绊计数取 state.board,候选贡献经 CHARACTERS 阵营/流派
    ∩ TRANSITION_TRAITS(与 scoring._cand_system_bonds 同口径)。
    A-1 刀法:仅此判定为真的件计入容量,未跨档期权件(q<1,W469
    已实测死法)不计。"""
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    from sr_od.application.currency_war.cw_deploy_logic import (
        TRANSITION_TRAITS,
        engines_count,
    )
    ch = CHARACTERS.get(name)
    if ch is None:
        return False
    bonds = set(ch.factions or ()) | set(ch.flows or ())
    fac = dict(state.board or {})
    if not (bonds & {b for b, _t in TRANSITION_TRAITS}):
        return False
    dep_names = {d.char_id for d in (state.deployed or []) if d is not None}
    before = engines_count(fac, dep_names)
    for b in bonds:
        fac[b] = fac.get(b, 0) + 1
    after = engines_count(fac, dep_names)
    return after > before


def _scan_shop_buy_accounts(state: GameState,
                            registry: DecisionV2Registry,
                            ) -> tuple[list[int], list[int]]:
    """店内件两路账单单次扫描(防双计;调用方按需取路)。

    - countable:非期权正账件费用(A-1 刀法:当帧跨档 ∪ 3合1 合成,
      合成件不占槽);
    - fill:O1 备战空位填补件费用(其余件;A-2 同一槽位账——槽位
      先扣跨档件已占数,满槽后不再扩账);升序返回(容量口径取最便宜
      k 件=保守侧,买入质量序在 candidates/scoring 放行面)。
    """
    from sr_od.application.currency_war.cw_state import (
        bench_occupied,
        will_merge_on_buy,
    )
    costs: list[int] = []
    fill: list[int] = []
    bench_free = max(0, registry.bench_capacity
                     - bench_occupied(state.bench or []))
    for sc in (state.shop or []):
        name = getattr(sc, 'name', '') or ''
        if not name:
            continue
        merge = will_merge_on_buy(sc, state.bench, state.deployed)
        if merge:
            costs.append(sc.cost or 3)   # 合成件不占槽
            continue
        if bench_free <= 0:
            continue    # A-1/A-2:未跨档期权件与满槽帧均不扩账
        bench_free -= 1
        if _crosses_engine_tier(state, name):
            costs.append(sc.cost or 3)
        else:
            fill.append(sc.cost or 3)
    fill.sort()
    return costs, fill


def _countable_buy_costs(state: GameState, session: StrategySession | None,
                         registry: DecisionV2Registry) -> list[int]:
    """店内「非期权」正账件费用表(A-1 刀法)。

    countable = ①当帧跨档完成件(买入后四体系达成数 +1)∪ ②3合1
    合成件(买入即 2★ 完成,价值在星级阶梯非板面差分)。原配对信号
    (ADR-0446)退回后,跨档判定改本结构性口径——语义与 S1/S2 的
    「当帧跨档」同一集合(信号判定的核心即此跨档事实)。
    """
    return _scan_shop_buy_accounts(state, registry)[0]


def bench_fill_account(state: GameState, registry: DecisionV2Registry) -> int:
    """O1 备战空位填补通道的容量分量(W611 设计 §1.2/§1.3)。

    溢余帧备战有空位时,店内其余件(非跨档非合成)按费用升序取「剩余
    空槽」件的费用和计入 C_t——义务在「无目标帧」的容量不再结构性为
    0(局20/局23 支出冻结的根:comp 空→正 EV 帧空→C_t=0→义务恒 0)。
    数学依据=设计 §1.3:溢余段买 1★ 退全款+利息不减(息帽截断),
    已实现成本 0、收益≥0(压库+bench 期权),弱占优、参数无关。
    买入放行面([31] 限域质量序)在 candidates/scoring,随 W607 二波
    后接线;本分量先接通 flip/义务预算的容量判定与存息准入门。
    """
    return sum(_scan_shop_buy_accounts(state, registry)[1])


def channel_capacity(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry) -> int:
    """C_t = 升级计划费 + 非期权可买账 + 刷价×刷新预算。

    刷新分量取 ``refresh_ev_budget`` 预算式(查表核单一址,批 3 预算
    收权;合法 0 帧契约见该函数 docstring)。
    """
    total = 0
    if schedule_upgrade(state, session):
        total += upgrade_plan_fee(state)
    total += sum(_countable_buy_costs(state, session, registry))
    total += bench_fill_account(state, registry)
    rolls = refresh_ev_budget(state, session)
    total += (state.shop_refresh_cost or 2) * rolls
    return total


def obligation(state: GameState, session: StrategySession,
               registry: DecisionV2Registry) -> int:
    """义务花销 f = min((g − R*)+, C_t)(设计 §1.4;0=无义务)。"""
    r = overflow(state, session, registry)
    if r <= 0:
        return 0
    return min(r, channel_capacity(state, session, registry))


def tier_truncated_spend(gold: int, want: int, essential: bool) -> int:
    """溢余消费的息档边界截断(纯金额;W645 提案 E-v2)。

    利息 = gold//10 cap 5,按节点结算,当轮息损 = interest(轮初金) −
    interest(轮末金),首末金量的纯函数、路径无关 → 花后不跨 10 的倍数
    档则息损 0(P13/[11] 同档零息损)。本函数按「息档结构直接输出
    ``gold % 10``」截断非必要溢余支出金额,零标定参数(数学先行硬门的
    合格形态)。

    - essential=True → 不截断,原样返回 want。两枝由消费点显式分类:
      ①正账件(跨档/合成件,买账已过 scoring 单一裁决面)——一张牌
      不可拆,截断即弃购,弃购代价归 P1 再遇窗口口径,不在本函数辖内;
      ②M-A 定向刷新车道(arbiter 定向授权分支,directed_refresh_budget,
      P1 末窗/boss 窗)——末窗没有下轮重摇,截断后残差不足一刷 = 定向
      搜索永久丢失,截断代价是无穷大而非「推迟一轮」,弱占优前提对该
      车道为假。函数自身不判车道(车道判定单一址留在 arbiter 分支结构)。
    - essential=False(常态刷新逐笔、release 预算内的负分搜索等非必要
      溢余支出)→ 截断为 min(want, gold % 10):花后不跨息档,息损 0;
      不花的余量结转下轮(义务逐帧重算,R* 与 C_t 下帧重出,结转零成本、
      不产生第二义务)。

    调用契约:返回值 < want = 本笔不放行(消费不可拆,不花部分金额,
    也不替调用方改写金额)——截断只裁「可不可花满」,放行裁决仍在既有
    预算门(authorize_release_refresh 等);量级按严口径 1 金/档报
    1-2 金/局,主判如实降级「方向披露」(提案 E-v2 §2 量级双口径)。
    """
    if essential:
        return want
    return min(want, gold % 10)
