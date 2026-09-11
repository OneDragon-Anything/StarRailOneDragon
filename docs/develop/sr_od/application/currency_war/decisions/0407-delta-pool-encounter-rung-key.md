# ADR-0407 Δ池 encounter 桶键 depth→rung(v11 重生成)+ 板深维分辨力裁决

- 日期:2026-09-04
- 状态:accepted
- 谱系:ADR-0404(同型键迁移先例:boss 桶)的 encounter 维续篇;
  批⑬ F1「encounter rung 样本不足暂 depth 分桶」边界声明的解禁;
  W248 报告 §二/§四假设 C 的收口
- 任务:W250

## 背景

W248(n=150 sim)实证:r7 encounter 是 P1 最大非 boss 单点损耗
(~29%),且板深完全不敏感(dep 三桶 EΔ=18.0~21.7 平)——但当时
encounter 桶仅 56 样本、depth 键只有 {6,9,12,15} 四档离散值,
「测不出弹性」无法区分**桶太粗**与**机制真平**;battle rung 桶
rung3/rung4 缺失,假设 A(投资节奏前置)的验证设计有失真风险。
任务书要求:全量扩容 + 分辨力查证(W248「主通道断裂」总闸工程)。

## 盘点与扩容实况(数据源口径)

快照由生成器从生产 replay(decisions/outcomes.jsonl)全量重建——
「历史局+W235 后新局」本就全部入池(W488 后每个实机局终自动再生;
离线扩容=把当前语料基准从 W240 时点推进到当前),增量 = 快照基线后
新增 outcomes 行。逐样本特征提取 n(P1):battle 177 / encounter 56 /
boss 51 / reward 118 / supply 3。

**每深度键 n≥30 未达**(见偏差节):P1 encounter 语料天花板=56 样本,
任何键方案下都不可能四桶各 ≥30——这是离线批的硬边界,需新实机局。

## 决策(分辨力裁决 + 键迁移)

1. **裁决:板深维「真平」,非桶太粗。** P1 encounter n=56 逐样本:
   - Σboard 原值 7 档,EΔ 无序(-28.0~-11.8,大板 15 号位 EΔ=-11.8
     反而最好);中位数分界两组置换检验 **p=0.87**;
   - Spearman(dep,Δ)=−0.001(零序相关;battle 对照 0.121);
   - 净星深键同样无梯度(sd0 E−18.9 / sd1 E−17.5,CI 大幅交叠);
   - 宽桶 w=6 两桶 E −18.5 vs −18.0。
   结论升级为实锤:**板面件数本身在遭遇战不可兑换伤害减免**,W248
   「主通道断裂」在 encounter 维从「池太粗不可判」改为「机制层真平
   (以本语料为准)」。
2. **rung 键显著可辨**:r0 n=23 EΔ−24.9(CI[−27.1,−22.0])/
   r1 n=27 EΔ−15.6(CI[−18.7,−12.6])/ r2 n=6 EΔ−4.3
   (CI[−7.8,−0.7])——梯度单调且 bootstrap CI 不交叠。「成型度
   (四体系引擎数)」才是遭遇战期望伤害的真载体。
3. **encounter 桶键 depth→rung**(v11):与 battle 同源
   `_engines_count`/`_settle_rung` 单一源;`live_delta_for` encounter
   并入 battle 分支(rung 域截幅+逐级下探+邻接宽 ±1 共式);
   `_pool_from_replay` 与 `cw_delta_pool_gen.build_pool` 镜像同步。
   否决净星深键:查证无梯度,不迁。
4. **v10→v11**:重生成指纹 **7af8197782d42c05**;W248 基线指纹
   73c64c8bc1992bab 作废标注不可比。boss/reward/supply 键不动。
5. **消费端对齐**(grep 全量核过):①simulate_p1 encounter 采样键
   (`_settle_rung`);②`_pool_from_replay` encounter 分桶;
   ③`cw_delta_pool_gen.build_pool` 同;④`live_delta_for` 分支+
   docstring;⑤checks:`battle_rung_pool_bucket_lock` 辖域反转
   (encounter 出现 depth 键≥6 = 违规)、`depth_cliff_monotonicity`
   跳过表增 encounter;⑥registry `handoff_boss_e_damage` **无需动**
   (boss 维 v10 已是净星深常数表,encounter 键变更不涉);v2 回退层
   掉血带 band_encounter 与池互斥(池 miss 才走回退),不动。
6. **已知边界**:battle BATTLE_RUNG_TRUTH{0:-11.5,1:-6.3} vs 当前
   实测 -13.4/-4.3,漂移 1.9/2.0hp < 3hp 门槛,真值表不动、如实记档;
   encounter r2/rung3+/boss sd>0 仍薄(贫困披露承接);cfg 波及:
   combat_losses 统计口径不变(encounter 战斗类节点计败场照旧)。

## Considered Options

- **保留 depth 键等攒样**:裁决已证 dep/sd 维无信号,攒到 n≥30 也
  测不出弹性(样本粉碎在无信息维度上)——否。
- **encounter 改净星深**:ADR-0404 方向算术对 boss 成立的理由
  (合并变号冲突)在 encounter 同样存在,但该维实测无梯度,迁了也
  是无信息键——否。
- **守卫/检查不动**(最小面诱惑):辖域反转不做 → 旧 depth 键池
  静默通过,键迁移完整性无防线——必须随批落。

## 验证

- 新锁 `test_cw_adr0407_encounter_rung_pool.py`(主桶单调/无 depth
  域残留/接线静态三锁);既有锁语义化适配:battle_rung 池锁
  (encounter 辖域反转)/r409 守卫两测(supply/reward 承载 depth
  路径)+版本锁 11×2(adr0292/r409)/w50 docstring 辖域/
  _pool_from_replay fixture 期望值;全量 pytest 见交付报告。

## 影响

- `cw_sim.py`(采样键/镜像分桶/live_delta_for/docstring/
  _SAMPLER_VERSION 11)、`cw_delta_pool_gen.py`(build_pool+头注+
  note 链 v11)、`cw_delta_pool_data.py`(v11 快照重生成)、
  `cw_sim_checks.py`(两检查辖域)。
- 下游 unlocked:W248 假设 C 兑现——r7 结算现在带真实 rung 条件性,
  「加强板面能少掉血」类 sim A/B 在 encounter 维恢复效力(经 rung
  通道,boss 维仍待 sd>0 语料)。
