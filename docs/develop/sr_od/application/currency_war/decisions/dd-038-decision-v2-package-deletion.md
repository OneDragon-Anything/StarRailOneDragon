# dd-038 decision/ 整包删除 + mandate_v1 单核直替（回溯建档）

> 回溯 ADR：决策发生于 2026-09-04 09:59 用户裁定，commit b94e9cfb（2026-09-04 13:55）执行；本件 2026-09-04 由 strategy-docs 修复批回溯建档（对抗审查发现 02 篇引用 dd-038 但 ADR 缺档）。

## Status

accepted（2026-09-04，用户裁定）

## 背景

strategies 统一迁移检查点②。设计期曾以「decision/cw4 与 decision_v2 并存跑三臂 A/B、过线 = 删除旧包触发门」为过渡方案；用户裁定（2026-09-04 09:59）：删 decision_v2，不再被旧栈影响——过渡方案终结，直接收敛到单一核。

## 决策

1. **decision/ 整包删除（42 文件）**：decision_v2 十九模块（allocator/arbiter/candidates/director_v2/discipline/ev/filters/handoff/phase/posture/posture_release/remediation/scoring/series_adapter 等）+ ①期 shim + decision_v2 注册壳 + DecideAdapter 离线链 + sim 侧 v2 死面（checks/decision_v2 六项、w300 探针、segments 四件、simulate_p2_ab 双臂、ab_core_swap 基线臂全套）+ v3_hoard 写端（读端零）。
2. **单核 = mandate_v1**（`strategies/impl/mandate_v1/`，生产注册壳 `strategies/mandate_v1_strategy.py`）；**注册面为封闭集 {mandate_v1}**（config 值域同步收缩；`strategies/impl/cw_strategy_manager.py` 强制注册 mandate_v1 为唯一活策略核）。
3. 九族随删语义入档（四层仲裁/DP 姿态核/危机金出口/terminal_release/停刷门/remediation/allocator/handoff/基线臂——历史 A/B 报告归档史实）；血预算/危机带判据 kernel 下沉件单一源；策略变更验证方式 = **sim 侧代码版本对照**，A/B 对照无裁决权。

## Considered Options

- 保留 decision_v2 走三臂 A/B 过线再删（原过渡方案）——用户裁定弃：旧栈继续影响迭代，验证权归数学证明与预注册判据，不归 A/B 对照。
- 整包删除 + 单核直替（采纳）——语义存活部分（血预算停升级门、危机带让位等）已由 mandate_v1/kernel 下沉件承接（dd-034 候选③等）。

## 影响

- src 内 decision/ 引用归零（decision_assembly 除外，为假阳性）；注册面封闭集 {mandate_v1}。
- 验收（b94e9cfb）：L1=2192 过（唯一红 w614 裁决内）、契约锁/单臂自配对/零漂移门全绿、ruff 净。
- 关联文档：[02_mandate_layer.md](../strategy-docs/02_mandate_layer.md) §7（落地方式现行态）、04 §7 #8（掉血三臂随删退役）。
