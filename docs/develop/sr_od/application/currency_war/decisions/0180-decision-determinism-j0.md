# ADR-0180: 决策确定性验收落地(redesign 46 号处置:J0 体检 + CI 护栏)

> **版本界碑(2026-09-04 ADR 存量 review;对象属 decision_v2 栈或旧策略代,现行权威 = strategy-docs/flow/proofs)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb 删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

## Status

Accepted(2026-08-17,策略优化会话;J1 静态读取面扫描为增量)

## Context

46 号诊断:决策函数自身的确定性是 14 CRN/24 CEM fork/42 T1/05 adherence 共同押注的静默地基
假设,违反不报错只污染统计功效。J0 判据(预注册):50 前缀重放自洽 100% → 地基已净,
主张降级为文档+CI 护栏(46 号自我证伪条款)。

## Decision Drivers

- 42 号 T2(值函数一步差)与 14 号反事实的「同信息集→同决策」前提需客观验收
- 生产侧已存在种子钩子(strategy_seed → session.rng,battle_loop:112)

## Considered Options

1. **J0 体检 harness + CI 护栏(选)**:真实语料重放体检(一次性)+ 合成局面护栏(常驻);
2. 直接上 J1 静态读取面拦截(调用栈归因矩阵)——工程量大,J0 全绿后按提案条款降级为增量;
3. 不验收——地基假设继续悬空。

## Decision

选 1:`cw_decision_replay.py`——

- ``state_from_row``:decisions.jsonl 行 → GameState 复原(嵌套 ShopCard/BenchChar,
  未知未来字段剔除——schema 演进安全);
- ``run_replay``:50 前缀 × 同种子双跑自洽 + 录制对拍(分歧行归因清单);
- **J0 首测结果(6824 行语料前 50)**:自洽 **100%**(硬判据过);对拍 6% 差异归因 =
  录制时 rng 未种子(生产默认真随机,分布等价)+ 录制管线含执行层截断(shop.py 两阶段)
  ——非确定性违纪,属地基已净 + 录制口径差的实证清单;
- CI 护栏测试 ×3:三局面(健康/血危/晚期)同种子双跑一致 + state 复原 roundtrip + 跨调用栈一致。

## Consequences

- 46 号 J0 兑现,确定性主张按预注册条款降级为常驻护栏;J1(读取面矩阵,预注册未声明依赖
  ≥3)为下批增量;
- 生产种子路径确认在位(strategy_seed 配置);42 号 T2 地基验收门可引用本护栏;
- 46 号处置完成(v0),提案文件删档;测试 +3。
