"""决策框架 v2 层4:预算仲裁器(ADR-0290;按分执行+约束收口+审计表)。

按层3分数排序→依次裁决→全局约束(金≥地板/bench 容量/同轮互斥/
boss 轮禁令[32]/息律[28])**一处收口**——约束一处定义(registry
.constraints),全部候选受辖(通道制下约束散在各通道是漏门根源)。

**完备性审计表**(对抗修订④):资源维(金/bench/槽/同轮)×回合态维
(boss/应急/窗口)矩阵,每格=约束名或显式「无约束覆盖」声明;
``build_audit_report`` 输出矩阵,检查项 decision_v2_arbiter_matrix 锁
「无空格+约束名存在」;新增动作类型时审计表强制过检。

执行 log=每轮候选×分数表(判读可直接读)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_state import (
    Action,
    BuyCard,
    DeployMove,
    GameState,
    LevelUp,
    RefreshShop,
    SellBench,
    deployed_occupied,  # ADR-0392 helper 导入
    simulate,
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.candidates import Candidate
from sr_od.application.currency_war.decision_v2.discipline import (
    blood_budget_levelup_blocked,
    boss_window_active,
    form_break_sell_blocked,
    p1_early_gate_open,
    register_round_bought,
    register_round_sold,
    sole_engine_sell_blocked,
)
from sr_od.application.currency_war.decision_v2.ev import (
    interest_cost,
    levelup_ev_basis,
    round_posture,
)
from sr_od.application.currency_war.decision_v2.filters import (
    current_mode,
    is_emergency,
)

# W252/ADR-0409:M-A 收尾裁决消费(延迟 import 防环不必要——handoff
# 不回 import arbiter;直连单一源)
from sr_od.application.currency_war.decision_v2.handoff import (
    directed_refresh_budget,
)
from sr_od.application.currency_war.decision_v2.phase import (
    Phase,
    derive_phase,
)
from sr_od.application.currency_war.decision_v2.posture_release import (
    authorize_release_refresh,
)
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.decision_v2.remediation import (
    Rejection,
    RejectReason,
    remediation_pass,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.decision_v2.discipline import (
        DisciplineView,
    )


@dataclass
class ArbiterResult:
    """仲裁产物:执行序列 + 判读 log + 使用的覆盖态 + 拒绝事件 + 补偿日志。"""

    actions: list[Action] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)
    coverage: str = 'mode'          # emergency / mode(追赶态已退场,ADR-0349)
    floor: int = 0                  # 本轮生效地板
    #: 资源型拒绝事件(补偿的受益候选;W52 回连机制输入,ADR-0326)
    rejections: list[Rejection] = field(default_factory=list)
    #: 补偿日志(§1.1 schema;arbiter 末段补偿趟产出)
    remediation_log: list[dict] = field(default_factory=list)


def _active_floor(state: GameState, session: StrategySession,
                  registry: DecisionV2Registry) -> int:
    """地板分派(W119/ADR-0347 相位地板;覆盖态优先序不变——应急/boss/
    war 旁路与节点授权先于相位,逐位保留)。

    - 应急 → rebirth_floor([18],旁路不动);
    - boss 窗(节点图统一口径 boss_window_active)→ boss_floor;
    - war 模式(报警升级/boss_breaker 覆盖)→ war_floor;
    - 常态 → **相位地板**(W113 §3.4 替换行,阶梯地板退场):
      FORM → form_floor(保险丝,EV 授权下的本金下限;Q1 四档 sim
      对照待校准,本批只接线);HOARD/SPEND → interest_floor(满息
      平台,只花溢余)。HOARD 的 [11] 无损购买例外在同档/1费放行
      (gold_floor 内实现,非地板值变化)。
    """
    if is_emergency(state, registry):
        return registry.rebirth_floor
    if boss_window_active(state, session, registry):
        return registry.boss_floor
    if current_mode(session) == 'war':
        return registry.war_floor
    if derive_phase(state, session, registry) is Phase.FORM:
        return registry.form_floor
    return registry.interest_floor()


def _round_state_dims(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> set[str]:
    """当前命中的回合态维(审计表列;'catchup' 已随 W126/ADR-0349 退场)。"""
    dims: set[str] = set()
    if boss_window_active(state, session, registry):
        dims.add('boss')
    if is_emergency(state, registry):
        dims.add('emergency')
    return dims


def _below_floor_refresh_e2(working: GameState, state: GameState,
                            session: StrategySession,
                            registry: DecisionV2Registry) -> bool:
    """息线以下刷新例外 E2([6] 精确化;方向三,ADR-0434)。

    「店全是想要的」的可算化口径收窄=「店内有配方围栏名集件」——与
    方向一同一把名集尺(scoring._cand_system_bonds 单一源,禁造第二
    把),定向刷新语义,上限 1 次/轮(轮内计数 session.v3_bf_refresh_*,
    消耗登记在 refresh 采纳块,与 dir_refresh 键式同构)。辖域与本例外
    正交声明:C1 的 _refreshable_names 辖溢余段,本例外辖息线以下。
    """
    from sr_od.application.currency_war.decision_v2.scoring import (
        _cand_system_bonds,
    )
    key = (state.plane, state.round_num)
    if getattr(session, 'v3_bf_refresh_key', None) != key:
        used = 0
    else:
        used = getattr(session, 'v3_bf_refresh_round', 0)
    if used >= 1:
        return False
    for sc in (working.shop or []):
        if sc is None or not getattr(sc, 'name', ''):
            continue
        if _cand_system_bonds(Candidate(action=BuyCard(sc), tag='e2',
                                        source='e2')):
            return True
    return False


def _check_constraint(name: str, cand: Candidate,
                      working: GameState, state: GameState,
                      session: StrategySession,
                      registry: DecisionV2Registry,
                      val: float = 0.0,
                      bd: dict | None = None,
                      auth: dict | None = None,
                      ) -> RejectReason | None:
    """单约束裁决:通过返回 None,拒绝返回结构化原因(判读可读)。

    W52(ADR-0326):拒绝原因从裸 str 升为 ``RejectReason``——资源型
    约束(gold_floor/bench_capacity/deploy_cap)填 resource/shortfall
    (补偿路由键/缺口量,程序可读);纪律型拒绝(interest_rule/
    copies_cap/same_round_mutex/boss_levelup_ban)
    resource='' shortfall=0 占位,**不进回连**(§1.1 捕获条件)。
    log 行格式不变(``f'{cname}:{reason.describe}'``)。

    W119(ADR-0347):``val``/``bd`` = 层3 分数与 breakdown(interest_rule
    的 EV 授权消费——V 从分数剥离息分量取得,单一源不重算);补偿重验
    路径(_resource_blocked/_beneficiary_recheck)不查 interest_rule,
    缺省 0 即可。``auth`` = 授权依据 trace 出口(判读「为什么放行」,
    验证门 5):interest_rule 的 EV 放行值写 auth['ev_auth'] 进执行 log。
    """
    a = cand.action
    if name == 'gold_floor':
        cost = _cost_of(cand, working)
        if cost <= 0:
            return None
        floor = _active_floor(state, session, registry)
        if cand.tag == 'o1_bench_fill':
            # W611 O1 备战空位填补(ADR-0463):逐笔花后金 ≥R*——只花
            # 溢余段,不吃排程升级储蓄(DESIGN §1.2 量上限的逐笔口径;
            # R*≥息线≥各相位地板,取 max 只在排程帧收紧,常态零漂移)。
            from sr_od.application.currency_war.decision_v2.economy_cycle import (
                reserve_cap as _o1_reserve_cap,
            )
            floor = max(floor, _o1_reserve_cap(state, session, registry))
        if cand.tag == 'levelup':
            # W126/ADR-0349:升级的金门槛整体让位 boss_levelup_ban 块的
            # ev.levelup_ev_authorized 单一裁决——可负担性(after≥0 入口门)
            # + 三路授权(① 人口位保险丝=可负担性,34 帧误拒修订;② DP
            # 平台未破;③ 静态总账含省刷金项)全在那处收口;此处再设
            # form_floor 保险丝=双重门(34 帧误拒的拦截者之二)。
            return None
        elif (not is_emergency(state, registry)
              and current_mode(session) == 'economy'
              and not boss_window_active(state, session, registry)
              and derive_phase(state, session, registry)
              is not Phase.FORM):
            # 相位地板域(HOARD/SPEND,W119/ADR-0347):
            # - SPEND(金 ≥50):破平台候选让位 interest_rule 的 EV 授权
            #   (此处硬拒会架空总账——EV>0 的破息买是本批的合法放行面);
            # - HOARD(金 <50):[11] 无损购买例外(同档/1费)放行,
            #   跨档拒(攒息——三通道默认关,例外=[11]/[33]/DP 花费授权)。
            if working.gold >= registry.interest_floor():
                if working.gold - cost < registry.interest_floor():
                    return None    # 交 interest_rule EV 裁决
            else:
                # 批 3 预算收权(W623 D2):「>0 即行动授权」改预算函数口径
                # ——息线以下帧 refresh_ev_budget 恒 0(合法 0 帧契约:g<R*
                # 是储备段),故息线下刷新授权只剩 [11]/E2/E3 白名单
                # (R1 规则:囤息域内无 EV 授权;原 DP 姿态 dp_spend 臂随
                # DP 退役,锁面重推出处=W615 §2-R1)。
                posture = round_posture(state, session)
                dp_spend = posture is not None and (
                    posture.level_up or posture.refresh_budget > 0)
                # 息线以下支出门(方向三,ADR-0434):gate 开时刷新的
                # 息线下授权收窄为三例外白名单——E3 同档(与既有 [11]
                # 同档臂同式)与 E2(店内有配方围栏名集件,1 次/轮);
                # dp_spend 不再单独授权息线下刷新([6] 原文不可直算的
                # 口径收窄 + w43 never_50 病灶,w415 DESIGN §3.2)。
                # cost==1 的 [11] 净0 特例原样保留(既有语义,不属本门
                # 新增面);levelup 不经本分支(单一裁决在 ev.levelup_ev_
                # basis 前置门,gate 开时同款三例外收窄)。
                _gate_refresh = (registry.below_floor_spend_gate_enabled
                                 and cand.tag == 'refresh')
                if cost == 1 \
                        or (working.gold - cost) // 10 >= working.gold // 10:
                    return None    # [11] 同档/1费(E3 零息损事实的同义臂)
                if _gate_refresh:
                    if _below_floor_refresh_e2(working, state, session,
                                               registry):
                        if auth is not None:
                            auth['bf_refresh_e2'] = True   # 授权 trace
                        return None    # E2 定向刷新放行(1 次/轮)
                    return RejectReason(
                        'gold_floor', 'gold', working.gold % 10 + cost,
                        f'below_floor_spend(金{working.gold}<息线'
                        f'{registry.interest_floor()},刷新无例外)')
                if dp_spend and cand.tag in ('levelup', 'refresh'):
                    return None    # DP 说花→授权放行(§3.2d;gate 开时
                    # 刷新已在上方 E2 分支收窄,本臂只余 levelup 及 gate 关)
                return RejectReason(
                    'gold_floor', 'gold',
                    working.gold % 10 + cost,
                    f'HOARD 攒息(金{working.gold}-费{cost} 破档;'
                    f'档线{working.gold // 10 * 10})')
        if working.gold - cost < floor:
            if _press_floor_exempt(cand, working, state, session,
                                   registry, auth):
                return None    # W300/§3.3:[11] 同档/1费三相位前置臂
            if _p1_early_buy_exempt(cand, working, state, session,
                                    registry, auth):
                return None    # W179/ADR-0372:早期买入门放行(同息档)
            if _p2_core_firstpiece_exempt(cand, working, state, session,
                                          registry, auth):
                return None    # W194/ADR-0378:P2 核心件首件同档放行
            shortfall = floor + cost - working.gold
            return RejectReason('gold_floor', 'gold', shortfall,
                                f'金<{floor}(地板;现{working.gold}-费{cost})')
        return None
    if name == 'interest_rule':
        # [11][17][28] → W119/ADR-0347 EV 授权(W113 §3.2(d)):
        # 跨档消费判 EV = V − C_interest,V = 层3分剥离息分量(bd['int_emb'],
        # scoring 声明自己嵌入的息分量,单一源),C_interest = 跨档数 × R
        # (R=跨位面剩余节点,ev.interest_cost)。EV>0 放行(含破息),
        # ≤0 拒——恒拒语义退场,[11] 同档/1费/满息结余特例**原样保留**
        # (它们是 EV 规则的零息损特例)。升级(levelup)不辖——升级的
        # 总账在 boss_levelup_ban 块的 levelup_ev_authorized(平台账,
        # 含息引擎未立的延迟损,口径不同,双门并设会双重计罚)。
        # war/boss/应急覆盖态交给 gold_floor 的地板,不辖息档(原语义)。
        cost = _cost_of(cand, working)
        if cost <= 0 or cand.tag in ('levelup',):
            return None
        if current_mode(session) != 'economy':
            return None
        if is_emergency(state, registry):
            return None
        if boss_window_active(state, session, registry):
            return None
        # 金<50 时辖权让位 gold_floor 的相位地板(HOARD 摊档/FORM 保险丝)
        # ——此处只辖「从 ≥50 跌破 50」的降息档(原辖域保留)
        if working.gold < registry.interest_floor():
            return None
        after = working.gold - cost
        if after >= registry.interest_floor():
            return None
        if cost == 1:
            return None    # [11] 1 费净0(1★卖出全额退)
        if after // 10 >= (working.gold // 10):
            return None    # 同息档内花费([11] 不损息)
        # W131/ADR-0352 买侧标定:V 取「层3 分剥离息分量」与「组合跳变
        # 金账(bd['form_gold'],scoring 单一源——引擎跳变/进度份额按
        # C 同视界 R 折金)」的较大者;C 用回档折中口径(R_eff=min(R,
        # interest_recovery_rounds))——买是一次性金→板兑换,P6 回档
        # 账辖;「持续低金」的政策态由相位地板辖,不在此重复计罚。
        # 刷新(D)不辖本分支:V_D 批口径+平面 R 上界逐位保留(P5⑤
        # 金 50/51 拒 D 的退化输出,W126 锁②)。EV>0 放行公式不变。
        buy_side = isinstance(a, BuyCard)
        c = interest_cost(
            working.gold, cost, state,
            recovery_rounds=(registry.interest_recovery_rounds
                             if buy_side else None))
        v = val - (bd or {}).get('int_emb', 0.0)
        if buy_side:
            fg = (bd or {}).get('form_gold') or 0.0
            if fg > v:
                v = fg
            # W227/ADR-0400 EV 承接缺口项(设计件 08 §4.2 Phase 1
            # 挂载点 b):P1 末窗投影承接档位未达标时买侧 V 加
            # handoff_ev_gap_bonus×缺口——末窗破息投资授权阈值放宽
            # ([18] 位面末 ALL IN 的承接扩展;[19] 三态谱裁决变量④的
            # 承接位)。非末窗 gap=0 零漂移;只辖买侧(板面投资)——
            # 刷新的搜寻消耗口径不动(ADR-0352 D 平面 R 上界纪律),
            # 升级平台账在 levelup_ev_basis,不在此双计。
            from sr_od.application.currency_war.decision_v2.discipline import (
                p1_directed_downgrade_active,
            )
            from sr_od.application.currency_war.decision_v2.handoff import (
                handoff_gate_gap,
            )
            _gap = handoff_gate_gap(state, session, registry)
            # 血预算停手·P1-a 末窗支出降格(设计件 12 §5.3;ADR-0451):
            # 缺口项是承接门定向投资授权的破息放宽面,血预算不足帧
            # 同步降格(战力投资的息豁免授权停;血线胜,与息线门 AND)。
            if _gap > 0 and not p1_directed_downgrade_active(state, registry):
                v += registry.handoff_ev_gap_bonus * _gap
                if auth is not None:
                    auth['handoff_gap'] = _gap   # 授权依据 trace(判读)
        ev = v - c
        if ev > 0:
            if auth is not None:
                auth['ev_auth'] = round(ev, 1)   # 授权依据 trace(放行)
            return None    # EV 授权放行(含破息)
        return RejectReason('interest_rule', '', 0,
                            f'EV≤0 破息拒(V{v:.1f}-C{c}={ev:.1f},'
                            f'{working.gold}→{after})')
    if name == 'bench_capacity':
        if isinstance(a, BuyCard):
            from sr_od.application.currency_war.cw_state import (
                bench_occupied,
                merge_buy_completes,
            )
            # N1(ADR-0324):容量判据=占用计数——采纳买后 simulate 已把
            # 买入落槽,旧 ``+pending_bench`` 再数一次=双计(恰剩 1 空槽
            # 时误拒第二笔);pending_bench 计数整体删除(现状无「未
            # simulate 的预占」用例)。
            # S3(ADR-0325):**合并买入豁免**——真 merge 候选(同名同 1★
            # 计数==2 且待买 1★)合成净腾 1 槽(净增量 +1−2=−1),满员
            # 也可买;非 merge(含 1× 2★ 加权 2 的误标例)仍按占用拒。
            # W544(ADR-0453):豁免判据升级为 merge_mechanics §2.5 一般式
            # (用户权威裁决「备战满时,触发合成的购买应该被支持,否则
            # 被迫卖有用角色」)——同名同星计数(备战+场上)+本次购买≥3
            # 即允许,k = min(店内张数, 3−已有数 mod 3) 张一次买入,金按
            # k×单价校验(gold_floor/interest_rule 经 _cost_of 同源取数);
            # 不满足合成条件仍拒(ADR-0283 守卫语义保留为兜底)。
            occupied = bench_occupied(working.bench or [])
            if occupied >= registry.bench_capacity \
                    and not merge_buy_completes(a.card.name,
                                                a.card.star or 1,
                                                working.bench,
                                                working.deployed,
                                                working.shop):
                shortfall = occupied - registry.bench_capacity + 1
                return RejectReason('bench_capacity', 'bench', shortfall,
                                    'bench 满(需先腾位;[32] 腾席优先用卖;'
                                    '合成触发购买豁免见 ADR-0453)')
        return None
    if name == 'copies_cap':
        if isinstance(a, BuyCard) and a.card.name:
            copies = sum(getattr(b, 'star', 1) or 1
                         for b in (working.bench or [])
                         if b is not None and b.char_id == a.card.name)
            copies += sum(getattr(d, 'star', 1) or 1
                          for d in (working.deployed or [])
                          if getattr(d, 'char_id', '') == a.card.name)
            if copies + 1 > registry.copies_cap:
                return RejectReason('copies_cap', '', 0,
                                    f'同名副本>={registry.copies_cap}份')
        return None
    if name == 'same_round_mutex':
        # r408 族:同轮已买禁卖 / 已卖禁买(session 集由 strategy 维护)
        # ADR-0337(W82):SellBench 分支读 **working** 槽位(与 index_drift
        # 同快照源)——r408 语义=「卖动作执行时真正卖出的卡」不可为同轮
        # 已买;旧读 state(exec_state)槽位在演进 CompTransaction 腾空槽
        # + 同趟买入同名落槽时短路放行,实卖刚买同名卡(「BUY X→SELL X」
        # 账本,no_same 3/300 残留,seeds 259/304/342)。
        bought = getattr(session, 'v2_round_bought', set()) or set()
        sold = getattr(session, 'v2_round_sold', set()) or set()
        if isinstance(a, SellBench):
            idx = a.bench_idx
            _bc = (working.bench[idx]
                   if 0 <= idx < len(working.bench or []) else None)
            if _bc is not None and _bc.char_id and _bc.char_id in bought:
                return RejectReason('same_round_mutex', '', 0,
                                    f'同轮已买 {_bc.char_id}')
        if isinstance(a, BuyCard) and a.card.name in sold:
            return RejectReason('same_round_mutex', '', 0,
                                f'同轮已卖 {a.card.name}')
        return None
    if name == 'blood_budget_stop':
        # 血预算停手·停升级门(设计件 12 §3.1/§2.3-P1-b;ADR-0448):
        # 候选通道的授权前置拒付——hp ≤ 停升级线(P1/P2 各自线)时
        # 拒绝购买经验,唯一豁免=plane_last_battle ALL IN 窗(谓词内)。
        # 与息线门独立谓词取 AND(血线胜;金侧放行不等于这笔花有正
        # 期望),不是第五种覆盖态:emergency 态内同样生效。拒付行
        # (计数/原因)落披露,模式对齐执行层 level_cap_rejects。
        if isinstance(a, LevelUp) and blood_budget_levelup_blocked(
                state, session, registry):
            from sr_od.application.currency_war.decision_v2.discipline import (
                p1_levelup_stop_hp,
                p2_levelup_stop_hp,
            )
            _line = (p2_levelup_stop_hp(registry) if state.plane == 2
                     else p1_levelup_stop_hp(registry))
            session.v3_blood_budget_rejects = getattr(
                session, 'v3_blood_budget_rejects', 0) + 1
            return RejectReason(
                'blood_budget_stop', '', 0,
                f'血预算停手拒(plane{state.plane} hp{state.hp}'
                f'≤停升级线{_line};P21 h>d·L_c 恒假域,ADR-0448)')
        return None
    if name == 'boss_levelup_ban':
        # W255/ADR-0410([32] 节点无关定调 2026-08-27):旧「boss 窗禁
        # 升级」一刀切禁令臂删除——[32] 消费有效性/腾席优先级是全程通用
        # 纪律,升级是否做 = EV 总账问题(ev.levelup_ev_basis,[12]/[33]
        # 单一裁决点;[32] 病例注:「真病是升完没有能上场的强单位」,
        # 人口位臂①已辖)。约束名保留(审计矩阵 ('slot','boss') 格与
        # 检查器名字空间稳定);本金边际由 boss_floor 地板(覆盖态分派臂,
        # b 类保留)继续兜住。
        if isinstance(a, LevelUp):
            # [12] 追级息引擎门 → EV 总账收编(W119/ADR-0347;A1 镜像
            # 与 E6 latch 一并退场,单一裁决点在 ev.levelup_ev_authorized:
            # [33] 人口位 / DP 花费授权(平台未破)/ 静态 EV 平台账)
            cost = _cost_of(cand)
            from sr_od.application.currency_war.decision_v2.candidates import (
                _target_names,
            )
            _basis = levelup_ev_basis(
                state, session, registry, working.gold, cost,
                _target_names(state, session),
                val=val,
                int_emb=(bd or {}).get('int_emb', 0.0))
            if not _basis:
                return RejectReason(
                    'boss_levelup_ban', '', 0,
                    '息引擎总账拒([12] EV 化:平台账不过/无人口位/金不足)')
            # 授权依据观测(ADR-0354):放行臂名记进动作对象(sim 账本
            # auth 键→检查器 levelup_interest_engine_gate;记录非指令,
            # 行为零改动)。拒绝路径不写(未过账=无授权,检查器侧可见)。
            a.auth_basis = _basis
        return None
    if name == 'deploy_cap':
        if isinstance(a, DeployMove):
            if deployed_occupied(working.deployed or []) >= working.max_units():   # ADR-0392
                return RejectReason('deploy_cap', 'slot', 1,
                                    f'上阵满 cap({working.max_units()})')
        return None
    return None    # 未知约束名:放行(审计表锁名存在)


def _cost_of(cand: Candidate, working: GameState | None = None) -> int:
    a = cand.action
    if isinstance(a, BuyCard):
        # W544(ADR-0453):满栏合成买 k>1 张一次扣款(无价格优惠,
        # merge_mechanics §2.5)——金地板/息账按 k×单价校验;判据单一源
        # = cw_state.merge_buy_completes/merge_buy_k(与 bench_capacity
        # 门同源)。非满栏(working=None 或有余槽)恒 1×(零漂移)。
        if working is not None:
            from sr_od.application.currency_war.cw_state import (
                BENCH_CAPACITY,
                bench_occupied,
                merge_buy_k,
            )
            if bench_occupied(working.bench or []) >= BENCH_CAPACITY:
                return max(1, merge_buy_k(a.card.name, a.card.star or 1,
                                          working.bench, working.deployed,
                                          working.shop)) \
                    * (a.card.cost or 3)
        return a.card.cost or 3
    if isinstance(a, LevelUp):
        return a.cost
    if isinstance(a, RefreshShop):
        return a.cost or 2
    return 0    # 卖/部署:无花费(卖回金)


def _p1_early_buy_exempt(cand: Candidate, working: GameState,
                         state: GameState, session: StrategySession,
                         registry: DecisionV2Registry,
                         auth: dict | None = None) -> bool:
    """W179/ADR-0372 P1 早期新件买入门:gold_floor 拒绝前的逐笔放行判据。

    修 pass_buy 形态(W173/W175:own<门槛=买少了——缺件曾 1-3 费出现在
    店、金 7-15 金穷轮,被 FORM 相位地板 20 一刀切拦掉;[11] 口径:档内
    购买不损息,攒息不该拦无损购买)。轮级窗在
    ``discipline.p1_early_gate_open``(P1 ∧ 派生配方对——**未锁形态期
    同样派生**——∧ 未持有 distinct ≥ k ∧ bench 余槽 ≥1),此处辖逐笔:

    - 常态经济态才放行(非应急/boss 窗/war——[18]/[32] 纪律态优先,
      买入门不越权改它们的地板);FORM 相位地板段是本门主要辖域
      (HOARD 段 [11] 同档例外已在 gold_floor 相位地板分支存在);
    - **买入后同息档**([11] 逐字口径:(working.gold − cost)//10 ==
      working.gold // 10;**不设第二道金常数门**——跨档购买照旧走
      interest_rule 的 EV 授权,不在本门放行);
    - 单轮放行笔数 < ``p1_early_round_cap``(防 r1 扫店;采纳处经
      auth['p1_early'] 计数,session.v2_round_p1_early,轮键重置)。

    授权依据 trace:auth['p1_early'] 进执行 log(判读「为什么放行」)。
    """
    if not isinstance(cand.action, BuyCard):
        return False
    if is_emergency(state, registry) \
            or boss_window_active(state, session, registry) \
            or current_mode(session) != 'economy':
        return False
    gate = p1_early_gate_open(state, session, registry)
    if not gate or cand.action.card.name not in gate:
        return False
    # 同名重复不辖(W175 散买边界③:distinct=对 working 现持判定——同轮
    # 前笔买入后,同名第二笔不再是「未持有新件」,交既有 copy 豁免面,
    # 本门不再授权(3合1 素材语境走正常通道)
    _name = cand.action.card.name
    if _name in ({getattr(d, 'char_id', '') for d in working.deployed or ()}
                 | {b.char_id for b in (working.bench or [])
                    if b is not None}):
        return False
    cost = cand.action.card.cost or 3
    if (working.gold - cost) // 10 != (working.gold or 0) // 10:
        return False    # 跨息档([11]:跨档损息,不走本门)
    if getattr(session, 'v2_round_p1_early', 0) >= registry.p1_early_round_cap:
        return False
    if auth is not None:
        auth['p1_early'] = (f'早期门同息档放行(金{working.gold}-费{cost}'
                            f',对缺{len(gate)})')
    return True


def _press_floor_exempt(cand: Candidate, working: GameState,
                        state: GameState, session: StrategySession,
                        registry: DecisionV2Registry,
                        auth: dict | None = None) -> bool:
    """W300/§3.3(V-B8 修订):[11] 同档/1费零息损**三相位共用前置臂**。

    把 HOARD 分支既有的同档/1费放行(FORM 之外的相位地板域)提升到
    FORM 相位地板段:同息档/1费购买不损息([11] 最高权威口述「档内
    购买不损息」),任何相位都不该被地板拦——修 W281 主根因(FORM 段
    <floor 一刀切把 E02 类无损买全拦)。

    显式裁决(V-B8.2):**豁免保零息损(息档线),不保 form_floor
    本金**——FORM 段允许击穿 20 地板至息档线(form_floor 语义=
    「EV 收益端估乐观时的本金下限」,让位于 [11] 口述;若加
    after≥form_floor 条件,金<20 时恒假,W281 主修归零)。风险防线=
    ①本臂逐轮笔数上限 press_exempt_round_cap ②经济卫生副锚(破息
    轮次占比)A/B 验收兜底。该裁决进 ADR(W300)Considered Options。

    辖域边界:常态经济态才放行(非应急 [18]/非 boss 窗 [32]/非 war
    ——纪律态地板优先,本臂不越权);HOARD 段既有 [11] 臂(相位地板
    域分支)行为不变(V-B8.3),本臂实际辖 FORM 段。总闸=
    registry.press_channel_enabled(与候选层 press 臂捆绑为一臂,
    design §5.1/V-B4 双臂同尺;默认关零漂移)。授权依据 trace
    auth['press_floor_exempt'] 进执行 log。
    """
    if not registry.press_channel_enabled:
        return False
    if not isinstance(cand.action, BuyCard):
        return False
    if is_emergency(state, registry) \
            or boss_window_active(state, session, registry) \
            or current_mode(session) != 'economy':
        return False
    cost = cand.action.card.cost or 3
    if cost != 1 and (working.gold - cost) // 10 != (working.gold or 0) // 10:
        return False    # 跨息档有息损,不走本臂(交既有裁决)
    if getattr(session, 'v2_round_press_exempt', 0) \
            >= registry.press_exempt_round_cap:
        return False    # V-B8.1 逐轮量控:超 cap 豁免失效,回落现行裁决
    if auth is not None:
        auth['press_floor_exempt'] = (
            f'[11] 同档/1费零息损放行(金{working.gold}-费{cost};'
            f'保息档线不保 form_floor 本金,V-B8.2;轮用'
            f'{getattr(session, "v2_round_press_exempt", 0)}'
            f'/{registry.press_exempt_round_cap})')
    return True


def _p2_core_firstpiece_exempt(cand: Candidate, working: GameState,
                               state: GameState,
                               session: StrategySession,
                               registry: DecisionV2Registry,
                               auth: dict | None = None) -> bool:
    """W194/ADR-0378 件3:P2 意向核心**首件**同息档买入门(W183 方向②
    「自然店目标件首件优先买」的实现)。

    病灶(W194 探针,n=10 seeds planes=2):P2 穷轮(gold<50)核心件
    自然出现在店 6 轮漏买 5——HOARD 相位 interest_floor 50 对同档
    ([11] 零息损口径)购买一刀切拦,弃购代价=核心再遇窗口
    (W183:3费@lv6 E=27 次刷新 / 5费 7-8 级 60-180 轮)。

    逐笔判据(与 W179 p1_early 同构,P1 的配方对语义在 P2 换为核心
    目标语义):

    - plane ≥ 2 ∧ 常态经济态(非应急/boss 窗/war——[18]/[32] 优先);
    - 买入件 ∈ 意向核心名集(``candidates._core_names`` 单一源);
    - **首件**:working 现持(deployed∪bench)无同名(镜像 W175
      distinct 对 working 现持判定的纪律);
    - **买入后同息档**([11] 逐字口径;跨档照旧走既有通道,本门
      不设第二道金常数门);
    - 单轮放行 < 1 笔([31]②「目标件刷新出现=唯一最高优先级,
      只买它」;session.v2_round_p2_core,轮键重置)。

    零刷新授权(与 W170/W185 刷门管辖动作不交集);授权依据 trace
    auth['p2_core'] 进执行 log。
    """
    if not registry.p2_core_firstpiece_enabled \
            or state.plane < 2 \
            or not isinstance(cand.action, BuyCard):
        return False
    if is_emergency(state, registry) \
            or boss_window_active(state, session, registry) \
            or current_mode(session) != 'economy':
        return False
    from sr_od.application.currency_war.decision_v2.candidates import (
        _core_names,
    )
    _name = cand.action.card.name
    if _name not in _core_names(session):
        return False
    # 首件判据:对 working 现持(同轮前序买入已反映)
    if _name in ({getattr(d, 'char_id', '') for d in working.deployed or ()}
                 | {b.char_id for b in (working.bench or [])
                    if b is not None}):
        return False
    cost = cand.action.card.cost or 3
    if (working.gold - cost) // 10 != (working.gold or 0) // 10:
        return False    # 跨息档([11]:跨档损息,不走本门)
    if getattr(session, 'v2_round_p2_core', 0) >= 1:
        return False
    if auth is not None:
        auth['p2_core'] = (f'P2 核心首件同息档放行(金{working.gold}'
                           f'-费{cost})')
    return True


def _register_accepted(a: Action, state: GameState,
                       session: StrategySession) -> None:
    """采纳动作的同轮簿记(ADR-0328):登记点=动作采纳处(同一事务域),
    非 decide_prep 尾部——同趟先采纳 BUY X 后,后续 SELL X(段首旧副本)
    候选的 r408 守卫立即可见(no_same_round_buy_sell 回归 96/400 的
    根因:r408 守卫读上一段已买集,同趟 buy+sell 双双过)。对称臂
    (先卖后买不回买)同辖——采纳 SellBench 即登记已卖集。

    BuyCard → v2_round_bought(register_round_bought,轮键校验)+
    engine_seed 购入轮登记(ADR-0289 §5,seed_age_blocked 数据源;
    随采纳处一并完成);SellBench → v2_round_sold(卖名取 state
    快照槽位,与 same_round_mutex 守卫同源)。
    """
    if isinstance(a, BuyCard) and a.card.name:
        register_round_bought([a.card.name], state, session)
        if getattr(a, 'reason', '') in ('engine_seed', 'd2_engine_seed'):
            key = (state.plane, state.round_num)
            if getattr(session, 'v2_round_key', None) == key:
                _log = getattr(session, 'v2_seed_bought', None)
                if _log is None:
                    _log = session.v2_seed_bought = {}
                _prev = _log.get(a.card.name)
                if _prev is not None and _prev[0] == key:
                    _log[a.card.name] = (key, _prev[1] + 1)
                else:
                    _log[a.card.name] = (key, 1)
    elif isinstance(a, SellBench):
        if 0 <= a.bench_idx < len(state.bench or []):
            _bc = state.bench[a.bench_idx]
            if _bc is not None and _bc.char_id:
                register_round_sold([_bc.char_id], state, session)


def arbitrate(scored: list[tuple[Candidate, float, dict]],
              state: GameState, session: StrategySession,
              registry: DecisionV2Registry,
              disc_view: DisciplineView | None = None,
              ) -> ArbiterResult:
    """层4 入口:按分排序→依次裁决→约束收口→执行序列+log。

    ``disc_view``:纪律族视图(strategy 侧传入避免重复评估;None 时
    内部调 assess_discipline 自取——数据通路单一,ADR-0326 方案 B)。
    """
    if disc_view is None:
        from sr_od.application.currency_war.decision_v2.discipline import (
            assess_discipline,
        )
        disc_view = assess_discipline(state, session, registry)
    floor = _active_floor(state, session, registry)
    coverage = ('emergency' if is_emergency(state, registry)
                else 'mode')
    working = state.copy()
    ordered = sorted(scored, key=lambda t: -t[1])
    res = ArbiterResult(coverage=coverage, floor=floor)
    sells_accepted = 0
    refresh_cand: tuple[Candidate, float, dict] | None = None
    for cand, val, bd in ordered:
        verdicts: list[str] = []
        if val <= 0:
            # 评分制语义:非正分候选不执行(相对不动的期望不增;
            # 骨架版防「只剩负 EV 刷新也执行」的段空转)。
            # C 豁免(W242/ADR-0405 C 项,末窗星级定向授权;ADR-0411
            # 起无条件启用):P1 末窗承接缺口 gap>0 时 'copy' 标签买候选
            # (同名副本=升星素材,星级投资的承接价值计入)放行进入约束链
            # ——W231 主因:副本评分零维(merge_progress/core_star/targets
            # 全辖目标集名)被本门结构性拒,到不了 interest_rule 的 EV 账。
            # 防双计:授权值零新增——EV 放行值由 W227 缺口项
            # (handoff_ev_gap_bonus×gap)独担,本门只补「评分零维进不了
            # EV 账」的通道缺口;金地板/copies_cap/bench 容量等约束链
            # 照常辖(放行≠必买)。只辖 'copy' 标签(定向授权,不辖
            # 其它零分候选);非末窗 gap=0 零行为。
            _copy_ok = False
            if cand.tag == 'copy':
                from sr_od.application.currency_war.decision_v2.discipline import (  # noqa: E501
                    p1_directed_downgrade_active,
                )
                from sr_od.application.currency_war.decision_v2.handoff import (  # noqa: E501
                    handoff_gate_gap,
                )
                # 血预算停手·P1-a 末窗支出降格(设计件 12 §5.3;ADR-0451):
                # 末窗血预算不足帧承接授权不豁免——降格面=授权豁免通道,
                # 正分 copy 候选不经此豁免门,不受影响。
                _copy_ok = (handoff_gate_gap(state, session, registry) > 0
                            and not p1_directed_downgrade_active(
                                state, registry))
            # merge 完成豁免(ADR-0438;开关 registry.merge_completion_exempt
            # 默认关=零漂移锚):merge=True 的**买候选**(第三张副本买入即
            # 合成 2★)无条件于末窗 gap 放行——完成价值在星级阶梯
            #(e0/e1/e2 胜率)不在板面差分,评分维对它构造性零增量
            #(merge_progress 只计第 2 份),非正分拒是评分零维测量伪影;
            # 与上面 C 豁免同为「完成素材放行」语义对称。豁免≠必买:
            # 约束链(金地板/copies_cap/bench 容量/息账)照常辖。仅辖
            # BuyCard(synthesize 候选 merge=True 不辖,防语义外溢)。
            _merge_ok = (registry.merge_completion_exempt
                         and cand.merge
                         and isinstance(cand.action, BuyCard))
            # M-A 定向 D 牌授权窗(W252/ADR-0409,W249 诊断修法;
            # ADR-0411 起无条件启用):负分刷新在「授权窗开」时放行进入
            # 收尾裁决(实际放行与预算消耗在收尾块,见下)——W249 H3 病灶
            # 「策略从不支付搜索成本」:追名 peak≥2(某目标件差最后一张
            # 凑 3合1)∧末窗承接缺口 gap>0 时,策略此前把刷新预算分配为
            # 零(全程 0.44 次/局),双核心不可达的主导约束。**只辖刷新维**
            # (防双计,W232 A/B/W242 C 各辖买牌维,互斥边界):本豁免只让
            # 候选越过非正分门,不修改分数、不动买侧授权路径;同一次刷新
            # 只有一个授权来源。辖域=plane==1(应急态不排除:[27] 星级投资
            # 的危机授权先例 ADR-0302 危机买偏置同族,低 hp 出口局恰是
            # W249 病灶人群;金代价由收尾的可负担性下限+局级预算封顶兜住);
            # 非末窗 gap=0 零行为。
            _dir_ok = False
            if cand.tag == 'refresh' and state.plane == 1:
                _dir_ok = directed_refresh_budget(
                    state, session, registry) > 0
            # W332b release 泄息预算(义务通道):FLIP 命中/末窗 slot 守卫
            # 帧的负分刷新凭有界预算越过非正分门(预算扣账与放行在收尾块,
            # 见下;同一刷新只走一条授权来源,M-A 优先)。
            _rel_ok = (cand.tag == 'refresh'
                       and getattr(session, 'v3_release', None) is not None)
            # W611 O1 备战空位填补(ADR-0463):义务通道候选评 0 中性
            # (scoring 单一源,证明背书=溢余段买 1★ 弱占优参数无关)——
            # 凭义务语义越过非正分门(copy 零维豁免同判例);豁免≠必买:
            # 约束链照常辖,金可行性(g_after≥R*)在 gold_floor 的 o1
            # 地板加深处辖。
            _o1_ok = cand.tag == 'o1_bench_fill'
            if not (_copy_ok or _dir_ok or _rel_ok or _merge_ok or _o1_ok):
                res.log.append({'tag': cand.tag, 'score': val,
                                'desc': _describe(cand, state),
                                'accepted': False, 'reject': '非正分',
                                'breakdown': bd})
                continue
        if cand.tag == 'refresh':
            # 刷新放行与否在收尾裁决(段语义:刷后 re-decide)
            refresh_cand = (cand, val, bd)
            continue
        # 索引漂移防护(r408b 同族):紧缩表时代 pop/merge 会左移后续
        # bench 下标——ADR-0316 槽位模型下索引恒稳,本守卫保留作语义
        # 防线(目标名与工作态现槽名不一致仍拒;空槽=已被动过也拒)。
        a = cand.action
        if isinstance(a, (SellBench, DeployMove)):
            intended = cand.breakdown_hint.get('name')
            _bc = (working.bench[a.bench_idx]
                   if 0 <= a.bench_idx < len(working.bench or []) else None)
            cur = _bc.char_id if _bc is not None else None
            if intended and cur != intended:
                verdicts.append(f'index_drift:目标 {intended} '
                                f'现槽 {cur}(槽位已被前序动作消费)')
        # W197/ADR-0380 件①:卖候选采纳点复检——sole_engine_sell_blocked
        # 的下界语义此前只在候选生成(candidates._sell_tag,对批前状态
        # 计数)生效;同段多笔同名 TT 件逐笔合法而聚合跌破 tier
        # (136 r7 两笔三月七,列车在手 3>tier 2 → 卖后 1)。对 working
        # (前序采纳后的状态)复检 = 前序卖出计入计数,批量语义经
        # 逐笔复检实现;flag off 逐位回 W195 后行为。
        if registry.sell_floor_exec_guard_enabled \
                and isinstance(a, SellBench) \
                and cand.tag in ('off_target', 'for_gold', 'free_bench'):
            _fb = (working.bench[a.bench_idx]
                   if 0 <= a.bench_idx < len(working.bench or [])
                   else None)
            if _fb is not None and sole_engine_sell_blocked(
                    _fb, working, registry):
                verdicts.append(
                    f'sell_floor:{_fb.char_id} 在手≤tier 体系件'
                    '(同批前序卖出已计入,ADR-0380)')
        # 方向二/ADR-0433:成型后拆队卖采纳点复检——候选生成对批前状态
        # 评估,同批多笔卖出的聚合净效果经对 working(前序采纳后)逐笔
        # 复检实现(与上一条 sole_engine 复检同构; formed_stop 未激活帧
        # 自动不辖)
        if registry.form_break_sell_blocked_enabled \
                and isinstance(a, SellBench) \
                and cand.tag in ('off_target', 'for_gold', 'free_bench'):
            _fbb = (working.bench[a.bench_idx]
                    if 0 <= a.bench_idx < len(working.bench or [])
                    else None)
            if _fbb is not None and form_break_sell_blocked(
                    _fbb, working, session, registry):
                verdicts.append(
                    f'form_break:{_fbb.char_id} 卖后破成型态'
                    '(同批前序卖出已计入,ADR-0433)')
        auth_note: dict = {}
        for cname in registry.constraints:
            reason = _check_constraint(
                cname, cand, working, state, session, registry,
                val=val, bd=bd, auth=auth_note)
            if reason is not None:
                verdicts.append(f'{cname}:{reason.describe}')
                # 资源型拒绝捕获点①(W52/ADR-0326):仅 resource 非空进
                # rejections(纪律型拒绝不回连);本分支 val>0 已由上文保证
                # (非正分提前 continue)——正分闸(§1.5-2)在捕获层成立。
                if reason.resource:
                    res.rejections.append(Rejection(reason, cand, val))
                break
        accepted = not verdicts
        if accepted and cand.tag in ('off_target', 'for_gold', 'free_bench'):
            if sells_accepted >= registry.sell_top_k:
                accepted = False
                verdicts.append(f'sell_top_k:{registry.sell_top_k}')
        if accepted and cand.tag == 'copy_press':
            # W300/V-B8.1:press 候选逐轮采纳笔数上限(比豁免臂更严一级;
            # 默认 cap=1。session.v2_round_press_copy 轮键重置同 p1_early)
            if getattr(session, 'v2_round_press_copy', 0) \
                    >= registry.press_copy_round_cap:
                accepted = False
                verdicts.append(
                    f'press_copy_cap:{registry.press_copy_round_cap}')
        row = {
            'tag': cand.tag, 'score': val,
            'desc': _describe(cand, state),
            'accepted': accepted,
            'reject': '; '.join(verdicts) if verdicts else '',
            'breakdown': bd,
        }
        if auth_note:
            row['ev_auth'] = auth_note   # 授权依据 trace(ADR-0347)
        res.log.append(row)
        if accepted:
            _a = _materialize(cand, state)
            res.actions.append(_a)
            # W179/ADR-0372:早期买入门的单轮笔数计数(轮键重置见
            # strategy.decide_prep;auth trace 在 row['ev_auth'] 可判读)
            if auth_note.get('p1_early'):
                session.v2_round_p1_early = (
                    getattr(session, 'v2_round_p1_early', 0) + 1)
            # W194/ADR-0378 件3:P2 核心首件门单轮笔数(轮键重置见
            # strategy.decide_prep)
            if auth_note.get('p2_core'):
                session.v2_round_p2_core = (
                    getattr(session, 'v2_round_p2_core', 0) + 1)
            # W300/V-B8:press 通道两臂逐轮笔数(轮键重置见 strategy.
            # decide_prep;[11] 豁免臂=press_exempt_round_cap,press 候选
            # 采纳=press_copy_round_cap)
            if auth_note.get('press_floor_exempt'):
                session.v2_round_press_exempt = (
                    getattr(session, 'v2_round_press_exempt', 0) + 1)
            if cand.tag == 'copy_press':
                session.v2_round_press_copy = (
                    getattr(session, 'v2_round_press_copy', 0) + 1)
            # ADR-0328:采纳即登记(r408 同轮簿记在动作采纳处完成——
            # 同趟后续 SELL/BUY 同名候选的守卫立即可见,不再等
            # decide_prep 尾部统一回写)。
            _register_accepted(_a, state, session)
            working = simulate(working, cand.action)
            if cand.tag in ('off_target', 'for_gold', 'free_bench'):
                sells_accepted += 1
    if refresh_cand is not None:
        cand, val, bd = refresh_cand
        reason = None
        auth_note: dict = {}
        # 血预算停手·搜索型刷新停付(设计件 12 §2.3-P1-c/§3.2;ADR-0451):
        # 刷新收尾的授权前置拒付——血预算不足帧(急救型豁免/ALL IN 豁免
        # 在谓词内)所有刷新授权面(V_D 正分搜索/M-A 定向/release 泄息)
        # 一律停付:血线胜(seam §5.2 独立谓词 AND),M-A 预算不消耗。
        from sr_od.application.currency_war.decision_v2.discipline import (
            blood_budget_refresh_blocked,
        )
        if blood_budget_refresh_blocked(state, session, registry):
            session.v3_blood_budget_refresh_rejects = getattr(
                session, 'v3_blood_budget_refresh_rejects', 0) + 1
            reason = RejectReason(
                'blood_budget_refresh_stop', '', 0,
                f'血预算停手·搜索型刷新停拒(plane{state.plane} '
                f'r{state.round_num} hp{state.hp}'
                f'<{registry.p1_exit_blood_target} 末窗;[31]④/W516,'
                'ADR-0451)')
        # M-A 预算消耗裁决(W252/ADR-0409):非正分刷新能到这里说明已在
        # 非正分门凭预算豁免越过——收尾逐笔扣预算并**取代两道息纪律门**
        # (gold_floor 的 HOARD 攒息拒 / interest_rule 的 EV≤0 拒):
        # 这两道正是「策略从不支付搜索成本」的纪律载体,定向授权的本体
        # 语义=按有界额度显式裁定末窗搜索成本(局级 cap 封顶代价);
        # 放行仍照付刷价(simulate 真值扣金)+可负担性下限(花后 ≥
        # boss_floor,P1 出口金生存边际)兜底。其余约束对 refresh 无涉;
        # 正分刷新(V_D)不进本分支,既有路径逐位不动。
        _ma_ok = False
        if reason is None and val <= 0:
            _b = directed_refresh_budget(state, session, registry) \
                if state.plane == 1 else 0
            if _b > 0:
                _used_r = getattr(session, 'v3_dir_refresh_round', 0)
                _cost = cand.action.cost or 2
                if _used_r < min(registry.directed_refresh_per_round, _b) \
                        and (working.gold or 0) - _cost \
                        >= registry.boss_floor:
                    _ma_ok = True
                    auth_note['dir_refresh'] = (
                        f'M-A 有界预算放行(轮用{_used_r}/'
                        f'{registry.directed_refresh_per_round},'
                        f'局耗{getattr(session, "v3_dir_refresh_used", 0)}'
                        f'/{registry.directed_refresh_game_cap})')
            # W332b release 义务预算(W332b 设计 §②规则4):FLIP 命中帧
            # release 是义务(下界),DP/plan 是许可(上界)——负分刷新在
            # 预算内有界放行(累计刷金 ≤ 预算 ∧ 花后 ≥ boss_floor);
            # 「通道开+预算内按 EV 排序」的中性行为,不预设花满
            # (判据单一源=decision_v2.posture_release.authorize_release_
            # refresh)。与 M-A 互斥:M-A 先判,预算未耗才轮到本臂。
            if not _ma_ok:
                # 息档边界截断(W645 提案 E-v2 消费点 1):release 义务
                # 预算分支是非必要溢余支出,逐笔先过截断门——溢余残差
                # (gold % 10)不足一刷时本笔不放行,余量结转下轮(义务
                # 逐帧重算)。essential 显式传 False;上方 M-A 定向授权
                # 分支 essential=True 不截断、不经本门(末窗无下轮重摇,
                # 截断=定向搜索永久丢失)。
                from sr_od.application.currency_war.decision_v2.economy_cycle import (
                    tier_truncated_spend,
                )
                _cost = cand.action.cost or 2
                if tier_truncated_spend(working.gold or 0, _cost,
                                        essential=False) < _cost:
                    reason = RejectReason(
                        'refresh', '', 0,
                        '息档边界截断:溢余残差不足一刷,'
                        '余量结转下轮(W645 提案 E)')
                else:
                    _rel_note = authorize_release_refresh(
                        session, working.gold or 0,
                        cand.action.cost or 2, registry)
                    if _rel_note:
                        _ma_ok = True
                        auth_note['release'] = _rel_note
            if not _ma_ok:
                reason = RejectReason('refresh', '', 0, '非正分')
        if reason is None:
            for cname in registry.constraints:
                if _ma_ok and cname in ('gold_floor', 'interest_rule'):
                    continue    # M-A 授权面取代两道息纪律门(见上)
                reason = _check_constraint(cname, cand, working, state,
                                           session, registry, val=val, bd=bd,
                                           auth=auth_note)
                if reason is not None:
                    break
        accepted = reason is None
        row = {'tag': 'refresh', 'score': val,
               'desc': f'刷新(-{cand.action.cost or 2}金)',
               'accepted': accepted,
               'reject': reason.describe if reason else '',
               'breakdown': bd}
        if auth_note:
            row['ev_auth'] = auth_note
        res.log.append(row)
        if accepted:
            res.actions.append(cand.action)   # 段尾:刷后 re-decide
            # M-A 预算消耗计数(局级+轮级;轮键 v3_dir_refresh_key 由
            # decide_prep 轮首重置与 p1_early 同式;正分刷新不计入——
            # 只辖 M-A 授权面)
            if auth_note.get('dir_refresh'):
                key = (state.plane, state.round_num)
                if getattr(session, 'v3_dir_refresh_key', None) != key:
                    session.v3_dir_refresh_key = key
                    session.v3_dir_refresh_round = 0
                session.v3_dir_refresh_round = getattr(
                    session, 'v3_dir_refresh_round', 0) + 1
                session.v3_dir_refresh_used = getattr(
                    session, 'v3_dir_refresh_used', 0) + 1
            # E2 息线下定向刷新轮内消耗计数(方向三/ADR-0434;授权点在
            # gold_floor HOARD 分支,轮键 v3_bf_refresh_key 惰性重置同
            # dir_refresh 键式;正分刷新/E3 臂不计入——只辖 E2 授权面)
            if auth_note.get('bf_refresh_e2'):
                _bf_key = (state.plane, state.round_num)
                if getattr(session, 'v3_bf_refresh_key', None) != _bf_key:
                    session.v3_bf_refresh_key = _bf_key
                    session.v3_bf_refresh_round = 0
                session.v3_bf_refresh_round = getattr(
                    session, 'v3_bf_refresh_round', 0) + 1
            # W122 F-01/W120 P8:扑满节点刷新豁免的轮计数(同轮 re-decide
            # 链可见;scoring 豁免门消费,单节点支出 s≤2金辖)。
            # (ADR-0297 局刷新计数 v2_refresh_used 已随 W126/ADR-0349
            # refresh_budget 约束退场删除——无消费点)
            session.v2_round_refreshes = getattr(
                session, 'v2_round_refreshes', 0) + 1
        elif reason.resource:
            # 资源型拒绝捕获点②(N2/S2):refresh 收尾裁决的金拒也是
            # 拒绝事件——漏收则 S2 报警态 refresh 变现链死。
            res.rejections.append(Rejection(reason, cand, val))
    _steady_levelup_pass(working, state, session, registry, res)
    _run_remediation_pass(working, state, session, registry, res,
                          disc_view)
    return res


def _steady_levelup_pass(working: GameState, state: GameState,
                         session: StrategySession,
                         registry: DecisionV2Registry,
                         res: ArbiterResult) -> GameState:
    """[33] 稳态多击组趟(W194/ADR-0378;在补偿趟**之前**——推进后的
    working 回传给补偿趟重验,防双趟各自对着陈旧金位验证)。

    每轮至多一组(``session.v2_steady_lv_used`` 轮键,decide_prep 轮首
    重置——刷后 re-decide 段链不连发);组构造在
    ``remediation.steady_state_levelup_group``,事务性重验与补偿组
    同链(逐动作资源三约束+simulate,任一失败整组放弃)。
    """
    if getattr(session, 'v2_steady_lv_used', False):
        return working
    from sr_od.application.currency_war.decision_v2.remediation import (
        steady_state_levelup_group,
    )
    acts = steady_state_levelup_group(working, state, session, registry)
    if not acts:
        return working
    wk = working
    for a in acts:
        if _resource_blocked(a, wk, state, session, registry) is not None:
            log.info('[cw][d2][steady-lv] r%d 放弃:整组事务性重验失败',
                     state.round_num)
            session.v3_steady_lv_abandoned = getattr(
                session, 'v3_steady_lv_abandoned', 0) + 1
            return working
        wk = simulate(wk, a)
    # 插入位置=首个已采纳 RefreshShop 之前(与补偿组同款:组内动作
    # 语义属旧店段,refresh 后 re-decide 才自洽;无 refresh 末尾追加)
    _first_refresh = next(
        (i for i, a in enumerate(res.actions)
         if isinstance(a, RefreshShop)), None)
    if _first_refresh is None:
        res.actions.extend(acts)
    else:
        res.actions[_first_refresh:_first_refresh] = acts
    session.v2_steady_lv_used = True    # 轮键重置(decide_prep 轮首)
    return wk


def _run_remediation_pass(working: GameState, state: GameState,
                          session: StrategySession,
                          registry: DecisionV2Registry,
                          res: ArbiterResult,
                          disc_view) -> None:
    """层4 末段补偿趟(ADR-0326):拒绝→补裁决,同轮单趟。

    流程(§1.2):rejections 非空 且 本轮补偿未用 → remediation_pass 构造
    补偿动作组 → 逐动作 _check_constraint(资源型三约束)+simulate 推进
    (受益候选最后重验,全过才整组采纳)→ 追加进 res.actions;任一失败
    → 整组放弃(事务性,§1.5-3)+ abandoned 计数 + 遥测 log 行。
    补偿动作不再触发第二次 remediation_pass(结构上不可环)。
    """
    if not res.rejections or getattr(session, 'v2_remedy_used', False):
        return
    acts, rlog = remediation_pass(working, state, session, registry,
                                  res.rejections, disc_view, floor=res.floor)
    if not acts:
        return    # 无补偿动作(弱序降级链尽头/无可卖件)——不记 log
    rej = res.rejections[0]
    # 受益候选重验语义(§1.2):买受益候选(金/槽补偿重发)时,重验在
    # **其自身 simulate 前**的 working 上验证拒绝原因已被补偿动作解除
    # ——买后金已扣,simulate 后重验恒误拒;非重发的补偿组(如 S4 的
    # LevelUp/SwapDeploy——受益 DeployMove 解的是下轮/被换位替代)以
    # 组内逐动作重验为闸(设计 §9-2 自评点:升级跨轮闭环,一致性靠注释)。
    beneficiary_emitted = bool(acts) and _same_target(acts[-1],
                                                      rej.cand.action)
    body = acts[:-1] if beneficiary_emitted else acts
    wk = working
    verdict = True
    for a in body:
        if _resource_blocked(a, wk, state, session, registry):
            verdict = False
            break
        wk = simulate(wk, a)
    if verdict and beneficiary_emitted:
        # 受益候选最后重验(补偿是事务:卖/换全落地后受益候选才可过)
        verdict = _beneficiary_recheck(rej, wk, state, session,
                                       registry) is None
    if verdict:
        # AD9-2-1(方案 D',ADR-0326):补偿组**插入位置=首个已采纳
        # RefreshShop 之前**——补偿的受益候选(买 B)是**旧店**的目标
        # 件,refresh 后店即换,补偿组必须在 refresh 前落地语义才自洽;
        # 本批 actions 无 refresh 则仍末尾追加。v2_remedy_used 置位
        # 语义随之保持正确(补偿真执行了)。
        _first_refresh = next(
            (i for i, a in enumerate(res.actions)
             if isinstance(a, RefreshShop)), None)
        if _first_refresh is None:
            res.actions.extend(acts)
        else:
            res.actions[_first_refresh:_first_refresh] = acts
        # ADR-0328:补偿动作采纳即登记(卖侧补偿器构造时已
        # register_round_sold,此处幂等;买侧受益重发补登
        # v2_round_bought——同趟后续候选的守卫可见)。
        for a in acts:
            _register_accepted(a, state, session)
    else:
        if rlog:
            rlog[-1]['outcome'] = 'abandon'
            rlog[-1]['reason'] = '事务性重验失败(整组放弃)'
        session.v3_remedy_abandoned = getattr(
            session, 'v3_remedy_abandoned', 0) + 1
        log.info('[cw][d2][remedy] r%d 放弃:补偿动作组事务性重验失败',
                 state.round_num)
    res.remediation_log.extend(rlog)
    session.v2_remedy_used = True    # 轮键重置(strategy 轮首已有同族逻辑)


def _same_target(a: Action, benef: Action) -> bool:
    """动作组末元素是否=受益候选的重发(金/槽补偿重发的买)。

    识别=同 BuyCard 同卡(对象/名称;重发用同一 ShopCard 实例)。
    """
    if isinstance(a, BuyCard) and isinstance(benef, BuyCard):
        return (a.card is benef.card
                or bool(a.card.name and a.card.name == benef.card.name))
    return False


_RESOURCE_CONSTRAINTS: tuple[str, ...] = ('gold_floor', 'bench_capacity',
                                          'deploy_cap')


def _resource_blocked(a: Action, working: GameState, state: GameState,
                      session: StrategySession,
                      registry: DecisionV2Registry) -> RejectReason | None:
    """单动作资源型三约束检查(补偿动作重验用;只查 gold/bench/slot)。

    理论不发生(补偿器构造已守卫),兜底闸(§1.2 伪码)禁散写。
    """
    probe = Candidate(action=a, tag='remedy', source='remedy')
    for cname in _RESOURCE_CONSTRAINTS:
        r = _check_constraint(cname, probe, working, state, session,
                              registry)
        if r is not None:
            return r
    return None


def _beneficiary_recheck(rej: Rejection, working: GameState,
                         state: GameState, session: StrategySession,
                         registry: DecisionV2Registry) -> RejectReason | None:
    """受益候选重验(全补偿动作 simulate 后的 working 上,资源型三约束)。"""
    for cname in _RESOURCE_CONSTRAINTS:
        r = _check_constraint(cname, rej.cand, working, state, session,
                              registry)
        if r is not None:
            return r
    return None


def _describe(cand: Candidate, state: GameState) -> str:
    """log 的一行描述(判读直接读)。"""
    a = cand.action
    if isinstance(a, BuyCard):
        extra = ' [3合1]' if cand.merge else ''
        slot = ' [需腾位]' if cand.needs_slot else ''
        return f'买 {a.card.name}({a.card.cost}费){extra}{slot}'
    if isinstance(a, SellBench):
        nm = '?'
        if 0 <= a.bench_idx < len(state.bench or []):
            _bc = state.bench[a.bench_idx]
            if _bc is not None:
                nm = _bc.char_id or '?'
        return f'卖 bench[{a.bench_idx}] {nm}'
    if isinstance(a, LevelUp):
        return f'买经验(-{a.cost}金)'
    if isinstance(a, RefreshShop):
        return f'刷新(-{a.cost or 2}金)'
    if isinstance(a, DeployMove):
        nm = '?'
        if 0 <= a.bench_idx < len(state.bench or []):
            _bc = state.bench[a.bench_idx]
            if _bc is not None:
                nm = _bc.char_id or '?'
        return f'上阵 bench[{a.bench_idx}] {nm}->{a.to_row}'
    return str(a)


def _materialize(cand: Candidate, state: GameState) -> Action:
    """执行体定型:BuyCard 打 reason='d2_<tag>'(账本可归因)。"""
    a = cand.action
    if isinstance(a, BuyCard):
        reason = 'd2_' + cand.tag + ('_merge' if cand.merge else '')
        return BuyCard(a.card, reason=reason)
    return a


def build_audit_report(registry: DecisionV2Registry) -> dict:
    """完备性审计表报告(资源维×回合态维;检查项消费)。

    每格=(约束名…)/('none', 显式原因);空格或约束名不存在=违规。
    """
    matrix: dict[str, dict[str, object]] = {}
    violations: list[str] = []
    known = set(registry.constraints)
    for res_dim in registry.audit_resource_dims:
        row: dict[str, object] = {}
        for st_dim in registry.audit_round_state_dims:
            cell = registry.audit_matrix.get((res_dim, st_dim))
            if cell is None:
                row[st_dim] = None
                violations.append(f'空格:({res_dim},{st_dim})')
                continue
            row[st_dim] = cell
            if not (isinstance(cell, tuple) and cell
                    and cell[0] == 'none'):
                for name in cell:
                    if name not in known:
                        violations.append(
                            f'未知约束 {name}@({res_dim},{st_dim})')
        matrix[res_dim] = row
    return {'matrix': matrix, 'violations': violations,
            'constraints': list(registry.constraints)}
