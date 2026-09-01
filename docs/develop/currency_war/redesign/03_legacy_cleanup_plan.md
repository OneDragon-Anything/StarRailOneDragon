# 旧策略代码处死清单与依赖图(Phase 3 前置盘点)

> **性质**:只读盘点(2026-09-01),未删未改任何代码/测试。处死授权与生死判据见同目录 [README.md](README.md) §2。
> **数字总览**:死刑/待判面共 **16 个源文件组、约 17,859 行**(不含测试);另 82 个测试文件 import 旧策略(随各自批次同死)。保留层有 **6 个文件**存在对旧策略的 import 边(ops 4 + telemetry 5 + 框架 context/app),处死前需解耦。

## 0. 盘点口径

- 死刑名单(redesign README §2「处死」)在册模块:`cw_intention` / `cw_recipe` / `cw_transition` / `cw_evolution` / `decision/` 全部(decision_v2 家族) / `cw_strategy*` / `cw_line_defs` / `cw_line_switch` / `cw_deploy_logic`(决策半部) / `cw_comps`(决策函数半部)。
- 依赖图 = 全仓真实 import 边(`from/import sr_od...` 正则提取,含 `src/`、`sr-od-test/`;`.debug/temp/` 隔离副本不计)。原始边清单存档 `.debug/temp/cw_death_imports.txt`(易失,可再生)。
- 消费者分类:**a**=纯旧策略互调(整体处死) / **b**=被 sim 引用(被测体替换点) / **c**=被保留层引用(需解耦/迁移符号) / **d**=被测试引用(旧测试同死)。

## 1. 处死清单(逐文件:路径 / 行数 / 职责)

### 1.1 kernel 判据族

| 文件 | 行数 | 职责一句话 |
|---|---|---|
| `kernel/cw_intention.py` | 1382 | 意向层:阵容方向锁定/配方锁/P1 配对/换线门判据,意向单一入口 |
| `kernel/cw_evolution.py` | 1414 | 进化层:board 卖出/保留/换血围栏与决策 |
| `kernel/cw_deploy_logic.py` | 276 | 部署逻辑:engines_count、TRANSITION_TRAITS、部署侧拍值判据(README 点名决策半部死;`TRANSITION_TRAITS` 数据被 telemetry/schema 消费 → 拆解件) |
| `kernel/cw_line_defs.py` | 202 | 流派定义表:core trio/recipe tier 等注册数据(数据半部被 telemetry/cw_win_model 消费 → 拆解件) |
| `kernel/cw_line_switch.py` | 342 | 换线判据:e_rounds/存轮门/换线事件 |
| `kernel/cw_transition.py` | 251 | 过渡阵容判据:过渡池→正式池判据 + TRANSITION_PACK(telemetry/query 消费) |
| `kernel/cw_recipe.py` | 95 | 配方表:量子配方 comp 与 decision_target 解析 |
| `kernel/cw_comps.py` | 2203 | **混合件(README「待判」)**:`COMP_LIBRARY`/机制克制表=数据保留为起点;`comp_score`/`select_comp`/equip_allocation 决策函数死 |
| `kernel/cw_strategy_session.py` | 311 | **接口件(glob 命中 `cw_strategy*` 但本质不同)**:StrategySession 每局跨步状态载体,纯 dataclass 零行为——建议不进处死序列,归 Phase 3 新策略接口设计裁决(见 §4) |

kernel 判据族小计:6,476 行(含两个拆解/接口件)。

### 1.2 decision/ 全家(11,112 行)

| 文件 | 行数 | 职责一句话 |
|---|---|---|
| `decision/cw_strategy.py` | 196 | 策略插件机制:CwStrategy ABC(12 钩子)+ CurrencyWarMatch 容器(挂 `ctx.cw_match`) |
| `decision/cw_strategy_manager.py` | 214 | 策略发现/注册 manager(目录扫描 + id 去重实例化) |
| `decision/decision_v2/`(23 文件) | 10,702 | v2 决策核:strategy(1075)/arbiter(1294)/discipline(1225)/scoring(1082)/allocator(642)/candidates(676)/posture_release(737)/remediation(637)/tier_push(491)/ev(342)/filters(413)/其余 adapter/contracts/director_v2/economy_cycle/handoff/phase/posture/prep_brain/realization/spend_gate/turn_state/__init__ |
| `decision_assembly.py`(app 桶) | 240 | 装配点:`install_obs_ports` 把 obs 读数注入决策(死名单内的装配侧) |
| `strategies/decision_v2_strategy.py` | 31 | 生产注册桥壳(DecisionV2Live,零逻辑) |

## 2. 依赖图(逐模块全部消费者,按 a/b/c/d 分类)

### 2.1 `kernel/cw_intention`(消费者最多,26 src + 38 test)

- **a 旧策略互调**:`cw_recipe`、`cw_evolution`、`cw_economy`(懒 import:schedule_upgrade 目标核心链,§3 批0 裁决)、decision_v2 全家 13 文件(candidates/discipline/ev/filters/handoff/phase/prep_brain/realization/remediation/scoring/spend_gate/strategy/tier_push)。
- **b sim**:`sim/engine_p1`、`sim/ledger_hooks`、`sim/checks/corpus`、`sim/checks/decision_v2`。
- **c 保留层**:`operations/prep/deploy_bench`(部署 op 读意向)、`operations/prep/shop`(刷新判据)、`telemetry/recorder`(`_to_jsonable`/`_derive_p1_pair`)、`telemetry/schema`(IntentionState 序列化)、`telemetry/state`(`_to_jsonable`)。
- **d 测试**:38 个 `test_cw_*`。

### 2.2 `kernel/cw_recipe`

- a:`cw_intention`、`cw_evolution`、decision_v2/strategy。
- c:`operations/prep/deploy_bench`。
- d:4 个 test(test_cw_deploy_ops / test_cw_release_endgame / test_cw_telemetry_archive / test_quantum_recipe)。

### 2.3 `kernel/cw_transition`

- a:`cw_recipe`、decision_v2/strategy。
- b:`sim/cw_replay`、`sim/engine_p1`。
- c:`kernel/cw_deploy_seat`(腾席判据,待判归属)、`operations/prep/deploy_bench`、`telemetry/query`(TRANSITION_PACK 显示标注)。
- d:16 个 test(crafted_scenarios / deploy_ops / round_flow / telemetry_archive / w628 / faction_fallback / framework_boot / hoard_boot / hoard_no_refresh / portal_bias / quantum_hoard / quantum_recipe / scenario_gen 等)。

### 2.4 `kernel/cw_evolution`

- a:decision_v2/strategy(唯一 src 消费者)。
- d:9 个 test。**无 sim/保留层运行时 import 边 → kernel 族里最先可整体处死**。

### 2.5 `kernel/cw_line_defs`

- a:decision_v2 discipline/phase/scoring、`cw_deploy_logic`。
- b:`sim/engine_p1`、`sim/checks/segments`。
- c:`kernel/cw_battle_calib`(recipe_tier/_CORE_TRIO)、`kernel/cw_system_cards`、`operations/prep/deploy_bench`、`telemetry/cw_win_model`(`_CORE_TRIO` 注册表真值)。
- d:11 个 test。

### 2.6 `kernel/cw_line_switch`

- a:`cw_intention`。
- c:`kernel/cw_first_passage`。
- d:4 个 test(intention_lock / levelup_gates / plane_p2 / release_endgame)。

### 2.7 `kernel/cw_deploy_logic`(拆解件)

- a:`cw_intention`、`cw_evolution`、`cw_line_defs`、`cw_discipline_rules`、decision_v2 candidates/discipline/economy_cycle/scoring/tier_push。
- b:`sim/engine_p1`、`sim/checks/segments`。
- c:`kernel/cw_battle_calib`、`operations/prep/deploy_bench`、`telemetry/schema`(TRANSITION_TRAITS)。
- d:10 个 test。

### 2.8 `kernel/cw_comps`(混合件:数据活/决策死)

- a(决策半部消费):decision_v2 candidates/discipline/filters/phase/remediation/scoring/strategy、`cw_economy`、`cw_intention`、`cw_recipe`、`cw_evolution`、`cw_line_switch`、`cw_deploy_seat`、`cw_junk_first`、`cw_equip_env`、`cw_events`、`cw_performance`、`cw_plugins`、`cw_strategy_session`。
- b:`sim/engine_p1`、`sim/engine_p2`、`sim/checks/ledger`、`sim/checks/segments`(消费 Comp 类型/池数据)。
- c(数据半部消费):`operations/battle_loop`、`operations/prep/equip_all`、`operations/prep/shop`。
- d:39 个 test(最大测试消费面)。

### 2.9 `decision/` 全家 + 装配

- **框架接缝(c)**:`src/sr_od/context/sr_context.py`(`ctx.cw_match: CurrencyWarMatch`,TYPE_CHECKING 注解)、`currency_war_app.py`(`install_obs_ports`)、`prep_director.py`(BuyExpect/XpLedger 装配)。
- **ops(c)**:`operations/battle_loop`、`operations/entry/start_currency_war_match`、`operations/prep/shop`。
- **b sim**:`sim/engine_p1`、`sim/engine_p2`、`sim/checks/corpus`、`sim/checks/decision_v2`。
- **d 测试**:82 个 test 文件(全仓 union,含仅 import `decision.cw_strategy` 取 StrategySession 桩的)。
- `decision_assembly` 消费者:`currency_war_app.py`、`prep_director.py` + 2 test。
- `strategies/decision_v2_strategy` 消费者:仅 StrategyManager 目录扫描(动态,无静态 import)。

### 2.10 `kernel/cw_strategy_session`(接口件,单列)

消费者 = kernel 保留/待判面(`cw_economy`、`cw_battle_calib`、`cw_discipline_rules`、`cw_line_switch`、`cw_intention`)+ `decision_assembly` + `decision/cw_strategy`。它是 kernel↔decision 断环的产物(纯 dataclass 载体),**sim 与 ops 不直接 import 它**。建议:随 decision/ 一起退役,但其字段清单是 Phase 3 新策略会话接口的输入(设计 01 已有对应物),新包就位后整文件删除。

## 3. 处死顺序建议(分批,每批 = 可独立删除 + sim 仍可跑)

**总原则**:decision_v2 是几乎一切边的汇聚点;sim 的策略被测体(engine_p1 直连旧策略)是唯一不允许断的运行面。所以顺序 = 先断 decision 核(被测体换成新策略桩/空桩),再剥 kernel 判据族,数据半部最后拆。每批伴随删除其 d 类测试。

- **批 0(前置解耦,只迁符号不删文件)**:把保留层消费的纯符号迁出死刑文件——
  1. `telemetry/schema`+`recorder`+`state` ← `cw_intention._to_jsonable/_derive_p1_pair/serialize_intention`、`cw_deploy_logic.TRANSITION_TRAITS`;
  2. `telemetry/cw_win_model` ← `cw_line_defs._CORE_TRIO`;
  3. `telemetry/query` ← `cw_transition.TRANSITION_PACK`(或该标注功能随旧策略退役,裁决点);
  4. `cw_economy` 对 `cw_intention` 的懒 import(schedule_upgrade 链)——先判语义:属决策函数则该消费点本身随批 1 删;属经济事实则迁入 cw_economy 本地;
  5. `cw_system_cards`/`cw_battle_calib` 对 `cw_line_defs`/`cw_deploy_logic` 的注册表消费迁入保留侧或数据注册表。
  完成判据:telemetry/ops 对死刑文件 import 边归零,sim 全量测试仍绿。

- **批 1(decision 核,11,623 行)**:`decision/decision_v2/` 全部 + `decision/cw_strategy.py` + `cw_strategy_manager.py` + `decision_assembly.py` + `strategies/decision_v2_strategy.py`。前置:新策略包(Phase 3 绿地)提供 CwStrategy 等价接口 + sim 被测体替换;`sr_context.cw_match`、`currency_war_app` 装配、`prep_director` 改接新接口;ops `battle_loop`/`start_currency_war_match`/`shop` 的决策调用点改接新接口。注意 `decision/cw_strategy.py` 的 ABC 钩子面是框架合同,其形状在新设计 01 已重定义——删旧前新接口必须先落。**⚠️ 执行门(裁决记录:docs/develop/currency_war/redesign/decisions/dd-001-ab-baseline-gate.md;01 §7 时序细化):批 1 拆两段——批 1a=改接新接口+新旧双被测体并存 selectable(不删,旧包作 A/B 基线);批 1b=「sim A/B 过线(新层不劣)」裁决后物理删除**。

- **批 2(kernel 判据族·低耦合,~2,100 行)**:`cw_evolution`(唯一 src 消费者已在批 1 死)、`cw_recipe`、`cw_line_switch`、`cw_transition`。前置:`cw_first_passage`(待判归属)、`cw_deploy_seat`、ops `deploy_bench`、sim `cw_replay`/`engine_p1` 的对应消费点迁移。

- **批 3(kernel 意向/部署 hub,~1,860 行)**:`cw_intention`、`cw_deploy_logic`、`cw_line_defs`。前置:批 0 全部解耦完成 + sim engine_p1/checks 的意向消费改接新策略。批 3 完成后 kernel 桶只剩保留/待判件。

- **批 4(cw_comps 拆解,2,203 行)**:`COMP_LIBRARY`/机制克制表等数据按新知识形态迁移(README §2「待判」授权)后,删决策函数半部;最后删除整文件。39 个测试中锁数据注册表的(test_cw_data_registry/test_cw_comps_library)改锁新家,其余同死。

- **批 5(接口件收尾)**:`cw_strategy_session.py` 在新策略会话载体落地后删除;`cw_discipline_rules`/`cw_first_passage`/`cw_deploy_seat` 等「待判」件按 README 逐件裁决(不在本清单强判)。

**sim 连续性**:批 1 是唯一必断 sim 的批次(被测体不存在即断);批 0/2/3 的 sim 边是 engine_p1/checks 对判据函数的点状消费,按批迁移即可,engine_p1 本体(1,998 行)属 sim 框架保留、其内部对旧策略的 import 是逐批清空的债。

## 4. 保留物清单核对(redesign README §2「保留」逐项现状)

| 保留项 | 现状核对 | 边界风险 |
|---|---|---|
| 知识层文档 `docs/game/currency_war/` | 存在,不受本次盘点影响 | 无 |
| 数据注册表 `data/cw_chars/cw_factions/cw_equipment_data/cw_shop_odds/cw_invest_data/cw_enemy_data/affix_effects_data/cw_battle_tables` | 全部存在,无对死刑文件的 import 边 | `cw_battle_tables`/`affix_effects_data`/`cw_synthesis` 注释提到 decision_v2/cw_comps 消费——仅文档性注释,无运行时耦合 |
| obs/(`cw_node_reader`/`cw_shop_obs`/`cw_equipment`/recognizers 等) | 存在,零对死刑文件 import 边(装配经 decision_assembly 端口注入,方向正确) | 批 1 删 decision_assembly 时端口注入点需由新装配接管 |
| ops 链(operations/) | 存在;**4 个文件有策略耦合点**:`prep/deploy_bench`(intention/recipe/transition/line_defs/deploy_logic)、`prep/shop`(intention/comps)、`prep/equip_all`(comps)、`battle_loop`+`entry/start_currency_war_match`(decision.cw_strategy/manager) | 批 1/3 需改接新策略接口;耦合点已全部列于 §2 |
| screen_info 建档 | 不受影响 | 无 |
| sim/(框架) | 存在;`engine_p1`(1,998 行)是最大策略耦合面,`engine_p2`/`checks/corpus`/`checks/decision_v2`/`checks/segments`/`checks/ledger`/`ledger_hooks` 也有点状 import | sim 被测体替换是批 1 硬前置(README「策略被测体替换」语义);替换期间 sim 的对拍基线数据不可丢 |
| telemetry/(判读口径) | 存在;recorder/schema/state/query/cw_win_model/match_archive 有符号级 import(批 0 解耦) | 序列化 schema 中旧意向字段(v3 意向状态/P1 配方对)处死后仍需可读历史档案——批 0 迁移时保留序列化形状 |
| `kernel/cw_state.py` 状态语义 | 1,509 行;**无对死刑文件的 import 边**(消费方向是别人 import 它) | 干净,Phase 3 可直接作为 GameState 字面量基线 |
| `kernel/cw_economy.py`(待判) | 693 行;事实函数(收入/息/卖退金/刷新价)在,但其头部 import cw_comps、懒 import cw_intention 的 schedule_upgrade 链属决策半部 | 批 0 第 4 项裁决;经济接缝族(§507 起)为批 1 下沉产物,语义可留 |

## 5. 待裁决件汇总(本次不强判,移交 Phase 3)

1. `cw_strategy_session.py`:随批 5 删 or 并入新策略会话设计;
2. `cw_economy` schedule_upgrade 消费链:决策(死) or 事实(迁);
3. `telemetry/query` 的 TRANSITION_PACK 显示标注:随旧策略退役 or 迁新家;
4. `cw_first_passage` / `cw_deploy_seat` / `cw_discipline_rules` / `cw_events`:README「按机制事实 or 决策拍值逐件分拣」在册件,依赖图已备好(§2),分拣时直接引用。
