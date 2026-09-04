"""货币战争 TurnState:唯一的决策数据件(蓝图 §2;重构单一规格源 =
``.debug/temp/currency_war/w613_strategy_refactor/BLUEPRINT.md`` §1/§2)。

每备战节点入口由 ``prep_brain.assemble()`` 幂等装配:frozen 数据结构 =
Snapshot(已落库 contracts,原样嵌入)+ 方向/预算投影。纪律:

- **幂等重算、单一写端**:投影只在 assemble() 装配点派生,派生值一律
  不落 session(根治跨局污染类缺陷的可变共享态发生机制);
- **快照语义 = 机制事实(W636 C 经 W639 升级落码)**:TurnState 元素经
  ``cw_state.snapshot_copy`` 浅拷贝 + equips 固化 tuple,与
  session.tracked_*(就地写端=shop 星级/装备拼接、deploy_bench 装备
  覆盖)断开对象别名——「快照不在帧间存活」由拷贝保证,不再依赖消费
  纪律约定;成本 <20µs/帧(占帧预算 <0.1%,效率一等验收达标);
  隔离锁=test_cw_w633_migration_b3;
- **投影字段 = 前版方向/预算契约字段照搬**(蓝图 §2 字段清单),丢的
  只是「独立跨层传输权」(消费方全集 = 决策器 + 遥测);
- 本模块纯数据契约:零 IO、零识别调用、零决策逻辑。
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from sr_od.application.currency_war.kernel.cw_state import BenchChar
from sr_od.application.currency_war.strategies.impl.mandate_v1.contracts import Snapshot


@dataclass(frozen=True)
class DirectionView:
    """方向投影(方向权威 = cw_intention,本视图只读快照;蓝图 §2)。

    - ``intent``:当前意向线(COMP_LIBRARY 套名;''=未锁);P1 配方锁局
      另见 ``p1_pair``(体系对,锁定产物形态见 IntentionState 契约)。
    - ``locked``:意向状态机是否已锁(phase=='locked')。
    - ``hoard``:囤货目标集合(hoard_target_set 输出的角色+装备件名并集;
      买侧唯一消费面)。空集=未锁/兜底空窗。
    - ``gates``:资格门快照(只读映射;F5 模块级旗标随批 3 清偿后无
      旗标面,恒空——字段保留为契约形状)。快照语义:装配帧的门状态,
      不在帧间存活。
    - ``fallback_comp``:⑤无信号兜底线(单一源=cw_intention.FALLBACK_COMP_NAME)。
    - ``committed``:R1 显式化(蓝图 §4.3)——P1 攒息语义(True=已定型/
      非双轨期)。装配点单一写端;唯一合法 session 读端 =
      ``prep_brain.committed_from``(grep 守卫锁其余读点归零)。
    - ``bench_view``/``deployed_view``:R2 读口(蓝图 §2/§4.2)——
      tracking 优先(session.tracked_*),fresh read 补缺;语义同老栈
      方向计算输入(方向消费面;决策板面输入仍走 snap 新鲜读)。
      元素 = BenchChar;bench 槽位 None=空槽,deployed 紧缩型(滤 None)。
    """

    intent: str = ''
    locked: bool = False
    p1_pair: tuple[str, ...] = ()
    hoard: frozenset[str] = frozenset()
    hoard_readable: bool = True
    """D1 可信位(供给点清单 D1):False = 本帧 hoard 投影失败——空集不再
    兼任「真无囤货目标」与「不可得」双义,消费侧经
    ``prep_brain.hoard_consumer_domain`` 对不可得帧走保守域(整库)而非
    空集放行。变异探针(投影抛错)下买侧行为 ≠ 空集放行(单帧锁钉)。"""
    gates: Mapping[str, bool] = field(default_factory=lambda: MappingProxyType({}))
    fallback_comp: str = ''
    committed: bool = True
    bench_view: tuple[BenchChar | None, ...] = ()
    deployed_view: tuple[BenchChar, ...] = ()


@dataclass(frozen=True)
class BudgetView:
    """预算投影(现役件 = economy_cycle + posture_release;蓝图 §2/§3)。

    - ``interest_floor``:息线(economy_cycle 口径 = registry.interest_cap
      × 10,守息线同源派生)。
    - ``reserve_cap``:R*(t) = 息线 + 窗口内排程升级费(储备制储备线)。
    - ``obligation``:义务花销 f = min((g − R*)+, C_t);0=无义务帧。
    - ``schedule``:排程升级判据(R4 可替换接缝 ``schedule_upgrade``,
      economy_cycle 单一源)。
    - ``ev_auth``:刷新 EV 授权刷数(R4 可替换接缝 ``refresh_ev_budget``,
      DP 姿态 refresh_budget 单一源;0=不可达/无授权,保守侧)。
    """

    interest_floor: int = 0
    reserve_cap: int = 0
    obligation: int = 0
    schedule: bool = False
    ev_auth: int = 0


@dataclass(frozen=True)
class TurnState:
    """备战决策环步的唯一「件」(蓝图 §2;每节点入口幂等装配)。"""

    snap: Snapshot
    direction: DirectionView
    budget: BudgetView
