# turnstate-retirement 设计对抗报告

- **被审对象**：`design.md`（总纲，单文档方案）/ `landing.md` / `README.md`（本目录，2026-09-16 时点版本）
- **审查角色**：设计对抗（无前提；干净上下文）
- **日期**：2026-09-16
- **行号声明**：所有行号以本审查亲读时点的工作区为准（同仓多批并行在飞，行号随实现漂移，符号定位优先）。
- **权威源**：`flow/projection_contract.md` §6 G7（现状申报权威）、`docs/develop/harness/iteration-design.md` §3/§5/§7、`skills/sr-od-currency-war-dev/references/strategy-work.md` §1/§4/§6、项目 AGENTS.md。

---

## 发现清单

### F-1 [阻断] [核一·试读] 阶段1 迁移后、阶段2 删除前的中间态不可成立：`_budget` 迁出使 `assemble` 无法构造 TurnState

- **发现**：design §2.2 规定 `_budget` 与 `_disclose_budget` 合并为单函数 `disclose_budget(state, session, registry) -> None`（"BudgetView 载体死，算值直写披露字段，不保留中间结构"），landing §3.1 范围 = "assembly.py 披露链三函数迁 economy_cycle.py"，同时"不含 TurnState 符号删除（阶段2）；不含 assembly.py 剩余部的清理"。但 `assemble`（存活至阶段2）构造 `TurnState.budget` 的唯一途径就是调用 `_budget`：`turn_state.py::TurnState` 是 frozen dataclass、`budget: BudgetView` 必填字段（turn_state.py:98-104），`_budget` 是 BudgetView 唯一生产构造点（assembly.py:145-185，175 行构造）。阶段1 按文迁走三函数后：①`assemble` 调用 `_budget` 变 NameError，`test_cw_migration_direction_layer.py`（:70-73 import、:123/:131 调用，属阶段2 才处置的面）在阶段1 的 L1 全绿门必红；②若为保 assemble 而内联/保留预算现算，则与"迁出+合并不保留中间结构"直接矛盾，且实现者须自行设计中间形态——正是 iteration-design §5 规则2 的停手情形。
- **证据**：`strategies/impl/mandate_v1/assembly.py:145`（`_budget` 定义）、`:175-183`（BudgetView 构造）、`:184`（内嵌披露调用）、`:206-226`（`assemble`）；`strategies/impl/mandate_v1/turn_state.py:98-104`；`strategies/mandate_v1_strategy.py:55-58`（覆写调 assemble）；`sr-od-test/.../test_cw_migration_direction_layer.py:70-73,123,131`；design.md §2.2/§2.1 注；landing.md §3.1 范围行。
- **修正方向**（三选一，写入 §2.2 与 landing §3.1）：(a) 阶段1 只把披露**写路径**迁 economy_cycle（`disclose_budget` = 现算+直写），`assembly._budget` 保留至阶段2 随 `assemble` 同删，阶段1 同时摘除 `_budget` 内嵌的 `_disclose_budget` 调用防双写；(b) 把披露迁移整体并进阶段2，取消独立阶段1；(c) 阶段1 显式规定 `TurnState.budget` 的过渡供给形态。任何一项都须先过修订再定稿。

### F-2 [中危] [核一] §2.2 调用点1 的位置锚与「时点不变」主张在前置发射位短路帧上不相容

- **发现**：现状 `decide_prep_screen` 的顺序 = 方向代次消费 → `_launch_front_check` 短路 return → `_assemble_turn`（披露唯一触发点），因此 **armed 短路帧现状不披露**（bridge.py:185-196）。design §2.2 把新调用点锚在"帧内务段（方向代次消费之后）"——字面落点在发射位判定**之前**，armed 短路帧将**新增**披露四字段+键戳写；锚在"原 `_assemble_turn` 调用位（发射位判定之后）"才与"替代 assemble 内嵌披露、时点不变"等价。两种满足字面的落点产生可观测的遥测差异，与设计自报"零行为变化/时点不变"矛盾；§2 改后数据流图漏画前置发射位环节，加剧歧义（实现者二选一 = 违 iteration-design §5 规则2）。
- **证据**：`strategies/impl/mandate_v1/bridge.py:185-196`（顺序实证）；design.md §2.2 调用点1、§2 数据流图。
- **修正方向**：明写"调用点置于前置发射位判定之后、原 `_assemble_turn` 调用位（armed 短路帧维持不披露，与现状逐位一致）"；若编排者裁定要改为"每决策入口一次（含短路帧）"，须显式申报行为变化并同步修订判据与 A/B 口径。

### F-3 [中危] [核一] 披露面读端申报过期：「sim engine_p1 遥测链」已不存在；「sim batch 冒烟披露列产出」判据结构性不可满足

- **发现**：design §2.2 "读端 = recorder + sim engine_p1 遥测链"、§2.4 "读端（recorder/engine_p1）活跃"、§2.5 验收总门"验披露面在 sim 链仍产出"、landing §3.1 "sim batch 冒烟披露列产出不断流"。实证：①`engine_p1.py` 源文件已不存在（全仓 glob 仅剩 `sim/__pycache__/engine_p1.cpython-311.pyc` 死缓存；该名应为 2026-09-15 sim-redesign 前旧模块）；②sim 全目录 grep `v3_reserve|v3_release|reserve_cap|sess_|TurnState|decide_from_turn|entry.emit|assembly` **全部零命中**——sim 既不读披露字段也不触披露写点（prep 面 sim 不可达 = flow/README.md §2.4；run_buy_waves 不在 sim 链）；③sim 的 `disclosures` dict（cw_sim_engine.py）是"未建模面披露"机制，与预算四字段无关。现行活读端 = `telemetry/schema.py:480-500` 的 sess_* 透传 + `kernel/cw_decision_trace.py:121-139` 披露族封闭清单。结论（保留披露面）不受损，但依据是 ADR-0571 时代（2026-09-07）口径的转述未复审——正是 strategy-work §6 攻击纪律"码点直调复核禁转述"点名的错误类；且"披露列产出不断流"在 sim 链无对象：跑了也只能得到"结构性无帧"，按 strategy-work §4 恰是"禁把盲区读数当零值证据"的形态。
- **证据**：glob `src/**/engine_p1*`（仅 pyc）；grep sim 目录（零命中，见上）；`src/sr_od/application/currency_war/sim/cw_sim_engine.py`（disclosures dict 语义）；`docs/develop/sr_od/application/currency_war/flow/README.md` §2.4；`telemetry/schema.py:476-500`；`kernel/cw_decision_trace.py:121-139`。
- **修正方向**：读端申报改为"recorder sess_* 透传 + cw_decision_trace 披露族封闭清单"；sim 冒烟判据收窄为"决策分布无漂移"单一用途，并在可观测性申报中写明"披露面改动 sim 结构性不可见，披露产出验证归实机 recorder 行"（strategy-work §4 观测盲区申报义务）。

### F-4 [中危] [核一/核二] 阶段2 grep 清零判据与文件面冲突：两处命中点不在任何处置面

- **发现**：landing §3.2 判据"src + sr-od-test 全仓 grep `…|snapshot_from_obs|…|decide_from_turn` 零活引用"，但：①`strategies/impl/mandate_v1/adapter.py:4-5` 模块头"装配半部(…observe 端口 snapshot_from_obs/影子开关)落 app 桶 decision_assembly.py"——阶段2 后成死指针且直接命中 grep 判据；同文件 :13 "唯一消费 assembly.assemble 改容器单例直读"亦随 assembly.py 删除失锚（`assemble` 裸名不在判据里，判据抓不到，属漏改）；②`sr-od-test/.../test_cw_unified_action_2b.py:136-137` 注释"route_tag 透传面…由桥伴在 decide_from_turn 装载"——命中 `decide_from_turn` 判据。两文件均不在 design §2.3 清单、不在 §2.5 表、不在 landing §3.2 文件面。账本阶段以 landing 为单一源 → 按面执行则判据必红，按判据执行则越文件面——不可验收判据（iteration-design §5 规则4 防的事故形状；同型先例 = execstate-dissolution attack 对消费文件缺列的裁定）。
- **证据**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/adapter.py:1-21`（模块头全文）；`sr-od-test/test/sr_od/application/currency_war/test_cw_unified_action_2b.py:136-138`；landing.md §3.2 判据与文件面。
- **修正方向**：§2.3 增补 adapter.py 两处与 test_cw_unified_action_2b.py 一处；landing §3.2 文件面补列两文件（或判据加明示豁免行并说明归宿）。

### F-5 [中危] [核一] §2.3 失效指针清单系统性漏项（mandate_state.py 写端指针×3 等）

- **发现**：披露面迁移后一类"写端指针"注释集体失锚，§2.3 只覆盖了 shop.py 一处同款，漏掉：①`strategies/impl/mandate_v1/mandate_state.py:188-190/195-196/205-208` —— 披露四字段+键戳的字段定义注释三处写"写端=assembly._disclose_budget / _disclose_budget 每 prep 装配帧幂等覆写 / 写入端=assembly._disclose_budget"；这些是当期经济判读遥测列的**写入端声明**（注释规范"写入端"义务的承载面），阶段1 迁移即失真、阶段2 assembly.py 删除后全灭。mandate_state.py 不在 §2.3、不在 landing §3.1/§3.2 任何文件面。②`kernel/cw_economy.py:1147-1148` "同一调用链全部接缝必须传**同一个** registry 实例——prep_brain._budget 单源装配"：P6 纪律句仍有效，但锚例函数随批死亡。③`telemetry/schema.py:488` "轮界清零在装配键戳"（该文件已因 :301 decide_from_turn 指针在面内，但本处未点名，需同批改口径）。④`decision_assembly.py:133` "与 sim 合成器(runner.synthesize_snapshot)共享字段映射语义"——`synthesize_snapshot` 在 sim 树零定义（grep 实证），与 design §2.3 已点名的 contracts.py:23 同款失效叙事，未列。⑤`telemetry/match_archive.py:1267` "依赖 decision_assembly 对 readable=False 帧写"——若系历史档案判读口径描述则合法保留，落地时需逐字判别，§2.3 应给出判别规则。
- **证据**：上述行号均经亲读/grep 核实（`_disclose_budget|disclose_budget_at_shop_frame|v3_reserve_cap…` 全仓 grep 清单）。
- **修正方向**：§2.3 逐条补列，并按泛化义务以"写端=assembly._* / snapshot_from_obs / 装配键戳 / prep_brain._budget"为 grep 样式全仓反查一遍、命中处逐点处置（strategy-work §6"修复方不得只改被点名处不看同类"）。

### F-6 [中危] [核一/核二] `cw_screen_buy_cards.py` 注释修正属阶段2 范围，但阶段2 文件面漏列该文件（design↔landing 失同步）

- **发现**：design §2.3 明列"cw_screen_buy_cards.py「同一 BudgetView 链」注释"为失效指针（BudgetView 阶段2 才死），实证在 `operations/cw_screen/cw_screen_buy_cards.py:1028`。landing §3.1 文件面含该文件但仅限"调用点仅改 import"（阶段1）；**§3.2 文件面无此文件**，而 §3.2 范围声明含"§2.3 注释口径修正"——同一阶段小节内范围与文件面自相矛盾，worker 按"允许动的文件"验收会拒改或漏改。
- **证据**：`operations/cw_screen/cw_screen_buy_cards.py:1026-1043`；design.md §2.3；landing.md §3.1/§3.2 文件面行。
- **修正方向**：landing §3.2 文件面补列 `cw_screen_buy_cards.py`（注释）。

### F-7 [中危] [核一/核二] 正本更新清单漏项四处：收尾后正本仍声明已删符号

- **发现**：landing 正本更新清单已列 projection_contract §1 表两行/§3 不变式5/§4.1/§6 G7 与 flow/README L24+L92，但未列：①`flow/projection_contract.md:3` 头注定位句"（cw_state.GameState 面板 / 观察帧 / **TurnState 视图**）"；②`flow/projection_contract.md:75` §3 **不变式3**"**TurnState** 元素经 cw_state.py::snapshot_copy 浅拷贝…断开对象别名"（前半随 TurnState 死亡，需改写为 Snapshot 隔离承诺并申报 snapshot_copy 现役消费方；快照隔离不变式本体不得整条消失）；③`flow/README.md:93` §2.3 装配点条"obs→Snapshot **装配半部在 app 桶（decision_assembly）**"（该半部随批删除，与 L92 同段却未列）；④`flow/README.md:116` §3 篇导读"状态面板/**TurnState 视图** ↔ 执行臂的字段消费"。末阶段判据"清单清零；正本与实现一致"以清单为单一源 → 按清单清零后正本仍命名已删符号，"正本与实现一致"不成立（iteration-design §5 规则4"全量同步复查"、§3.2）。
- **证据**：上述四行均亲读核实；landing.md §正本更新清单（:36-41）。
- **修正方向**：清单补四行（不变式3 行须写明改写形态而非删除）。

### F-8 [中危] [核三] 本批将使 adapter.py 成为零消费全孤儿模块，设计未申报其归宿——与"不留新墓碑"立意相悖

- **发现**：adapter.py 在 src 的最后消费关系有两条：①`decision_assembly.py:22-24` import `PREP_SUBSTATE_NAME`——其唯一使用点是 `snapshot_from_obs` 的缺省参数（decision_assembly.py:130），随本批 #8 死亡；②`action_to_atomop`（adapter.py:111）全仓（src+sr-od-test）零调用点（grep 实证）；测试仓对 `mandate_v1.adapter|action_to_atomop|PREP_SUBSTATE_NAME` 零命中。阶段2 完成后 adapter.py = 零 import 方、零调用点的完整死模块原地留存。本迭代的立意正是清除"零消费仍计税"的孤儿（§1.2/§1.3；strategy-work §1 2026-09-16 改判"注记留码 = 垃圾代码"）；§1.3 外溢清单只登记了 adapter.py 的**墓碑注释行**，未登记**模块本体的孤儿化**——"本迭代删除完成后，Snapshot 契约族的生产消费方 = 零（仅测试与自引用）"的外溢立项输入也因此不准确（adapter.py 仍是对 contracts.AtomOp 的 src 级 import）。
- **证据**：`strategies/impl/mandate_v1/adapter.py`（全文亲读）；`decision_assembly.py:22-24,130`；grep `action_to_atomop|PREP_SUBSTATE_NAME|mandate_v1.adapter`（src 命中仅上两处+定义处；sr-od-test 零命中）。
- **修正方向**：二选一——①本批同删 adapter.py（无任何第三方消费，属同一删除面的自然收口）；②§1.3 外溢批立项输入补"adapter.py 模块本体（孤儿）"项，并把外溢表述修正为"生产调用链 = 零（adapter.py 为无调用方的存量 import，随外溢批处置）"。

### F-9 [中危] [核二] 同文件在飞协调缺账本载体：依赖栏未挂 execstate-dissolution，且协调面漏了 telemetry/schema.py

- **发现**：design §2.3 ⚠️ 申明"落地时按两迭代账本协调同文件在飞面"，但 landing §3.2 **依赖：阶段1**——账本立任务照阶段小节 `dag.py add`（iteration-design §3.1"阶段小节 = 账本唯一源"），依赖栏不含该前置 = 协调指令没有执行载体。实证冲突面实际是**两个文件**：execstate-dissolution landing §3.1-§3.6 多阶段文件面含 `kernel/cw_exec_state.py` 与 `telemetry/schema.py`（其 landing.md:9/17/30），turnstate 阶段2 也要动这两文件（cw_exec_state.py 注释三行、schema.py 的 decide_from_turn 指针 :301）——协调声明只覆盖了 cw_exec_state.py。该迭代明确在飞（其 attack.md 记载并行批已实际同窗改文件）。
- **证据**：`changes/2026-09-16-execstate-dissolution/landing.md:9,17,30`；design.md §2.3 ⚠️ 行；landing.md §3.2 依赖行。
- **修正方向**：landing §3.2 依赖补"execstate-dissolution 对应在飞阶段（防冲突最小前置，iteration-design §1.1）"，协调申报扩为两文件。

### F-10 [低] [核一] ADR-0571 权威指针指向不存在位置：主树已无 decisions/ 目录

- **发现**：design §0/§1.3/§2.2/§2.3/§2.4 多处引"decisions/ 下 ADR-0571"；实证 `docs/develop/sr_od/application/currency_war/decisions/` **不存在**（目录枚举+Test-Path 双确认；CW skill 亦申报"decisions/ ADR 档案已按用户令退役"）。ADR-0571 唯一存世副本在 `.debug/temp` worktree（`.debug/temp/t162_wt/main/.../decisions/0571-t88-dataflow-relink-r1-qualified-set-and-budget-disclosure.md`，不入 git）。裁决语义已由 assembly.py/mandate_state.py/schema.py 注释与 design §2.2 语义清单自足承载（本审已对照 worktree 副本核实 §2.2 写端/键戳语义引用**属实**），断链只伤可核验性与"持久索引"纪律。
- **修正方向**：引用锚改为现行可解析对象（如 mandate_state.py 披露字段注释、迁移后的 `economy_cycle.disclose_budget` docstring），并注明"ADR-0571 档案已按用户令退役，语义以现行代码注释为准"；落地面内的注释改写（§2.3 各处）同步采用此口径。

### F-11 [低] [核二] 三阶段完成判据均无「通用工程门（引用，不复述）」行；「§12 通用工程门」指针不可解析且未采用任一先例可解形态

- **发现**：iteration-design §3.1 模板要求判据含"<§12 通用工程门（引用，不复述）>"。本 landing 三阶段把 L1/ruff/L3 等**内联复述**（内容无错），无引用行；"§12 通用工程门"在全仓无可解析目标（先例裁定 = changes/2026-09-16-chain-observation-landing/attack.md F11）。仓内已有两种被裁定可解析的形态可循：实指引用（changes/2026-09-15-prep-single-action-contract/landing.md:14）或首节自包含定义（changes/2026-09-16-chain-observation-landing/landing.md:3）。
- **修正方向**：landing 首节加通用工程门单一定义（源标注项目 AGENTS.md「测试规范」「提交流程与协作边界」节）+ 各阶段判据改引用行。

### F-12 [低] [核二] §1.1 标题行"均已亲读核实"属过程叙事

- **发现**："（依据 = projection_contract.md §6 G7 + 代码锚，均已亲读核实）"——"亲读核实"是对写作过程的陈述，非系统事实；依据已就地标注，过程归对抗报告与账本（iteration-design §5 规则3 卡点："谁审的/已验"类措辞）。
- **修正方向**：删该短语，保留依据标注本身。

### F-13 [低] [核一·试读] §2.5 两处测试处置表述与实况有偏差（可执行但需 worker 补判断）

- **发现**：①test_cw_migration_direction_layer "不消费的保留原样"——该文件头 `from …assembly import (assemble, hoard_consumer_domain)`（:70-73）与 `contracts` import、`_snapshot` 助手（:74-95）随删除面死亡，保留的 4 个测试（P6 注入探针/局23 两锁/committed 直锁）必须同步清 import，否则 ImportError 连坐全文件——"保留原样"字面不可执行（L1 门会逼出正确行为，但表述应写实）。②test_cw_budget_disclosure "四字段+键戳断言逐条保留"——主锁断言右端引用 `turn.budget.reserve_cap/.obligation`（:189/:193/:227），载体死后须改为独立现算 oracle（文件内已有 `kernel_reserve_cap` 独立重算先例 :188），非机械保留；design §2.5 对 test_cw_economy 行已写明等价改写形态，本行宜同款。
- **修正方向**：§2.5 两行各补一句改写形态（import 清理义务 / oracle 独立重算）。

### F-14 [低] [核一] cw_exec_state.py 注释修正量申报"共三处"与 grep 实况 2 处不符

- **发现**：design §2.3 "snapshot_copy docstring 及相邻注释**共三处**"；grep `TurnState` 于 `kernel/cw_exec_state.py` 实命中 2 行：:438（`BenchChar.equips` 字段注释"TurnState 快照拷贝侧固化为 tuple"）与 :454（`snapshot_copy` docstring 首行"TurnState 快照语义的元素拷贝"）。若按注释块计数口径应写明；落地判据（阶段2 该文件 TurnState grep 清零）不受影响。
- **修正方向**：申报改为"两处（:438 注释块 + :454 docstring）"或写明计数口径。

---

## 结论

**存在阻断（1 项：F-1）。** 阶段1 作为"可独立派工、独立验收"的批（iteration-design §3.1 阶段粒度判据）在现行设计下不可执行：披露链三函数按文迁出后，存活至阶段2 的 `assemble`→`TurnState.budget` 供给链断裂，且设计未给出任何中间形态答案。定稿门槛（攻击收敛 + 试读过，iteration-design §6）未达，应停在草案修设计后再派落地。

**数量与分布**：共 14 项——阻断 1、中危 8（F-2…F-9）、低 5（F-10…F-14）；核一 9 项（F-1/2/3/5/6/7/10/13/14，另 F-4/F-7 双标核二）、核二 4 项（F-4/9/11/12，双标 2）、核三 1 项（F-8）。

**核三裁决**：①根因陈述**成立**——`entry.emit` 函数体（entry.py:435-946）对 `turn` 形参零使用、全仓对 `TurnState` 实例的 `.snap/.direction/.budget` 零生产读点、决策输入实证走 `obs.*` + `game_state_of(session)` 容器直读，G7 申报与代码一致，"架构层归层"判定正确。②本方案**修根**：物理删除未生效的理想态视图层、把事实通路转正为声明通路、纪律句随批对齐——非症状补丁；外溢划分（contracts.py Snapshot 契约族本体、全仓墓碑注清点）各自有独立问题→方案→验收闭环，成立；跨件半问通过外溢登记实现家族级收敛（TurnState 批 + Snapshot 契约族批 + 在飞 execstate 解散批同属"声明态与实现通路漂移"家族），不构成第三件症状补丁；唯一保留意见 = F-8（本批自己制造的 adapter.py 孤儿未入账）。③删除面主体经全量复核**无多删**：`assemble` 唯一生产调用方（mandate_v1_strategy.py:57）、`_assemble_turn` 唯一调用点（bridge.py:193）、`snapshot_from_obs` 唯一生产消费（mandate_v1_strategy.py:19）、`hoard_consumer_domain` src 零生产读点、`emit` 唯一生产调用方（bridge.py:338）、sim 与删除面完全无涉（grep 零命中）、`snapshot_copy` 保留判据准确（活消费方 = cw_game_state.py:2058-2064）、壳保留判据准确（cw_strategy_manager.py:205-221 强制注册 mandate_v1_strategy 模块壳）、contracts.py"sim 合成器"失效判定准确（sim 零 Snapshot 消费）——漏删面即 F-4/F-5 所列指针类。

## 试读清单（逐阶段「能否开工」判定）

| 阶段 | 判定 | 依据 |
|---|---|---|
| 阶段1（披露面迁移） | **不能开工** | F-1（阻断：`assemble` 预算供给无解）；F-2（调用点位置二义，armed 帧行为分叉）；F-3（"披露列产出不断流"判据无对象，须改写）。三处修订并入后可开工。 |
| 阶段2（物理删除） | **意图可辨，验收不可关闭** | 删除面本体凭 §2.1 表可执行；但 grep 清零判据命中面外文件（F-4）、§2.3 漏项（F-5）、文件面漏列（F-6）、在飞协调缺载体（F-9）——补全前面不可作账本 criteria。 |
| 末阶段（正本更新） | **按现清单清零 ≠ 收尾** | F-7 四处漏项，照单执行后正本仍命名已删符号，"正本与实现一致"判据不成立。 |

## 附录：实际攻击过的面（复核手段）

- 亲读：design.md/landing.md/README.md 全文；iteration-design.md 全文；strategy-work.md 全文；projection_contract.md 全文；代码 = turn_state.py、assembly.py、bridge.py、entry.py（1310 行全文）、mandate_v1_strategy.py、decision_assembly.py、adapter.py、cw_exec_state.py（snapshot_copy 段）、cw_economy.py（BudgetView 指针/P6 锚/schedule_upgrade 段）、mandate_state.py（披露字段段）、shop.py（必花域披露写点段）、cw_screen_buy_cards.py（店开披露段）、contracts.py（模块头+版本守卫）、mandate.py/cw_vocab.py/telemetry/schema.py（指针行）、flow/README.md 全文、cw_strategy_manager.py（强制注册段）、cw_decision_trace.py（披露族清单）；测试 = test_cw_budget_disclosure.py（401 行全文）、test_cw_migration_direction_layer.py（348 行全文）、test_cw_game_state.py（件3 段）、test_cw_economy.py（W636 A 锁段）、test_cw_prep_contract_shape.py（缝桩段）、test_cw_unified_action_2b.py（指针段）；execstate-dissolution 的 design/landing/attack（协调面）；ADR-0571 worktree 副本（§2.2 对照）。
- 全仓 grep（src 与 sr-od-test 分别执行）：`TurnState|DirectionView|BudgetView`、`_assemble_turn|snapshot_from_obs|decide_from_turn|hoard_consumer_domain`、`\bassemble\b|assembly\.|prep_brain`、`disclose_budget_at_shop_frame|_disclose_budget|v3_reserve_*|v3_release_*`、`snapshot_copy|action_to_atomop|require_schema_version|derive_snapshot`、`committed_from|hoard_target_set`、`entry\.emit|mandate_v1\.entry`、`refresh_ev_budget|schedule_upgrade|saturation_line|interest_floor`、`engine_p1`、sim 目录定向 grep 五组、`install_obs_ports|decision_assembly`、`mandate_v1\.contracts import`、`sess_reserve_cap|sess_release_*`、`通用工程门`。
- 存在性核验：decisions/ 目录（不存在）、engine_p1.py（不存在，仅死 pyc）、synthesize_snapshot（sim 树零定义）、ADR-0571 主树路径（不存在）。
