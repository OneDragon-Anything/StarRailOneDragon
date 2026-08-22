# ADR-0001 本仓 skills/ + sr-od- 前缀(不进公共仓)

## Status

accepted(2026-08-22)

## Context

按仓库约定,公共 skill 仓放跨项目通用(`od-`/`od-dev-` 前缀,SR/ZZZ 共用);星铁独有、跨项目不成立的才进本仓 `skills/`(`sr-od-` 前缀,提交),junction 挂载到工具的 skill 目录。CW 开发手册的内容(MCP 工具链、docs/*/currency_war/ 结构、cw_sim/telemetry、残局画面)全部绑定本项目。

## Considered Options

1. 公共仓 `od-dev-*` 新篇:内容项目专属,泛化会掏空实义——违反公共 skill 泛化约束(不提项目专属基础设施)。
2. 只写在 AGENTS.local:always-on 占上下文,且个人本地不跨人共享,团队/CI 场景失效。
3. **本仓 `skills/sr-od-currency-war-dev/`**(选):跟仓库走、入 git、按需触发;公共仓泛化约束由本仓约定天然满足。

## Decision

选 3。挂载 = junction 到 `.dsh/skills/`(`.dsh/*` 已 gitignore)。

## Consequences

- 未来 ZZZ 同类需求各建各的,通用骨架沉淀回公共 skill 而非从本 skill 抽。
- 仓内约定「SR 专属 skill 目前无」自此失效,需同步更新约定文本。
