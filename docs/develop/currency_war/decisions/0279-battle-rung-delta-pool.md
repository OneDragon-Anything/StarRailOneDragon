# 0279 battle Δ池按 rung 一维分桶(批⑬最大杠杆;批⑬ F1-F4/F7 + 检查项)

- 状态: accepted
- 日期: 2026-08-24
- 来源: sim 压测批⑬(数据可行性裁决「battle 一维键现在就够」);
  worker 任务「战斗结算成型感知——battle Δ池按 rung 分桶」

## 背景

批⑬定量解剖「sim hp_ge_60=4% vs 实机 32%(19 局 hp≥60=6/19)」
裂口,定位最大已定量化分量:

- F1:battle 按 (node×rung) 一维分桶 r0 n=26 / r1 n=24 双主桶
  达标(门槛主桶各 ≥10),分桶拟合对 battle 立即可做;encounter
  全线不足(4/9/2),不阻塞 battle 先行;
- F2:梯度真实——battle 桶均值 -11.5(r0)→-6.3(r1)→-4.7(r2)
  单调走强,rung 携带 depth 之外的成型信息;**depth-only 池把
  成型信息扔掉了**;
- F4:快照 battle 池 d9 桶均值 -7.3,实机真值 d9×rung1 = -0.9
  (n=10)——成型局单场战斗 sim 多扣 ~6.4hp,P1 多场累积即数十
  hp 量级(与批⑫ F4「成型-hp 耦合只剩 boss 门槛」互证);
- F3:联合二维键(node×depth×rung)不可行——27 个非空格仅 3 格
  ≥10,二维切分把样本粉碎;
- F7:run154910 boss 决策帧 100→结算 58(读数 -42)超出快照 boss
  池域 [-36,-13]。

## 决策

1. **battle Δ 桶键 depth→rung(一维替换,不上二维键)**:
   `live_delta_for('battle', key=rung)`——桶键即 rung(0-4),
   depth 维弃用(F3:样本粉碎;depth 残差折叠进桶均值,即批⑬
   建议的「池均值兜底」形态);rung 定义**单一源** = 收口
   `_settle_rung`(`_engines_count` 口径,与 ADR-0277
   boss_settle_delta 同源,boss 路径同步改调该函数);
2. **rung 输入口径**:池侧 = 结算前 `board_before`(outcomes
   自带主阵营计数)+ decisions deployed join(希儿系单卡判据;
   join 缺失希儿系漏计 → rung 低估 1 档,批⑬盲区声明);sim 侧
   = `_board_factions_of(deployed)`(factions+flows 并计,与
   boss 路径一致)——五个体系判据词(仙舟/列车同行/持续伤害/
   量子同频/贝洛伯格)均为主阵营词条,两口径在判据词表上等价;
3. **battle 桶不可达链**:逐级下探更低 rung(信息最接近的可及桶)
   → 全 rung 桶不可达 → 全池合并兜底(保经验分布方差)→ 池空
   → None(调用方旧方向二元模型);防饥饿守卫(ADR-0268)沿
   用,邻接宽随键语义 = rung±1;
4. **encounter 暂不分桶**(批⑬ F1 边界声明):维持 depth 键;
   r1 仅差 1 样本达标,攒样后下次快照重生成并入 battle 同法
   (`check_battle_rung_pool_bucket_lock` 边界锁防意外 rung 化);
5. **快照池重生成**(v3,`_SAMPLER_VERSION` 2→3 入指纹):battle
   桶键 rung(r0=26/-11.5、r1=24/-6.3、r2=9/-7.4),META 带
   `battle_rung` 真值表;历史报告对旧池(v2 指纹)重放须用导出
   JSON 快照(⓪ 纪律);
6. **检查项 `battle_rung_pool_bucket_lock`**(批⑬设计,进
   `simulate_p1_batch` checks 栈):battle 桶键全落 rung 域
   (0-4,depth 域键=rung 分桶未生效)/rung0+rung1 双主桶存在且
   n≥10/均值距批⑬真值表({0:-11.5, 1:-6.3})漂移 ≤3hp/
   encounter 未分桶边界声明/boss 池域覆盖;
   `depth_cliff_monotonicity` 同步收窄:battle(rung 键)不辖
   深度单调(r2 方差未判,批⑬盲区;rung 方向锁归真值表)。

## 回归验证(n=300,seed 0-299,snapshot d891233d28be3493)

| 指标 | 旧锚(ADR-0277 批,e19afdfa) | 新锚(本批) | 判读 |
|---|---|---|---|
| hp_ge_60 | 0.04 | **0.067** | 上移 ✓(向实机 32% 收敛中,幅度见下) |
| battle_losses_le_2 | 0.033 | **0.08** | 成型局败场收敛 ✓ |
| avg_final_hp | 28.81 | 28.95 | 小幅抬升 |
| engines2_by_r6 | 0.277 | 0.277 | 不变 ✓(分桶只动结算层,成型指标不动——规格预期) |
| recipe5_by_r6 | 0.62 | 0.62 | 不变 ✓ |
| avg_refreshes | 1.11 | 1.113 | 不变 ✓ |
| 成型-hp 耦合 diff | +4.28 | **+11.81** | 价值链大幅增强(formed 37.1 vs unformed 25.3) |
| boss 胜 | 25/300 | 24/299 | 不变 ✓(boss 路径零改动) |
| battle_rung_pool_bucket_lock | —(池 depth-only) | 0 违规 | ✓ |

与实机 32% 收敛度:4% → 6.7%,方向正确但**残余裂口仍大**
(32% 是上界读数,含少量中断局)——下一分量候选:encounter
depth-only 桶(F1 攒样后并入)、策略分歧分量(批⑬ F5 未分离)。

## Considered Options

- **A. (node_type, rung) 二维键推广到全部节点**:部分采纳——
  battle 一维 rung 键即刻落地;encounter 样本不足(4/9/2)拒绝
  本批并入,攒样后下次快照重生成顺带(F1 原文建议);
- **B. node×depth×rung 联合二维键**:拒绝——批⑬ F3 实测 27 个
  非空格仅 3 格 ≥10,样本粉碎;depth 残差按池均值兜底;
- **C. battle 缺 rung 桶时回 None 走旧方向二元模型**:拒绝——旧
  模型 rung 盲,正是本批要修的病灶;全池兜底保经验分布方差
  (批⑬ F3「池均值兜底」原文形态);
- **D. boss 池域按 F7 扩到 -42**:按差分口径**不可达**——
  run154910 是 attach 局,-42 是决策帧口径读数(决策帧 100 →
  结算 58);outcomes 相邻轮差分口径下该局 boss Δ=71→58=-13
  已入池。扩域诉求兑现为「域不缩」锁(min≤-36,重生成不丢失
  既有极值样本);若未来要纳决策帧口径极值,需先扩 outcomes
  schema(结算行记录决策帧 hp),另立 ADR。

## 影响

- `cw_sim.py`:`_settle_rung`(单一源)/`live_delta_for` battle
  rung 路径/`_pool_from_replay` battle rung 键/结算接线/
  `_SAMPLER_VERSION=3`;
- `tools/cw/gen_delta_pool_snapshot.py`:battle rung 桶 + META
  `battle_rung` 真值表;
- `cw_delta_pool_data.py`:重生成(指纹 d891233d28be3493);
- `cw_sim_checks.py`:`check_battle_rung_pool_bucket_lock` +
  `BATTLE_RUNG_TRUTH`;`depth_cliff_monotonicity` 收窄(battle
  不辖);`ANCHOR_REGISTRY_N300` 换新锚(旧值见上表);
- 测试:`test_cw_battle_rung_delta_pool.py`(新锁)+ r339/r340、
  r409、r413 旧锁按新语义更新(depth 守卫锁改 encounter 承载、
  sampler v3、锚登记动态取指纹前缀);
- 判读边界:battle r2 桶均值 -7.4(n=9)未锁(时代分层方差大,
  批⑬盲区);rung3+ 无实机样本,采样走下探/兜底链;实机 32%
  是上界读数,收敛判读以方向+趋势为准。
