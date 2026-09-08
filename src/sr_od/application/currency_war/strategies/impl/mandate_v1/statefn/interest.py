"""L(g,d,R,Ī) 息档损失递推(P47 规范解;税基单一源)。

实现已下沉 kernel/cw_economy(ADR-0516:kernel 判据 schedule_upgrade 的
U_L 阈值检验消费 loss_exact,下沉保持「kernel 禁 import strategies」桶
依赖矩阵)——本模块经 import 重定向保留调用面,消费方零改;单一源在
kernel,与 schedule_upgrade 下沉同款先例。NMF §2 「L(息档损失)」的
唯一实现语义不变:双轨迹递推(基线守 g* 溢余即花 vs 花后守 g*),cap 按
resolved 参数化(默认 5 / 息律投资 10 / 开源节流 9 / 买断制 0——覆写
单一源 = aggregate_economy(session.active_strategies),解析口 =
kernel cw_economy.cap_resolved_of_session,ADR-0598)。对拍锚 =
``tools/cw/proofs/p47_check.py`` 的 ``loss_exact``;税基单一源纪律 =
P47 息账与 P51 存量清零账互不包含(NMF §6 第 4 条)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_economy import (
    DEFAULT_INTEREST_CAP,
    INTEREST_CAP_SUP,
    interest,
    interest_cap_resolved,
    loss_exact,
    saturation_line,
)

__all__ = [
    'DEFAULT_INTEREST_CAP', 'INTEREST_CAP_SUP', 'interest',
    'interest_cap_resolved', 'loss_exact', 'saturation_line',
]
