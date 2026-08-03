# 货币战争 策略完整方案(总)

> 目标:**纯代码(无 LLM)自动打最高难度 A8 + 高胜率 + 灵活自适应肉鸽各种情况**,**留用户偏好配置口**。
> 总分结构:本 README 是「总」,`0N_*.md` 是「分」。设计先行(方案打磨完美再写代码)。
> 依据:review r1(44 条 code bug,已修)+ review r2(架构 A1-A6)+ review r1-r4 方案(~75 findings,已并入各 doc)。
>
> **核心哲学(2026-08-03 用户定调,贯穿全方案)**:**像人一样玩** —— 观测驱动而非预测驱动。用**观测结果**(每回合 OCR 掉血/胜负)当核心反馈信号,**不建精确战斗模拟器**(星铁战斗太复杂、版本会迭代、维护不起),**ML 只采集(debug 开关)不主依赖**(训练价值版本短命)。目标不是"算得比人精",是"反应得像人一样对"。详 10。

## 一句话方案
**三层架构**:数据层(OCR 真值 + bot 跟踪 + 对账 A6)→ 战术层(阶段键控 eval A3 + 贪心 + 蒙特卡洛 D 牌 A1)→ 战略层(阵容规划 A2 + 转型 + 巨星)。现有「eval+贪心」是战术层内核(已实现);待加战略层 + 对账层 + 装备/节点决策 + 接线。不推翻重做,补齐缺失的 2/3。

## 目标架构(分层)
```
meta-run 层(09,跨局):开新局前**按配置激活最优「优势布局」**(`manage_meta_run` 默认**关 = 不碰玩家跨局继承**,开了才自动激活)+ **游戏自带「攻略」推荐作 COMP_LIBRARY 兜底**(只读、版本无关)【凹开局重开已删 —— 策略够好该能克服任何开局】
    ▼
战略层(A2):选 target_comp(阵容库 + 目标选择 + 转型 + 巨星)→ 指导战术估值
    ▼ target_comp
战术层(已实现+A1/A3):evaluate(阶段键控 + target_progress + 通关能力[成型度+装备,装备 comp 相关非独立项] + 连胜)+ plan(硬门贪心 + 蒙特卡洛 D牌)
    ▼ Actions
数据层(A6):OCR→GameState + bot 跟踪 deployed + 每回合对账(置信度加权)+ 动作后验证
节点决策:遭遇难度/词缀 + 补给出钻 + 巨星 + 事件白名单 + 投资策略刷新(纯函数,各节点调)
```

## 用户配置口(2026-08-03 重设计;实施时再细调)

**设计原则**:配置 = 在 comp 驱动流程上表达"我想怎么玩"(**方向盘**),不是引擎旋钮。策略引擎(COMP_LIBRARY / level_plan / eval)自动最优;配置只 steer。严格区分**真偏好(给用户)** vs **通用数据(内部,改了只会改坏)**。

### A. 用户配置(GUI 可改)

**优先 / 禁止 / 必含(4 轴,三档强度;空 = 纯自适应):**
- 角色:`character_priority`(优先,soft+)/ `character_forbid`(禁止,hard− 永不选)/ `build_around`(必含,hard+,围绕你的强角色)
- 阵营:`faction_priority`(soft+)/ `faction_forbid`(hard−)/(build_around 同,必含阵营)
- 投资策略:`strategy_priority`(soft+)/ `strategy_forbid`(hard−)
- 投资环境:`env_priority`(soft+)/ `env_forbid`(hard−)
- 三档:**必含(hard+)> 优先(soft+)> 默认(T0 数据)> 禁止(hard−)**。优先=倾向选;禁止=永不选(哪怕客观强);必含=一定带上。`*_forbid` 让用户排除不喜欢/被克/不想碰的(如某 boss 克的阵营、净化身心环境)。

**接管 / 用例:**
- `handoff`(bool,**主轴**):是否停下让人接管(全自动=false / 代刷接手=true)。
- `handoff_point`:接手点 —— 好开局 / 阵容成型 / 某节点(无濒死停)。
- `difficulty`:A8 / A7 / …(reward/时间权衡)。
- `retry`:失败重试次数(日常可靠性)。
- `record`(bool):记录 / 统计面板。
- `manage_meta_run`(bool,**默认 false**):bot 是否动**跨局内容**(激活优势布局/花钻钞)。**默认关 = 不碰,保留玩家自己攒的跨局继承**(防打乱玩家 buff);开了才开新局前自动激活最优。持久化状态默认 opt-in,不做破坏性操作。

**Top3 用例字段组合**:日常清扫 = `handoff=false` 全默认;成就 = 选成就预设;开局代刷+接手 = `handoff=true` + `好开局`。

### B. 预设(后续做,一键填优先轴)
- **成就预设**:7 仙舟 / 15 连胜 / 3 星 X / 8 人全装备 … 每个 = 4 优先轴打包 + 个别行为标志。用户选预设 = 换一组优先偏好(**非特殊代码路径**,和 comp 驱动一致,bot 正常按偏好打、成就自然达成)。
- (可选)playstyle 预设。

### C. 内部数据表(不放 GUI,代码/yml 维护)
对谁都一样的正确数据:COMP_LIBRARY / MECHANIC_COUNTERS+SYNERGIES / boss_counter / dot_punish_envs / 优势布局自动激活 / hp_safe_threshold(由 difficulty 派生)/ _refresh_cap(动态)。

### D. 已移除(及原因)
`run_mode`(→ 字段值表达)/ `aggression`(虚)/ `economy_mode`(和 level_plan 打架,经济 comp 驱动)/ `event_whitelist`(拆成 env+strategy priority)/ `achievement_target`(→ 预设)/ `target_comp_preference`(并入 build_around+priority)/ `hp_safe_threshold`+`refresh_budget`(→ 内部派生)/ 钻钞 farming(自动激活优势布局)/ `opening_restart`(策略不依赖,见 09)/ 濒死停(无用)/ 多账号·定时·领奖(一条龙框架层,非 app)。

⚠️ **现状**:`currency_war_config.py` 当前仍是旧结构(faction/character/aggression/economy_mode/event/boss/dot_punish);**实施时按本节重写**,保 README↔代码单一真相。

## 决策点 × 层归属
| 决策 | 层 | 状态 |
|---|---|---|
| 买哪张/deploy 谁/站哪排/升等级/卖谁 | 战术(eval+贪心) | ✅ |
| 何时 D 牌(刷新) | 战术(蒙特卡洛 A1) | ✅ |
| commit 哪个阵容/转型 | 战略(A2) | ✅ 骨架(cw_comps 阶段2)|
| 巨星绑谁 | 战略(select_megastar) | ✅ 骨架(cw_comps 阶段2)|
| 事件(投资环境/策略)选哪个 | 战术(白名单 decide_event) | ✅ |
| **遭遇难度/词缀避开** | 节点(decide_encounter) | ❌ 阶段 2(08) |
| **补给选装备/出钻** | 节点(decide_supply) | ❌ 阶段 3a(07) |
| **装备合成/分配** | 战略/comp 评估(`equip_fit(comp)` comp 相关,详 07;不独立评分)+ Equip 动作 | ❌ 阶段 3a(07) |
| boss 克制切换阵营 | 战略/战术(decide_boss_priority) | ✅ 基础 |
| **战斗反馈(掉血/胜负跟踪)** | 数据(PerformanceTracker)+ 战术(comp_viability) | ✅ 骨架(cw_performance 阶段2)+ 阶段 4 接线 |
| 状态对账/动作验证 | 数据(A6) | ❌ 阶段 4 |

## 当前状态(2026-08-03)
**已实现+提交**:战术层内核 + review r1(44 条修)+ A1(蒙特卡洛 D 牌)+ A3(阶段键控)+ **阶段 2 战略层(cw_comps 阵容库/comp_score/select_comp/转型/巨星 + cw_performance 观测反馈 PerformanceTracker/comp_viability/死局 + cw_telemetry 决策迹采集)**。78 测试绿。百科数据全量(米游社 V4.4,../data/)。
**方案**:strategy_plan/ 11 篇(本 README + 01-10),经 review r1-r4 方案(~75 findings)打磨 + 2026-08-03 观测驱动哲学修订。

## 实施阶段(总览,详 06)
| 阶段 | 内容 | 游戏? | 状态 |
|---|---|---|---|
| 0 | 战术层内核 + r1 修 | 否 | ✅ |
| 1 | A1 蒙特卡洛 D 牌 + A3 阶段键控 | 否 | ✅ |
| 2 | **A2 阵容规划 + 巨星 + 节点决策骨架 + 战斗反馈(观测驱动)+ 决策迹采集** | 否 | ✅ 骨架(战略层/观测/telemetry 落地;↔战术层接法待阶段 4)|
| 3a | A4 牌池概率 + 装备模型 + 通关能力 eval | 否 | 待做 |
| 4 | A6 对账 + OCR 接线 | 是 | 待做 |
| 5 | op 层接线 | 是 | 待做 |
| 5.5 | **replay 测试 harness**(A/B 权重) | 是 | 待做 |
| 5+ | A5 战术涌现(多步搜索,删 bolt-on) | 否 | 待做 |
| 6 | 实机测 A8 胜率 → 迭代 | 是 | 待做 |

## 游戏/非游戏边界
阶段 0-3a + 5+ 纯逻辑(可现在做);阶段 4-6 + 5.5 需游戏(星铁在线)。当前星铁未开 → 先推进阶段 2-3a(非游戏)。

## 文档索引(分)
- [01 目标架构](01_architecture.md)—— 三层架构 + 数据流 + 为何不推翻。
- [02 评估+搜索](02_eval_search.md)—— A3 阶段键控✅ + A1 蒙特卡洛 D牌✅ + A4 PvE 牌池❌ + 通关能力 eval(成型度+装备,去邪道)❌ + aggression + 鲁棒性。
- [03 阵容规划](03_comp_planning.md)—— A2 阵容库(多维打分:强度+成型难度+契合)+ comp_score 公式 + target_progress(去三重)+ 转型(比较型)+ 巨星。
- [04 状态对账](04_state_reconciliation.md)—— A6 置信度加权对账 + 动作后验证。
- [05 数据与接线](05_data_wiring.md)—— GameState 完整字段表(单一真相源)+ 签名/失败语义 + 每回合 op 序列图 + meta 表。
- [06 实施阶段](06_phases.md)—— 逐阶段 + replay harness(5.5)+ A5 拆分 + cw_factions meta 分层。
- [07 装备系统](07_equipment.md)—— 装备模型 + **equip_fit(comp) comp 相关评分**(非独立 equip_score)+ Equip 动作 + 补给决策。
- [08 节点决策](08_node_decisions.md)—— 遭遇难度/词缀 + 巨星 + 补给出钻。
- [09 meta-run 层](09_meta_run.md)—— round 2 新发掘:优势布局(跨局 meta)+ 攻略推荐(版本无关 ground truth)+ 超频 farming。【凹开局重开已删】
- [10 战斗反馈+敌人机制](10_battle_and_enemies.md)—— 观测驱动(用户定调):PerformanceTracker(OCR 掉血/胜负 ground truth)+ comp_viability(先验+观测)+ 敌人机制克制(跨版本稳);不建精确战斗 sim。
