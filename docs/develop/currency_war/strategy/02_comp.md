# 02 阵容选择(战略层)

> 「这局打什么阵容、何时定型/转型、跨局怎么分配」的语义。本篇:`cw_comps`(COMP_LIBRARY + select_comp/pivot)/ `cw_transition`(双轨过渡)/ `cw_line_tribunal`(审判层)/ `cw_run_allocator`(跨局分配)/ `cw_evolution`(阵容演进引擎,§10)/ `cw_intention`(终局意向分层,§11)。玩法证据 → [game/research/plaza_methodology](../../../game/currency_war/research/plaza_methodology.md)(M1-M16);单套打法叙事(入场/退场/counter)→ [game/research/final_comps](../../../game/currency_war/research/final_comps/README.md)(终局阵容十类深读,单套 comp 知识单一源)。

## 1. COMP_LIBRARY:阵容注册表(数据模型)

`cw_comps.COMP_LIBRARY`,数据源 `cw_plaza_comps`(plaza API 生成,勿手编)。`Comp` 关键字段语义:

- **`factions` vs `flex_factions`**:核心羁绊(成型判定用)与弹性羁绊(亲和不断判)二分——M2「核心锁死 × 弹性填充」;评估板面时朝弹性羁绊铺**不算 spread**。
- `core_chars` 核心角色;`shared_chars`/`transition_chars`(跨线共享/过渡衔接件);`form_tiers` 各羁绊成型档;`level_plan` 等级→动作曲线(**`star_goals` 是 `LevelGoal` 字段**——按等级段给目标星的追星曲线,缺省 = `default_star_goal` 费用档规则,M6 升星经济学);`key_equips` 关键装备(有序,合成优先级);`form_difficulty` 成型难度(easy/medium/hard,选型关键维度);`countered_by_bosses`/affix 双向(克它的与利它的词缀);`mechanic_attributes`(机制属性,与 `MECHANIC_COUNTERS` 同本体);`char_positions` comp 特定站位覆盖(ADR-0139);`weak_planes` 保命 pivot 位面过滤(ADR-0174)。
- P1 双轨期的「目标阵容」另有**过渡配方伪 comp**(`cw_recipe.RecipeComp`,README §模块地图):双轨期 plan/deploy 拿配方伪 comp,配方完成度即 P1 胜利条件;终局线 P1 内冻结换线(定义型 augment 除外)。

## 2. comp_score 与 select_comp

`select_comp(state, score_ctx, config)` = argmax comp_score,候选打分用**纯先验**(无观测,评已 commit 阵容才用观测——双签名拆分,防逻辑错位)。comp_score 结构 = 成型进度(主导,可成型优先)+ boss 契合 + 环境契合 + 装备契合 + 强度先验(权重常量在 `cw_comps`);词缀经 `AFFIX_MECHANIC_MAP` 归一进 `mechanics_fit`(克/利双向:同一词缀对不同阵容方向相反,M15),boss 侧有开局先验冲击乘子。**select_comp 每回合跑**(商店强随机 + 投资选择在位面中进行)。

## 3. commit 粘性与 prefilter(防散架)

历史头号死因 = board 全程 spread 弱阵 → P2 秒死。机制三件:

- **commit 粘性**(`target_committed` 单一判据):form_progress 越过 commit 阈值后 target 强粘,仅更强信号才转(maybe_pivot);**已成型豁免**(成型后掉血 → 补装备/星级,不换阵容,掉血归因三分法:成型中继续组建 / 成型后补强 / 凑不齐才转)。
- **买侧 prefilter**:commit 后拒 off-target 散买(改刷新找 target),但**放行过渡骨架与通用辅助**(组建期支撑,防一刀切饿死);早期未 commit 放行 tempo。
- **drought bail**:连续多轮无 target 进度 → 解除粘性重选(防 commit 锁死不可达)。

## 4. cw_transition:双轨过渡(P1 过渡包模型)

P1 同时持有**过渡框架包**与**最终线框架包**两条轨(ADR-0209):P1 半成型最终线打不过成型过渡包是七连败根因。`CommitSignals`(7 信号源)驱动何时收敛到最终线;P2-3 deadline 兜底;五人口早期结构。`cw_plan` 与 `default_strategy` 消费。

## 5. cw_line_tribunal:战略假设审判层

战略层假设(commit/pivot/drought 等)的**去留门**:每条战略线按证据(时间线掉队对照 `cw_progress_curves` 健康线/连败/成型度)判继续、降权或退出;`cw_evaluate` 消费(诊断与五族门设计 → ADR-0171)。

## 6. cw_run_allocator:跨局分配层

「这局打哪个臂(策略/阵容方向)」的跨局回答(ADR-0170):各臂 Beta 后验(先验来自 plaza 伪计数,封顶防幸存者偏差)+ Thompson 采样选择;`forbid` 方向盘 + forced 豁免;update 按位面进度分级奖励 × adherence 加权;**必死局回收**(P(win)<ε 时选方差最大可达臂采数据);指数遗忘。P(win) 供给 = `cw_first_passage`(01 §6)。`battle_loop` 每局开始消费。

## 7. 巨星选择(select_megastar)

巨星效果是**乘区**,绑定逻辑 = comp 引擎 × 乘法关系(非单属性键):选择序 = ① core 在阵绑定该角色 → ② `COMP_MEGASTAR_PREFERENCE` comp 级偏好表(前台单核族→星期日 / 暴击引擎族→知更鸟 / 战技点→花火 / 击破→大丽花|加拉赫 / 5费堆叠→黑天鹅)→ ③ 机械属性兜底 → ④ naive。执行在巨星节点 op(04)。

## 8. 转型成本与共享角色

pivot 重叠度(`pivot_overlap` = 共享角色重合度)调制转型信号阈值——换阵成本显式化;optionality(α(t) 承诺-期权时间衰减,与 commit 正交:α(t)/optionality 在 eval 奖 bench 上属 ≥2 comp 的通用角色,commit 在 maybe_pivot 管 target 粘性,ADR-0096)。

## 9. 边界

- COMP_LIBRARY 版本敏感(`version_tag`);数据源以官方 API 聚合为准,版本更新重跑生成器。
- 试用/本体/局外(M11)是可行性隐藏变量,GameState 暂不建模。
- 站位静态特例(`char_positions`)已建;动态换位(M12③)不建模。

## 10. cw_evolution:阵容演进引擎

「任何时刻、任何档位规模的阵容替换」的通用法则实现——过渡 1 档换终局 2 档、插件档换副羁绊档、插件换单卡,全部同构走同一入口,不为每类换法写特例。决策与取舍见 ADR-0319。

**统一入口四步**(`evolution_step`,任何阵容改进步动走这里):

1. `propose_upgrades`:枚举当前全部「可上新羁绊」机会,三个来源——体系卡注册表(`SYSTEM_CARDS`,体系卡→判据阵营→目标档映射派生自注册表字段)、COMP_LIBRARY 各套主档、当前板已有羁绊加深 1 档。意向同向(session 目标 comp)作 tie-break 加权,非一票否决。
2. `evaluate_upgrade`:三条件裁决,逐项可审计(`UpgradeVerdict`):
   - **① 效果判断**:新档成型投影 > 现状代理(「2 换 1 占优」的具体化;投影含再遇窗口件——缺口张内当轮店里可见成员)。评分权重是草案级代理,常量(`_TIER_WEIGHT`/`_CORE_BONUS`/`_ENGINE_BONUS`/`_CORE_ON_BOARD_W`)只在代码。
   - **② 核心校验**:carry 或替班核心在手。与①构成**发令枪交叉语义**:档齐核心未到 → 不拆过渡档;核心到档未齐 → core 上 bench 等档;**最后到齐的那个是发令枪**(综合裁决 = ①∧②)。
   - **③ 人口检查 = 信息位,不阻断**:摆不下也上(替换优先于人口保守——人口可随后续腾出,硬门会让换档死锁在低人口期)。
3. `execute_replacement`:生成**显式 `CompTransaction`**(整档替换一条事务,决策在执行前一次敲定):新档成员上场(核心优先)/旧档整档解除/被换下成员去向 = bench 保留优先(保回滚窗),bench 溢出才卖。模块不自己迁移状态,全部经 `cw_state.simulate` 应用与验证;ADR-0317 同名/代际守卫在事务收口统一生效;事务 reason 带 `evolve:` 前缀(旧行→新行)供审计。填位若拖垮事务原子性(simulate 拒收)→ 剥离 fill,另轮走常规填位。
4. `fill_gap_after`:数人口缺口,按**空位规则**填位——插件优先(能开新档 > 单卡效果 > 散件兜底)/替班核心例外(带自己的低档一起上)/真核心 bench 等档(上场时机 = 新档成型时机,不是到手时机);插件禁用矩阵(`PLUGIN_LIBRARY`)命中 = 硬冲突不降级为散件。无事务语境的独立入口 = `fill_slot_policy`。

**中断恢复与谷底回滚**(`EvolutionState` 跨步记忆,调用方持有):遭遇/boss 轮**冻结**——不启动新替换,最优机会登记 `pending`,恢复 = 下个非遭遇轮入口三条件重校验(替换本身是原子事务,冻结打断的永远是「还没开始的那次」);`paused` = 谷底回滚后的放缓标志,下个非遭遇轮解暂停再续;`last_deployed`/`last_retained` = 上次替换的上场/保留名单,`rollback_weakest`(转型期单场掉血超阈值触发,观测归调用方)回滚**一件**最弱替换位(有 bench 保留件则换回,无则退役)后置 paused。

**边界**:替换决策不消费 bench 装备字段(按角色身份 + 羁绊档判断,装备只随人走——装备分配是独立决策面);效果评分是量化代理而非战斗模拟(核心哲学 2)。

## 11. cw_intention:终局意向分层

终局方向的意向状态机:纯逻辑模块,不碰游戏、**不改板上**——终局件「买而不上」,锁线后只改囤货方向。决策与取舍见 ADR-0319;它是旧件 `cw_signal_lock`(信号 2 层)/`cw_line_library_v1`(LineV1)的 v4 后继。

**信号五层**(`detect_signals`,①>②>③>④ 严格分层):

- ① 策略驱动:投资环境/投资策略亲和表命中(近硬绑);
- ② 类专属羁绊:家族专属羁绊计数达阈(`FAMILY_BOND_MIN_COUNT`)——信号表 `FAMILY_BOND_SIGNALS` 从 `Comp.bond_signal` 数据字段派生(ADR-0320,不手编);**资格门(ADR-0338)**:羁绊副产品计数不构成直通终局线的锁线资格——信号发射前要求 `_direct_line_qualified`(资格 = 亲和表反查:持有策略/环境指向该 comp);无资格不发②(意向保持 unlocked,囤货落⑤兜底);
- ③ 核心卡:具名意向核心(`intention_core`:plaza carry 且在 core_chars 内者,否则 core_chars 首位——单一核心保证 miss 计数良定义)在店/到手;
- ④ 资源:升费链角色到手作资源到位代理(升费资源暂无 GameState 字段);
- ⑤ 兜底线:`FALLBACK_COMP_NAME`(欢愉族绯英档,无信号默认落点)——**不在 detect_signals 产出**,信号列表为空时解析侧落兜底。

**锁线/撤销状态机**(`IntentionState`:unlocked / locked / weak,`update_intention` 每回合驱动;一回合最多一次转移——撤销后当轮不重锁,防弱意向态不可观测):锁定后撤销**只有两个出口(析取)**:

1. **出口① miss-N**:意向核心连续 `CORE_MISS_N` 轮不可得 → 降级弱意向。计数带**窗口冻结语义**(`LineTrack`):分母只计刷新窗已开的轮(窗口未开时「买不到」是结构性的,不是不可达证据,计 `frozen_rounds` 不计 `miss_count`);冻结累计超位面剩余节点 → 该线**逐出**候选集(`evicted`,移出后不再产信号),意向回无信号态且当轮不触发③;
2. **出口② 高层替代**:更高层级信号(层级低于锁定层)且过**可达性对照**(再遇窗口期望轮数 `encounter_window_rounds` ≤ 全局剩余节点数)——层级高 ≠ 必换。

分数涌现劣势换线**不在本模块**(终局线由贯穿件锁定,不是 pivot)。**强制锁线**(P3 入口仍无意向):候选按资产厚度(终局件星级当量 + 骨架件折算)择最优锁;全部不可达 → **降格终局**(`demoted_endgame`,「赢不了就少输」),为 absorbing 态(不回弹)。

**锁后效果接口**(`hoard_target_set` → `HoardTarget`):输出囤货目标集合 = 角色件(char_targets:意向线采购集,core/shared/替班/羁绊成员)+ 装备件(equip_targets:意向线 equip_assign 派生,剔具名 equip_taboos)+ mode('locked'/'forced'/'weak'/'fallback'/'demoted_endgame',买侧按 mode 区分囤货语义)。生产载体 = decision_v2 的 `update_target` 每轮把它写进 `session.v3_hoard`,是**买侧唯一消费面**——意向模块不产出任何上场/换人动作(意向管方向、演进管换档)。弱意向态撤销后去向 = 只囤跨线骨架件(`CROSS_LINE_SKELETON`,从 W16 过半统计派生,ADR-0312)。

撤销阈值/信号阈等常量(`CORE_MISS_N`/`SKELETON_ASSET_WEIGHT`/`FAMILY_BOND_MIN_COUNT`)属 sim 校准域,值只在代码。
