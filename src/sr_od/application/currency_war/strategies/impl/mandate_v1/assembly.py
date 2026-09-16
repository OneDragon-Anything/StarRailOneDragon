"""货币战争 mandate_v1 装配点(自 decision_v2.prep_brain 迁入;策略统一
迁移批,底稿 MAP ⓪ A2「Snapshot/TurnState/assemble 三件迁出」的落位)。

装配点管线(蓝图 §1.3):``assemble()``(Snapshot + session → TurnState,
方向/预算投影一次装配)。纪律(蓝图 §2):装配幂等重算、单一写端
(assemble 装配点)、派生值一律不落 session——唯一显式豁免 = 遥测
披露面四字段 + 键戳(``_disclose_budget`` 写点;不入决策输入,裁决
与边界 = ADR-0571)。

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
from sr_od.application.currency_war.kernel.cw_intention import committed_from
from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY
from sr_od.application.currency_war.strategies.impl.mandate_v1.contracts import (
    Snapshot,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.economy_cycle import (
    _budget,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.turn_state import (
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


# (_tracking_view 已随 T-268 三次修正删除:R2「tracking 优先,fresh read
#  补缺」滞回读口的滞回职责已被 T-261 kernel 锚定取代,其「空则回退
#  snapshot.bench」静默回退 = 观察态掩盖路径一并消灭;DirectionView 两视
#  图字段零消费面,恒缺省空元组。策略消费只走 game state——观察态 =
#  GameState.tracked_account_observed(kernel/cw_game_state.py 判定单一源
#  tracked_unobserved),未观察 → 商店门关店回备战。)


def _direction(state: Any, session: StrategySession, snapshot: Snapshot,
               registry: DecisionV2Registry | None = None) -> DirectionView:
    """方向投影:cw_intention 只读快照(权威不迁移,只投影)。"""
    from sr_od.application.currency_war.kernel.cw_intention import hoard_target_set

    ist = getattr(state_of(session), 'v3_intention', None)
    locked = ist is not None and getattr(ist, 'phase', '') == 'locked'
    hoard: frozenset[str] = frozenset()
    hoard_readable = True   # D1:可信位——失败帧 False,消费侧走保守域
    if ist is not None:
        try:
            # P86:session/registry 透传甲臂 G 门(强锁门逐字需要 plane
            # 真值视界与当帧注册表 ε;落地审 F-2 两域禁分叉);投影失败帧
            # 走 hoard_readable=False 保守域,同 D1 面。输入 = 容器单例
            # (prep 链容器化段 2:assemble 一次置顶的决策判据载体直传,
            # 禁二次取容器)。
            ht = hoard_target_set(state, ist, session=session,
                                  registry=registry)
            hoard = frozenset(ht.char_targets) | frozenset(ht.equip_targets)
        except Exception:   # noqa: BLE001  投影失败显式暴露(D1):不再静默退空集
            hoard_readable = False
            log.warning('[cw][prep_brain] hoard 投影失败(hoard_readable=False,'
                        '消费侧走保守域)', exc_info=True)
    # F5 清偿(批 3,蓝图 §6):三门模块级 flag 删除、行为无条件化,
    # 旗标快照无生产面——``gates`` 字段保留=契约形状稳定,恒空映射
    # (W629-R2 镜像雷随旗标面一起退役)。
    gates = MappingProxyType({})
    return DirectionView(
        intent=(getattr(ist, 'locked_comp', '') or '') if ist is not None else '',
        locked=locked,
        p1_pair=tuple(getattr(ist, 'p1_pair', ()) or ()) if ist is not None else (),
        hoard=hoard,
        hoard_readable=hoard_readable,
        gates=gates,
        committed=committed_from(session, state),
    )


def assemble(snapshot: Snapshot, session: StrategySession,
             registry: DecisionV2Registry | None = None) -> TurnState:
    """装配点:Snapshot + session → TurnState(方向/预算投影一次算完)。

    幂等:同输入重入返回等值 TurnState(投影重算)。纪律边界(T-88
    披露面豁免,ADR-0571):决策投影不落 session;唯一例外 =
    ``_disclose_budget`` 写遥测披露面四字段 + 键戳(不入决策输入,
    读端只有 recorder/engine_p1 遥测链)。决策输入 = session 容器单例
    (方向/预算投影直读容器,同帧同视图,一次置顶禁二次取容器)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of,
    )

    reg = registry or DEFAULT_REGISTRY
    gs = game_state_of(session)
    return TurnState(
        snap=snapshot,
        direction=_direction(gs, session, snapshot, reg),
        budget=_budget(gs, session, reg),
    )
