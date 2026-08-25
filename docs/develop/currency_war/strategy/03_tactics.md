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

组合动作保留四项板上行为(DeployBench 内:换血/同角色去重/前排保证/cap 门)——`_should_deploy`+`_pick_deploy_row` 不足以复现,全原子切换会静默回归。部署槽位上限实测读取(财富宝钻 +1 随环境变,不硬编码)。**deploy 围栏**(配方饥饿期非过渡件留 bench)= `_DEPLOY_FENCE` = RECIPE∪ENGINE 桥派生单一源(ADR-0226)。⚠️ 已知漂移(ADR-0261):op 侧 `_deploy_deterministic` 与 `cw_deploy_logic.select_deployments` 纯函数非同源——op 无 ignition 排序首键、且多 r288 配方底线门(列车≥2 且仙舟<3 拦列车件;纯函数无此门=sim 盲区),引擎件存量躺 bench 的生产机制在此,修复待裁决。

## 3. cw_plan:备战动作规划

**硬门贪心**(bench-full / gold≥0 / `LEVEL_MAX` 门内,选 eval-delta 最大的动作序列)+ **蒙特卡洛 D 牌**(`_refresh_expected_delta`:扣刷新金采样 shop 取最优买+deploy 均值 − base;采样 = 先按等级采费用(`REFRESH_PROB`)再按角色均匀采)+ **D 牌动态上限**(`_refresh_cap`,**定义在 cw_evaluate**、cw_plan 消费:常规基线,关键回合——P3/搜核心/HP 危险急救——放宽;奖励节点收紧;拿刷新减费策略再提)+ **level_plan 硬 gate**(level_up + afford 直接执行,非纯贪心 delta;破息窗提案走 **LevelUp 总成本门**——clicks×单击价升不完不提案,ADR-0223)+ **腾席链**(deploy 空位 > 卖杂件(off-target,ADR-0274) > 升级扩容(boss 轮禁 + 真缺人口前置 + 息引擎前置,ADR-0274) > 卖最弱保 3合1 件 > Defer)+ **两阶段 refresh**(刷新后 shop 未知,重 OCR 再 plan)。boss 关前不攒息 + 刷牌放宽(ADR-0128)。XP 单击价 = flat-4(`XP_CLICK_COST_FALLBACK`,OCR 通道 stylized 不可检,ADR-0275)。

**P1 r5+ 决战窗**(接管 economy 分派;旧 LineStrategy 语义,ADR-0336 后由 decision_v2 纪律族 boss_breaker 承载——**W119/ADR-0347 起 boss 窗改节点图口径**(`boss_window_active`:node_type 为主,P1 r≥9 只作缺读兜底),P1 r5-r8 非 boss 节点不再入窗):成型检查点(`p1_formation_target`,轮窗常量 `_P1_FORMATION_TARGETS`/`_P1_FORMATION_ROUND_EDGES` 见 cw_line_defs,ADR-0225/0241)→ boss_breaker(板面集中买 + 配方围栏:recipe_tier<BASE 时只买 RECIPE∩板面,ADR-0221/0225)+ 买牌守卫 copies 星级加权(ADR-0224)。买入标签链含 **engine_seed 放行通道**:P1 未持有的过渡体系阵营件(TRANSITION_TRAITS 键,含 flow 羁绊)金够即买,与 seed/pair 门并行、地板语义调用方保留;bench 满员不触发(容量门,ADR-0267)。追级(LevelUp)在 boss_breaker/追赶两窗加**息引擎前置**:lv≥5 且未曾满息且花完 <50 不提案(曾达满息 latch ∨ 花完 ≥50 放行;lv<5 过渡成型基线豁免,ADR-0266;decision_v2 侧该门已收编 EV 总账,见 ADR-0347)。

**同轮买卖互斥**(ADR-0267;decision_v2 时序语义见 ADR-0328):round-scoped 已买集/已卖集(`session.v2_round_bought`/`v2_round_sold`,按 `(plane, round_num)` 换轮重置)——**登记点=动作采纳处**(arbiter 主循环/补偿趟/carry_gate/演进事务卖件采纳即登记,非趟尾统一回写;决策域对齐执行域:arbitrate 基于前置动作 simulate 后的状态裁决,消除 SellBench 槽位语义漂移卖错件)。**守卫快照源=working**(`same_round_mutex` 的 SellBench 分支与 index_drift 同读 arbitrate 内逐采纳推进的工作态,ADR-0337——演进腾空槽+同趟买入同名回填后,按卖动作执行时的真实目标卡裁决「同轮已买」,不再读 exec_state 快照短路放行)。同趟内买过的卡名,四条卖通道禁卖(3合1 让位豁免:同名副本星级加权 ≥3 的冗余件放行);对称臂:卖通道提案即时入已卖集,engine_seed 对集内卡名禁买(防同 call 卖→买回)。拆「engine_seed 买→卖通道卖→再买」永动机(bench 满员态段间互踩,自由批 F1);先卖后买不同名的同轮序不受限。**engine_seed 年龄豁免**(ADR-0289 §5/ADR-0294 件1)补跨轮窗:采纳处把 reason=engine_seed 的存活提案登记进 `session.v2_seed_bought`(char_id → (轮键, 同轮份数)),买入 ≤2 轮的种子在全部卖通道不进可卖集(种子归零=白烧预算;同轮同名 ≥2 份=3合1 素材语境豁免;锁:买入 r=N → r=N+1/N+2 卖不选、r=N+3 可卖)。**卖侧唯一体系引擎守卫**(ADR-0373):四过渡体系件(TRANSITION_TRAITS 三羁绊,全羁绊口径)在其体系**在手件数**(bench∪deployed 逐件计)≤ tier 时不进任何卖件通道(谓词 `discipline.sole_engine_sell_blocked`,挂 `_sell_tag` 与 `sell_priority_key` 两处=四卖件通道单点全覆盖;owned>tier 冗余件照旧可卖)——修「演进换线把旧体系件下场到 bench 后被 off_target 当死库存卖出 → 体系引擎永不回场」(S2 恶化谱系;[31] 引擎件是方向件非填充件)。

**carry 腾位门**(ADR-0280):`_carry_bench_gate` 挂 economy/boss_breaker/war 三买通道尾——P1 r≤`_CARRY_GATE_MAX_ROUND`(=7,收益域:r8-r9 miss 无差异;r9 boss 轮不触发)锁线局,carry 在店+金足(不破调用方地板)+bench 满(≥9)+零 off-target 可卖时,**降保护集卖最弱件再买**(reason=`carry_gate`)。「最弱件」弱序=非保护件 > 非当前线件 > 非桥件 > 副本冗余(镜像 `_copy_swap_useless` 保留判据);3合1 完整份(星级加权 copies==3)不腾;**合成份缺席场冗余**(absent_mergeable:该角色上场份缺席+架内星级加权副本 ≥2,卖 1 份仍留副本)与超上限冗余(>3)同列最弱级;卖出件入 `v2_round_sold` 同轮不回买。根因:保护集(双桥池全名单+锁线名单)窒息卖通道(批⑯ F3),强制买已证零效应(批⑯ F4)。腾位卖出同走 engine_seed 年龄豁免(ADR-0294 件1):窗内种子不腾——唯一可卖=种子且 bench 真满时兜底放行(不腾则 carry 死锁,豁免让位给 carry)。decision_v2 载体落点 `carry_gate_actions`:carry=意向核心(`intention_core`),保护集=**意向线正料派生**(core ∪ shared ∪ 替班 ∪ 引擎件,非 `v3_hoard` 全集;弱序与豁免语义同上,ADR-0314)。

**decision_v2 纪律族:掉血报警梯度**(strategy_v4 点4/点12;ADR-0313):`BloodAlarmTracker` 三臂(连续战斗失败 / 最近 3·5 个**战斗节点**累计掉血)激活时按处置梯度行动——①自然补强窗(窗上界 `BLOOD_GRADIENT_NATURAL_BATTLES` 个战斗节点,`mode='economy'` 不弃息)→ 窗耗尽或血边际低于 `BLOOD_MARGIN_LOW_HP` → ②弃息 D 保血(war+硬节点放行 refresh)。三臂窗口单位=战斗节点计数器(非战斗节点不计入不重置),跨位面全臂重置。**报警不是 ALL IN 的触发**;位面末最后一战(`plane_last_battle`)的 ALL IN 授权在报警态下同样开通(授权来自位面末,非报警)——`allin` 是唯一清零地板的路径。「来牌顺不顺」([19]③)未消费(定性变量,声明欠账挂实机语料)。

**decision_v2 评分活性(ADR-0332;P1 boss 转化)**:评分的「停手」=仲裁器对买候选的 0/负分拒绝(评分侧无成型停手语义;显式停手门见 ADR-0343);P1 破息窗(r≥5)的评分活性两修——①**息崖平滑**:买入跌破 50 满息平台只付真实档位息损(非全平台消失),消除与 boss_breaker 地板(10)授权的双重计罚;emergency([18] 不为苟住破息)与经济态([17] 平台)的 -25 语义不变;②**成型补充偏置**:未成型(引擎<2)时引擎件候选的 0/小负买入顶正(常量 `forming_bias`/`forming_bias_val_max` 在 registry)——成型后偏置关闭=停手攒息([13])。

**decision_v2 经济授权(ADR-0347;经济循环总模型步②「切授权」)**:常态经济行为由**相位**(FORM/HOARD/SPEND 派生量,W114 步①上线)驱动——form_ok 判据分两支:意向锁定=三件套(见成型停手门段);**意向未锁兜底局=结构判据**(ADR-0353:r≥`phase_fallback_min_round` ∧ 有效体系数≥`phase_fallback_min_engines`,有效体系数=四过渡体系达成数 `_engines_count`(deployed 口径)+`hp_charge_stack` 型全局累积角色豁免(上场 2★ 计 1,W127 字段消费)——语义=「板面真收敛到 ≥2 过渡体系」即 transition_combos「两两组合=过渡成型」;`form_score` 为纯遥测观测不进判据);地板族=FORM→`form_floor`(保险丝,Q1 四档 sim 对照待标定)/HOARD=SPEND→`interest_floor`(覆盖态优先序不变:应急/boss 窗/war 先于相位);跨档消费走 **EV 授权**(`interest_rule`:V=层3分剥离息分量,**买候选取 max(层3分剥离息分量, 组合跳变金账 `bd['form_gold']`,ADR-0352)**——引擎整数档跳变按全额跳变金、未跨档按进度增量×下一级跳变金(与 V_D 收益侧同式同源,C 同视界 R);C=跨档数×跨位面剩余节点,**买侧用回档折中口径 min(R, `interest_recovery_rounds`)**(一次性买按 P6 回档账辖;刷新保持平面 R 上界=P5⑤ 退化输出,升级平台账口径不动);[11] 同档/1费/满息结余特例保留);**P1 早期新件买入门(ADR-0372)**:FORM 相位地板拒绝前的买候选放行例外——轮级窗 `discipline.p1_early_gate_open`(P1 ∧ 派生配方对 `cw_intention.p1_early_pair`,**未锁形态期同样派生** ∧ 未持有 distinct 对成员 ≥ `p1_early_min_missing` ∧ bench 余槽 ≥1)∧ 逐笔「买入后同息档」([11] 逐字口径,跨档仍走 EV 授权)∧ 单轮 ≤`p1_early_round_cap` 笔 ∧ 同名/刷新不辖(`registry.p1_early_gate_enabled` 开关,auth `p1_early` trace);应急/boss/war 纪律态地板不受其影响;升级走 **EV 总账**(`ev.levelup_ev_authorized`:[33] 人口位 / DP 花费授权(平台未破)/ 静态平台账——[12] 息引擎门与 E6 latch 收编退场);**DP 接线**=v2 栈首次真实消费 `cw_horizon` 解(轮缓存 `session.v3_dp_posture`,遥测 dp_posture 字段);boss 窗统一节点图口径(`boss_window_active`,轮数只作 node_type 缺读兜底);「经济过热」类环境的 reward 节点按**低危战斗**处理(扑满守卫,ADR-0348:战斗向刷新理由开放+地板不降——扑满不掉血,目标=伤害阵容拿奖励)。

**decision_v2 三通道调度(ADR-0349;经济循环总模型步③「切调度」收口;P2 段 V_D 修法 ADR-0361)**:买/升/D 三通道竞争同一笔金——**D 候选批口径化**(`scoring.vd_refresh_score` 金账:收益=核心 2★ 完成的成型跳变金值(rung Δ×跨位面 R+胜率跳变×掉血×HP 金价,registry 单一源)/成本=`expected_refreshes_for_card` 批口径×刷价;目标=锁定线具名核心且已开张;**概率窗二分**=level_plan goal 说 level_up 时 D 让位([3]);**P2 段(plane≥2,ADR-0361)**:窗二分改消费 DP `refresh_budget` 授权(「升级+D」=并行预算;预算 0 仍让位,DP 异常回退 level_plan 门),成本换决策成本口径 `C_dec`=Δinterest×min(R,`vd_p2_recovery_rounds`)+ρ·s(P11:溢余段面值高估≥20×,[17] 溢余即花)+预算硬界 批口径刷金≤g−`boss_floor`,收益换存活口径(`vd_p2_loss`/`battles_left_p2` state 槽序表推导);A/B 通道 `vd_p2_enabled`;**P1 pair 缺件找牌通道(ADR-0369)**:P1 锁定帧(配方锁 `p1_pair`/①锁 `transition_pair`)缺件 ≥1 且金 ≥ `interest_floor`+刷价+缺件买价([3]「刷新后还能买之后保证 50 金」单次口径)时,pair 缺件账参与 V_D(`scoring._vd_p1_pair`:收益=下一档引擎跳变金值,e_cur≥2 无对象;成本=E₁×刷价,E₁=当前等级刷 1 张缺件的期望刷新数——概率表即 [3]「到概率等级才 D」的载体,错等级账自然负;缺件取账最大者;A/B 通道 `vd_p1_pair_enabled`);core 通道(level_plan 窗/批口径)与 P2 分支不受辖,P1 分支逐位不动指 core 通道);**升级总账加省刷金项**(`ev.levelup_refresh_saving`=刷价×ΔE 批口径,k 放大,峰值以上为 0——P5 定理检验点②);人口位保险丝=可负担性(34 帧误拒修订,升级金检查单点在 ev,gold_floor 对 levelup 让位);refresh 附庸闸(轮界/金门/常量 EV/饥饿折扣/预算约束/成型找件通道)与**追赶态**整体退场(人口落后由人口位升级+概率等级窗+EV 涌现);war 模式与危机态的 D 与常态同账(标签集只管候选在场);扑满节点凑伤害 D 走 `piggy_refresh_ev`×`piggy_refresh_round_cap`(P8 上限)。

**成型停手门(ADR-0343;[13] 停手线显式化;W119/ADR-0347 收编 form_ok)**:层2 后置**动作级**步(`filters.formed_stop_active`+`filter_candidates` 尾段)——P1 ∧ r≥max(锁定线 `typical_form_round`,`formed_stop_min_round`)(comp 派生辖轮)∧ `form_ok`(谓词本体在 `decision_v2/phase`:意向锁∧`form_tiers` 全键满足∧核心**上场** 2★;无等级项;①锁局 P1(comp 锁)另要求体系对引擎数
≥`phase_fallback_min_engines`——[13] P1 验收仍是体系对,ADR-0367),丢弃全部 BuyCard 候选(应急态不豁免;levelup/refresh/卖/合装例外)。标志 `session.v3_formed_stop`→sim 账本(轮内 OR 聚合)/生产遥测 `formed_stop` 字段;`overflow_gold_zero_buy_streak` 检查器对成型轮重置 streak。开关 `formed_stop_enabled`(registry)。

**decision_v2 体系集中度(ADR-0333;板面散面收敛)**:候选层加**engine_seed
配方亲和过滤**(开关 `engine_affinity_enabled` 在 registry;判据
`_engine_seed_affinity` 在 candidates)——板面已有过渡体系未成型时,新体系
引擎件不生成 engine_seed 候选(散买断,语义=[20] 过渡是配方不是散买:
配方=体系内加法,先深堆已有体系再开新体系);**空窗**(板面无过渡体系)放行
(第一体系要开,[31])、**全部成型**(引擎≥2)放行(两两组合可开新体系)、
深化件放行;希儿系/非三羁绊件不辖。与 forming_bias(评分活性)正交:forming
管「买不买」,亲和管「买哪个体系」。新 sim 指标(板面集中度度量)纯函数在
`cw_line_defs`(`board_max_recipe_tier`/`board_recipe_faction_count`/
`board_total_faction_count`)。

**decision_v2 买侧通道锁定目标约束(ADR-0359;①锁局副方向 ∪ 见 ADR-0367)**:锁定帧(约束基准
`cw_intention.locked_buy_scope`=P1 配方对成员集 ∪ comp 锁定采购集 ∪ ①锁局过渡对成员集(ADR-0367,
`transition_pair`);空窗/
弱意向/降格=None 不辖)时,`line_opportunistic`/`bond_fallback` 买候选中
目标件 ∉ 锁定目标体系集者**评分降级**(常量 `off_lock_buy_penalty` 在
registry;末段施加,降级非禁绝——[31]④ 填充不变量保留,填充件让位目标件
而非禁买);位面末轮 boss 窗的非目标 opportunistic 件**直接拒**
(`final_fence`;目标件+填充+对件照旧)。应急态豁免([18]);开关
`buy_lock_constraint_enabled`(A/B 通道)。语义=约束「方向」:锁定后买侧
材料供给不再喂换档挤出(W147:挤出执行侧的保留序/deploy 围栏是另一批)。

## 4. cw_evaluate:局面评估

阶段键控加权(`_phase_weights`:HP 危险→保血 / P3→锁血 / 健康→平衡)+ `target_progress`(距 form_tiers 剩余进度,不与 synergy/char_quality 三重计分)+ optionality α(t) 承诺-期权混合 + `transition_tempo`(过渡期节奏项,ADR-0140)+ streak 项(只计连胜)。消费 DP 姿态(`cw_horizon`)、审判层(`cw_line_tribunal`)、期望进度线(`cw_progress_curves`)、经济层(`cw_economy`)。

## 5. cw_bundle:回合内联合行动束

历史头号杀手的另一面:单动作贪心在「买 A 卖 B 升级」联合更优时逐项看不见。bundle 把**回合内联合行动束**作为优化单元整体估值(ADR-0156);`cw_plan` 消费。

## 6. 装备执行(EquipAll)

装备机制 = 拖拽(装备区 owned → 角色槽;点「装备推荐」只弹列表非一键穿)。EquipAll 按 `key_equips` 有序优先分配(carry 先拿,合成优先级 = 合成首选数据);狼狩线受穿戴纪律约束(物品栏真积压报警,不为狼狩牺牲合成规划,M16 用户修正版);拆装扳手/冶金炉/投影仪等工具域动作在动作全集但决策函数按需实现。P1 阶段**合成保留组件不入穿戴池**(`cw_synthesis.RESERVED_COMPONENTS` 单一源,key_equips 豁免;组件留 owned 待合成,ADR-0265)。

## 7. 边界

- plan 是纯函数(可离线测/可对拍,`cw_plan_replay_audit`);执行器负责坐标与验证。
- 战斗过程不可介入(AV 限时自动打),战术全部发生在备战期。
