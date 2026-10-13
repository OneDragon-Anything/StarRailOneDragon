"""视界层:R_全局/R_剩余/R_截(场字段自算)+ Δ息流̂ 增量算子。

单一源纪律(R3-2 定理 L-R3-2;位面轮次单一源):长度唯一真值源 =
GameState 场字段 ``node_seq_by_plane``(环境注册刻一次性落全量:修饰局
P1=10/P2=8、默认局 9/7;None = 未注册态,开局 P1 前段/裸 session,读侧
回退默认表 ``cw_node_schedule.PLANE_NODE_TABLES``)。
**本层禁新建任何长度常量**——PLANE_LENGTHS_TRUTH 冻结元组形态已处死
(它是 TOTAL_NODES=27 病灶的复发形态)。

**裁决点 9 契约(框架不供视界量)**:位面轮次族(r_remaining/r_global/
r_remaining_in_plane)已自 kernel/cw_plane_table 退役,本层为策略侧自算
单一消费面(kernel 禁 import strategies 桶边界不动;kernel 判据点就地
求和,禁回引本层)。视界封顶 modeled planes(场字段键集 = P1+P2;P3 =
建模域外 = 运行终局,bot 进 P3 即走结束链)——**位面 ∉ 序列表键集
(含 P3)契约:返回 0**(局终后无剩余轮;禁 KeyError/异常形态)。

Φ(未来纯金流)口径:P51 终态 E[局终金−g](R5-1 定谳);**全量 Φ/W_floor/
W_flow 数值模块私有、类型上不对外暴露**(R5-7/R6-4 收口)——Φ 只在增量
算子(Δ息流̂)与区间敞口比较 API 内部使用,对外输出列不含 Φ 数值。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_node_schedule import (
    PLANE_NODE_TABLES,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import proof_consts
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
    INTEREST_CAP_SUP,
)


def _probe_seqs(session) -> dict[int, tuple[str, ...]] | None:
    """场字段现值读出(裸 session/None 的 duck-typed 读出门面内部自备;
    cw_plane_table._probe_books 同款模式):GameState 本体直读;其余经
    game_state_of 桥;None → 未注册态(读侧回退默认表)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
        game_state_of,
    )
    if session is None:
        return None
    gs = session if isinstance(session, GameState) else game_state_of(session)
    return gs.node_seq_by_plane.value or None


def r_remaining_in_plane(node_in_plane: int, plane_length: int) -> int:
    """本位面剩余节点数(含当前节点;node_in_plane 为 1 基槽序)。"""
    return max(0, plane_length - (node_in_plane - 1))


def r_global(session: object, plane: int, node_in_plane: int) -> int:
    """R_全局 = 当前节点 + 后续位面按**场字段实际长度**求和
    (NMF §2「R_全局」行;裁决点 9:策略侧场字段自算)。

    ``remaining = Σ_{p>plane} len(seq[p]) + (len(seq[plane]) − round + 1)``
    (含当前节点,到局终;与退役前 kernel 实现半部逐值同式)。长度全部
    来自 ``gs.node_seq_by_plane`` 场字段(None 回退默认表),禁任何路径
    引用位面长度字面量替代。视界封顶 modeled planes:序列表键集只有
    P1+P2,P3 虚拟 9 轮先验已随 9 制几何层退役移除(不可达轮不计)。
    **位面 ∉ 序列表键集(含 P3)契约**:返回 0 = 局终后无剩余轮
    (纯防御面,现役调用点先于 kernel 局终短路),禁 KeyError/异常形态。
    """
    seqs = _probe_seqs(session)
    tables = seqs if seqs is not None else PLANE_NODE_TABLES
    seq = tables.get(int(plane))
    if seq is None:
        return 0
    return r_remaining_in_plane(node_in_plane, len(seq)) \
        + sum(len(t) for k, t in tables.items() if k > plane)


def r_remaining(session: object, plane: int, node_in_plane: int) -> int:
    """R_剩余(到局终的总剩余轮数;Φ̂=Ī×R_剩余 的组成因子,R2-8)。"""
    return r_global(session, plane, node_in_plane)


def r_trunc() -> int:
    """R_截 = λ₃ 视界(3 轮窗累积危险率的截断口径,P51 §R/§5-11)。

    值取 proof_consts.LAMBDA3_WINDOW(【证】常数白名单,R17-5)——本层禁
    新建长度常量纪律辖「位面长度」维;R_截系证明声明常数,归宿在白名单模块。
    """
    return proof_consts.LAMBDA3_WINDOW


def delta_interest_flow(refund: int, cap_sup: int = INTEREST_CAP_SUP,
                        trunc: int | None = None) -> int:
    """Δ息流̂ 生产式(R9-3 上界形态;R63-1:cap 消费 cap_sup 而非现值)。

    ``min(⌈r/10⌉, cap_sup) + cap_sup × max(0, R_截−1)``

    方向保证:生产式 ≥ 轨迹真值 Σ_t Δ息_t 且 ≤ 复合安全界 cap_sup×R_截
    (对拍锚 §5.3「Δ息流对拍」行,升帽注入反例锚 R63-1 在测试侧构造)。
    卖出抬高 g 使后续息流严格增加(R5-1);第二项按现值 cap 组装即红。
    """
    if trunc is None:
        trunc = r_trunc()
    first = min(-(-refund // 10), cap_sup)  # ⌈r/10⌉
    return first + cap_sup * max(0, trunc - 1)


def delta_w_increment(lambda_upper: float, refund: int,
                      cap_sup: int = INTEREST_CAP_SUP) -> int:
    """V_power 增量敞口第一项系数通道:λ_U × (refund + Δ息流̂)。

    R5-1 修正后的卖面消费形态——全量 W_floor=λ×(g+Φ) 在 Φ 取下界时卖出门槛
    系统性下偏(fail-open),卖面消费改为**增量敞口**(refund + Δ息流̂ 组装
    保守上界)。λ 端点由 lambda_death 层供给(判据侧禁自持端点,R19-3)。
    """
    return int(lambda_upper * (refund + delta_interest_flow(refund, cap_sup)))


__all__ = [
    'delta_interest_flow', 'delta_w_increment', 'r_global', 'r_remaining',
    'r_remaining_in_plane', 'r_trunc',
]
