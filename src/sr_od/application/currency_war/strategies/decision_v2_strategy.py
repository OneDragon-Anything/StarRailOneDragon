"""货币战争 · 决策框架 v2 注册桥(DecisionV2Live;ADR-0290 渐进迁移)。

本包(``strategies/``)是 **生产注册面**——``SrContext.currency_war_strategy_plugin_dirs``
只扫描本目录(BUILTIN 源),不在此处的策略对 ``StrategyManager`` 不可见;
策略 id 构造期即校验,未注册 id 显式报错(无静默回退)。

``DecisionV2Strategy`` 的实现体在框架实现包
``sr_od.application.currency_war.decision.decision_v2.strategy``(四层:候选生成→
硬过滤→板面评分→预算仲裁),不在扫描面内——本文件是**桥**:定义一个
零逻辑复制的壳子类把它接入注册面(ADR-0290 渐进迁移的开关注入位:
观察局/灰度走本桥,框架演进仍在 decision_v2 单一源)。

为什么必须是子类定义而非纯 re-export:manager 的
``_find_strategy_in_module`` 有 ``__module__`` 守卫——只注册「定义于
本模块」的类,``from ... import DecisionV2Strategy`` 直接转发的类其
``__module__`` 指向实现包,不会被注册。壳子类在此文件定义 → ``__module__``
匹配 → 注册;所有行为(含 ``__init__`` 的 registry 注入语义)全部继承父类。
"""
from __future__ import annotations

from sr_od.application.currency_war.decision.decision_v2.series_adapter import (
    DecisionV2SeriesAdapter,
)


class DecisionV2Live(DecisionV2SeriesAdapter):
    """decision_v2 生产注册壳:零逻辑复制,全部行为继承 ``DecisionV2Strategy``。

    序列契约 v1(dd-020;R192 症2 包装形态):基类链 =
    ``DecisionV2Live → DecisionV2SeriesAdapter → DecisionV2Strategy``——
    生产 ``match.strategy`` 经本桥拿到**包装实例**(decide_prep_screen 返回
    长度 1 ``list[PrepAction]``),冻结基线 ``DecisionV2Strategy`` 本体零改动
    (IMPL_DESIGN §4.1 冻结;A/B 基线臂保持单动作原状)。
    ``strategy_id='decision_v2'`` 语义不变。

    类属性重申仅为注册面自描述(GUI 显示/StrategyInfo 元数据);
    实现单一源在 ``decision_v2/strategy.py``,改行为去那边,别在此加逻辑。
    """

    STRATEGY_ID: str = 'decision_v2'
    STRATEGY_NAME: str = '决策框架 v2(候选×评分×仲裁)'
    AUTHOR: str = 'OneDragon'
    VERSION: str = '0.1'
    DESCRIPTION: str = ('ADR-0290 四层决策骨架:候选生成→硬过滤→'
                        '板面评分→预算仲裁;本文件是注册面桥,'
                        '实现单一源在 decision_v2 包')
