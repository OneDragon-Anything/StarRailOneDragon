# 0002. 全生命周期单 skill + 深度 defer 协作 skill(不重复)

- **Status**: accepted
- **Date**: 2026-08-04

## Context
本 skill 管"从零开发新玩法自动化",覆盖阶段 0-9 全流程。但其中多个阶段有**更专精的协作 skill** 已存在:
- 画面建档/screen_info area 维护 → `sr-od-dev-screen-onboarding`
- UI 区域坐标检测 → `sr-od-dev-ui-region-detect`
- bug 决定怎么修 → `sr-od-dev-deciding-a-fix`

问题:本 skill 该**重复**这些协作 skill 的内容(自包含),还是**只 defer**(引用)?另外:本 skill 该覆盖**全生命周期**,还是**只覆盖实现**(更窄)?

## Decision Drivers
- **不重复(DRY)**:同一方法论两处写 → 漂移;协作 skill 是该方法论的单一真相源。
- **端到端价值**:自动化开发的价值在"从理解玩法到产出可运行 app 的完整流程 + 阶段门控判据",抽掉任一段(如玩法建档/事件长尾)就断链。
- **`sr-od-dev-skill-guide` 规范 3**:项目内 dev skill 可引用其它 skill(写完整标识符)。

## Considered Options
1. **重复协作 skill 内容(自包含)**:DRY 违反,两处会漂移。
2. **只覆盖实现阶段(窄 scope)**:断链,失端到端价值。
3. **全生命周期单 skill + 深度 defer 协作 skill(不重复)**(选中):本 skill 给完整流程 + 每阶段判据 + 跨阶段不变量;专精深度(screen_info 建模细节、坐标检测、bug 修复决策)引用协作 skill。
4. **全生命周期 + 重复协作内容**:最冗余。

## Decision
选 3:
- 本 skill **scope = 全生命周期**(阶段 0-9),给每阶段判据 + 跨阶段不变量 + 框架踩坑。
- 专精深度**defer 给协作 skill**(写完整标识符):`sr-od-dev-screen-onboarding`(画面建档/screen_info area)、`sr-od-dev-ui-region-detect`(坐标检测)、`sr-od-dev-deciding-a-fix`(bug 修复决策)。本 skill 只在相关阶段一句指针 + 该 skill 才管的核心判据摘要,不重复其完整方法论。
- SKILL.md「协作 skill」节集中列指针。

## Consequences
- **正向**:无漂移(协作 skill 是 SSOT);本 skill 紧凑聚焦"生命周期编排 + 阶段判据";agent 拿到完整流程,需深度时按指针跳协作 skill。
- **负向**:agent 需跨 skill 拼(需主动读协作 skill);协作 skill 改名/移除 → 本 skill 指针过期(规则 3 已提交 + 稳定可校验,PR review 兜底)。
- **follow-up**:协作 skill 演进时核对指针仍准;若某协作 skill 长期不存在,该段深度回填本 skill references/。

## Links
- `sr-od-dev-skill-guide` 规范 3(项目内 dev skill 可引其它 skill,完整标识符)+ [ADR-0002](../../sr-od-dev-skill-guide/design/decisions/0002-self-contained-framework-interface-names.md)。
- 本 skill SKILL.md「协作 skill」节。
