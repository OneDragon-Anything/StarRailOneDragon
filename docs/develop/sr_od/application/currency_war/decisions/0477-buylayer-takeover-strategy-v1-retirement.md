# ADR-0477 买层接管:strategy_v1 待删桶退役,腾席判据迁 kernel 单一源

> **版本界碑(2026-09-04 ADR 存量 review;统一迁移批史,与 b94e9cfb 互证)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb 删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

## 状态

accepted

## 背景(为什么做)

分包重构(DESIGN v3)把旧 v1 决策栈五文件(cw_plan/cw_evaluate/cw_bundle/cw_line_tribunal/cw_progress_curves)归入 `strategy_v1/` 待删桶(期 5,W722)。此前退役批(ADR-0466/0467/0469)已删 default 栈,v2(decision_v2)是唯一策略载体;v1 栈仅剩一条活生产 import:`decision_v2/strategy.py` 消费 cw_plan 的**腾席判据函数族**与 deploy 全局不变量(ADR-0466 挂账②,蓝图 §3.2 唯一豁免边,包布局守卫白名单单列)。W699 清点确认除此之外 src 全树零生产消费;`cw_plan_replay_audit.py`(tools 桶)零生产消费,唯 plan_fn 依赖 v1。

删除前置(段 0)= 豁免边解耦:判据函数语义保持平移到 kernel(ADR-0466 挂账②原定「腾席链折叠批后删」,与「整桶删除」有时序张力,故先平移后折叠——两批各自小半径、独立验证锚,W699 §4 裁决)。

## 决策

1. **段 0(豁免边解耦)**:腾席判据函数族 + deploy 不变量平移至新模块 `kernel/cw_deploy_seat.py`:
   - 自 cw_plan:`_should_deploy`/`_dep_activates_tier`/`_bench_faction_counts`/`_card_supports_target`/`_bench_sell_value`/`_weakest_bench_idx`/`_pick_deploy_row`/`level_up_gate`/`deploy_legal`/`deployed_name_set`;
   - 自 cw_evaluate:`_close_factions`/`_close_to_next`/`_card_hits_target`;
   - `xp_click_cost` 改 kernel.cw_economy 直引。函数体逐字符语义保持;decision_v2/strategy.py 14 调用点重定向;deploy_bench 同源注释改指新址。
2. **段 1(主线删除)**:strategy_v1 整桶(5 文件+__init__)与 `cw_plan_replay_audit.py` 删除;包布局守卫删 strategy_v1 桶、豁免白名单、tools 成员行(守卫转绿即白名单消亡证明)。
3. **replay 通道保全**:删码不删通道——telemetry recorder 的 decisions.jsonl 写路径不动,历史局离线审计仍可读;仅退役「live vs v1 plan 对拍器」(其可复现性锚 v1 plan,随 v1 失去意义)。
4. **随删测试**:整删 8 个纯钉 v1 符号的测试文件;改钉/删用例其余 import 面;cw_quick 清单同步 8 行。

## 验证

- 段 0 等价性:平移前后同参 fuzz(seed 477,400 局态,17598 对函数输出)逐位一致——比 ADR-0466 挂账的「同 seed sim 决策序列哈希」更强的直接等价证明(函数级而非链级);
- 受影响测试直跑全绿;布局守卫三件绿(桶级边 strategy_v1=0);cw_quick 全绿(数字见 w730 报告);
- scan 快照前后留档:`.debug/temp/currency_war/w730_buylayer/scan_{before,after}.json`(strategy_v1 入边 4→0)。

## Considered Options(段 0 处置裁决)

| 选项 | 裁决 |
|---|---|
| **平移 kernel 语义保持(采)** | 删除批与腾席链折叠批解耦;零行为变化可独立证明;deploy_legal/deployed_name_set 全局不变量单一源得以保留并指明新址 |
| 腾席链折叠先行(把判据逻辑折叠进 v2 再删) | 本批半径暴涨;折叠属行为层重构,与「整目录删除」混做失败归因缝不清(ADR-0466② 仍归腾席折叠批销账) |
| 保留 strategy_v1 仅判据函数 | 违背 DESIGN §2 待删桶定位;留 1200+ 行死码负债 |

## 影响

- 腾席判据单一源 = `kernel/cw_deploy_seat`(deploy_legal 不变量的「一切上场路径必过本守卫」语义随之迁移);ADR-0466 挂账①销账,挂账②转由腾席链折叠批对 `cw_deploy_seat` 折叠销账;
- 买层唯一入口 = `DecisionV2Strategy.decide_prep`(shop.py);旧 plan/evaluate 语义(grep 锁 `test_cw_decisions` v1 段、压缩买/骨架买/束优化等)随 v1 退役,历史见 ADR-0145/0149/0152/0156/0171;
- 遗留(限界面,归后续批):sim/checks/telemetry 面 4 处注释与 3 个 v1-import 测试文件(test_scenario_gen/test_crafted_scenarios/test_telemetry_replay 已做最小 import 改钉,深清理归 W729 残差批)。
