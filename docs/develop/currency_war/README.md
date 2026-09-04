# 货币战争(currency_war)自动化设计

> 玩法本身(机制 / 数据 / 画面 / 攻略)见 [docs/game/currency_war/](../../game/currency_war/)(游戏知识,游戏版本改才变;经我们提炼核实的知识在其 `research/`)。
> **本目录 = 自动化实现设计**(bot 流程 / 策略 / 决策 / why,代码改才变;依据 `od-dev-gameplay-automation` ADR-0008:docs/game/ 只放游戏玩法,自动化归 docs/develop/)。
> 文档纪律:**as-designed 无状态**(结构/语义/数据流/边界;值在代码、why 在 ADR、进度在本地进度树——方法论 ADR-0210,已入 AGENTS.md);数字一律带三形态标注(【注】游戏定义/【推】已证推导/【拟】观测估计,章程见 strategy-docs/01 §6)。

## 目录结构(2026-09-04 文档树重画终态:策略决策与流程控制分家,零归档零底稿)

### [strategy-docs/](strategy-docs/) —— 策略设计(唯一现行语义家:每个画面结合哪些数学证明、怎么产出决策)
- [README](strategy-docs/README.md) —— 入口导航:阅读顺序 / 资产分工 / 宪法四条 / 文档纪律
- 总纲(跨决策点共享):[00 哲学与约束](strategy-docs/00_framework.md) / [01 数学框架](strategy-docs/01_math_framework.md)(公理栈+三形态章程+两条总纲不变量) / [02 骨架层](strategy-docs/02_mandate_layer.md)(三层权限+M1-M7) / [04 生存预算](strategy-docs/04_survival_budget.md)(h>d·L_c 唯一模型+hp 授权对账表 §7)
- 分篇(按决策点):[10 备战画面决策](strategy-docs/10_prep_decisions.md)(部署/装备/腾席+工具 7 件判据 §2.1) / [11 商店画面决策](strategy-docs/11_shop_decisions.md)(六序+买面+引擎池+卖出+刷新+升级) / [12 换线与意向](strategy-docs/12_line_and_intention.md) / [13 pick 族薄判据](strategy-docs/13_pick_family.md) / [08 事件面](strategy-docs/08_events.md)(E1-E15) / [07 跨局出辖](strategy-docs/07_meta_run.md)

### [flow/](flow/) —— 流程控制设计(执行骨架:怎么驱动策略产出决策)
- [README](flow/README.md) —— 总纲:四层图(外层循环→画面指挥→策略步进→动作执行)+ 策略↔流程契约(CwStrategy 17 接口/四身份分离)+ 守卫总览
- [outer_loop](flow/outer_loop.md)(画面路由/轮次推进/停机钩子) / [prep_visit](flow/prep_visit.md)(备战访问相位机) / [shop_visit](flow/shop_visit.md)(商店波次) / [action_exec](flow/action_exec.md)(三态发射契约) / [guards](flow/guards.md)(G3 守卫/降级链) / [screen_op](flow/screen_op.md)(画面 op 统一规范·ADR-0517 目态)

### [proofs/](proofs/) —— 证明体系(策略判据的数学背书,一切「多少算够」的定价权威)
- [math_proofs](proofs/math_proofs.md) —— 命题索引(P1-P57 状态与重建纪元);命题本体与 [validations/](proofs/validations/) 验证报告
- A/B 判据与结果一律落 proofs 命题单篇或 ADR 判据节,不建独立预注册文件(原 prereg/ 已删,git 历史可溯)

### [sim/](sim/) —— sim 设计文档(战斗结算层)
- [sim-power-model](sim/sim-power-model.md)(战力模型设计件,需求定义,ADR-0512) / [sim-wiring](sim/sim-wiring.md)(GameState↔sim 接线对照 as-built 底账)

### [decisions/](decisions/) —— 决策日志(ADR,一个决策一文件;INDEX 索引)

### [config.md](config.md) —— 用户配置设计(配置语义单一源;用户偏好才进配置,ADR-0203)

> 历史注记:本目录曾有 `strategy/`(v2 as-built 十二篇+底稿三件)、`AUTHORITY.md`、`archive/`(design/redesign 两树)与 `prereg/`——2026-09-04 用户裁定清理,内容已塌缩进 strategy-docs/ 与 flow/(逐节映射见塌缩批交付记录),原件全量可从 git 历史回溯。

## 代码引用稳定路径

- 策略实现 = `src/sr_od/application/currency_war/strategies/`(契约与管理器在 impl/,注册壳在顶层;架构见 [flow/README §2](flow/README.md))
- `cw_performance.py` 观测反馈层 → 代码 docstring + decisions/ 相关 ADR(旧 strategy/05 已随 v2 树清退)
- sim/回放基建(`cw_sim`/`cw_sim_checks`/`cw_replay`/`cw_match_recorder` 等)→ [sim/](sim/) + `sr-od-currency-war-dev` skill 的 verification.md(验证工作台:批量/对拍/Δ 池)
- 注册表 = 游戏数据单一源(生成器重跑流程见 [game 侧 README](../../game/currency_war/README.md))

## 关联 skill

- `od-dev-gameplay-automation`(玩法自动化 playbook + 策略设计 + 策略需求清单)
- `od-dev-write-application`(app 设计文档组织依据)
- 进度 / 临时调研 / 踩坑 → 本地 `.debug/temp/currency_war/`(不入 git)
