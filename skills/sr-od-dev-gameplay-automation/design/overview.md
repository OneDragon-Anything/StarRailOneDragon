# sr-od-dev-gameplay-automation · 设计概览(what)

## 定位
本 skill 是**通用的新玩法自动化开发生命周期方法论 playbook** —— 把"从零开发一个新玩法自动化到产出可运行 SrApplication"拆成可复现阶段(0-9),每阶段给判据,全程守「看→动→等→验」循环。给 coding agent 看,**不绑具体玩法**。

## 背景 / 来源(provenance)
本 skill 的方法论最初从「货币战争」自动化开发中提炼(货币战争是试验场),随实战迭代持续优化,遇新的可通用经验增量补。**具体玩法细节(机制/键位/坐标/数据)归各玩法 `docs/game/` 与 `docs/game/gameplay/<play>.md`,不进本 skill** —— 本 skill 只记跨玩法通用的方法论 / 判据 / 不变量。

## 范围 / 边界
- **覆盖**:阶段 0-9 全流程(先验现实约束 → 玩法建档 → 找兄弟 → 画面建档 → 设计 → 实现 → 验证 → 策略 → 事件长尾 → 测试文档);全程跨阶段不变量(证据纪律、知识维护、调试纪律);框架级踩坑清单。
- **不管**(深度细则 defer 给协作 skill,不重复):画面建档/screen_info area 维护细节 → `sr-od-dev-screen-onboarding`;UI 区域坐标检测 → `sr-od-dev-ui-region-detect`;bug 决定怎么修 → `sr-od-dev-deciding-a-fix`。
- **不绑具体玩法**:方法论抽象成判据("X 条件下选 A,Y 条件下选 B"),不写"某玩法用了 A"。

## 构成
- `SKILL.md`(always-on,每次触发加载):frontmatter + 总流程阶段表 + 阶段 0/1/3/7 的核心判据 + 跨阶段不变量(证据纪律/知识维护/调试纪律)+ 协作 skill 指针。
- `references/`(situational,按需读):`screen-identification.md`(阶段 3 深度)、`build-craft.md`(阶段 2/4/5/6/9 深度)、`runtime-iteration.md`(阶段 8 + 调试深度)、`framework-pitfalls.md`(框架踩坑清单)。
- `design/`(本文 + ADR,给后续维护者,不进智能体执行上下文)。

## skill 类型 + 测试
方法论覆盖型(整合业界方法论 + 实战提炼的生命周期 playbook 成系统流程)。按 `sr-od-dev-skill-guide` 两类 skill:**RED 可省,GREEN 不可省**。GREEN 方法 = utility test(干净工作空间 + 子 agent 拿本 skill 从零开发一个新玩法自动化 + 扮用户只答所问 + 观察 gap + 修 + 循环)。当前状态:draft(GREEN-pending)。

## 维护(何时更新本 skill)
开发中遇到一个**可通用**的新经验/坑/方法论(不绑具体玩法),就往 SKILL.md 对应阶段或 `references/framework-pitfalls.md` 加一条,增量维护,不强求一次写全。**具体玩法细节不进本 skill**(归该玩法 docs)。
