# 0092. select_comp 可得性用理论概率(refresh_prob)非观察(shop_supply)

- **Status**: accepted
- **Date**: 2026-08-11
- **原编号**: D-92

## Context
`select_comp` 用 `shop_supply`(本回合 shop 观察)+ `_shop_history_factor`(历史 shop 观察)判 comp 可得性。用户点破:**商店刷新独立(每轮独立)→ 观察(本回合/历史刷没刷到)对未来无预测力**,该用理论概率表。

## Decision Drivers
- 刷新独立 → 观察无预测力
- 理论概率表(D-91 REFRESH_PROB)权威可用
- comp 成型受最稀卡限制

## Considered Options
1. 保留 shop_supply 只删 shop_history(仍单回合短视,没解决根因)
2. acquirability 用期望刷新次数(考虑副本数;A4.2 副本数未全核,过早)
3. acquirability = 核心角色最低 `refresh_prob(level, cost)`,理论基于 REFRESH_PROB(选中)

## Decision
`select_comp` 的 `shop_supply` + `_shop_history_factor` 两观察因子 → 合并成 `acquirability_factor(comp.core_chars, state.level) = min(refresh_prob(level, cost) for 核心角色)`(阵容受最稀卡限制),理论基于 REFRESH_PROB。用法范围同 shop_supply(`[0,1]`,`0.15 + 0.85*`)。drought 检测**保留** `shop_supply`(判本回合 shop 有无 target 卡 → drought 计数,观察语义合理)。

## Consequences
- 正向:可得性判断有理论依据,不再随观察抖动;清 D-6 carryover(shop_supply 冗余)。
- 负向:未考虑副本数(`expected_refreshes` 留 A4.3 精化)。
- 边界:drought 用观察(连续无目标计数)语义不同,保留。

## Links
- `· docs/develop/currency_war/strategy/03_comp_planning.md`(select_comp)
- 关联 D-NN:D-6(shop_supply carryover 解)、D-91(REFRESH_PROB 数据地基)、D-93(副本数 9)
