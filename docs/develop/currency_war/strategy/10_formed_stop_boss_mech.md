# 10 成型停手目标件白名单 + boss 轮特殊机制族裁决(W255;ADR-0410)

> 本篇 = as-built 语义:①成型停手([13])的「停」辖什么、放行什么(目标件
> 白名单);②决策栈内 boss 轮特殊机制族的节点无关化裁决结果。数值一律指
> registry 常量名,不写值。

## 1. 成型停手语义([13] 正确口径)

口述权威:`user_playstyle.md` [13]/[21]/[22]——成型停的是**过渡件**;
**目标阵容件照买照囤**([21] final 买而不上/[22] 有用先囤正是成型后阶段
的正常行为)。旧实现(Archived,ADR-0410)对成型停手态丢弃全部 BuyCard
候选,把 final 囤件一并饿死 = 语义过宽。

**新语义**(filters.formed_stop_active + filter_candidates):

- 停手判定五项不变:P1 ∧ r≥max(锁定线 `typical_form_round`,
  `formed_stop_min_round`)∧ form_ok ∧ 末窗承接门(缺口>0 不停手)。
- 动作级后置步改为**分域拦**:成型停手命中时,BuyCard 候选仅当其买入名
  ∈ **目标件白名单**才被拦除之外放行;白名单外(过渡件/散件)照旧拒。

**白名单判据**(单一源 `filters._formed_stop_buy_allowed`):
买入名 ∈ `candidates._target_names(state, session)`——意向载体
(`session.v3_hoard.char_targets`,锁定/兜底各模式的囤货采购集)∪ 体系卡
引擎件(engine_char_names,[31] 三级梯队的目标层)。判据映射:[31]
目标件=最高优先级照买;非目标件([31] 填充/散件层)=过渡件,停手拒绝。
应急态不豁免的整体语义保留(停手仍拦应急强制买),白名单例外同样适用
于应急态前的候选流——即白名单在一切覆盖态下一致。

- 标志与观测面不变:`session.v3_formed_stop`;链日志行新增
  `'formed_stop_exempt'`(白名单放行的 BuyCard 行,True=放行),
  遥测字段 `formed_stop` 语义不变(轮级 OR 聚合)。
- 检查网联动(`cw_sim_checks.check_overflow_gold_zero_buy_streak`):
  豁免本身不变——成型停手轮若因白名单买了目标件,streak 自然被购买
  打断;纯零买停手轮的重置语义保持(合法攒息)。**另一处随修**
  (`check_levelup_interest_engine_gate`):合法授权面从 {pop_slot, dp}
  扩到 **{pop_slot, dp, static_ev}**——boss 禁令删除后 static_ev 臂成为
  末窗升级主授权臂,W123 的「该臂帧量级 0-1 保守计违规」校准已失效;
  无 auth 键的退化检测面不受影响。

## 2. boss 轮特殊机制族裁决表

[32] 定调(2026-08-27):消费有效性/腾席优先级**全程通用,节点无关**;
病例注已消解「boss 轮特殊化」。据此对决策栈的 boss 机制逐条三类裁决:

| # | 机制 | 现状 | 归类 | 处置 | 依据 |
|---|---|---|---|---|---|
| 1 | `arbiter.boss_levelup_ban`(约束链内)**禁令臂**:boss 窗内 LevelUp 一律拒 | constraints 表 slots ('slot','boss') | **c 删禁令臂** | 删除禁令分支——升级是否做交给既有 EV 总账(`ev.levelup_ev_basis`,[12]/[33] 单一裁决点;金账可负担性 after≥0 仍在);boss 窗地板(`_active_floor` → `boss_floor`)继续兜本金下限 | [32]:腾席优先级全程通用——升级 cap 当轮兑现与否是期望账问题([27] 投资变现),不是禁令问题;病例注明确「真病是升完没有能上场的强单位」,EV 总账 Population-bit 臂①已辖该病 |
| 2 | `_active_floor` boss 窗 → `boss_floor` 地板 | 地板族覆盖态分派臂 | **b 保留** | 不动 | 与 [32] 冲突仅在「禁花」方向,boss_floor 是低门槛(放花),语义 = 位面末战前本金边际(ALL IN 路径 `plane_last_battle` 清零由 discipline 承载);非节点特殊化 |
| 3 | `discipline.boss_breaker` / `assess_discipline` boss 窗 coverage='boss_breaker' + 连胜 EV 地板降档 | war 覆盖态 | **b 保留有据** | 注记归属 ADR-0410(判据全来自 [19] 连胜三态谱+[17],boss 只是触发语境之一,`_hard_node` 同构涵盖 encounter/battle-tail)——保留不改 | 攻略专题 [19]:高难节点连胜 vs 保息抉择,boss 是高难节点的实例;去掉反而违反 [19] |
| 4 | default_strategy `_boss_window` pivot 冻结(r70/r73RC1) | update_target 换线冻结窗 | **b 保留有据** | 注记归属 ADR-0410;冻结域含 P2r1(plane≥2 round==1),其理由(boss 前换线=丢成形板去追零进度新线,两局实证)独立于[32] 消费有效性条目;[23] 锁线纪律同向 | 属换线纪律(避免撕囤件),非消费有效性节点特殊化 |
| 5 | `registry.plane_last_battle`(=位面末最后一战)ALL IN 授权(discipline.allin) | 全局窗口谓词 | **b 保留** | 不动;ALL IN 是 [18] 口径原文点位面末时机,[32] 不推翻 | [18][28] 直引 |
| 6 | cw_observation boss 轮次门(gate_node_type `_BOSS_MIN_ROUND`) | 观测防误读 | **b 保留** | 观测层,非策略;防止把即将到来的 boss 标签张冠李戴 | 观测正确性,与 [32] 无涉 |
| 7 | scoring/sim 内 boss 窗预算硬界 `g − boss_floor`(V_D P2 分支)、scoring `_off_lock_demotion` 的 `final_fence`(末轮∧boss 窗拦非目标 opportunistic,W143/ADR-0359) | 各评分域引用 | **b 保留** | 消费 #2 同常量/末轮围栏(run17 直证 r9 四张零目标件买入;[31]④ 目标件+填充不辖)——依据独立于 [32] 消费有效性 | run17 直证/[18] |
| 8 | default 栈(direct 流)`cw_plan` 腾席链「升级扩容 boss 轮禁」(ADR-0274)与 `update_target` `_boss_window` pivot 冻结(r70/r73RC1) | 冻结栈语义 | **b 保留不改码** | default 栈为非决策主路(v2 四层为准);pivot 冻结属换线纪律([23] 锁线+两局撕囤实证),不是消费有效性节点化。若后续泛化到 v2,v2 侧对应物(scoing final_fence/evolve_final_freeze)已按同语义在位 | 本表 #4 |

小结:**#1 是唯一 c 类**(删禁令臂,EV 总账接管);其余全部 b 类(有据
保留,依据非 [32];无 a 类泛化件——[32] 本身已是全程通用的纪律文本,
代码侧不存在需要把它复制到其它节点的机制,#1 反向属「把 boss 特殊禁令
取消回归通用账」)。

**验证法**:
- 单帧锁(新):boss 窗构造帧中,满足 EV 总账人口位条件的 LevelUp 在
  开臂(registry boss_levelup_ban 删除后恒开,新语义)获接受;EV 总账
  不过(平台破/无人口位/金不足)的 LevelUp 仍拒且拒因走息引擎总账文案
  (非 boss_levelup_ban 文案)。
- sim 对照:A/B 臂省略(本批为无开关的单向语义修正——boss_levelup_ban
  在 registry.constraints 固定存在无独立 flag,A/B 无法构造关臂对照);
  以主客观测面批量前后对照(主客观测=成型停手轮目标件购买恢复数 +
  boss 轮 LevelUp 从 0→出现)代替。

## 3. 波及面(as-built 引用)

- 承接门 W227(filters.formed_stop_active 内 handoff_gate_gap 消费)不
  变;白名单只改动作级后置步内的 BuyCard 拦截面。
- 检查网 `overflow_gold_zero_buy_streak`:豁免语义不变;`levelup_interest_engine_gate` 合法授权面扩 static_ev(上节)。锁见
  test_cw_w107_formed_stop::test_checker_exempts_formed_stop_rounds
  (契约不变)+ test_cw_w255 新增白名单语义锁。
- 遥测:`DecisionTrace.formed_stop` 字段语义不变;过滤链日志新增
  `formed_stop_exempt` 键(producer 端 filters.log,consumer 端暂无强依赖)。
- registry:constraints 元组内 'boss_levelup_ban' 名字保留(名字空间稳定,
  审计矩阵 ('slot','boss') 格消费它);行为变化集中在 arbiter.
  _check_constraint 该分支的 boss 禁令臂删除。审计矩阵格不动(槽位资源
  ×boss 态的约束仍是『升级要过 EV 总账』,非空格)。
- 测试波及:sr-od-test 旧锁 test_cw_adr0291(constraints 名单集)不受
  影响(名字保留);W52 remediation 补偿测试与 W194 稳态组守卫测试
  按 ADR-0410 新语义修订(docstring 记旧断言过期原因:boss 轮 LevelUp
  改走 EV 总账;合法面锁迁移至 test_cw_w255)。
