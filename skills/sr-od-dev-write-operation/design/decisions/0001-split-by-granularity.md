# 0001. 按粒度拆分玩法自动化开发 skill(op / app / 玩法三层)

- **Status**: accepted
- **Date**: 2026-08-04

## Context

`sr-od-dev-gameplay-automation` 原本是"从零开发新玩法自动化"的唯一 skill,装了:全程 pipeline(阶段 0-9)+ op / app mechanics 一行带过 + 一大块 op 作者方法论(调试纪律 / 预料外画面 / 密集日志 / 多样本核实 / 重复手动建op / 证据纪律)。

两个问题:

1. **mechanics 缺口**:op / app 怎么实际写(节点图 / round 结果 / `round_by_*` 选型 / `handle_init` / factory / config / GUI)从未教,agent 只能逆向 `sim_universe` 学。实际开发中反复出现"逆向挖框架 API"的浪费 —— `controller.btn_tap`、现成可复用 op(如 `GuideChooseTab`)、`round_by_find_area` 只检测不点击、自环 `@node_from` 死循环、`pre_delay` / active_window 间隙、mouse_move + click 缓解 bug#1 —— 全是 mechanics 缺失导致的试错,不是策略问题。

2. **触发错位**:gameplay-automation 触发条件是"从零做新玩法",明确排除"小改现有自动化"。但最高频的日常是**给已有 app 写 / 改 / 修单个 op**,这些任务进不去 gameplay-automation,也就拿不到锁在里面的 op 作者方法论 —— 完整性缺口。

## Decision Drivers

- **触发可达性**:高频任务(写 / 改 / 修单个 op)必须能触发到它需要的方法论。
- **单一源 / 不重复**:同一套 op 粒度规范不能散在多个 skill 双源。
- **token 效率 / progressive disclosure**:别一个巨型 skill 在一行 op 修改时全量注入(lost-in-the-middle)。
- **YAGNI**:不过度拆分,每层必须自洽完整才有存在价值。

## Considered Options

### A. 按粒度拆三层(本决策)

`sr-od-dev-write-operation`(op 粒度,高频,完整 op 作者参考)+ `sr-od-dev-application`(app 粒度,产品化)+ `sr-od-dev-gameplay-automation`(瘦成纯玩法粒度 pipeline)。每层自洽完整,高层引用低层。

- ✅ 触发可达:写 / 改 / 修 op 进 write-operation 拿到完整 op 参考。
- ✅ 单一源:op 粒度规范随 op 走(迁入 write-operation),gameplay-automation 引用。
- ✅ token:每个 skill 聚焦、按粒度注入。
- ❌ 需维护跨 skill 引用(节点图机制 write-operation 讲一次、application 引用);需迁移 gameplay-automation 既有内容(动共享 skill,改前确认)。

### B. 一个大 skill(把 mechanics 塞进 gameplay-automation + 扩触发)

- ✅ 无跨 skill 引用、无迁移。
- ❌ 触发两难:扩触发 → 一行 op 修改也全量注入巨型 skill(lost-in-the-middle);不扩 → 写改修 op 仍拿不到。
- ❌ 单 skill 膨胀到 pipeline + op mechanics + app mechanics 全装,违反 progressive disclosure。

### C. 折进现有 skill、不新建

= B 的变体,同样触发两难 + skill 膨胀。

### D. operation / application 各自纯 mechanics,规范全留 gameplay-automation

- ❌ 纯 mechanics 的 operation skill 不完整(写 op 要写"对"离不开 op 粒度规范);且规范留 gameplay-automation → 写改修 op 够不着(回到 Context 问题 2)。

## Decision

选 **A**:按粒度拆三层,**每层自洽完整**(mechanics + 该粒度规范织在一起),高层 pipeline 引用低层。op 粒度规范从 gameplay-automation **迁入** write-operation 作单一源。application 与 operation 仅共享节点图机制(operation 讲一次、application 引用),不重复。

## Consequences

- **正向**:最高频任务(写 / 改 / 修 op)拿到完整 op 作者参考;每层 skill 聚焦、token 高效;op 粒度规范单一源。
- **代价**:跨 skill 引用需维护(节点图机制一处写、一处引用);动 gameplay-automation(共享 skill,改前确认)。
- **必须 follow-up**:
  1. MVP 后把 gameplay-automation 迁出节替换为指针(防双源);
  2. gameplay-automation 全案瘦身(阶段 5/6 收窄成"策略 + 引用");
  3. 建 `sr-od-dev-application`。
- **推翻它会碎什么**:若退回单 skill(B/C),写改修 op 重回"够不着方法论 + mechanics 靠逆向";若 operation 退回纯 mechanics(D),写 op 不完整。「三层粒度 + 每层自洽完整」是本设计的关键不变量。

## Links

- 相关 design 章节:`../overview.md`(范围 IN/OUT、构成、phasing)
- 相关 skill:`sr-od-dev-gameplay-automation`(将瘦身)、`sr-od-dev-application`(待建)、`od-dev-screen-onboarding`(建档前置引用)
