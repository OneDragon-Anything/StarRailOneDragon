# sr-od-dev-skill-guide · 设计文档索引

本 skill 的设计存档(**给后续维护者,不进智能体执行上下文**)。

- `overview.md` —— 定位 / 边界 / 4 条硬规范是什么 / 落点 / 写法来源 / 当前状态(what)。
- `decisions/` —— ADR(架构决策,arc42 格式 = why):
  - [INDEX](decisions/INDEX.md)
  - [0001 design 与 ADR 分离(取代单 design.md)](decisions/0001-design-adr-separation.md)
  - [0002 自包含 + 框架地基级接口名可写进 SKILL.md](decisions/0002-self-contained-framework-interface-names.md)
  - [0003 写方法论不写具体例子](decisions/0003-methodology-not-examples.md)
  - [0004 引用卫生硬门 + 硬规范作不变量](decisions/0004-reference-hygiene-invariants.md)
  - [0005 去 superpowers 依赖,整合核心写法](decisions/0005-drop-superpowers-dependency.md)
  - [0006 skill 测试方法论(utility test 作方法论型主方法)](decisions/0006-skill-testing-methodology.md)

方法论细则见上级 `../references/`:`design-docs.md`(design/ + ADR + 引用卫生)、`writing-craft.md`(SKILL.md 写法)、`skill-testing.md`(GREEN 测试方法)。
