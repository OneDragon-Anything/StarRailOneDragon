# sr-od-dev-skill-guide · 设计概览(what)

## 为什么做
项目 skill 部署到不确定的智能体环境(不像 superpowers 自带 plugin、运行时文件环境确定),需要项目特定的自包含 / 落点 / 风格规范。`superpowers:writing-skills` 通用且偏严格 TDD,不含本项目约束(自包含 / 落点 / design-ADR 等);其核心写法**已整合**进本 skill(见 [ADR-0005](decisions/0005-drop-superpowers-dependency.md)),不外引依赖。不固化项目规范则每次写 skill 易踩红线。

**为什么是 skill 而非 docs**:skill 触发时自动注入执行上下文(主动);docs 要记得翻(被动)。写 skill 的规范本身也该在「要写 skill 时」被主动注入,故做成 skill。

## 4 条硬规范(是什么;各条 why 见对应 ADR)
1. **必须有 design/ 文件夹,design 与 ADR 分开**(迁移自旧「单 design.md」;why 见 [ADR-0001](decisions/0001-design-adr-separation.md))。
2. **内容给智能体看(指令式)**:正文是祈使句 + 判据;`description` 只写触发条件(SDO 结论:description 写流程 → 智能体照 description 走、不读正文;整合自 superpowers,见 [`../../references/writing-craft.md`](../../references/writing-craft.md) §1.3)—— 非本项目新决策,故不单列 ADR。
3. **自包含(分场景)+ 框架地基级接口名可写进 SKILL.md**(why + PR #2575 incident 见 [ADR-0002](decisions/0002-self-contained-framework-interface-names.md))。
4. **写方法论,不写具体例子**(why 见 [ADR-0003](decisions/0003-methodology-not-examples.md))。

## 落点
- 根 `skills/`(跨工具源)而非 `.claude/skills/`(工具特定):项目 skill 面向多个 skills 感知工具。
- `sr-od-dev-` 前缀:项目开发流程类,与工具自带 skill 区分。
- junction 而非 symlink:Windows symlink 需特权,junction 免管理员;junction 不提交(`.claude/` gitignore),每人本地建。
- **不外引写法依赖**:通用写法已整合进 `references/writing-craft.md`,不 defer 给 superpowers:writing-skills(见 [ADR-0005](decisions/0005-drop-superpowers-dependency.md))。

## 写法来源(已整合 superpowers 核心,无依赖)
- **通用写法**(frontmatter / SDO / token / 结构 / form-to-failure / 例子 / 何时建):已从 superpowers:writing-skills 整合进 [`../../references/writing-craft.md`](../../references/writing-craft.md),本 skill **不再 defer / 依赖**它(见 [ADR-0005](decisions/0005-drop-superpowers-dependency.md))。
- **刻意偏离**:superpowers 的 Iron Law(每个 skill 必先 RED baseline)→ 本 skill 弱化为「两类 skill」(方法论覆盖型 RED 可省)。理由 = 外部效度 / 团队工具模型异构(见 ADR-0004 / writing-craft §3.1)。
- **本 skill 叠加**(superpowers 没有):design/ + ADR(规范 1)、自包含硬门 + 引用卫生(规范 3)、写法工程指南(writing-craft)。
- **两类 skill**:**纠正型**(改变智能体默认错误)RED 必做;**方法论覆盖型**(整合业界方法论)RED 可省、GREEN 必做。`sr-od-dev-deciding-a-fix` 是方法论型范例(锚定业界 RCA / Impact Analysis / Trade-off Matrix)。

## 自身一致性
本 skill 遵守自己的规范:有 `design/`(design 与 ADR 分开);SKILL.md 指令式;**不引 skill 目录外的 docs 文件**,写法细则自含在 `references/`(不外引 superpowers:writing-skills);正文是规范 / 判据 / 流程,无具体项目叙事例子。

## 当前状态
团队已统一采用 superpowers,本 skill 已 unignore 并提交(目录名 `sr-od-dev-skill-guide`)。
