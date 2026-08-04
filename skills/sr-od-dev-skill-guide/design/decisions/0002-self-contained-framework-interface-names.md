# 0002. 自包含 + 框架地基级接口名可写进 SKILL.md

- **Status**: accepted
- **Date**: 2026-07(「框架地基级接口名」补充部分;「自包含」基线更早)

## Context
SKILL.md 注入智能体执行上下文,引用外部文件有两类问题:
1. **独立发布 skill** 引 skill 目录外文件 → 发布不含、目标环境可能没有 → 智能体执行时找不到。
2. 但**项目内 dev skill**(放项目 `skills/`,跟项目走)要读写**项目 runtime 资产**(screen_info / application 源码 / docs/game)—— 这些是 skill 的操作对象,本项目必有且稳定;一刀切禁止引用则指令无法落地。
3. PR #2575 暴露:CodeRabbit 按硬规范 4「不写函数名」字面,把 `sr-od-dev-debug-automation` SKILL.md 里 `@operation_node` / `@node_from` / `analyze_screen` / `is_debug` / `save_screenshot` 5 个接口名当 Major 违规报;但这 5 个是**指令本身**(debug / 排查类 skill 要搜 / 要调 / 要提醒的名)+ **框架地基级**(整个节点系统靠它,改名 = 重写框架)→ 应允许。

## Decision Drivers
- **自包含**:独立发布 skill 不能依赖外部文件。
- **可执行**:项目内 dev skill 的指令要能落到具体操作对象。
- **不静默指错**:接口名要写全名(改名时全局搜能发现),而非模糊化(改名后静默指错更危险)。

## Considered Options
1. **一刀切「所有路径都不写」**:独立发布安全,但项目内 dev skill 指令无法落地。
2. **分场景**(选中):独立发布禁外引;项目内 dev skill 可引**稳定操作对象 / 自带工具**,不可引**易变佐证位置**(某 devtools L640、「详见某 README」)。
3. **框架接口名判据两问**:① 删掉这名智能体还会不会照做?(不会做 = 名是指令本身 → 倾向留)② 这名稳不稳?(地基级、几乎不改名 → 留;易变 → 挪 design/ ADR)。过两问 → 可写,且**写全名**别模糊化。

## Decision
选 2 + 3:分场景(独立发布 vs 项目内);项目内 dev skill 可引稳定 runtime 资产路径 + skill 目录内自带工具;框架地基级接口名(过两问判据)可写进 SKILL.md,写全名。判据写进 SKILL.md 硬规范 3。

## Consequences
- **正向**:dev skill 指令可落地 + 自包含边界清晰;接口名全名 → 改名时全局搜可发现过期。
- **负向**:判据有主观性(「地基级」「稳定」要人判),需 PR review 对齐。
- **follow-up**:早先违反的 `sr-od-miyoushe` SKILL.md(「端点 / 参数 / 过期算法见 design.md」)待修 —— 使用信息应内联 SKILL.md 或进 `references/`,不进 design。

## Links
- PR #2575(CodeRabbit incident);review #2300(screen-onboarding「转换工具见 design.md」致 AI 漏读、手写重复转换脚本)。
- 本 skill SKILL.md 硬规范 3。
