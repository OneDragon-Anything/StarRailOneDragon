"""货币战争 · 新核 mandate_v1 注册壳(生产注册面;策略统一迁移批后形态)。

``strategies/`` 是生产注册面(StrategyManager 只扫描本目录顶层 BUILTIN 源,
忽略 ``impl/`` 子包);实现本体在 ``strategies/impl/mandate_v1/bridge.py``
(不在扫描面内)。本文件是桥:零逻辑复制的壳子类——``__module__`` 守卫
(只注册「定义于本模块」的类)要求壳子类在此定义。manager 另在 discover
收尾强制注册本壳(不依赖扫描发现)。壳类本体 = 零覆写的注册自描述载体:
决策通路 = obs(黑板)+ session 容器直读,实现单一源在 impl 桶 bridge。
"""
from __future__ import annotations

from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
    MandateV1Strategy,
)


class MandateV1Live(MandateV1Strategy):
    """mandate_v1 生产注册壳:零决策逻辑复制,全部行为继承 ``MandateV1Strategy``。

    无覆写(类属性重申仅为注册面自描述:GUI 显示/StrategyInfo 元数据);
    实现单一源在 ``strategies/impl/mandate_v1/``,改行为去那边,别在此加逻辑。
    """

    STRATEGY_ID: str = 'mandate_v1'
    STRATEGY_NAME: str = '新数学框架核(mandate_v1;三遍化决策序)'
    AUTHOR: str = 'OneDragon'
    VERSION: str = '0.1'
    DESCRIPTION: str = ('cw4 新核:证明 pass→升档器求值位→骨架 pass'
                        '(M1-M7)→EV pass(criteria 七面);序列契约 v2'
                        ' 帧稳定截断发射')
