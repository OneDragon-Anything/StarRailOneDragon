# ADR-0233 sim 校准层双修:事件金注入 + deployed 代理

## Status

accepted(2026-08-22;r361b;经济对账 v7 + review 17c916e0 驱动)

## Context

①经济对账(r360 v7)证实奖励球/节点事件金是真实收入(残差随轮次增长,r1→r2 中位+1 → r8→r9 中位+9)但 sim 收入层没有——sim 金压力系统性偏穷,攒息/破息行为的输入分布失真。②review 发现 r358 检查点核心维读 state.deployed 而 sim 不建模该字段(恒空)→ 核心恒 0/2 → 档位折扣恒触发 → r5+ 恒走围栏——sim 策略行为与实机分叉(ADR-0219 代理语义纪律第三次命中:新字段进 GameState 时漏查 sim 侧消费点)。

## Decision

1. 收入层:`_event_gold(round, rng)` 按轮次经验中位 ±2 抖动注入(v7 分布)。
2. deployed 代理:逐轮把 bench 引擎件/成对阵营件代理为 deployed(同 depth_trail 的 _deployable 口径),供 update_target/检查点读。
3. 配套修 review 项:`_deployed_fac` 补 flows 口径(与 _tier_completes 全羁绊判档一致);board_names 空集不折扣守卫(SIFT 全 miss ≠ 核心不在场)。

## Considered Options

- 不修 sim(声明边界):sim 与实机行为分叉会让后续所有 A/B 结论失真——修。
- 完整 deployed 建模(3合1/升星/站位):超本轮范围,代理口径与 depth 一致先行。

## Consequences

- sim A/B 基线作废(收入层+策略输入双变),下次 A/B 前先重标基线;事件金 A/B 数字差异在噪声带内,不作为效果结论。
- 「新字段进 GameState 查三消费面(策略/遥测/sim 代理)」入 skill 防坑清单。
