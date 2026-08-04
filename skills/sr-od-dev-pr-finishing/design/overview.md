# sr-od-dev-pr-finishing · 设计概览(what)

## 为什么做
「把 PR 跑到完善可合并」是高频且步骤固定的工作,但知识散落多处:done criteria、CodeRabbit 平台行为、resolve 工具操作、命令清单。不固化则每次重新摸索(实操踩过 replies 漏 `pull_number`、`line` 字段为 null、`comment_id` 与 thread id 体系不同等坑)。

**为什么是 skill 而非 docs**:skill 触发时由智能体自动注入执行上下文(主动);docs 要记得翻(被动)。这类「每次收尾 PR 都要按它走」的流程,skill 的主动注入比 docs 的被动参考更可靠。

## 定位(边界)
横向引用,不重复:

| skill | 管什么 |
|---|---|
| superpowers:receiving-code-review | 单条 review 评论怎么 verify / 回复 / push back(通用方法论) |
| superpowers:finishing-a-development-branch | 实现完成后选 merge / PR / keep / discard |
| **sr-od-dev-pr-finishing(本 skill)** | PR 已开后,把它跑到「完善可合并」(checks + review + resolve + 迭代) |

与 receiving-code-review 重叠约 1/3(单条处理),不冲突,互补:它横向单条,本 skill 纵向整 PR。

## 构成
- **`SKILL.md`**:智能体执行指令 —— done criteria + 6 步流程(摸现状 / 清 unresolved / resolve 时机 / push 迭代 / 合并前 / 关联 PR 协同)+ 边界。每次触发都加载。
- **`design/`**(本目录,给后续维护者,不进智能体上下文):设计概览 + ADR(记「为什么这么定」,尤其 CodeRabbit 平台行为踩坑论据)。

## 范围内的关键选择(why 见对应 ADR)
- **CodeRabbit 作为 review bot 写死进 skill**(非 review-bot 抽象)→ [ADR-0001](decisions/0001-coderabbit-hardcoded.md)。
- **resolve 走 GraphQL `resolveReviewThread` + reply 走 REST replies(用 REST `databaseId`)** —— 两操作两条 API、两套 id,不混 → [ADR-0002](decisions/0002-resolve-reply-api.md)。
- **CodeRabbit 完成态靠 ack issue comment body 判(非 check run/reviews)+ push 不自动触发靠 auto-pause 检测** —— 平台行为驱动的判据 → [ADR-0003](decisions/0003-coderabbit-state-detection.md)。
- **每条 thread 最终都 resolve(不设暂缓类)**:done criteria「无 unresolved」严格满足,不在 PR 上留暂缓项(要后续追踪的另开 issue,不在本 skill 范围)。属范围内约定,不单列 ADR。
- **resolve 时机判据(有 push 等下一轮 review 完成、无 push 等 10 分钟)**:方法论/判据,在 SKILL.md(确保 CodeRabbit「说完话」再 resolve,不抢判断也不干等)。

## 落点(项目约定)
- `skills/sr-od-dev-pr-finishing/`(项目根,跨工具源)。`sr-od-dev-` 前缀:项目开发流程类。
- junction 到 `.claude/skills/sr-od-dev-pr-finishing`:Claude Code 扫 `.claude/skills/` 发现;Windows 用 junction(`mklink /J`)免管理员。junction 不提交(`.claude/` gitignore),每人本地建。

## 当前状态
- **部署**:已 unignore 并提交(目录名 `sr-od-dev-pr-finishing`)。CodeRabbit 限定不阻塞(团队各项目统一采用 CodeRabbit)。
- **GREEN 验证状态**:**draft(GREEN-pending)** —— 本次为按 `sr-od-dev-skill-guide` 做的结构合规重构(design/ + ADR 拆分),尚未跑 utility test(方法见 skill-guide `references/skill-testing.md`)。「结构合规」(满足 4 硬规范)与「validated」(GREEN 过)独立;本 skill 目前是前者达成、后者待做。
- **维护者常用时区**:UTC+8(GitHub API 返回 UTC,显示前转 +8;换维护者时按实际调整)。
