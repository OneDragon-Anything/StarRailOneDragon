# 0001. design 与 ADR 分离(取代单 design.md)

- **Status**: accepted
- **Date**: 2026-08-04
- **Supersedes**: 本 skill 旧版「单 design.md 混合设计 + 决策」做法

## Context
原硬规范 #1 要求每个 skill 有一个 `design.md`,「记设计与决策」—— 即把 **design(what:系统长什么样)** 和 **decision(why:为什么这么选)** 写进同一个文件。实践暴露的问题:
- design 和 decision 读者 / 生命周期不同(前者随系统演进常改,后者 immutable 只 supersede),混写互相干扰 —— design 文档被「为什么」叙述撑乱,decision 又被「是什么」描述稀释。
- 单文件「decisions 日志」(如 currency_war `decisions.md` 的 D-NN 紧凑条目)是 ADR-lite,但丢了 ADR 最值钱的 **Context**(当初面对的问题)和 **Consequences**(代价 + follow-up);且单文件难承载 rich 条目、supersede 链别扭。
- 本项目早先曾决定「不一决策一文件(决策多,奢侈)」用单文件日志 —— 但「奢侈」只在**给每个决策都建文件**时才成立。

## Decision Drivers
- **可维护**:后续维护者能快速找到「为什么这么定」+ 推翻后果。
- **不过度工程**:小 skill 不该被强制建一堆文件。
- **业界对齐**:用成熟方法论(arc42 + ADR)而非自造格式。

## Considered Options
1. **保留单 design.md,design+decision 混写**(旧做法):简单,但混写问题不解决。
2. **单文件 decisions 日志 + design 分文件**:日志条目缺 Context/Consequences,rich 条目撑爆文件。
3. **design/ 文件夹 + decisions/ ADR(一决策一文件)+ 门槛**(选中)。
4. **每条决策一文件,无门槛**:最纯,但调参 / 笔误也建文件 → 文件爆炸。

## Decision
选 3:`design/` 文件夹(design doc + `decisions/` ADR 物理分开),ADR 按 arc42 §9 全字段(Status/Context/Options/Decision/Consequences),用**门槛**(架构级 / 难逆 / 有实质备选 才写 ADR)治「奢侈」。细则见 `../../references/design-docs.md`。

## Consequences
- **正向**:design / decision 分离清晰;ADR 的 Context + Consequences 给未来维护者真实指导;门槛控文件数;对齐业界方法论(arc42 / MADR),团队 / 工具认知成本低。
- **负向**:比单文件多几个文件;写 ADR 有格式成本(门槛 + 模板)。
- **follow-up**:① 子项目 currency_war 的 `decisions.md` 单日志迁到 `decisions/` ADR-per-file + INDEX(作 reference implementation);② 其他已有 skill 的 design.md 逐个迁。

## Links
- 细则:`../../references/design-docs.md`(目录结构 / ADR 模板 / 写作方法论)。
- 本 skill SKILL.md 硬规范 1。
