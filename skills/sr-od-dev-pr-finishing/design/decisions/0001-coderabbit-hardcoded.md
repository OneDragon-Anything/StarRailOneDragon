# 0001. CodeRabbit 写死进 skill(非 review-bot 抽象)

- **Status**: accepted
- **Date**: 2026-07

## Context
本 skill 管的是「把 PR 跑到完善可合并」,其中自动化 review 完成态、resolve 时机、auto-resolve 行为等都依赖具体的 review bot 行为。团队各项目**统一采用 CodeRabbit**(非偶然选择)。问题是:skill 写成「以 CodeRabbit 为前提」(直接用它行为做判据),还是写成「review-bot 中立」(抽象出通用接口,再针对某 bot 适配)?

## Decision Drivers
- **可执行**:判据要能落到具体可观测信号(某 bot 回的 ack comment body、暂停 comment 文案),抽象接口会让指令悬空、agent 不知看哪里。
- **维护成本**:团队实际只用 CodeRabbit,review-bot 中立是「为不会发生的切换付抽象税」。
- **诚实标注耦合**:若哪天换 bot,哪些表述要跟着改要一目了然。

## Considered Options
1. **review-bot 中立**(抽象出「review 完成」「auto-resolve」通用概念,不点名 bot):通用,但判据无法落到具体可观测信号(不同 bot 的 ack 文案 / 行为不同),agent 照做不了。
2. **CodeRabbit 写死**(选中):指令直接以其行为为前提,可执行、信号具体;耦合显式可见。
3. **中立骨架 + CodeRabbit 适配附录**:看似两全,但实际只用一个 bot → 双源、易漂移、维护重。

## Decision
选 2:skill 正文直接以 CodeRabbit 为前提(命名 `@coderabbitai`、ack comment body 文案、auto-pause 机制等)。若团队改用其它 review bot,「review 完成态判据」「auto-resolve 行为」「push 触发机制」等表述需同步调整。

## Consequences
- **正向**:判据具体可执行(指 CodeRabbit 实际回的 comment / 行为);耦合显式,换 bot 时全局搜 `coderabbitai` / CodeRabbit 即知改哪。
- **负向**:换 review bot 要改 skill 正文(不止删一行);对非 CodeRabbit 团队不通用(但本 skill 本就是项目内 dev skill,不独立发布,可接受)。
- **follow-up**:若团队切 bot,重写「review 完成态」相关流程段(链 ADR-0003 的判据)。

## Links
- SKILL.md「done criteria 2」+「流程 1」(CodeRabbit review 触发 / 完成态判据)。
- 相关平台行为判据:[ADR-0003](0003-coderabbit-state-detection.md)。
