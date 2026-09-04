# ADR-0245 生产遥测接 checks(栈判别+检查子集适配)

## Status

accepted(2026-08-24;用户决策项 1「你来接」;ADR-0242 的生产侧延伸)

## Context

ADR-0242 把异常检查建在 sim 批次上;生产局判读仍靠逐局人工/agent 走视图。实机配置 `strategy_id: line_v2` 解封了关键前提——生产跑的就是 LineStrategy,`BuyCard.reason` 是共享 dataclass,生产 decisions.jsonl 同带 v2 词表标签,检查可直接吃生产账本。但盲跑全检查集不行:ledger 一致性检查依赖 sim 键(生产行没有);default 栈(cw_plan,reason='plan')不辖 r368 冷启动门,盲跑 coldstart 必误报。

## Considered Options

1. 不接:生产判读靠人工视图——局49 类指纹仍靠人眼,与「实机学费回灌」闭环目标矛盾。
2. 全检查集直跑生产:ledger 一致性对生产行全误报(缺 sim.income/spend);与 econ_reconcile 工具链(cw_dev/econ_reconcile_v0~v6)双源对账——重复造轮子。
3. **栈判别+检查子集适配**(选):逐局判栈(strategy_id=='line_v2' 优先;缺失时按开局轮 reason 词表推断:v2 词表∩→v2,{plan}∩→default,零买牌→'?'照跑无害);v2 栈跑 coldstart(违规带 run_id);default 跳过并声明;金对账不跑(归 econ_reconcile 单一源)。

## Decision

选 3。`cw_telemetry checks --recent N` 子命令;锁:栈判别三例(default 跳过/v2 违规检出含 run_id 溯源/词表推断)+ 检查器自身的变异自检锁(测试仓 test_cw_mutation_selftest:monkeypatch 去门 → sim 批次违规必须涌现,基线 0——把审查 316ebbc0 的一次性变异证据固化为 CI 资产)。

## Consequences

- 生产局获得与 sim 批次同源的秒级指纹扫描,局后判读多一道自动网;实测(2026-08-22 五局,全 v2 栈)coldstart 零违规。
- default 栈历史局自动跳过(不误报);strategy_id 空的旧局按词表判,零买牌局判 '?' 照跑(无买=无违规)。
- 新增回灌检查时:生产侧适用性按栈逐一声明(同 coldstart 的 docstring 模式),禁盲加进生产检查集。
