# sr-od-dev-debug-automation · 设计文档索引

本 skill 的设计存档(**给后续维护者,不进智能体执行上下文** —— SKILL.md 不写「见 design/」取使用信息)。

- `overview.md` —— 定位 / 边界 / 构成 / 当前状态(what)。
- `case-study.md` —— SKILL.md 判据的来源论据(上游一次真实排查的弯路 + 采集复现);具体函数名 / 坐标 / 版本号是那次案例的偶然细节,记这不进 SKILL.md。含非本 skill 范围的框架可排查性 follow-up。
- `decisions/` —— ADR(架构决策,arc42 §9 = why):
  - [INDEX](decisions/INDEX.md)
  - [0001 叠加在 superpowers:systematic-debugging 之上](decisions/0001-layer-on-systematic-debugging.md)

方法论细则见 `sr-od-dev-skill-guide`(`design-docs.md` / `writing-craft.md`)。
