# ADR-0253 deploy_fills_cap 检查项:r387 类 bug 的 sim 常态防线(r391)

## Status

accepted(2026-08-23;r391;commit 1bb975de;ADR-0249 执行层代理的配套回灌)

## Context

r390 执行层代理落地后,变异探针已证分布差异可涌现(关 cap_roomy 守卫 → loss≤2 从 0.017 → 0.117,ADR-0249)——但变异探针是「主动验证」,只在人为去守卫时跑;常态 sim 批量不会自动报警。本检查把 r387 修前形态(围栏系统性拦截空槽)变成批量检查项的**常态拦截**(skill 纪律:实机暴露的策略病变现成 sim 检查项)。

数据源缺口配套修:账本补 `state.deployed`(dict 形状对齐 rounds 视图消费,带 position_pref)+ `state.cap`。

## Considered Options

1. **只靠变异探针(不进 _BATCH_CHECKS)**:每次改围栏须记得手动跑变异——防线依赖人的记性,回归不可自动发现。否
2. **单轮 deployed<cap 即报**:sim 代理在决策前生成、同轮买入后不刷新——单轮短缺常是「买了还没重新部署」的过渡态(game14 实证:r2 4/6 → r3 6/6),会误报。否
3. **连续 2 轮 `deployed ≤ cap-2` 且 bench 有货才报**(选):连续 2 轮才是围栏系统性拦截的指纹;三个边界排除——贴 cap(差 1,cap 竞争是 r387 修后仍合法的形态)/单轮短缺(代理时序过渡态)/bench 无货(没牌可上不报)。窗口限定 plane1 r2-r4(首两轮系统卡未定排除)。

## Decision

选 3。`check_deploy_fills_cap` 纯函数进 `_BATCH_CHECKS`,真实 sim 批次自动扫。

## Consequences

- 非空转验证:基线 0 违规 / 变异(r387 修前)4 违规——零误报且有信号;
- 锁测试 4 条(合成账本双向);全量 1043 passed;
- 账本新增 deployed/cap 字段为 rounds 视图与后续检查项的公共数据源。
