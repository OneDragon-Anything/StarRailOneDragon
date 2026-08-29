"""货币战争 v2 决策装配边界(app 桶)。

承接分包期 5 前原 decision_v2/adapter.py 的「装配侧」半部:决策具现
``DecideAdapter``(策略 decide → 执行器回放绑定)、实机观察 → Snapshot 的
observe 端口 ``snapshot_from_obs``、旧环当权步影子比对(shadow_compare_*)。
纯映射半部(Snapshot→PrepObservation/GameState、PrepAction→AtomOp)留在
decision 桶 ``decision_v2/adapter.py``——它们被决策核(prep_brain)内部消费,
落 app 会造成 decision→app 反向边。

为何在 app:本模块 import prep_actions/prep_director/obs 执行面词汇,且被
prep_director(备战环)消费——两侧都在 app 桶,装配边界归 app 是分包矩阵
(DESIGN 分包 §3.2,app 依一切)的自然落位。
"""
from __future__ import annotations

import contextlib
import copy
from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.decision_v2.adapter import (
    PREP_SUBSTATE_NAME,
    action_to_atomop,
)
from sr_od.application.currency_war.decision_v2.contracts import (
    SNAPSHOT_SCHEMA_VERSION,
    AtomOp,
    Decision,
    RewardSphere,
    Snapshot,
    SubstateClassification,
    SupplyBox,
    Tome,
)
from sr_od.application.currency_war.kernel import cw_telemetry_exit
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    BailToOuter,
    DeferSpheres,
    PrepAction,
    PrepObservation,
)
from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY
from sr_od.application.currency_war.kernel.cw_state import snapshot_copy
from sr_od.application.currency_war.kernel.cw_strategy_session import StrategySession

# ------------------------------------------------------- obs 读口注入(期5 ⑦)

def install_obs_ports() -> None:
    """装配点接通 decision 桶的 obs 读口(生产武装点 = CurrencyWarApp.__init__)。

    分包依赖矩阵禁 decision→obs 直依:决策核只持注入槽
    (``cw_strategy._RESET_PHASE_ROUND_CACHE``),本函数从 obs 桶取实现注入。
    未接通(缺省关)= 新局弃置残留容器时跳过 obs 模块级缓存清理——
    session 全量重建承担状态隔离,仅 last-known-good 观测缓存延用旧值。
    """
    from sr_od.application.currency_war.cw_strategy import set_obs_reset_hook
    from sr_od.application.currency_war.obs.cw_observation import (
        reset_phase_round_cache,
    )
    set_obs_reset_hook(reset_phase_round_cache)


def _registry_of(strategy: Any):
    """策略携带的注册表(DecisionV2Strategy 有 .registry;default 栈退缺省表)。"""
    return getattr(strategy, 'registry', None) or DEFAULT_REGISTRY


def shadow_compare_enabled(strategy: Any) -> bool:
    """影子比对开关(纯诊断工具,sim/离线对拍用;不改任何游戏动作)。"""
    return bool(getattr(_registry_of(strategy), 'director_v2_shadow_compare', False))


# ------------------------------------------------- obs → Snapshot(观察端口)

def snapshot_from_obs(obs: PrepObservation, session: StrategySession,
                      substate_name: str = PREP_SUBSTATE_NAME) -> Snapshot:
    """实机观察视图 → Snapshot(observe 端口;None 语义 = 契约「读不到≠真值」)。

    与 sim 合成器(cw_sim.synthesize_snapshot)共享字段映射语义但**不合并
    实现**:sim 侧恒真位(confident/gold_trusted/shop_open/board…)在本函数
    全部按实机观测原样携带(None 合法)。bench 取紧缩型(仅已识别件,元素
    BenchChar.slot 1-based 保持)。
    """
    from types import MappingProxyType
    st = obs.state
    last = getattr(session, 'last_state', None)
    return Snapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        classification=SubstateClassification(
            name=substate_name, evidence=('prep_director:observe',),
            confident=True),
        plane=(st.plane if st is not None else None)
        or (last.plane if last is not None else 1),
        round_num=(st.round_num if st is not None else None)
        or (last.round_num if last is not None else 1),
        node_type=(st.node_type if st is not None else None)
        or getattr(session, 'node_type_current', None),
        selected_difficulty=(st.selected_difficulty if st is not None else ''),
        gold=(st.gold if (st is not None and st.gold_readable) else None),
        gold_trusted=bool(obs.state_gold_trusted),
        streak=(st.streak if st is not None else None),
        level=(st.level if st is not None else None),
        xp_progress=(st.xp_progress if st is not None else None),
        level_up_cost=(st.level_up_cost if st is not None else None),
        bench=tuple(None if b is None else snapshot_copy(b)
                    for b in obs.bench_chars),
        deployed=tuple(None if d is None else snapshot_copy(d)
                       for d in obs.deployed_chars),
        board=(MappingProxyType(dict(st.board))
               if (st is not None and st.board_readable) else None),
        deploy_cap=(st.deploy_cap if st is not None else None),
        deploy_vacancy=obs.deploy_vacancy,
        free_bench_slots=obs.free_bench_slots,
        front_occupied=frozenset(obs.front_occupied),
        back_occupied=frozenset(obs.back_occupied),
        front_size=obs.front_size,
        back_size=obs.back_size,
        shop_open=obs.shop_open,
        shop_cards=None,   # P1 恒 None(PrepObservation 同款)
        spheres=tuple(RewardSphere(color=c, x=p.x, y=p.y, radius=r)
                      for c, p, r in obs.spheres),
        boxes=tuple(SupplyBox(x=p.x, y=p.y) for _s, p in obs.boxes),
        tomes=tuple(Tome(x=p.x, y=p.y) for _s, p in obs.tomes),
        box_overlay_open=obs.box_overlay_open,
        event_overlay=obs.event_overlay,
        hp=(st.hp if (st is not None and st.hp_readable) else None),
        hp_readable=bool(st.hp_readable) if st is not None else False,
    )


# ------------------------------------------------------- decide 适配器(§5)

class DecideAdapter:
    """``decide(snapshot, session) -> Decision`` 的策略具现(现役 = DecisionV2Strategy)。

    - decide:构造 obs-like → 现役 ``strategy.decide_prep_action(obs, session,
      config)``(r412 latch 采样随原函数继承)→ 控制流/原子映射;
    - execute:按 op_key 查绑定表回放 PrepAction → 现役执行器(F3 验证链
      原样);查无绑定 = 框架缺陷路径(progressed=False,由引擎连败链兜)。
    绑定表实例内、每 decide 覆盖——DirectorV2 单线程逐步消费,无并发面。
    """

    def __init__(self, strategy: Any, config: Any, executor: Any) -> None:
        self._strategy = strategy
        self._config = config
        self._executor = executor
        self._binding: dict[str, PrepAction] = {}
        self.last_action: PrepAction | None = None   # 最近一步底层动作(遥测/记账消费)

    def bound_action(self, op_key: str) -> PrepAction | None:
        """op_key → 绑定的 PrepAction(执行侧记账/回放消费;查无 = None)。"""
        return self._binding.get(op_key)

    def decide(self, snapshot: Snapshot,
               session: StrategySession) -> Decision:
        from sr_od.application.currency_war.decision_v2 import prep_brain
        if not snapshot.classification.confident:
            raise ValueError('DecideAdapter.decide:非 confident 快照(框架门失守)')
        # 迁移迁移批 1(守卫分区) 装配点管线:TurnState 一次装配(方向/预算投影)+ _select
        # 复用现役决策核(行为与旧环等价;折叠归迁移迁移批 2(方向层接管))。F3 参数校验经
        # prep_brain validator 钩子(非法 → 空批 stall,旧环拒绝路径同型)。
        turn = prep_brain.assemble(
            snapshot, session, registry=_registry_of(self._strategy))
        decision, action = prep_brain.decide(
            turn, self._strategy, session, self._config,
            validator=(getattr(self._executor, 'validate', None)
                       if self._executor is not None else None))
        self.last_action = action
        if decision.ops:
            self._binding[decision.ops[0].op_key] = action
        return decision

    def execute(self, op: AtomOp) -> tuple[bool, str]:
        """绑定回放执行(op_key → PrepAction → 现役执行器)。"""
        action = self._binding.get(op.op_key)
        if action is None:
            return False, f'v2适配器:op_key 无绑定 {op.op_key}'
        return self._executor.execute(action)


# ------------------------------------------------- 影子比对(协议门1;§7)

#: 影子比对运行计数(进程内留证;jsonl 为持久留证)。任何影子路径异常
#: 只计数不影响现役决策(编排者放行条件②:零当权风险)。
SHADOW_STATS: dict[str, int] = {'steps': 0, 'match': 0, 'divergence': 0,
                                'error': 0}


def shadow_compare_step(director: Any, match: Any, obs: PrepObservation,
                        session: StrategySession, config: Any,
                        old_action: PrepAction,
                        out_dir: str | None = None) -> None:
    """旧环当权步的影子比对(全隔离 best-effort;异常只计数不留患)。

    隔离三件:①session 深拷贝(旧 decide 的 prep_phase 前移/r412 latch
    等副作用不重放);②try/except 全包(异常 → error 计数 + log,不上抛);
    ③零执行——影子只产出决策做逐位对照,不落地任何游戏动作。
    比对粒度 = AtomOp/控制流标记(类型+op_key 指纹),同帧两次纯函数 decide。
    """
    SHADOW_STATS['steps'] += 1
    record: dict[str, Any] = {}
    try:
        sess2 = copy.deepcopy(session)
        snap = snapshot_from_obs(obs, sess2)
        adapter = DecideAdapter(match.strategy, config, executor=None)
        decision = adapter.decide(snap, sess2)
        if isinstance(old_action, DeferSpheres):
            old_sig = ('control', 'Defer')
        elif isinstance(old_action, BailToOuter):
            old_sig = ('control', 'Bail')
        else:
            _op = action_to_atomop(old_action)
            old_sig = ('op', _op.op_key, _op.domain)
        if decision.control is not None:
            new_sig = ('control', type(decision.control).__name__)
        elif decision.ops:
            new_sig = ('op', decision.ops[0].op_key, decision.ops[0].domain)
        else:
            new_sig = ('op', '<empty>', '<none>')
        record = {'old': old_sig, 'new': new_sig}
        if old_sig == new_sig:
            SHADOW_STATS['match'] += 1
        else:
            SHADOW_STATS['divergence'] += 1
            log.warning(f'[cw][v2-shadow] 决策分歧 step={SHADOW_STATS["steps"]} '
                        f'old={old_sig} new={new_sig}')
            _shadow_telemetry(director, 'v2_shadow_divergence',
                              f'old={old_sig} new={new_sig}')
        _shadow_record(director, record, out_dir)
    except Exception as e:   # noqa: BLE001  影子隔离:异常绝不影响现役决策
        SHADOW_STATS['error'] += 1
        log.warning(f'[cw][v2-shadow] 影子路径异常(已隔离,计数留证): {e}')
        _shadow_telemetry(director, 'v2_shadow_error', str(e))
        with contextlib.suppress(Exception):
            _shadow_record(director, {'error': str(e)}, out_dir)


def _shadow_telemetry(director: Any, event: str, detail: str) -> None:
    """影子事件落遥测 exec_event(best-effort,失败静默)。
    分包期 4:落账/run_id 归属键经 kernel/cw_telemetry_exit 出口钩子位
    (缺省关=不落行;生产武装点=CurrencyWarApp.__init__)。"""
    with contextlib.suppress(Exception):   # 影子隔离:遥测失败绝不影响现役决策
        cw_telemetry_exit.record_exec_event(
            run_id=cw_telemetry_exit.current_run_id() or '-',
            round_num=0, action_family='V2Shadow', screen='battle_prep',
            event=event, reason=detail[:200])


def _shadow_record(director: Any, record: dict[str, Any],
                   out_dir: str | None) -> None:
    """影子步记录追加 jsonl(协议 §7.1;路径可注入供测试落 tmp_path)。"""
    import json
    import os
    if out_dir is None:
        out_dir = os.path.join('.debug', 'temp', 'currency_war',
                               'w606_stage2_batch3')
    os.makedirs(out_dir, exist_ok=True)
    rid = 'local'
    with contextlib.suppress(Exception):
        # 分包期 4:run_id 归属键经 kernel/cw_telemetry_exit 出口钩子位
        rid = cw_telemetry_exit.current_run_id() or 'local'
    record['ts_step'] = SHADOW_STATS['steps']
    record['stats'] = dict(SHADOW_STATS)
    path = os.path.join(out_dir, f'compare_{rid}.jsonl')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')
