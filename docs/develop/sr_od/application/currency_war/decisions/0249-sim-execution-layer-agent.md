# ADR-0249 sim 执行层代理:deploy 围栏单一源(r390)

## Status

accepted(2026-08-23;r390;用户定调「这些问题明明都可以模拟发现」驱动)

## Context

局53-62 实机暴露三个 deploy 侧 bug(r373 桥期 target 真空/r387 cap 富余仍拦散牌/r388 开局乱装备),全部是 **DeployBench op 的执行层行为**。sim 的 deployed 是自动代理(bench 引擎件直进,`_deployable_depth` 数 bench 阵营对)——围栏逻辑零覆盖,这类 bug 天然测不出。修复缺口的三个环节各有玄机:

1. **提取纯函数**(select_deployments):围栏判定从 op 搬出(无 ctx/画面/SIFT),sim 与 op 同源消费——不是重写是搬家,实机改=sim 改;
2. **deployed 代理改走真围栏**:带 session 真实 target 集(锁线 tf/tc+桥期 fw_carry 三通道);
3. **深度口径读 deployed**(变异差异死点):首版只做 1+2 时变异探针分布不动——排查发现 `_deployable_depth` 还在数 bench(旧 r343 口径),围栏的输出没人消费。修后变异 A(r387 修前形态)检出 loss≤2 0.017→0.117 涌现。

## Considered Options

1. sim 重写一份围栏逻辑:双源必漂移(本次修的就是这种病),否决;
2. 只提纯函数不动深度口径:变异差异死在中间(实证),不够;
3. **提取+接线+口径三件套**(选):全链路打通变异可检出。

## Decision

选 3。装备层(equip_allocation)同法待做(纯逻辑已可 import,sim 接线+变异探针留下一批)。

## Consequences

- r373/r387 类 deploy bug 从此 sim 可发现(变异探针=永久回归验证);
- sim 的 depth_trail/Δ 池采样/账本 depth 语义随 deployed 真值化(不再高估:bench 有但上不了场的不计);
- r343 旧源码锁(数 bench 字面量)随语义演进更新;
- 装备层执行代理是下一个同类缺口。
