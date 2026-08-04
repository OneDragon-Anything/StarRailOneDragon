# 0001. 阶段门控 playbook + 渐进式披露(what 留 SKILL.md vs 进 references)

- **Status**: accepted
- **Date**: 2026-08-04

## Context
本 skill 的方法论从「货币战争」自动化开发提炼,随实战增长,SKILL.md 一度膨胀到 ~190 行密集正文(LCS 误匹配深挖、调试纪律、事件长尾、运行时不确定性、框架踩坑……全堆 always-on)。问题:
- **always-on token 成本**:SKILL.md 每次触发都注入上下文;lost-in-the-middle(Liu et al. 2023)+ context rot → 越长回忆精度越降。always-on 应只放**每次都要的核心**(方法论/不变量/判据),情境性深度应按需加载(progressive disclosure)。
- **结构缺主脊**:一堆平行"通用经验"段落,缺"先做什么再做什么"的可复现骨架 → agent 不知从哪进。
- 违反 `sr-od-dev-skill-guide` 规范 2(指令式 compact)+ writing-craft §1.7(token 效率)/§2(progressive disclosure)。

## Decision Drivers
- **token 效率**:always-on 留最小高信号集,情境深度进 references/ 按需读。
- **可复现**:agent 照流程能从零走到产出,不是一堆零散经验。
- **可维护**:经验增量补时有明确归属(某阶段 / 跨阶段不变量 / 框架踩坑)。

## Considered Options
1. **保留单一大 SKILL.md(~190 行)**:简单,但 always-on token 重 + 结构无主脊 + 违反 writing-craft。
2. **阶段门控 playbook(SKILL.md 主脊)+ 渐进式披露(深度进 references/)**(选中):SKILL.md 留总流程阶段表 + 阶段 0/1/3/7 核心判据 + 跨阶段不变量;阶段 2/3/4/5/6/8/9 的深度细则进 4 个 references/ 文件按需读。
3. **按阶段拆成多个 skill(每阶段一 skill)**:过度拆分,丢失"端到端流程 + 阶段门控判据"的整体价值(见 [ADR-0002](0002-lifecycle-scope-defer-to-siblings.md))。
4. **拆 per-concern(画面/实现/调试各一 skill)**:同 3,且与协作 skill(screen-onboarding/ui-region-detect)重叠。

## Decision
选 2:
- **SKILL.md 主脊** = 总流程阶段表(阶段 / 做什么 / 达标判据 / 深度细则指针)+ 阶段 0/1/3/7 的核心判据(够具体能引导 + 够抽象)+ 跨阶段不变量(证据纪律 / 知识维护 / 调试纪律)+ 协作 skill 指针。
- **references/** 按主题(非阶段)组织深度细则:`screen-identification.md`(画面建档,阶段 3)、`build-craft.md`(构建工艺,阶段 2/4/5/6/9)、`runtime-iteration.md`(运行时迭代,阶段 8 + 调试)、`framework-pitfalls.md`(框架踩坑清单)。SKILL.md 阶段表"深度细则"列指针 → 按需读(just-in-time)。
- 跨阶段不变量(证据纪律 / 知识维护 / 调试纪律)留 SKILL.md always-on —— 它们**每次都用**,即使长也该内联(writing-craft §2:核心但长 → 留 SKILL.md,拆出去每次再读更费)。

## Consequences
- **正向**:always-on 紧凑(~110 行 vs 旧 190);agent 触发时拿主脊 + 判据,需要某阶段深度时按指针读 references/;经验归属清晰。
- **负向**:多 4 个 references 文件;agent 需主动按指针读(若忘了读会漏深度 —— 靠阶段表"深度细则"列显式指针降低漏读)。
- **follow-up**:随新经验增量补时,先判归属(某阶段深度 → references/;跨阶段不变量 → SKILL.md;框架踩坑 → framework-pitfalls.md);SKILL.md 长度反弹就再抽 references/。

## Links
- `sr-od-dev-skill-guide` 规范 2 + `references/writing-craft.md` §1.7(token)/§2(progressive disclosure)。
- 本 skill SKILL.md 总流程表 + references/。
