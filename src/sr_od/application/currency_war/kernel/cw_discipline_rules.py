"""决策纪律判据族(自 decision_v2.discipline 下沉;DESIGN §3.3-①e)。

现役面 = 位面末战判定(``plane_last_battle``,ALL IN 豁免窗与终局
ALL IN 判定共用的轮维单一源)+ 决策 hp 可信位委托
(``hp_decision_trusted``;现存消费 = 经验批支付门 fail-closed 读数
〔R-1 币种通式保留面〕与濒死带观测谓词〔R-7 观测保留面〕)。旧卖侧
下界判据族(``sole_engine_sell_floor_plan`` 批量逐笔下界 、计数基础
``_sell_floor_counts/_eval/_decrement``、星级加权计数
``star_weighted_copies``)已停用
——全仓零调用核实(2026-09-20;其 decision_v2 消费面先期停用),
判据语义归档见 git 历史。"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )

# ===== 位面末战判定与 hp 政策层读口委托(kernel 内单一源)=====
# plane_last_battle 轮维单一源(nodes_of_plane 真值);hp 可信位委托
# cw_hp_policy.hp_decision_trusted_of(统一 state 经 kernel 政策层
# 单一读口:决策分支禁旁路直读 gs.hp/state.hp,消费同门纪律承接)。

from sr_od.application.currency_war.kernel.cw_hp_policy import (  # noqa: E402
    hp_decision_trusted_of,
)
from sr_od.application.currency_war.kernel.cw_plane_table import (  # noqa: E402
    nodes_of_plane,
)


def hp_decision_trusted(frame: GameState) -> bool:
    """hp 决策可信位(单一源;状态容器一等形态):

    - 委托 ``cw_hp_policy.hp_decision_trusted_of``(定案二单一源:
      ``gs.hp.source in ('observation', 'carried')``,语义见该函数
      docstring)。

    同模块(及跨模块引用点)禁再手写双位判定( A1.1 单一源纪律):
    语义=对账层「沿用真值帧放行 vs 兜底假值帧拒」(
    收紧口径)——prior/logic 支两位皆 False 不评估,carried 沿用帧放行。
    新增 hp 守卫消费点一律走状态容器形态本 helper 或政策层读口。
    """
    return hp_decision_trusted_of(frame)


# p1_crisis_band(P1 ≈22 血危局带判据)不设:经用户裁决不授权、废弃
# (发展为主,不做低血补救)——(b)2/(b)3 消费位永久挂空,处置记录 =
# docs/develop/sr_od/application/currency_war/strategy-docs/14_p1_consume_arms.md §11.8。
# 濒死带观测谓词单一源 = statefn/predicates.p1_blood_floor,不在本模块设第二份。
def plane_last_battle(gs: GameState,
                      session: StrategySession | None) -> bool:
    """位面末最后一战([18]):当前节点=boss 且轮=位面节点数(真值源
    ``nodes_of_plane``——P2 boss@r7 判正;旧按 9 计 P2 永不触发,
    口径断层修复)。签名切状态容器:节点类型/轮次经状态容器读口
    (node_kind_of/round_num_of 镜像,桥视图 kind 空串 = 未识别忠实镜像
    同旧 `or ''`)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        node_kind_of,
        round_num_of,
    )
    # node 单一源 = gs 推导(终态契约 §A′:session.node_type_current 识别
    # 优先源停用,与 flow/entry 等已直读消费点对齐;重新确认非删除——值同源)。
    node = node_kind_of(gs) or ''
    return node in ('boss',) and round_num_of(gs) >= nodes_of_plane(session)

