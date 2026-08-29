"""货币战争 prep_brain 备战决策器(纯函数;蓝图 §1 模块①)。

装配点管线(蓝图 §1.3):``assemble()``(Snapshot + session → TurnState,
方向/预算投影一次装配)→ ``decide()``(方向→预算→选择)。纪律(蓝图 §2):
投影幂等重算、单一写端(assemble 装配点)、派生值一律不落 session。

**批 1(接线批)行为语义 = 与旧环等价**(蓝图 §7 批 1 行):``_select()``
仍复用现役决策核(既有 candidates/scoring 经 ``decide_prep_action``),
本批只接线骨架与数据流;决策器接管与四层折叠归批 2(届时 _select 内联
为私有函数,消费点改显式参数)。方向权威 = cw_intention 只读快照;
预算权威 = economy_cycle + posture_release 现役件。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_state import BenchChar
from sr_od.application.currency_war.decision_v2.contracts import (
    Bail,
    Decision,
    Defer,
    Snapshot,
)
from sr_od.application.currency_war.decision_v2.registry import DEFAULT_REGISTRY
from sr_od.application.currency_war.decision_v2.turn_state import (
    BudgetView,
    DirectionView,
    TurnState,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_strategy import StrategySession
    from sr_od.application.currency_war.decision_v2.registry import (
        DecisionV2Registry,
    )


def committed_from(session: StrategySession) -> bool:
    """R1(蓝图 §4.3):``session.dual_track_phase`` 的唯一合法读端。

    返回 committed(已定型;= 非双轨期)。批 1 写端仍是老栈 update_target
    (批 2 随其退役,committed 改装配点从定型信号幂等派生);消费面经本
    读端取值,grep 守卫锁「session.dual_track_phase 直读点归零(本函数
    之外)」——禁 getattr 缺省兜底散落(缺省 False = 恒已定型 = 激进化)。
    """
    return not bool(getattr(session, 'dual_track_phase', False))


def _tracking_view(session: StrategySession, snapshot: Snapshot,
                   ) -> tuple[tuple[BenchChar | None, ...],
                              tuple[BenchChar, ...]]:
    """R2 读口(蓝图 §2/§4.2):tracking 优先,fresh read 补缺。

    session.tracked_bench_chars / tracked_deployed = bot 执行记录计数器族
    (session 保留清单,非派生值;识别噪声滞回锚)。语义同老栈方向计算
    输入;决策板面输入仍走 snap 新鲜读(批 1 行为等价前提)。
    """
    tracked_bench = getattr(session, 'tracked_bench_chars', None)
    bench = tuple(tracked_bench) if tracked_bench else tuple(snapshot.bench)
    tracked_dep = getattr(session, 'tracked_deployed', None)
    if tracked_dep:
        deployed = tuple(d for d in tracked_dep if d is not None)
    else:
        deployed = tuple(d for d in snapshot.deployed if d is not None)
    return bench, deployed


def _direction(state: Any, session: StrategySession, snapshot: Snapshot,
               ) -> DirectionView:
    """方向投影:cw_intention 只读快照(权威不迁移,只投影)。"""
    from sr_od.application.currency_war import cw_intention
    from sr_od.application.currency_war.cw_intention import hoard_target_set

    ist = getattr(session, 'v3_intention', None)
    locked = ist is not None and getattr(ist, 'phase', '') == 'locked'
    hoard: frozenset[str] = frozenset()
    if ist is not None:
        try:
            ht = hoard_target_set(state, ist)
            hoard = frozenset(ht.char_targets) | frozenset(ht.equip_targets)
        except Exception:   # noqa: BLE001  投影只读:失败退空集(不阻塞决策)
            log.warning('[cw][prep_brain] hoard 投影失败(退空集)', exc_info=True)
    gates = {
        name: bool(getattr(cw_intention, name, False))
        for name in ('P1_FINAL_LINE_GATE', 'P1_RECIPE_LOCK',
                     'P1_LOCK_TRANSITION_PAIR')
    }
    bench_view, deployed_view = _tracking_view(session, snapshot)
    return DirectionView(
        intent=(getattr(ist, 'locked_comp', '') or '') if ist is not None else '',
        locked=locked,
        p1_pair=tuple(getattr(ist, 'p1_pair', ()) or ()) if ist is not None else (),
        hoard=hoard,
        gates=gates,
        fallback_comp=cw_intention.FALLBACK_COMP_NAME,
        committed=committed_from(session),
        bench_view=bench_view,
        deployed_view=deployed_view,
    )


def _budget(state: Any, session: StrategySession,
            registry: DecisionV2Registry) -> BudgetView:
    """预算投影:economy_cycle + posture_release 现役件(权威不迁移)。"""
    from sr_od.application.currency_war.decision_v2.economy_cycle import (
        obligation,
        refresh_ev_budget,
        reserve_cap,
        schedule_upgrade,
    )
    floor = registry.interest_cap * 10   # 守息线(与 reserve_cap 内部同源派生)
    return BudgetView(
        interest_floor=floor,
        reserve_cap=reserve_cap(state, session, registry),
        obligation=obligation(state, session, registry),
        schedule=schedule_upgrade(state, session),
        ev_auth=refresh_ev_budget(state, session),
    )


def assemble(snapshot: Snapshot, session: StrategySession,
             registry: DecisionV2Registry | None = None) -> TurnState:
    """装配点:Snapshot + session → TurnState(方向/预算投影一次算完)。

    幂等:同输入重入返回等值 TurnState(投影重算,不落任何状态)。
    """
    from sr_od.application.currency_war.decision_v2.adapter import decision_state

    reg = registry or DEFAULT_REGISTRY
    state = decision_state(snapshot, session)
    return TurnState(
        snap=snapshot,
        direction=_direction(state, session, snapshot),
        budget=_budget(state, session, reg),
    )


def _select(turn: TurnState, strategy: Any, session: StrategySession,
            config: Any) -> Any:
    """选择层(批 1 = 现役决策核复用;批 2 折叠为私有函数族)。

    输入视图经 adapter.snapshot_to_obs 重建(与旧环同一条 obs 通道,
    行为等价由构造保证;单帧等价锁钉住该性质)。
    """
    from sr_od.application.currency_war.decision_v2.adapter import snapshot_to_obs
    return strategy.decide_prep_action(
        snapshot_to_obs(turn.snap, session), session, config)


def decide(turn: TurnState, strategy: Any, session: StrategySession,
           config: Any, validator: Any = None) -> tuple[Decision, Any]:
    """prep_brain 决策入口:TurnState → (Decision, 底层动作)。

    返回动作供执行侧绑定回放(AtomOp 契约无参数字段;控制流决策时
    动作 = DeferSpheres/BailToOuter 实例)。无 session 写端之外的行为
    ——老栈 decide_prep_action 的 session 副作用随批 2 折叠消除。

    ``validator(action) -> str | None``:F3 参数校验钩子(旧环语义:参数
    非法 = 拒绝执行 + 计 stall,不进失败/恢复链);非法 → 返回空 ops 决策
    (执行环空批语义 = 计 stall + 轻观察,与旧环拒绝路径同型)。
    """
    from sr_od.application.currency_war.decision_v2.adapter import action_to_atomop
    from sr_od.application.currency_war.prep_actions import BailToOuter, DeferSpheres

    action = _select(turn, strategy, session, config)
    if validator is not None:
        err = validator(action)
        if err is not None:
            log.warning(f'[cw][prep_brain] 参数非法 {action}: {err} → 空批(stall)')
            return Decision(ops=()), action
    if isinstance(action, DeferSpheres):
        return Decision(control=Defer('球留置')), action
    if isinstance(action, BailToOuter):
        return Decision(control=Bail(action.reason or '未注明')), action
    op = action_to_atomop(action)
    return Decision(ops=(op,)), action
