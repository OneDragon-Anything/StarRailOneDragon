# ADR-0465: 迁移批 3 预算收权——义务模型归位优化层核,确定性费用查表替换 DP 姿态供给

> **版本界碑(2026-09-04 ADR 存量 review;统一迁移批史,与 b94e9cfb 互证)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb 删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

## 状态

accepted(2026-09-03;W633)

## 背景

重构蓝图(W613 BLUEPRINT v-final.1 §3 裁决)定谳:优化层 = 义务模型为核 + 排程查表 + 单步 EV,DP 退出生产路径。批 2 落地后,预算侧两接缝(`economy_cycle.schedule_upgrade` / `refresh_ev_budget`)仍以 DP 姿态(`cw_horizon._solved` 的 level_up/refresh_budget 标量)为供给——义务模型是在「DP 喂输入」的配置下转正的。批 3 是全重构唯一「换算法」批,必须有自己的行为判据(W623 预验尸 D0-D4、W630 预注册 A/B 协议判前锁定)。

## 决策

1. **确定性预算核单一址(R4)**:`schedule_upgrade`(排程预告态:人口位触发 [33] ∨ 概率级触发 [3]+息引擎前置 [12];禁升 = 息引擎未立不追级 + 淘金客姿态升级通道退役)与 `refresh_ev_budget`(预算式 `min(6, ⌊(g−R*)/刷价⌋)`,合法 0 帧契约:储备段与应急带——**血预算带不在预算层辖域,停付由 arbiter 拒付层兜底,W635 F1 收口**)两接缝换机制常量直算;排程判据、R* 储蓄分量、arbiter 金地板授权、EV 升级授权②臂共调同一函数,禁第二实现。轮姿态载体(`decision_v2.posture.Posture`)字段形状与旧 DP 姿态同构,消费方接口零改动,只有生产者换核。**规则文本偏差披露(W635 F2)**:W615 §2-R4 规则 2 的第三合取「花完升级费后 g′≥息线」与其 §1.3 伪码矛盾,实现取伪码侧(不设该合取,防预告态塌缩),可负担性/平台未破由执行层收口(ev.levelup_ev_basis);W615 文档修订与 A/B 左移面判读披露由编排者处理。
2. **供给权交接(D0)**:6 个姿态消费点逐点接新供给(strategy 生产链/arbiter 金地板/scoring P2 窗/ev 授权②臂/posture_release 合并与准入门/遥测投影);确定性核恒有定义,「查询异常→None→保守回退」级联面消灭;局23 型帧哨兵锁(g=100+备战空+comp 空 → 义务>0 ∧ release 活性 ∧ 标签≠存息)同 commit 变绿。
3. **cw_horizon 摘除(F3 扩口)**:非 DP 真值/标定面(节点日程真值 `nodes_of_plane`、日程几何、`clicks_to_level`、息闭式、损血先验表、`p_win_p2` 胜率映射、峰值级查表)迁保留模块 `cw_plane_table`,12+ 消费文件单源改引,**禁内联常量置换**(ADR-0366 P2 计 9 病灶防线);DP 本体(762 行)整文件删除,git 历史为 prior art;`grep cw_horizon import` 全仓生产代码 = 0。
4. **消费方口径显式化(D2)**:三个「>0 即授权」点(scoring P2 窗/posture_release 准入门/arbiter 金地板)改**预算函数口径**;存息准入门辖域从「DP 存息姿态帧」改机制口径(溢余且未被 flip 覆盖,E1 原文)——查表预算在溢余帧天然>0,旧姿态短路会让准入门结构性失活;血预算带停付防线=arbiter 拒付层(blood_budget_levelup_blocked/blood_budget_refresh_blocked),合并层不特判(穿透锁钉住,W635 F1 修正版)。
5. **淘金客姿态集成(W621)**:LevelUp 退役为刷驱姿态主驱动(谓词 `refresh_invest_active` 单一址辖排程核与授权链全臂,与 W621 sim 注入臂「LevelUp 全抑制」同口径);预算式为语义显式件(sim 实证行为近零增量);等级回落为预期方向(w630 协议出口 9 预期带 7.0-8.6)。
6. **R3 断供驱逐推广(蓝图 §4.3-R3)**:冻结驱逐语义从 LineTrack 推广到配方对——pair 体系成员**在店新件**连续断供 ≥5 轮(保守阈值,DROUGHT_BAIL 同族先验,探针批标定)→ 体系入 `pair_evicted`、pair 重派生排除;W578 代理门锁:驱逐后 `pair_target_comp` 物化非空(target 链不因驱逐全盲)。
7. **F5 清偿(蓝图 §6)**:三模块级旗标(P1_FINAL_LINE_GATE/P1_RECIPE_LOCK/P1_LOCK_TRANSITION_PAIR)删除、行为无条件化(三门 sim A/B 已终裁 0341/0357/0367);`DirectionView.gates` 字段保留恒空(契约形状);A/B 基线臂自批 3 起只走 git 冻结快照。
8. **标签词汇表 v2(D4)**:`升级`/`升级+D<刷数>`/`+D<刷数>`/`存息`(经 release 包装恒 `release`),生产者=`build_round_posture` 单点;离散动作码(+D2/4/6)假设退役,连续刷数为查表预算值域形状;批 3 前回放语料的姿态标签仅供参考、不进批 3 后对拍基线。
9. **注入面单源(W636 A)**:schedule_upgrade/refresh_ev_budget/build_round_posture 增 `registry` 显式参数(缺省落 _registry_of(session)→DEFAULT),prep_brain._budget/scoring/strategy 生产链传同一实例——BudgetView 装配禁混双源;注入一致性锁钉住(注入非默认 registry 三函数行为同变)。现双臂同 DEFAULT_REGISTRY,已跑 sim 数据未被污染,只修地基不返工数据。**TurnState 快照语义落码(W636 C → W639 升级)**:真实别名写者实证(shop.py mutate_bench_deployed 元素级星级/装备就地写、deploy_bench 装备覆盖,均 session 侧活对象)→ _tracking_view 与 adapter 快照装配对 BenchChar 做 `cw_state.snapshot_copy` 浅拷贝+equips 固化 tuple(成本 <20µs/帧,<0.1% 帧预算),「快照不在帧间存活」由机制保证非消费纪律;BenchChar.equips 注解放宽 Sequence(写端仅 session/state 活对象);隔离锁双向钉住。

## Considered Options

- **保留 DP 为「咨询输出」**:被蓝图 §3 否决(3M 状态格 ×3 处硬伤世界模型产出 3 个可直算标量;W615 §3 逐消费点清点);本 ADR 执行其退役。
- **排程收窄为「付得起才排」**:否决(W623 D1)——R* 塌缩→义务花光→更排不上的自我强化贫穷循环;预告态契约把可负担性收口在执行层单点。
- **查表预算不设合法 0 帧**:否决(W623 D2)——存息准入门结构性失活、血预算停手被预算合并穿透;0 帧契约+穿透锁为此设。
- **`nodes_of_plane` 内联常量 9**:否决(W623 D3)——会话自适应真值内联 = ADR-0366 修掉的 P2 计 9 病灶成批回流;迁保留表函数模块。
- **驱逐度量含到手资产**:否决——「补不进的新件」量的是供给渠道(蓝图原文);到手资产不救供给,否则持 1-2 引擎的死体系永占 pair 槽。

## 后果

- 正面:删 762 行 DP 模块与 0.3s/解求解面;标定错误沿一次加法/查表传播(单帧锁可定位),不再乘状态格;供给恒定义,静默保守级联(局23 形态的发生机制)结构性消灭;效率复核判据:decide 热点回落(原 DP 求解热点随核替换消失)。
- 代价/边界:升级费表 ±20% 粗估误差只进一次加法但直接进 R*(W615 F5,探针=攥金死亡出口);N5 连胜耦合二阶盲区按蓝图 §3.3 预注册复活条件挂账;v1 栈(非活路径)投影语义换核(里程碑地板不再产自供给,D-24/M55 语义由峰值级+息引擎前置近似承担,如实记档);批 3 后验证队列基线带重定(w630 协议 §6 交接:off 臂分布 [p5,p95])。
- 验证:cw 域全量 3071 绿(W635 收口后终版);新批锁 `test_cw_w633_migration_b3`(哨兵/排程四触发与禁升/预算契约/应急带穿透+血预算带拒付层兜底/R3 驱逐);行为基线 digest 重锚(c13c365b…,批 2 末 93ca26cc…);批 3 专属 A/B(w630 协议,off=03dcf22d)为转正判据,判据判前锁。
