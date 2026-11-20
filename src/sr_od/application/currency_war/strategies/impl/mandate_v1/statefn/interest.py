"""L(g,d,R,Ī) 利息档损失递推(规范解;税基单一源)。

实现已下沉 kernel/cw_economy(下沉保持「kernel 禁 import strategies」
桶依赖矩阵;原 U_L 阈值检验消费面已随排程升级接缝删除)——本模块经
import 重定向保留调用面,消费方零改;单一源在 kernel。
01_math_framework §2 「L(利息档损失)」的
唯一实现语义不变:双轨迹递推(基线守 g* 富余即花 vs 花后守 g*),cap 按
resolved 参数化(默认 5 / 息律投资 10 / 开源节流 9 / 买断制 0——覆写
单一源 = aggregate_economy(session.active_strategies),解析口 =
kernel cw_economy.cap_resolved_of_session)。税基单一源纪律 =
息账与存量清零账互不包含(01_math_framework §6 第 4 条;
交叉核对脚本已随证明体系退役,考古走 git 历史)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_economy import (
    DEFAULT_INTEREST_CAP,
    INTEREST_CAP_SUP,
    interest,
    interest_cap_resolved,
    loss_exact,
    next_interest_line,
    saturation_line,
)

__all__ = [
    'DEFAULT_INTEREST_CAP', 'INTEREST_CAP_SUP', 'interest',
    'interest_cap_resolved', 'loss_exact', 'next_interest_line',
    'saturation_line',
]
