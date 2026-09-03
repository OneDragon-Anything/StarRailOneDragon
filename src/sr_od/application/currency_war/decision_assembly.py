"""货币战争 v2 决策装配边界(app 桶)。

承接分包期 5 前原 decision_v2/adapter.py 的「装配侧」半部:决策具现
``DecideAdapter``(策略 decide → 执行器回放绑定)、实机观察 → Snapshot 的
observe 端口 ``snapshot_from_obs``。
纯映射半部(Snapshot→PrepObservation/GameState、PrepAction→AtomOp)留在
decision 桶 ``decision_v2/adapter.py``——它们被决策核(prep_brain)内部消费,
落 app 会造成 decision→app 反向边。

为何在 app:本模块 import prep_actions/cw_screen_prep/obs 执行面词汇,且被
cw_screen_prep(备战环)消费——两侧都在 app 桶,装配边界归 app 是分包矩阵
(DESIGN 分包 §3.2,app 依一切)的自然落位。

旧环当权步影子比对(shadow_compare_* / SHADOW_STATS / v2_shadow_* 遥测
事件)已随旧方案清退批删除:ADR-0465 迁移批 3 后旧环无生产者,比对无意义。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sr_od.application.currency_war.decision.decision_v2.adapter import (
    PREP_SUBSTATE_NAME,
)
from sr_od.application.currency_war.decision.decision_v2.contracts import (
    SNAPSHOT_SCHEMA_VERSION,
    AtomOp,
    Decision,
    RewardSphere,
    Snapshot,
    SubstateClassification,
    SupplyBox,
    Tome,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
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

    同点接通 kernel 侧合成特效帧态门(``cw_reconcile`` 注入槽,分包矩阵禁
    kernel→obs 直依;缺省关 = 门放行走既有连续 2 次确认防抖主干)。

    同点接通期望态留证 sink(``cw_expected_state.set_evidence_sink``,追加
    ``expected_reconcile.jsonl``;缺省关 = 只 log 不落盘,测试零真实 IO)。
    """
    from sr_od.application.currency_war.decision.cw_strategy import set_obs_reset_hook
    from sr_od.application.currency_war.kernel.cw_expected_state import (
        set_evidence_sink,
    )
    from sr_od.application.currency_war.kernel.cw_reconcile import set_merge_effect_gate
    from sr_od.application.currency_war.obs.cw_identity_obs import (
        is_merge_effect_frame,
    )
    from sr_od.application.currency_war.obs.cw_observation import (
        reset_phase_round_cache,
    )
    set_obs_reset_hook(reset_phase_round_cache)
    set_merge_effect_gate(is_merge_effect_frame)

    set_evidence_sink(_expected_reconcile_sink_for_test(
        _reconcile_dir()))


def _reconcile_dir() -> Path:
    """expected_reconcile.jsonl 目录(项目根锚定绝对路径;P4R4 缺陷②:
    旧相对路径依赖 server cwd,cwd 漂移进程把追加写去别处 = 主文件
    「零新增」假截断)。"""
    from one_dragon.utils.file_utils import get_project_root
    return (get_project_root() / '.debug' / 'temp' / 'currency_war')


def _expected_reconcile_sink_for_test(base_dir: Path):
    """sink 工厂(注入点可测形态):返回按 base_dir 追加写的 sink 闭包。

    打开模式恒 'a'(跨进程/跨重启追加不截断——第六局复盘缺陷②,单测
    锁定 append 语义防回退);失败静默(观测面)。生产 = 工厂(项目根
    .debug/temp/currency_war),由 install_obs_ports 装配。"""
    import json

    def _sink(row: dict) -> None:
        try:
            p = Path(base_dir) / 'expected_reconcile.jsonl'
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
        except Exception:  # noqa: BLE001  留证 best-effort
            pass

    return _sink


def _registry_of(strategy: Any):
    """策略携带的注册表(DecisionV2Strategy 有 .registry;default 栈退缺省表)。"""
    return getattr(strategy, 'registry', None) or DEFAULT_REGISTRY


# ------------------------------------------------- obs → Snapshot(观察端口)

def snapshot_from_obs(obs: PrepObservation, session: StrategySession,
                      substate_name: str = PREP_SUBSTATE_NAME) -> Snapshot:
    """实机观察视图 → Snapshot(observe 端口;None 语义 = 契约「读不到≠真值」)。

    与 sim 合成器(runner.synthesize_snapshot)共享字段映射语义但**不合并
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
            name=substate_name, evidence=('cw_screen_prep:observe',),
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

    - decide:黑板写路径兜底(快照→session.prep_obs_frame,仅无帧时)→
      现役 ``strategy.decide_prep_screen(session, config)``(r412 latch 采样随
      原函数继承)→ 控制流/原子映射;
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
        from sr_od.application.currency_war.decision.decision_v2 import prep_brain
        if not snapshot.classification.confident:
            raise ValueError('DecideAdapter.decide:非 confident 快照(框架门失守)')
        # 黑板写路径兜底(W971 §2,P2):黑板决策 decide_prep_screen 读
        # session.prep_obs_frame。生产路径帧由 cw_screen_prep._observe 写
        # (真 obs 原帧);本装配点兜底 = 快照驱动的离线/测试入口
        # (无 _observe 参与)按旧映射重建同源视图写入——保证「同快照同
        # 决策」不变。已有帧(生产/破警告派生帧)不覆盖:帧即最新观察。
        if getattr(session, 'prep_obs_frame', None) is None:
            from sr_od.application.currency_war.decision.decision_v2.adapter import (
                snapshot_to_obs,
            )
            session.prep_obs_frame = snapshot_to_obs(snapshot, session)
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
        """绑定回放执行(op_key → 绑定的 PrepAction → 现役执行器)。

        期望态登记(EXPECTED_STATE §6 对抗 F8)随执行器同源覆盖:本面委托
        ``PrepActionExecutor.execute``,登记钩子挂在那里(单一挂点 = 两执行面
        一次覆盖、零双写);回归锁 = test_cw_expected_state.py 的 assembly 面
        登记 invariants。
        """
        action = self._binding.get(op.op_key)
        if action is None:
            return False, f'v2适配器:op_key 无绑定 {op.op_key}'
        return self._executor.execute(action)
