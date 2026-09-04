"""视界层:R_全局/R_剩余/R_截(schedule_of 单一源消费)+ Δ息流̂ 增量算子。

单一源纪律(IMPL_DESIGN §6.1 / R3-2 定理 L-R3-2):长度唯一真值源 = 生产
``cw_plane_table.schedule_of(session)``(session 表真值,P3 进表自适应、脏表
夹 [1,9];sim 引擎同源喂 plane_lengths_seen,两路共用同一消费函数)。
**本层禁新建任何长度常量**——PLANE_LENGTHS_TRUTH 冻结元组形态已处死
(它是 TOTAL_NODES=27 病灶的复发形态);未揭晓位面回退直接引
``cw_plane_table.PLANE_FALLBACK_PRIORS``(保守上端语义,R46-1)。

Φ(未来纯金流)口径:P51 终态 E[局终金−g](R5-1 定谳);**全量 Φ/W_floor/
W_flow 数值模块私有、类型上不对外暴露**(R5-7/R6-4 收口)——Φ 只在增量
算子(Δ息流̂)与区间敞口比较 API 内部使用,对外输出列不含 Φ 数值。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_plane_table import (
    schedule_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import proof_consts
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
    INTEREST_CAP_SUP,
)


def r_remaining_in_plane(node_in_plane: int, plane_length: int) -> int:
    """本位面剩余节点数(含当前节点;node_in_plane 为 1 基槽序)。"""
    return max(0, plane_length - (node_in_plane - 1))


def r_global(session: object, plane: int, node_in_plane: int) -> int:
    """R_全局 = 当前节点 + 后续位面按**实际长度**求和(NMF §2「R_全局」行)。

    长度全部来自 ``schedule_of(session)``(启动必载真值);dd-003 旧缺陷
    (cross_plane_remaining_nodes 写死 9)在此修复——禁任何路径引用
    NODES_PER_PLANE 先验替代 session 表。金跨位面继承 ⇒ 视界跨位面求和。
    """
    lengths = schedule_of(session)
    total = r_remaining_in_plane(node_in_plane, lengths[plane - 1])
    for i in range(plane, len(lengths)):
        total += lengths[i]
    return total


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


def _phi_hat(ibar: int, r_rem: int) -> int:
    """Φ̂ 基础流组成下界 = Ī×R_剩余(R2-8 估计器)——**模块私有**(R6-4:
    无裸 Φ̂ 消费位;仅第三口差分复合项经 lambda_death 层以 d̂×(g+Φ̂) 复合
    形态消费,非裸数值)。下划线命名 + 测试静态断言「判据模块禁 import」。"""
    return ibar * r_rem


__all__ = [
    'delta_interest_flow', 'delta_w_increment', 'r_global', 'r_remaining',
    'r_remaining_in_plane', 'r_trunc', 'schedule_of',
]
