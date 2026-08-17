# ADR-0196: 实验多路复用层 v0 落地(redesign 29 号处置:注册表+兼容矩阵+窗口调度)

## Status

Accepted(2026-08-17,策略优化会话;局前调度执行侧(run_context 写入/telemetry 标记)挂
实机批次)

## Context

29 号诊断:消化终态 400-600 局实机验证债(月-季度串行);每轮默认「一局一判据」——
真正互斥的只有行为层(≤5 域),shadow/passive/perception 三层天然全兼容。

## Decision Drivers

- J1(债务审计:全兼容 ≥70%+行为域 ≤5)+ J2(同 100 局复用 vs 串行 FIFO ≥3×)
  为生死判据
- 45 号吞吐常数(5.07 局/时)进调度输入

## Considered Options

1. **注册-兼容-调度纯函数先行(选)**:ExperimentSpec(登记冻结)+ compatible(行为域
   正交+排斥)+ schedule_package(贪心 info_value×deadline 紧迫)+ pollution_check
   (共因变量显式记账);最坏退化=现状;
2. 直接建 run_context 写入链——执行侧需实机;
3. 不做——月级债务继续串行。

## Decision

选 1:`cw_experiment_mux.py` v0——

- **J1 过**:17 项债务登记(29 号 §1 原表忠实映射,含漏补的 19 号 L1 感知硬门)
  → 全兼容类 12/17=70.6%、行为域 5(horizon/bundle/equip/injector/weight)——
  复用主张前提成立;
- **J2 过(仿真)**:同 100 局预算,分层重叠完成判据 **13 vs 串行 FIFO 1(≥3× 达标)**;
- 污染哨兵:drift_inject×lambda_j0 排斥对生效;共因变量对显式 block 记账;
- 涌现协同位就绪:必死局×注入(05+23)、L1 硬门 info_value=4.0 绝对优先。

## Consequences

- 400-600 局债务理论压至 ~100-150 局(3-5×),月级→周级;29 调度器成为 47 发布
  注册表与 34 预算表的消费端;
- 局前调度的 run_context/telemetry 标记接线挂实机批次;
- 29 号处置完成(v0),提案文件删档;测试 +5。
