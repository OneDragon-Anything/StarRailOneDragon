# 03 战术执行(备战层)

> 备战画面内「下一步做什么」的执行架构:观察驱动单步决策环(PrepDirector,ADR-0123)+ 战术规划(plan/evaluate/bundle)。框架与策略分离:环是框架(不含玩法判断),「下一步做什么」全部是策略(CwStrategy 钩子,07)。

## 1. prep_director:备战决策环(框架)

两层环的内环(外环 = battle_loop 屏幕级路由)。循环:`observe(轻/重分层) → strategy.decide_prep_action(obs) → execute(带完成验证) → 再观察`;环出口 = StartBattle(执行且验证成功)。替代历史固定流水线(收球→买牌→部署→装备)——腾席/收球/事件时序由观察驱动。

**框架不变式(F1-F8,策略可依赖)**:单步契约 / 观察真实(reader 产出,shop 开关互斥由框架校验)/ 动作合法域校验 / 验证与防护对策略透明 / 出口兜底(策略失能强制出战)/ 环不污染策略实例(跨步意图走 session)/ 可换策略 / obs+action 落 telemetry。

**防死循环三层**:动作验证失败 → 同动作连败达 `PrepDirector.FAIL_TO_RECOVER` 触发恢复原语(按已知弹层分型)→ 恢复无效 BailToOuter(环让位外环)或本环屏蔽该动作实例;环级连续零进展且恢复试尽 → 强制出战;外环由对局步数预算兜底。`cw_reconcile` 在环入口对账 tracking。

## 2. prep_actions:原子动作全集(以 `prep_actions` 代码为单一源)

| 域 | 动作 |
|---|---|
| 奖励 | ClickSpheres / OpenBox / PickBoxCard / **OpenTome**(典籍开卷,策划事件链) |
| 席位 | SellBench(身份感知,物理槽位)/ SellDeployed / DeployMove(腾席链) |
| 升级 | LevelUp |
| 战斗 | StartBattle(含未达上限确认勾选) |
| 观察管理 | EnsureShopOpen / EnsureShopClosed(gold 只在开态、HP 只在关态可读) |
| 控制流 | DeferSpheres(球留置,环级计数)/ BailToOuter |
| 组合(过渡) | RunBuyPhase(BuyShopCards)/ RunDeploy(DeployBench)/ RunEquip(EquipAll) |

**注意分层**:买牌内的刷新(RefreshShop)与买入(BuyCard)是 `cw_state` 的 **sim/决策层 Action**(plan 产出、`cw_plan`/`cw_sim` 消费),由 RunBuyPhase(BuyShopCards op)在执行层落地,不是 prep_actions 类;穿戴/合成同理——装备执行走 RunEquip(EquipAll op,§6),合成决策在 `cw_synthesis`(op 层暂无独立动作)。

组合动作保留四项板上行为(DeployBench 内:换血/同角色去重/前排保证/cap 门)——`_should_deploy`+`_pick_deploy_row` 不足以复现,全原子切换会静默回归。部署槽位上限实测读取(财富宝钻 +1 随环境变,不硬编码)。**deploy 围栏**(配方饥饿期非过渡件留 bench)= `_DEPLOY_FENCE` = RECIPE∪ENGINE 桥派生单一源(ADR-0226)。

## 3. cw_plan:备战动作规划

**硬门贪心**(bench-full / gold≥0 / `LEVEL_MAX` 门内,选 eval-delta 最大的动作序列)+ **蒙特卡洛 D 牌**(`_refresh_expected_delta`:扣刷新金采样 shop 取最优买+deploy 均值 − base;采样 = 先按等级采费用(`REFRESH_PROB`)再按角色均匀采)+ **D 牌动态上限**(`_refresh_cap`,**定义在 cw_evaluate**、cw_plan 消费:常规基线,关键回合——P3/搜核心/HP 危险急救——放宽;奖励节点收紧;拿刷新减费策略再提)+ **level_plan 硬 gate**(level_up + afford 直接执行,非纯贪心 delta;LineStrategy 破息窗提案走 **LevelUp 总成本门**——clicks×单击价升不完不提案,ADR-0223)+ **腾席链**(deploy 空位 > 升级扩容 > 卖最弱保 3合1 件 > Defer)+ **两阶段 refresh**(刷新后 shop 未知,重 OCR 再 plan)。boss 关前不攒息 + 刷牌放宽(ADR-0128)。

**LineStrategy 的 P1 r5+ 决战窗**(接管 economy 分派):成型检查点(`p1_formation_target`,轮窗常量 `_P1_FORMATION_TARGETS`/`_P1_FORMATION_ROUND_EDGES` 见 cw_line_defs,ADR-0225/0241)→ boss_breaker(板面集中买 + 配方围栏:recipe_tier<BASE 时只买 RECIPE∩板面,ADR-0221/0225)+ 买牌守卫 copies 星级加权(ADR-0224)。

## 4. cw_evaluate:局面评估

阶段键控加权(`_phase_weights`:HP 危险→保血 / P3→锁血 / 健康→平衡)+ `target_progress`(距 form_tiers 剩余进度,不与 synergy/char_quality 三重计分)+ optionality α(t) 承诺-期权混合 + `transition_tempo`(过渡期节奏项,ADR-0140)+ streak 项(只计连胜)。消费 DP 姿态(`cw_horizon`)、审判层(`cw_line_tribunal`)、期望进度线(`cw_progress_curves`)、经济层(`cw_economy`)。

## 5. cw_bundle:回合内联合行动束

历史头号杀手的另一面:单动作贪心在「买 A 卖 B 升级」联合更优时逐项看不见。bundle 把**回合内联合行动束**作为优化单元整体估值(ADR-0156);`cw_plan` 消费。

## 6. 装备执行(EquipAll)

装备机制 = 拖拽(装备区 owned → 角色槽;点「装备推荐」只弹列表非一键穿)。EquipAll 按 `key_equips` 有序优先分配(carry 先拿,合成优先级 = 合成首选数据);狼狩线受穿戴纪律约束(物品栏真积压报警,不为狼狩牺牲合成规划,M16 用户修正版);拆装扳手/冶金炉/投影仪等工具域动作在动作全集但决策函数按需实现。

## 7. 边界

- plan 是纯函数(可离线测/可对拍,`cw_plan_replay_audit`);执行器负责坐标与验证。
- 战斗过程不可介入(AV 限时自动打),战术全部发生在备战期。
