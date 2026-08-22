# ADR-0005 阵容知识方法论的家 = skill(docs 留判例+指针)

## Status

accepted(2026-08-22;用户指令「将这部分迁移到 skill 中,变成阵容的方法论」)

## Context

阵容提炼的证据三层(统计骨架×逐篇细节×机制解释)初版写在 `docs/game/currency_war/research/combo_methodology.md`(知识文档)。用户要求迁入 skill。方法论与知识的归位冲突:research 层的写作纪律管「知识怎么写」,而「怎么提炼知识」是操作规程——按项目分层判据,操作规程的单一源应是 skill(跨会话、跨人、指令式),知识文档记被消费的结论与判例。

## Considered Options

1. 两处全文保留(docs + skill):双源漂移,违反单源纪律。
2. 留 docs 不进 skill:方法论对「不读 skill 的读者」可见,但智能体工作流不会读到——提炼/重跑时跳层病复发。
3. **skill 全文承载,docs 留精简版(工作流一句+判例)+ 指针**(选):操作入口单一;知识文档读者仍能从指针找到方法论,判例(r146)留在知识语境里。

## Decision

选 3。skill 侧新增 `references/compo-knowledge.md`(证据三层职能表/从零提炼六步/单套修订/版本重跑/防坑)+ SKILL.md 主章节(核心纪律一段+细则指针);combo_methodology 原节压缩为指针+判例。

## Consequences

- 证据三层表格只在 skill 一处;改方法论改 skill,docs 判例随判例语义(知识)独立演进。
- combo_methodology 的读者(人/只读 docs 的流程)依赖指针跳转——指针断链时 grep skill 目录名可恢复。
