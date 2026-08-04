# 0003. CodeRabbit 完成态靠 ack comment + auto-pause 检测(非 check run / 偶发假设)

- **Status**: accepted
- **Date**: 2026-07

## Context
两个 CodeRabbit 平台行为会打破 naive 假设,导致 agent 误判「没 review」或「review 没触发」而干等或空等。均经实战 PR 2419 验证:

1. **增量 review 无新建议时 API 无痕**:CodeRabbit 增量 review 没新建议时,**不建 check run、不留 review 记录**,只回一条 issue comment ack。naive 判据「看 check run / 看 `reviews` 有无新记录」会误判「没 review」(实战:PR 2419 增量 review 完成但 API `reviews` 停在上一天、该 commit 无 CodeRabbit check run)。**手动 @ 后 ack 的演变**:ack comment 先回 `Review triggered`(review 进行中,中间态),完成后 CodeRabbit **编辑同一条** comment 为 `Review finished`(不另发新 comment)。判完成必须看到 `finished`,别把 `triggered` 当结果(实战:PR 2419 `bf2ebfea` 手动 @ 后 06:38Z 回 `triggered`,review 完成后同条被编辑成 `finished`)。
2. **push 后不自动触发 = 被 auto-pause(非偶发)**:CodeRabbit 有 `reviews.auto_review.auto_pause_after_reviewed_commits` —— PR 活跃开发 / 频繁 commit 时**自动暂停** review,之后**每次 push 都不自动触发**(不是偶尔)。检测:PR 有 `Reviews paused` comment。暂停下两命令语义不同:`@coderabbitai review` = **单次**触发(保持暂停,下次 push 仍不自动);`@coderabbitai resume` = **恢复**自动(之后 push 自动触发,ack `Reviews resumed.`)。实战:PR 2419 从 7-01 起被 auto-pause,故每轮 push 都要手动补 —— 曾误判为「偶尔不触发」,实际是**始终暂停**。

> 区别 **rate limit**(另一类 push 不 review):rate limit 是组织级 per-developer 配额(ack 含「Review limit reached」+「Next review available in <时长>」),等时间恢复;auto-pause 是频繁 commit 暂停(`resume` 恢复)。两者检测 query 不同。

## Decision Drivers
- **对症判据**:用 CodeRabbit 实际暴露的信号(ack comment body / 暂停 comment),而非它不暴露的(check run / reviews 新记录)。
- **防误判**:把「平台行为使然的『无痕』『不触发』」与「真没 review / 真失败」区分开,避免 agent 干等或空报。
- **实战可复现**:PR 2419 作为论据,后人能复核。

## Considered Options
1. **naive 判据**(看 check run / 看 reviews 有无新记录 / 假设 push 必自动触发):被上述两个平台行为直接打破 → 误判。
2. **ack comment body + auto-pause 检测**(选中):用 CodeRabbit 实际暴露的信号判。
3. **只用 `@coderabbitai review` 兜底,不判状态**:能驱动 review 但不知何时算「完成」→ done criteria 落空。

## Decision
选 2,判据写进 SKILL.md:
- **完成态**:查 CodeRabbit 最近一条 ack issue comment 的 body,含 `Review finished`(在 `✅ Action performed` 的 `<details>` 里)即这轮完成;若 body 是 `Review triggered` → 还在进行,等几分钟再查(完成后编辑同条为 `finished`,不另发)。
- **push 不自动触发**:先查暂停(`gh pr view <PR> --json comments --jq '.comments[]|select(.body|test("Reviews paused"))'`,命中 = 已暂停);命中则按需 `@coderabbitai review`(单次)或 `@coderabbitai resume`(恢复自动)。未暂停却不触发(罕见)才走 `review` 兜底。

## Consequences
- **正向**:判据对症平台行为,agent 不干等 / 不误报;PR 2419 论据可复现复核。
- **负向**:判据耦合 CodeRabbit 具体文案(`Review finished` / `Reviews paused` 等),CodeRabbit 改文案要跟着调(与 [ADR-0001](0001-coderabbit-hardcoded.md) 的耦合一致)。
- **follow-up**:CodeRabbit 若改 ack 文案 / 暂停机制,更新 SKILL.md 流程 1 对应 query 与关键词。

## Links
- SKILL.md「流程 1」(摸现状:review 触发 / 完成态 / auto-pause / rate limit 检测)。
- 耦合前提:[ADR-0001](0001-coderabbit-hardcoded.md)。
- 论据:实战 PR 2419(commit `bf2ebfea`)。
