# ADR-0223 破息窗 LevelUp 总成本门

## Status

accepted(2026-08-22;r354)

## Context

局43 实锤:r8 备战金 28,LevelUp 提案按单击价(4)过门 → 执行侧循环点经验 12 击金尽停 → 等级没升(经验槽差太多)+ 金全灭 → r9 boss 裸奔 3 金买 0,-36 惨败。半吊子点经验 = 最差结局(钱花了等级没变战力没买)。

## Decision Drivers

- 执行侧语义是「循环点至 level+1 或金尽」,策略侧提案时不知总需求
- clicks_to_next_level(xp_progress 实读)已存在但 LevelUp 门没用它

## Considered Options

1. 执行侧加「剩余金不够升完就停手」:执行层不知策略意图(有时就该点到哪算哪),职责错位
2. **策略侧总成本门**(选):提案前算 clicks×click_cost,升不完不提案、金留给买牌;预算扣减对齐总成本
3. 凑不够就全花掉保底几击:局43 已证是最差结局

## Decision

选 2。连带发现并修正三个旧锁(r307/r308/r293)的语义:它们的「不买」断言实为旧 LevelUp 分食预算的副作用,非地板真语义——地板本意是保息,破息线金无息可保,买板面件堆深更优。锁更新:test_cw_r354_levelup_total_cost.py。
