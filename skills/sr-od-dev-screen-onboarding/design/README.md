# sr-od-dev-screen-onboarding · 设计文档索引

本 skill 的设计存档(**给后续维护者,不进智能体执行上下文**)。SKILL.md 是智能体指令(方法论 + 判据);本目录记「方法论长什么样 + 为什么这么定」。

- [`overview.md`](overview.md) —— 定位 / 边界 / 方法论构成 / 当前状态(what)。
- `decisions/` —— ADR(架构决策,arc42 §9 格式 = why):
  - [INDEX](decisions/INDEX.md)
  - [0001 五步流:客观→主观→建档→缺口→建模](decisions/0001-five-step-flow.md)
  - [0002 MCP 直调 + area CRUD 工具 > 手编 yml / HTTP 脚本](decisions/0002-mcp-direct-call-crud-over-handedit.md)
  - [0003 信息源三层并用:截图 + screen_info + 代码(含版本迁移核对)](decisions/0003-three-information-sources.md)
  - [0004 多模态 vision 必需,不只靠 MCP(含 vision 不可信边界)](decisions/0004-vision-required.md)
  - [0005 截图手动分解 op 节点,不靠跑 app/op 中途 capture](decisions/0005-manual-decomposition-screenshots.md)
  - [0006 重 app 多子玩法按 app 维度建档](decisions/0006-heavy-app-dimension-onboarding.md)
  - [0007 建档文档只写画面事实,过程产物不进描述章节](decisions/0007-doc-stable-facts-only.md)
  - [0008 自包含:webp 转换工具内联进 SKILL.md](decisions/0008-bundled-webp-tool-inline.md)

本 skill 遵守 `sr-od-dev-skill-guide` 4 条硬规范(目录结构 / 指令式 / 自包含 / 方法论不写具体例子)。
