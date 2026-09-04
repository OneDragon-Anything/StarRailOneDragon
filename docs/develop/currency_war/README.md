# 货币战争(currency_war)自动化设计

> 玩法本身(机制 / 数据 / 画面 / 攻略)见 [docs/game/currency_war/](../../game/currency_war/)(游戏知识,游戏版本改才变;经我们提炼核实的知识在其 `research/`)。
> **本目录 = 自动化实现设计**(bot 流程 / 策略 / 决策 / why,代码改才变;依据 `od-dev-gameplay-automation` ADR-0008:docs/game/ 只放游戏玩法,自动化归 docs/develop/)。
> 文档纪律:**as-built 无状态**(结构/语义/数据流/边界;值在代码、why 在 ADR、进度在本地进度树——方法论 ADR-0210,已入 AGENTS.md)。

## 目录结构(复杂 app 拆分,依据 ADR-0003;2026-09-03 终态重组,2026-09 文档树重画批执行归档)

> **哪代文档现行、哪代只归档,唯一裁决表 = [AUTHORITY.md](AUTHORITY.md)**;本节只列结构。

### [AUTHORITY.md](AUTHORITY.md) —— 权威声明(代际裁决表/数字三形态章程/现行语义信谁)
### [strategy/](strategy/) —— 策略设计正文(唯一现行语义家;01-11 v2 as-built + 12 血预算/13 买面现行设计件)
- [README](strategy/README.md) —— 总览:为什么有策略 v2 + 每回合决策链 + 模块地图 + 核心哲学 + 边界 + 旧编号对照
- [01 姿态与经济](strategy/01_posture.md) / [02 阵容](strategy/02_comp.md) / [03 战术执行](strategy/03_tactics.md) / [04 节点决策](strategy/04_nodes.md) / [05 观测与遥测](strategy/05_observation.md) / [06 信息模型](strategy/06_input_model.md) / [07 策略插件](strategy/07_plugin.md) / [08 承接](strategy/08_p2_handoff.md) / [09 boss](strategy/09_boss_hp.md) / [10 成型停手](strategy/10_formed_stop_boss_mech.md) / [11 P1 保血](strategy/11_p1_exit_blood.md) / [11 工具使用](strategy/11_tools_usage_design.md)
- [12 血预算语义](strategy/12_blood_budget_semantics.md) / [13 买面设计](strategy/13_buy_face_design.md) —— 现行设计件(锚定新核 cw4)

### [proofs/](proofs/) —— 证明体系(策略判据的数学背书,系统设计依据)
- [math_proofs](proofs/math_proofs.md) —— 命题索引(P1-P51 状态与重建纪元)
- 命题本体 50 件(p08 扑满 EV/p24 残位填补支配性/p37 迟转成本/p41 囤卖 EV/p51 等待成本引理等)
- [validations/](proofs/validations/) —— 命题验证报告 56 件(五门验证/重推判决)

### [sim/](sim/) —— sim 设计文档(战斗结算层)
- [sim-power-model](sim/sim-power-model.md) —— 战力模型设计件(需求定义,唯一消费者=sim 战斗结算层,ADR-0512)
- [sim-wiring](sim/sim-wiring.md) —— GameState ↔ sim 引擎接线对照表(as-built 底账)

> 历史注记:本目录曾有 `prereg/`(A/B 判读预注册件,73 个文件)——2026-09 用户裁定为过程件整体删除(git 历史可溯);**A/B 判据/结果一律落 proofs 命题单篇或 ADR 的判据节,不再建独立预注册文件**。

### [decisions/](decisions/) —— 决策日志(ADR)
- [INDEX](decisions/INDEX.md) —— 决策索引(Status + 一句话)
- 一个决策一文件(`00NN-<slug>.md`,NN = 原 D-NN 号可追溯)。记 why + 备选(防重复扯皮);**bug 修 / 诊断 / 取代的旧条目不进 ADR**。

### [archive/](archive/) —— 历史档案(只读性质,不承载现行语义;各子目录来历见 AUTHORITY.md §2)
- [archive/redesign/](archive/redesign/) —— 重构工程史原树(章程/旧核分层设计/对抗与验证报告族 313 件,整体迁入)
- [archive/design/](archive/design/) —— 旧 design/ 原树(设计本意件 6 件+判据/锁存/遥测登记件;三个巨型堆叠件 IMPL_DESIGN/IMPL_FIX_LEMMAS/design_telemetry 在此,只读)

### [config.md](config.md) —— 用户配置设计(配置语义单一源)
- 目标用户画像(日常玩家 + 成就刷取)→ 配置面(角色/投资策略/投资环境 × 禁用/优先 + strategy_id)
- 归属判据:用户偏好才进配置;游戏客观数据归注册表、校准参数归代码(ADR-0203)。

## 代码引用稳定路径

- 模块职责地图(模块 → 设计文档)→ [strategy/README §模块地图](strategy/README.md)
- `cw_performance.py` → [strategy/05](strategy/05_observation.md)(观测反馈)
- `cw_shop_odds.py` 牌池证据 → [game/research/economy](../../game/currency_war/research/economy.md)
- sim/回放基建(`cw_sim`/`cw_sim_checks`/`cw_replay`/`cw_match_recorder` 等)→ [strategy/README §模块地图](strategy/README.md) + [strategy/05 §5](strategy/05_observation.md);验证工作台用法(批量/对拍/Δ 池)→ `sr-od-currency-war-dev` skill 的 verification.md
- 注册表 = 游戏数据单一源(对应 data 文档已删,ADR-0210;生成器重跑流程见 [game 侧 README](../../game/currency_war/README.md))

## 关联 skill

- `od-dev-gameplay-automation`(玩法自动化 playbook + 策略设计 + 策略需求清单)
- `od-dev-write-application`(app 设计文档组织,本目录结构依据)
- 进度 / 临时调研 / 踩坑 → 本地 `.debug/temp/currency_war/`(不入 git)

