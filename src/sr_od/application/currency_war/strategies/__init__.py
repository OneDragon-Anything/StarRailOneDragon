"""货币战争策略包(StrategyManager BUILTIN 扫描目录)。

目录形态(策略统一迁移批):
- 顶层 ``*_strategy.py`` = **生产注册壳**(每文件最多一个 ``CwStrategy``
  子类,``__module__`` 守卫只注册「定义于本模块」的类);
- ``impl/`` = 实现本体子包(接口基类/主流程驱动核/mandate_v1 机器),
  **manager 扫描忽略**,且 ``discover`` 收尾强制注册 mandate_v1(不依赖
  扫描发现)。注册壳唯一存量 = ``mandate_v1_strategy.py``(decision_v2 注册壳已随统一迁移批 ② 删除)。

第三方/参赛策略放项目根 ``plugins/currency_war_strategies/<子目录>/``(不在本包;THIRD_PARTY 源)。
"""
