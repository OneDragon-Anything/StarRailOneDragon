"""【证】证明声明常数白名单(R17-5 第四审计形态;01_math_framework §6 只正典
三形态(【注】/【推】/【拟】),【证】=其外的审计扩展形态,载体=本模块
白名单(映射=ADR-0644 §2 design_economy 行);原 design_economy §E4.0
第 4 条已删档,取回口径=ADR-0644)。

登记对象 = 证明件原文声明的阈值/参数:非注册表机制真值(【注】)、非可从
注册表重算的推导量(【推】)、非标定注入量(【拟】);公理 5(参数溯源)
溯到证明件。**白名单出处形态三项禁类推扩用**:证明件原文出处(R17-5)/
用户裁定的实证扫描常数(R27-7)/登记表自证的数学平凡界(R39-低2);
新增条目须附出处;消费位全灭 ⇒ 条目退役(存档态符号保留溯源、注释标
「已退役,禁入任何消费位」,判据模块 import=评审红)。

落码纪律:判据模块一律 import 符号名消费(判据侧写字面量=ruff 红)。
"""
from __future__ import annotations

#: ①段界 0.1——**退役存档态**(R26-H1/R10-1:0.1 死阈值随三段管辖退役,
#: §2.0-2「0.1 常数退役」)。符号保留溯源,禁入任何消费位;阈值类消费
#: 一律走扫描带形态(辖未来新消费位,带端点须按 PL 键主表重扫)。
LAMBDA_SEGMENT_BOUND: float = 0.1

#: ②λ₃ 视界 = 3 轮(P51 §R/§5-11 v3 口径注:λ_death 是 3 轮窗累积危险率)。
LAMBDA3_WINDOW: int = 3

#: ③κ 窗因子 = 3(P51 推论 3 / L-R3-1 推论 3)。
KAPPA_WINDOW: int = 3

#: ④阈值扫描带端点 (0.40, 0.65)——**退役存档态**(R30-4:消费位逐个清点后
#: =空集,条目转退役存档;扫描带纪律本体不废,辖未来新阈值类消费位,
#: 届时带端点须按 PL 键主表重扫,禁沿用本存档带常数)。
ADV_SCAN_BAND: tuple[float, float] = (0.40, 0.65)

#: ⑤金→轮折算率下界 5.8——**退役存档态**(R44-1:折算率归宿改
#: provisional 槽位 CONV_GOLD_PER_ROUND【拟·语料拟合】,依附 λ 表版本带
#: 版本锚;落地前槽位 None=窗口帧 C_stay/χ 项 fail-closed)。
CONV_GOLD_PER_ROUND_LB: float = 5.8

#: 退役存档态条目集(消费位全灭 ⇒ 转存档;import 检测的测试断言消费)。
RETIRED: frozenset[str] = frozenset({
    'LAMBDA_SEGMENT_BOUND', 'ADV_SCAN_BAND', 'CONV_GOLD_PER_ROUND_LB',
})

#: 现役(可消费)条目集。
ACTIVE: frozenset[str] = frozenset({'LAMBDA3_WINDOW', 'KAPPA_WINDOW'})

__all__ = [
    'ACTIVE', 'ADV_SCAN_BAND', 'CONV_GOLD_PER_ROUND_LB', 'KAPPA_WINDOW',
    'LAMBDA3_WINDOW', 'LAMBDA_SEGMENT_BOUND', 'RETIRED',
]
