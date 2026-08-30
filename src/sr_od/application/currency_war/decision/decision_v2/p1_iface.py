"""P1→P2 接口机制 v2(W774 设计落码;决策 why=ADR-0484)。

设计单一源:`.debug/temp/currency_war/w774_p1_interface_design/REPORT.md`(v2)
+ 同目录 `SIM_AB_PREREGISTRATION.md`(v2,单帧锁/拦截枚举/R 族协议)。
病灶(W764):位面 1 阶段没有为位面 2 留接口——锁线摇摆无代价管理、
carry 裸装进硬节点、遭遇裸进、连败溢余金流向不明、血线三带缺判据面。
v2 全部辖 **plane==1**(与 p2_spend_auth 的 plane==2 正交,W774 §4)。

五开关(生命周期第 1 态,strategy-work「策略开关的生命周期」:准入理由=
判据阈值依赖 P26-P28 标定与 A/B;开臂判据挂账=协议 M1-M3+R+G1-G4;
默认关=零漂移锚,off 臂逐位 HEAD):

- ``p1_iface_lockline_v2_enabled``:①锁线 v2——[23] 锚(贯穿件在手即
  锁,cw_intention 信号驱动)是主机制,本模块只补**摇摆代价管理**:
  degrade≥N ∨ 连败≥N 且仍未锁 → FALLBACK 评估;锁前必过**板面一致性
  验证**(候选线与板面交叠成员 ≥ ``p1_iface_board_match_min`` 才锁,
  全不达 → 不锁——锁错不如不锁,错锁会把 P2 搜牌方向钉在板面为零的
  线上)。锁产物 = ``ist.p1_pair``(P1 锁定产物形态,ADR-0357);换线
  精确定义 = 锁定后 p1_pair 变更事件(方向层),ADR-0451 支出降格不
  改 p1_pair、不计入换线(方向层/支出层分层)。降格事件计数是摇摆的
  直接可测信号(p1_directed_downgrade_active 触发面);换线次数降为
  分层读数(session 计数,遥测消费),无 ≤1 上限(v1 循环论证已撤回)。
- ``p1_iface_carry_equip_enabled``:②carry 装备——硬节点备战帧 ∧ 意向
  核心上场 ∧ 0 装备 → 简易非组件件必分配(意向核心优先;消费点=
  ``equip_all`` 过渡期 hold 过滤的 duty 豁免);**禁无接收者的卸装**
  (卖出/弃置致装备回栏闲置;转移合法 ⇔ 接收者=意向线成员 ∨ 接收者
  在场星数 ≥ 被卸者,[24]「装备转移是常态操作」语义保全;操作化只用
  既有 star 字段,不新增评估器)。
- ``p1_iface_hardnode_prep_enabled``:③遭遇备战授权——硬节点备战帧
  ``hp − L_node(rung) < emergency_hp`` → 授权备战支出,**只开门不收门**
  ( arbiter 门侧额外放行,False 即回落既有裁决);金下限=花后金 ≥
  ``rebirth_floor``(低金局不授权);口径边界:`streak_floor_loss_damage`
  是条件败局伤害**均值**,本判据只作触发面不作安全保证(W774 §2③,
  尾部/斜率敏感性挂 P26 采集账)。
- ``p1_iface_lossstreak_flow_enabled``:④连败金流——连败≥2 ∧ 金>息线
  ([17] 息律背书)∧ 意向线 form 缺口 → 溢余段支出候选过 [22]④ 再遇
  账比较式:**当场可上场体系件**授权优先;「不买」仅指**纯散件**
  ([31] 既有硬约束,有出处非自创);本线目标件/稀有件照买照囤([21]/
  [13] 正常行为,不在此拦);等级仅 [33] 人口位例外(本通道对 LevelUp
  恒不授权,升级账归 ev.levelup_ev_authorized 单一裁决)。
- ``p1_iface_blood_bands_enabled``:⑤血线三带——预警带 hp<40([18]
  「卖血不低于 40」质量线直引,单一源=``discipline.BLOOD_MARGIN_LOW_
  HP``)禁纯囤件买入(对象=非转化 ∧ 非压库 ∧ 非本线目标件);应急带
  hp≤``emergency_hp`` 只放行当轮可转化(上场/合成)与本线目标件——
  **压库在应急带维持禁**(显式取舍:血紧时压库是奢侈品,W774 §2⑤
  声明);boss 窗与 ALL IN 窗既有行为零触碰(豁免面)。

横切裁决(W774 §5 写死):
- **同帧优先序**:⑤禁令 > ④排序 > ③授权(拦截枚举/仲裁序同序);
- **末窗让位仲裁**:末窗(r≥handoff_gate_min_round)∧ p1_exit_blood_
  short → ADR-0451 降格独占,③④在该帧不触发(⑤禁令属收门面保留);
- **①一致性门为②③④输入前置**:意向线与板面交叠不足的帧②③④宁可
  漏触发(验证失败→不触发),不错花(协议锁⑥「门零泄漏」)。

出手率红线 R 族(协议 §3)是 A/B 判定线(50%),**不进决策代码**;
telemetry 面 = ``session.v3_p1_iface_intercept`` 拦截枚举(decide_prep
每帧写,决策迹统一接出)+ 仲裁拒绝计数 ``session.v3_p1_iface_blocks``。
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
    LevelUp,
    SellBench,
)

#: 拦截枚举优先序(W774 §5-1:⑤>④>③;①门失败与末窗降格先于三者;
#: carry_frame=②硬节点帧触发面记录)。
_INTERCEPT_PRIORITY: tuple[str, ...] = (
    'downgrade_window', 'no_consistency',
    'blood_warn', 'blood_emergency', 'lossstreak_flow', 'hardnode_prep',
    'carry_frame',
)


@dataclass
class P1IfaceAuth:
    """接口帧快照(每帧一次派生;纯观测判据,无跨轮状态)。

    ``hardnode_prep``/``lossstreak_flow`` = ③④授权面;``blood_band``
    = ⑤带位(''|'warn'|'emergency');``carry_frame`` = ②硬节点帧触发
    面(分配义务/卸装禁令的辖域帧);``consistency_ok`` = ①板面一致
    性门读数(②③④输入前置);``notes`` 带命中位与判读锚点(拦截面
    审计数据源,协议 M3/R 族分层消费)。
    """

    hardnode_prep: bool = False
    lossstreak_flow: bool = False
    blood_band: str = ''
    carry_frame: bool = False
    consistency_ok: bool = False
    notes: dict = field(default_factory=dict)


def _owned_chars(state: GameState) -> set[str]:
    """已到手角色名(bench+deployed;cw_intention 同口径转发)。"""
    from sr_od.application.currency_war.kernel.cw_intention import (
        _owned_chars as _fn,
    )
    return _fn(state)


def intent_member_scope(state: GameState,
                        session: StrategySession) -> frozenset[str]:
    """意向线成员名集(①一致性门的判定域)。

    = ``p1_pair`` ∪ ``transition_pair`` 体系成员 ∪ 锁定 comp 采购集
    (``locked_buy_scope`` 同口径的成员版;空 = 未锁空窗帧,一致性
    判 False——门语义是「意向线与板面匹配」,无线可匹配即失败)。
    """
    from sr_od.application.currency_war.kernel.cw_intention import (
        _line_hoard,
        _pair_members,
        get_comp,
    )
    ist = getattr(session, 'v3_intention', None)
    if ist is None:
        return frozenset()
    scope: set[str] = set()
    for pair in (tuple(getattr(ist, 'p1_pair', ()) or ()),
                 tuple(getattr(ist, 'transition_pair', ()) or ())):
        if pair:
            scope |= _pair_members(pair)
    if getattr(ist, 'phase', '') == 'locked' \
            and getattr(ist, 'locked_comp', ''):
        comp = get_comp(ist.locked_comp)
        if comp is not None:
            scope |= _line_hoard(comp)[0]
    return frozenset(scope)


def board_consistency_ok(state: GameState, session: StrategySession,
                         registry: DecisionV2Registry) -> bool:
    """①板面一致性验证(②③④输入前置门;FALLBACK 锁前验证同式)。

    意向线成员与板面(bench+deployed)交叠 ≥
    ``registry.p1_iface_board_match_min``(新设阈=transition_combos 各
    体系最低激活档 2-3 人的下界,挂 A/B M3 质量维标定;W774 §2①)。
    """
    scope = intent_member_scope(state, session)
    if not scope:
        return False
    return len(scope & _owned_chars(state)) \
        >= registry.p1_iface_board_match_min


# ===== ① 锁线 v2(摇摆代价门 + FALLBACK 板面一致性锁)=====


def p1_iface_lockline_update(state: GameState,
                             ist,   # IntentionState(kernel;参数不注型防环)
                             session: StrategySession,
                             registry: DecisionV2Registry) -> None:
    """①锁线 v2 后处理(update_target 在 update_intention 之后消费)。

    - 开关关 / 非 P1 / comp 已锁([23] 锚是主机制,信号驱动优先)/
      降格终局:零行为(就地返回;comp 锁定帧顺带清 latch——信号锁
      永远优先于 FALLBACK 锁)。
    - **摇摆代价计数**(每 game-round 恰一次,由调用方 key 守卫保证):
      ADR-0451 降格触发面(p1_directed_downgrade_active)False→True 的
      位面内转移计数(直接可测的摇摆信号,W774 §2①)。
    - **FALLBACK 评估**:计数达 ``p1_iface_swing_degrade_n`` ∨ 连败达
      ``p1_iface_swing_loss_n`` 且仍未锁 → 候选线集(p1_early_pair
      派生对 ∪ 兜底对 = ``_P1_PAIR_PREF[:2]``)逐一算板面交叠,交叠
      最大且 ≥ ``p1_iface_board_match_min`` 才锁(写 latch + ist.
      p1_pair);全不达 → 不锁(未锁=方向集空,P2 不被误导)。
    - **锁存续**:latch 非空帧逐轮覆写 ``ist.p1_pair``(update_
      intention 未锁分支每轮重派生会覆盖,闩是锁的持久载体);锁定后
      p1_pair 变更(重派生对 ≠ 闩)计一次换线事件(遥测计数,无上限;
      ADR-0451 降格不改 p1_pair,天然不计入)。
    """
    if not registry.p1_iface_lockline_v2_enabled or state.plane != 1:
        return
    if getattr(ist, 'phase', '') == 'locked' \
            or getattr(ist, 'demoted_endgame', False):
        session.v3_p1_iface_lock_pair = ()
        return
    # 摇摆代价计数(位面内 False→True 转移;键控 by 调用方每轮一次)
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        p1_directed_downgrade_active,
    )
    deg_now = p1_directed_downgrade_active(state, registry, session=session)
    plane = int(state.plane)
    if getattr(session, 'v3_p1_iface_deg_plane', None) != plane:
        session.v3_p1_iface_deg_plane = plane
        session.v3_p1_iface_deg_prev = False
        session.v3_p1_iface_deg_count = 0
    if deg_now and not getattr(session, 'v3_p1_iface_deg_prev', False):
        session.v3_p1_iface_deg_count = \
            getattr(session, 'v3_p1_iface_deg_count', 0) + 1
    session.v3_p1_iface_deg_prev = deg_now

    from sr_od.application.currency_war.kernel.cw_intention import (
        _P1_PAIR_PREF,
        _pair_members,
        p1_early_pair,
    )
    latch = tuple(getattr(session, 'v3_p1_iface_lock_pair', ()) or ())
    if not latch:
        loss_streak = max(0, -(state.streak or 0))
        triggered = (
            getattr(session, 'v3_p1_iface_deg_count', 0)
            >= registry.p1_iface_swing_degrade_n
            or loss_streak >= registry.p1_iface_swing_loss_n)
        if triggered:
            owned = _owned_chars(state)
            cands: list[tuple[str, ...]] = []
            derived = tuple(p1_early_pair(state, ist) or ())
            if derived:
                cands.append(derived)
            fallback = tuple(_P1_PAIR_PREF[:2])
            if fallback not in cands:
                cands.append(fallback)
            best: tuple[tuple[str, ...], int] | None = None
            for pair in cands:
                n = len(set(_pair_members(pair)) & owned)
                if n >= registry.p1_iface_board_match_min \
                        and (best is None or n > best[1]):
                    best = (pair, n)
            if best is not None:
                latch = best[0]
                session.v3_p1_iface_lock_pair = latch
                ist.p1_pair = latch
                ist.last_event = ('p1_iface_lockline:' + '+'.join(latch)
                                  + f'(overlap={best[1]})')
            else:
                # 全不达 → 不锁:未锁=合法探索,方向集空(W774 §2①;
                # 错锁=把 P2 搜牌方向钉在板面为零的线上,更糟)
                ist.last_event = 'p1_iface_lockline:no_match'
    if latch:
        prev = tuple(getattr(session, 'v3_p1_iface_locked_pair_prev', ())
                     or ())
        if prev and tuple(ist.p1_pair or ()) != prev \
                and tuple(ist.p1_pair or ()) == latch:
            # 换线事件(方向层;遥测计数,无 ≤1 上限——v1 循环论证撤回)
            session.v3_p1_iface_switch_count = \
                getattr(session, 'v3_p1_iface_switch_count', 0) + 1
        if tuple(ist.p1_pair or ()) != latch:
            ist.p1_pair = latch
            ist.last_event = 'p1_iface_lockline:hold'
        session.v3_p1_iface_locked_pair_prev = latch


# ===== ③ L_node(硬节点条件败局均值;口径边界见模块 docstring)=====


def hard_node_loss(state: GameState, session: StrategySession,
                   registry: DecisionV2Registry) -> float:
    """硬节点条件败局伤害均值 L_node(rung)。

    单一源转发:encounter/boss = ``streak_floor_loss_damage[kind]``
    截距+斜率×rung;battle 类 = ``vd_p1_loss_*``;rung 坐标 =
    ``scoring._engines_formed`` 0-2 钳制(discipline.terminal_survival_
    upper_bound 同式,禁第二份拟合)。**均值代生存尾部**——只作触发
    面,不作安全保证(W774 §2③ 口径边界声明)。
    """
    from sr_od.application.currency_war.decision.decision_v2.scoring import (
        _engines_formed,
    )
    rung = min(2, max(0, _engines_formed(state, registry)))
    node = (getattr(session, 'node_type_current', None)
            or state.node_type or '')
    if node in ('encounter', '遭遇'):
        intercept, slope = registry.streak_floor_loss_damage['encounter']
        return max(0.0, intercept + slope * rung)
    if node == 'boss':
        intercept, slope = registry.streak_floor_loss_damage['boss']
        return max(0.0, intercept + slope * rung)
    return max(0.0, registry.vd_p1_loss_intercept
               + registry.vd_p1_loss_slope_rung * rung)


# ===== 帧判定(③④⑤ + ①门 + 末窗仲裁)=====


def p1_iface_frame(state: GameState, session: StrategySession,
                   registry: DecisionV2Registry
                   ) -> tuple[P1IfaceAuth | None, str]:
    """帧判定核(帧/拦截原因二元组;frame 与 intercept 同一推导)。

    返回 ``(None, 原因)`` = 本帧不触发零行为;原因枚举(telemetry 面
    ``v3_p1_iface_intercept``;off/非 P1 = ''):
    'downgrade_window'(末窗降格独占帧,③④让位 ADR-0451)/
    'no_consistency'(①门失败,②③④不触发=锁⑥)/ 触发面按优先序
    ⑤>④>③ '+' 连接(blood_warn/blood_emergency/lossstreak_flow/
    hardnode_prep)。
    """
    switches_on = (registry.p1_iface_hardnode_prep_enabled
                   or registry.p1_iface_lossstreak_flow_enabled
                   or registry.p1_iface_blood_bands_enabled
                   or registry.p1_iface_carry_equip_enabled)
    if not switches_on or state.plane != 1:
        return None, ''
    # 末窗让位仲裁(W774 §5-2):降格独占帧,加支出方向(③④)不触发
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        p1_directed_downgrade_active,
    )
    downgrade = p1_directed_downgrade_active(state, registry, session=session)
    cons = board_consistency_ok(state, session, registry)
    auth = P1IfaceAuth(consistency_ok=cons)
    if downgrade:
        return None, 'downgrade_window'
    # ⑤ 血线三带(hp 可信位守卫:兜底 100 帧不作血线判据,ADR-0282 口径)
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        BLOOD_MARGIN_LOW_HP,
        hp_decision_trusted,
    )
    if registry.p1_iface_blood_bands_enabled and hp_decision_trusted(state):
        if state.hp <= registry.emergency_hp:
            auth.blood_band = 'emergency'
        elif state.hp < BLOOD_MARGIN_LOW_HP:
            auth.blood_band = 'warn'
    # ③ 遭遇备战(硬节点帧 ∧ 水位判据 ∧ ①门)
    if registry.p1_iface_hardnode_prep_enabled and cons:
        from sr_od.application.currency_war.decision.decision_v2.discipline import (
            _hard_node,
        )
        if _hard_node(state, session) \
                and (state.hp - hard_node_loss(state, session, registry)
                     < registry.emergency_hp):
            auth.hardnode_prep = True
    # ④ 连败金流(连败≥2 ∧ 溢余段 ∧ form 缺口 ∧ ①门;[17] 息律背书)
    if registry.p1_iface_lossstreak_flow_enabled and cons:
        loss_streak = max(0, -(state.streak or 0))
        from sr_od.application.currency_war.decision.decision_v2.phase import (
            form_ok,
        )
        if loss_streak >= 2 \
                and (state.gold or 0) > registry.interest_floor() \
                and not form_ok(state, session, registry):
            auth.lossstreak_flow = True
    # ② 硬节点帧触发面(分配义务/卸装禁令辖域;①门前置,锁⑥同辖)
    if registry.p1_iface_carry_equip_enabled and cons:
        from sr_od.application.currency_war.decision.decision_v2.discipline import (  # noqa: E501
            _hard_node,
        )
        if _hard_node(state, session):
            auth.carry_frame = True
    hit = [k for k, v in (('blood_emergency',
                           auth.blood_band == 'emergency'),
                          ('blood_warn', auth.blood_band == 'warn'),
                          ('lossstreak_flow', auth.lossstreak_flow),
                          ('hardnode_prep', auth.hardnode_prep),
                          ('carry_frame', auth.carry_frame)) if v]
    if not hit:
        if not cons:
            return None, 'no_consistency'
        return None, ''
    auth.notes = {
        'consistency_ok': cons, 'hp': state.hp, 'gold': state.gold,
        'streak': state.streak,
        'L_node': round(hard_node_loss(state, session, registry), 2),
    }
    return auth, '+'.join(sorted(hit, key=_INTERCEPT_PRIORITY.index))


def p1_iface_intercept(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> str:
    """拦截枚举(telemetry 面;纯观测零决策行为,decide_prep 每帧写)。"""
    return p1_iface_frame(state, session, registry)[1]


# ===== 门侧消费(③④ 只开门;⑤④ + ②卸装禁令 收门面)=====


def _action_of(cand) -> object:
    return getattr(cand, 'action', cand)


def _convertible_now(working: GameState, session: StrategySession,
                     a: BuyCard) -> bool:
    """当轮可转化(⑤豁免面/④「当场可上场」共用口径):买入即合成
    (``merge_buy_completes`` 单一源)∨ 上阵未满可上场。"""
    from sr_od.application.currency_war.kernel.cw_state import (
        deployed_occupied,
        merge_buy_completes,
    )
    if merge_buy_completes(a.card.name, a.card.star or 1,
                           working.bench, working.deployed, working.shop):
        return True
    return deployed_occupied(working.deployed or []) < working.max_units()


def p1_iface_spend_authorized(cand, working: GameState, state: GameState,
                              session: StrategySession,
                              registry: DecisionV2Registry,
                              auth_trace: dict | None = None) -> bool:
    """arbiter 门侧消费:③④授权帧内本笔花费是否**额外放行**。

    「只开门不收门」(p2_spend_auth 同纪律):False 即回落既有裁决,
    既有门放行的笔授权不拒、拒绝的笔授权不改判。升级(LevelUp)恒不
    在辖(④等级仅 [33] 例外,升级账归 ev 单一裁决)。授权面:
    - ③ 硬节点备战:花后金 ≥ ``rebirth_floor``([18];低金局不授权)
      的买/定向刷新放行;
    - ④ 连败金流:**当场可上场体系件**(``_cand_system_bonds`` 非空 ∧
      ``_convertible_now``)买放行;纯散件不放行(收门面在
      ``p1_iface_gate_blocked``,此处只不开门)。
    """
    auth, _ = p1_iface_frame(state, session, registry)
    if auth is None:
        return False
    a = _action_of(cand)
    if isinstance(a, LevelUp):
        return False
    if isinstance(a, BuyCard):
        cost = int(a.card.cost or 3)
    else:
        cost = int(getattr(a, 'cost', 0) or 0)
    if cost <= 0:
        return False
    if auth.hardnode_prep \
            and (working.gold or 0) - cost >= registry.rebirth_floor:
        if auth_trace is not None:
            auth_trace['p1_iface'] = (
                f'硬节点备战授权(金{working.gold}-费{cost}'
                f'≥rebirth_floor{registry.rebirth_floor};hp{state.hp})')
        return True
    if auth.lossstreak_flow and isinstance(a, BuyCard):
        from sr_od.application.currency_war.decision.decision_v2.scoring import (
            _cand_system_bonds,
        )
        if _cand_system_bonds(cand) and _convertible_now(working, session, a):
            if auth_trace is not None:
                auth_trace['p1_iface'] = (
                    f'连败金流授权(当场可上场体系件 {a.card.name};'
                    f'金{working.gold}/连败{max(0, -(state.streak or 0))})')
            return True
    return False


def p1_iface_gate_blocked(cand, working: GameState, state: GameState,
                          session: StrategySession,
                          registry: DecisionV2Registry) -> str | None:
    """收门面(约束 'p1_iface_gate' 消费;开关关/非辖帧恒 None)。

    - ⑤ 预警带(hp<40):禁「非转化 ∧ 非压库 ∧ 非本线目标件」买入
      ([18] 质量线直引);压库豁免 = 候选 tag ``copy_press``([34]①
      费用档语义的既有标签单一源);本线目标件豁免 =
      ``intent_member_scope`` 成员([21]/[13] 正常行为不拦)。
    - ⑤ 应急带(hp≤emergency_hp):只放行当轮可转化与本线目标件;
      **压库不豁免**(显式取舍:血紧时压库是奢侈品,W774 §2⑤)。
    - ④ 触发帧:纯散件(``_cand_system_bonds`` 空)买入拒([31] 既有
      硬约束「不为凑数羁绊花金 D 牌」;[22]④ 再遇账的「不买」面)。
    - ② 卸装禁令:卖出**带装备**角色且无合格接收者(意向线成员 ∨
      在场星数 ≥ 被卸者,[24])→ 拒(装备回栏闲置=无接收者卸装)。
    - boss 窗 / 位面末 ALL IN 窗豁免(既有行为零触碰,[27]/[18])。
    """
    auth, _ = p1_iface_frame(state, session, registry)
    if auth is None:
        return None
    a = _action_of(cand)
    # boss/ALL IN 窗:P 罚最小化投入与清零路径既有语义,本批零触碰
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        boss_window_active,
        plane_last_battle,
    )
    if boss_window_active(state, session, registry) \
            or plane_last_battle(state, session):
        return None
    if isinstance(a, SellBench) and registry.p1_iface_carry_equip_enabled:
        return _unequip_ban_reason(a, working, state, session, registry)
    if not isinstance(a, BuyCard):
        return None
    name = a.card.name
    scope = intent_member_scope(state, session)
    is_target = name in scope
    if auth.blood_band:
        conv = _convertible_now(working, session, a)
        if auth.blood_band == 'warn':
            press = getattr(cand, 'tag', '') == 'copy_press'
            if not (conv or press or is_target):
                return ('预警带禁纯囤件(hp<40 非转化∧非压库∧非本线'
                        f'目标件:{name};[18] 质量线)')
        else:
            if not (conv or is_target):
                return (f'应急带非转化买入拒(hp≤{registry.emergency_hp}:'
                        f'{name};压库不豁免=显式取舍)')
    if auth.lossstreak_flow:
        from sr_od.application.currency_war.decision.decision_v2.scoring import (
            _cand_system_bonds,
        )
        if not _cand_system_bonds(cand) and not is_target:
            return f'连败金流帧纯散件不买({name};[31] 反散件原则)'
    return None


def _unequip_ban_reason(a: SellBench, working: GameState, state: GameState,
                        session: StrategySession,
                        registry: DecisionV2Registry) -> str | None:
    """②禁无接收者的卸装:卖出带装备角色时,须存在合格接收者。

    合格接收者 = 在场(部署位)且(意向线成员 ∨ 在场星数 ≥ 被卸者)
    ([24] 转移常态语义的操作化;只用既有 star 字段)。卖出无装备
    角色不辖(无装备可卸)。"""
    idx = a.bench_idx
    bc = (working.bench[idx] if 0 <= idx < len(working.bench or [])
          else None)
    if bc is None or not getattr(bc, 'char_id', ''):
        return None
    equips = list(getattr(bc, 'equips', None) or [])
    if not equips:
        return None
    scope = intent_member_scope(state, session)
    seller_star = int(getattr(bc, 'star', 1) or 1)
    for d in (working.deployed or []):
        if not getattr(d, 'char_id', ''):
            continue
        if len(list(getattr(d, 'equips', None) or [])) >= 3:
            continue    # 装备上限 3 件,无空槽不是接收者
        if d.char_id in scope or int(getattr(d, 'star', 1) or 1) \
                >= seller_star:
            return None    # 有接收者:转移合法([24])
    return (f'禁无接收者的卸装(卖 {bc.char_id} 带 {len(equips)} 件装备'
            '回栏闲置;[24] 转移语义)')


# ===== ② carry 装备分配义务(equip_all 消费的 duty 谓词)=====


def p1_iface_carry_duty_active(registry: DecisionV2Registry,
                               state: GameState | None,
                               session: StrategySession | None,
                               deployed: list,
                               occupied: dict,
                               wearable_names: list[str]) -> bool:
    """②分配义务:硬节点备战帧 ∧ 意向核心上场 ∧ 0 装备 → True。

    消费点 = ``equip_all`` 过渡期 hold 过滤的 duty 豁免(义务帧全量
    分配,简易非组件件必给核心 ≥1;``equip_allocation`` 的 carry 优先
    序承载「意向核心优先」)。供给面空(owned 无可穿件)→ 调用侧
    ``alloc`` 空自然停,本谓词只表义务(空转率归 R-② 归因输入)。

    ``occupied`` = {(row, slot): [已穿装备名]}(equip_all M7 读数);
    ``wearable_names`` = 当前 owned 可穿面(供给面判据;非组件过滤由
    调用侧 wearable 口径承载)。
    """
    if not registry.p1_iface_carry_equip_enabled:
        return False
    if state is None or getattr(state, 'plane', 1) != 1:
        return False
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        _hard_node,
    )
    if session is None or not _hard_node(state, session):
        return False
    cores = (getattr(session, 'v3_core_names', None) or set())
    if not cores:
        return False
    for d in (deployed or []):
        cid = getattr(d, 'char_id', '')
        if not cid or cid not in cores:
            continue
        row = getattr(d, 'position_pref', None) or 'back'
        slot = int(getattr(d, 'slot', 1) or 1)
        worn = occupied.get((row, slot)) or []
        if worn:
            continue    # 该核心已穿 → 义务已兑现
        # 供给面空 → False(合法空转,R-② 归因输入);有货 → 义务成立
        return bool(wearable_names)
    return False    # 意向核心未上场:义务不辖
