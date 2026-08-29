# 01 姿态与经济(跨期决策)

> 「钱该花还是攒、什么时候升、什么时候刷」由**确定性预算核**统一回答(义务模型 + 排程查表 + 预算式刷新;原 DP 求解器已退出生产路径,历史:静态 NodeGoal 表 → DP 切流 ADR-0208 → 预算收权,ADR-0465;等级节奏权威 = 用户口述,ADR-0126/0128)。本篇:`cw_plane_table` / `decision_v2.economy_cycle` / `cw_effect_ledger` / `cw_economy` / `cw_first_passage` / `cw_progress_curves` 的语义。

## 1. 预算收权核:三个标量的确定性供给(ADR-0465)

**是什么**:原 DP 求解器被生产消费的全部投影只有 3 个标量——「该不该升」「刷几枪」「花还是攒」——每个都有机制常量直算式(W615 §2 R1-R4 规则集)。生产者单一址 = `decision_v2.economy_cycle` 两个接缝:

- **`schedule_upgrade(state, session) -> bool`(排程判据)**:触发 = ①人口位(cap 满 ∧ bench 有成型件等上场,[33])或 ②概率级(目标核心峰值级 > 当前级 ∧ 息引擎已立 g≥息线,[3]+[12]);禁升 = 息引擎未立不追级、淘金客姿态升级通道退役(`cw_investments.refresh_invest_active` 单一谓词)。**预告态契约**:排程只回答「要不要开始攒」,不以当帧可负担为前置(付得起是执行层 `ev.levelup_ev_basis` 可负担性入口门的事)。峰值级查表 = `cw_plane_table.peak_refresh_level`(REFRESH_PROB argmax,并列取高档)。目标核心解析:意向锁定核心 → 兜底 comp 核心 → 缺省 3 费。三处共调同一函数(R4 单一址):R* 储蓄分量、arbiter 金地板授权、EV 升级授权②臂。
- **`refresh_ev_budget(state, session) -> int`(刷新预算)**:`min(6, ⌊(g−R*)/刷价⌋, ⌈−ln(1−q)·E_find⌉)` 前置塌缩带归零——只花溢余(W610 spec 预算式;6 刷帽单一源 = REFRESH_ROLL_CAP)。概率校准分量(ADR-0475):锁定核帧塌缩带(refresh_prob 当前级/峰值级 < `registry.omega_collapse_ratio`)→ 0;有望帧帽按目标可寻性收紧(q = `registry.refresh_find_quantile` 真分位,E_find = `cw_shop_odds.expected_refreshes_for_card`;概率单一址与分配器 Π_refresh 同源互指)。兜底链空帧豁免归零判据(D1「空帧不缩供给」契约优先)。**合法 0 帧**:g≤R* 常态帧、应急/血预算停手帧(`filters.is_emergency` 单一源)与塌缩带归零帧三类——0 流过 scoring P2 窗判据(`>0 即窗开`)与存息准入门;定向刷新授权是独立车道不并入(其对塌缩判据的同判据辖接线挂账见 ADR-0475)。
- **轮姿态载体**(`decision_v2.posture.Posture`,字段形状与旧 DP 姿态逐位同构):由 `ev.build_round_posture` 装配 + 遥测标签词汇表 v2(`升级`/`升级+D<刷数>`/`+D<刷数>`/`存息`;经 release 包装后恒 `release`),`ev.round_posture` 轮缓存同轮共用。确定性核恒有定义,旧「查询异常 → None → 各消费点保守回退」级联面不存在。

- **R\*(储备线)与义务**(ADR-0445/ADR-0463,原样):`R* = 息线(interest_cap×10) + 窗口 h=min(3, 位面末前轮数) 内排程升级费`;溢余 `(g−R*)+` 经义务 `min(溢余, C_t)` 进 release 预算;存息准入门(E1)辖「溢余且未被 flip 覆盖」的帧(预算函数口径,W611 退出链),零预算 release 指令 = 容量不足的合法结转。
- **标定表/真值归属**(`cw_plane_table`,原 `cw_horizon` 的非 DP 面):位面轮数真值 `nodes_of_plane`(P1=9/P2=7/P3 进表自适应,ADR-0366)、日程几何(`schedule_of`/`plane_offsets`/`plane_end_slots`)、升级费用次数(`clicks_to_level`)、息闭式(`interest`)、损血先验表(`HP_LOSS_MU`,ADR-0183 单一源)、P2 两态胜率映射(`p_win_p2`)。DP 世界模型(难度曲线/损血递推/平局扫描序)随模块退役,git 历史为 prior art。
- **消费端**:`cw_economy`(spend_mode 档位经 `get_node_goal` 标量投影,唯一档位源)、`cw_comps`、`cw_evaluate`、`cw_plan`、`cw_state`、`cw_telemetry`(影子记录)、`decision_v2`(arbiter/scoring/posture_release/ev)。
- **维护红线**:排程/预算判据改动必须走 sim A/B(w630 协议式:升级时机分布为硬守卫);三处共调单一址禁第二实现。

## 2. cw_effect_ledger:既持效果台账

「已持有投资卡的效果」结构化三层:现金日程(calendar)/ 机制突变(mutations)/ 免费额度(budgets),按四象限路由(时点金/规则改/选卡权/资产)。消费面 = 经济效果查询(`cw_investments`/`cw_economy`);原 DP 台账注入重解与指纹随 DP 退役。效果分类知识与可建模边界 → [game/research/invest_effects](../../../game/currency_war/research/invest_effects.md);落地与纠错 → ADR-0202/0205。

## 3. cw_economy:经济纯函数层

金/经验/息/刷新成本的纯函数模型(三层共享底层,economy/evaluate/plan 均消费):单击经验模型(单击 XP 常量 `XP_PER_BUY`、门槛自动升级溢出结转,ADR-0129)、重复性效果折算(ADR-0142)、spend_mode 档位(由预算收权核经 `get_node_goal` 标量投影导出,**唯一档位源**;`NodeGoal.refresh_budget` 随投影下传,与评分层合并语义单一源 = `decision_v2.posture_release`)。

## 4. 息引擎与例外窗口(语义)

基线是用户口述的人玩节奏(权威,[game/research/user_playstyle](../../../game/currency_war/research/user_playstyle.md)):

- **50 金息引擎**:利息(息律常量 `INTEREST_THRESHOLD`/`GOLD_CAP_INTEREST`,用户口述「每 10 金 1 息、50 封顶」)是默认态;前期 snowball 到 50,中期维持吃息升人口,后期血危花光。
- **无损购买窗口**:金低于无损窗口上限(`cw_plan.NO_LOSS_GOLD_CEILING`;1 息档内)买过渡件不损息还压缩牌库——攒息不拦无损买。
- **连胜破息门**:连胜 ≥ `WIN_STREAK_BREAK_INTEREST` 时破息提质量维持连胜(断连胜亏 > 利息亏,ADR-0117);货币战争**无连败补偿,只计连胜**(ADR-0128)。
- **奖励节点守卫**:必胜节点(无战斗/连胜白拿)刷牌的战斗向理由全关(`_refresh_cap` 收紧)。
- **血量换经济边界**:血危时经济让位保血,但保留重生基数(旧 `line_strategy._REBIRTH_FLOOR`,ADR-0336 后常量随删;decision_v2 的 emergency 地板语义见 [0313](../decisions/0313-blood-alarm-semantics-final.md))。

## 5. 压缩买链(1 费免费牌池操纵的执行语义)

地基:1 星买卖净 0、1 费 2 星合成再卖也净 0(cost≥2 才有 1 金手续费,`cw_state.sell_refund`,ADR-0121)→ **1 费各星 = 零成本压缩牌库**。plan 中的压缩买链(`_compress_release` 纯函数 + 扫尾)按此买同费非目标 1 星卡压缩分母、目标到手后再释放。量化幅度与前提 → [game/research/economy §3](../../../game/currency_war/research/economy.md)。

## 6. cw_first_passage:目标函数层

全栈优化目标的单一源:**首达生存概率**(P(reach plane_k) / P(win))+ 风险姿态三区律——替代各处各自为政的「均值计价」(诊断与设计 → ADR-0161)。`cw_state` 消费;P(win) 供给跨局分配层。掉血分布 μ 的位面维:P1 = `cw_plane_table.HP_LOSS_MU` 现档(P1 不走 P2 标定);P2+ = 两态同构 `(1−p(rung(tier)))·L_cond_mix`(registry `p_win_p2_by_rung` + `p2_cond_loss_table`,P3 别名 P2);无本地位面乘数自由度(W443 双源合一,ADR-0440)。`effective_hp_threshold` P2+ 阈值 = base × `plane_hp_ratio`,五处策略消费点(economy 止损/evaluate 保血/comps 与 default_strategy 保命转型 0.75×/plan 刷新帽)全部经该单口消费。

## 7. cw_progress_curves:期望进度线

「健康线在节点 t 应有的等级/板强」期望侧基准编译器(ADR-0171),供 `cw_line_tribunal` 的「时间线掉队」通道做对照。

## 8. 边界

- **不预测战斗结果**:掉血模型是期望近似(升级方向 = 换实测桶分布,属设计演进,决策时另立 ADR)。
- 姿态回答「花钱节奏」,**不回答**买哪张/上谁(战术层,03)。
- 电表倒转(砂里淘金)流与优势布局钻钞 farming 不建模(ADR-0211)。
