"""criteria/refresh——刷新面(§2.4)。

四函数位(r0_stop/r1_start/r2_budget/crisis_refresh_invariant,
R10-3 缺行封死后的完备集)。D-D(硬节点备战补强门)落点:
``hard_node_reinforce_gate`` 按节点类型(遭遇/boss)接线 P26 备战门 +
P40 刷新门的语境输入(共根组 2:威胁语境进决策输入)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# 硬节点类型(节点行识别词;D-D 语境维)
HARD_NODE_TYPES: frozenset[str] = frozenset({'encounter', 'boss'})


def r0_stop(no_qualifying_set: bool, budget_exhausted: bool) -> bool:
    """R0 维持结构门/R0-2 结构判据(辖刷新循环停止;零参数)。

    合格集空(店面无目标域卡)∨ 预算递推耗尽 ⇒ 停刷。结构位,臂①
    保留(旁路 r1/r2 后无循环可停,递推输入=店面快照+金,仍良定义——
    R10-3 辖域交叠声明)。
    """
    return no_qualifying_set or budget_exhausted


def r1_start(ev_positive: bool | None) -> tuple[bool, str]:
    """付费刷新发射位(r1)。EV 正性判据输入 None(V̄ 封印/未标定)
    ⇒ 不刷(fail-closed)。"""
    if ev_positive is None:
        return False, 'ev_unavailable'
    return ev_positive, ''


def r1_commitment_account(v_gap: float,
                           member_accounts: list[float]) -> tuple[bool, str]:
    """R1 启动门总账判定(P40 ② R1 承诺账形态;标定批落码)。

    形态(k=1 单卡代表):``member_accounts`` = 合格集 E 中每个可追成员
    的承诺账 ``c_eff·E[refreshes|j] + L(g, spend, R_剩余, Ī)``——Σ卡费项
    在 k=1 与 ``V_gap(k=1) = V̄_net + 同成员卡价`` 两侧同成员相消,装配侧
    (shop.py)不再计入;启动 iff ``min(member_accounts) ≤ v_gap``。
    出处:P40-refresh-ev.md ②「R1 完成门(启动判据)」;V_gap 标定带
    [16.7, 24.7](calib_vuh_v1 合成价值链,k≥2 线性外推无标定出处 ⇒ 只
    k=1 形态可落码,cw3 calibration.py V1 同源声明)。
    边界:``member_accounts`` 空/全 inf(无可追成员:E=∅ 或该级不出此费)
    ⇒ 不启动——P40 R0-1「合格集空 ⇒ EV 恒负」的刷新侧特例;多类合格集
    的 E[refreshes] 推广系 P40 结论待办,本门以「逐成员单卡账取 min」
    为其可落码下界(独立近似偏紧向,P40 ①表注)。
    """
    import math

    finite = [a for a in member_accounts if math.isfinite(a)]
    if not finite:
        return False, 'no_chaseable_member'
    best = min(finite)
    return (True, '') if best <= v_gap else (False, 'account_over_vgap')


def r2_budget(gold: int, reserve: int, refresh_cost: int) -> bool:
    """付费刷新预算门(r2;臂①=门关闭)。金−预留 ≥ 刷价才批。"""
    return gold - reserve >= refresh_cost


def crisis_refresh_invariant(gold: int, hp_critical: bool) -> bool:
    """P36-a 危机不变式(executor 结构位承载,本函数=纯数供对拍)。

    危局帧刷新维持结构约束(危机成因不可达优先于危机特设出口,
    [39] 裁定——hp 只进读数位)。返回 True = 不变式成立(允许刷新)。"""
    return not (hp_critical and gold <= 0)


def hard_node_reinforce_gate(node_type: str | None, gold: int,
                             floor_gold: int) -> tuple[bool, str]:
    """D-D 硬节点备战补强门(P26 备战门+P40 刷新门按节点类型接线)。

    下一节点 ∈ HARD_NODE_TYPES ∧ 金 ≥ 守息下界 ⇒ 放行补强意图
    (定向 D 缺档件/治疗件);非硬节点 ⇒ 关。Δp_prep 挂标定
    (标定前形态 = 结构门,数值加权随标定批)。
    """
    if node_type not in HARD_NODE_TYPES:
        return False, 'not_hard_node'
    if gold < floor_gold:
        return False, 'gold_below_floor'
    return True, ''
