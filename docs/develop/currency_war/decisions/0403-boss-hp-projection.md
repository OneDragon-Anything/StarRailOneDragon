# ADR-0403 承接门 hp 维 boss 投影(最小可验第一步)

- 日期:2026-09-02
- 状态:accepted
- 谱系:设计件 09_boss_hp(W234,ac570261)§3.1 主修法落地;ADR-0400
  承接门的 hp 维语义化;ADR-0399 档位切点标定口径的兑现
- 任务:W238

## 背景

ADR-0400 承接门 `handoff_gate_gap` 末窗投影取 `handoff_snapshot` 现算,
其中 **hp 维取当前 state.hp**——r8/r9 时点的 hp 是 **boss 前**值;而档位
切点 `HANDOFF_HP_CUTS=(20,50)` 的标定语料(ADR-0399,n=48)是 **P2 进场
真值 hp(boss 结算后)**。→ 末窗用 boss 前 hp 喂 boss 后切点 = 标定口径
错位,hp 维系统性高估一档:**板面达标、hp 临界局(r8 hp 21~50)现投影
总档=1 → gap=0 门不触发,而 boss 结算后 hp 归零**(run28/31/33 三局连证
的机制解释,设计件 09 §1-§2)。

## 决策

1. **常数表 `E[boss 伤害|板深档]` 离线标定进 registry**(非运行时预测):
   源=Δ池 plane=1 boss 桶(板深键 `min(Σboard//3,5)*3`,与 sim 采样键
   `cw_sim._deployable_depth` 同口径,不建第二套分桶),**地板删失行剔除**
   (boss 行 hp_after∈{0,1}=下界非真值,ADR-0307 口径)后的桶均值。
   标定结果(2026-09-02,生产 replay 48 行 plane=1 boss 差分):
   **桶 9:n=4/29.25;桶 12:n=17/30.35;桶 15:n=6/17.5;删失剔除 21 行;
   全池未删失均值 27.33 作缺桶 fallback**(`handoff_boss_e_damage` /
   `handoff_boss_e_damage_default`)。标定脚本
   `.debug/temp/w238_calibrate_boss_delta.py`(逐行明细含删失标记)。
2. **投影语义**(`handoff.boss_projected_hp` 纯函数,消费点=
   `handoff_gate_gap` 内部):
   `hp_proj(r8) = hp + 2(奖励节点胜,五局恒 +2) − E[伤害|档]`;
   `hp_proj(r9) = hp − E[伤害|档]`;钳制 [0,100]。快照本身不动
   (Phase 0 语义=P2 进场真值,两层口径各归各位);板面维不投影;
   切点/标定语料不动——变的只是「喂给切点的 hp 取哪个时点」。
3. **flag `handoff_boss_project` 默认关,与 `handoff_gate_enabled` 正交**
   (投影只在门开路径内被消费,单独开=零行为)。默认关论证:A/B 裁决
   先例(ADR-0400/0402 双关默认)——outcome 面(sim P2 存活分布)无
   一致正方向不解锁默认开;投影修的是判据口径(盲区类触发面),收益
   仲裁依赖 ADR-0400 复验链,通道保留。
4. **观测披露**:`session.v3_handoff_hp_proj`(投影开时写)/sim 账本轮行
   `handoff_hp_proj`(关臂恒 None)——每局 r8/r9 判读可先看「boss 后
   投影 hp」而非裸 hp(与 Phase 0 快照同判读增益路径)。
5. **A/B `simulate_handoff_ab` 扩三臂+正交臂**:off(双关基线)/gate
   (门开无投影)/proj(门开+投影)+ proj_only(仅投影,整局 ledger
   应与基线逐位一致=正交性结构证据);新增 `blindspot` 观测(同 seed
   同轮 proj gap≥1 ∧ gate gap=0 的轮/局数——盲区修复行为差)。

## Considered Options(取舍)

- **运行时预测器(模拟剩余轮 hp 漂移)**:被 08 §4.2「不预测」裁决
  否;本修法只把**已知必然发生节点(boss)的期望结算**计入近端投影,
  与 ADR-0400「近端投影」同族,精度更高一步而非换预测范式。
- **候选 b(boss 前 EV 账偏向战力)另立臂**:ADR-0347 双门双计禁令,
  合流(投影使 gap 更准 → 挂载点 b 授权方向自动更准,设计件 09 §3.2)。
- **键改净星深(Σboard+Σ(star−1))当场做**:见缺口②处置——需 Δ池
  重生成批,本批不辖。

## 已知边界(缺口②实证与处置)

- **删失剔除的存活偏差**:剔除 hp_after∈{0,1} 行后留存样本偏向「存活
  boss 的局」,弱板真值伤害被低估(桶 12 均值 30.35 含大量败北重创局
  的未删失邻近样本,方向上仍 >桶 15)。声明为标定口径而非修法缺口
  (ADR-0307 口径的代价面,桶 n 已披露)。
- **Σboard 键与升星方向冲突(设计件 §5 缺口②,实证成立)**:Δ池 boss
  桶键=Σboard;`_merge_bench` 3合1 消耗场上副本 → 场上件数 3→1
  (Σboard −2/次,单帧锁 `test_merge_reduces_board_sum_direction_gap`
  钉死)→ 键落更浅桶,而浅桶期望伤害更大(桶 12 30.35 > 桶 15 17.5)
  → **sim 判「升星→boss 伤害↑」,与 [27] 机制(升星→输出↑→P 罚↓)
  方向相反**。sim n=150 默认策略下 3合1 合并 0 次(第三副本买入被
  copies_cap/r410 守卫拦),该失真当前潜伏,主要咬 W232 C 项(末窗
  星级定向)与本门联动的 sim 仲裁。**处置=声明边界**(本批):投影
  常数表与 sim 采样共用同一 Σboard 键,口径自洽但星级投资的 hp 收益
  被 sim 系统性低估;**键改净星深归 Δ池重生成批**(v10 采样器版本
  升级,池指纹重算),W232 C 项批前置。
- **boss 胜率 0.05 无条件(设计件 §5 缺口①)**:胜→+2 小额,非阻塞,
  A/B 判读声明(ADR-0308 待重标沿用)。

## 验证

- 单帧锁 `test_cw_w238_boss_hp_projection`(8 锁):常数表方向/盲区
  修复行为差(hp 22/30/33 三点 × gate gap=0 ∧ proj gap≥1)/弱板两臂
  同值/公式(r8+2、r9 无、缺桶 fallback、钳制)/正交性/缺口②机制锁/
  sim 账本披露/proj_only 整局正交+零漂移(n=4 fallback 池)。
- A/B 三臂 n=300 同池(snapshot)同 seed 配对:数字见 W238 交付报告
  (blindspot 行为差/零漂移门/正交门为结构判据,应恒过;outcome 面
  按裁决口径如实报)。
- registry hash 锁同步(test_cw_adr0293,新 hash 8aa73966…)。

## 影响

- `decision_v2/handoff.py`(投影函数+gate 内消费)、`decision_v2/
  registry.py`(W238 块四字段)、`decision_v2/strategy.py`(轮清零)、
  `cw_sim.py`(账本披露+三臂 A/B)。
- as-built:strategy/03「P1 末窗承接门」段补投影语义;设计件 09 收缩
  (第一步落地标记);三同步代码注释引 ADR-0403。
