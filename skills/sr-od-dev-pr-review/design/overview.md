# sr-od-dev-pr-review · 设计概览(what)

## 为什么做
项目痛点:PR 提交后**无人验证功能**(作者自测、review 多停留在代码层,功能没跑)。本 skill 沉淀一套系统化的「审查 + 验证」方法论(从 30 个 open PR 的实操中提炼),让审查者不只看 diff,还核实背景、跑逻辑、验画面、给可合并结论。

**为什么是 skill**:审查流程触发时自动注入执行上下文(主动);docs 要记得翻(被动)。

## 定位与边界
- **管**:一个 PR 从「拿到分支」到「给可合并结论」的全流程(分诊 → 静态审查 → 背景核实 → 离线/live 验证 → 冲突解决 → 结论)。
- **不管**(引用而非重复):
  - PR 收尾(处理 review comment / 推可合并 / checks)→ `sr-od-dev-pr-finishing`;
  - 单条 review comment 处理 → `superpowers:receiving-code-review`;
  - 画面建档细节 → `sr-od-dev-screen-onboarding`。

## 构成(SKILL.md 的方法论骨架)
- **集成基线纪律**:在「PR + 当前 main」集成结果上审,不在旧 base 上审;测试仓同名分支隔离。
- **L0~L4 分级验证**:L0 分诊判适用 → L1 静态(总做)→ L2 背景核实 → L3 离线 → L4 live(游戏流程类硬性)。每级有则记无则跳。
- **框架语义必查项**:L1 固定查生命周期钩子 / 节点重试预算 / `@operation_node` / `execute()` 重置 / `node_from` 路由。
- **游戏流程 PR 先建玩法理解**:L1 前查 `docs/game/gameplay/` + `docs/game/screens/` 建立玩法理解。
- **冲突解决**:看实际不预设;逻辑纠缠先 live 建档;解完 `py_compile` + `ruff` + `import` 冒烟三连。
- **live 三位一体**:live 不只验 PR,沿途画面未建档顺便补 screen_info(走 `sr-od-dev-screen-onboarding`)——成本最低、价值叠加。

## 落点
- 目录:根 `skills/sr-od-dev-pr-review/`(跨工具源,提交共享)。
- 前缀:`sr-od-dev-`(开发流程类)。
- junction:`.claude/skills/sr-od-dev-pr-review` → 根 skills/(本地建,不提交)。
- 结构:`SKILL.md`(方法论入口)+ `design/`(本文件夹,设计 + ADR)。

## 与现有 skill 的关系
- `sr-od-dev-pr-finishing`:PR 收尾。本 skill 是**收尾前的审查验证**;审完给结论,收尾走 pr-finishing。
- `sr-od-dev-screen-onboarding`:画面建档。本 skill L4 live 时「顺路建档」引用它。
- `sr-od-dev-skill-guide`:本项目 skill 编写规范。本 skill 的结构 / frontmatter / 写法遵循它。

## 当前状态(GREEN 语义)
- **类型**:方法论覆盖型(整合 PR 审查验证方法论成系统流程)。按 `sr-od-dev-skill-guide` 两类 skill,RED 可省、GREEN 不可省。
- **GREEN**:**draft**(GREEN-pending)。方法论本体经 30 个 open PR 实操提炼(有 dogfooding 证据);但按 `sr-od-dev-skill-guide` 的 utility test(干净上下文子 agent + 扮用户只答所问 + 观察 gap)做正式 GREEN 验证待补。
- **结构合规**:满足 skill-guide 4 硬规范(design/ 分离 / 指令式 / 自包含 / 方法论不写具体例子)。
