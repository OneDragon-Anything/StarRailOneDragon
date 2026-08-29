"""决策适配器(W606 阶段2批③;设计单一源 =
``.debug/temp/currency_war/w606_stage2_batch3/DIRECTOR_ADAPTER_DESIGN.md``)。

薄适配层:快照 → 现役 ``decide_prep_action`` 的输入视图(obs-like + 决策
GameState)→ PrepAction → AtomOp/Decision 契约。**策略核零改**——
``DecisionV2Strategy.decide_prep_action`` 原样消费(含息引擎 latch
采样),所有新旧语义差异收敛在本模块的映射表并逐条锁测试。

三个映射面:
- ``snapshot_to_obs`` / ``decision_state`` —— Snapshot → 决策输入(§3);
  含义务清单四字段(dual_track_phase/active_strategies/equips/
  refresh_probs)的 session 显式注入。``active_strategies`` 注入即修复
  现役 ``_pseudo_state`` 漏拷裂缝(持有策略判据在步级路径静默失效为空,
  消费点 = cw_intention._direct_line_qualified / cw_economy.level_up_gate
  /cw_plan._sample_cost)——该修复是相对现役的预期行为差,归对拍
  已知合法差异白名单。
- ``action_to_atomop`` —— PrepAction → AtomOp(§4 映射表)。AtomOp 契约
  无参数字段:op_key 携参数指纹(幂等/屏蔽键粒度 = 动作类型+参数,与现役
  ``action_key`` 同粒度思想),PrepAction 全参数经 ``DecideAdapter`` 的
  绑定表回放给现役执行器。
- ``shadow_compare_enabled`` —— 影子比对开关(纯诊断工具,生产分支随
  旧环批 3 退役;见 registry 字段注释)。

W620 批 1(蓝图 §7 批 1 行):DirectorV2 升正为唯一生产路径(无开关,
``director_v2_prep_enabled`` 已删);decide 通道经 ``prep_brain`` 装配点
(TurnState 一次装配 + _select 复用现役决策核,行为与旧环等价)。

本模块零 SrOperation 依赖、零识别调用;PrepObservation/PrepAction 经
延迟 import 防 prep_director ↔ adapter 循环。
"""
from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_state import BENCH_CAPACITY, GameState
from sr_od.application.currency_war.decision_v2.contracts import (
    AtomOp,
    Decision,
    Snapshot,
)
from sr_od.application.currency_war.decision_v2.registry import DEFAULT_REGISTRY

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_strategy import StrategySession
    from sr_od.application.currency_war.prep_actions import PrepAction
    from sr_od.application.currency_war.prep_director import PrepObservation

#: 决策子态名(适配器只服务备战决策环;分类可信度由框架门在环顶拦截,
#: 进本模块的快照恒 confident——``DecideAdapter.decide`` 断言此前提)。
PREP_SUBSTATE_NAME: str = 'prep_shop'


# ---------------------------------------------------------------- 开关读取

def _registry_of(strategy: Any):
    """策略携带的注册表(DecisionV2Strategy 有 .registry;default 栈退缺省表)。"""
    return getattr(strategy, 'registry', None) or DEFAULT_REGISTRY


def shadow_compare_enabled(strategy: Any) -> bool:
    """影子比对开关(纯诊断工具,sim/离线对拍用;不改任何游戏动作)。"""
    return bool(getattr(_registry_of(strategy), 'director_v2_shadow_compare', False))


# ------------------------------------------------- Snapshot → 决策输入(§3)

def snapshot_to_obs(snapshot: Snapshot, session: StrategySession) -> PrepObservation:
    """Snapshot → 现役 decide_prep_action 的观察视图(设计 §3.1 逐字段表)。

    保守方向裁决(设计钉死,fixture 锁):free_bench_slots None →
    ``BENCH_CAPACITY``(宁多收球——点击失败可自愈、defer 门兜住;不误卖,
    SellBench 不可逆);deploy_vacancy None → 0(不假装有空位)。
    """
    from sr_od.application.currency_war.prep_director import PrepObservation

    if not snapshot.classification.confident:
        raise ValueError(
            'snapshot_to_obs:非 confident 快照不可进 decide(框架门职责,'
            f'name={snapshot.classification.name})')

    st = _anchor_state(snapshot, session)
    spheres = [(s.color, _point(s.x, s.y), s.radius)
               for s in snapshot.spheres]
    boxes = [(None, _point(b.x, b.y)) for b in snapshot.boxes]
    tomes = [(None, _point(t.x, t.y)) for t in snapshot.tomes]
    return PrepObservation(
        state=st,
        state_gold_trusted=bool(snapshot.gold_trusted),
        bench_chars=[b for b in snapshot.bench if b is not None],
        deployed_chars=[d for d in snapshot.deployed if d is not None],
        spheres=list(spheres),
        boxes=list(boxes),
        tomes=list(tomes),
        free_bench_slots=(snapshot.free_bench_slots
                          if snapshot.free_bench_slots is not None
                          else BENCH_CAPACITY),
        deploy_vacancy=(snapshot.deploy_vacancy
                        if snapshot.deploy_vacancy is not None else 0),
        shop_open=snapshot.shop_open,
        box_overlay_open=snapshot.box_overlay_open,
        front_occupied=set(snapshot.front_occupied),
        back_occupied=set(snapshot.back_occupied),
        front_size=snapshot.front_size,
        back_size=snapshot.back_size,
        event_overlay=snapshot.event_overlay,
    )


def _point(x: int, y: int):
    """交互面坐标 → Point(1080p 游戏空间,契约 RewardSphere 同坐标系)。"""
    from one_dragon.base.geometry.point import Point
    return Point(x, y)


def _anchor_state(snapshot: Snapshot, session: StrategySession) -> GameState:
    """快照数值域 → GameState 骨架(plane/round/level 等带 session 锚回退)。"""
    last = getattr(session, 'last_state', None)
    st = GameState()
    st.plane = snapshot.plane or (last.plane if last is not None else 1)
    st.round_num = snapshot.round_num or (last.round_num if last is not None else 1)
    st.node_type = (snapshot.node_type
                    or getattr(session, 'node_type_current', None)
                    or (last.node_type if last is not None else None))
    st.level = snapshot.level or (last.level if last is not None else 1)
    st.xp_progress = snapshot.xp_progress
    st.level_up_cost = snapshot.level_up_cost
    st.selected_difficulty = snapshot.selected_difficulty
    st.streak = snapshot.streak
    # gold:F2 门(gold_trusted=True 才采用,镜像现役 _pseudo_state 保守口径;
    # gold_readable 保真位独立记录「读到了」这一观测事实)。
    if snapshot.gold_trusted and snapshot.gold is not None:
        st.gold = snapshot.gold
    st.gold_readable = snapshot.gold is not None
    st.hp_readable = snapshot.hp_readable
    return st


def decision_state(snapshot: Snapshot, session: StrategySession) -> GameState:
    """Snapshot + session → 策略内部链消费的 GameState(设计 §3.2 逐字段表)。

    与现役 ``_pseudo_state`` 的关键差异 = W598 映射义务清单四字段显式注入;
    其中 ``active_strategies`` 注入修复现役伪态漏拷裂缝(见模块 docstring)。
    """
    from sr_od.application.currency_war.cw_strategy import gated_hp

    st = snapshot_to_obs(snapshot, session).state
    st.board = dict(snapshot.board) if snapshot.board is not None else {}
    st.board_readable = snapshot.board is not None
    st.bench = [b for b in snapshot.bench if b is not None]   # __post_init pad 到定长
    st.deployed = [d for d in snapshot.deployed if d is not None]
    st.deploy_cap = snapshot.deploy_cap
    st.front_max = snapshot.front_size
    st.back_max = snapshot.back_size
    # R1(蓝图 §4.3)+ 批 2 接管:committed 唯一合法读端
    # (prep_brain.committed_from,内部 = cw_intention 权威派生);
    # state.dual_track_phase 为老栈决策核的既有消费面,装配时显式回填
    # (值源 = 方向层权威,P1 同 commit 面)。
    from sr_od.application.currency_war.decision_v2.prep_brain import committed_from
    st.dual_track_phase = not committed_from(session)
    st.active_strategies = list(getattr(session, 'active_strategies', None) or [])
    st.equips = list(getattr(session, 'last_owned_equips', None) or [])
    last = getattr(session, 'last_state', None)
    probs = getattr(last, 'refresh_probs', None) if last is not None else None
    st.refresh_probs = dict(probs) if probs else None
    # hp 过现役同一新鲜度门(session 锚;None 现读=沿用链,禁 0/100 兜底改值)。
    _t = ((st.plane - 1) * 9 + st.round_num) if (st.plane and st.round_num) else None
    _cur = snapshot.hp if snapshot.hp is not None else (
        last.hp if last is not None else 100)
    st.hp = gated_hp(_cur, session, _t, current_readable=snapshot.hp_readable)
    st.hp_readable = snapshot.hp_readable
    return st


# ------------------------------------------------- obs → Snapshot(观察端口)

def snapshot_from_obs(obs: PrepObservation, session: StrategySession,
                      substate_name: str = PREP_SUBSTATE_NAME) -> Snapshot:
    """实机观察视图 → Snapshot(observe 端口;None 语义 = 契约「读不到≠真值」)。

    与 sim 合成器(cw_sim.synthesize_snapshot)共享字段映射语义但**不合并
    实现**:sim 侧恒真位(confident/gold_trusted/shop_open/board…)在本函数
    全部按实机观测原样携带(None 合法)。bench 取紧缩型(仅已识别件,元素
    BenchChar.slot 1-based 保持)。
    """
    from sr_od.application.currency_war.cw_state import snapshot_copy
    from sr_od.application.currency_war.decision_v2.contracts import (
        SNAPSHOT_SCHEMA_VERSION,
        RewardSphere,
        SubstateClassification,
        SupplyBox,
        Tome,
    )
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


# ------------------------------------------- PrepAction → AtomOp 映射(§4)

@dataclass(frozen=True)
class _OpSpec:
    """动作族的 AtomOp 映射规格(设计 §4.1 表的代码化)。"""

    family: str    # op_key 族名(带参数时 op_key = family:参数指纹)
    domain: str


#: 全集映射表(16 动作;键 = PrepAction 类型)。PrepAction 新增动作必须
#: 同步登记(F3 白名单同纪律:漏登记 = 影子侧未知动作缺陷计数,开环侧
#: decide 直接抛错防静默)。
_OP_SPECS: dict[type, _OpSpec] = {}
for _cls, _fam, _dom in [
    ('PickBoxCard', 'pick_box_card', 'interact'),
    ('OpenBox', 'open_box', 'interact'),
    ('OpenTome', 'open_tome', 'interact'),
    ('ClickSpheres', 'click_spheres', 'interact'),
    ('SellBench', 'sell_bench', 'bench'),
    ('SellDeployed', 'sell_deployed', 'bench'),
    ('DeployMove', 'deploy', 'bench'),
    ('LevelUp', 'level_up', 'shop'),
    ('EnsureShopOpen', 'ensure_shop_open', 'shop'),
    ('EnsureShopClosed', 'ensure_shop_closed', 'shop'),
    ('StartBattle', 'start_battle', 'battle'),
    ('RunBuyPhase', 'run_buy_phase', 'shop'),
    ('RunDeploy', 'run_deploy', 'deploy'),
    ('RunEquip', 'run_equip', 'equip'),
]:
    _OP_SPECS[_cls] = _OpSpec(_fam, _dom)


def _param_fingerprint(action: PrepAction) -> str:
    """op_key 参数指纹(与 action_key 同粒度思想:同族不同参数=不同幂等键)。"""
    if not dataclasses.is_dataclass(action):
        return ''
    parts = []
    for f in dataclasses.fields(action):
        v = getattr(action, f.name)
        parts.append('' if v is None else str(v))
    return ':'.join(parts) if any(parts) else ''


def action_to_atomop(action: PrepAction) -> AtomOp:
    """PrepAction → AtomOp(控制流动作不经此——Defer/Bail 走 Decision.control)。"""
    spec = _OP_SPECS.get(type(action).__name__)
    if spec is None:
        raise ValueError(f'action_to_atomop:未登记动作 {type(action).__name__}'
                         '(新动作必须同步 _OP_SPECS,防静默)')
    fp = _param_fingerprint(action)
    return AtomOp(op_key=f'{spec.family}:{fp}' if fp else spec.family,
                  domain=spec.domain)


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
        # 批 1 装配点管线:TurnState 一次装配(方向/预算投影)+ _select
        # 复用现役决策核(行为与旧环等价;折叠归批 2)。F3 参数校验经
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
    from sr_od.application.currency_war.prep_actions import (
        BailToOuter,
        DeferSpheres,
    )
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
        import contextlib
        with contextlib.suppress(Exception):
            _shadow_record(director, {'error': str(e)}, out_dir)


def _shadow_telemetry(director: Any, event: str, detail: str) -> None:
    """影子事件落遥测 exec_event(best-effort,失败静默)。"""
    try:
        from sr_od.application.currency_war import cw_telemetry
        rid = cw_telemetry.current_run_id() or '-'
        cw_telemetry.get_recorder().record_exec_event(
            run_id=rid, round_num=0, action_family='V2Shadow', screen='battle_prep',
            event=event, reason=detail[:200])
    except Exception:   # noqa: BLE001
        pass


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
    try:
        from sr_od.application.currency_war import cw_telemetry
        rid = cw_telemetry.current_run_id() or 'local'
    except Exception:   # noqa: BLE001
        pass
    record['ts_step'] = SHADOW_STATS['steps']
    record['stats'] = dict(SHADOW_STATS)
    path = os.path.join(out_dir, f'compare_{rid}.jsonl')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')
