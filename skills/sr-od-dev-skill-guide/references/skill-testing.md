# Skill 测试方法论(sub-agent)

> 本文件是 `sr-od-dev-skill-guide` 的测试方法。**写 / 改 skill 后按此验证**(GREEN 不可省,见 SKILL.md「两类 skill」)。
> 与 superpowers 的区别:**不强制 RED**(见 [ADR-0006](../design/decisions/0006-skill-testing-methodology.md));按 skill 类型选测试制度。

## 0. 为什么测 + 测什么
skill 是给 agent 用的指令。**你以为写清楚了 ≠ agent 真能照做**。必须实测:让一个**干净上下文**的 agent 用这 skill 干真活,看它能不能干好。这是唯一能发现"你以为清楚、其实没写清"的办法。

**GREEN 状态语义**:skill 两态 —— **draft**(GREEN-pending:诚实标「待测」,可带 caveat 用)/ **validated**(GREEN 过)。**跳过 GREEN 却声称合规 = 违规**(比 draft 糟)。新写 skill 允许 draft,但 status 写明。**声明位置**:写进 `design/overview.md` 的状态节(maintainer 文档,不污染 always-on SKILL.md)。
**「合规」≠「validated」**:**合规** = 满足 4 硬规范(结构性,硬门);**validated** = GREEN 过(质量闸)。draft skill 可「结构合规但未 validated」—— 两者独立;「完成」需结构合规,GREEN-validation 用 draft/validated 跟踪。

## 1. 两类测试制度(映射两类 skill)

### 1.1 方法论覆盖型 / how-to / reference(我们的大多数)→ **utility test**(主方法)
测:**skill 能不能让 agent 真把活干好、自主推进**(不是守不守规矩)。
形态:**干净工作空间 + 可交互子 agent + 你扮用户只答所问 + 观察 gap + 修 skill + 循环**(详 §2)。

### 1.2 纠正型(有动机绕过的纪律规则,少数)→ pressure test
测:**压力下守不守规矩**。
形态:一次性脚本化 A/B/C 选择题,叠 3+ 重压力(时间 / 沉没成本 / 权威 / 疲惫),抓 rationalization 原话,堵漏循环。来自 superpowers 思路(非依赖);RED(baseline 无 skill 看失败)+ GREEN(有 skill 看守规矩)+ REFACTOR(堵新 rationalization)。

**选哪个**:问"这 skill 防的是'agent 会偷懒绕过'(纠正型 → pressure),还是'agent 不会做这方法'(方法论型 → utility)"。

## 2. utility test 详解(方法论型主方法)

### 2.1 设置
- **干净工作空间**:`git worktree`(隔离文件)或子 agent 用 worktree 隔离;子 agent **从干净上下文起**(只给它 skill + 任务,不泄漏你 session 的推断)—— 观察到的行为才能归因到 skill。
- **子 agent 有 skill**:待测 skill 装好 / 可被发现;给它一个**真实任务**(非测验题)。
- **你扮用户(关键)**:子 agent 干活时,你**只回答它问的问题,不给最终答案、不替它决策、不暗示**。它是主角,你是只会"答所问"的真实用户。

- **谁跑 / 何时**:GREEN 由**编排者 / 作者**在 skill 写 / 改**之后**跑(起子 agent 测),**不是**正在编辑该 skill 的子 agent 自己跑(它既当运动员又当裁判 + 受任务边界限,跑不了)。

### 2.2 跑
1. 给子 agent 任务 + 确保 skill 可用。
2. 它推进;遇到不清楚的会**问你**。
3. 你**只答所问**(non-leading facilitation,可用性测试手法):它问"X 放哪"你答路径;它问"选 A 还是 B"你回"你自己定,按 skill" —— **绝不**替它选 / 替它做。
4. 观察它:**在哪卡住 / 乱问 / 走偏 / 产出差**。这些是 skill 的 gap。
5. 记 gap 原话(它问了啥、卡在哪、产出了啥不对)。

### 2.3 修 + 循环
- 每个 gap:**先 RCA**(`writing-craft.md` §3.1)—— 是**通用 gap**(任何 agent 按方法论都会撞)还是 **model/env 特异**?**只修通用 gap** 进共享 skill;模型怪癖进 design ADR。
- 修 skill(补 / 澄清 / 重排),重测,直到子 agent 能**少问、自主、产出达标**地完成。

### 2.4 成功判据(utility)
- 子 agent 完成**真实任务**到达标质量。
- 问题**少且是真实模糊**(非"下一步干啥")。
- 产出符方法论意图。
- 重测不撞旧 gap。

## 3. mechanics(可落地,不写死 harness 细节)
- **干净工作空间**:`git worktree add` / Agent 的 worktree 隔离 / 新 session。
- **可交互子 agent**:起子 agent(Agent / 后台命名 agent),它**问你就答**;一轮不够就 SendMessage 多轮,或它返回问题、你答完再起。
- 子 agent 只给:**任务 + 待测 skill(可发现)**;**不给**你的推断 / 答案。
- 别让子 agent 看你 session 的上下文(污染归因)。

## 4. checklist(两类通用)
**utility(方法论型)**:
- [ ] 干净工作空间 + 干净上下文子 agent
- [ ] 给真实任务(非测验)+ skill 可用
- [ ] 你扮用户只答所问,不替做
- [ ] 记 gap 原话(卡点 / 乱问 / 产出差)
- [ ] 每 gap RCA 过滤 → 只修通用 gap 进 skill
- [ ] 重测:子 agent 少问、自主、达标

**pressure(纠正型)**:
- [ ] 3+ 重压力的 A/B/C 脚本场景
- [ ] baseline(无 skill)看失败 + 抓 rationalization
- [ ] 有 skill 重测看守规矩
- [ ] 新 rationalization → 堵漏 → 重测

## 5. 与 superpowers 的区别(见 ADR-0006)
- **不强制 RED**(方法论型 RED 可省,外部效度不足 —— 你本地看到的失败可能只是你模型 / env 的弱点)。
- 主方法是 **utility test**(测实用性 / 完整性),非 superpowers 的 pressure test(测纪律)。
- 两者互补:纠正型用 pressure,方法论型用 utility。
