# ADR-0404 Δ池 boss 桶键改净星深(v10 重生成)

- 日期:2026-09-03
- 状态:accepted
- 谱系:ADR-0403 已知边界缺口②的修复落地(其 Considered Options
  「键改净星深当场做」明确留给池重生成批);ADR-0399 star_depth
  口径同源;W232 C 项(末窗星级定向)前置链第一步
- 任务:W240

## 背景

ADR-0403 实证(W238,commit 511627b6 单帧锁
`test_merge_reduces_board_sum_direction_gap` 钉死):Δ池 boss 桶键
= Σboard(场上件数),`_merge_bench` 3合1 消耗场上副本 → 件数
3→1(Σboard −2/次)→ 键落更浅桶,而浅桶期望伤害更大(标定桶 12
30.35 > 桶 15 17.5)→ sim 判「升星→boss 伤害↑」,与机制 [27]
(星级↑=战力↑=伤害↓)方向相反。默认策略 sim 合并 0 次时潜伏,
W232 产星通道开臂后(merges 0.13→0.38)被咬。

## 决策(键口径论证)

1. **boss 桶键 Σboard → 净星深 = 上场件 Σ(star−1)**,与
   ADR-0399 `HandoffSnapshot` 的 star_sum−deployed_n、
   `cw_sim.p2_form_key` 的 star_depth **同源口径**(纯 state 可算、
   生产 decisions deployed/sim GameState/离线回放三面同式),单一源
   = `cw_sim.deployed_star_depth`(replay dict 行口径共源
   `_star_depth_from_rows`,池侧经 `cw_delta_pool_gen._star_depth_of`
   引用,防双公式)。候选否决:Σ(star) 系(Σboard+Σ(star−1) /
   star_sum 全量)在 3合1 下 3s→s+1 变号恒负(1−2s<0),方向仍反
   ——净星深是 1★ 合并方向为正的唯一同源口径。
   **方向性质**:1★→2★ 合并(场上 3 副本)键 0→+1 单调不减 ⇒
   桶 `min(sd//3,5)*3` 不落浅桶 ⇒ sim 判升星后 boss 期望伤害不升
   (同桶同值);买 bench 副本键不动(买件不再扰动 boss 伤害估计)。
   已知边界:2★→3★ 合并键 −1(3→2),仅当键恰为 3 的倍数时跨桶
   ——高级合并语料零样本,攒厚后复验。
2. **只改 boss 桶**(最小面):battle(rung)/encounter/reward/
   supply(Σboard)桶键全部不动;`_deployable_depth` 语义不变,
   辖域收窄为 encounter/reward/supply+观测面。
3. **v10 重生成**:`_SAMPLER_VERSION` 8→10(⚠️ 版本号勘误:快照
   note 链自 W109 批起与常量错位 +1——ADR-0362 在 note 链记 v9、
   常量为 8;自 v10 起两链对齐,故跳 9 直上 10)。数据源不变
   (生产 replay 49+ 行 plane=1 boss 差分,键投影变),指纹
   重算:b0f13268915db647。
4. **W238 常数表重标定**(registry):P1 boss 语料净星深**全落
   桶 0**(n=28 未删失/删失 21,均值 −27.57)——旧 Σboard 桶
   9/12/15 的「条件性」系键口径伪影(升星减件使强板落浅桶、浅桶
   均值被强板样本抬升,即缺口②的语料侧成因)。新表
   `handoff_boss_e_damage = {0: 27.57}`、default 27.57(≈旧全池
   fallback 27.33,交叉自洽)。标定脚本
   `.debug/temp/w240_calibrate_boss_star.py`。
5. **消费端对齐**(grep 全量核过):①`cw_sim.simulate_p1` boss
   采样键;②`cw_sim._pool_from_replay` boss 分桶;③
   `cw_delta_pool_gen.build_pool` boss 分桶;④
   `decision_v2/handoff.boss_projected_hp` 档键;⑤registry W238
   块;⑥测试锁(w238 8 锁/w50/r409/adr0292/adr0293 hash)。

## Considered Options(取舍)

- **键改 Σ(star) 系(任务书候选「Σ(star)+件数」)**:3合1 下
  变号 1−2s 恒负(s=1 即 −1),方向冲突不修反固——否。
- **保留 Σboard + 运行时补偿项**:在消费端对升星局加修正=第二套
  分桶逻辑,与「不建第二套分桶」防线冲突——否。
- **battle/encounter 一并改键**:battle 已是 rung 键、encounter
  语料不足(批⑬ F1),超最小面——否。

## 已知边界

- **star_depth 条件性当前语料不可辨**(全落桶 0):常数表实为
  无条件期望;深桶(净星深≥3)零样本,语料攒厚后复验桶间单调。
- 删失剔除存活偏差(ADR-0307 口径代价面)沿用 ADR-0403 声明。
- 锚登记(ANCHOR_REGISTRY_N300 等)为 drift 披露制,指纹前移
  属预期(cw_sim_checks 侧无需换锚;跨池对照走导出 JSON 重放)。

## 验证

- 方向锁(替代旧 `test_merge_reduces_board_sum_direction_gap`):
  ①`test_merge_star_depth_never_shallower`(3合1 后净星深与桶
  均不减,机制面);②`test_v10_pool_boss_buckets_direction`
  (v10 池 boss plane=1 深桶均值 ≤ 浅桶;键域 ⊆ {0,3,…,15};
  当前单桶非空)。
- 常数表锁(w238 ①:键域 {0}/正值/default)、公式锁重构
  (表内桶 0 vs 表外桶走 default,临时 registry 区分两路)。
- 版本锁:adr0292/r409 `_SAMPLER_VERSION == 10` + 快照自洽;
  registry hash 重锁(test_cw_adr0293 →
  29814027b7b96c1bb9a40b5e1859a9869faa3b31b667bac4501bc90e5d15d718)。
- ruff + 直接影响面 94 测通过 + 全量 pytest 0 failed。

## 影响

- `cw_sim.py`(deployed_star_depth/_star_depth_from_rows 单一源、
  _pool_from_replay boss 分桶、simulate_p1 boss 采样键、
  _SAMPLER_VERSION v10、live_delta_for/_deployable_depth 辖域
  docstring)、`cw_delta_pool_gen.py`(boss 分桶+note 链 v10+
  版本号勘误)、`cw_delta_pool_data.py`(v10 快照重生成)、
  `decision_v2/handoff.py`(boss_projected_hp 档键)、
  `decision_v2/registry.py`(常数表重标定)。
- as-built:strategy/03 末窗承接门段、09 §3.1 档键表述;三同步
  代码注释引 ADR-0404。
- W232 C 项(末窗星级定向)前置解除,可进 C 项批。
