"""cw4 决策入口(entry 三遍编排 + 帧稳定截断发射器)。

IMPL_DESIGN §6.4-R 步4 / R189-4 结构签名:

    def _emit(turn) -> list[PrepAction]:
        actions += self._mandate_pass(turn)    # 骨架动作流,逐条 mandate=True
        actions += self._criteria_pass(turn)   # EV 追加动作流,mandate=False
        return truncate_frame_stable(actions)  # 帧稳定截断(契约 v2 §3.2)

三遍编排(§3.1):证明 pass → 升档器求值位 → 骨架 pass → EV pass。
ev_arm 模式参数(skeleton_only/full,R1-1)决定 EV 发射面旁路集(§4.2.1)
并写遥测行(bridge 侧)。

truncate_frame_stable 判 = 契约 v2(CONTRACT_SERIES_DECISION.md,2026-09-03
用户批准)§3.2 备战线域 17 类逐类表 + §3.3 fail-closed(词表外/无分类
动作 ⇒ 截断 + 计数披露,禁静默丢弃)。发射器实现期增补条目须回契约
改版,禁只改代码。R196 修复批(症5)对齐:ClickSpheres=条件判(末批
可能掉箱 ⇒ 其后截断)、conditional 五类名-槽一致性复检(推不出即截断,
计数 ``emitter_conditional_truncated``)、BailToOuter=退役·终点(判型
标签对齐契约 §3.2 行,发射行为等价)。

R197 修复批(症1)发射序规格:同一 decide 输出内,EV 卖面
(line_switch_sell/funding_support)与骨架动作按**依赖拓扑**重排——
EV 卖面全部系 bench 域操作(画面零迁移,契约 §2 可续),而骨架的开店
意图(OpenShop)系截断点;EV 卖面插到首个截断点/终点动作**之前**
(``_merge_ev_before_frame_end``),否则换线生效帧(M2 对新线缺口发
OpenShop 的典型帧)的塌缩出口发射会落在截断点之后被静默丢弃
(IMPL_ADV_R197 症1;IMPL_DESIGN §3.4「EV 只追加」的追加面=发射
组织面,执行序按依赖拓扑承载)。截断器丢弃尾动作一律计数
``emitter_post_truncation_dropped``(零静默披露;登记=design_telemetry
键节 R197 补登行)。

R197 修复批(症2)影子面声明:A/B 期换线权威 = decision_v2 意向状态机
(``update_target`` 透传,两臂同源恒等);本模块 ``switch.event`` 只登记
回锁窗遥测与 switchline_event 计数,**不写 target_comp**——cw4 的
should_switch/回锁窗/干旱计数全部为影子面(实装接线=过线后批)。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    BailToOuter,
    ClickSpheres,
    DeferSpheres,
    DeployMove,
    EnsureShopClosed,
    EnsureShopOpen,
    LevelUp,
    OpenBox,
    OpenShop,
    OpenTome,
    PickBoxCard,
    PrepAction,
    RunBuyPhase,
    RunDeploy,
    RunEquip,
    RunTools,
    SellBench,
    SellDeployed,
    StartBattle,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import mandate, proof
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import contracts
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    levelup as crit_levelup,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    sell as crit_sell,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        PrepObservation,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.kernel.cw_state import GameState
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.turn_state import (
        TurnState,
    )

#: ev_arm 值域(R1-1:skeleton_only=臂① EV 发射面旁路;full=臂② 全开)
EV_ARM_VALUES: tuple[str, ...] = ('skeleton_only', 'full')

log = logging.getLogger(__name__)

# ===== 帧稳定截断分类(契约 v2 §3.2 备战线域逐类)=====

#: 截断点(该动作可作序列最后一个动作发出,其后截断)
_TRUNCATION_POINTS: tuple[type, ...] = (
    OpenBox, OpenTome, PickBoxCard, OpenShop,
    EnsureShopOpen, EnsureShopClosed,      # 退役类兼容面保守判=截断点
    RunBuyPhase,                           # 退役类兼容面保守判=截断点
)
#: 终点(只能作序列最后一个动作;StartBattle=出战环出口;BailToOuter=
#: 退役·终点——中止本环交外环按序列终点语义,契约 §3.2 行,R196 症5 标签对齐)
_TERMINAL: tuple[type, ...] = (StartBattle, BailToOuter)
#: 可续(画面零迁移/坐标不变)
_CONTINUE: tuple[type, ...] = (LevelUp, DeferSpheres)
#: 条件续(bench 索引结构恒稳+名-槽一致性复检;board 空位/星级合成按
#: 前序动作累积静态推出,推不出即截断——契约 §3.2 五行+ClickSpheres 行;
#: 组合动作类(SellDeployed/RunDeploy/RunEquip)按发射期计划静态推出成立
#: [ADR-0316],复检不适用,经 _CONDITIONAL fallthrough 达成同效——
#: R197 症8:独立死常量 _CONDITIONAL_COMPOSITE 已删,分类语义不变)
_CONDITIONAL: tuple[type, ...] = (
    SellBench, SellDeployed, DeployMove, RunDeploy, RunEquip,
    RunTools,                             # 组合类(ADR-0532 工具执行批):同组合语义
    ClickSpheres,                          # 条件:常态可续;末批可能掉箱后截断
)


def classify_frame_stability(action: PrepAction) -> str:
    """单动作帧稳定分类(契约 v2 §3.2 逐类判的机器可读形式)。

    返回:'continue' / 'conditional' / 'truncation' / 'terminal' /
    'unknown'(词表外/无分类 ⇒ §3.3 fail-closed)。
    """
    for t in _TERMINAL:
        if isinstance(action, t):
            return 'terminal'
    for t in _TRUNCATION_POINTS:
        if isinstance(action, t):
            return 'truncation'
    for t in _CONDITIONAL:
        if isinstance(action, t):
            return 'conditional'
    for t in _CONTINUE:
        if isinstance(action, t):
            return 'continue'
    return 'unknown'


def truncate_frame_stable(actions: list[PrepAction],
                          session: StrategySession | None = None,
                          *, bench_slots: set[int] | None = None,
                          ) -> list[PrepAction]:
    """帧稳定截断发射器(契约 §2 帧稳定域 + §3 分域枚举 + §3.3)。

    逐动作判「本动作执行后的画面状态能否静态推出」:可续/条件续 →
    继续发射;截断点 → 该动作作为序列最后一个动作发出;终点 → 序列
    终点(其后必须截断);unknown(词表外/无分类)→ fail-closed 截断
    + 计数披露(``emitter_unknown_action_truncated``,键登记见
    design_telemetry 键节——契约禁成遥测键第二登记源)。

    conditional 类的复检(R196 症5,契约 §3.2 依据列「名-槽一致性复检/
    前序累积静态推出,推不出即截断」):

    - ``SellBench``/``DeployMove``:bench 槽位引用对 ``bench_slots``
      (生成期观察的占用槽位集)复检 + 前序同序列卖出/拖出累积投影
      (槽位卖出后从投影集移除)——引用空槽/未知槽 ⇒ 推不出 ⇒ 该动作
      处截断 + ``emitter_conditional_truncated`` 计数。``bench_slots``
      缺省 None = 复检语境缺失,按条件成立续发(发射器自身产序列时
      引用即生成期观察,生产路径 bridge 总是供给语境)。
    - ``ClickSpheres``:末批判——同序列其后还有 ClickSpheres 批次 ⇒
      非末批,常态分支可续;本批为序列内最后一批 ClickSpheres(可能
      掉箱,掉箱弹 overlay 不可静态预测)⇒ 其后截断(契约 §3.2
      ClickSpheres 行;末批截断系判型内语义,非失败,不计
      ``emitter_conditional_truncated``)。
    - 组合类(SellDeployed/RunDeploy/RunEquip):内部成员按部署/装备
      计划静态推出,发射器序列内成立(ADR-0316)⇒ 可续。

    尾动作丢弃计数(R197 症1②):任一截断路径(词表外/复检失败/截断点/
    终点/ClickSpheres 末批)丢弃的后续动作逐个计数
    ``emitter_post_truncation_dropped``——截断本身系契约语义(非失败),
    但「丢弃了什么」必须可观测,禁零计数静默(EV 发射被截断丢弃时
    遥测可辨「评估了不发射」vs「发射被丢弃」)。
    """
    counters: dict | None = None
    if session is not None:
        got = getattr(state_of(session), 'cw4_counters', None)
        if isinstance(got, dict):
            counters = got

    def _count(key: str, n: int = 1) -> None:
        if counters is not None:
            counters[key] = counters.get(key, 0) + n

    out: list[PrepAction] = []
    slots: set[int] | None = set(bench_slots) if bench_slots is not None else None

    def _cut() -> list[PrepAction]:
        # 截断收口:丢弃尾动作逐个计数(零静默披露,R197 症1②)
        _count('emitter_post_truncation_dropped', len(actions) - len(out))
        return out

    for i, a in enumerate(actions):
        kind = classify_frame_stability(a)
        if kind == 'unknown':
            _count('emitter_unknown_action_truncated')
            return _cut()       # 词表外:该动作处截断(不猜测分类)
        if kind == 'conditional':
            if isinstance(a, ClickSpheres):
                has_later_batch = any(
                    isinstance(a2, ClickSpheres) for a2 in actions[i + 1:])
                out.append(a)
                if not has_later_batch:
                    return _cut()  # 末批可能掉箱 ⇒ 其后截断(判型内语义)
                continue
            if isinstance(a, SellBench):
                if slots is not None and a.slot not in slots:
                    _count('emitter_conditional_truncated')
                    return _cut()  # 名-槽一致性复检失败:推不出即截断
                out.append(a)
                if slots is not None:
                    slots.discard(a.slot)
                continue
            if isinstance(a, DeployMove):
                if slots is not None and a.from_slot not in slots:
                    _count('emitter_conditional_truncated')
                    return _cut()
                out.append(a)
                if slots is not None:
                    slots.discard(a.from_slot)
                continue
            # 组合类(SellDeployed/RunDeploy/RunEquip):按计划静态推出成立
            out.append(a)
            continue
        out.append(a)
        if kind in ('truncation', 'terminal'):
            return _cut()
    return out


# ===== 三遍编排 =====

@dataclass
class UpgraderSignals:
    """升档器求值位输出(R27-1②:证明 pass 后、骨架 pass 前每备战期
    现读;信号位必须先于 F7/M3 消费位产出)。

    标定落地(用户裁定=按 15,撤销 R29-1/R36-2 None 期影子维持声明):
    血线阈值单一源 = lambda_death.HP_BAND_NEAR_DEATH(=15,
    BLOODLINE_HP_THRESHOLD provisional 源退役);hp≤阈值 ⇒ 解锁包三件
    (F7 禁令/M3 分流/arm2 门)武装,行为介入开启。λ 顾问:标定前置
    影子维持声明同批撤销——p 注入形态触发即真键武装(行为介入),
    ``lambda_shadow``/``bloodline_shadow`` 影子键保留为对照(同条件
    置位,禁删)。

    R196 症3 载体:``lambda_armed``(真键 ``advisor_lambda_armed``)/
    ``lambda_shadow``(对照键)。
    """

    f7_ban_armed: bool = False
    neardeath_unlock: bool = False
    arm2_gate_open: bool = False
    lambda_shadow_armed: bool = False
    lambda_armed: bool = False
    bloodline_shadow_armed: bool = False


def _lambda_quantile_armed(state: GameState | None, hp: int | None,
                           p_value: float) -> bool | None:
    """λ 顾问相对分位触发谓词(R28-1;R196 症3 影子/真键共用求值体)。

    求值 = 当前帧 PL 键的 λ 点估计(CI 上端,排序键同 ``lambda_u_order``
    的全序口径)在 C 集合可消费格 λ_U 降序全序中的分位序 ≤ p ⇒ 触发。
    键观测量缺失/域外/不可消费格 → None(不评估;域外同判 R52-4a)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
        lambda_death,
    )
    if state is None:
        return None
    node = getattr(state, 'node_type', None) or ''
    key = lambda_death.make_key(getattr(state, 'enemy_difficulty', None),
                                hp, getattr(state, 'plane', 1), node)
    ci = lambda_death.lambda_ci(key)
    if ci is None:
        return None
    order = lambda_death.lambda_u_order()
    if not order:
        return None
    # 降序全序中的序位:取同值首址(饱和并列组按最危端,保守)
    idx = next((i for i, v in enumerate(order) if v <= ci[1]), None)
    if idx is None:
        return None
    return (idx + 1) / len(order) <= p_value


def _upgrader_evaluate(session: StrategySession, state: GameState | None,
                       gold: int, hp: int | None) -> UpgraderSignals:
    """升档器求值(§2.0-3 判危口径①②;本批 None 期 = 结构位 + 影子计数)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
        provisional,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
        lambda_death,
    )
    sig = UpgraderSignals()
    # λ 顾问:R28-1 相对分位触发。标定前置影子维持声明按用户裁定撤销
    #(死亡线标定落地批):p 在场即求值,触发 ⇒ 真键武装(行为介入开启);
    # lambda_shadow 保留为对照键(同条件置位,禁删)。p=None ⇒ 不求值。
    p = provisional.get('P_LAMBDA_QUANTILE')
    if p is not None:
        armed = _lambda_quantile_armed(state, hp, float(p.value))
        if armed:
            sig.lambda_armed = True
            sig.lambda_shadow_armed = True   # 对照键保留
    # 血线硬地板(标定落地,用户裁定=按 15):阈值单一源 =
    # lambda_death.HP_BAND_NEAR_DEATH(BLOODLINE_HP_THRESHOLD provisional
    # 源退役,两源归一);hp ≤ 阈值 ⇒ 解锁包三件武装(F7 禁令/M3 分流/
    # arm2 门,行为介入开启);影子键保留对照。
    if hp is not None and hp <= lambda_death.HP_BAND_NEAR_DEATH:
        sig.neardeath_unlock = True
        sig.arm2_gate_open = True     # R28-2 解锁包:g*→0(arm2 金下限)
        sig.f7_ban_armed = True
        sig.bloodline_shadow_armed = True   # 对照键保留
    return sig


def emit(obs: PrepObservation, turn: TurnState, session: StrategySession,
         config: object, *, ev_arm: str = 'full',
         registry: DecisionV2Registry | None = None) -> list[Emitted]:
    """决策入口三遍编排(R189-4 结构签名;返回 Emitted 列表交桥截断发射)。

    编排:① prep 实体面(箱选卡/球/箱/典籍——控制流与 overlay 切换
    优先于三遍)→ ② 证明 pass(信号臂/K/stop_flag/线级状态机/换线)→
    ③ 升档器求值位 → ④ 骨架 pass(M1-M7)→ ⑤ EV pass(criteria,
    臂①旁路)→ ⑥ 无动作 ⇒ StartBattle(序列终点=备战环正常出口)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )

    if getattr(state_of(session), 'cw4_counters', None) is None:
        state_of(session).cw4_counters = {}

    # ① prep 实体面
    if getattr(obs, 'box_overlay_open', False):
        # 武装箱选择对话框在场(OpenBox 已开箱)⇒ 补选卡动作闭环。第十八局
        # 停场修复(g_20260905_175220 备战 2-2):此前 OpenBox→弹窗后决策
        # 面无臂消费 box_overlay_open,OpenBox 重开空转 15 分钟(执行器
        # _pick_box_card/期望态投影/适配器注册均早在库,独缺发射位)。
        return [Emitted(PickBoxCard(), True, 'prep_box_pick')]
    if obs.boxes:
        return [Emitted(OpenBox(slot=obs.boxes[0][0]), True, 'prep_box')]
    if obs.tomes:
        return [Emitted(OpenTome(slot=obs.tomes[0][0]), True, 'prep_tome')]
    if obs.spheres:
        return [Emitted(ClickSpheres(max_k=min(3, len(obs.spheres))), True,
                        'prep_spheres')]
    if obs.event_overlay:
        return [Emitted(BailToOuter(reason=obs.event_overlay), True,
                        'event_overlay')]

    state = obs.state
    # 帧级复位(与 posture_release.attach_spend_authorization 同口径):
    # 每决策段「入口=无声明、段尾=本段真值」,防 posture_unfulfilled 旧值
    # 跨帧滞留成假信号(病灶②修法的正确性前提)。
    state_of(session).v3_posture_unfulfilled = None
    k = getattr(state_of(session), 'target_comp', None)
    k_members = predicates.line_members(k)
    # K 空窗回退(准备域;经济冻结批病灶①保险层):shop.py 商店域已有
    # 同款回退,准备域(mandate pass)旧形态 K=None ⇒ k_members=() ⇒
    # M2 无目标、dominance/M6 停手、引擎只剩 M7,0 买 0 刷经济冻结
    # (实机局 g_20260904_042657 p1r7-r9)。回退单一源 = cw_intention
    # (与 shop.py 同源消费,禁复制四体系全集/兜底逻辑);ist 缺失 =
    # 意向供给缺帧,保守侧不回退(与 shop.py 同款 fail 方向)。
    if k is None:
        from sr_od.application.currency_war.kernel import cw_intention
        _ist = getattr(state_of(session), 'v3_intention', None)
        if _ist is not None and state is not None:
            _fb, _band = cw_intention.k_empty_window_fallback(state, _ist)
            if _fb:
                k_members = tuple(sorted(_fb))
                state_of(session).cw4_counters[f'prep_k_fallback_{_band}'] = \
                    state_of(session).cw4_counters.get(f'prep_k_fallback_{_band}', 0) + 1
    bench = list(obs.bench_chars)
    deployed = list(obs.deployed_chars)
    bench_names = [b.char_id or '' for b in bench]
    deployed_names = [b.char_id or '' for b in deployed]

    # ② 证明 pass(信号臂 R11-3:两臂同开不旁路;命中=直通线语境,计数披露)
    if proof.signal_arm(session) is not None:
        _ct_sig = state_of(session).cw4_counters
        _ct_sig['signal_arm_direct'] = _ct_sig.get('signal_arm_direct', 0) + 1
    stop_flag = None
    # 契约核验(FIX_REVIEW R1 漏接位补齐):stop_buy 消费位经
    # ensure_contract(前提恒真 None 登记,违例路径仅剩未登记键);
    # 弃权侧=保守停买(fail-closed,支配买/溢余面不因缺核验开闸)
    if contracts.ensure_contract(
            ('proof', 'stop_buy'), contracts.ContractCtx(),
            state_of(session).cw4_counters):
        stop_flag = proof.stop_buy(k, bench_names, deployed_names)
    else:
        stop_flag = True
    proof.update_line_state(session, k, bench_names, deployed_names)
    skeleton_only = (ev_arm == 'skeleton_only')
    switch = proof.should_switch(
        state, session, config, registry, skeleton_only=skeleton_only)
    # 换线事件本帧只登记,K 变更下一备战期生效(R1-3):登记 = 撤线窗口
    # 步进 + 换线遥测;K 翻转由 update_target(下帧)承载。
    # 【R197 症2 影子面声明(编排者裁=方案 a)】A/B 期 target_comp 权威
    # = decision_v2 意向状态机(update_target 透传,两臂同源恒等);本
    # 登记只写回锁窗状态与计数,不写 target_comp——cw4 换线判据族
    # (should_switch/回锁窗/干旱计数)=影子面,实装接线=过线后批。
    if switch.event:
        proof.register_eviction(session, getattr(k, 'name', ''))
        counters = state_of(session).cw4_counters
        counters['switchline_event'] = counters.get('switchline_event', 0) + 1
    # k_switched 实值化(R196 症1):上一备战期线名快照 vs 本帧生效 K 名
    # ——不同即换线已在本帧生效(塌缩出口评估条件,line_switch_sell 只在
    # K 已更新的备战期评,§2.7);旧线成员自 COMP_LIBRARY 按名取回。
    prev_name = getattr(state_of(session), 'cw4_prev_line_name', '') or ''
    cur_name = getattr(k, 'name', '') if k is not None else ''
    k_switched = bool(prev_name) and prev_name != cur_name
    old_line_members = predicates.line_members(get_comp(prev_name)) \
        if k_switched else ()

    # ③ 升档器求值位(先于一切卖面判据评估,§3.1)
    _sig = _upgrader_evaluate(session, state,
                              state.gold if state else 0,
                              getattr(state, 'hp', None))
    _ct = state_of(session).cw4_counters
    if _sig.lambda_shadow_armed:
        _ct['advisor_lambda_shadow_armed'] = \
            _ct.get('advisor_lambda_shadow_armed', 0) + 1
    if _sig.lambda_armed:
        _ct['advisor_lambda_armed'] = \
            _ct.get('advisor_lambda_armed', 0) + 1
    if _sig.bloodline_shadow_armed:
        _ct['advisor_bloodline_shadow_armed'] = \
            _ct.get('advisor_bloodline_shadow_armed', 0) + 1
    if _sig.neardeath_unlock:
        _ct['advisor_bloodline_armed'] = \
            _ct.get('advisor_bloodline_armed', 0) + 1
        _ct['neardeath_unlock'] = _ct.get('neardeath_unlock', 0) + 1

    # ④ 骨架 pass
    # cap 真值源=state.max_units() 派生链(R4 统一,FIX_REVIEW ②-1 双源
    # 漂移修复:旧 ``obs.deploy_vacancy + len(deployed)`` 观察复合废弃
    # ——与 shop 侧 arm1 消费位同链单源;state 缺读=None,消费点
    # deploy_vacancy 保守 0)
    # 部署面 membership 消费口径声明(评估出处 = 策略审查报告 20260905-093104-strategy-review/策略审查-第十二跳.md):本帧 k_members
    # = predicates.line_members(core∪shared,部署语义口径)——部署/升级
    # 授权只量可上阵阵容;买入义务面口径 = buy_members(shop 域,含锁定
    # 采购集超集)——两口径分域 = 有意设计(编排者存-2 裁决:囤腿件走
    # 合成→上板,部署面只量可部署现量)。分层归属:transition_pair 维持
    # ADR-0367 二级囤货(locked_buy_membership 已排除,不入部署/买入义务);
    # F3(全 2★ 旧线重锚)经编排者裁决驳回(前提事实错误:第十局板面为
    # 全 1★ 旧线;§9.5 单一源资格已覆盖该病例),全 2★ 形态另案观察。
    frame = mandate.MandateFrame(
        gold=state.gold if state else 0,
        level=state.level if state else 3,
        bench=bench, deployed=deployed,
        deploy_cap=(state.max_units() if state is not None else None),
        node_type=getattr(session, 'node_type_current', None),
        stop_flag=stop_flag, k_members=k_members,
        round_num=getattr(state, 'round_num', 1) if state else 1)
    out: list[Emitted] = mandate.run_mandate(frame, session, state=state)

    # ⑤ EV pass(臂①旁路集=§4.2.1 显式清单;仅 criteria 真 EV 项)。
    # R197 症1:EV 输出先收进独立列表,经 _merge_ev_before_frame_end
    # 按依赖拓扑并入(EV 卖面=bench 域可续动作,插到骨架首个截断点/
    # 终点动作之前——否则换线生效帧的塌缩出口发射落在 OpenShop 之后
    # 被截断器静默丢弃)。
    ev_out: list[Emitted] = []
    if not skeleton_only:
        ev_out = _criteria_pass(frame, session, state, k_members,
                                k_switched=k_switched,
                                old_line_members=old_line_members,
                                skeleton_out=out)
    else:
        # 支付支撑通道(两臂同开,R13-5):金不足侧筹资变现;同槽冲突
        # 先到先得丢弃(R196 症2,与骨架 M4 已发射槽位比对)
        sold_slots = {e.action.slot for e in out
                      if isinstance(e.action, SellBench)}
        missing = [m for m in k_members
                   if m not in set(bench_names) | set(deployed_names)]
        # 判据契约核验(IMPL_DESIGN §4.2.2):前提不成立 ⇒ 本帧弃权
        # + criteria_contract_violation 计数,禁静默执行
        if missing and state is not None and contracts.ensure_contract(
                ('sell', 'funding_support_sell'),
                contracts.ContractCtx(gold=state.gold), _ct):
            slots, _why = crit_sell.funding_support_sell(
                state.gold, mandate.cheapest_member_cost(frame), bench,
                k_members, state=state, counters=_ct,
                dedup_names=set())   # C1 事件口径:单帧去重(单调用语境)
            for s in slots:
                if s in sold_slots:
                    _ct['ev_conflict_dropped'] = \
                        _ct.get('ev_conflict_dropped', 0) + 1
                    continue
                ev_out.append(Emitted(SellBench(slot=s), False,
                                      'funding_support',
                                      funding_support=True))
    out = _merge_ev_before_frame_end(out, ev_out)

    # ⑤′ 姿态兑现对账(经济冻结批病灶②):预算核姿态(spend_mode='level')
    # 授权了本轮升级而发射序列无 LevelUp ⇒ posture_unfulfilled 显式置位
    # + 姿态降级声明 + 计数/日志。旧形态=守卫字段接而不用:授权面
    # (get_node_goal,确定性预算核单一供给)与执行面(M3:arm1 存在性 +
    # spend_unified 整批纪律)判定不一致时零对账,session.v3_posture_
    # unfulfilled 恒 None(实机局 g_20260904_042657 p1r7-r9 posture=
    # 'level' 全程零 LevelUp)。本对账只声明不兜底花钱(禁重引入「乱花」
    # 对立面:P56 下界语义零触碰,升级仍由 M3 判据独裁)。
    _reconcile_posture_authorization(session, state, out, k_members)

    # ⑥ 无动作 ⇒ 出战(序列终点)
    if not out:
        out.append(Emitted(StartBattle(), True, 'battle'))
    state_of(session).cw4_prev_line_name = cur_name   # 下帧 k_switched 判定基准
    return out


def _reconcile_posture_authorization(session: StrategySession,
                                     state: GameState | None,
                                     emitted: list[Emitted],
                                     k_members: tuple[str, ...] = ()) \
        -> dict | None:
    """姿态兑现对账(经济冻结批病灶②;授权面与执行面的唯一仲裁点)。

    授权面 = ``get_node_goal`` 确定性预算核(spend_mode 单一供给,遥测
    dp_posture 同源);执行面 = M3 升级链(arm1 存在性 → lv9 停 →
    spend_unified 整批纪律 → 可负担)。spend_mode='level'(本轮授权升级)
    而发射序列无 LevelUp ⇒ 逐门评估定位未兑现原因,显式声明:
    - ``state_of(session).v3_posture_unfulfilled`` 置位(遥测 posture_unfulfilled
      消费;形状与 decision_v2.posture_release.reconcile_spend 同构);
    - 计数键 ``posture_unfulfilled_level``(state_of(session).cw4_counters);
    - log.info(带未兑现原因,判读可直接归因)。

    只声明不兜底:不因授权未兑现而改发射(升级发射仍由 M3 判据独裁,
    P56 下界语义零触碰)。授权形态非 level / 已发射 LevelUp ⇒ 返回
    None(且入口帧级复位保证无声明滞留)。state 缺席=无姿态供给,不评。
    """
    if state is None:
        return None
    from sr_od.application.currency_war.kernel.cw_economy import get_node_goal
    ng = get_node_goal(state.plane, state.round_num, gold=state.gold,
                       level=state.level, hp=state.hp,
                       strategies=list(getattr(state, 'active_strategies',
                                               []) or []) or None)
    if getattr(ng, 'spend_mode', '') != 'level':
        return None
    if any(isinstance(e.action, LevelUp) for e in emitted):
        return None
    # 候选③:危机带经验授权让位 = 显式降级而非「未兑现故障」——
    # M3 发射位(mandate/shop)被 level_spend_blocked 挂起时,授权面
    # 按 crisis_yield 声明(P48 λ>0 段转化优先;判据单一源同 M3 消费位),
    # 不落逐门故障定位(那些门本轮根本未被求值)。
    if state is not None and contracts.ensure_contract(
            ('levelup', 'level_spend_blocked'),
            contracts.ContractCtx(), getattr(state_of(session), 'cw4_counters',
                                             None) or {}) \
            and crit_levelup.level_spend_blocked(state, session):
        un = {'auth_id': f'{state.plane}-{state.round_num}',
              'channel': 'levelup',
              'reason': 'crisis_level_spend_blocked',
              'channels': {'levelup': 'crisis_level_spend_blocked'},
              'action': 'crisis_yield'}
        state_of(session).v3_posture_unfulfilled = un
        counters = getattr(state_of(session), 'cw4_counters', None)
        if isinstance(counters, dict):
            counters['posture_crisis_level_defer'] = \
                counters.get('posture_crisis_level_defer', 0) + 1
        log.info('[cw][cw4] posture level 授权危机让位 '
                 '(hp=%s, plane=%s r%s): %s',
                 state.hp, state.plane, state.round_num,
                 un['reason'])
        return un
    # 逐门定位未兑现原因(与 run_mandate M3 链同序同判据,复用判据本体
    # 禁第二实现;M3 未发射时这些门的求值是纯函数,零副作用)。
    from sr_od.application.currency_war.kernel.cw_economy import (
        clicks_to_next_level,
        xp_click_cost,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup,
    )
    cap = state.max_units()
    if levelup.lv9_stop(state.level):
        reason = 'lv9_stop'
    elif cap is None:
        reason = 'contract_cap_missing'
    elif not predicates.arm1_existence(
            len([d for d in state.deployed if d is not None]),
            [b.char_id or '' for b in state.bench if b is not None],
            [d.char_id or '' for d in state.deployed
             if d is not None], cap):
        reason = 'arm1_board_not_full'
    else:
        clicks = clicks_to_next_level(state)
        cost = xp_click_cost(state)
        if not levelup.spend_unified(clicks, state.gold, cost):
            reason = 'spend_unified_batch_unaffordable'
        elif state.gold < clicks * cost:
            reason = 'unaffordable'
        else:
            # P71-b (3) 溢余段预算闸镜像(ADR-0560;与 run_mandate M3 链
            # 同序同判据,复用判据本体禁第二实现):闸拒归因 = budget_gate
            # 族独立拒因,禁落 contract_other 兜底桶(prep 侧降级归因
            # 全错形态,方案审 B4)。cap_resolved 用 resolved 口径单一源。
            _gate_ok, _gate_why = (False, '')
            if contracts.ensure_contract(
                    ('levelup', 'levelup_budget_gate'),
                    contracts.ContractCtx(gold=state.gold, deploy_cap=cap),
                    getattr(state_of(session), 'cw4_counters', None) or {}):
                from sr_od.application.currency_war.kernel.cw_economy import (
                    cap_resolved_of_session,
                )
                _gate_ok, _gate_why = levelup.levelup_budget_gate(
                    state, state.gold, cap_resolved_of_session(session),
                    k_members, list(state.bench or []),
                    list(state.deployed or []), clicks, cost)
            reason = (_gate_why if not _gate_ok and _gate_why
                      else 'contract_other')
    un = {'auth_id': f'{state.plane}-{state.round_num}',
          'channel': 'levelup',
          'reason': reason,
          'channels': {'levelup': reason},
          'action': 'downgrade'}
    state_of(session).v3_posture_unfulfilled = un
    counters = getattr(state_of(session), 'cw4_counters', None)
    if isinstance(counters, dict):
        counters['posture_unfulfilled_level'] = \
            counters.get('posture_unfulfilled_level', 0) + 1
    log.info('[cw4][posture] level 授权未兑现(p%sr%s g=%s lv=%s):%s '
             '(posture_unfulfilled 置位,显式降级,不兜底花钱)',
             state.plane, state.round_num, state.gold, state.level, reason)
    return un


def _merge_ev_before_frame_end(skeleton: list[Emitted],
                               ev: list[Emitted]) -> list[Emitted]:
    """EV 卖面与骨架动作的依赖拓扑合并(R197 症1;IMPL_DESIGN §3.1)。

    EV 卖面(line_switch_sell/funding_support 的 SellBench)系 bench 域
    操作(画面零迁移,契约 §2 可续类);骨架的开店意图(OpenShop)系
    截断点。合并规则:EV 发射整体插到骨架序列中**首个截断点/终点动作
    之前**,骨架内部相对序与 EV 内部序均不变;骨架无截断点/终点 ⇒ EV
    追加尾部(与 R196 前行为一致)。「EV 只追加」(§3.4)的追加面=
    发射组织面;执行序按依赖拓扑承载——不重排则换线生效帧(K 已翻为
    K′、新线有缺口 ⇒ M2 发 OpenShop 的典型帧)的塌缩出口发射全部落
    在截断点之后,被截断器静默丢弃(IMPL_ADV_R197 症1)。
    """
    if not ev:
        return skeleton
    idx = next(
        (i for i, e in enumerate(skeleton)
         if classify_frame_stability(e.action)
         in ('truncation', 'terminal')),
        len(skeleton))
    return skeleton[:idx] + ev + skeleton[idx:]


def _criteria_pass(frame: mandate.MandateFrame, session: StrategySession,
                   state: GameState | None, k_members: tuple[str, ...], *,
                   k_switched: bool,
                   old_line_members: tuple[str, ...],
                   skeleton_out: list[Emitted] | None = None) -> list[Emitted]:
    """EV pass:criteria 七面按 §2 映射逐面追加(只增不减,§3.4)。

    None 期缺省姿态:各面内部 fail-closed(未标定不发射);本函数
    只做发射面组织。冲突处理(R196 症2 落地):EV 项与已发射动作冲突
    (同槽 SellBench——M4 已卖槽/同 pass 内重复提案)⇒ 先到先得丢弃
    + 记遥测(``ev_conflict_dropped``):第二笔执行必 progressed=False
    触发 fail-stop,整序列后半被一帧废动作截断(契约 §2),禁重发。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    counters = getattr(state_of(session), 'cw4_counters', None)
    if not isinstance(counters, dict):
        counters = {}
        state_of(session).cw4_counters = counters
    # 先到先得冲突域:骨架 pass 已发射的 SellBench 槽位(席位冲突面)
    sold_slots = {e.action.slot for e in (skeleton_out or [])
                  if isinstance(e.action, SellBench)}
    # 拦截事件去重集(C1 口径:同一备战帧内同一素材名只计 1;跨通道共享,
    # 单一源 = cw_state.count_merge_material_blocked)
    _mm_dedup: set[str] = set()
    out: list[Emitted] = []
    # line_switch_sell(换线塌缩出口:k_switched 时对旧线件重评;
    # 契约核验=IMPL_DESIGN §4.2.2,前提不成立 ⇒ 本帧弃权+计数;
    # 拒因分键接线(D1 整改):本位曾静默 continue,现同键计数显影)
    if contracts.ensure_contract(
            ('sell', 'line_switch_sell'),
            contracts.ContractCtx(k_members=k_members), counters):
        slots, _key = crit_sell.line_switch_sell(
            old_line_members, k_members, frame.bench, frame.deployed, state,
            k_switched=k_switched, counters=counters,
            dedup_names=_mm_dedup)
    else:
        slots = []
    for s in slots:
        if s in sold_slots:
            counters['ev_conflict_dropped'] = \
                counters.get('ev_conflict_dropped', 0) + 1
            continue
        out.append(Emitted(SellBench(slot=s), False, 'line_switch_sell'))
        sold_slots.add(s)
    # 凑息档 EV 面 / 压库 / 装备精修 / 付费刷新:商店线辖域或【拟】
    # None 期 fail-closed,prep 帧无追加发射(判据本体已落
    # criteria/*,商店线接线随步6 前接线批——STEP34_REPORT 裁量呈报)。
    # 支付支撑通道(两臂同开)
    missing = [m for m in k_members
               if m not in set(frame.bench_names) | set(frame.deployed_names)]
    if missing and state is not None and contracts.ensure_contract(
            ('sell', 'funding_support_sell'),
            contracts.ContractCtx(gold=state.gold), counters):
        # T3 同轮保留集读端(第四消费位,与店侧 shop.py funding 发射位
        # 同款口径):被保垫件仅降序放行(转化类,非禁卖),命中卖出分键
        # funding_support_stall_convert + 卖出销账。
        _t3_protect = mandate.stall_protect_active(
            session, int(getattr(state, 'round_num', 1) or 1),
            counters=counters)
        fslots, _why = crit_sell.funding_support_sell(
            state.gold, mandate.cheapest_member_cost(frame), frame.bench,
            k_members, state=state, counters=counters,
            defer_names=_t3_protect,
            dedup_names=_mm_dedup)
        for s in fslots:
            if s in sold_slots:
                counters['ev_conflict_dropped'] = \
                    counters.get('ev_conflict_dropped', 0) + 1
                continue
            # T3 转化类分键 + 卖出销账(店侧同款;prep 域 SellBench 载体
            # 无 reason 字段故分键只落计数不落动作标记——sim 不执行 prep
            # 域,豁免检查只辖 sim 账本,prep 侧无需 reason;defer 保护
            # 全时段覆盖,不依赖该注释所述的任何时序假设)
            _fbc = next((b for b in frame.bench if b.slot == s), None)
            _fname = (_fbc.char_id or '') if _fbc is not None else ''
            if _fname in _t3_protect:
                counters['funding_support_stall_convert'] = \
                    counters.get('funding_support_stall_convert', 0) + 1
                mandate.stall_buys_consume(session, _fname)
            out.append(Emitted(SellBench(slot=s), False, 'funding_support',
                               funding_support=True))
            sold_slots.add(s)
    return out
