# 货币战争 策略完整方案(总)

> 目标:**纯代码(无 LLM)自动打最高难度 A8 + 高胜率 + 灵活自适应肉鸽各种情况**,**留用户偏好配置口**。
> 总分结构:本 README 是「总」,`0N_*.md` 是「分」。设计先行(方案打磨完美再写代码)。
> 依据:review r1(44 条 code bug)+ review r2(架构 A1-A6)+ review r1-r4 方案(~75 findings)。
>
> **核心哲学(2026-08-03 用户定调,贯穿全方案)**:**像人一样玩** —— 观测驱动而非预测驱动。用**观测结果**(每回合 OCR 掉血/胜负)当核心反馈信号,**不建精确战斗模拟器**(星铁战斗太复杂、版本会迭代、维护不起),**ML 只采集(debug 开关)不主依赖**(训练价值版本短命)。目标不是"算得比人精",是"反应得像人一样对"。详 10。

> **2026-08-09 研究驱动方向修订(依据 decisions D-17;米游社/bwiki/TapTap/17173/豌豆荚攻略研究,带证据等级)**:三条核心 shift ——
> 1. **comp:均衡多羁绊(6+3 / 5+4 型双羁绊),非纯单阵营深堆**。A8 主流是 **2 个羁绊叠到各自阈值**,而非 1 个阵营叠满;辅助(缇宝/星期日/记忆主/知更鸟)价值 > 凑非核心羁绊;投资环境「净化身心」克 DoT/减益 → 选阵须检测环境。**印证实测「集中到 tier-3 做不到」**(A8 商店稀疏 + 正确策略本非纯集中)。→ 12_comp_commitment「commit + 不散」仍对,但 **target = 多羁绊均衡成型,非单阵营叠满**。具体 comp 清单 + 羁绊阈值见 03。**⚠️ 版本待核**:本次 research(D-17)抓到的 comp meta 标 V3.7(高速阿雅/遐蝶/黑天鹅DoT),与项目 round-5 research 的 V4.4/V4.5(列车同行/命运圣杯/欢愉)不一致 —— comp meta 版本敏感,**须按当前游戏版本核实哪套为准**(round-5 为项目自有近期研究,优先信;D-17 的机制/经济/装备结论版本无关,可信)。
> 2. **装备:A8 成型关键,bot 完全裸装 → 最高杠杆**。「1雅1鞋成型」、反重力皮靴必备,裸装输;每局保底 ≥3 装。机制待 live 验(攻略说拖拽;VLM 实测见「装备推荐」按钮 ~x1494,y811,功能未验)。→ 07_equipment 升优先 + live 验机制。
> 3. **economy:D-14 leveling 方向对(攒够 cost 就升);tempo = 先冲等级(4级前主升级)→ 维持 50 金吃满息 → 多余金币刷牌/买同费卡(卡池稀释);奖励关不花钱留息**。升级费用表待从「数据银行」图鉴取权威值(代码现表估,6→10≈262≈攻略 270)。
>
>

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

⚠️ **现状(2026-08-04 对齐,D-18)**:`currency_war_config.py` 已删 `aggression`(死字段);**保留** `economy_mode`(eval 权重微调,与 level_plan 硬 gate 共存非冲突)+ `event_whitelist`/`boss_counter`/`dot_punish_envs`(decide_event/decide_boss 用)。**仍缺** `character_forbid/build_around`、`faction_forbid`、`strategy/env_*`、`handoff/difficulty/manage_meta_run`(cw_comps 已 `getattr` 防御读取,可增量加,deferred)。原 §D "economy_mode/event_whitelist 已删"计划**撤销**(见 D-18)。

## 决策点 × 层归属
| 决策 | 层 |
|---|---|
| 买哪张/deploy 谁/站哪排/升等级/卖谁 | 战术(eval+贪心) |
| 何时 D 牌(刷新) | 战术(蒙特卡洛 A1) |
| commit 哪个阵容/转型 | 战略(A2) |
| 巨星绑谁 | 战略(select_megastar) |
| 事件(投资环境/策略)选哪个 | 战术(白名单 decide_event) |
| 遭遇难度/词缀避开 | 节点(decide_encounter) |
| 补给选装备/出钻 | 节点(decide_supply) |
| 装备合成/分配 | 战略/comp 评估(equip_fit(comp),详 07)+ Equip 动作 |
| boss 克制(comp-vs-boss) | 战术(boss_fit/comp.countered_by_bosses;decide_boss_priority 已删错模型) |
| 战斗反馈(掉血/胜负跟踪) | 数据(PerformanceTracker)+ 战术(comp_viability) |
| 状态对账/动作验证 | 数据(A6) |

## 实施阶段(总览,详 06)
| 阶段 | 内容 | 游戏? |
|---|---|---|
| 0 | 战术层内核 + r1 修 | 否 |
| 1 | A1 蒙特卡洛 D 牌 + A3 阶段键控 | 否 |
| 2 | A2 阵容规划 + 巨星 + 节点决策骨架 + 战斗反馈(观测驱动)+ 决策迹采集 | 否 |
| 3a | A4 牌池概率 + 装备模型 + 通关能力 eval | 否 |
| 4 | A6 对账 + OCR 接线 | 是 |
| 5 | op 层接线 | 是 |
| 5.5 | replay 测试 harness(A/B 权重) | 是 |
| 5+ | A5 战术涌现(多步搜索,删 bolt-on) | 否 |
| 6 | 实机测 A8 胜率 → 迭代 | 是 |

## 游戏/非游戏边界
阶段 0-3a + 5+ 纯逻辑;阶段 4-6 + 5.5 需游戏(星铁在线)。

## 文档索引(分)
- [01 目标架构](01_architecture.md)—— 三层架构 + 数据流 + 为何不推翻。
- [02 评估+搜索](02_eval_search.md)—— A3 阶段键控 + A1 蒙特卡洛 D牌 + A4 PvE 牌池 + 通关能力 eval(成型度+装备,去邪道)+ aggression + 鲁棒性。
- [03 阵容规划](03_comp_planning.md)—— A2 阵容库(多维打分:强度+成型难度+契合)+ comp_score 公式 + target_progress(去三重)+ 转型(比较型)+ 巨星。
- [04 状态对账](04_state_reconciliation.md)—— A6 置信度加权对账 + 动作后验证。
- [05 数据与接线](05_data_wiring.md)—— GameState 完整字段表(单一真相源)+ 签名/失败语义 + 每回合 op 序列图 + meta 表。
- [06 实施阶段](06_phases.md)—— 逐阶段 + replay harness(5.5)+ A5 拆分 + cw_factions meta 分层。
- [07 装备系统](07_equipment.md)—— 装备模型 + **equip_fit(comp) comp 相关评分**(非独立 equip_score)+ Equip 动作 + 补给决策。
- [08 节点决策](08_node_decisions.md)—— 遭遇难度/词缀 + 巨星 + 补给出钻。
- [09 meta-run 层](09_meta_run.md)—— round 2 新发掘:优势布局(跨局 meta)+ 攻略推荐(版本无关 ground truth)+ 超频 farming。【凹开局重开已删】
- [10 战斗反馈+敌人机制](10_battle_and_enemies.md)—— 观测驱动(用户定调):PerformanceTracker(OCR 掉血/胜负 ground truth)+ comp_viability(先验+观测)+ 敌人机制克制(跨版本稳);不建精确战斗 sim。
- [11 策略插件机制](11_strategy_plugin.md)—— `CwStrategy` ABC(可替换大脑,无状态+模板方法全默认)+ `StrategySession`(每局状态)+ `StrategyManager`(对标 app 插件自动发现);服务「自写策略」+「策略比赛」。why 见 decisions D-34。
- [12 comp 成型深化(commitment)](12_comp_commitment.md)—— P2 真正通关 blocker:bot commit 一个可成型 comp + roll 找其阵营 + 深 stack(不散)。解「board 全程 spread → 弱 → plane2 秒死」。
- [13 局内信息模型(策略入参)](13_input_model.md)—— `GameState` 重做成完整局内信息单一入口(全量字段 + 整局固定事实归位 + `None` 不说谎 + 节点观测日志 + 游戏参考数据注册表)。原则:信息层完整提供,用不用归策略。
- [14 阶段节奏骨架](14_phase_skeleton.md)—— **阵容无关骨架 × 阵容参数**:等级曲线驱动(+ bwiki 完整刷新概率表 Lv1-10 作 `level_plan` 硬地基)+ 节点×等级×动作骨架 + 经济线 + 骨架/参数分离(`level_plan` 接缝)。灵活支持所有 T1,不为每阵容硬编码流程。
