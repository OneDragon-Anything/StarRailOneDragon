# ADR-0172 线组合管理器 v0(承诺前半程;21 号)

## Status

Accepted(2026-08-16;消费端切流/事件统一入口[棱彩/环境/巨星三口]/T1 涌现对拍为后续——首口建议「boss 克线开局压 commit」)

## Context

21 号诊断:目标生命周期两半,后半已被 20 号收编,前半仍是手调族(optionality_score/α(t)/top-N/0.4 阈值/硬绑表 ×1.5——同一物种五种手工近似)。四种输法实证:错线 commit(boss 日程只是评分项不构成否决——15 号 matchup 已能开局判克线)/被动等待(池枯竭要等 drought 5 轮——16 号实时可判)/pivot 无活口(optionality 只加分不构成持有规则)/版本脆性。零件已齐(15/16/17/19/20/char_routes),只缺统一消费端。

## Decision Drivers

1. 与 20 号分工清晰:那边审已承诺的线(判决),这边管线集合构成与资源分配(配置);交棒协议让边界无重叠。
2. spread 防线写进设计(最大历史风险 M 系列):板面/储备严格分离——板面永远下当前最优阵(不动),组合只活在 bench 与买入侧。

## Considered Options

- **继续手调族**:拒绝——21 号考古论证与 20 号同源(同一物种)。
- **全案(事件统一入口 M 级)**:分阶段;core 先行。
- **core 纯函数**(采纳):Line/五路更新/持有价值/集中门/交棒。

## Decision

1. 新增 `cw_line_portfolio.py`:
   - `Line`:候选线(core_assets/进出场成本[17]/log-odds 后验/判别日程余量);
   - 五路证据一套更新(数学与 20 号同源对数累加,但从 t=0 对**全部线**跑):`boss_prior`(15 matchup 开局先验——克线开局即压,不会被过渡牌堆高骗过阈值)/`pickup_shock`(棱彩拾取,硬绑表=依赖度 1 特例)/`pool_feasibility`(16+20 LR——池枯实时压,不等 drought)/`battle_evidence`(19 gap)/`discriminators_consumed`;
   - `hold_value`:H(u) = Σw_l·V_l + 共享红利 − 容量成本(容量逼紧 → 持有更贵——「牺牲哪条线的期权」静态估值表达不了的边际);
   - `concentration_gate` 三条件(后验分离 ≥阈值/**判别日程耗尽强制集中**[=现状行为,损失封顶]/容量成本>组合增益),门限由 17×18 定价不拍常数;**交棒协议**(`handoff_hypothesis`):集中 = 注册进 20 号登记簿,本层静默零双重管理。
2. 测试 6 条(T2/T3 判据核心):boss 克线方向性/池枯压线/拾取冲击(依赖线上跳)/集中门三路径/判别耗尽强制集中/交棒+持有价值容量边际。
3. 集中后行为 = 现状 commit 接缝零改(eval/prefilter 切 target);事件三口迁移(棱彩/环境/巨星)为后续 M 级。

## Consequences

- T1(集中时点 vs plaza labels 涌现对拍)与 T5(影子重放 diff)待切流窗口;首口建议「boss 克线开局压 commit」(最干净、证据最强)。
- 与 10 号 MPC 边界:本层作 MPC 搜索域约束与初始解供给(接口预留)。
- 提案原文删档;决策单一源移本 ADR。
