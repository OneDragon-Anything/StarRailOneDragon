# 0108 策略 review 修复批次3(shop_faction_seen 死数据 / difficulty_phase per-plane bug / target_committed *9)

> ✅ 注:文末「仍留」清单中 #6 牌池 acq 已由 [ADR-0109](0109-pool-copies-canonical-27-9.md)/[ADR-0110](0110-acquirability-pool-aware.md) 落地、SELL_VALUE cost-based 已由 [ADR-0111](0111-sell-refund-cost-based.md)/[ADR-0121](0121-sell-refund-fee-cost-dependent.md) 落地(2026-08-12);其余次优项如需处理先核代码现状。

Status: accepted
Date: 2026-08-12

## Context
review 次优剩余里 3 条独立小修(不依赖 #6 牌池 acq,可单独做)。

## Decision Drivers
- 死数据该删(留尸体误导后人以为在用)。
- per-plane 语义 bug 会误判游戏阶段。

## Considered Options / Decisions

### 1. shop_faction_seen 死数据删除
`session.shop_faction_seen`(跨回合 shop 阵营历史累积,default_strategy 累积 + 透传 make_score_context)
**无任何评分函数读取** —— ADR-0092 把 shop 可得性从「观察法」改成「理论 REFRESH_PROB」后,这套累积成尸体。
删:ScoreContext 字段 + make_score_context 参数 + session 字段 + default_strategy 累积/透传。
- 备选(留):否 —— 留着误导(读代码以为 shop 历史在用,实则在 #6 牌池 acq 才真要读 shop/牌池)。

### 2. `_difficulty_phase_factor` per-plane bug
原 `early = state.round_num <= 3`。但 `state.round_num` 是**位面内 1-6**(cw_state 注释确认),
每位面循环 → plane2/3 的 r1-3 被误判「早期」(实为 elapsed 7-9 / 13-15,中后期)。
改:`early = (round_num + (plane-1)*6) <= 3 or gold < 30`(全局 elapsed,与 `_elapsed_rounds`/maybe_pivot
同公式)。「穷」仍由 `gold<30` 全局判。「早期」现仅 plane1 r1-3(真早期)。
- 影响:plane2/3 不再误偏 easy+early_power comp(那时通常已 commit,difficulty 因子该让位)。

### 3. `target_committed` 全局轮次 `*9 → *6`
原 `(plane-1)*9 + round_num`。位面是 6 关非 9(`_elapsed_rounds`/maybe_pivot signal2 都用 `*6`)。
对 COMMIT_ROUND=2 当前不改变行为(plane2+ 任一轮两种公式都 ≥2),但语义错且 COMMIT_ROUND 调高即暴露。
改 `*6` 与全局 elapsed 单一公式一致。

## Consequences
- shop_faction_seen 全清(4 处);make_score_context 签名简化(无测试传该参)。
- difficulty_phase 仅真早期激活;target_committed 轮次公式统一 *6。
- 296 测试过。
- **仍留**:#6 牌池 acq(用户根因,大改)+ 次优剩余(SELL_VALUE cost-based / board 梯度 / comp_viability obs_weight
  分母 / star_achievement 加权 / COMMIT_ROUND 门槛 / maybe_pivot raw vs 乘法 / formation_cost 衰减 / 注释过期)。
