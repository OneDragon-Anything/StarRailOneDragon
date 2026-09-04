"""V̄ 合成价值链·帧级 horizon 现算(增量 B 重推导,2026-09-04;证明修订
单一源 = p53-frame-horizon-vgap 修订单)。

R1 刷新门的比较项 ``V̄_net(r)`` 为**决策帧现算**(修 A 批确立的形态;
增量 B 按宪法第一条「策略不依赖战力建模」+用户裁定「未证即退役/
A-B 无裁决权」重接地全部因子):

::

    V̄_net(r, plane) = Δp[plane] × 单战价值 × r

    Δp = win_rate_dp_by_plane[plane]
       (成型档条件胜率边际,分位面【推】;P2 fail-closed 钳 0)
    单战价值 = vbar_hp_value_transitional(P15v2 P1 battle CI 下缘,
               P21 1:1 过渡口径) + 连胜金下界(2,表值【注】)

因子处置史(增量 B,2026-09-04):
- ``rung_value`` 档位流(P3 经验拟合)——**退役**:收入三元分解中无
  rung 确定函数(息律边际 0;连胜流已由 Δp 通道计账,再立=双计);
  史料=ADR-0515。
- ``h3_win_rate`` 阶梯(P1 校准/无位面维/rung2 n=9)——被分位面实测
  ``win_rate_dp_by_plane`` 取代:P1 Δp=0.450 [0.274,0.612](冻结语料
  73 局 sha 848dc1aa,局聚类 bootstrap n=2000 seed=20260910;battle-only
  +killed 结算屏权威口径);P2 点估计 −0.197 [−0.498,0.091] 薄桶
  CI 含 0 → fail-closed 钳 0(P1/P2 CI 不重叠=必须分位面;P2 追档
  门实质关闭,与 economy「P2 少刷吃息」共识同向;P2 语料扩至
  n≥40/桶后重拟)。
- ``expected_battle_loss×hp_to_gold``(10.0 未标定×0.5 P3 废溯源)——
  换 ``vbar_hp_value_transitional``(9.59,P15v2 锚+P21 过渡口径,
  λ_death 重锚债挂账,P35_VALIDATION:116 通道;先例=strategy-docs/
  04 §2 收益侧)。

行为差(与旧链 slope=rung_value[2]+Δp×7.0=4.939 对照):P1 新 slope
=0.450×11.59=5.22(CI [3.18,7.10] 覆盖旧值,决策温和变);P2 slope=0
(旧链凭空多记 3 金/轮档位收益+正 Δp,P2 刷新/凑档门收紧关闭——
方向正确的清退)。**旧 P53 连续性锚「r=5 ⇒ 24.70」随 slope 变化作废**
(见 p53 修订单)。
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

#: 连胜金下界的连胜档窗(连胜 2-4 档;表值真源
#: = cw_economy.STREAK_GOLD_TABLE,禁在本模块复制表值)。
#: 窗口下界论证:连胜 0-1 档无弹窗金(不计);5+ 档金更高(排除=
#: 低估方向);取窗内 min=连胜金流的保守下界口径(P53 组成声明沿用)。
_STREAK_FLOOR_WINDOW = slice(2, 5)


def streak_floor_gold() -> int:
    """连胜 2-4 档弹窗金下界(STREAK_GOLD_TABLE 表值 min;零新自由参数)。"""
    return min(STREAK_GOLD_TABLE[_STREAK_FLOOR_WINDOW])


def per_battle_value(registry: DecisionV2Registry) -> float:
    """单战斗节点的金价值(胜率流组成;hp 分量=过渡口径,见模块 docstring)。"""
    return registry.vbar_hp_value_transitional + streak_floor_gold()


def v_bar_net(registry: DecisionV2Registry, r_remaining: int,
              plane: int) -> float:
    """V̄_net 帧级现算(r=决策帧剩余视界;plane=当前位面,分位面 Δp)。

    边界:``r_remaining ≤ 0``(局终帧)⇒ 0——视界耗尽即无跨期价值,
    门自然关(r1 总账恒不过),与 P40 ⑤「本期刷窗用尽即停」同向。
    P2 的 Δp 在注册表已 fail-closed 钳 0(薄桶负点估计禁进账,见
    win_rate_dp_by_plane 注释),本函数不重复钳制。
    """
    dp = registry.win_rate_dp_by_plane.get(plane, 0.0)
    return dp * per_battle_value(registry) * max(0, int(r_remaining))


#: P57 窗口门 V̄ 读法全集(设计出处 = 11_shop_decisions §6;两读法裁决
#: 原=sim A/B(P57),按用户裁定「A/B 无裁决权」降级为**读法②默认+
#: 读法①登记待证**——A/B 结果仅作实现验证不作裁决)。
VBAR_READINGS: tuple[str, ...] = ('per_step', 'frame_horizon')
DEFAULT_VBAR_READING: str = 'frame_horizon'


def window_vbar(registry: DecisionV2Registry, r_remaining: int,
                reading: str = DEFAULT_VBAR_READING,
                plane: int = 1) -> float:
    """窗口门 V̄ 取值(P57 双读法参数化;零新自由参数)。

    读法① = ``v_bar_net(reg, 1)``:链在 r=1 的取值即斜率本身(单步兑现
    价值);读法② = ``v_bar_net(reg, r)``:帧级视界价值。未知读法按缺省
    读法②回落(配置桩脏值不放大为行为面分叉,回落计入消费位申报)。
    """
    if reading == 'per_step':
        return v_bar_net(registry, 1, plane)
    return v_bar_net(registry, r_remaining, plane)


__all__ = ['DEFAULT_VBAR_READING', 'VBAR_READINGS', 'per_battle_value',
           'streak_floor_gold', 'v_bar_net', 'window_vbar']
