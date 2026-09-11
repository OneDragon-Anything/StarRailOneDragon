# 0277 sim boss 胜分支 + win 侧校准(批⑪最大杠杆;批⑪ F1/F2 + 检查项)

- 状态: accepted
- 日期: 2026-08-24
- 来源: sim 压测批⑪(F1/F2 + 检查项 4 条);worker 任务「sim 侧修复批五件」件2/件5(批⑪部分)

## 背景

批⑪ F1(结构性缺口):boss Δ池桶仅存 depth≥12/15,P1(depth≤7)
不可达 → `live_delta_for` 恒 None → 回退旧 `boss_delta`(返回值
恒负,无胜 branch)→ sim 300/300 boss 恒败且**机制上不可能胜**
——hp_ge_60 天花板被 boss 恒败 -18 钉死,与成型好坏无关;实机 P1
boss 可胜(局63 hp20 险过 / 局69 hp75 过 boss)。

F2(同根):过渡成型 e≥2 与 final_hp 零耦合(达成局 26.9 vs 未达
26.0)——战斗结算只读 depth,engines2 与 hp 之间无因果通道,一切
成型向策略 A/B 在 hp 类指标上判读力为零。

## 决策

1. **胜率 = f(成型度)**:boss Δ池不可达的回退路径加胜分支
   (`boss_settle_delta`):rung = 四体系达成数(`_engines_count`
   口径),按 `BOSS_WIN_P_BY_ENGINES` 掷胜——参数取批③ H3 实测
   矩阵(99 局实机 replay):boss 胜率 e0/e1=0、e2=0.25;
   **rung≥3 零样本,沿用 e2 值 0.25 不虚构**(局63/69 两胜局不足
   以拟合独立档,待实机 boss 胜局样本积累后再升级);
2. **胜时 Δ = 胜利小额**(+2,与 reward/supply 的 EARLY_WIN_DELTA
   同档)——「大胜」形态(局69 hp75)幅度不建模,待样本;
3. **Δ池优先序不变**:可及桶命中时经验分布优先(池是实机真值,
   规则表只补「桶不可达」的洞);
4. ⚠️ **P1 初始 HP=80 非 100**(批⑪自纠记档:按 100 锚算 boss 损
   失出伪影,常量注释落 `BOSS_WIN_P_BY_ENGINES` 处);
5. **批⑪ 检查项 4 条**(批级聚合,`simulate_p1_batch` 内嵌):
   - `boss_win_calibration`:boss 轮存在但 0 胜 = 恒败回归;可信
     深度桶(n≥5)间胜率应单调不减(薄桶不判,声明边界);
   - `formation_hp_coupling_sentinel`:e≥2 局与未达局 final_hp 差
     应显著为正,≤0 = 校准失败(价值链仍断);
   - `levelup_binding_check`:LevelUp 时 deployed≥level=binding
     (当轮 depth 可受益),r8/r9 loose>60% 报警(阈值=判据表原值);
   - `r5plus_refresh_closure`(纯披露):r5-r9 刷新计数(批⑪ 实测
     0/483),偏离 0 是行为变化信号非违规,实机遥测对照后定性。

## 回归验证(n=300,seed 0-299,snapshot e19afdfa;与 ADR-0276 同批落地)

| 验收判据(批⑪判据表) | 结果 |
|---|---|
| boss 胜率 >0 | **25/300**(97 局 rung≥2 × 0.25 ≈ 24,吻合)✓ |
| 胜率随 depth 单调 | issues=[] ✓(桶间无非单调对) |
| 成型-hp 耦合 >0 | formed 31.71 vs unformed 27.43,**diff +4.28**(修前 +0.9 噪声)✓ |
| hp_ge_60 天花板 | 0.017 → 0.04(「P1 高血通关」形态恢复可表达)✓ |
| levelup binding | r8/r9 loose 0/190(修前 49.7% loose——merge 恢复 deploy 通道后 binding 反而全绿)✓ |
| r5+ 刷新 | 0(与批⑪ 一致,闭合形态未变) |

## Considered Options

- **A. Δ池 boss 桶补样本(重放实机胜局)**:拒绝为本批方案——
  boss 胜局仅 2 局(局63/69),补进池会造出 n=1-2 的饥饿桶
  (ADR-0268 守卫会降级采样,白做);攒样本后再走此路;
- **B. boss_delta 加胜 branch + 胜率=f(rung)(选定)**:结构性
  解恒败,参数有 H3 实测矩阵背书,幅度沿用旧档;
- **C. battle/encounter 一并换规则表(批③ H3 全表)**:拒绝(本批)
  ——battle Δ池可及桶已在工作,重写会与本批 merge 归因混杂;
  encounter e2 胜率 n=1 不足以立规则,待样本。

## 影响

- `cw_sim.py`:`BOSS_WIN_P_BY_ENGINES`/`BOSS_WIN_DELTA` 常量;
  `boss_settle_delta`(结算回退路径);批级检查接线;
- `cw_sim_checks.py`:boss_win_calibration / coupling sentinel /
  levelup_binding / r5plus_refresh_closure;
- 测试:`test_cw_r413_sim_merge_win_wiring.py`(rung 档位/小额/
  批涌现/检查双向锁);
- 判读边界:engines2→hp 的因果通道**已接但幅度校准薄**(e2 格
  n=4、rung≥3 无样本)——hp 类 A/B 结论方向可信、点值 ±30% 浮动
  (H4 同判);「大胜 boss」形态未建模。
