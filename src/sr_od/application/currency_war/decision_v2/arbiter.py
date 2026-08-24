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
from sr_od.application.currency_war.decision_v2.filters import (
    current_mode,
    is_catchup,
    is_emergency,
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
    coverage: str = 'mode'          # emergency / catchup / mode
    floor: int = 0                  # 本轮生效地板
    #: 资源型拒绝事件(补偿的受益候选;W52 回连机制输入,ADR-0326)
    rejections: list[Rejection] = field(default_factory=list)
    #: 补偿日志(§1.1 schema;arbiter 末段补偿趟产出)
    remediation_log: list[dict] = field(default_factory=list)


def _active_floor(state: GameState, session: StrategySession,
                  registry: DecisionV2Registry) -> int:
    """地板分派(覆盖态优先序同层2;[18]/[32]/redesign §5.2)。"""
    if is_emergency(state, registry):
        return registry.rebirth_floor
    node = getattr(session, 'node_type_current', None) or ''
    if node in registry.boss_round_node_types or \
            (state.plane == 1 and state.round_num >= 9):
        return registry.boss_floor
    if current_mode(session) == 'war':
        return registry.war_floor
    # 经济/追赶:阶梯地板(v1 _economy_actions 734-739 同式镜像——
    # ≥50 保满息;10-49 档内全花(配方未满,息让位);<10 零息全花。
    # 骨架初版恒 50 是 smoke「0/N 买入」根因之一:金<53 全拒)
    if state.gold >= registry.interest_floor:
        return registry.interest_floor
    if state.gold >= 10:
        return state.gold % 10
    return 0


def _round_state_dims(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> set[str]:
    """当前命中的回合态维(审计表列)。"""
    dims: set[str] = set()
    node = getattr(session, 'node_type_current', None) or ''
    if node in registry.boss_round_node_types or \
            (state.plane == 1 and state.round_num >= 9):
        dims.add('boss')
    if is_emergency(state, registry):
        dims.add('emergency')
    if is_catchup(state, session, registry):
        dims.add('catchup')
    return dims


def _check_constraint(name: str, cand: Candidate,
                      working: GameState, state: GameState,
                      session: StrategySession,
                      registry: DecisionV2Registry,
                      ) -> RejectReason | None:
    """单约束裁决:通过返回 None,拒绝返回结构化原因(判读可读)。

    W52(ADR-0326):拒绝原因从裸 str 升为 ``RejectReason``——资源型
    约束(gold_floor/bench_capacity/deploy_cap)填 resource/shortfall
    (补偿路由键/缺口量,程序可读);纪律型拒绝(interest_rule/
    copies_cap/same_round_mutex/boss_levelup_ban/refresh_budget)
    resource='' shortfall=0 占位,**不进回连**(§1.1 捕获条件)。
    log 行格式不变(``f'{cname}:{reason.describe}'``)。
    """
    a = cand.action
    if name == 'gold_floor':
        cost = _cost_of(cand)
        if cost <= 0:
            return None
        floor = _active_floor(state, session, registry)
        if working.gold - cost < floor:
            shortfall = floor + cost - working.gold
            return RejectReason('gold_floor', 'gold', shortfall,
                                f'金<{floor}(地板;现{working.gold}-费{cost})')
        return None
    if name == 'interest_rule':
        # [11][17][28]:息档保持——常态(经济)下花费不得降息档,
        # 除非 1 费(卖出全额退=净0)或花后仍 ≥50(满息结余);
        # war/boss/应急覆盖态交给 gold_floor 的地板,不辖息档。
        cost = _cost_of(cand)
        if cost <= 0 or cand.tag in ('levelup',):
            return None
        if current_mode(session) != 'economy':
            return None
        if is_emergency(state, registry):
            return None
        node = getattr(session, 'node_type_current', None) or ''
        if node in registry.boss_round_node_types:
            return None
        # 金<50 时辖权让位 gold_floor 的阶梯地板(v1 语义:档内全花,
        # 配方未满息让位)——此处只保护「从 ≥50 跌破 50」的降息档
        if working.gold < registry.interest_floor:
            return None
        after = working.gold - cost
        if after >= registry.interest_floor:
            return None
        if cost == 1:
            return None    # [11] 1 费净0(1★卖出全额退)
        if after // 10 >= (working.gold // 10):
            return None    # 同息档内花费([11] 不损息)
        return RejectReason('interest_rule', '', 0,
                            f'破息档({working.gold}→{after})')
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
        bought = getattr(session, 'v2_round_bought', set()) or set()
        sold = getattr(session, 'v2_round_sold', set()) or set()
        if isinstance(a, SellBench):
            idx = a.bench_idx
            _bc = (state.bench[idx]
                   if 0 <= idx < len(state.bench or []) else None)
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
            node = getattr(session, 'node_type_current', None) or ''
            if node in registry.boss_round_node_types or \
                    (state.plane == 1 and state.round_num >= 9):
                return RejectReason('boss_levelup_ban', '', 0,
                                    'boss 轮禁升级([32])')
            if registry.levelup_interest_engine_gate:
                # [12] 追级息引擎前置:曾达满息 或 花后仍 ≥50;
                # P1 lv<5 宽松(gate=10,v1 _economy_actions _lvl_gate
                # 同式镜像——否则等级恒 1→cap 1→板面 1 件,团灭)
                cost = _cost_of(cand)
                if state.plane == 1 and state.level < 5:
                    ok = working.gold - cost >= 10
                else:
                    ok = (getattr(session, 'v2_ever_full_interest', False)
                          or working.gold - cost >= registry.interest_floor)
                if not ok:
                    return RejectReason('boss_levelup_ban', '', 0,
                                        '息引擎未立([12]:曾达满息或花后≥50)')
        return None
    if name == 'refresh_budget':
        # ADR-0297 刷新×追级并存(约束侧,方案 a):刷新链曾以
        # re-decide 抽干金→[12] 息引擎门锁死升级(lvl 2 vs v1 7);
        # 两通道并存=刷新留预算、追级留保底金,非二选一。
        if isinstance(a, RefreshShop):
            used = getattr(session, 'v2_refresh_used', 0)
            if registry.refresh_game_cap > 0 \
                    and used >= registry.refresh_game_cap:
                return RejectReason('refresh_budget', '', 0,
                                    (f'局刷新预算{registry.refresh_game_cap}'
                                     f'已用尽({used})'))
            if registry.levelup_reserve_gold > 0 \
                    and state.level < registry.level_max:
                cost = _cost_of(cand)
                if working.gold - cost < registry.levelup_reserve_gold:
                    return RejectReason('refresh_budget', '', 0,
                                        (f'追级保留金(金{working.gold}-费'
                                         f'{cost}<{registry.levelup_reserve_gold})'))
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
                else 'catchup' if is_catchup(state, session, registry)
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
        for cname in registry.constraints:
            reason = _check_constraint(
                cname, cand, working, state, session, registry)
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
        res.log.append({
            'tag': cand.tag, 'score': val,
            'desc': _describe(cand, state),
            'accepted': accepted,
            'reject': '; '.join(verdicts) if verdicts else '',
            'breakdown': bd,
        })
        if accepted:
            res.actions.append(_materialize(cand, state))
            working = simulate(working, cand.action)
            if cand.tag in ('off_target', 'for_gold', 'free_bench'):
                sells_accepted += 1
    if refresh_cand is not None:
        cand, val, bd = refresh_cand
        reason = None
        if val <= 0:
            reason = RejectReason('refresh', '', 0, '非正分')
        if reason is None:
            for cname in registry.constraints:
                reason = _check_constraint(cname, cand, working, state,
                                           session, registry)
                if reason is not None:
                    break
        accepted = reason is None
        res.log.append({'tag': 'refresh', 'score': val,
                        'desc': f'刷新(-{cand.action.cost or 2}金)',
                        'accepted': accepted,
                        'reject': reason.describe if reason else '',
                        'breakdown': bd})
        if accepted:
            res.actions.append(cand.action)   # 段尾:刷后 re-decide
            # ADR-0297:局刷新计数(预算约束的数据源;sim 局=独立
            # session,生产局=session 生命周期同构)
            session.v2_refresh_used = getattr(
                session, 'v2_refresh_used', 0) + 1
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
        nm = ''
        if 0 <= a.bench_idx < len(state.bench or []):
            nm = state.bench[a.bench_idx].char_id or '?'
        return f'卖 bench[{a.bench_idx}] {nm}'
    if isinstance(a, LevelUp):
        return f'买经验(-{a.cost}金)'
    if isinstance(a, RefreshShop):
        return f'刷新(-{a.cost or 2}金)'
    if isinstance(a, DeployMove):
        nm = ''
        if 0 <= a.bench_idx < len(state.bench or []):
            nm = state.bench[a.bench_idx].char_id or '?'
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
