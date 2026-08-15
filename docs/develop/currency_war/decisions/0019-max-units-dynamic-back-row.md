# 0019. 团队规模上限 = level + 财富宝钻/诅咒;后排槽位非固定 6

> ✅ 注([ADR-0120](0120-deploy-center-drag-unified.md),2026-08-13):Consequences 所记「>6 漏检(D-50 gap)」已缓解 —— `DragCwChar._slot_center` 支持调用方传 back_centers、`DeployBench._row_centers` 读全部 后排-N area(不硬编码 6);>6 实际槽位坐标仍待财富宝钻局 live 验。

- **Status**: accepted
- **Date**: 2026-08-09
- **原编号**: D-19

## Context
deploy 槽位原按"前 4 后 6"硬编码。但财富宝钻(装备,无论是否穿戴)团队规模上限 +1,诅咒·宝石剑泽尔里奇 -1。用户确认前排固定、后排可变;实测见过后排 7。投资环境/投资策略数据核实无加位机制。

## Decision Drivers
- 财富宝钻/诅咒动态改 cap,硬编码 6 会错
- 投资环境/投资策略无加位机制(数据核实)
- deploy 须按运行时实测槽位部署

## Considered Options
1. 硬编码 6(错,财富宝钻 +1 实测见过后排 7)
2. 运行时实测槽位数(选中)
3. 静态表(无,随装备动态)

## Decision
deploy 槽位数 = 前排固定 4 + 后排基准 6,但**团队规模上限可被财富宝钻 +1 / 诅咒 -1**。`deploy_bench` 须按运行时实测槽位数部署(非硬编码)。cap = level(无钻石/宝钻/诅咒时)。

## Consequences
- 正向:正确支持动态 cap;deploy 不因装备错位。
- 负向/边界:运行时槽位 CV 检测(后排 avatar 位置)未做 → 当前后排 count=6 硬编码覆盖 6 内(主流场景),>6 漏检(D-50 gap)。
- 边界:前排恒 4(团队规模前排固定,不动态)。

## Links
- `· docs/game/gameplay/currency_war.md`(max_units)
- 关联 D-NN:D-50(后排 >6 适配 gap)、D-53(cap=level 实测核正)
