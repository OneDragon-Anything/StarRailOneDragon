# 0283 sim bench 超容买守卫(批⑰ F6)

- 状态: accepted
- 日期: 2026-08-24
- 来源: 批⑰ sim 压测 F6(seed 130/152/217,3/300 局;ADR-0219 状态侧同族)

## 背景

sim 执行层的 BuyCard 无容量守卫:决策层单轮可输出 4-8 连买,r7-r9 满仓
连买把 bench 顶到 11-17(> `BENCH_CAPACITY`=9)。而生产语义 bench 满 =
**硬模态**拒买(ADR-0136「备战席已满」球点不动,cw_identity_obs)——
sim 满仓局的买门/腾位门读的是生产不可能出现的状态,污染 r416 腾位门类
判读(ADR-0219 同族,这次在状态合法性而非代理语义)。

## 决策

BuyCard 执行前置容量检查:合并域(bench+deployed,`_merge_bench` 全场域)
中 **bench 槽为约束**——deployed 不占备战槽,判据 =
`len(st.bench) >= BENCH_CAPACITY`(与生产 `bench_is_full` 同源常量)。
超容买**跳过**(金/牌池均不消费)+ 计数披露:轮账本
`sim.bench_full_skipped_buys`、批量报告 `bench_full_skipped_buys`
(0=常态;>0 = 决策层在满仓态想买,判读买门/腾位门时须对照)。

## Considered Options

- **A. 决策层修(满仓不发 BuyCard)**:拒绝——决策层修不完(stub/探针/未来
  策略都能再发),守卫放执行层才与生产硬模态同层(sim 是执行语义模拟器,
  不是策略正确性假设器);
- **B. 合并域全量和(len(bench)+len(deployed))对单一容量判**:拒绝——
  deployed 不占备战槽,全量和会把「bench 9 + deployed 6」这类生产合法态
  误判超容,反向制造 sim↔生产分叉;合并域的意义在 merge 计数(ADR-0276),
  容量约束绑定 bench 槽;
- **C. 超容买仍执行但事后截断**:拒绝——金/池已消费,账本与状态脱节,
  比不守卫更难判读;
- **D. 前置守卫 + 计数披露(选定)**——状态合法性由执行层保证,披露让
  「守卫介入」本身成为判读可见事件(后续可升检查项
  `bench_capacity_invariant` 的锁,基线 3/300 → 0)。

## 影响

- `cw_sim.py`:BuyCard 分支前置守卫 + `_bench_full_skips` 计数
  (轮账本 `sim.bench_full_skipped_buys`) + 批量报告
  `bench_full_skipped_buys` 聚合;
- 测试:`test_cw_adr0282_0283.py::test_sim_bench_capacity_guard`
  (无脑买桩逼满仓:容量不变式 + skips>0)。
