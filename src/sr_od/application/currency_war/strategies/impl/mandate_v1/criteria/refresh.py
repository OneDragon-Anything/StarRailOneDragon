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
    ⇒ 不刷(fail-closed)。

    墓碑纪律标注(ADR-0516):生产消费者已随 V̄ 链退役——R1 启动门
    现行判据 = ``r1_commitment_account`` 路径总账(装配在 shop.py),
    本函数零调用面。保留 = 四函数位完备集(r0_stop/r1_start/r2_budget/
    crisis_refresh_invariant,R10-3 缺行封死),禁按旧 EV 正性语义
    复活接线(旧 V̄_net 比较项属已退役的胜率建模链)。
    """
    if ev_positive is None:
        return False, 'ev_unavailable'
    return ev_positive, ''


def r1_commitment_account(total_ledger: float, budget: int) -> tuple[bool, str]:
    """R1 启动门·形式二可负担性判定(ADR-0516;路径总账判据)。

    刷新启动 iff ``c_eff·E(D|L*) + Σ卡费 + L(g, spend, R_剩余, Ī)
    ≤ 可用预算 = g − g*``(g* = saturation_line(cap_resolved)
    = 10×cap_resolved)。装配侧(shop.py)算总账并选 L*(形式二等级
    选择输出:留级账 T_stay vs 升一级账 T_up 取小,升级账含 U_L 及其
    息损);本函数只做比较。输入全为游戏定义量(REFRESH_PROB 池参数/
    XP 表/息律),零胜率建模(用户裁定 2026-09-04;旧 V̄_net 比较项
    已随 V̄ 链退役,statefn/vbar 墓碑)。

    边界:``total_ledger`` 非有限(无可追成员:E=∅ 或该级不出此费)
    ⇒ 不启动——P40 R0-1「合格集空 ⇒ EV 恒负」的刷新侧特例;
    ``budget ≤ 0``(金在息线 g* 及以下)⇒ 恒不启动——息线双侧修正
    (ADR-0516 修正③:停级买牌也压金破息,两侧都过 g* 账)由比较式
    结构承载,不另设门。
    """
    import math

    if not math.isfinite(total_ledger):
        return False, 'no_chaseable_member'
    return ((True, '') if total_ledger <= budget
            else (False, 'account_over_budget'))


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
