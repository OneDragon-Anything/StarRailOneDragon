# 0362 Δ池 plane 维键化 + sim P2 位面段(案 a 最小可用)

- 日期:2026-08-28
- 状态:accepted(直接落地)
- 关联:W156 设计评估(`.debug/temp/currency_war/cw_dev/deep_read/W156_报告.md`,
  裁决单一源——案 a/分期 M1)、0361(P2 V_D 修法,本批给它的批量 A/B
  验证场)、0308/0312/0355(指纹版本与锚重记先例)、0351(P2 基础收入 5
  实测口径,economy.md §10.1)

## 背景

`simulate_p1` 只跑 P1 九轮,ADR-0361 的 P2 修法(DP 窗授权 + 机会成本)
只有单帧锁与四局真帧回放,**无 sim 批量验证场**。同时 W156 勘察发现既有
P1 池被 P2 污染:桶键无 plane 维,44 条 plane=2 差分(含 16 条 P1r9→P2r1
跨位面差分)混入 P1 主导的池——P2 掉血带(15-17)系统性抬高 P1 桶战损。

## 决策(W156 案 a,M1 最小可用)

1. **Δ池 plane 维键化**:SNAPSHOT 形状 `{节点:{位面:{桶:[Δ]}}}`,差分
   归属**后行位面**(P1r9→P2r1 归 plane=2)——顺手清除既有 P1 池 P2 污染。
   `_SAMPLER_VERSION` 7→8,指纹重算;`live_delta_for` 增 plane 参,
   **plane≥2 不跨位面回退**(位面难度语义不同,跨位面借样本=口径混桶),
   该位面缺桶走位面内兜底/回退层。P2 语料 44 行,条件化分桶不做
   (每桶 n<5,防饥饿守卫辖;实际采样≈位面内全池合并经验分布)。
2. **simulate_p1 参数化 `planes`**:位面段迭代(P1 9 轮 + `planes>=2`
   追加 P2 7 轮);进场继承 P1 末态(hp/gold/board/bench/deployed/
   equips/意向全带过;HP 跨位面继承=用户纠错真值,其余无重置证据按
   全继承标注假设)。P2 节点序列=16 局 outcomes 拼版(battle/battle/
   supply/battle/encounter/reward/boss,逐槽一致无变异观测);P2 battle
   回退档=掉血带 15-17/胜率 0.11(W151);事件金复用 P1 表(打标未校准,
   P2 基础收入 5 已实测)。**决策代码 plane-aware 已就位,策略层零改动**
   (进 P2 时 st.plane=2 自动激活 cw_economy/cw_intention/ADR-0361 分支)。
3. **P1 段逐位不变**:`planes=1`(默认)循环体与 RNG 消耗序与旧代码
   逐位一致——回归门=改前后同 seed 同池(池未变侧)全指标 diff={};
   P1 锚定指标在 `planes>=2` 批次按 plane=1 行切片(`_Plane1View`)。
4. **P2 headline 四联**进批报告:存活轮/P2 胜率/hp0 率/D 次数
   (分母=进场 P2 的局,幸存口径与实机一致);`simulate_p2_ab` 同池同
   seed 配对 `vd_p2_enabled` on/off(同进程 flag 对照,W154 记档的并行期
   唯一安全法)。
5. **检查器**:池级检查(桶饥饿/深崖/rung 锁/reward 锁/coverage)消费
   `plane_view(pool,1)`——P1 语料判据零改动,P2 桶贫困走生成器 META
   ``p2:`` 前缀披露;新增最小集 `p2_gold_nonneg`/`p2_segment_shape`
   (ts 单调跨位面/plane 域/round_num 域)。

### 锚登记表换锚(ADR-0308/0355 同款流程)

W140 锚(bab146c6)再次失效——P2 段扩展换锚:池指纹随 plane 键化重算
(v8)且锚池与主仓提交快照此前已分叉(bab146c6 vs 4d28822c 系列)。新锚
=主仓提交快照 v8(0bf6c0d6…),P1 侧 drift 如实记档(键化后 P1 桶语料
变化:battle rung1 混入的 P2 差分清除→均值/胜率移动)。

## Considered Options

- **案 b(独立 simulate_p2,16 真值进场态重放)**:消除 P1→P2 进场建模
  误差,但 16 进场态非独立同分布(旧策略病局幸存弱板偏差)+ A/B 统计
  功效受限(16×seed 网格)——**M2 作交叉校验臂**,验 a 的进场分布不偏。
- **案 c(simulate_match 三段连跑)**:P3 语料零样本,全层无据=伪验证场;
  当期收益 0。**缓**,P3 语料攒到再立项。
- **P2 池条件化分桶(rung×plane)**:44 行差分按 rung 分桶后每桶 n<5,
  `_BUCKET_MIN_N=5` 全线触发——分桶是假条件化。**不做**,如实走位面内
  全池合并 + 回退层掉血带。
- **P1 指标不切片(planes>=2 批次全量算)**:P2 段行会稀释 engines2/
  recipe5/battle_losses 等 P1 锚定指标(与历史锚不可比)——切片后
  planes=1/2 批次的 P1 指标口径恒同。
- **P2 节点序列取 economy.md §10.2 开局帧(1 帧权威)**:开局帧 1 样本
  vs outcomes 拼版 5+ 局一致(r3-r6 槽序不一致,帧 1 样本不敌拼版;
  帧间变异无观测不外推)——取拼版,注释记分歧,多局复核后如需变异位再改。

## 后果

- P1 sim 基线锚换到 v8 池;跨日对照一律核指纹(`pool_fingerprint`
  进报告头,⓪ 纪律不变)。
- P2 语料边界如实:行为分布验证(D 次数/金轨迹/存活轮)支撑,**hp 点值
  校准不支撑**(W156 §2);P2 事件金逐轮分布零样本——事件金复用 P1 表
  打标未校准,P2 金流系统性偏差披露在案。
- 案 b 校验臂与 P2 节点序列敏感性对照(±1 变体)= M2;sim-wiring 四字段
  (简报/投资二段/事件 overlay)披露不建模 = M3 按需。
