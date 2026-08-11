# 货币战争(currency_war)自动化设计

> 玩法本身(机制 / 数据 / 画面)见 [docs/game/currency_war/](../../game/currency_war/)(游戏知识,游戏版本改才变)。
> **本目录 = 自动化实现设计**(bot 流程 / 策略 / 决策 / why,代码改才变),落此(依据 `od-dev-gameplay-automation` ADR-0008:docs/game/ 只放游戏玩法,自动化归 docs/develop/)。
> 设计文档记 **why + 代码不直接表达的**(架构 overview / 配置语义 / 流程概述),**不复述代码**(行为在代码;依据 `od-dev-write-application` ADR-0003)。

## 总分结构(复杂 app 才拆,依据 ADR-0003)

### [strategy/](strategy/) —— 策略完整方案(设计先行,代码按它实现)
- [README](strategy/README.md) —— 总(一句话方案 + 三层架构 + 用户配置口 + 实施阶段)
- [01 架构](strategy/01_architecture.md)—— 三层架构 + 数据流
- [02 eval+搜索](strategy/02_eval_search.md)—— 阶段键控 eval + 蒙特卡洛 D 牌 + 牌池
- [03 阵容规划](strategy/03_comp_planning.md)—— comp_score / 转型 / 巨星 / 掉血归因 / 经济统一论
- [04 状态对账](strategy/04_state_reconciliation.md)—— 多层数据校准
- [05 数据接线](strategy/05_data_wiring.md)—— GameState 字段表 + 每回合 op 序列
- [06 实施阶段](strategy/06_phases.md)—— 逐阶段 + replay harness
- [07 装备](strategy/07_equipment.md)—— 装备模型 + equip_fit
- [08 节点决策](strategy/08_node_decisions.md)—— 遭遇 / 巨星 / 补给
- [09 meta-run](strategy/09_meta_run.md)—— 跨局(优势布局默认不碰)
- [10 战斗反馈+敌人](strategy/10_battle_and_enemies.md)—— 观测驱动 PerformanceTracker + 敌人机制
- [11 策略插件](strategy/11_strategy_plugin.md)—— CwStrategy ABC
- [12 comp 成型](strategy/12_comp_commitment.md)—— commit + 深 stack
- [13 输入模型](strategy/13_input_model.md)—— GameState 完整字段
- [14 阶段节奏骨架](strategy/14_phase_skeleton.md)—— 阵容无关骨架 × 阵容参数(NodeGoal + 7 经济杠杆)

### [decisions/](decisions/) —— 决策日志(ADR 式)
- [INDEX](decisions/INDEX.md) —— 决策索引(Status + 一句话)
- 一个决策一文件(`00NN-<slug>.md`,NN = 原 D-NN 号可追溯)。记 why + 备选(防重复扯皮);**bug 修 / 诊断 / 取代的旧条目不进 ADR**(进 commit 或废弃,git 可查)。依据 ADR-0003。

## 游戏数据(策略地基,留游戏侧)
策略依赖的游戏数据(角色 / 阵营 / 装备 / comp / 经济 / 词缀 / boss)在 [docs/game/currency_war/data/](../../game/currency_war/data/)(游戏知识,米游社百科 V4.4 原文)。本目录只放**自动化设计**,不重复游戏数据(单一源,防漂移)。

## 代码引用稳定路径
代码注释引用本目录(strategy = 自动化设计)+ 游戏数据(留 game 侧):
- `cw_comps.py` → `docs/develop/currency_war/strategy/03_comp_planning.md`(阵容规划)
- `cw_decisions.py` → `docs/develop/currency_war/strategy/02_eval_search.md`(战术层 eval)
- `cw_performance.py` → `docs/develop/currency_war/strategy/10_battle_and_enemies.md`(观测反馈)
- `cw_chars.py` → `docs/game/currency_war/data/characters.md`(角色规范名,游戏侧)
- `cw_shop_odds.py` → `docs/game/currency_war/data/economy_research.md`(牌池参数,游戏侧)

## 关联 skill
- `od-dev-gameplay-automation`(玩法自动化 playbook + 策略设计 + 策略需求清单)
- `od-dev-write-application`(app 设计文档组织,本目录结构依据)
- 进度 / 临时调研 / 踩坑 → 本地 `.debug/temp/currency_war/`(不入 git)
