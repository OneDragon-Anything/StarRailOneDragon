# 0292 reward/supply Δ池采样真值化(EARLY_WIN_DELTA 摘除 reward 通道)+ 批㉗ F4 胖尾证伪

- 状态: accepted
- 日期: 2026-08-24
- 来源: sim 压测批㉗ F3/F4(校准件 EARLY_WIN_DELTA 真值化,worker 任务
  「奖励轮 Δ池经验分布采样」);批⑬ 分桶先例(ADR-0279 同法)

## 背景

批㉗ F3 定位 EARLY_WIN_DELTA 是校准层最敏感旋钮(±2 → avg_final_hp
∓6.9,超 n=300 分辨率底 3.6 倍),且它喂 reward/supply 结算(L604 旧位)
从未被真值核对;F4 断言语料分布「median +2 / 恒 2 占 82.9% / mean 9.15 /
p90 +39 / 负值 2.4%」→ 结论「sim 每局期望 hp 低估 20+」,任务是按该
分布改经验采样并预期 hp_ge_60 显著上移。

**本批首先复核 F4 数据,结论:胖尾是探针配对伪影,非语料真值。**

- 同 run 内奖励轮 hp 差分(replay outcomes.jsonl,191 结算行/29 run,
  与池生成器同配对口径):**n=43,全部 = +2**,median=mean=p90=+2,
  零负值;decision 帧 hp 与 outcomes hp_after 的另两种配对(轮内/跨轮)
  同样全 +2,零胖尾;
- 跨 run 相邻行差分(未按 run_id 分组的全局行序):25 个奖励行的前行
  属于**上一 run**(reward 常为 run 首节点),差分 = 上一 run 末行 hp →
  下一 run 首行 hp,取值 {+27, +17, +25, +11, +24, +35, **−2**, +61, …}
  ——**p90≈+39、约 2% 负值的形态与 F4 报告完全同构**(−2 负值是跨 run
  配对的指纹:同 run 内 HP 只降不升 + 奖励恒 +2,不可能出现负奖励差分);
- 推论:F4 的「每局期望 hp 低估 ~20」不成立;批⑬ 裂口
  (sim hp_ge_60 vs 实机 32%)的 reward 侧分量 ≈ 0(恒 +2 已被旧常数
  正确建模)。

## 决策

1. **reward/supply 结算真值化(机制照做,真值换源)**:结算由恒
   `EARLY_WIN_DELTA` 改 `live_delta_for(node, depth, rng, pool_map)`
   Δ池经验分布采样——EARLY_WIN_DELTA 从此只喂 r1-r2 battle(fallback
   档);「最敏感旋钮从未核对真值」的病灶以**采样源=语料**根治,语料
   增长(若未来真出现回血机制)经快照重生成自动跟真,零再校准;
2. **桶键与守卫**:沿用既有 depth 分桶维度 + 缺桶浅侧回退(r343 E),
   再缺 → 该节点**全池合并兜底**(奖励/补给零战力交互,语料差分无
   深度条件性;不让 r1-r2 浅板深轮退恒常数)——池空 → None → 回退
   `EARLY_WIN_DELTA`(两态语义不变);防饥饿守卫(ADR-0268)原样辖;
3. **快照重生成**:`_SAMPLER_VERSION` 3→4(采样语义变更入指纹),
   新指纹 `066c41856dd5d4f5`(reward n=30→43 全 +2;battle r0 n=26→40
   / r1 n=24→31,语料 2026-08-23 晚批 7 run 增样);历史报告对旧池
   (v3 `d891233d`)重放须用导出 JSON 快照(⓪ 纪律);
4. **检查项 `reward_delta_pool_bucket_lock`**(进 simulate_p1_batch
   checks 栈):reward 池非空 n≥30 / 全样本均值距语料真值 +2.0 漂移
   ≤1hp / **跨 run 配对伪影哨兵**(域 [0, 20],负值与大正值即报——
   F4 形态若在重生成后涌现,先核生成器 run 分组,不当作真值入锚);
   空 reward/supply 池(fallback/Path)不辖(同 battle 锁语义);
5. **HP 上界联动(X 件复核)**:胖尾既证伪,「+20~39 回血破百」的
   触界担忧消解——n=300 实测终值 >95 = 0 局、逐轮 hp≥100 = 0 次;
   `HP_UPPER_BOUND=100` 钳制**维持**(防御性不变式,真值核仍留实机),
   cw_sim 内 ADR-0287 注释同步改指向本 ADR;
6. **锚换代归因分离**:`ANCHOR_REGISTRY_N300` 换新锚(指纹
   066c4185)——**换锚主因 = 池数据增长**(battle 桶增样 + 新 run),
   非采样语义;同池同 seed 配对 A/B(新采样 vs 恒 +2)分离两者(下表)。

## 回归验证(n=300,seed 0-299,同池 066c4185 同 seed 配对)

| 指标 | 旧锚(ADR-0284,d891233d) | 恒+2 臂(同新池) | 池采样臂(=新锚) | 判读 |
|---|---|---|---|---|
| hp_ge_60 | 0.047 | 0.127 | 0.127 | 上移 ✓ 但归因=池增长,**非 reward 采样** |
| avg_final_hp | 29.25 | 34.82 | 33.98 | A/B 差 0.85 < 分辨率底 2.80(sd_pair 24.7 现算)→ **噪声带内,不可叙述方向** |
| battle_losses_le_2 | 0.073 | — | 0.127 | 池增长(battle 桶增样) |
| engines2_by_r6 | 0.237 | — | 0.407 | 池增长/语料新 run 侧 |
| reward/supply Δ | 恒 2(常数) | 恒 2(常数路径) | 全 2(池采样,n=1205 轮) | 真值分布=恒 +2,与 F4 伪影分布无关 |
| 终值 >95 / 触界 | 0 | 0 | 0 / 0 | 触界率 0,钳制维持(决策 5) |
| reward_delta_pool_bucket_lock | — | — | 0 违规(reward n=43 mean=2.0) | ✓ |
| battle_rung_pool_bucket_lock | 0 | — | 0(r0 −11.75/r1 −5.9,距真值 ≤0.4) | ✓ 语料增长未漂移 |

与实机 32% 收敛度:4.7% → 12.7%,方向正确;**但该上移是池数据增长
的产物**,reward 侧分量经 A/B 证为零——裂口剩余分量候选不变
(encounter 分桶、策略分歧)。

## Considered Options

- **A. 按 F4 分布落地「17% 概率 +20~39」混合**:拒绝——胖尾经语料
  复核为跨 run 配对伪影(负值 −2 是其指纹),按伪影校准 = 采样凑证,
  会凭空 +15~25hp 使 hp 类指标全体失真;
- **B. 证伪后整个任务撤销(维持恒 +2 常数)**:拒绝——EARLY_WIN_DELTA
  「最敏感旋钮从未核对真值」的结构病仍在;真值化后采样源=语料,
  未来语料出现真回血机制时自动跟真,且伪影防线(检查项哨兵)沉淀;
- **C. reward/supply 按 rung/深度分桶采样**:部分采纳——沿用 depth
  桶键载体 + 全池兜底;拒绝更细分桶(语料零方差,n=43 细分=把无信息
  维度当效应,且浅桶缺样会让 r1-r2 退常数形成伪分层);
- **D. 修正批㉗ 探针(重建 sim_stress_b27_reward 配对)再跑**:拒绝
  落地为本批动作——探针脚本已删(压测批用毕即清),复核已用生成器
  同口径独立完成(伪影证据链见背景节);F4 证伪结论进本 ADR 与检查项
  哨兵,批报告原件不改(历史存档)。

## 影响

- `cw_sim.py`:`live_delta_for` reward/supply 全池兜底 + docstring、
  结算接线(reward/supply → live_delta_for)、`node_delta` 降为回退档
  docstring、`_SAMPLER_VERSION=4`、simulate_p1_batch 接线
  `reward_delta_pool_bucket_lock`、HP 上界注释改指本 ADR;
- `cw_delta_pool_data.py`:重生成(指纹 066c41856dd5d4f5,
  sampler_version=4);
- `cw_sim_checks.py`:`check_reward_delta_pool_bucket_lock` +
  `REWARD_POOL_*` 常量;`ANCHOR_REGISTRY_N300` 换新锚(旧值链注);
- 测试:`test_cw_adr0292_reward_pool_sampling.py`(新锁 8 条:池采样
  接线/全池兜底/回退常数/快照对拍真值/漂移+伪影变异/跨 run 配对防线/
  采样器 v4/批内嵌锁)+ r409 锁 v3→v4、repay 锚指纹串更新;
- 判读边界:reward n=43 集中单文件语料、plane 维未分(P1 主导);
  supply 结算标签语料零行(池空,回退常数路径=当前真值路径);本批
  checks 红项(engine_seed 回卖/幻影装备/dead_system 等)为 ADR-0289
  清偿批待裁项 + 池增长边际效应(encounter 桶9/12 均值 -17.86/-17.91
  险触单调带),归判读域不归本批;
- 下游:批㉗ F4 的「reward 侧裂口分量 ~20hp」从裂口归因账上**核销**;
  boss 族/encounter 分桶仍是裂口剩余候选(F6/F1 原文)。
