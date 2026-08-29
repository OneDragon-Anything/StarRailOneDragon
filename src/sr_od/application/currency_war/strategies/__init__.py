"""货币战争策略包(StrategyManager BUILTIN 扫描目录)。

每个 ``.py`` 定义一个 ``CwStrategy`` 子类(每文件最多一个真实策略)。
``decision_v2_strategy.py`` = 生产注册桥(壳子类接入 StrategyManager 注册面,
实现单一源在 ``decision_v2/strategy.py``)。default 栈(``DefaultCwStrategy``)
本体已退役删除,唯一策略载体 = ``decision_v2``(ADR-0309)。

第三方/参赛策略放项目根 ``plugins/currency_war_strategies/<子目录>/``(不在本包;THIRD_PARTY 源)。
"""
