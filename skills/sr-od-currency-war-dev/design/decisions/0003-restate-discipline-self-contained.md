# ADR-0003 通用纪律自包含重述,不引个人本地文件

## Status

accepted(2026-08-22)

## Context

「改策略前读三份文档/设计先行/验证=分布非叙述」等纪律已在项目个人本地入口文件(AGENTS.local.md,不入 git)有成文。skill 硬规范禁止引用未提交内容(个人本地/memory/gitignored)——引用闭包外的状态在别人机器/clean checkout 上不存在。

## Considered Options

1. 引用个人本地文件:违反规范 3 硬门。
2. 只留在个人本地,skill 不写:个人本地是 always-on,但跨人/CI 场景失效,且 skill 的 checklist 依赖这些判据才完整。
3. **skill 内自包含重述**(选):以 CW 操作语境重写关键判据(三份文档点名路径、sim 先行、影响面预判),与个人本地的通用版各自演进;重复是接受的成本,失效是更大的成本。

## Decision

选 3。重述时具体化到 CW 路径(如 user_playstyle 全文路径),不写「见某 local 文件」。

## Consequences

- 同一纪律两处表述可能漂移:个人本地管「任何玩法」,本 skill 管 CW 细节——语义冲突时以 skill 的 CW 具体版为准并在两处同步修正。
