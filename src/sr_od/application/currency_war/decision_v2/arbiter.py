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
    simulate,
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.candidates import Candidate
from sr_od.application.currency_war.decision_v2.discipline import (
    boss_window_active,
    p1_early_gate_open,
    register_round_bought,
    register_round_sold,
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
from sr_od.application.currency_war.decision_v2.phase import (
    Phase,
    derive_phase,
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
    return registry.interest_floor


def _round_state_dims(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> set[str]:
    """当前命中的回合态维(审计表列;'catchup' 已随 W126/ADR-0349 退场)。"""
    dims: set[str] = set()
    if boss_window_active(state, session, registry):
        dims.add('boss')
    if is_emergency(state, registry):
        dims.add('emergency')
    return dims


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
        cost = _cost_of(cand)
        if cost <= 0:
            return None
        floor = _active_floor(state, session, registry)
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
            if working.gold >= registry.interest_floor:
                if working.gold - cost < registry.interest_floor:
                    return None    # 交 interest_rule EV 裁决
            else:
                posture = round_posture(state, session)
                dp_spend = posture is not None and (
                    posture.level_up or posture.refresh_budget > 0)
                if cost == 1 \
                        or (working.gold - cost) // 10 >= working.gold // 10 \
                        or (dp_spend and cand.tag in ('levelup', 'refresh')):
                    return None    # [11] 同档/1费;DP 说花→授权放行(§3.2d)
                return RejectReason(
                    'gold_floor', 'gold',
                    working.gold % 10 + cost,
                    f'HOARD 攒息(金{working.gold}-费{cost} 破档;'
                    f'档线{working.gold // 10 * 10})')
        if working.gold - cost < floor:
            if _p1_early_buy_exempt(cand, working, state, session,
                                    registry, auth):
                return None    # W179/ADR-0372:早期买入门放行(同息档)
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
        cost = _cost_of(cand)
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
        if working.gold < registry.interest_floor:
            return None
        after = working.gold - cost
        if after >= registry.interest_floor:
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
                will_merge_on_buy,
            )
            # N1(ADR-0324):容量判据=占用计数——采纳买后 simulate 已把
            # 买入落槽,旧 ``+pending_bench`` 再数一次=双计(恰剩 1 空槽
            # 时误拒第二笔);pending_bench 计数整体删除(现状无「未
            # simulate 的预占」用例)。
            # S3(ADR-0325):**合并买入豁免**——真 merge 候选(同名同 1★
            # 计数==2 且待买 1★)合成净腾 1 槽(净增量 +1−2=−1),满员
            # 也可买;非 merge(含 1× 2★ 加权 2 的误标例)仍按占用拒。
            occupied = bench_occupied(working.bench or [])
            if occupied >= registry.bench_capacity \
                    and not will_merge_on_buy(a.card, working.bench,
                                              working.deployed):
                shortfall = occupied - registry.bench_capacity + 1
                return RejectReason('bench_capacity', 'bench', shortfall,
                                    'bench 满(需先腾位;[32] 腾席优先用卖)')
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
    if name == 'boss_levelup_ban':
        # [32] boss 轮禁升级腾席(升级 cap 收益下轮才兑现)
        if isinstance(a, LevelUp):
            if boss_window_active(state, session, registry):
                return RejectReason('boss_levelup_ban', '', 0,
                                    'boss 轮禁升级([32])')
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
            if len(working.deployed or []) >= working.max_units():
                return RejectReason('deploy_cap', 'slot', 1,
                                    f'上阵满 cap({working.max_units()})')
        return None
    return None    # 未知约束名:放行(审计表锁名存在)


def _cost_of(cand: Candidate) -> int:
    a = cand.action
    if isinstance(a, BuyCard):
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
            # 骨架版防「只剩负 EV 刷新也执行」的段空转)
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
        if val <= 0:
            reason = RejectReason('refresh', '', 0, '非正分')
        if reason is None:
            for cname in registry.constraints:
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
    _run_remediation_pass(working, state, session, registry, res,
                          disc_view)
    return res


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
