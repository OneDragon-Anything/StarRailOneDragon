# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争内置策略包(StrategyManager BUILTIN 扫描目录)。

每个 ``.py`` 定义一个 ``CwStrategy`` 子类(每文件最多一个真实策略)。``default_strategy.py`` =
``DefaultCwStrategy``(``STRATEGY_ID="default"``,内置全具现,薄委托既有模块函数 = 今天打法)。

第三方/参赛策略放项目根 ``plugins/currency_war_strategies/<子目录>/``(不在本包;THIRD_PARTY 源)。
"""
