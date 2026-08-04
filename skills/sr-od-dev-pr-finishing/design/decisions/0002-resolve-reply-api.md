# 0002. resolve 走 GraphQL + reply 走 REST(用 REST databaseId)

- **Status**: accepted
- **Date**: 2026-07

## Context
本 skill 要求「每条 thread 最终都 resolve」+「每条都回复」。GitHub 的 thread 操作分散在两套 API,且 gh CLI 无内置 resolve 命令,实操踩过坑:
- **resolve**:REST 无 resolve endpoint;gh CLI 无内置命令。只能 `gh api graphql` 跑 `resolveReviewThread` mutation。
- **reply**(回复某条 review comment):走 REST `pulls/<pr>/comments/<comment_id>/replies`。⚠️ 端点必须带 `pull_number`(漏了报错);`line` 字段可为 null。
- **id 体系不同(最坑)**:`replies` 端点的 `comment_id` 是 **REST 数字 `databaseId`**(从 `pulls/<pr>/comments` 拉),**不是** GraphQL 的 `PRRT_xxx` thread id。混用 → 404。

## Decision Drivers
- **正确性**:用对 id 体系才能跑通(混用直接 404)。
- **最少摩擦**:能用 gh CLI / REST 的不绕 GraphQL(REST replies 比 GraphQL reply mutation 简单)。
- **可发现**:把「两操作两条 API、两套 id」写明,后人不用重新踩。

## Considered Options
1. **全 GraphQL**(resolve + reply 都 mutation):统一,但 reply 走 REST 端点更简单、字段更直观;且 GraphQL reply mutation 更繁琐。
2. **resolve GraphQL + reply REST,用 REST databaseId**(选中):各用最顺手的 API;id 体系写明防混。
3. **等 gh CLI 内置 resolve**:不存在该命令,等不起。

## Decision
选 2:
- **reply** 走 REST `repos/<owner>/<repo>/pulls/<pr>/comments/<comment_id>/replies`,`comment_id` 用 GraphQL reviewThreads query 里 `comments[].databaseId` 的 **REST 数字**(不是 `PRRT_` thread id),端点带 `pull_number`。
- **resolve** 走 GraphQL `resolveReviewThread(input:{threadId:"PRRT_xxx"})`,thread id 用 reviewThreads query 的 `id`(`PRRT_xxx`);反操作 `unresolveReviewThread`。
- 两套 id 各取各的,**不混用**(混了 404)。

## Consequences
- **正向**:两操作各走最简途径;id 体系写明,后人不必重新踩 404。
- **负向**:agent 要记两套 id 分别用在哪;GraphQL mutation 对不熟的人有门槛(但 SKILL.md 给了完整 query,可直接套)。
- **follow-up**:若 GitHub 给 REST 加 resolve endpoint 或 gh CLI 内置命令,改走更简途径。

## Links
- SKILL.md「流程 2(回复)」+「流程 3(resolve)」。
- 踩坑论据:实操踩过 replies 漏 `pull_number`、`line` 为 null、`comment_id` 与 thread id 体系不同致 404。
