# turnstate-retirement 迭代设计（总纲）

## 0. 元信息
- 迭代目标：TurnState 决策视图层退役物理删除（用户裁定 2026-09-16）。立项依据 = `flow/projection_contract.md` §6 G7（现状申报：TurnState 生产零消费、纪律表述与真实通路不一致）+ 同日用户裁定废除「墓碑注」退役形态（`skills/sr-od-currency-war-dev/references/strategy-work.md` §1 未证即退役通则③ 2026-09-16 改判：退役 = 物理删除，禁原位注记）。
- 状态：对抗审中
- 文档清单：无详设（单文档方案，本篇即完整设计）

## 1. 问题与动机

### 1.1 现状症状（依据 = projection_contract.md §6 G7 + 代码锚，锚以符号名定位）

- **视图层生产零消费**：TurnState（`turn_state.py` = Snapshot + DirectionView + BudgetView）每备战帧照常装配（`bridge.decide_prep_screen` → `_assemble_turn` → `assembly.assemble`），但决策实际输入 = `obs`（黑板 `session.prep_obs_frame`）+ `state_of(session)` 容器直读——`entry.emit` 的 `turn` 形参函数体内零使用（唯一生产调用方 = bridge `decide_from_turn` 内单一调用点）；`DirectionView` 全字段零生产读点；`hoard_consumer_domain` src 零生产读点（唯一消费 = test_cw_migration_direction_layer.py 测试）。
- **装配链专属件连坐成孤**：装配缝 `bridge._assemble_turn`（抽象缺省抛 NotImplementedError）+ `MandateV1Live` 覆写注入（mandate_v1_strategy.py，该壳唯一逻辑覆写）；`decision_assembly.snapshot_from_obs`（obs→Snapshot 观察端口）唯一生产消费方 = 该装配链（mandate_v1_strategy.py 唯一 import 调用）。
- **墓碑残留与纪律失真**：`DirectionView.bench_view`/`deployed_view` 退役留码（恒缺省空元组，每帧照付装配与 snapshot_copy 成本）；「决策判据一律消费 TurnState 幂等装配」纪律句（assembly.py 模块头与 `_disclose_budget` docstring、shop.py 注释、test_cw_budget_disclosure.py 头注）与真实通路矛盾，下游按 docstring 推依赖图得出错误结论（G7 影响栏原文）。

### 1.2 根因归层

**架构层**：设计蓝图 §2 的「决策数据件」（TurnState 幂等装配）未成为真实决策通路即零消费化，架构声明与实现通路漂移；漂移后被旧墓碑纪律（退役留注记）阻止物理清理，垃圾代码持续计税。本迭代 = 把现状真实通路（obs + 容器直读）转正为唯一通路，删掉未生效的理想态视图层。

### 1.3 解决到哪 / 明确不解决

解决到哪：
- `turn_state.py` 整模块（TurnState/DirectionView/BudgetView）物理删除；
- 装配链专属件删除：`assemble`/`_direction`/`hoard_consumer_domain`（assembly.py）、`_assemble_turn` 缝（bridge.py 抽象 + mandate_v1_strategy.py 覆写）、`snapshot_from_obs` 与 obs→Snapshot 装配半部（decision_assembly.py，删后余量为空则整模块删）、`adapter.py` 整模块（见 §2.1 #10）；
- `decide_from_turn` 改名 `decide_prep_frame` 并丢 `turn` 形参；`entry.emit` 丢 `turn` 形参；
- 预算遥测披露面（T-88 活通路，裁决语义锚 = mandate_state.py 披露字段注释 + 守卫锁 test_cw_budget_disclosure；ADR-0571 档案已按用户令退役，历史副本不入 git）**语义 1:1 迁移**保留（§2.2）；
- 失真纪律句与失效指针注释随批修正（§2.3）。

明确不解决（外溢，禁并入本迭代——iteration-design.md §1.1 边界判定）：
- **contracts.py 的 Snapshot 契约族本体**（Snapshot/SubstateClassification/Decision/AtomOp/Defer/Bail + `require_schema_version`/`derive_snapshot`）：本迭代只删其 obs→Snapshot 生产端与 adapter.py 载体；数据契约本体的退役牵接口形态历史裁决（ADR 档案已退役）、G8 权威表迁移挂账（flow/projection_contract.md §6）与「新循环契约族是否整体废弃」裁决，自成外溢迭代。本迭代删除完成后，Snapshot 契约族的 src 级生产消费方 = 零（仅测试与自引用；曾有的模块级 import 方 adapter.py 随本批删除）——该现状即外溢批立项输入。
- **全仓存量墓碑注清点**：新纪律（strategy-work §1 2026-09-16 改判）的首个全量执行批——statefn/vbar.py 墓碑模块、criteria/contracts.py 墓碑行、flow.py 墓碑注等（adapter.py 已随本批删除，不在其列），另批清点处置。

## 2. 方案

系统级变化一句话：**决策通路 = obs（黑板）+ session 容器直读（现状事实）转正为唯一通路；TurnState 视图层与其专属装配链物理删除；预算遥测披露面脱离装配语境独立存活，语义逐字段不变。**

改后数据流（对比 projection_contract.md §4.1 现时间线，删 assemble 环节，其余不变）：

```
备战节点入口 heavy 观察(唯一读屏点) → 黑板 session.prep_obs_frame
  → bridge.decide_prep_screen:方向代次消费(不变)
  → 前置发射位 _launch_front_check(armed 帧短路 return,不变;短路帧不披露 = 现状逐位保持)
  → disclose_budget(预算披露;落点 = 原 _assemble_turn 调用位,即前置发射位判定之后,非 armed 帧才到达)
  → decide_prep_frame(obs, session, ...) → entry.emit(obs, session, ...) 三遍编排(决策输入 = obs + 容器直读)
  → 帧稳定截断 → 执行(不变)
```

### 2.1 删除面（符号清单；消费方均经全仓 grep 核实，落地时按同名 grep 复核为验收步）

| # | 删除对象 | 位置 | 唯一/残余消费方与处置 |
|---|---|---|---|
| 1 | `TurnState`/`DirectionView`/`BudgetView` | `turn_state.py`（整模块删） | 生产零消费（G7）；测试消费 = test_cw_migration_direction_layer（装配面测试删）、test_cw_budget_disclosure（载体改）、test_cw_economy 注入锁（载体改），处置见 §2.5 |
| 2 | `assemble` | assembly.py | 唯一调用方 = mandate_v1_strategy.py 装配覆写（同批删） |
| 3 | `_direction` | assembly.py | 仅 assemble 内部调用 |
| 4 | `hoard_consumer_domain` | assembly.py | src 零生产读点；测试消费随 test_cw_migration_direction_layer 处置 |
| 5 | `_assemble_turn` 缝 | bridge.py 抽象 + mandate_v1_strategy.py 覆写 | 唯一调用点 = bridge.decide_prep_screen（改调披露，§2.2）；test_cw_prep_contract_shape 缝桩改（§2.5） |
| 6 | `decide_from_turn` → 改名 `decide_prep_frame`（丢 turn 参） | bridge.py | 调用点 = bridge.decide_prep_screen 内单一处；模块桩 = test_cw_prep_contract_shape（同步改名）；指针注释 = telemetry/schema.py、cw_vocab.py、mandate.py、test_cw_unified_action_2b.py（改写，§2.3） |
| 7 | `emit` 的 `turn` 形参 | entry.py | 函数体内零使用（G7）；唯一调用方 = bridge.decide_from_turn（同步改）；entry.py 顶部 TurnState import 同删 |
| 8 | `snapshot_from_obs` + obs→Snapshot 半部 | decision_assembly.py | 唯一生产消费方 = #5 装配链；测试 test_cw_game_state.py「件3」随删；删后 decision_assembly.py 若无剩余符号则整模块删 |
| 9 | mandate_v1_strategy.py 瘦身 | 注册壳 | 装配覆写与 snapshot_from_obs/assemble/TurnState imports 删；壳类本体保留——`__module__` 守卫要求壳类定义于本模块、StrategyManager discover 收尾强制注册（mandate_v1_strategy.py 模块头声明） |
| 10 | `adapter.py` 整模块 | strategies/impl/mandate_v1/adapter.py | 本批删除 #8 后成零消费孤儿：其 src 最后 import 方 = decision_assembly 对 `PREP_SUBSTATE_NAME`（唯一使用点 = snapshot_from_obs 缺省参数，随 #8 死亡）；`action_to_atomop` 全仓（src + sr-od-test）零调用点。留 = 本批自产新墓碑，故随批删 |

上表全部落阶段2；阶段1 仅 §2.2 搬迁面（原签名迁移，不删任何符号）。`snapshot_copy`（`cw_exec_state.py`）**保留**——TurnState 消失后仍有活消费方 = `cw_game_state.py` 部署装配 scratch 拷贝链。

### 2.2 保留面：预算遥测披露面 1:1 迁移（先立后破 = 阶段1 原签名搬迁，阶段2 随 BudgetView 死亡合并）

- 现状：披露链三函数住 assembly.py——`_budget`（预算现算，返回 BudgetView，内嵌披露写入）、`_disclose_budget`（写 MandateState 四字段 + 键戳）、`disclose_budget_at_shop_frame`（店开帧覆写写点）。现行活读端 = recorder sess_\* 透传（telemetry/schema.py sess_reserve_cap 族）+ cw_decision_trace 披露族封闭清单（kernel/cw_decision_trace.py）。assembly.py docstring 所载「sim engine_p1 轮快照」读端已亡：engine_p1.py 源文件不存在（仅存死 pyc），sim 全目录对披露字段 grep 零命中——该 docstring 系过期转述，随 assembly.py 删除消亡，本节按现行实况申报。禁令 = 禁决策消费（裁决语义锚 = mandate_state.py 披露字段注释 + 守卫锁 test_cw_budget_disclosure）。活通路，本迭代不删语义，只搬家与合并。
- **阶段1 形态（原签名搬迁）**：三函数迁 `mandate_v1/economy_cycle.py`（预算权威同文件：`obligation` 已在该文件；`reserve_cap`/`saturation_line`/`schedule_upgrade`/`refresh_ev_budget` kernel 接缝 import 关系不变），**签名与函数体逐字不变**——`_budget` 仍返回 BudgetView、内嵌披露调用不变（存活至阶段2 的 `assemble` 依赖它供 `TurnState.budget` frozen 必填字段，供给链不得断）；`disclose_budget_at_shop_frame` 函数名不变。assembly.py 改为 import；cw_screen_buy_cards 调用点仅改 import 路径；测试对 `_budget` 的 import 随迁（test_cw_economy）。零行为变化。
- **阶段2 形态（随 BudgetView 死亡合并）**：`_budget` 现算与 `_disclose_budget` 写入合并为单函数 `disclose_budget(state, session, registry) -> None`（算值直写披露字段，不保留中间结构）；`disclose_budget_at_shop_frame` 名称保留（内部改调新函数）。bridge.decide_prep_screen 删 `_assemble_turn` 调用行，改为在**原 `_assemble_turn` 调用位**调 `disclose_budget(...)`——即前置发射位判定之后，非 armed 帧才到达；armed 短路帧维持不披露，与现状逐位一致（若未来要 armed 帧也披露，属行为变化，另批立项）。
- 逐字段语义不变清单（验收锚，出处 = assembly.py `_disclose_budget` docstring，随批迁注于新函数）：reserve_cap/obligation 现算幂等覆写；overflow = `max(0, gold − reserve_cap)` 纯派生直算（禁二次调 economy_cycle.overflow 双算）；键戳 (plane, round) 变更 ⇒ spent/reason 清零后盖新戳；同键重入不清 spent。

### 2.3 注释与指针口径修正（随阶段2；落地时以泛化反查收口，禁只改点名处）

反查样式：`_disclose_budget|disclose_budget_at_shop_frame|snapshot_from_obs|prep_brain._budget|装配键戳|decide_from_turn` 于 src + sr-od-test 全仓 grep，命中处逐点处置。已知命中清单（符号定位，行号以落地时点为准）：

- 失真纪律句「决策判据一律消费 TurnState 幂等装配」：shop.py 注释处、test_cw_budget_disclosure.py 头注 → 统一改口径「决策输入 = obs（黑板）+ session 容器直读；披露面禁决策消费（语义锚 = mandate_state.py 披露字段注释与守卫锁）」。assembly.py 自身随批删除。
- 写端指针类：mandate_state.py 披露四字段+键戳的字段定义注释（多处「写端 = assembly._disclose_budget」）→ 改新写端 `economy_cycle.disclose_budget`；
- 锚例失效：cw_economy.py BudgetView.interest_floor 注释、「同一调用链同 registry 实例」纪律句的 `prep_brain._budget` 锚例 → 锚例改 `disclose_budget`；cw_screen_buy_cards.py「同一 BudgetView 链」注释 → 改口径；telemetry/schema.py 轮界清零「装配键戳」锚 → 改新键戳写端；
- decide_from_turn 改名指针：telemetry/schema.py、cw_vocab.py、mandate.py、test_cw_unified_action_2b.py 注释各一处 → 随 #6 改名；
- 失效叙事：contracts.py 模块头「sim 合成器(CwSimFrame→Snapshot)是无损门的第一个消费者」→ 改如实申报（sim 全目录对 Snapshot 零消费）；
- cw_exec_state.py 快照拷贝注释两处（`BenchChar.equips` 字段注释块 + `snapshot_copy` docstring）「TurnState 快照语义」表述 → 改「Snapshot 拷贝语义」并留保留理由（活消费方 = cw_game_state.py）。⚠️ 该文件是 execstate-dissolution 迭代在飞改面——本批只动这两处注释，协调载体见 landing 阶段2 依赖栏；
- match_archive.py「依赖 decision_assembly 对 readable=False 帧写」注释 → 判别规则：若为历史档案判读口径描述 = 合法保留原样；若为现行时态声明 = 随批改写；worker 按此规则逐字判别并在交付报告申报判定；
- adapter.py 模块头死指针、decision_assembly.py 失效叙事 → 随模块删除消亡（#8/#10），不单独改注。

### 2.4 关键取舍

- **披露面迁移而非同删**：备选 = 披露链随 TurnState 一起删 → 放弃。理由：读端（recorder sess_\* 透传 + cw_decision_trace 披露族）活跃，删 = 静默拔遥测；预算四字段是当期经济判读的现役遥测列。
- **阶段1 原签名搬迁而非合并**：合并形态（`disclose_budget -> None`）使存活至阶段2 的 `assemble` 失去 `TurnState.budget` 唯一供给（frozen 必填字段），阶段1 不可独立验收——先迁后并，合并归阶段2 随 BudgetView 死亡执行。
- **snapshot_from_obs 同批删而非外溢**：它是 TurnState 专属装配半部，留 = 立即新增墓碑，违 2026-09-16 改判纪律；contracts.py Snapshot 契约族本体牵历史裁决面与 G8，外溢另批（§1.3），边界清晰故可分批。
- **adapter.py 同批删而非外溢**：本批删除 #8 直接造成其孤儿化（零 import 方、零调用点），留 = 自己制造新墓碑；无第三方消费，属同一删除面的自然收口。
- **decide_from_turn 改名而非保留**：名内 "turn" 指向已死载体，留名 = 语义误导；成本 = 四处指针注释 + 一个测试桩名，可控。
- **披露落点 = 原 `_assemble_turn` 调用位**：备选 = 方向代次消费后立即披露 → 放弃。理由：前置发射位 armed 短路帧现状不披露，提前落点会新增披露写 = 行为变化，违本批零行为变化承诺。

### 2.5 测试重构面（测试仓 sr-od-test，独立提交）

| 测试文件 | 处置 |
|---|---|
| test_cw_budget_disclosure.py | `assemble(snap, sess)` 调用改 `disclose_budget(state, sess, registry)` 直调；断言右端 `turn.budget.*` 改独立现算 oracle（文件内已有 kernel 独立重算先例可循）；四字段+键戳断言逐条保留；头注纪律句改口径（§2.3） |
| test_cw_economy.py 注入一致性锁（W636 A） | 阶段1 仅 import 路径随迁；阶段2 载体改披露函数：注入 registry 后披露字段值 == 逐字段显式注入值（等价强度，不降锁） |
| test_cw_migration_direction_layer.py | 凡消费 assemble/DirectionView/hoard_consumer_domain 的测试删除；保留测试同步清 assembly/contracts import 与失活助手（防 ImportError 连坐全文件），保留测试本体原样 |
| test_cw_prep_contract_shape.py | `_assemble_turn` 实例桩删；`decide_from_turn` 模块桩改名 `decide_prep_frame` |
| test_cw_game_state.py「件3」（snapshot_from_obs 回退锚测试） | 随 snapshot_from_obs 删除 |
| test_cw_unified_action_2b.py | decide_from_turn 指针注释随 #6 改名（仅注释） |

验收总门：L1 快速集绿（`uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"`）+ 触点文件 ruff 零告警 + 一次 sim batch 冒烟（单一用途 = 决策分布无漂移确认；可观测性申报：本批改 assembly 策略层、sim 对披露面与删除面结构性不可见——披露产出验证归 test_cw_budget_disclosure 与实机 recorder 行，禁把 sim 盲区读数当零值证据）。本批设计上零行为变化，A/B 非裁决仅确认。
