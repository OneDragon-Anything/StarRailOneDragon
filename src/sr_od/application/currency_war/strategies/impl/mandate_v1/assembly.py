"""货币战争 mandate_v1 装配点(自 decision_v2.prep_brain 迁入;策略统一
迁移批,底稿 MAP ⓪ A2「Snapshot/TurnState/assemble 三件迁出」的落位)。

装配点管线(蓝图 §1.3):``assemble()``(Snapshot + session → TurnState,
方向/预算投影一次装配)。纪律(蓝图 §2):投影幂等重算、单一写端
(assemble 装配点)、派生值一律不落 session。

- 方向权威 = cw_intention 只读快照(``committed`` 读端 = kernel 单一源);
- 预算权威 = economy_cycle(本包,自 decision_v2 迁入)+ kernel.cw_economy
  确定性接缝;
- 注册桥壳 ``strategies/mandate_v1_strategy.py`` 持 obs→snapshot 半部
  (``decision_assembly.snapshot_from_obs``),本模块持 snapshot→TurnState
  半部——obs→Snapshot→assemble 全链即 mandate_v1 步3 装配缝。
"""
from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_intention import committed_from
from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY
from sr_od.application.currency_war.kernel.cw_state import BenchChar
from sr_od.application.currency_war.strategies.impl.mandate_v1.contracts import (
    Snapshot,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.turn_state import (
    BudgetView,
    DirectionView,
    TurnState,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


def hoard_consumer_domain(direction: DirectionView,
                          full_domain: frozenset[str]) -> frozenset[str]:
    """hoard 买侧消费域(D1 语义):不可得帧走保守域,禁静默空集放行。

    - ``direction.hoard_readable`` True → hoard 目标集(可能为空 = 真无
      囤货目标,语义成立);
    - False(投影失败帧)→ ``full_domain``(调用侧给保守域,如整库可买
      面)——「投影失败」与「真无目标」不再折叠为同一空集表示。
    """
    if direction.hoard_readable:
        return direction.hoard
    return full_domain


def _tracking_view(session: StrategySession, snapshot: Snapshot,
                   ) -> tuple[tuple[BenchChar | None, ...],
                              tuple[BenchChar, ...]]:
    """R2 读口(蓝图 §2/§4.2):tracking 优先,fresh read 补缺。

    exec_state_of(session).tracked_bench_chars / tracked_deployed = bot 执行记录计数器族
    (session 保留清单,非派生值;识别噪声滞回锚)。语义同老栈方向计算
    输入;决策板面输入仍走 snap 新鲜读(批 1 行为等价前提)。
    元素经 ``cw_state.snapshot_copy`` 浅拷贝(W639 C 落码):TurnState 帧
    与 session.tracked_* 断开对象别名——session 侧就地写端(shop 星级/
    装备拼接、deploy_bench 装备覆盖)不再穿透视图,反向亦然。
    """
    from sr_od.application.currency_war.kernel.cw_state import snapshot_copy
    tracked_bench = getattr(exec_state_of(session), 'tracked_bench_chars', None)
    bench = (tuple(None if b is None else snapshot_copy(b)
                   for b in tracked_bench)
             if tracked_bench else tuple(snapshot.bench))
    tracked_dep = getattr(exec_state_of(session), 'tracked_deployed', None)
    if tracked_dep:
        deployed = tuple(snapshot_copy(d) for d in tracked_dep
                         if d is not None)
    else:
        deployed = tuple(d for d in snapshot.deployed if d is not None)
    return bench, deployed


def _direction(state: Any, session: StrategySession, snapshot: Snapshot,
               ) -> DirectionView:
    """方向投影:cw_intention 只读快照(权威不迁移,只投影)。"""
    from sr_od.application.currency_war.kernel import cw_intention
    from sr_od.application.currency_war.kernel.cw_intention import hoard_target_set

    ist = getattr(state_of(session), 'v3_intention', None)
    locked = ist is not None and getattr(ist, 'phase', '') == 'locked'
    hoard: frozenset[str] = frozenset()
    hoard_readable = True   # D1:可信位——失败帧 False,消费侧走保守域
    if ist is not None:
        try:
            ht = hoard_target_set(state, ist)
            hoard = frozenset(ht.char_targets) | frozenset(ht.equip_targets)
        except Exception:   # noqa: BLE001  投影失败显式暴露(D1):不再静默退空集
            hoard_readable = False
            log.warning('[cw][prep_brain] hoard 投影失败(hoard_readable=False,'
                        '消费侧走保守域)', exc_info=True)
    # F5 清偿(批 3,蓝图 §6):三门模块级 flag 删除、行为无条件化,
    # 旗标快照无生产面——``gates`` 字段保留=契约形状稳定,恒空映射
    # (W629-R2 镜像雷随旗标面一起退役)。
    gates = MappingProxyType({})
    bench_view, deployed_view = _tracking_view(session, snapshot)
    return DirectionView(
        intent=(getattr(ist, 'locked_comp', '') or '') if ist is not None else '',
        locked=locked,
        p1_pair=tuple(getattr(ist, 'p1_pair', ()) or ()) if ist is not None else (),
        hoard=hoard,
        hoard_readable=hoard_readable,
        gates=gates,
        fallback_comp=cw_intention.FALLBACK_COMP_NAME,
        committed=committed_from(session, state),
        bench_view=bench_view,
        deployed_view=deployed_view,
    )


def _budget(state: Any, session: StrategySession,
            registry: DecisionV2Registry) -> BudgetView:
    """预算投影(批 3 预算收权):W611 义务模型为核 + 确定性费用查表两接缝。

    预算权威 = economy_cycle(schedule_upgrade/refresh_ev_budget 确定性
    核 + R*/义务链);DP 姿态供给已退役(原「帧内单一求解、四路共用」
    的 W620 效率热点随核替换消失——确定性核为闭式直算,无 0.3s 求解面,
    效率复核判据:decide 热点回落)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        refresh_ev_budget,
        reserve_cap,
        schedule_upgrade,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.economy_cycle import (
        obligation,
    )
    floor = registry.interest_cap * 10   # 守息线(与 reserve_cap 内部同源派生)
    return BudgetView(
        # P6 注入单源(W636 A):BudgetView 各字段消费同一 registry 实例,
        # 禁混用 state_of(session).v3_registry 死通道 / DEFAULT 缺省表。
        interest_floor=floor,
        reserve_cap=reserve_cap(state, session, registry),
        obligation=obligation(state, session, registry),
        schedule=schedule_upgrade(state, session, registry),
        ev_auth=refresh_ev_budget(state, session, registry),
    )


def assemble(snapshot: Snapshot, session: StrategySession,
             registry: DecisionV2Registry | None = None) -> TurnState:
    """装配点:Snapshot + session → TurnState(方向/预算投影一次算完)。

    幂等:同输入重入返回等值 TurnState(投影重算,不落任何状态)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.adapter import (
        decision_state,
    )

    reg = registry or DEFAULT_REGISTRY
    state = decision_state(snapshot, session)
    return TurnState(
        snap=snapshot,
        direction=_direction(state, session, snapshot),
        budget=_budget(state, session, reg),
    )
