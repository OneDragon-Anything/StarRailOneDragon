# ADR-0170 跨局分配层 v0(RunAllocator Thompson + 必死局回收;05 号)

## Status

Accepted(2026-08-16;telemetry 接线/漂移闭环 CUSUM+重抓/节奏维拆臂为 v1——需实机窗口)

## Context

05 号诊断:所有已落组件都是**局内优化器**,没人回答「数据本身从哪来、分配对不对」——bot 集中玩当前最强 comp → telemetry 窄分布 → 学习组件外推失真 → 更不敢选 = 死锁（05 自诊断 CRITICAL-for-convergence）。必死局（A8 约三成败局的一半可中局判死）的剩余动作是免费实验预算，被白白输掉。版本漂移靠人工重跑脚本。

## Decision Drivers

1. goal 轮已落 13 个子系统，多个是学习/统计组件（pool_belief/damage_ledger scale/competence map）——它们的数据分布都由「下一局玩什么」决定，分配层是它们共同的数据供给侧。
2. plaza 幸存者偏差（784 篇全是赢家帖）需「可被自家 5-8 局推翻的弱先验」修正。
3. P(win) 投影供给方已就位（ADR-0161 first_passage）。

## Considered Options

- **F-1 式手动批处理**（K 臂×N 局全价一次性）：拒绝——弱臂全价、非持续、校准前一次性。
- **greedy 锁最优**：拒绝——零探索，数据死锁。
- **Thompson 常驻分配**（采纳）：后验定价探索、弱臂早停、后验集中后自动退化为总选最优（层自己关自己）。

## Decision

1. 新增 `cw_run_allocator.py`：
   - `StrategyArm`：comp 家族臂 + Beta 后验（v1 再拆节奏维）；
   - `from_plaza`：**伪计数封顶 ≤8**（幸存者偏差数据只配弱先验，自家实测可翻案）；
   - `select`：Thompson 采样；forbid 过滤（用户方向盘）；forced 豁免（成就/handoff 局）；
   - `update`：**分级奖励**（win=1.0；输局按位面/节点进度——小样本最有效降噪）× **adherence 加权**（防「分配姬子中途转万敌赢了算姬子」信用错配）+ 指数遗忘 γ（旧版本退潮）；
   - `dead_run_salvage`：P(win)<ε（保守 0.05）→ 可达臂中后验方差最大者（信息价值最大）+ **审计留证**（「没误杀有救的局」≥95% 判据的数据源）。
2. 测试 6 条：先验封顶/方向盘（forbid+forced）/后验移动+adherence/分级奖励单调/salvage 触发纪律+方差选择/**收敛 sanity**（合成环境 120 局，后 30 局 ≥25 次选真最优臂——Thompson 机制正确性实证）。

## Consequences

- v1 待办：telemetry 接线（每局终局 update；开局臂/终局臂双列）、CUSUM 漂移+自动重抓 plaza、节奏维拆臂、统计面板。
- 离线判据（合成 bandit 回放 Thompson vs 均匀批 vs greedy 的后悔/覆盖熵对比）可后补——收敛测试已是其核心断言。
- 与 09 号（competence）分工：09 管局内格子级门控,本层管局间臂级分配。
- 提案原文删档；决策单一源移本 ADR。
