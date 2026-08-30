"""支出门(买侧收门,W829 v3 设计落码;策略开关生命周期第 1 态)。

设计单一源 = ``.debug/temp/currency_war/w829_spend_gate_design/REPORT.md``
v3(§1.4 判据形式化 / §3 落码规格 / §4 辖界切分);开臂判据挂账 = 同目录
``PREREG_v4.md``(判前锁,冻结后生效;禁悬置默认关)。

门的本体语义 = 收门(ADR-0434 同族范式从升级/刷新侧扩展到买侧):对
评分-仲裁管线产出的正分 BuyCard 候选,加逐笔可复算的「不许花」否决
谓词——不开源、不设预算、不授权、不分配,否决空转是合法态(与
ADR-0492 删除的正授权器分属两类机制,W801 类型错配定谳不波及本形态)。
全部拒因在 registry.spend_gate_enabled(伞)及对应子旗标同时为真时才
产生——默认关 = 零漂移锚(生产默认行为不变)。

三条判据独立否决,任一命中且无豁免 → 拒(设计 §1.4):
- D1 息线臂(子旗标 spend_gate_interest_enabled):真破息(花后金 <
  息线 ∧ ⌊gold/10⌋ 下降;⌊·⌋ 不变 = 零息损不拦,ADR-0434 E3 同款)
  → 拒,豁免 = E-a 合成完备 / E-b 锁定线缺档成员∧非应急带 / E-c
  人口位(门不辖升级,仅对齐登记);
- D2 血线臂(无独立旗标,随伞;消费既有血线常量单一源,零新状态源):
  hp < 血线报警线(预警带)豁免面 = 当轮可上场 ∨ 压库 ∨ E-b;
  hp ≤ 应急线(应急带)收窄 = 当轮可上场 ∨ E-b(压库禁——血紧时压库
  是奢侈品,W774⑤ v2 显式取舍);
- D3 位置臂(子旗标 spend_gate_bench_enabled):bench 占用 ≥ 容量−1
  → 拒非(E-a ∪ 当轮可部署)买入;挤占判据单一实现 = 本模块
  ``bench_front_full``(P29 评分加项消费同一函数,禁第二处)。

辖界切分(设计 §4,禁第二分配器/第二授权器):
- W802 κ 通道 = 评分层改序,本门 = 可买性层过滤,不接手线外缺口;
- P29 决定「值多少分」,本门决定「买不买得出」;E-b 缺件判定引同一
  ``missing_members`` 单一源但**不引用 P29 项**(v3 内联解耦,修
  攻击 B 的循环豁免:门只看「缺档成员∧血带」,与 P29 反向锁分属
  两层,判据各自内联);
- R_min 门不消费(血-R 组合辖域只由 P29 反向锁辖于评分层);
- merge 完成豁免通道(ADR-0437/0438)在前,E-a 让位(防复活
  「非正分门拒」断点 ③-a);
- ADR-0474 分配器接管帧(d2_entry_frame 单一源)门整体让位;
- boss 窗让位(W774⑤ 血线三带「boss 窗与末窗让位仲裁」同语义);
  末窗 ADR-0451 降格独占帧门不新增放行(本门无豁免与降格联动,
  无代码面,锁面见测试仓);
- 金地板/copies_cap/bench 容量等既有约束链守卫**先到先记**(本门
  在 constraints 序末尾):守卫已拒的候选门不再求值、不产生门拒因;
  d3_bench 仅记「既有 bench 容量守卫未拒(未满栏)但门按前瞻拒」,
  G4 分项读数取纯 d3_bench 计数,与守卫计数零混账(设计 §3.2)。

逐笔金推进宿主核验结论(设计 §3.2 spike):arbiter.arbitrate 采纳
处 ``working = simulate(working, action)`` 逐笔推进金/bench——门读
``working``(前序采纳后状态)即得「花后金/前瞻占用」,门求值序 =
仲裁序(按分排序),拒因回放可复算。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.decision.cw_strategy import StrategySession
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    GameState,
    bench_occupied,
    deployed_occupied,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.decision.decision_v2.remediation import (
        RejectReason,
    )


def _on(registry: DecisionV2Registry, sub: bool) -> bool:
    """伞开关 × 子旗标合取(全部消费点的统一进门判)。"""
    return registry.spend_gate_enabled and sub


def bench_front_full(state: GameState,
                     registry: DecisionV2Registry) -> bool:
    """bench 挤占前瞻判据(占用 ≥ 容量−1)。

    单一实现(设计 §1.4 D3/§3.2):支出门 D3 位置臂与 P29 囤牌加项的
    既有定性门(realization.p29_priority_term)消费同一函数,禁第二处
    ——这是 G4(存活挤席)的直接落点。
    """
    return bench_occupied(state.bench or []) >= registry.bench_capacity - 1


def _missing_names(state: GameState, session: StrategySession,
                   registry: DecisionV2Registry) -> dict[str, float]:
    """锁定线缺档成员清单(missing_members 单一源直判;E-b 不引用 P29 项)。"""
    from sr_od.application.currency_war.decision.decision_v2.realization import (
        missing_members,
    )
    return missing_members(state, session, registry)


def _deploy_free(working: GameState) -> bool:
    """当轮可部署/可上场(转化性判据):有空上阵位。"""
    return deployed_occupied(working.deployed or []) < working.max_units()


def _press_budget_left(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> bool:
    """压库帧内预算余量(只读检查;消耗在采纳处 register_press_buy)。"""
    key = (state.plane, state.round_num)
    if getattr(session, 'v3_sg_press_key', None) != key:
        return True
    return getattr(session, 'v3_sg_press', 0) \
        < registry.tier_push_press_round_cap


def register_press_buy(state: GameState, session: StrategySession) -> None:
    """压库买入采纳计数(帧内 ≤ N 张;轮键惰性重置,ADR-0434 E2 的
    v3_bf_refresh_* 轮内计数同模式——计数在采纳处,评估不预扣)。"""
    key = (state.plane, state.round_num)
    if getattr(session, 'v3_sg_press_key', None) != key:
        session.v3_sg_press_key = key
        session.v3_sg_press = 0
    session.v3_sg_press = getattr(session, 'v3_sg_press', 0) + 1


def _block(state: GameState, session: StrategySession,
           code: str, detail: str) -> RejectReason:
    """拒因产出 + 帧级拒因计数(sess_spend_gate_block 遥测写入面;
    轮键惰性重置,dict[拒因枚举, 次数] 按备战帧快照)。"""
    from sr_od.application.currency_war.decision.decision_v2.remediation import (
        RejectReason,
    )
    key = (state.plane, state.round_num)
    if getattr(session, 'v3_sg_block_key', None) != key:
        session.v3_sg_block_key = key
        session.v3_sg_block = {}
    blocks: dict[str, int] = session.v3_sg_block
    blocks[code] = blocks.get(code, 0) + 1
    return RejectReason('spend_gate', '', 0, f'{code}:{detail}')


def _e_b_exempt(state: GameState, session: StrategySession,
                registry: DecisionV2Registry, name: str) -> bool:
    """E-b:锁定线缺档成员 ∧ 非应急带(hp > emergency_hp)→ 破息放行。

    v3 内联判据(不引用 P29 项):P29 项内含 hp<40 反向锁与 R_min
    条件,借道会构成循环豁免(hp<40 带 E-b 恒死,预警带线内件整段
    拒买)并间接消费 R_min 破坏「血线臂只看 hp 梯度」自约束。hp 不可
    读(None)时不放行(豁免面保守收窄,门管可买性不猜血带)。
    """
    if not name or name not in _missing_names(state, session, registry):
        return False
    return (state.hp is not None
            and state.hp > registry.emergency_hp)


def spend_gate_verdict(cand, working: GameState, state: GameState,
                       session: StrategySession,
                       registry: DecisionV2Registry,
                       auth: dict | None = None) -> RejectReason | None:
    """支出门单候选裁决:通过返回 None,拒返回结构化拒因。

    ``working`` = arbiter 前序采纳动作 simulate 后的工作态(逐笔金
    推进/前瞻占用);``state`` = 帧快照(血带/辖域判定用)。``auth``
    = 授权依据 trace 出口(压库豁免命中记 auth['sg_press'],采纳处
    经 register_press_buy 计数)。
    """
    if not registry.spend_gate_enabled:
        return None
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        boss_window_active,
    )
    from sr_od.application.currency_war.kernel.cw_state import BuyCard
    a = cand.action
    if not isinstance(a, BuyCard) or getattr(cand, 'merge', False):
        return None    # 只辖买侧;E-a 合成完备(merge 候选)门让位
    if boss_window_active(state, session, registry):
        return None    # boss 窗让位(W774⑤ 同仲裁语义)
    from sr_od.application.currency_war.decision.decision_v2.realization import (
        d2_entry_frame,
    )
    if d2_entry_frame(state, registry):
        return None    # ADR-0474 分配器接管帧整体让位(单一分配器)
    name = getattr(getattr(a, 'card', None), 'name', '') or ''
    cost = a.card.cost or 3
    gold = working.gold or 0
    hp = state.hp
    # ---- D3 位置臂 ----
    if _on(registry, registry.spend_gate_bench_enabled) \
            and bench_front_full(working, registry) \
            and not _deploy_free(working):
        occ = bench_occupied(working.bench or [])
        return _block(
            state, session, 'd3_bench',
            f'bench 前瞻挤占(占用{occ}≥容量{registry.bench_capacity}-1,'
            f'非合成∧非当轮可部署拒)')
    # ---- D1 息线臂(真破息:花后 < 息线 ∧ ⌊g/10⌋ 下降)----
    if _on(registry, registry.spend_gate_interest_enabled) \
            and gold - cost < registry.interest_floor() \
            and (gold - cost) // 10 < gold // 10 \
            and not _e_b_exempt(state, session, registry, name):
        return _block(
            state, session, 'd1_interest',
            f'真破息拒(金{gold}-费{cost}→{gold - cost},'
            f'息档{gold // 10}→{(gold - cost) // 10};无兑现路径豁免)')
    # ---- D2 血线臂(随伞,消费血线常量单一源)----
    if hp is not None and hp < registry.blood_margin_low_hp:
        emergency_band = hp <= registry.emergency_hp
        # 转化性(当轮可上场;合成完备 = E-a 已在门入口让位)
        if not _deploy_free(working) and not _e_b_exempt(
                state, session, registry, name):
            if emergency_band:
                return _block(
                    state, session, 'd2_blood',
                    f'应急带(hp{hp}≤{registry.emergency_hp})非转化'
                    f'∧非线内缺档件拒(压库禁)')
            from sr_od.application.currency_war.kernel.cw_intention import (
                locked_buy_scope,
            )
            _scope = locked_buy_scope(_ist(session))
            in_line_scope = bool(name) and _scope is not None \
                and name in _scope
            ch = CHARACTERS.get(name)
            if (ch is not None
                    and (ch.cost or 3) <= registry.tier_push_press_cost_max
                    and not in_line_scope
                    and not getattr(cand, 'needs_slot', False)
                    and _press_budget_left(state, session, registry)):
                # 压库豁免(ADR-0494 操作化单一源,三条件全引:费用
                # ≤ 上界 ∧ 非线内成员 ∧ 帧内 < 上限张;豁免不穿透
                # bench 挤占门——needs_slot 不获豁免,计数在采纳处)
                if auth is not None:
                    auth['sg_press'] = True
                return None
            return _block(
                state, session, 'd2_blood',
                f'预警带(hp{hp}<{registry.blood_margin_low_hp})'
                f'非转化∧非压库∧非线内缺档件拒')
    return None


def _ist(session: StrategySession | None):
    return getattr(session, 'v3_intention', None)
