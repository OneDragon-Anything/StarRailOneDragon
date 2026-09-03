"""货币战争 prep_brain 备战决策器(纯函数;蓝图 §1 模块①)。

装配点管线(蓝图 §1.3):``assemble()``(Snapshot + session → TurnState,
方向/预算投影一次装配)→ ``decide()``(方向→预算→选择)。纪律(蓝图 §2):
投影幂等重算、单一写端(assemble 装配点)、派生值一律不落 session。

**批 2(方向层接管)语义变化**(蓝图 §7 批 2 行 + R1 §4.3):
``committed`` 权威 = cw_intention 派生(``committed_from`` 单点换源,
消费端同 commit 面);意向状态机驱动点显式化(``drive_intention``,
P7:每 game-round 恰一次,锚定决策环入口,段级重入守卫幂等)。
``_select()`` 仍复用现役决策核(四层折叠与 step 级接管归批 3/4);
方向权威 = cw_intention 只读快照;预算权威 = economy_cycle +
posture_release 现役件。
"""
from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.decision.decision_v2.contracts import (
    Bail,
    Decision,
    Defer,
    Snapshot,
)
from sr_od.application.currency_war.decision.decision_v2.turn_state import (
    BudgetView,
    DirectionView,
    TurnState,
)
from sr_od.application.currency_war.kernel.cw_intention import committed_from
from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY
from sr_od.application.currency_war.kernel.cw_state import BenchChar

if TYPE_CHECKING:
    from sr_od.application.currency_war.decision.cw_strategy import StrategySession
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )


def drive_intention(state: Any, session: StrategySession,
                    registry: DecisionV2Registry | None = None) -> None:
    """意向状态机驱动点(P7 契约,批 2 方向层接管):每 game-round 恰一次。

    - 锚定 = 决策环入口(cw_screen_prep 环入口 update_target 之前调用);
      驱动键 = (plane, round_num),段级重入守卫 = session.v3_intention_key
      (与 decision_v2 栈的 update_target 驱动共享同一键面——双驱动并存
      天然幂等,同轮重入不重复计数,miss/冻结分母 = 轮不膨胀);
    - ist 归属(session 保留清单裁决,P4):``v3_intention`` 是跨轮状态机
      计数器族(miss_count/frozen_rounds/evicted/tracks),显式归 session
      保留清单;局级重置由「每局新建 StrategySession」保证,跨局零残留
      (行为锁 test_cw_w628);
    - registry 显式参数(P6):撤销阈值/门判据注入面直达状态机,禁在
      折叠后静默落缺省表——缺省 None 只用于无注入臂的缺省栈。
    """
    from sr_od.application.currency_war.kernel.cw_intention import (
        IntentionState,
        update_intention,
    )
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState):
        ist = IntentionState()
        session.v3_intention = ist
    key = (getattr(state, 'plane', 1), getattr(state, 'round_num', 1))
    if getattr(session, 'v3_intention_key', None) == key:
        return   # 同轮已驱动:幂等出口(重入只保派生视图刷新,不计数)
    session.v3_intention_key = key
    update_intention(state, ist, session, registry=registry)


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

    session.tracked_bench_chars / tracked_deployed = bot 执行记录计数器族
    (session 保留清单,非派生值;识别噪声滞回锚)。语义同老栈方向计算
    输入;决策板面输入仍走 snap 新鲜读(批 1 行为等价前提)。
    元素经 ``cw_state.snapshot_copy`` 浅拷贝(W639 C 落码):TurnState 帧
    与 session.tracked_* 断开对象别名——session 侧就地写端(shop 星级/
    装备拼接、deploy_bench 装备覆盖)不再穿透视图,反向亦然。
    """
    from sr_od.application.currency_war.kernel.cw_state import snapshot_copy
    tracked_bench = getattr(session, 'tracked_bench_chars', None)
    bench = (tuple(None if b is None else snapshot_copy(b)
                   for b in tracked_bench)
             if tracked_bench else tuple(snapshot.bench))
    tracked_dep = getattr(session, 'tracked_deployed', None)
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

    ist = getattr(session, 'v3_intention', None)
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
    from sr_od.application.currency_war.decision.decision_v2.economy_cycle import (
        obligation,
    )
    from sr_od.application.currency_war.kernel.cw_economy import (
        refresh_ev_budget,
        reserve_cap,
        schedule_upgrade,
    )
    floor = registry.interest_cap * 10   # 守息线(与 reserve_cap 内部同源派生)
    return BudgetView(
        # P6 注入单源(W636 A):BudgetView 各字段消费同一 registry 实例,
        # 禁混用 session.v3_registry 死通道 / DEFAULT 缺省表。
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
    批 1 现状:投影已装配、未消费(决策路径仍走老决策核;消费接线归
    批 2)——投影现值仅作装配点数据流与遥测面。
    """
    from sr_od.application.currency_war.decision.decision_v2.adapter import (
        decision_state,
    )

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

    黑板接口(W971 §2,P2):直接调 ``strategy.decide_prep_screen(session,
    config)``——输入 = session.prep_obs_frame(备战观察装配点直写,即
    snapshot 的同一来源 obs 原帧),不再经 snapshot_to_obs 重建视图
    (重建层原是「快照→旧签名」的兼容 shim;黑板化后观察帧即单一输入,
    消费字段两者逐项同源)。方向/预算投影仍走 turn(装配点管线不变)。
    """
    return strategy.decide_prep_screen(session, config)


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
    from sr_od.application.currency_war.decision.decision_v2.adapter import (
        action_to_atomop,
    )
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        BailToOuter,
        DeferSpheres,
    )

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
