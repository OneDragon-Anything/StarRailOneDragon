"""V̄ 合成价值链·帧级 horizon 现算(修 A 批;证明单一源 = p53-frame-horizon-vgap)。

R1 刷新门的比较项 ``V̄_net(r)`` 不再用「一次性合成 + rounds_left_est=5
常数」的静态标定值(REFRESH_CFO_REPORT §3/§5 定谳:常数 5 低估决策帧
真实剩余视界——被拦帧 R_剩余 中位 12——系统性压小 V_GAP,P1 过渡带
512/512 帧全拒刷),改为**决策帧现算**:

::

    V̄_net(r) = (rung_value[2] + Δp(e0→e1) × 单战价值) × r

零新自由参数(全部锚 = cw_registry / cw_economy 已收字段,与
``tools/cw/calibration/calib_vuh_v1.py``「V̄ 合成价值链」同链):

- ``rung_value[2]``:e2 变体(合格集条件凑档累计,CALIB_REPORT §2.1
  注入语义沿用);
- ``Δp(e0→e1) = h3_win_rate[1] − h3_win_rate[0]``:注册表胜率阶梯的
  跨档边际;
- ``单战价值 = expected_battle_loss × hp_to_gold + 连胜金下界``
  (连胜金下界 = ``cw_economy.STREAK_GOLD_TABLE`` 连胜 2-4 档弹窗金
  取 min,下界口径——高连胜不计);
- ``r = horizon.r_remaining(session, plane, node)``:schedule_of 单一源
  (本模块不接 session,由消费位现算后传入——纯数函数保持可单测)。

连续性锚:r=5 时本式逐位等于 calib_vuh_v1 的 ``v_bar_e2=24.7``
(旧静态注入值即本链在 r=5 的特例,修 A 只换 horizon 口径不换链)。
**共享面申报**:`cw_registry.rounds_left_est` 本身不动——decision_v2
scoring(层3 板面查表评分)仍消费该字段,属冻结基线;修 A 只移除 cw4
R1 门对该常数的依赖(臂②域内变更,两臂共享字段零触碰)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_economy import (
    STREAK_GOLD_TABLE,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )

#: 连胜金下界的连胜档窗(连胜 2-4 档;P53 单战价值组成声明,表值真源
# = cw_economy.STREAK_GOLD_TABLE,禁在本模块复制表值)
_STREAK_FLOOR_WINDOW = slice(2, 5)


def streak_floor_gold() -> int:
    """连胜 2-4 档弹窗金下界(STREAK_GOLD_TABLE 表值 min;零新自由参数)。"""
    return min(STREAK_GOLD_TABLE[_STREAK_FLOOR_WINDOW])


def per_battle_value(registry: DecisionV2Registry) -> float:
    """单战斗节点的金价值(胜率流组成;calib_vuh_v1「单战价值」同式)。"""
    return (registry.expected_battle_loss * registry.hp_to_gold
            + streak_floor_gold())


def v_bar_net(registry: DecisionV2Registry, r_remaining: int) -> float:
    """V̄_net 帧级现算(r=决策帧剩余视界;连续性锚 r=5 ⇔ 旧注入 24.7)。

    边界:``r_remaining ≤ 0``(局终帧)⇒ 0——视界耗尽即无跨期价值,
    门自然关(r1 总账恒不过),与 P40 ⑤「本期刷窗用尽即停」同向。
    """
    dp = registry.h3_win_rate[1] - registry.h3_win_rate[0]
    return (registry.rung_value[2] + dp * per_battle_value(registry)) \
        * max(0, int(r_remaining))


__all__ = ['per_battle_value', 'streak_floor_gold', 'v_bar_net']
