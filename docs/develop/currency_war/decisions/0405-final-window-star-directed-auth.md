# ADR-0405 末窗星级定向授权(W232 挂账 C 项落地)

- 日期:2026-09-03
- 状态:accepted
- 谱系:ADR-0402 方案 C 挂账(依赖链 A/B→ADR-0400 复验→C;前置
  W232 产星通道 / W238 hp 投影 / W240 键改净星深已全解除);
  设计件 08 §4.2 Phase 1b(EV 授权框架的星级投资方向)
- 任务:W242

## Context(为什么)

W231 诊断(W232 ADR-0402 前身)实证 P1 段几乎不做星级投资的根因
之一:**末窗承接缺口大时,副本买入(升星素材)拿不到授权**——副本
的评分维(merge_progress/core_star/targets)只辖目标集内名字,填充件
副本全维零 delta 被仲裁器「非正分」结构性拒,W227 的 EV 缺口项
(`handoff_ev_gap_bonus`×gap)根本没机会被消费(评分零维的候选到
不了 EV 账)。W232 的 filler_star(期权分)开了**全轮域**的产星通道
(24.4% star≥2),但末窗「承接缺口大→定向放宽」的 C 项语义
(原 W231 定稿定义)一直挂账;W240 键改净星深后 sim 侧「升星→
boss 伤害方向」冲突已修,前置全解除。

C 项语义(任务书):P1 末窗(r≥`handoff_gate_min_round`)对**同名
副本买入**的 EV 账给定向授权——承接缺口大(gap≥1)时授权阈值放宽
(星级投资的承接价值计入),与 W232 filler_star_unit(期权分)/W238
handoff_boss_project(hp 投影)同一通道族,gap 单一源复用。

## Decision(授权点论证——本 ADR 最值钱段)

**授权点拆两半,分属两层**(防「一处豁免=授权越权」):

1. **candidates 层只放行候选生成**(r410 守卫 + `_buy_tag` 方向门,
   = W232 A/B 两豁免的 gap 条件化分支):gap>0 时 deployed 名同名
   副本生成 'copy' 候选。**这不是授权**——copies_cap/r408 同轮已卖
   守卫/bench 容量照常辖,候选进仲裁器仍要过全约束链。
2. **arbiter 非正分门定向放行**(授权点的显影位):gap>0 时 'copy'
   标签买候选放行进入约束链(不再被「非正分」结构性拒)。W231 主因
   的直接修复:评分零维是「到不了 EV 账」的通道缺口,不是「这笔投资
   无价值」的裁决。
3. **授权值零新增,单一源 = interest_rule 的 W227 缺口项**:
   `handoff_ev_gap_bonus`×gap(与 [33] 人口位/DP 花费授权同层的既有
   EV 授权框架,设计件 08 §4.2 Phase 1b 原文「承接缺口项进 ev 既有
   授权框架」的兑现)。C 项**不新增任何数值常量**(registry 无
   `star_directed_*_bonus` 字段,单帧锁钉死)——EV 放行值由缺口项
   独担,r8(boss 窗外)副本跨档买的 ev_auth 与 gate 臂同式。

**flag:`handoff_star_directed=False` 默认关,与 `handoff_gate_enabled`/
`handoff_boss_project` 三 flag 正交**(同 `handoff_boss_project` 式:
只在门开路径内被消费,单独开=零行为——正交臂整局 ledger 与基线逐位
一致的结构证据)。gap 判据单一源复用 `handoff.handoff_gate_gap`
(新增薄封装 `star_directed_gap` = flag 检查 + gate_gap,不建第二套
缺口公式)。

### Considered Options(取舍)

| 选项 | 裁决 | 理由 |
|---|---|---|
| 授权点挂 arbiter.interest_rule 内(与 W227 缺口项同位,加副本特判) | 否 | interest_rule 只辖「金≥50 跌破 50」的跨档账,而 C 项主拦截位是**非正分门**(评分零维候选到不了 interest_rule)——挂在 interest_rule 内修不到病灶;且副本特判进 EV 公式=授权值第二源(双计风险) |
| candidates 层新豁免=授权(豁免即放行执行) | 否 | 生成层放行≠授权:约束链(金地板/copies_cap/bench 容量)必须照辖;「放行≠必买」由单帧锁 `test_arbiter_constraint_chain_still_rejects` 钉死 |
| 副本评分维加权(filler_star 泛化到末窗) | 否 | W232 已建全轮域产星通道(filler_star_unit),C 项再叠评分=同语义双通道;C 项是「末窗承接定向」不是「产星」,授权走 EV 账不走评分表(设计件 08 反验收:不给承接做全局评分权重) |
| star 联动臂单开 filler_star(gap 条件化 W232 两 flag) | 否 | 与 W232 通道族纠缠(改 filler_star_unit 语义=动已标定项);独立 flag=可独立 A/B、可独立回滚 |
| r9(boss 轮)也辖 | 保留(随 gap 辖域) | r9 boss 轮 interest_rule 让位 boss 窗(boss_floor=10 地板辖),零分副本经非正分门放行后按 [18] 位面末 ALL IN 语义受地板约束——EV 缺口项在 r9 不消费(与 W227 同辖域),ADR 声明边界非缺陷 |

## Consequences

- **默认关论证**:ADR-0400/0402/0403 三连先例——outcome 面
  (sim P2 存活分布)无一一致正方向不解锁默认开;C 项同样按四臂
  联合 A/B 裁决(数字见下),通道保留。默认关=三 flag 全关时行为面
  与改码前基线逐 seed 逐位一致(零漂移门,实测 0 处)。
- **四臂联合 A/B**(n=300,snapshot 池 v10 指纹 b0f13268915db647,
  seeds 0-299 配对,planes=2 invest on,
  `.debug/temp/currency_war/w242_star_directed/w242_ab.json`):
  - **结构判据全过**:零漂移门(全关臂 vs 改码前基线逐 seed 逐位
    diff = **0 处**)/ 正交门(star_only 臂整局 ledger = 基线臂,
    drift=0 seeds)/ P1 非末窗(<8)三行为臂 vs 基线逐位零漂移
    (gate/gp/star 全 0)。
  - **行为面触发**:star 臂 p1_digest 与基线差异 300/300 seeds
    (末窗定向授权全面生效);gate/gp 臂分别 282/300、300/300。
  - **主指标(C 项边际 = star 臂 vs gp 臂;W232 flags 全关)**:
    进场 star≥2 率 7.38%→**13.65%**(基线 7.41%;C 项单独增量
    +6.3pp——末窗定向只辖 r8-r9,量级约为 W232 全轮域通道
    (7.7→24.4%)的 1/3.6,符合辖域预期);merges 0.127→0.21
    (有 merge 局 10.3%→17.7%);进场承接 tier1 局 13→**24**
    (+11 局,承接质量分布上移);配对方向 core2 20>/2<、
    merges 26>/2<(强正)。
  - **代价面**:末窗买入 1.61→3.18 笔/局;P1 出口金 32.72→27.62
    (−5.1,大于 W232 的 −1.3——末窗破息买更激进;逐局尾部跨档
    未在本批复算,沿 W232 代价口径声明);dup 买入 0.83→1.67。
  - **outcome 面(裁决口径)**:p2_hp0 0.9333→0.9225(方向为正,
    配对存活轮 17>/21< 微负 wash)/存活轮 3.79→3.71(微降)/
    胜率 0.1952→0.1888(微降)。**hp0 维正方向但存活轮/胜率
    wash/微负——与 ADR-0400/0402 同型:部分正方向,不足以裁
    默认开**(W232 hp0 正方向先例完全一致),通道保留默认关。
- **star 联动增量 vs W232 单开基准**(24.4%):本批四臂的 C 臂
  **不含** W232 flags(filler_star/pair_copy 全关)——star 臂 13.65%
  是 C 项单独增量(基线 7.41%,+6.3pp),不是与 W232 叠加的联合值;
  叠加联测(三 flag 家族全开)按需另批,C 项交付按边际口径收账。
- 单帧锁 `test_cw_w242_star_directed`(8 锁):授权点两半
  (生成/非正分门)+ 防双计(ev_auth 与 gate 臂同式 + registry 无
  C 项数值常量)+ 窗口/正交(star_only 恒 0)+ 约束链照辖 +
  默认值锁 + sim star_only 整局恒等。
- registry hash 锁同步更新(f2b0f572…,新增默认关 flag)。
- 风险与边界:r9 boss 轮零分副本按 boss_floor 辖(上表末行);
  副本买入金代价沿 W232 代价口径披露面(尾部跨档已在其 ADR 审计
  批披露);C 臂只辖 'copy' 标签(定向),bond_fallback 等通道的
  零分候选不受辖。**常数表方差观察(run 34/35,W242 收账时提)**:
  两局 boss Δ=-34/-14 同期差 2.4×——`handoff_boss_e_damage`
  单值常数(27.57 无条件口径)或需带方差/分位,归 ADR-0404
  已知边界(语料攒厚复验时一并评估),不辖本批。

## 影响

- `decision_v2/registry.py`(flag `handoff_star_directed`)、
  `decision_v2/handoff.py`(`star_directed_gap` 薄封装)、
  `decision_v2/candidates.py`(r410 守卫 C 臂豁免 + `_buy_tag`
  C 臂豁免分支)、`decision_v2/arbiter.py`(非正分门 'copy' 定向
  放行)。
- as-built:strategy/03 末窗承接门段补 C 项语义;设计件 08 §4.2
  Phase 1 表行标注;三同步代码注释引 ADR-0405。
