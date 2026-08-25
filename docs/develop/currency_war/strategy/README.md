# 货币战争 策略设计(总览 · as-built)

> **本文档族描述系统「现在是什么」**(as-built,方法论 ADR-0210):结构 / 语义 / 数据流 / 边界;值在代码(常量名单一源)、why 在 [decisions/](../decisions/INDEX.md)(ADR)、玩法证据在 [game/currency_war/research/](../../../game/currency_war/research/README.md)、实现进度在本地进度树。目标:纯代码(无 LLM)自动打最高难度 A8 高胜率,留用户偏好配置口([../config.md](../config.md))。

> **⚠️ 改任何策略前的强制入口序**(用户 2026-08-20 定调):①先读
> `game/currency_war/research/user_playstyle.md` **全文**(口述权威,条目 1-26)——
> **每次改策略都整体考虑全部原则,不是逐条打补丁**;②攻略证据以 plaza 精读为准
> (`research/plaza_methodology.md` M1-M16 + 专题);③动代码前用四原则自检:
> **息律节点无关 / hp低是报警不是触发 / final 买而不上 / 过渡是配方不是散买** ——
> 与原则冲突的改动方向(如新造节点特例、把报警线当 spending 触发器)一律重想。

## 为什么有策略 v2(动机;裁定史 ADR-0227,砍除归档 ADR-0365)

v1 的四个假设被 784 篇投稿深读(r167-r187)与用户系列裁定(r149-r192)推翻:①终局阵容成员写死(实际:核心角色固定,副羁绊按来牌灵活替换);②过渡与终局两套独立数据靠某时刻"切换"(实际:阵容连续演化,开局引擎由来牌决定);③没有"当前阵容能否过接下来的节点"的判断(买/升/存息缺时机依据);④装备与领航员静态绑定(实际:装备公式跟核心驱动型走且有时序,领航员是时间函数)。v2(现行 decision_v2 族)围绕这四点重建;形态战力证据表在 game/research/power_baseline。

## 核心哲学(三条,贯穿全系统)

1. **像人一样玩,观测驱动非预测驱动**:用每回合 OCR 掉血/胜负等**观测结果**当反馈信号;不预测战斗(为什么砍掉战斗模拟器:ADR 见 INDEX)。
2. **不建精确战斗模拟器**:星铁战斗太复杂、版本敏感、维护不起;通关能力 = 阵容质量先验 + 观测确证。
3. **ML 只采集不主依赖**:telemetry 是一等公民(决策迹/结算全量落盘),训练管线是 side door。

## 每回合决策链(数据流)

```
battle_loop(主循环,屏幕级路由)
  ├─ 观测层:各屏 reader(OCR/SIFT/CV)→ GameState(06_input_model)
  ├─ 对账:cw_reconcile(tracking vs 读到的真值;05_observation)
  ├─ 策略钩子(CwStrategy,07_plugin):
  │    update_target(选/转阵容,02_comp)
  │    decide_prep_action(备战单步动作 → PrepDirector 环执行,03_tactics)
  │    decide_invest/encounter/supply/megastar/partner(事件节点,04_nodes)
  ├─ 战术层:plan(硬门贪心+蒙特卡洛D牌)/ evaluate(阶段键控)/ bundle(联合束)
  │    —— 花钱节奏(升/刷/攒)由 DP 姿态统一回答(01_posture)
  ├─ 执行:prep_actions 原子动作(带完成验证)
  └─ 战后:结算观测 → PerformanceTracker(掉血/胜负)→ telemetry 落盘
跨局:cw_run_allocator(Thompson 选臂)+ cw_first_passage(P(win) 目标函数)
```

## 模块地图(`src/sr_od/application/currency_war/`)

| 域 | 模块 | 职责 | 详 |
|---|---|---|---|
| 信息模型 | `cw_state` | GameState/Action/MatchOutcome 等核心类型;sell_refund;hp 阈值派生 | [06](06_input_model.md) |
| 注册表 | `cw_chars`/`cw_factions`/`cw_equipment`/`cw_invest_data`+`cw_investments`/`cw_comps`/`cw_shop_odds`/`cw_synthesis`/`cw_enemy_data`/`affix_effects_data` | 游戏数据单一源(名称/效果/关系/概率);`cw_plaza_comps` 为生成产物 | [06](06_input_model.md) |
| 战力表(策略v2) | `cw_power_table`(判断层)+`cw_power_table_data`(数据层,生成勿手编) | 形态×位面→验证篇数(敢用白名单);三级回退+分层保守系数;策略 v2 Phase A | [02](02_comp.md) · [数据 meta](../power_table_meta.md) |
| 桥线池(策略v2) | `cw_bridge_pool` | 未锁线时的购买方向(手牌重合度选桥;fixed/core/flex 三档;W126/ADR-0350 删已封存 hunt3/dot_belog 两桥,存活三桥全四体系);`ENGINE_FACTIONS` 从桥池 engine_bonds 派生(单一源,={仙舟,持续伤害,列车同行}) | [02](02_comp.md) · [0350](../decisions/0350-retire-sealed-factions-scoring.md) |
| 过渡配方/检查点 | `cw_line_defs` | RECIPE_FACTIONS/RECIPE_BASE/ENGINE_FACTIONS 常量单一源 + `p1_formation_target` P1 成型检查点(轮窗常量 `_*_FORMATION_*` 见 cw_line_defs,ADR-0225/0241) | [02](02_comp.md) |
| 过渡配方一等公民模型(策略v2) | `cw_recipe` | P1 双轨期决策中心:配方伪 comp(RecipeComp)令 plan/deploy 评分自动转向配方完成度;「配方完成度即 P1 胜利条件」(user_playstyle [20]-[23]/[26];ADR-0225/0243) | [02](02_comp.md) |
| 线库v1(策略v2,**已删**) | `cw_line_library_v1` | 三线档案(姬子/绯英/DOT兜底)随 LineStrategy 删除(ADR-0336);历史数据见 git | [0336](../decisions/0336-delete-line-strategy.md) |
| 信号锁线(策略v2,**已删**) | `cw_signal_lock` | 信号 2 层(核心卡到手→锁线)随 LineStrategy 删除(ADR-0336);信号分层现由 cw_intention 承载 | [0336](../decisions/0336-delete-line-strategy.md) |
| 状态机(策略v2,**已删**) | `cw_phase_machine` | 相位机随 LineStrategy 删除(ADR-0336);模式判定现由 decision_v2 的 v3_mode 承载 | [0336](../decisions/0336-delete-line-strategy.md) |
| decision_v2(唯一策略载体) | `decision_v2/`(strategy=独立 DefaultCwStrategy 实现+discipline 纪律族+candidates/filters/scoring/arbiter 四层+remediation 补偿子模块+registry) | 战略层=cw_intention 意向分层(update_target 写 v3_hoard/target_comp=COMP_LIBRARY v2 真 Comp);目标件=hoard_target_set+体系卡引擎件+PLUGIN_LIBRARY;演进=cw_evolution(evolution_step 进决策循环发显式 CompTransaction);纪律族=应急/boss_breaker/carry_gate/掉血三臂(报警梯度:①自然窗→②弃息 D→③位面末 ALL IN,ADR-0313)/保血通道(追赶态已随 ADR-0349 退场——人口落后由人口位升级+概率等级窗+EV 总账涌现);carry_gate 弱序与保护集口径(ADR-0314;S5 统一弱序见 ADR-0327);**层4 末段补偿趟**(ADR-0326:资源型拒绝结构化捕获 → 同轮单趟 remediation_pass 定向补偿 → 事务性重验 → 重试;liquidity 通道已收编,触发源=working.gold 实际缺口;remedy_buy_tags/remedy_min_score/remedy_alarm_refresh 常量在 registry);**评分活性**(ADR-0332:war 破息窗 50 平台破碎只付真实息损——息崖平滑;未成型+引擎件买入顶正——成型补充偏置;常量 forming_bias/forming_bias_val_max 在 registry);**经济循环总模型**(ADR-0346/0347/0349:相位地板+EV 授权+V_D 批口径三通道调度——refresh 候选=vd_refresh_score 金口径批账(收益=核心 2★ 成型跳变,成本=expected_refreshes×刷价;war/危机同账),升级总账含省刷金项(k 放大),refresh 附庸闸十一参与 refresh_budget 约束退场;**P1 早期新件买入口**(ADR-0372:FORM 地板对配方对缺件的同息档购买放行,`p1_early_gate_enabled` 三常量在 registry)) | [0290](../decisions/0290-decision-framework-candidate-scoring.md)(框架本体)+[0309](../decisions/0309-decision-v2-sole-carrier.md)(载体迁移)+[0313](../decisions/0313-blood-alarm-semantics-final.md)+[0314](../decisions/0314-carry-gate-weak-order.md)+[0326](../decisions/0326-rejection-remediation-loopback.md)+[0327](../decisions/0327-sell-priority-key-unified.md)+[0332](../decisions/0332-forming-scoring-activity.md)+[0336](../decisions/0336-delete-line-strategy.md)+[0347](../decisions/0347-switch-authority-phase-ev.md)+[0349](../decisions/0349-switch-dispatch-vd-batch-caliber.md)+[0372](../decisions/0372-p1-early-buy-gate.md) · [07](07_plugin.md) |
| 姿态/经济 | `cw_horizon`(DP 求解器)/`cw_effect_ledger`/`cw_economy` | 跨期花钱节奏(升/刷/攒)单一姿态源;既持效果台账;经济纯函数 | [01](01_posture.md) |
| 战略 | `cw_comps`(select_comp/pivot)/`cw_transition`(双轨过渡)/`cw_line_tribunal`(战略审判)/`cw_run_allocator`(跨局)/`cw_first_passage`(目标函数)/`cw_progress_curves`(期望进度线) | 打什么阵容、何时定型/转型、跨局选臂 | [02](02_comp.md) |
| 演进引擎 | `cw_evolution` | 阵容替换通用法则:evolution_step 统一入口四步(propose→evaluate 三条件[③人口=信息位不阻断,发令枪=①∧②]→execute 整档 CompTransaction→fill 空位规则);中断恢复 pending 重校验/谷底回滚一件最弱(ADR-0319);换血保护:锁定目标件四件套(ADR-0360)+ 引擎下界守卫/末轮演进冻结(ADR-0363)+ 引擎补完守卫「拥有必上场」(ADR-0371) | [02 §10](02_comp.md) |
| 终局意向 | `cw_intention` | 意向分层纯逻辑:信号五层/锁线撤销析取两出口(miss-N 窗口冻结逐出 / 高层信号过可达对照)/降格终局 absorbing;锁后只输出囤货目标集合写 v3_hoard(买侧唯一消费面,不改板上)(ADR-0319) | [02 §11](02_comp.md) |
| 战术 | `cw_plan`/`cw_evaluate`/`cw_bundle` | 备战动作规划/局面评估/回合内联合行动束 | [03](03_tactics.md) |
| 节点决策 | `cw_events`/`cw_survey19_hooks`/`cw_difficulty_account` | 投资卡/遭遇/补给/巨星/伙伴选择;难度账本 | [04](04_nodes.md) |
| 执行 | `prep_director`/`prep_actions`/`operations/`(battle_loop+prep+handlers+run_nodes) | 备战决策环、原子动作执行器、op 层 | [03](03_tactics.md) |
| 观测 | `cw_observation`/`cw_obs_core`/`cw_identity_obs`/`cw_node_obs`/`cw_settlement_obs`/`cw_briefing_obs`/`cw_node_reader`/`cw_reconcile`/`cw_performance`/`cw_telemetry` | 读屏→GameState;对账;观测反馈;决策迹 | [05](05_observation.md) |
| sim/回放基建 | `cw_sim`(P1 全流程模拟器:真代码层同源+校准层可注入+实机 Δ 池重放,ADR-0218/0242)/`cw_sim_checks`(账本检查,实机学费回灌载体;池新鲜度报警 ADR-0344)/`cw_delta_pool_data`(Δ 池快照,生成勿手编)/`cw_delta_pool_gen`(池生成核心+局终自动再生管线,ADR-0344;CLI 壳 tools/cw/gen_delta_pool_snapshot.py)/`cw_replay`(决策回放 harness)/`cw_match_recorder`(对局采集器)/`cw_plan_replay_audit`(plan 对拍) | 策略迭代的秒级反馈链(sim 批量 → 回放对拍 → 实机最后一步);不进生产执行链 | [05 §5](05_observation.md) |
| 插件 | `cw_strategy`/`cw_strategy_manager`/`strategies/default_strategy`/`strategies/decision_v2_strategy`(现行生产 v2;旧 line_strategy 已删,ADR-0336) | 可替换决策大脑(第三方策略/比赛) | [07](07_plugin.md) |
| 离线工具 | `cw_weight_search`(CEM 权重搜索)/`cw_divergence_stats`(姿态分歧频率)/`cw_progress_curves` | 消费 telemetry 的离线分析,不进生产链 | [05](05_observation.md) |

## 分篇

- [01 姿态与经济](01_posture.md)—— DP 求解器、效果台账、息引擎与例外窗口、目标函数
- [02 阵容选择](02_comp.md)—— COMP_LIBRARY、select_comp/pivot/commit、双轨过渡、审判层、跨局分配
- [03 战术执行](03_tactics.md)—— PrepDirector 环、动作全集、plan/evaluate/bundle、部署与装备
- [04 节点决策](04_nodes.md)—— 投资/遭遇/补给/巨星/伙伴、难度账本
- [05 观测与遥测](05_observation.md)—— reader 家族、对账、PerformanceTracker、telemetry schema、日志格式
- [06 信息模型](06_input_model.md)—— GameState 语义、注册表地图
- [07 策略插件](07_plugin.md)—— CwStrategy ABC、发现机制、replay 语义

## 历史对照(旧编号 → 现行位置;供代码注释/ADR 里的旧引用导航)

| 旧文件 | 现行位置 |
|---|---|
| 01 架构 | 本 README(决策链)+ 各分篇 |
| 02 eval+搜索 | [03](03_tactics.md)(eval/plan/D 牌)+ [01](01_posture.md)(经济统一论) |
| 03 阵容规划 | [02](02_comp.md) |
| 04 状态对账 | [05](05_observation.md) |
| 05 数据接线 | [05](05_observation.md) + [06](06_input_model.md) |
| 06 实施阶段 | 已删(进度性质,历史在 git) |
| 07 装备 | [03](03_tactics.md)(执行)+ [02](02_comp.md)(equip_fit) |
| 08 节点决策 | [04](04_nodes.md) |
| 09 meta-run | [../config.md](../config.md)(manage_meta_run)+ ADR-0211 |
| 10 战斗反馈+敌人 | [05](05_observation.md)(PerformanceTracker)+ [06](06_input_model.md)(机制克/利) |
| 11 策略插件 | [07](07_plugin.md) |
| 12 comp 成型 | [02](02_comp.md)(commit/prefilter) |
| 13 输入模型 | [06](06_input_model.md) |
| 14 阶段节奏骨架 | [01](01_posture.md)(DP 单一姿态源,ADR-0208);证据 → game/research/economy |
| 15 备战决策环 | [03](03_tactics.md) |
| 16 plaza 方法论 | game/research/plaza_methodology(M1-M16) |
| 17 HORIZON 导览 | [01](01_posture.md) |
| 18 投资效果调研 | game/research/invest_effects(+ADR-0205) |
| 19 二轮扫描 | 溶解(M16→research/plaza;裁定→ADR-0211;其余已落地或撤回) |
| 20 live 观测规划 | [05](05_observation.md)(telemetry schema) |
| economy_research | game/research/{economy, user_playstyle} |

## 边界与已知风险(原 v2 设计期声明精简,ADR-0365;若与各分篇 as-built 冲突以分篇为准)

- **感知边界**:对手阵容细节/敌方词条实时变化不可得——counter 判定只用可识别信号;P3 决赛圈对手针对不在范围。
- **显式未覆盖**:事件选项语义/装备配方级选择等曾列为 v2 排除项,现状见各分篇(04/03)。
- **版本漂移**:游戏版本切换需重提取数据(生成器可重跑);战力/桥线等先验表随版本过期。
- **跨局分配**(cw_run_allocator)与本层正交,单独演进(02)。
