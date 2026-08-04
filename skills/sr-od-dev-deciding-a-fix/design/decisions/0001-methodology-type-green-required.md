# 0001. 方法论覆盖型归类(RED 可省,GREEN 必做)

- **Status**: accepted
- **Date**: 2026-08-04

## Context
`sr-od-dev-skill-guide`「两类 skill」要求按内容依据分类决定测试制度:
- **纠正型**:改变智能体默认会做错的行为,内容依据是 baseline 暴露的 failure → RED(baseline)必做,再写最小纠正。
- **方法论覆盖型**:整合业界已验证的方法论成系统流程,内容依据是方法论本身 → RED 可省;GREEN 必做。

本 skill 内容 = 整合 RCA / Impact Analysis / Trade-off Matrix / Hypothesis-driven Verify 业界方法论成「决定怎么修」的系统流程,不是从单一 baseline failure 推导的最小纠正。

## Decision Drivers
- **外部效度**:团队各人工具 / 模型异构,单一 baseline 看到的失败可能只是某模型 / env 的弱点,外部效度不足(见 skill-guide [ADR-0006](../../sr-od-dev-skill-guide/design/decisions/0006-skill-testing-methodology.md) / `writing-craft.md` §3.1)。
- **业界方法论普适**:RCA / Trade-off Matrix 等是跨工具 / 模型 / 项目的通用决策方法,作内容依据比 baseline failure 更普适。

## Considered Options
1. **纠正型(RED 必做)**:把本 skill 当「纠正 baseline 暴露的具体失败」,只写最小纠正。但内容依据是方法论而非 failure → 错配;且单环境 baseline 外部效度不足。
2. **方法论覆盖型(RED 可省,GREEN 必做)**(选中):以业界方法论为据,RED 可省;GREEN utility test 验证 agent 能否照方法论自主完成决策。

## Decision
选 2:本 skill 归方法论覆盖型。RED 可省;GREEN 必做(方法见 skill-guide `references/skill-testing.md` §2)。

baseline(pywin32 #2428)仍跑了,价值不在「证明 skill 必要」(那是纠正型用法),而在**沉淀两个必填槽位的论证**(见 [ADR-0002](0002-five-step-structure.md))—— 不进 SKILL.md 正文(正文只放方法论 / 判据)。

## Consequences
- **正向**:测试制度对症;方法论作主基底抗工具 / 模型异构;baseline 论证沉淀进 ADR 不污染 always-on 正文。
- **负向**:GREEN utility test 需起子 agent 多轮,成本不低(尚未跑,见 overview「当前状态」)。
- **follow-up**:跑 GREEN(干净上下文子 agent + 真实 bug 决策任务 + 扮用户只答所问 + 观察 gap + RCA 过滤 + 修 + 循环),通过后把 overview 状态从 draft 改为 validated。

## Links
- skill-guide [ADR-0006](../../sr-od-dev-skill-guide/design/decisions/0006-skill-testing-methodology.md)(skill 测试方法论 / utility test 作方法论型主方法)。
- skill-guide [ADR-0005](../../sr-od-dev-skill-guide/design/decisions/0005-drop-superpowers-dependency.md)(去 superpowers 强制 RED 立场)。
- skill-guide `references/writing-craft.md` §3.1(minimal + RCA 过滤增量)。
- skill-guide `references/skill-testing.md` §2(utility test 详解)。
- 本 skill [ADR-0002](0002-five-step-structure.md)(baseline 论证去向)。
