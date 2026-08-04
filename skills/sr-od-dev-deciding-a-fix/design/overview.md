# sr-od-dev-deciding-a-fix · 设计概览(what)

## 为什么做
已报告的 bug,"定位根因"有 `superpowers:systematic-debugging`,"决定怎么修"却缺一个系统决策框架。常见失败:直接采纳 issue 里用户给的方案、根因挖得不够深(误判方案临时/永久)、介入点前提没验证。本 skill 把"决定怎么修"锚定到业界方法论(RCA / Impact Analysis / Trade-off Matrix / Hypothesis-driven Verify),给一个可被 review 的决策流程。

## 定位与边界
- 管:从"故障机制已知"到"选定并验证修复方案"的决策。
- 不管:定位故障机制(→ `superpowers:systematic-debugging`);新功能设计(→ `superpowers:brainstorming`)。

## 构成(五步决策流程)
SKILL.md 正文给出 5 步可执行指令,每步锚定一个业界方法论:
0. 确认故障机制(入口)。
1. 画因果链(RCA / 5 Whys / Fault Tree)—— 停在 actionable 层(有权且能修的那层)。
2. 影响面 + 可行动性(Impact Analysis / Blast Radius)。
3. 候选方案(Intervention Selection)。
4. 前提验证 + 权衡(Trade-off Matrix)—— 必填:根因链的「上游修复状态」。
5. 假设驱动验证(Hypothesis-driven Verify)。

## 落点(项目约定)
- 根 `skills/sr-od-dev-deciding-a-fix/`(源,提交共享)。
- junction `.claude/skills/sr-od-dev-deciding-a-fix` → 根目录(`cmd /c mklink /J`,免管理员,不提交)。
- 结构:SKILL.md(入口,方法论 / 判据)+ design/(overview + decisions ADR)。

## 自身一致性
遵守 `sr-od-dev-skill-guide` 4 条硬规范:
- **规范 1**:有 `design/`(design 与 ADR 分开);设计 what 在本文件,决策 why 在 `decisions/` ADR。
- **规范 2**:SKILL.md 指令式(祈使句 + 判据)。
- **规范 3**:自包含 —— 只引 `superpowers:*` skill(写完整命名空间标识符),不引目录外文件、不引 memory / gitignored。
- **规范 4**:SKILL.md 只写方法论 / 判据,具体案例(pywin32 #2428)作 ADR 论据进 `design/decisions/`,不进 always-on 正文。

## 当前状态(GREEN)
- **draft**(GREEN-pending):按 skill-guide「两类 skill」,本 skill 为**方法论覆盖型**(见 [ADR-0001](decisions/0001-methodology-type-green-required.md)),RED 可省;**GREEN utility test 尚未跑**(跳过 GREEN 却声称合规 = 违规,故诚实标 draft)。
- **GREEN 方法**(待跑):起干净上下文子 agent,给一个真实 bug 决策任务(如 pywin32 #2428 同型场景),扮用户只答所问、不替做,观察 agent 能否自主走完 5 步并产出可 review 的决策,记 gap → RCA 过滤 → 修 skill → 循环(见 skill-guide `references/skill-testing.md` §2)。
- baseline(pywin32 #2428)已跑,价值不在「证明 skill 必要」(那是纠正型用法),而在沉淀两个必填槽位的论证,见 [ADR-0002](decisions/0002-five-step-structure.md)。
