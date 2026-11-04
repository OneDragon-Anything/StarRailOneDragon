"""货币战争 撤销/熔断操作证据留存索引层说明(纯观测;复用 defect_ledger
record 模式,禁第二套机制)。

在库分键(defect_ledger 内,写入点在 operations 执行侧):
- ``sell_breaker_preserved``:卖出熔断撤销面(谁/为何/
  保留了什么;写入点 = cw_op_deploy off-target 卖出通道的围栏保留分支)。

(干旱计数器证据分键 ``drought_buy_no_reset`` 及其入口函数已随
comp-structure-unification 3.3 配方决策层退役删除——判据对象
pair_drought/members_in_shop 随体系对域全族消亡,考古走 git 历史。)

既有覆盖(复用不另建):``m2_retry_exhausted`` / ``bench_full_buy_
abandon`` 等 cw4_counters 族;策略桶受包依赖矩阵限制(strategies→
telemetry 非合法边),店侧熔断 veto 经 cw4_counters 分键承载,证据
写入点收敛在 operations 执行侧。
"""
