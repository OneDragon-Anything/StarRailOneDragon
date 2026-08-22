# ADR-0231 回放对拍器升级(LineStrategy 忠实还原 + 分歧分桶)

## Status

accepted(2026-08-22;r359;子代理设计审查 b85c38eb 前置)

## Context

r98 版 cw_replay.py 只重放 DefaultCwStrategy——生产策略早已切 LineStrategy(v2),工具与生产脱节。且缺:v2 session 态恢复(应急/追赶 latch 决定 decide_prep 分支)、deployed 重建(r358 三维判读所需)、分歧分桶、低置信标记、边界声明。

## Decision Drivers

- 子代理审查结论:v2_state 缺失是重放系统性偏差的最大坑(同 r101 当年补 sess_* 的理由);「分歧≠好坏」边界必须印在输出里自持
- 07_plugin.md replay 语义:回归测试不是胜率裁判——报告支持按分歧类型分桶供人工判「意图内/外」

## Considered Options

1. 新写独立对拍器:与既有 harness 双源——否。
2. **升级既有 cw_replay.py**(选):--strategy line(default 保留);_restore_session 恢复 v2 字段(sess_v2_state 忠实还原 latch);_rebuild_state 补 deployed(含 star/equips)/xp tuple/active_env;_divergence_kind 三桶+兜底;首发分歧标记;低置信 ⚠;页首边界声明。
3. 快照恢复式 session(每回合完整重置):受旧记录无 v2_state 制约——作为增量演化式(line 现行)之外的第二版,先补遥测字段铺路。

## Decision

选 2 + 配套遥测补字段:DecisionTrace 末尾追加 `sess_v2_state: list | None`(schema 稳定约定,旧记录缺省 None);shop.py 决策记录点从 session 全量写入。新采集的局即可做忠实快照重放;旧局走默认 latch 演化(判读聚焦购买/升级动作族)。

## Consequences

- 实测局46:diff 模式即输出「r2 刷vs不刷(首发)/r6 其他」两处分歧+分布汇总——工具即时可用于回归。
- 稀有态扫描(cw_dev/rare_state_scan.py)+ 回放对拍 = 深度挖掘方向①②的首批实操(发现记录 r358f_scan_replay_findings.md)。
