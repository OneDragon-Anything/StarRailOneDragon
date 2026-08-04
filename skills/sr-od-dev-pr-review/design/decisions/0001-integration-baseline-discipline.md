# 0001. 集成基线纪律(主仓先 merge origin/main + 测试仓同名分支隔离)

- **Status**: accepted
- **Date**: 2026-08-04(形式化日;决策本身随 skill 创建 ~2026-07)

## Context
两条同源的基线问题,均出自「在旧/错的 base 上审查」:
1. **主仓**:PR 基于旧 main。在旧 base 上审 = 审一个不存在的世界 —— 漏 API 不兼容、被 main 改过的同文件、依赖 main 新加文件等问题。老 PR(#2300 等)缺 main 后加的 `server.py`,不 merge 直接在分支跑 server → `No module named` 崩;merge 后才正常。曾因没先 merge 就改代码被用户纠正(顺序必须 merge → 审 → 改,不能跳)。
2. **测试仓**:测试仓 `main` 是 test-check 的基准,必须与主仓 `main` 同步。若把**未合 PR** 的测试直接合到测试仓 `main` → 测试仓 `main` 领先主仓(测了还不存在的代码)→ 所有 PR 的 test-check 全红。实测:#2348 的测试 `4ca301d` 误合测试仓 `main`,致 `main` 自己 + 所有后续 PR 的 test-check fail。正确时序:该 PR 合进主仓 `main` 后,再把它的测试分支合进测试仓 `main`。

## Decision Drivers
- **审得准**:审查基线 = 「PR 合了实际长什么样」,不是旧 base。
- **test-check 不被污染**:测试仓 main 与主仓 main 同步,未合 PR 的测试不进测试仓 main。
- **防人误操作**:补测试时不会忘记切分支 → 误 commit 测试仓 main。

## Considered Options
1. **审旧 base(不 merge main)**:简单,但漏集成问题;不解决测试仓污染。
2. **只 merge 主仓 main,测试仓随意**:主仓审得准,但测试仓 main 被污染 → test-check 全红。
3. **主仓先 merge origin/main + 测试仓同名分支隔离**(选中):两处基线都守;测试改动只进同名分支,绝不进测试仓 main。
4. **用本地可能被 merge 污染的旧分支**:基线不可信。用 `gh pr checkout`(拉 PR 当前 HEAD)。

## Decision
选 3:
- **主仓**:每个 PR `gh pr checkout <n>` → `git fetch origin main` → `git merge origin/main`(fetch 确保 remote 引用最新,否则 merge 的是旧 `origin/main`)。审查与改动都在 merged 结果上。
- **测试仓**:处理每个 PR 前,无论该 PR 有无配套测试仓 PR,都先确保有同名分支(`git -C sr-od-test checkout <PR 同名分支>`,无则 `checkout -b`),再 `fetch origin && merge origin/main`(与主仓同理)。PR 的测试改动**只进该分支**,绝不直接 commit/push 测试仓 `main`。哪怕暂无测试也先建分支占位,防后续忘记切分支。
- 测试改动走 `git -C sr-od-test`(主仓 gitignore 静默跳过)。

## Consequences
- **正向**:审查基线 = 集成结果(test-check 红的真实风险被消除);测试仓 main 始终与主仓 main 同步;建分支占位防人误操作。
- **负向**:每个 PR 多两步(主仓 merge + 测试仓切分支);有 merge 冲突时要解(但解的过程本身暴露集成影响,见 [ADR-0005](0005-conflict-resolution-strategy.md))。
- **follow-up**:无。

## Links
- SKILL.md §0(分支与基线)。
- 相关:[ADR-0005](0005-conflict-resolution-strategy.md)(merge 冲突解决)。
