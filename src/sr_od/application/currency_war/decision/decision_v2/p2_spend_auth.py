"""位面 2 支出授权(W757 v2 设计落码;决策 why=ADR-0480)。

设计对象(W754 立案 B):P2 板面冻结在过渡形态、带金血崩死、血线恶化
无支出响应、锁线后目标核心卡不买——**授权/执行层缺「何时必须花钱 /
花在哪」的判据路径**。本模块 = 该授权的谓词与预算带单一源,消费点在
arbiter 的金地板/息账门(门开不开+预算上界),候选生成与评分公式零触碰
(P12 j=0 负例、升级三合法判据、血预算停手族全部既有单一源不动)。

**授权辖域声明(非动作互斥执行序)**:同一授权帧内多类动作各自按自己
的判据独立过门,不存在「先花完优先级 1 才轮到 2」的串行读法(设计件
v2 §3.2 序语义声明;W758 面2 攻击 A 封口)。

四条件合取(缺一不授权;设计件 v2 §3.1):

- T1 线锁定:``session.v3_intention`` 的 locked 位——该位本身是经 P16
  滞回(θ 滞回+D_min,registry.line_switch_*)后的 v3 状态机输出,本
  模块消费它即天然满足「禁接滞回前原始意向位」(W758 面3 攻击 D 残余
  缝隙封口;摇摆域辖锁定判据振荡,与本授权在锁定状态位上机械切分);
- T2 形态缺口:``phase.form_ok`` 锁定线分支为假——stage_transitions Q5
  口径(本线核心羁绊 ≥2 档 ∧ carry 2★ 在板)映射到既有单一源判据,
  不立第二口径(缺口=「有边际价值高的花处」[17] 的可计算化);
- T3 血线恶化(报警面,非单变量触发器):近 N_fail 个战斗节点连败
  (带符号 streak 单一源)∨ hp ≤ P2 警戒带(**占位=P1 出口血目标线**
  registry.p1_exit_blood_target,待标定);
- T4 金水位:g ≥ 息线单一源(interest_floor 派生,[17]/P13;W758 攻击 A
  实反例封口:边界点取 ≥,逐点账进 P25 分带核验)。

两层强度(同一触发骨架):

- 常授权层(T1∧T2∧T4;T3 无关——溢余即花节点无关):买牌预算地板
  =「花完仍 ≥50」(P5 预算前提的买牌推广);贴线带(花完 ∈ [45,50))
  逐点判是 P25 待证项,**证成前保守=不买**(设计占位子句,不做生产
  决策);破息带(花完 <45)常授权层不进,只走加急层;
- 加急层(常授权层 ∧ T3;[18] 止损落点):允许破息买入授权目标/定向
  D,下限=保留金占位(registry.p2_spend_auth_reserve_floor);升级仍禁
  (本模块不产生也不放宽任何 LevelUp;血预算停升级线/P21 既有谓词照常
  AND 辖)。

交界(设计件 v2 §3.3,全部显式):

- 分配器接管帧(v6 active,``allocator.alloc_domain`` 现值)内授权禁
  出手——帧归属二选一,不并存(单帧锁⑨);「大额」边界随之机械化,
  授权通道自身不设金额档;
- 位面末窗(boss 窗,discipline.boss_window_active 统一口径)归既有
  ALL IN/降格族,授权不触发(单帧锁⑦);
- 覆盖纪律态(应急/war)优先:授权不越权改它们的地板(与 arbiter
  既有豁免臂同款辖域边界);
- C1 溢余必花:P1 侧通道,位面切分无同帧交集;本模块是其「定向、
  预算上界」形状在 P2 中段的泛化,不平行新开金额档。

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

#: 授权买侧候选标签集(优先级 2「凑档件与压库件」的辖域映射;[34]
#: 购买序三层语义由候选/评分既有通道承载,本集只定「哪些买候选在授权
#: 门与预算带的辖域内」)。= remedy_buy_tags 去 engine_seed/carry_gate:
#: engine_seed 是 P1 过渡引擎语义非 P2 授权目标;carry_gate 腾位买有
#: 独立门。定向 D(RefreshShop)不经标签集(全刷新候选辖)。
P2_AUTH_BUY_TAGS: frozenset[str] = frozenset({
    'line_carry', 'line_opportunistic', 'bridge_core', 'plugin',
    'copy_press',
})


@dataclass
class P2SpendAuth:
    """授权帧快照(每帧一次派生;纯观测判据,无跨轮状态)。"""

    urgent: bool = False       # True=加急授权层(T3 命中);False=常授权层
    #: 判读注记(T1-T4 命中明细;「为什么授权/哪一层」可复算)
    notes: dict = field(default_factory=dict)


def p2_spend_auth_frame(state: GameState, session: StrategySession,
                        registry: DecisionV2Registry) -> P2SpendAuth | None:
    """授权辖域判定(T1∧T2∧T4 合取;None=本帧不授权,零行为)。

    纯函数,每消费点现算(派生量模式,同 phase.form_ok;session 丢失
    → 下帧现算,天然免疫)。返回 None 的帧一切既有裁决不变。
    """
    if not registry.p2_spend_auth_enabled:
        return None
    # 辖域:plane==2(P3 扩辖不在本批);末窗/覆盖纪律态归既有族。
    if state.plane != 2:
        return None
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        boss_window_active,
    )
    from sr_od.application.currency_war.decision.decision_v2.filters import (
        current_mode,
        is_emergency,
    )
    if is_emergency(state, registry) \
            or boss_window_active(state, session, registry) \
            or current_mode(session) != 'economy':
        return None
    # T1:线锁定(P16 滞回后 v3 状态机位;见模块 docstring)。
    ist = getattr(session, 'v3_intention', None)
    if getattr(ist, 'phase', '') != 'locked' \
            or not getattr(ist, 'locked_comp', ''):
        return None
    # T2:形态缺口(锁定线 form_ok 单一源取反;Q5 口径映射见模块头)。
    from sr_od.application.currency_war.decision.decision_v2.phase import (
        form_ok,
    )
    if form_ok(state, session, registry):
        return None
    # T4:金水位 g ≥ 息线(边界点取 ≥,W758 攻击 A 实反例封口)。
    if (state.gold or 0) < registry.interest_floor():
        return None
    # 交界⑨:分配器接管帧(v6 active)授权禁出手——帧归属二选一。
    from sr_od.application.currency_war.decision.decision_v2.allocator import (
        alloc_domain,
    )
    if alloc_domain(state, session, registry) is not None:
        return None
    # T3:血线恶化(报警面;连败口径=带符号 streak 单一源;hp 占位
    # 警戒带按可信位守卫——兜底 100 帧不作报警依据,ADR-0282 口径)。
    loss_streak = max(0, -(state.streak or 0))
    hp_alert = ((state.hp_readable or state.hp_trusted)
                and state.hp <= registry.p1_exit_blood_target)
    urgent = loss_streak >= registry.p2_spend_auth_fail_streak_n or hp_alert
    return P2SpendAuth(urgent=urgent, notes={
        'loss_streak': loss_streak, 'hp_alert': hp_alert,
        'hp': state.hp, 'gold': state.gold,
    })


def _budget_band_ok(auth: P2SpendAuth, working_gold: int, cost: int,
                    registry: DecisionV2Registry) -> bool:
    """单笔花费是否落在当前授权层预算带内(层强度唯一裁决点)。

    - 常授权层:花完仍 ≥ 息线(P5 前提推广);贴线带 [45,息线) 为
      P25 待证占位——证成前保守=不买(不做生产决策);破息带不进;
    - 加急层:花完 ≥ 保留金占位下限([18] 止损机械化)。
    """
    after = working_gold - cost
    if auth.urgent:
        return after >= registry.p2_spend_auth_reserve_floor
    return after >= registry.interest_floor()


def p2_spend_auth_spend_authorized(cand, working: GameState,
                                   state: GameState,
                                   session: StrategySession,
                                   registry: DecisionV2Registry,
                                   auth_trace: dict | None = None) -> bool:
    """arbiter 门侧消费:本笔花费(BuyCard/RefreshShop)是否授权放行。

    辖域内=授权目标买(标签集 P2_AUTH_BUY_TAGS ∪ 核心名)与定向刷新
    (RefreshShop 全辖);升级(LevelUp)永不在辖——授权不放宽升级。
    预算带按当前授权层裁决(见 ``_budget_band_ok``);授权帧本身为
    None(开关关/条件不合/接管帧/末窗)时恒 False=零行为。
    """
    auth = p2_spend_auth_frame(state, session, registry)
    if auth is None:
        return False
    a = getattr(cand, 'action', cand)
    from sr_od.application.currency_war.kernel.cw_state import LevelUp
    if isinstance(a, LevelUp):   # 升级永不在辖:授权不放宽升级(P21/ADR-0448)
        return False
    if isinstance(a, BuyCard):
        in_scope = (getattr(a.card, 'name', '') in _core_names(session)
                    or getattr(cand, 'tag', '') in P2_AUTH_BUY_TAGS)
    elif isinstance(a, RefreshShop):
        in_scope = True   # 定向 D 全辖(评分 V_D 批账不动,j=0 负例保持)
    else:
        return False
    if not in_scope:
        return False
    cost = int(getattr(a, 'cost', 0) or (a.card.cost if isinstance(a, BuyCard)
                                         else 2) or 0)
    if cost <= 0 or not _budget_band_ok(auth, working.gold or 0, cost,
                                        registry):
        return False
    if auth_trace is not None:
        auth_trace['p2_spend_auth'] = (
            f"{'加急' if auth.urgent else '常授权'}层放行"
            f'(金{working.gold}-费{cost};T1-T4 合取;'
            f'连败{auth.notes["loss_streak"]}/hp报警{auth.notes["hp_alert"]})')
    return True


def p2_spend_auth_core_must_buy(cand, working: GameState, state: GameState,
                                session: StrategySession,
                                registry: DecisionV2Registry) -> bool:
    """优先级 1 必买判定(非正分门豁免消费;[31]② 唯一最高优先级)。

    授权帧 ∧ 核心卡在店 ∧ 预算带内 → 该买候选越过非正分门进入约束链
    (豁免≠无条件采纳:金/槽/copies_cap 约束链与息账门照常辖——常授权
    层地板即息线,interest_rule 对花完仍 ≥50 的买自然放行)。买进
    bench/凑档,不无脑上板([21] 窗口语义,部署管线不动)。
    """
    from sr_od.application.currency_war.kernel.cw_state import BuyCard as _B
    a = getattr(cand, 'action', None)
    if not isinstance(a, _B):
        return False
    if a.card.name not in _core_names(session):
        return False
    auth = p2_spend_auth_frame(state, session, registry)
    if auth is None:
        return False
    return _budget_band_ok(auth, working.gold or 0, a.card.cost or 3,
                           registry)


def _core_names(session: StrategySession) -> set[str]:
    """意向核心名集(candidates._core_names 单一源转发,防循环导入)。"""
    from sr_od.application.currency_war.decision.decision_v2.candidates import (
        _core_names as _names,
    )
    return _names(session)
