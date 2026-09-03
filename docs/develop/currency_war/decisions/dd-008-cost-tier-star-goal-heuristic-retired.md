# DD-008:费用档星目标启发式废弃——星目标决策权回归成型档显式要求

- Status: accepted(用户裁定 2026-09-02「废弃这个,以数学证明为准」;编排者落码前清退批执行)
- 取代: ADR-0152 决策第 6 条「费用档星目标(M6)」(旧方案攻略广场统计启发式)

## 决策

删除 `cw_plaza_comps.default_star_goal(cost)`(≤3 费目标 3 星 / ≥4 费目标 2 星)及其生成器模板发射、文档 as-built 声明、测试锁。星目标决策权回归**成型档显式要求**建模:`LevelGoal.star_goals`(COMP_LIBRARY 逐套显式填值)与 `SYSTEM_CARDS[].star_goal`——无显式要求的卡不设默认启发式目标,按成型档需求走,缺什么升什么。

## Why

1. **无数学证明**:规则源于攻略广场 784 篇玩家帖的 3 星达成率统计(0.87/0.58/0.37),属元游戏经验频率,不满足重构准入「新方案能数学证明的为准」;
2. **零运行时影响面**(清查实证):`default_star_goal` 在生产代码中零调用点(已定义、待接线的死函数),废弃无行为变更;
3. **客观频次数据保留**:`star3_by_cost`/`carry_star3_rate` 注释改「客观频次,仅校准对拍用,不作星目标决策输入」——数据不死,只退出决策链。

## Consequences

- `docs/develop/currency_war/strategy/02_comp.md` star_goals 语义同步(成型档显式要求);
- 消费该规则的 skill 文档(`sr-od-currency-war-dev/references/data-collection.md`「星级目标先验」句)待按 skill 反馈流程修订;
- 升星决策缺省行为 = 成型档缺什么升什么,无 blanket 启发式。
