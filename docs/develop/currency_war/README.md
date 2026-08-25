# 货币战争(currency_war)自动化设计

> 玩法本身(机制 / 数据 / 画面 / 攻略)见 [docs/game/currency_war/](../../game/currency_war/)(游戏知识,游戏版本改才变;经我们提炼核实的知识在其 `research/`)。
> **本目录 = 自动化实现设计**(bot 流程 / 策略 / 决策 / why,代码改才变;依据 `od-dev-gameplay-automation` ADR-0008:docs/game/ 只放游戏玩法,自动化归 docs/develop/)。
> 文档纪律:**as-built 无状态**(结构/语义/数据流/边界;值在代码、why 在 ADR、进度在本地进度树——方法论 ADR-0210,已入 AGENTS.md)。

## 目录结构(复杂 app 拆分,依据 ADR-0003)

### [strategy/](strategy/) —— 策略设计正文(as-built)
- [README](strategy/README.md) —— 总览:为什么有策略 v2 + 每回合决策链 + 模块地图 + 核心哲学 + 边界 + 旧编号对照(v2 重设计定稿 redesign.md 已砍除归档,ADR-0365;裁定史 ADR-0227)
- [01 姿态与经济](strategy/01_posture.md) —— DP 求解器(花钱节奏单一姿态源)/ 效果台账 / 息引擎 / 目标函数
- [02 阵容选择](strategy/02_comp.md) —— COMP_LIBRARY / select_comp·pivot·commit / 双轨过渡 / 审判层 / 跨局分配
- [03 战术执行](strategy/03_tactics.md) —— PrepDirector 决策环 / 动作全集 / plan·evaluate·bundle / 部署与装备
- [04 节点决策](strategy/04_nodes.md) —— 投资 / 遭遇 / 补给 / 巨星 / 伙伴 + 难度账本
- [05 观测与遥测](strategy/05_observation.md) —— reader 家族 / 对账 / PerformanceTracker / telemetry / 日志格式
- [06 信息模型](strategy/06_input_model.md) —— GameState 语义 / 注册表地图
- [07 策略插件](strategy/07_plugin.md) —— CwStrategy ABC / 发现机制 / replay 语义

### [decisions/](decisions/) —— 决策日志(ADR)
- [INDEX](decisions/INDEX.md) —— 决策索引(Status + 一句话)
- 一个决策一文件(`00NN-<slug>.md`,NN = 原 D-NN 号可追溯)。记 why + 备选(防重复扯皮);**bug 修 / 诊断 / 取代的旧条目不进 ADR**。

### [config.md](config.md) —— 用户配置设计(配置语义单一源)
- 目标用户画像(日常玩家 + 成就刷取)→ 配置面(角色/投资策略/投资环境 × 禁用/优先 + strategy_id)
- 归属判据:用户偏好才进配置;游戏客观数据归注册表、校准参数归代码(ADR-0203)。

### [power_table_meta.md](power_table_meta.md) —— 战力表校准数据(生成勿手编)
- `tools/cw/gen_power_table.py` 产物;`cw_power_table_data.py` 的人读对拍源。

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
