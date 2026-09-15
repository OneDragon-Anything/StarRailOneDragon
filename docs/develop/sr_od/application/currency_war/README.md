# 货币战争(currency_war)自动化设计

> 玩法本身(机制 / 数据 / 画面 / 攻略)见 [docs/game/currency_war/](../../../../game/currency_war/)(游戏知识,游戏版本改才变;经我们提炼核实的知识在其 `research/`)。
> **本目录 = 自动化实现设计**(bot 流程 / 策略 / 决策 / why,代码改才变)。
> 文档纪律:**as-built 无状态**(结构/语义/数据流/边界;值在代码、why 在设计文档动机段与代码注释、进度在本地进度账本);数字一律带三形态标注(【注】游戏定义/【推】已证推导/【拟】观测估计,章程 = strategy-docs/01 §6)。

## 入口

**先读全景图**:[architecture.md](architecture.md) —— 分层全景图(入口编排 / 画面 op+观察解析 / game state 内核 / 策略 / 动作 op / 遥测与档案 / sim / 支撑面)+ 逐层职责表 + 四条主线(观察线/决策线/动作上报线/记录线)+ 职责铁律(对账只发生在观察边界且由 game state 执行;逻辑态写入由 game state 独占;策略消费口唯一 = game state;sim 只模拟环境)。

## 文档区(正本)

| 区 | 管什么 |
|---|---|
| [architecture.md](architecture.md) | 全景图:模块分层与职责边界(代码树反向规格化) |
| [strategy-docs/](strategy-docs/README.md) | 策略设计:每个画面结合哪些数学证明、怎么产出决策(阅读顺序 / 宪法四条 / 三形态章程在其 README) |
| [screens/](screens/README.md) | 画面 op 层:**一画面一文档**(分发判定/形态/观察面/动作面/终结交回/状态上报面/守卫/遥测);能力矩阵 + 画面文档模板在其 README;层设计正本 = screens/op-layer.md(行为规范+基类机制+obs 工具箱) |
| [flow/](flow/README.md) | 流程控制:外循环路由(outer_loop)/ 动作执行契约(action_exec)/ 守卫总册(guards)/ 策略↔流程契约与入口链(README)/ session 三态分离(session)/ 逻辑态面交互契约(projection_contract) |
| [game_state/](game_state/README.md) | GameState 设计:容器理念与权威序(README)/ 字段级规格(fields)/ 记录机制(journal)/ 效果域/节点域/链观察/动作逻辑态总则与逐动作更新规格(logic-updates)/ 两本账(决策行文件 schema) |
| [proofs/](proofs/math_proofs.md) | 证明体系:命题状态索引(P 系列单篇在 `proofs/`,验证件在 `validations/`)——一切「多少算够」的定价权威 |
| [sim/](sim/sim-design.md) | sim 设计:体系总纲(sim-design)/ GameState↔引擎接线底账(sim-wiring)/ 战力模型需求定义(sim-power-model,deferred) |
| [config.md](config.md) | 用户配置设计(配置语义单一源;用户偏好才进配置) |
| `changes/` | 增量迭代设计(过程区,会不定期删减;代码与正本禁引其内容) |

决策 why 的归宿 = 设计文档动机段与代码注释(ADR 档案体系已退役,考古走 git 历史)。进度 / 焦点 / 待办 = 本地 `.debug/progress/` 当前活跃迭代账本(不入 git)。

## 代码引用稳定路径

- 策略实现 = `src/sr_od/application/currency_war/strategies/`(契约与管理器在 impl/,注册壳在顶层;策略↔流程契约见 [flow/README §2](flow/README.md))
- 画面 op = `operations/cw_screen/`(一画面一文件)+ `obs/`(观察解析工具箱);动作 op = `operations/cw_op/`(一动作一文件,单一注册表 `cw_action_registry.py`)
- GameState = `kernel/cw_game_state.py`(容器+单一转移函数族);编排 = `operations/cw_loop.py`
- sim/回放基建(`cw_sim`/`cw_replay`/`cw_match_recorder` 等)→ [sim/](sim/sim-design.md) + `sr-od-currency-war-dev` skill 的 sim-testing
- 注册表 = 游戏数据单一源(`data/cw_*`;生成器重跑流程见 [game 侧 README](../../../../game/currency_war/README.md))

## 关联 skill

- `sr-od-currency-war-dev`(CW 操作手册:分诊表 / 单一源地图 / 验证阶梯)
- `od-dev-gameplay-automation`(玩法自动化 playbook + 策略设计)
- `od-dev-write-application`(app 设计文档组织依据)
