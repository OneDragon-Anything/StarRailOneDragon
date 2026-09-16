# execstate-dissolution 迭代设计（总纲）

## 0. 元信息

- 迭代目标：按用户裁定（2026-09-16，会话直接裁定）**解散 ExecState**（`kernel/cw_exec_state.py` 的 `ExecState` 状态载体）：①失败记忆删除（动作 op 已机械执行零判效）；②防重入旗标删除（策略实现侧自行记录）；③对账期望账删除（统一为动作 op 上报动作、game state 独占处理）；④接管/恢复类字段迁移 GameState。载体类与访问口随之拆除，全部消费点迁移，正本文档同步。
- 状态：草案
- 文档清单：无独立详设——本篇 §2 即完整设计（逐字段处置表 + 各族迁移动作），深度按「实现者无需再设计」标准写。

## 1. 问题与动机

- 现状症状：`ExecState`（27 具名字段）是 session 三态分离时代（用户 2026-09-06 裁定，`flow/session.md` as-designed）的第三类载体。其后 GameState（统一 state）波次已陆续收编其内容：tracked 主账宿主迁 `GameState.tracked_books`、效果账本正本归 `GameState.effects`、双账比对退役、对账唯一发生点收拢到观察边界。残余字段与现行架构三原则（[architecture.md](../../architecture.md) 职责铁律：对账只在观察边界、逻辑态写入 game state 独占、策略消费口唯一）呈三种冲突形态：死面（失败记忆无写端/无读者）、双源（防重入旗标与 GameState `node_screen_refresh` 域并存、GameState 字段「先申报无写端」）、宿主错位（接管/恢复是局内事实，挂在执行侧载体）。
- 根因归层：**约定层**——「执行层状态」这个类目本身在 GameState 成为一统的局内事实容器后失去存在依据；残余字段按其真实语义各自归位（删/策略器/GameState），类目整体退役。
- 解决到哪：ExecState 状态载体**整体消失**（类 + `exec_state_of`/`bind_exec_state` + 局容器字段），19 个具名字段逐一按 §2 处置表落位。模块 `cw_exec_state.py` 本体保留（宿主槽位表/BenchChar/`apply_op_effect`/换算函数等**领域模型与纯函数**，非状态）。
- 明确不解决：①`cw_exec_state.py` 模块改名/拆分（领域函数另有归属演进，另案）；②session 三态分离中「观察数据→StrategySession / 策略器状态→MandateState」两类（现行有效，不动）；③`apply_op_effect` 内 owned 写点仍写 `session.last_owned_equips` 的宿主问题（owned 正本迁 GameState 属效果/库存域建模批，本迭代不动，只随字段迁移改必要的宿主解析）。

## 2. 方案（逐字段处置表 + 各族迁移契约）

来源裁定：用户 2026-09-16 四条（按「失败记忆/防重入/对账期望账/接管恢复」四类给出）；未点名字段按其语义归入最近族，归属判据 = **谁产生/谁消费**（与 session.md §2 同判据）。消费点依据 = 全仓 grep（2026-09-16 盘点，行号快照见各字段行内注）。

### 2.1 逐字段处置表

| # | 字段 | 族 | 处置 | 去向与迁移契约 |
|---|---|---|---|---|
| 1 | `deploy_fail_counts` | 失败记忆 | **删** | 死字段：全仓仅定义处（cw_exec_state.py:111），零写端零读者。直接删。 |
| 2 | `equip_drag_fail_counts` | 失败记忆 | **删** | 无写端（全仓仅定义 + cw_equip_wear_plan.py:53/402/470 三处死读，读恒空 dict）。删字段 + 删三处死读路径（穿戴计划拉黑逻辑随之消失——机械执行零判效下无失败可记）。 |
| 3 | `megastar_candidate_clicked` | 防重入 | **删，策略器记录** | 迁 `MandateState` 具名字段 `megastar_clicked: bool`（mandate_v1 私有；语义原样平移：巨星节点内已点候选，observe 门 miss = 节点完成即复位）。写读点 = `cw_screen_megastar.py`（:119 复位/:147 读/:175 置位），经 `state_of(session)` 访问函数（执行层读写策略状态合法通道，flow/README §2.5；字段缺省 False 防御 getattr）。 |
| 4 | `_supply_refresh_used` | 防重入 | **删，接 GameState 写端** | GameState `node_screen_refresh.supply_refresh_used`（§3.4.2 字段位已在，「写端未接」申报终结）：刷新发射即 `write_logic` +1（动作上报口径，渠道②；「发射即记不等验效」语义原样平移）。读点 `cw_screen_supply_node.py:246` 改读容器字段。 |
| 5 | `_encounter_refresh_used` | 防重入 | **删，接 GameState 写端** | 同上 → `encounter_refresh_used`（§3.4.1）。写点 `cw_screen_encounter.py:175`；读点 :316/:443 改读容器字段。 |
| 6 | `_invest_refresh_used_slots` | 防重入 | **删，接 GameState 写端** | 同上 → `strategy_refresh_used` 逐卡计数（§3.4.4，键 = 规范卡名）：刷新发射即对应卡 +1。visit 起点清零语义（cw_screen_invest_strategy.py:294）随容器字段口径消失——容器字段为**局内累计计数**，节点内至多一次的硬限制 = 决策读计数对照注册表余量口径（§3.4.4 值域纪律），不再依赖 visit 清零集。读点 :330/:468 改读容器字段。 |
| 7 | `pending_buy_expect` | 期望账 | **删** | 买牌单元期望态机制整体拆除：`cw_prep_expect.py::BuyExpect/compare_buy_expect/build_*` + `cw_screen_prep.py` 消费点（:3097-3101 消费、:3485 写入、`_reconcile_buy_expect` :1396）。对账归一：动作上报经 `apply_prep_action_logic`/`apply_shop_action_logic` 写逻辑态，观察边界 `cw_reconcile` + observe 失配台账兜底（现行主路径，两态制 ADR-0651）。留证截图族（`_save_buy_evidence`）随消费点去留逐点核：无消费即删。 |
| 8 | `xp_expect_ledger` | 期望账 | **删** | `XpLedger` + `_xp_ledger` 取存（cw_screen_prep.py:1477-1486）+ telemetry 快照读点（schema.py:473 字段 `xp_expect_ledger` 随行删——遥测 schema 变更，decisions 行两文件模型不受影响）。xp 对账归一：LevelUp 金/经验腿 = `apply_prep_action_logic` 直写（批2b 已翻转），观察覆盖兜底。 |
| 9 | `cw_prep_pending_accts` | 期望账 | **删** | 备战挂起对账单元队列 + 消费段 `_v2_post_frame_accounting`（cw_screen_prep.py:1988-1990/2098-2100/2194-2196/2297-2299）整体拆除——同 #7/#8 归一。 |
| 10 | `_supply_detour_done` | 死面 | **删** | 全仓仅定义处（cw_exec_state.py:173），零消费者。 |
| 11 | `_pending_chosen_supply` | 期望账 | **删，直写容器** | 补给选定暂存（写 :295 / 取走 :162-180）拆除：选定确认时点直接 `write_logic` 写 GameState 选择结果域 `chosen_supply`（域规格 = game_state/README §3.3「②选择 handler 单次逻辑写」；字段在册）。出口验真保留为观察面（标识消失 = 观察事实），不再做「验真后才写」的前置门。重入弃旧语义随暂存消失：重复确认 = 重复逻辑写（观察赢覆盖，无账可污）。 |
| 12 | `cw_resumed_match` | 接管/恢复 | **迁 GameState** | 新容器字段（match_facts 域扩展，`resumed_match: Field[bool]`，渠道③接管协议 `logic_hook`）：写点 `cw_loop.py:1059`（`_mark_session_resumed` 单口内改写容器）、读点 `cw_observation.py:2694`（派生规则弹窗腿，改 `game_state_of`）。测试 test_cw_shop_unobserved_gate.py:212 同步。 |
| 13 | `cw_takeover_collect_done` | 接管/恢复 | **迁 GameState** | 同 #12 域：`takeover_collect_done: Field[bool]`。写点 cw_screen_prep.py:2415-2452（读改写三点）。 |
| 14 | `cw_takeover_tries` | 接管/恢复 | **迁 GameState** | 同上：`takeover_tries: Field[int]`。 |
| 15 | `star_regression_count` | 停机钩子簿记（未点名，归接管/恢复族——产生者 = reconcile 观察边界，消费 = 停机钩子判定） | **迁 GameState** | 非 Field 簿记容器槽（先例 = `tracked_books`/`settlement_ring`，非 Field 不进快照流水——历史累积计数器不符「只描述此刻」字段准入，cw_game_state.py 模块头 §8.8 治理）：`tracked_books.star_regression: dict[str, int]`。读写点 = `cw_reconcile.py:209/298`（唯一写读者，宿主解析改容器）。 |
| 16 | `bench_layout_epoch` | churn 事件通道（未点名，归接管/恢复族——reconcile 纠漂产物） | **迁 GameState** | `tracked_books.bench_layout_epoch: int`（同 #15 非 Field 簿记；坐标系注释原样平移：单调递增计数器，唯一写点 = cw_reconcile:387，消费点 = cw_screen_buy_cards.py:1002 / cw_shop_action_ops.py:247 改经容器解析）。 |
| 17 | `v2_round_key` / `v2_round_sold` | 轮内互斥账（未点名，归对账期望账族——动作上报写的事实账） | **迁 GameState** | 新容器字段组（`round_ledger_key: Field[tuple | None]` / `round_sold: Field[set[str]]`，渠道②动作）：`cw_round_ledger.py::register_round_sold`（:35-39）宿主解析改容器，轮键自校验语义逐字节不变；live 调用方 cw_shop_action_ops（卖出上报路径）不动签名。恢复局空集守卫语义不变（新局新容器即天然空）。 |
| 18 | `cw4_swap_fresh_buys` | 轮内互斥账（同 #17「本轮已买」半边） | **迁 GameState** | 新容器字段（`round_fresh_buys: Field[dict | None]`，键式注释原样平移）：`cw_deploy_logic.py::record_fresh_buy`（:965 已收 gs 参数，写点改容器字段）/`fresh_buys_of`（:984/:1018 读点改容器）/`fresh_buys_sell_face` 读端同。sim/live 同口（record_fresh_buy 单口不变）。 |
| 19 | `cw4_swap_arm_on` | 臂态位（未点名，归防重入族——执行面换血臂开合状态，判读面消费） | **迁 GameState** | 非 Field 簿记槽 `tracked_books.swap_arm_on`（判读面非局内事实，不进快照流水）：读写点 = cw_screen_deploy.py:642/:647 改容器解析。 |
| 20 | `plane_node_ledger`（含 `PlaneNodeLedger` 类） | 节点台账（未点名——观察采集的局内事实，归接管/恢复族语义最近：跨节点存续的局级事实） | **迁 GameState** | 容器字段（节点域扩展，`plane_node_sequences` 非 Field 簿记容器——整行快照语义、逐位合并写、低频重写，Field 化收益低；`PlaneNodeLedger` 类随迁 cw_game_state.py）：`get_node_ledger`/`ledger_node_type`/`ledger_update_plane` 三口**签名不变**，宿主解析改 `game_state_of`；全部写读点（cw_screen_prep/plane_intel/invest_env、obs/cw_observation、cw_equip_wear_plan、cw_equip_env、telemetry/schema、cw_vocab 转出口）零改动（经三口消费，无直摸）。 |
| 21 | `ExecState` 类 / `exec_state_of` / `bind_exec_state` / `CurrencyWarMatch.exec_state` / `cw_strategy.py` 绑定 | 载体 | **删** | 全字段迁毕后拆：类 + 两访问口 + 桩面存储（`_EXEC_BY_SESSION` 族）+ 局容器 dataclass 字段与 `__post_init__` 绑定（cw_strategy.py:206-211）。全仓 `exec_state_of`/`.exec_state` 调用点清零（grep 完成判据）；`test_cw_game_state_contract.py` §8 延迟绑定测试改写为容器绑定语义。 |

### 2.2 各族迁移契约（跨字段共用约定）

1. **GameState 新字段的治理**：#12-#14、#17-#18 走 Field（进 bs_schema 域映射与快照流水——它们是局内事实，值得记）；#15/#16/#19/#20 走**非 Field 簿记**（历史累积/事件通道/整表快照，不符「只描述此刻」准入，先例 = `tracked_books`/`settlement_ring`；模块头 §8.8 治理三件同判）。每字段的渠道签名：#4-#6/#17-#18 = `logic_action`（动作上报）；#12-#14 = `logic_hook`（接管协议）；字段注释带 `[索引定义]`/坐标系（规范硬门）。
2. **访问纪律**：全部消费点经容器读口/写口（`game_state_of`/`write_logic`），禁 getattr session 猜宿主——与 ExecState 时代 `exec_state_of` 单口同型，宿主换了、纪律不变。
3. **防重入的决策侧语义收口**：#4-#6 接容器计数后，「节点内至多刷一次」的判定 = 决策读计数对照注册表余量（遭遇/补给 1 次、策略逐卡口径 §3.4.4）；发射即计数（不等验效）保防重入时序，与现行「发射即置位」逐字节同语义。
4. **megastar 旗标的归属纪律**：#3 落 MandateState 后，op 对它的读写是「执行层读写策略状态」（合法通道 = `state_of(session)` 访问函数 + 防御 getattr）；字段定义注释带坐标系与复位时机（节点完成复位，写点 = op observe 门 miss）。
5. **sim 零改动申报**：sim 引擎不直摸 ExecState（grep 佐证：sim/ 目录无 `exec_state_of`/`.exec_state` 命中）；#18 经 `record_fresh_buy(session, gs, ...)` 单口自动切换宿主，sim 决策逻辑零改。
6. **遥测申报**：#8 删 schema 字段 `xp_expect_ledger`（伴随遥测 schema 变更：决策行两文件模型不受影响，删的是 state 快照行族字段——bs_schema/字段清单随 #12-#18/#20 同步，见正本更新清单）；supply 确认行的 `refreshed` 时点值读点（schema.py:642 注释锚）改读容器字段。

### 2.3 关键取舍

- **防重入为何不统一进 MandateState**：#3（megastar）的决策本体在策略器，落 MandateState 名正言顺；#4-#6 的刷新发射是**动作上报时点**（画面 op 发射位），GameState `node_screen_refresh` 域已为它们申报字段位（§3.4.1-3.4.4），接写端是兑现既有限定而非新设——且计数口径对 sim/回放可见（MandateState 不可见），A/B 判读受益。用户裁定「策略实现侧自己想办法记录」的落实形态 = 决策面读容器计数自行裁决（框架不再代管旗标）。
- **期望账为何整套删而非迁 GameState**：期望账的对账职能已被两态制吸收（逻辑态直写 + 观察边界失配台账）——`pending_buy_expect` 的「单元执行后应然态」与容器 logic 态是同构双账，双账比对又已退役（2026-09-15）；保留即维持第二对账通道，与「对账唯一发生点 = 观察边界」铁律冲突。
- **非 Field 簿记 vs Field 的分界**：进快照流水的判据 = 「该值是判读/决策要回看的局内事实」；历史累积计数（star 回退）、单调事件号（epoch）、臂开合位、整表台账是过程簿记/缓存，Field 化会让每帧写一行流水无判读收益。
