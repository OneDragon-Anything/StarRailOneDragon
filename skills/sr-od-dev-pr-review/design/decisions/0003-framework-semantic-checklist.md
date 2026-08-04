# 0003. L1 框架语义固定必查项(防「扫一眼」漏异常路径)

- **Status**: accepted
- **Date**: 2026-08-04(形式化日;决策本身随 skill 创建 ~2026-07)

## Context
框架语义是「代码看着对但运行时崩/死循环/泄漏」的高发点 —— 错了不是 style 问题,是真崩。初轮 review 若只做「扫一眼」表面审,会漏异常路径。实测踩坑:
- #2459 的 CodeRabbit comment 抓到 `after_operation_done` 里 stop_auto_battle 抛异常会跳过基类清理 → 应 try/finally。初轮 review 漏了这条(只做了 L1 表面审),说明框架语义要显式列出来查,不能靠「扫一眼」。
- #2503 删大 `node_max_retry_times=300` 看似回归,查源码发现主路径走 `round_wait`(无界)→ 安全。
- #2388 把「抛异常」改「返回 None」,逐个消费方确认 None-safe(AppRunCard 本就 None-safe)→ 否则只是位移崩溃。

## Decision Drivers
- **抓异常路径**:不只看 happy path,显式查异常/重试/路由语义。
- **不靠记忆**:固定 checklist 防漏(不依赖审查者记得查)。
- **以源码为准**:框架语义以源码为准,PR description 可能省略。

## Considered Options
1. **靠「扫一眼」**:漏异常路径(实测 #2459 漏 try/finally)。
2. **靠 PR description**:description 可能省略触发时机/重试预算。
3. **L1 固定必查项 checklist**(选中):逐条对照源码确认。
4. **穷举所有框架语义**:过度(只查高发点够)。

## Decision
选 3:L1 固定查 5 项框架语义(任一错就运行时崩,逐条对照源码确认):
1. **生命周期钩子 `after_operation_done` / `op_callback`**:success/fail 都触发;若 PR 在此做自定义清理(如 stop_xxx),查异常风险 → 基类调用必须在 `finally` 里(try 包自定义清理,finally 包基类清理),否则 run_record/notify/`APPLICATION_STOP` 等基类清理被跳过。
2. **节点重试预算**:`round_wait` 重置 `node_retry_times`(无界),只有 `round_retry` 消耗、超 `node_max_retry_times`(默认 3)才 FAIL。审「删大 `node_max_retry_times`」时确认主路径走 `round_wait`。
3. **`@operation_node` 装饰器**:只挂元数据、原样返回 func → 可直接调用被装饰方法;节点调度读元数据。
4. **`execute()` 重复调用安全**:每次开头全重置(节点图 + 重试计数 + `handle_init`)。retry 包 `execute` 的模式安全。
5. **节点路由 `node_from(status=...)`**:契约从「抛异常」改「返回 None/默认值」时,逐个消费方确认 None-safe;`ignore_status` + `status` 组合决定路由。

## Consequences
- **正向**:异常路径/重试/路由的高发崩溃被显式抓到;不靠审查者记忆。
- **负向**:5 项对非框架 PR 可能部分不适用(逐条判适用即可);框架语义随版本演进,checklist 要跟。
- **follow-up**:框架语义变化时更新 SKILL.md 的 5 项。

## Links
- SKILL.md §2(L1 框架语义必查项)。
