# ADR-0476: 通道边际排序(溢余义务帧升级/刷新优先级显式化,overlay A)

> **引用勘误(2026-09-04 ADR 存量 review)**:`.debug/` 归档 → 本目录(decisions/)同名 ADR。文内出现处按此对照读取。

## 背景

posture_release 的 docstring 自述「通道开+预算内按 EV 排序」,但实现只有
预算合并与逐笔扣账——刷新是 arbiter 收尾块的残差消费者,买牌/升级 pass
恒先于刷新的**隐式固定序**从未被显式排序裁决过。真实错序在反方向
(W645 对抗裁决攻击 2 修正):当升级的搜索侧边际低于刷新时(典型=峰值级
ΔE≤0 → 省刷金 saving=0),残差仍被固定序导向升级授权链,刷新面饿死;
反之升后级概率抬档明显时先升后刷才是对的。提案面原文=`.debug/temp/
currency_war/w645_proposal_v2/SPECS.md` 提案 A-v2;落码前重评(W720,
同目录 `w720_overlay_reeval/REPORT.md`)=「修订后实施」,前提缺口经实读
核实仍在、辖域与分配器(ADR-0474)被 pipeline_spent 门结构性互斥不冲突;
三条修订(现 flip 谓词重述/概率单一址互指/off 臂换当前 HEAD)本批全部
执行。另并入 ADR-0475 挂账的定向刷新车道塌缩判据 arbiter 接线
(W721 分包在飞面遗留项,判据单一址已在 kernel/cw_economy 落位)。

## 决策

- **排序函数** `posture_release.rank_refresh_vs_upgrade(state, session,
  registry) -> 'upgrade_first' | 'refresh_first'`(辖域=新谓词
  `channel_rank_scope`:flip 义务帧(session.v3_release 单一址,ADR-0445
  现语义纯溢余判定)∧ 包装后 posture.level_up ∧ cap 满员)。边际两腿均
  既有单一址函数输出、零新自由参数:升级腿=`levelup_refresh_saving /
  upgrade_plan_fee`;刷新腿按 spec「expected_refreshes_for_card 逐刷
  递减金值序列÷刷价」——剩余期望搜索成本序列逐刷递减步长=刷价,每刷
  价边际恒 1 当量,归一化后裁决=``saving ≥ fee → upgrade_first
  (现行固定序零漂移);saving < fee → refresh_first``。
- **消费点**:arbiter 升级门(`boss_levelup_ban` 块)——辖域帧排序裁
  refresh_first 时,授权臂 ∈{dp, static_ev} 的升级候选降级拒(升级授权
  重估留待下帧),刷新先吃溢余残差;**人口位臂(pop_slot,[33] 当轮兑现)
  恒升级优先,排序不覆写**;upgrade_first 帧/非辖域帧行为零漂移。两世界
  定价按 W720 修订要点①:upgrade_first 世界刷新边际取升后级(E(L+1)≤E(L)
  严格不劣),refresh_first 世界取当级——比较对象与执行世界一致,防
  「一律升后级」系统性偏向刷新侧。
- **概率单一址(W720 修订要点②)**:刷新边际的概率源=`ev.
  levelup_refresh_saving` 内部消费的 `cw_shop_odds.
  expected_refreshes_for_card`,与分配器 Π_refresh 估计器(refresh_prob
  同表)同源互指,禁第二概率口径;锁组含 monkeypatch 行为证明与结构锁。
- **定向刷新车道塌缩判据接线(ADR-0475 挂账补线)**:arbiter 刷新收尾
  M-A 定向分支前置 `_omega_collapse_zeroed` 判据——塌缩带归零帧定向
  车道同判据停付(含空帧豁免;判据单一址=kernel.cw_economy,零新概率
  口径);非塌缩帧/兜底链帧车道零漂移。

## Considered Options

1. **两通道最小版排序(本 ADR)**——只辖升级 vs 刷新,买牌第三通道
   降后续独立批(spec §1 自认评分侧量纲残余错配风险);辖域窄化到
   「升级∧刷新并存」的 flip 义务帧,交换论证只在固定序下良定(spec §2
   窄化声明),不证全局最优。
2. v2 旧稿「一律升后级」定价——否决:refresh_first 输出时比较对象与
   执行世界错位,系统性偏向刷新侧(W720 修订要点① 的由来)。
3. 多通道全局贪心分配(v1 形态)——否决:边际与序不独立时交换论证
   不成立,裁决攻击 1 已破其独立性前提。
4. 维持隐式固定序 + 只把 docstring 改诚实——否决:错序亏损(每局
   10-30 金当量量级,spec §3)是行为缺陷,改文档不改行为=洗白。

## 后果

- 行为增量仅落在「flip ∧ 升级并存 ∧ cap 满员 ∧ saving<fee」帧(升级
  让一拍)与「P1 末窗定向授权 ∧ 塌缩带」帧(定向刷停付);两域帧占比
  与效应量级由 sim 双臂绝对指标验收(主判=刷新支出分布/死时带金锚带/
  出口金,判据=持平或改善采信)。
- 单一址面:排序两腿 + 塌缩接线共三处,全部复用既有符号(概率表/省刷
  金/升级费/塌缩判据),零新自由参数、零第二口径;锁组 16 条
  (test_cw_w724_overlay_a_rank)钉辖域谓词语义/排序契约/消费点零漂移臂
  /单一址互指/塌缩停付。
