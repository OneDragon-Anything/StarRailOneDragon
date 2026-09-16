# execstate-dissolution 迭代设计（总纲）

## 0. 元信息

- 迭代目标：按用户裁定（2026-09-16，会话直接裁定）**解散 ExecState**（`kernel/cw_exec_state.py` 的 `ExecState` 状态载体）：①失败记忆删除（动作 op 已机械执行零判效）；②防重入旗标删除（策略实现侧自行记录）；③对账期望账删除（统一为动作 op 上报动作、game state 独占处理）；④接管/恢复类字段迁移 GameState。载体类与访问口随之拆除，全部消费点迁移，正本文档同步。
- 状态：定稿（r1 17 条修订 + r2 复审 17/17 闭合，前置补正 r2-A/r2-B/r2-C 已落）
- 文档清单：无独立详设——本篇 §2 即完整设计（逐字段处置表 + 各族迁移契约），深度按「实现者无需再设计」标准写。

## 1. 问题与动机

- 现状症状：`ExecState`（**21 具名字段**，与处置表 #1-#20+#21 逐一对应）是 session 三态分离时代（用户 2026-09-06 裁定，`flow/session.md` as-designed）的第三类载体。其后 GameState（统一 state）波次已陆续收编其内容：tracked 主账宿主迁 `GameState.tracked_books`、效果账本正本归 `GameState.effects`、双账比对退役、对账唯一发生点收拢到观察边界。残余字段与现行架构三原则（[architecture.md](../../architecture.md) 职责铁律：对账只在观察边界、逻辑态写入 game state 独占、策略消费口唯一）呈三种冲突形态：死面（失败记忆无写端/无读者）、双源（防重入旗标与 GameState `node_screen_refresh` 域并存）、宿主错位（接管/恢复是局内事实，挂在执行侧载体）。
- 根因归层：**约定层**——「执行层状态」这个类目本身在 GameState 成为一统的局内事实容器后失去存在依据；残余字段按其真实语义各自归位（删/策略器/GameState），类目整体退役。
- 解决到哪：ExecState 状态载体**整体消失**（类 + `exec_state_of`/`bind_exec_state` + 局容器字段），21 个具名字段逐一按 §2 处置表落位。模块 `cw_exec_state.py` 本体保留（宿主槽位表/BenchChar/`apply_op_effect`/换算函数/节点台账三访问函数等**领域模型与纯函数**，非状态）。
- 明确不解决：①`cw_exec_state.py` 模块改名/拆分；②session 三态分离中「观察数据→StrategySession / 策略器状态→StrategyState」两类（现行有效，不动；注意类名已由 MandateState 正名为 StrategyState，正本 flow/README §2.5 旧名随本迭代正本批修正）；③`apply_op_effect` 内 owned 写点仍写 `session.last_owned_equips` 的宿主问题（owned 正本迁 GameState 属效果/库存域建模批，本迭代不动）；④`session.star_pending_regression`（star 回退识别防抖，session 观察守卫字段）**留 session 不动**——它属观察数据类，不在本迭代辖域（与 #15 同机制但不同宿主与生命周期，#:15 处置时已声明二者关系）。

## 2. 方案（逐字段处置表 + 各族迁移契约）

来源裁定：用户 2026-09-16 四条（按「失败记忆/防重入/对账期望账/接管恢复」四类给出）；未点名字段按其语义归入最近族，归属判据 = **谁产生/谁消费**（与 session.md §2 同判据）。消费点依据 = 全仓 grep（2026-09-16 盘点 + 对抗审逐字段复核，见 attack.md 核验表）。

### 2.1 逐字段处置表

| # | 字段 | 族 | 处置 | 去向与迁移契约 |
|---|---|---|---|---|
| 1 | `deploy_fail_counts` | 失败记忆 | **删** | 死字段：全仓仅定义处，零写端零读者。直接删。**已落地**（commit 83ea60e5d）。 |
| 2 | `equip_drag_fail_counts` | 失败记忆 | **删** | 无写端（拉黑读恒空 dict）。删字段 + 拉黑函数族 + `_build_equip_wear_plan` 的 `exec_state` 形参（唯一调用方 mandate.py 同步收窄）。**已落地**（commit 83ea60e5d；实际文件面含 mandate.py/cw_op_equip_all.py，已回写 landing 3.1）。 |
| 3 | `megastar_candidate_clicked` | 防重入 | **删，策略器记录** | 迁 `StrategyState` 具名字段 `megastar_clicked: bool`（mandate_v1 私有；语义原样平移：巨星节点内已点候选，observe 门 miss = 节点完成即复位）。**访问通道 = kernel `strategy_state_of(session)`（None-safe 不冷建）**：读侧防御 getattr（None/异型退 False）；写侧仅在状态对象在位时写（缺席跳过，与现行为 `_match` None 跳过同型——禁从执行层冷建策略器状态）。写读点 = `cw_screen_megastar.py`（复位/读/置位三点）。 |
| 4 | `_supply_refresh_used` | 防重入 | **删，接容器写端** | GameState `node_screen_refresh.supply_refresh_used`（§3.4.2 字段位已在；sim 引擎已经 observe 通道在写，live 零写端）：live 刷新发射即 `write_logic` +1（渠道②；「发射即记不等验效」语义平移；**本屏无 on_outcome 注册件，写点 = `_do_action` 刷新分支单点，无双计面**）。读点 `cw_screen_supply_node.py:246` 改读容器计数（>0 语义）。telemetry supply 确认行 `refreshed` 时点值随本读点同步换源（归 3.3 阶段）。 |
| 5 | `_encounter_refresh_used` | 防重入 | **删，读点切容器** | 容器字段 `encounter_refresh_used` 写端**已在产**（`_emit_refresh_click` 经 on_outcome 发射型钩子 write_logic +1）。**只删 ExecState 置位行（:175），禁新增第二容器写点**（代码明示「双计即计数毒化」红线）；读点 :316/:443 改读容器计数对照（>0 = 已用）。 |
| 6 | `_invest_refresh_used_slots` | 防重入 | **删，读点切容器** | 容器逐卡计数 `strategy_refresh_used` 写端**已在产**（发射点 on_outcome 钩子写，测试在锁）。**只删 ExecState 侧**：visit 起点清零行（:294）与发射点 add 行（:330，系写点非读点）删除，禁第二容器写点；闸 2（:468 读点）改读容器逐卡计数 >0。visit 清零语义消亡申报：容器计数为局内累计，闸 1（屏上余量现读）+ 计数双闸下无重入放大面（终结动作化后每访问恰一次决策）。 |
| 7 | `pending_buy_expect` | 期望账 | **删** | 买牌单元期望态机制整体拆除：`cw_prep_expect.py::BuyExpect/compare_buy_expect/build_*` + `cw_screen_prep.py` 消费点（:3097-3101 消费、:3485 写入、`_reconcile_buy_expect`）。对账归一：动作上报经 `apply_prep_action_logic`/`apply_shop_action_logic` 写逻辑态，观察边界 `cw_reconcile` + observe 失配台账兜底（两态制 ADR-0651 现行主路径）。留证截图族（`_save_buy_evidence`）随消费点去留逐点核：无消费即删。 |
| 8 | `xp_expect_ledger` | 期望账 | **删** | `XpLedger` + `_xp_ledger` 取存（cw_screen_prep.py）+ telemetry schema 字段 `xp_expect_ledger`（schema.py:473）随删——**3.2 阶段仅删此 schema 字段；supply 确认行 `refreshed` 值不属本字段，归 3.3**（防遥测空窗）。xp 对账归一：LevelUp 金/经验腿 = `apply_prep_action_logic` 直写，观察覆盖兜底。 |
| 9 | `cw_prep_pending_accts` | 期望账 | **删** | 备战挂起对账单元队列 + `_v2_post_frame_accounting` 中的**期望账通道**（paddle 审计/drag_expect/equip_expect 三通道，输入全为 acct 暂存）整体拆除；**纯观察审计通道保留不动**（`_reconcile_faction_display`/`_reconcile_shop_pool`/`_reconcile_merge_preview`——零 ExecState 状态，非期望账）；方法签名随之去 acct 参。 |
| 10 | `_supply_detour_done` | 死面 | **删** | 全仓仅定义处，零消费者。**已落地**（commit 83ea60e5d）。 |
| 11 | `_pending_chosen_supply` | 期望账 | **删，确认即写容器** | 暂存拆除：选定确认时点直接 `write_logic` 写容器选择结果域 `chosen_supply`（域规格 = game_state/README §3.3「②选择 handler 单次逻辑写」）。**口径分叉显式申报**：supply 改「确认即写」，chosen_tome 维持「出口验真后写」家族口径不变——差异理由 = supply 的中转暂存正是本迭代要删的 ExecState 载体（裁定③），直写是载体消亡后的唯一形态；chosen_tome 无 ExecState 载体、不在本迭代辖域。确认未落地窗内 `chosen_supply` 短暂持未落地值：经 grep 无决策读者（仅写点与字段定义），低危可接受。出口验真保留为观察面。 |
| 12 | `cw_resumed_match` | 接管/恢复 | **迁 GameState** | 容器字段（match_facts 域扩展，`resumed_match: Field[bool]`，渠道③接管协议 `logic_hook`）：写点 `cw_loop.py::_mark_session_resumed` 单口内改写容器、读点 `cw_observation.py`（派生规则弹窗腿，改 `game_state_of`）。测试 test_cw_shop_unobserved_gate.py 同步。**gs_schema：match_facts 域内容变更 → bump 该域版本。** |
| 13 | `cw_takeover_collect_done` | 接管/恢复 | **迁 GameState** | 同 #12 域与渠道：`takeover_collect_done: Field[bool]`。写读点 cw_screen_prep.py 接管采集段三点。 |
| 14 | `cw_takeover_tries` | 接管/恢复 | **迁 GameState** | 同上：`takeover_tries: Field[int]`。 |
| 15 | `star_regression_count` | 留证采样簿记（未点名；**停机判定已退役**，现状 = reconcile 内「每 5 次回退存一张证、不 stop」的高频留证采样，段带删除预告「SIFT 身份修复后连同 `_star_stop_hook` 删」——attack [7] 修正） | **迁 GameState 簿记组**（不评估本迭代删：留证采样仍有消费，其退役前置 = SIFT 身份修复，另批） | 宿主 = **新增非 Field 簿记组 `ExecBooks`**（cw_game_state.py；执行侧过程簿记的容器内宿主组，**不塞 tracked_books**——后者契约 = tracked 主账槽位簿记，语义不容）：`ExecBooks.star_regression: dict[str, int]`。读写点 = `cw_reconcile.py`（唯一写读者，宿主解析改容器）。与 #16/#19 同组（见 §2.2-1b）。 |
| 16 | `bench_layout_epoch` | 纠漂簿记（未点名；reconcile 布局重排的 churn 代次通道——attack [14] 修正式族标签） | **迁 GameState 簿记组** | `ExecBooks.bench_layout_epoch: int`（坐标系注释原样平移：单调递增计数器，唯一写点 = cw_reconcile，消费点 = cw_screen_buy_cards.py / cw_shop_action_ops.py 改经容器解析）。 |
| 17 | `v2_round_key` / `v2_round_sold` | 死面（attack [1] 改判：原归「对账期望账族」按裁定③本应删） | **删（改判，原「迁容器」作废）** | 依据：①`v2_round_key` 全仓零写端（唯一维护者「决策层轮键重置段」属已删除的 decision_v2）→ `register_round_sold` 轮键守卫恒早退 = **永久 no-op** → `v2_round_sold` 恒空集；②买侧互斥消费面在 src 不存在（字段注声称的「engine_seed 禁买」已死），现役单一事实源 = mandate_v1 自有载体 `cw4_round_sold_names`；③给恒 no-op 机制新设容器 Field = 把第二已卖账铸进永久 schema 面，与 §2.3 删期望账的论证逐字同构。删除面 = 两字段 + `kernel/cw_round_ledger.py::register_round_sold` + 唯一调用桩 `cw_sell_bench_action.py:67-72`（调用方归属经对抗审修正：非 cw_shop_action_ops）。 |
| 18 | `cw4_swap_fresh_buys` | 轮内新鲜度账（「本轮已买」半边，动作发射写的事实账——在产活机制，与 #17 僵尸机制划清） | **迁 GameState Field** | 新域 `round_ledger`（**gs_schema 增域** + 对应版本项）：`round_fresh_buys: Field[dict | None]`，**值形状申报 = `{'phase': (plane, round) | None, 'names': list[str]}`**（现役 dict 内 set 改 list——快照行 JSON 序列化安全；record_fresh_buy 内部转形，读端成员判断在个位数量级无性能面）。写读单口不变：`cw_deploy_logic.py::record_fresh_buy`（已收 gs 参数，写点改容器字段）/`fresh_buys_of`/`fresh_buys_sell_face` 读点改容器解析；sim/live 同口（record_fresh_buy 单口不变）。键式与语义注释原样平移。 |
| 19 | `cw4_swap_arm_on` | 执行面观测闩（未点名；attack [14] 修正式族标签——原「防重入族」标签错误：它不是防重入，是换血臂开合的帧间状态，供判读） | **迁 GameState 簿记组（评估过删除，判保留）** | 保留理由 = 唯一消费「开合变更日志」是 projection_contract §4.3 在册判读面（臂态位），删 = 丢判读通道；其语义产生者 = 执行面逐环重评（非策略推导），不适用裁定②。宿主 = `ExecBooks.swap_arm_on`（不进快照流水）。读写点 = cw_screen_deploy.py 两点改容器解析。 |
| 20 | `plane_node_ledger`（含 `PlaneNodeLedger` 类） | 节点台账（未点名——观察采集的局内事实） | **迁 GameState** | 容器**非 Field 簿记** `plane_node_sequences`（整行快照语义、逐位合并写、低频重写，Field 化收益低）：**`PlaneNodeLedger` 类迁 cw_game_state.py；三访问函数（`get_node_ledger`/`ledger_node_type`/`ledger_update_plane`）与 `fill_boss_by_position` 留守 `cw_exec_state.py`（模块保留面），函数内惰性 import 类**——消费面（cw_vocab 转出口、cw_equip_wear_plan 直 import、obs/各画面 op）零改动申报由此闭合（attack [11]）。 |
| 21 | `ExecState` 类 / `exec_state_of` / `bind_exec_state` / `CurrencyWarMatch.exec_state` / `cw_strategy.py` 绑定 | 载体 | **删** | 全字段迁毕后拆：类 + 两访问口 + 桩面存储（`_EXEC_BY_SESSION` 族）+ 局容器 dataclass 字段与 `__post_init__` 绑定（cw_strategy.py）。**符号引用（import/属性访问/构造）全仓归零；注释历史锚不随符号删除自动消失，随正本更新清单逐条处置**（attack [16]）。`test_cw_game_state_contract.py` §8 延迟绑定测试删除（宿主消失，无可锁语义）。 |

### 2.2 各族迁移契约（跨字段共用约定）

1. **GameState 新字段的治理与 schema 面**：
   - **a. Field 组**（进 gs_schema 域映射与快照流水——局内事实，值得记）：#4-#6（node_screen_refresh 域，既有）；#12-#14（match_facts 域扩展——**域内容变更，bump match_facts 域版本**）；#18（**新增域 `round_ledger`** + 域版本项）。渠道签名：#4-#6/#18 = `logic_action`（动作上报）；#12-#14 = `logic_hook`（接管协议，relay 契约同族先例）。容器现役无 set 形 Field 先例——新增 Field 值形状一律 JSON 序列化安全形（#18 内嵌 set → list，见 #18 行）。
   - **b. 非 Field 簿记组 `ExecBooks`**（新 dataclass，cw_game_state.py；**独立宿主组，不塞 tracked_books**——TrackedBooks 契约 = tracked 主账槽位簿记，语义不容混装）：#15/#16/#19 宿主。判定依据 = 历史累积计数/单调事件号/帧间闩是过程簿记与判读面，不符「只描述此刻」的字段准入（模块头 §8.8 治理），但需局级存续与确定性清零（新局新容器）。
   - **c. 节点台账**：#20 非 Field 容器字段 `plane_node_sequences`（理由同 b：整行快照、逐位合并、低频重写）。
   - 每字段注释带 `[索引定义]`/坐标系（规范硬门）。
2. **访问纪律**：Field 组经容器读口/写口（`game_state_of`/`write_logic`）；ExecBooks 组经 `game_state_of(session).exec_books` 直读（非 Field 无渠道面，与 tracked_books 同型）。禁 getattr session 猜宿主。
3. **防重入的决策侧语义收口**：#4-#6 的「至多刷一次/逐卡余量」判定 = 决策读容器计数对照注册表口径（§3.4.1-3.4.4）；**encounter/strategy 容器写端已在产（on_outcome 钩子），本迭代只删 ExecState 半边，禁新增第二容器写点（双计毒化红线，cw_screen_encounter.py:133）**；supply 为唯一新接 live 写端（本屏无注册件，单点无双计面）。
4. **megastar 旗标的归属与通道**：#3 落 StrategyState；执行层读写策略器状态 = **kernel `strategy_state_of`（None-safe，不冷建）**——与 kernel 判据面同一通道；**禁用 impl 侧 `state_of` 从执行层调用**（其 None 冷建覆写副作用属策略器装配语义，执行层不得触发）。写端缺席态行为 = 跳过（与现 `_match` None 跳过同型）。正本 flow/README 补「执行层读写策略器状态通道」一句（正本清单）。
5. **sim 零改动申报**：sim 引擎不直摸 ExecState（全量 grep 佐证）；#18 经 `record_fresh_buy` 单口自动切换宿主，sim 决策逻辑零改；#4 supply 容器字段 sim 侧 observe 写端已有，live 写端接通后两源同域。
6. **遥测申报**：#8 删 schema 字段 `xp_expect_ledger`（3.2）；supply 确认行 `refreshed` 值换源随 #4（3.3，防 3.2→3.3 窗口遥测空窗——attack [9]）；gs_schema 域变更随 §2.2-1 申报。

### 2.3 关键取舍

- **防重入为何不统一进 StrategyState**：#3（megastar）的决策本体在策略器，落 StrategyState 名正言顺；#4-#6 的刷新发射是**动作上报时点**，GameState `node_screen_refresh` 域已为它们申报字段位且 encounter/strategy 写端已在产——删 ExecState 半边是兑现既有格局；容器计数对 sim/回放可见（StrategyState 不可见），A/B 判读受益。用户裁定「策略实现侧自己想办法记录」的落实形态 = 决策面读容器计数自行裁决（框架不再代管旗标）。
- **期望账为何整套删而非迁 GameState**：期望账的对账职能已被两态制吸收（逻辑态直写 + 观察边界失配台账）——期望态与容器 logic 态是同构双账，双账比对又已退役（2026-09-15）；保留即维持第二对账通道，与「对账唯一发生点 = 观察边界」铁律冲突。**同论证适用于 #17**（attack [1] 改判的依据）：`cw4_round_sold_names`（mandate 载体）已是现役单一事实源，v2 双字段是僵尸第二账，删而不迁。
- **#15 为何留证迁容器而非随删除预告删**：其退役前置 = SIFT 身份修复（识别质量批，另案）；在该批落地前留证采样是 star 误识别的唯一在环取证通道，删 = 裸奔窗口。宿主选 ExecBooks 独立组而非 tracked_books：混入会稀释 tracked 主账的申报契约（attack [14]）。
- **#19 为何保留而非删**：唯一消费是 projection_contract §4.3 在册的臂态位判读（开合抖动日志），删 = 丢判读通道；语义产生者 = 执行面重评，不适用裁定②的「策略侧记录」。
- **非 Field 簿记 vs Field 的分界**：进快照流水的判据 = 「该值是判读/决策要回看的局内事实」；历史累积计数（star 回退）、单调事件号（epoch）、帧间闩（臂态位）、整表台账（节点序列）是过程簿记/缓存，Field 化会让每帧写一行流水无判读收益。
