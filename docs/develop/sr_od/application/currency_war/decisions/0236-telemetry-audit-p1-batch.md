# ADR-0236 遥测审计 P1 批(gold 轨迹回合去重 + decisions 并列取末帧)

## Status

accepted(2026-08-22;r363b;审计 80b8a6c5 P1 组前两项)

## Context

审计 P1:①gold_trajectory 每轮 3-11 采样(shop 循环每次迭代调 record_decision,gold_point 默认 True;r69 只修了 director 步进路径)→ runs 的金轨迹/economy 判读被步进中间值拉歪;②_load_decisions_rounds 并列时严格大于让**最早**行胜出 → 轮末 state 被首帧代表(局47 r1 best=空板首帧实锤)。

## Decision

1. gold 采样去重下沉到 recorder 内部:`_gold_last_key=(run_id, plane, round)`,每回合只收首个 gold_point=True 采样——调用方语义不变,不靠纪律传参。
2. decisions 去重并列时取 ts 最晚(末帧=轮末真值);docstring 更新。

## Considered Options

- P1 余项(refresh 快照假金/level 非单调/board≠板深/exogenous 只一族):视图/写侧联动改动更大,下一批。P2 组(结算 OCR 首领误中风险/streak 前两胜恒 0 未证)挂观察。

## Consequences

- economy 视图与 runs.gold_trajectory 从此每轮一点;rounds/tiers/planexec 用轮末 state。
- 遥测测试 20 过。
