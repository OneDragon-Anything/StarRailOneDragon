# ADR-0173: boss 前花尽三豁免(骨架买兜底 boss 场解锁)

## Status

Accepted(2026-08-17,r7 e133f9f6 + r9 修正批)

## Context

M46/M48 3/3 局 P1-9 boss 濒死(掉 19-21 血,全灭于 P1-9/P2-1 边界):boss 备战期 gold 60-73 闲置,
RefreshShop 刷 8-10 次一张不买。当时归因「牌架无 target 卡」——后被 r7 review 证伪:**真根因是
P0-A shop 门 bug**(恒空);但 boss 帧行为审计(遮蔽排除后)仍确认骨架买兜底被 plane==1 +
gold<20 + fp<COMMIT_FRAC 三门结构性拦死(boss 帧全不满足)。

## Decision Drivers

- ADR-0128(攻略复查 #4「boss 关前把钱花完」)在执行层的落地缺口
- HP 是通关硬约束,息随时可再攒;boss 是位面末硬节点,板强=保血

## Considered Options

1. 只修 shop 门不动骨架买——boss 帧 best 可能是纯 RefreshShop(D 找质量),买不到 target 时金
   继续泄在刷新上;不解决「带 55-67 金空手出战」。
2. 骨架买兜底全域放开——P2 息引擎重建期(ADR-0148)吃骨架买会打断攒息节奏;spread 风险无位面门。
3. **boss 场定向豁免(选)**:`_boss_spend = node_type=='boss' and form<1.0` → plane/gold/fp 三门
   该场景豁免;金硬门(cost≤gold)保留防幽灵购买;DeployMove-only best 同放行(shop.py 两阶段
   不执行 deploy 就 break 会饿死骨架)。

## Decision

选 3。配套:node_type 经 `session.last_node_type` 携带(shop 开态被遮恒 None 的结构修复,
cw_evaluate 两处死码同治)。

## Consequences

- boss 帧「确定战力买上」恢复(金花板 > 闲置挨打);M51/M52 连续过 P1-9 验证。
- 骨架买的 spread 守卫/配对纪律不变(豁免的只是进入门,不是候选纪律)。
- 依赖 last_node_type 携带链正确(Director shop 关态写 / shop.py 拷入)。
