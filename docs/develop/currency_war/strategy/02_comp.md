# 02 阵容选择(战略层)

> 「这局打什么阵容、何时定型/转型、跨局怎么分配」的语义。本篇:`cw_comps`(COMP_LIBRARY + select_comp/pivot)/ `cw_transition`(双轨过渡)/ `cw_line_tribunal`(审判层)/ `cw_run_allocator`(跨局分配)。玩法证据 → [game/research/plaza_methodology](../../../game/currency_war/research/plaza_methodology.md)(M1-M16);单套打法叙事(入场/退场/counter)→ [game/research/comps](../../../game/currency_war/research/comps/README.md)(打法卡,有实战接触才建)。

## 1. COMP_LIBRARY:阵容注册表(数据模型)

`cw_comps.COMP_LIBRARY`,数据源 `cw_plaza_comps`(plaza API 生成,勿手编)。`Comp` 关键字段语义:

- **`factions` vs `flex_factions`**:核心羁绊(成型判定用)与弹性羁绊(亲和不断判)二分——M2「核心锁死 × 弹性填充」;评估板面时朝弹性羁绊铺**不算 spread**。
- `core_chars` 核心角色;`form_tiers` 各羁绊成型档;`level_plan` 等级→动作曲线(骨架与参数的接缝:无 comp 走通用兜底);`key_equips` 关键装备(有序,合成优先级);`form_difficulty` 成型难度(easy/medium/hard,选型关键维度);`countered_by_bosses`/affix 双向(克它的与利它的词缀);`star_goals`(缺省 = `default_star_goal`:≤3费追3星、≥4费追2星,M6 升星经济学)。

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
