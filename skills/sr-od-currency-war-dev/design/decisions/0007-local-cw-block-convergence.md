# ADR-0007 AGENTS.local CW 块收敛(细节迁 skill,本节只留通用授权)

## Status

accepted(2026-08-22;用户指令「看哪些应该总结成方法论放入 skill」)

## Context

AGENTS.local.md 的 CW 块(约 175 行)是 skill 出现前的积累:实跑闭环细节、模拟先行、文档规范、CW 踩坑(ESC/升等级/事件长尾/识别)混着通用授权与跨玩法约束。skill 建立后这些内容与 skill 双源。

## Considered Options

1. 全留不动:双源漂移(skill 更新不会同步 local)。
2. 全删只留一句指针:通用授权(不偷懒停/大胆推翻/工程化质量/commit 边界)与跨玩法通用约束(监控栈/自校准/工作纪律)仍需 always-on——skill 触发是按需的,授权不该依赖触发。
3. **分类收敛**(选):CW 专属操作细节(判读 CLI 细则/早停判据/交接序/CW 踩坑/CW 资料指针)删——skill 已覆盖或本轮迁入;通用授权与跨玩法约束(标「通用」/「试点泛化」)留;CW 节头声明操作单一源=skill。

## Decision

选 3。本轮迁移增量:恢复步骤入 checklist 步骤 1;--recent 对照/日志时间窗/# 未验证复审入 §判读;CW 踩坑三条(升等级破墙/事件长尾/识别边界)入 references/runtime-ops;铁律+先搜再写入 data-collection 总原则。local 侧泛化:模拟先行/文档规范/策略方向/资料目录改为 `<玩法>` 通用表述(CW 实例指 skill);bug#2 泛化为「玩法 op」;删日志格式速查节(skill §判读有)。

## Consequences

- 跨玩法通用节与 skill 的 CW 特化版并存是**刻意的双层**(ADR-0003):通用版管任何玩法,CW 版管 CW 细节——语义冲突时同步修正两处。
- 后续新玩法照此模式:通用判据进 local,玩法细节进各自 skill。
