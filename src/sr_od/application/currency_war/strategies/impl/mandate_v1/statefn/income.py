"""Ī(净收入率):收入日程逐节点现算(R09 收入三表;TUNING#3 消参路径)。

实现已下沉 kernel/cw_economy(kernel 判据 schedule_upgrade 的
U_L 阈值检验消费 net_income,下沉保持桶依赖矩阵)——本模块经 import
重定向保留调用面,消费方零改。旧 i_bar=7 常量已处死(NMF §5.4 处死
名单):net_income = base(r) + streak(决策前相) + 败轮底金;值全部
来自 cw_economy 注册表(【注】机制真值),本链零数值字面量。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_economy import (
    net_income,
    round_base_income,
)

__all__ = ['net_income', 'round_base_income']
