# 0272 sim 牌池 4/5 费去截断(批④ F1,实机已裁决;r411)

- 状态: accepted
- 日期: 2026-08-24
- 来源: sim 压测批④ F1(实机裁决);worker 任务「六件套批 B 件2」

## 背景

`cw_sim._Pool(max_cost=3)` 硬截断:4/5 费角色不进池,抽取时
`costs = [c for c in dist if c <= max_cost ...]` 把 REFRESH_PROB 的
4/5 费概率质量**静默重归一化**——lv9 实际 4 费概率 .30,截断后归零、
质量摊给 1-3 费(低费虚高频)。14 个 4 费角色不进池,供给结构失真。

表源权威性:`cw_shop_odds.REFRESH_PROB` = 游戏内「商店刷新概率」表
实机 OCR(D-91,Lv1-10 × 1-5 费),**无位面维度**——概率只随等级变
(依据注释见 cw_shop_odds.py 模块头)。

## 决策

1. **去截断**:`_Pool` 构造不再接受/应用任何费用上限,全角色
   (1-5 费)按 `POOL_COPIES_PER_CARD`(27/27/9/9/9)入池;
   `draw_shop` 费用档直接按 REFRESH_PROB 等级行采样;
2. **5 费可达性裁决(入池)**:P1 等级可达 9(sim 升级循环
   `while st.level < 9`),REFRESH_PROB lv7/8/9 均有 5 费概率
   (.01/.03/.10)→ 5 费 P1 可达,**一并入池**。量级如实记:lv9
   单槽 5 费 .10、4 费 .30(5 费是稀有供给,不是零供给);
3. **检查项 `sim_pool_no_cost_truncation`** 入 `cw_sim_checks`
   (纯 dict 入参,不 import cw_sim):池 copies 缺 4 费或 5 费角色
   即违规;`simulate_p1` 池构造后**硬断言**(不变式,违规 raise),
   `simulate_p1_batch` 报告 `checks_violations` 同步披露。

## 回归验证(n=60 配对,seed 0-59,pool='snapshot' e19afdfa,worktree 干净树 @59595f3f + 件1(ADR-0271)作为基线)

| 指标 | 基线(件1 后) | 新(+去截断) | Δ |
|---|---|---|---|
| hp_ge_60 | 0.067 | 0.067 | 0 |
| avg_final_hp | 26.00 | 26.43 | +0.4 |
| battle_losses_le_2 | 0.050 | 0.083 | +0.033 |
| engines2_by_r6 | 0.033 | 0.033 | 0 |
| recipe5_by_r6 | 0.450 | 0.433 | -0.017 |
| avg_refreshes | 1.77 | 2.03 | +0.26 |

聚合量级温和(4 费买入挤占低费预算、5 费稀有),供给结构修正的
意义在**分布级**(4 费核心件的可见性/买通道行为),不在均值。
附带:`deploy_fills_cap` 涌现 1 局违规(基线 0)——4 费件入池后
围栏拦截形态在 sim 可见,属修正暴露非引入(检查项即为此设计的
常态化防线)。

## Considered Options

- **A. 只放 4 费、5 费继续截断**:拒绝——P1 lv9 可达且 .10 非零,
  截断即重蹈「概率质量静默重归一化」;
- **B. 全费入池 + 硬断言检查项(选定)**:与 REFRESH_PROB 表自然
  对齐(表本身就是按等级给 1-5 费联合分布),去截断后无须任何
  补偿参数;硬断言防回归(重建 max_cost 类改动当场 raise);
- **C. 按位面分池**:拒绝——表源无位面维度(OCR 表只有等级行),
  造位面维度 = 无依据建模。

## 影响

- `cw_sim.py`:`_Pool` 去 max_cost;simulate_p1 池构造后硬断言;
  batch 报告加 `sim_pool_no_cost_truncation` 披露;
- `cw_sim_checks.py`:`check_sim_pool_no_cost_truncation`;
- 测试:`test_cw_r411_pool_no_cost_truncation.py`(5 锁:全费入池/
  lv5 出 4 费/lv9 出 5 费/检查双向);
- 依赖旧截断口径的 sim 批次结论(涉及 4/5 费供给、D牌期望对拍)
  需按新池重验——rng 流随池内容变化,同 seed 不同局(预期内,
  与 ADR-0268 v1→v2 同类声明)。
