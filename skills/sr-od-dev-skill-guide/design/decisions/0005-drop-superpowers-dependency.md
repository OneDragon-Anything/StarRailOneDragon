# 0005. 去 superpowers:writing-skills 依赖,整合核心写法

- **Status**: accepted
- **Date**: 2026-08-04
- **Supersedes**: 旧 SKILL.md「## 与 superpowers:writing-skills 的关系」段(defer 通用写法给 superpowers)

## Context
原 SKILL.md 有一段「与 superpowers:writing-skills 的关系」,把通用写法(frontmatter 字段 / SDO / token 效率 / 结构 / cross-reference)**defer 给 superpowers**(「它讲得全,引用即可,本 skill 不重复」)。问题:
1. **依赖外部 skill**:虽规范 3 允许项目内 dev skill 引其它 skill,但团队工具 / 模型异构 + 想做**内聚**的单 skill(写 skill 的规范自含,不东拼西凑)。
2. **立场冲突**:superpowers 是**严格 TDD 框架**(Iron Law:每个 skill 必须先 RED baseline 看失败,无例外),与本 skill「两类 skill / 方法论覆盖型 RED 可省」**直接冲突**(外部效度不足,见 ADR-0004 §3.1 同源)。
3. **体系散**:本 skill 叠加的(design/ + ADR、自包含硬门 + 引用卫生、写法工程指南)superpowers 没有;defer 通用部分 + 自造叠加部分 → 整体不内聚。

## Decision Drivers
- **内聚**:写 skill 的规范单 skill 自含,不跨 skill 拼凑。
- **稳定**:不随 superpowers 版本 / 可用性 / 安装情况漂移。
- **可控立场**:保留本 skill 对 TDD 的弱化(RED 可省),不被 superpowers Iron Law 绑架。

## Considered Options
1. **继续 defer 给 superpowers**(旧做法):依赖 + 立场冲突 + 不内聚。
2. **整合核心 + 刻意偏离**(选中):把 superpowers 通用写法核心吸收进 `references/writing-craft.md`,刻意偏离 Iron Law,丢弃 superpowers 内部附件。
3. **完全自造、不参考 superpowers**:丢 superpowers 沉淀的好东西(SDO 实测陷阱 / form-to-failure 对照实验 / token 手法)。

## Decision
选 2:
- **整合** superpowers 通用写法核心(frontmatter 规则 / SDO / token 效率 / 正文结构模板 / form-to-failure / 例子与反模式 / 何时建)→ `references/writing-craft.md`(与本项目讨论的 lost-in-the-middle / right altitude / progressive disclosure 拆分 / refactor / minimal+RCA 融合)。
- **刻意偏离** superpowers Iron Law:保本 skill「两类 skill」(方法论覆盖型 RED 可省,理由 = 外部效度 / 异构,见 writing-craft §3.1);GREEN 验证两类都不可省。
- **丢弃** superpowers 内部附件:graphviz flowchart 约定、`render-graphs.js`、`persuasion-principles.md`、重 pressure-scenario 测试 apparatus(`testing-skills-with-subagents.md`)。
- SKILL.md 删 defer 段,两类 skill 重述为本 skill 自身立场,加指针指 `references/writing-craft.md`。

## Consequences
- **正向**:单内聚 skill,写 skill 的规范全在 `sr-od-dev-skill-guide/` 内(SKILL.md + references/),无外部写法依赖;保留对 TDD 的弱化立场;writing-craft 一处统一写法工程指南。
- **负向**:writing-craft 要随业界(context engineering / prompt 研究)更新自负,不再自动跟 superpowers 演进。
- **follow-up**:① 定期回看 Anthropic context engineering / skill 新实践,更新 writing-craft;② 其他 skill 若仍 `@` / 强引 superpowers:writing-skills 的,按本 ADR 改引本 skill 的 references。

## Links
- SKILL.md(删 defer 段 + 两类 skill 重述 + 指针)。
- `../../references/writing-craft.md`(整合后的写法指南,§6 列偏离)。
- 同源外部效度问题:[ADR-0004](0004-reference-hygiene-invariants.md)(baseline 单环境不足)。
