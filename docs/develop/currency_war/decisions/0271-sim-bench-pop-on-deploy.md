# 0271 sim bench pop 语义修正:上阵即弹出(批⑦ F1;ADR-0219 第四次命中根治;r410)

- 状态: accepted
- 日期: 2026-08-24
- 来源: sim 压测批⑦ F1;worker 任务「六件套批 B 件1」(原任务编号 ADR-0270,因同批 worker N 已占 0269/0270 顺延)

## 背景

sim 的 deployed 代理(r390)每轮在决策前调
`cw_deploy_logic.select_deployments` 选人,但落地是
`st.deployed = [st.bench[i] ...]` **切片不弹出**,且每轮从零重算、
`deployed_cids=set()`/`deployed_fac=dict(st.board)`(恒空)——生产语义
(`cw_state.simulate`/`mutate_bench_deployed` 的 DeployMove)是
**bench.pop → deployed.append(跨轮累积)→ board[faction]+=1**。

失真量级(批⑦ 实证):94.6% 轮 bench≥9 虚高、极大 25——所有席位门
(`_P2_PRECACHE_MAX_BENCH`/破息窗/`bench_is_full`)在 sim 读假数据,
**席位/容量/卖出类 sim 结论全压在失真上**。这是 ADR-0219「新字段查
三消费面:策略/遥测/sim 代理」纪律的第四次命中(sim 代理与生产执行
语义错位,曾因 bench 计数≠上阵得出 1.8 倍增益伪影)。

## 决策

1. **上阵即 pop**(降序 pop 保索引)——`deployed` 跨轮累积(生产
   跟踪态,无下场机制则单调不减);
2. `select_deployments` 吃真实上下文:`deployed_cids`(已上场名单,
   同名去重门/5.1.7 生效)、`deployed_fac`(factions+flows 口径)、
   `board`(主阵营聚合)、`cap=st.max_units()` 语义与生产 op 一致;
3. `st.board` 由 deployed 主阵营聚合重建(`_board_counts_of`,生产
   DeployMove 口径;与判读用 `_board_factions_of` 的 flows 并计口径
   分立);line_strategy 的 board 消费点(recipe 门/在场阵营集合/
   成对判定)从恒空 dict 变为真值——**这本身是被修正掩盖的决策分叉**;
4. 账本 `state.board` 与 outcomes `board_before` 从恒空 dict 改填真值
   (rounds/economy 视图板面此前恒缺)。

## 回归验证(n=60 配对,seed 0-59,pool='snapshot' e19afdfa,worktree 干净树 @59595f3f)

| 指标 | 旧(切片不弹出) | 新(pop 对齐) | Δ |
|---|---|---|---|
| hp_ge_60 | 0.067 | 0.067 | 0 |
| avg_final_hp | 42.47 | **26.00** | **-16.5** |
| battle_losses_le_2 | 0.233 | 0.050 | -0.183 |
| engines2_by_r6 | 0.167 | 0.033 | -0.133 |
| recipe5_by_r6 | 0.483 | 0.450 | -0.033 |
| dir_by_r2 | 0.900 | 0.950 | +0.05 |
| avg_refreshes | 2.17 | 1.77 | -0.40 |

方向解读(数字大变是修正的意义,非回归):
- 旧代理「每轮从全量 bench 重选 + 恒空上下文」= 每轮满 cap 最优
  重排的幻觉板;新语义 deployed 累积(开局 junk 占位、同名副本滞留
  bench、围栏持件)才是生产行为——板深样本进入更深的 Δ 池桶
  (seed0: 3,5,5,5… → 3,5,6,6,6…),而当前快照池更深桶均值更痛
  (ADR-0268 §4 方向反转未决)→ avg HP 大降主要是**板深读真 + 池
  桶重排**的合成;
- engines2 崩落 = 旧值的「每轮最优重选」水分被挤掉(与 ADR-0259
  同型:挤非法水分,HP 三指标大跌是修正不是退化)。

### 批⑦ F1 波及重验:席位/卖出类结论

凡以旧口径 bench 计数/席位门/bench_is_full 为前提的 sim 结论
(批⑦ 及此前各批的席位、容量、卖出通道、囤件判断)按新基线重跑:

| 指标 | 旧 | 新 | 备注 |
|---|---|---|---|
| 末轮 bench 均值 | —(恒虚高) | 11.7 | **>9 超物理容量** |
| 末轮 deployed 均值 | — | 6.7 | 真上场 |
| 末轮金均值 | — | 53.3 | 滞留金(bench 堵塞买不进) |

**修正暴露的下一个已知缺口(本 ADR 不辖,排后续批)**:sim 未建模
3合1 全场合并(生产 `simulate(BuyCard)` 调 `_merge_bench`)——同名
副本在 bench 堆积无法消化(末轮 11.7>9 即其形态),滞留金 53 与
engines2 低读数均含此失真分量。接线对照表
(docs/develop/currency_war/sim-wiring.md)已列为待办。

## Considered Options

- **A. 保留切片、只修 bench 计数(补 pop 但每轮重算)**:拒绝——
  deployed 不累积则同名去重/围栏上下文仍假,只修一半;
- **B. 上阵即 pop + deployed 累积 + board 聚合(选定)**:与生产
  `mutate_bench_deployed` 逐条对齐,执行层错位从此 sim 可发现;
- **C. 连带把 3合1 合并一并接入本批**:拒绝(本批)——归因混杂
  (pop 与 merge 两个语义变更搅在同一基线差里),merge 单独成批
  对照;已登记缺口。

## 影响

- `cw_sim.py`:deploy 代理段重写(pop/累积/真上下文/board 聚合);
  `_board_counts_of` 新增;账本 board/board_before 填真值;
- `docs/develop/currency_war/sim-wiring.md`:board 行移入已接;
- 测试:`test_cw_r410_bench_pop_semantics.py`(4 锁:单位守恒/
  deployed 单调/board 聚合/主阵营口径);
- 基线锚:本批后 n=60(seed 0-59,snapshot e19afdfa)参照本表「新」列。
