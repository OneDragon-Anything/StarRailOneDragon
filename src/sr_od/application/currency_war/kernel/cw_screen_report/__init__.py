"""货币战争 画面观察上报包(每画面一文件:obs 类 + ``report_screen_*_obs``
函数同居;迭代 2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

- 文件名 = 画面 snake;obs 类命名 = ``CwScreenXxxObs``(商店框 op =
  ``CwOpXxxObs``),字段 = 现役 ``XxxObservation`` 逐位平移;
- 函数命名规约 = ``report_screen_<snake>_obs``(obs 类去前缀 ``CwScreen``
  去后缀 ``Obs`` 转 snake),与动作上报函数族 ``kernel/cw_action_report``
  同约定:一个「上报」概念一个形状,两族互不混用,都禁按类型聚合的
  分派转移函数;完备锁测试遍历包内全部 obs 类断言函数在场/不在场分侧;
- 本包不暴露模块(项目惯例):消费方按画面文件名直接 import。
"""
