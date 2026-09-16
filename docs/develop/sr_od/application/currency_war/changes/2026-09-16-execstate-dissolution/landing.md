# execstate-dissolution 落地

> 阶段小节 = 账本唯一源；设计依据指向 [design.md](design.md)（下称 design）§2 处置表行号（#N = §2.1 表行）。

## 3.1 死面与失败记忆删除

**范围**：design #1/#2/#10——删 `deploy_fail_counts`/`equip_drag_fail_counts`/`_supply_detour_done` 三字段；删 `cw_equip_wear_plan.py` 三处死读路径（:53 docstring 锚、:402-403、:470 读恒空 dict 的拉黑输入）。边界：不含防重入/期望账/任何 GameState 新字段。
**设计依据**：design §2.1 #1/#2/#10；§2.3（机械执行零判效下无失败可记）。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_equip_wear_plan.py`、`sr-od-test/`（受影响用例）。
**依赖**：无。
**优先级建议**：5
**完成判据**：
- 三字段名全仓 grep 归零（src + sr-od-test）；
- `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow and not legacy_baseline"` 全绿；
- ruff 过（改动文件）。
**验收凭据形式**：grep 输出 + 测试命令输出。

## 3.2 期望账拆除

**范围**：design #7/#8/#9/#11——删 `pending_buy_expect`/`xp_expect_ledger`/`cw_prep_pending_accts` 三字段及全部消费段（`_reconcile_buy_expect`/`_xp_ledger`/`_v2_post_frame_accounting` 挂起记账读写点）；删 `kernel/cw_prep_expect.py` 中随之无消费的 `BuyExpect`/`XpLedger`/`compare_buy_expect`/构建函数（模块内若余独立存活函数则留模块删类）；`_pending_chosen_supply` 暂存拆除，选定确认时点直写容器 `chosen_supply`（write_logic，选择结果域）；telemetry `xp_expect_ledger` schema 字段与 `refreshed` 时点值读点（schema.py:473/:642）随迁/删。边界：不含 cw_reconcile/observe 失配路径（已存在，不动）；不含防重入族。
**设计依据**：design §2.1 #7/#8/#9/#11；§2.2-1（渠道）；§2.3 取舍二。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_prep_expect.py`、`operations/cw_screen/cw_screen_prep.py`、`operations/cw_screen/cw_screen_supply_node.py`、`kernel/cw_game_state.py`（仅 chosen_supply 写端若有缺口）、`telemetry/schema.py`、`kernel/cw_strategy_session.py`（头注字符串化注解清锚）、`sr-od-test/`。
**依赖**：3.1。
**优先级建议**：5
**完成判据**：
- 四字段名 + `BuyExpect`/`XpLedger` 符号在 src 全仓归零（存活函数除外，逐一注明）；
- 补给选定路径行为对照：确认即容器 `chosen_supply` 有值（测试断言）；
- CW 快速集全绿 + ruff 过。
**验收凭据形式**：grep 输出 + 新增/改写测试名 + 测试命令输出。

## 3.3 防重入移交

**范围**：design #3/#4/#5/#6——megastar 旗标迁 `MandateState.megastar_clicked`（op 经 `state_of(session)` 读写，复位时机 = observe 门 miss）；`_supply_refresh_used`/`_encounter_refresh_used`/`_invest_refresh_used_slots` 删除，GameState `node_screen_refresh` 三字段接写端（发射即计数，渠道 `logic_action`），读点改容器。边界：不含 megastar 决策逻辑变更（决策本体零改，只换状态宿主）。
**设计依据**：design §2.1 #3/#4/#5/#6；§2.2-1/-3/-4。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_game_state.py`、`operations/cw_screen/cw_screen_megastar.py`、`cw_screen_supply_node.py`、`cw_screen_encounter.py`、`cw_screen_invest_strategy.py`、`strategies/impl/mandate_v1/mandate_state.py`、`telemetry/schema.py`、`sr-od-test/`。
**依赖**：3.1。
**优先级建议**：5
**完成判据**：
- 三旗标字段名在 src 归零；`node_screen_refresh` 四字段写端在产（grep 写点）且「零写端期间禁按字段值做决策」申报段删除；
- megastar 防重入行为对照：同节点二次派发不重复点候选、observe 门 miss 复位（测试断言， MandateState 宿主）；
- CW 快速集全绿 + ruff 过。
**验收凭据形式**：grep 输出 + 测试名 + 测试命令输出。

## 3.4 轮内互斥账与臂态位迁 GameState

**范围**：design #17/#18/#19——`v2_round_key`/`v2_round_sold`/`cw4_swap_fresh_buys` 迁容器 Field（`round_ledger_key`/`round_sold`/`round_fresh_buys`，渠道 `logic_action`），`cw_round_ledger`/`cw_deploy_logic`（record_fresh_buy/fresh_buys_of/fresh_buys_sell_face）宿主解析改容器、签名不变；`cw4_swap_arm_on` 迁 `tracked_books` 簿记槽。边界：不含 cw_round_ledger 轮键语义任何变更。
**设计依据**：design §2.1 #17/#18/#19；§2.2-1/-2。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_game_state.py`、`kernel/cw_round_ledger.py`、`kernel/cw_deploy_logic.py`、`operations/cw_screen/cw_screen_deploy.py`、`sr-od-test/`。
**依赖**：3.1。
**优先级建议**：4
**完成判据**：
- 三字段名在 src 归零；`register_round_sold` 轮键自校验测试不变绿；`record_fresh_buy` sim/live 同口测试不变绿；
- CW 快速集全绿 + ruff 过。
**验收凭据形式**：grep 输出 + 既有测试名（不变绿）+ 测试命令输出。

## 3.5 接管恢复/簿记/节点台账迁 GameState

**范围**：design #12/#13/#14/#15/#16/#20——`cw_resumed_match`/`cw_takeover_collect_done`/`cw_takeover_tries` 迁容器 Field（渠道 `logic_hook`）；`star_regression_count`/`bench_layout_epoch`/`cw4_swap_arm_on` 归 tracked_books 簿记（#19 若未在 3.4 一并做则归本阶段）；`plane_node_ledger` + `PlaneNodeLedger` 类迁容器（`get_node_ledger`/`ledger_node_type`/`ledger_update_plane` 签名不变，宿主改 `game_state_of`）。边界：不含派生规则判定本体（cw_observation 弹窗腿逻辑零改，只换读源）。
**设计依据**：design §2.1 #12-#16/#20；§2.2-1/-2。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_game_state.py`、`kernel/cw_reconcile.py`、`operations/cw_loop.py`、`operations/cw_screen/cw_screen_prep.py`、`obs/cw_observation.py`、`sr-od-test/`。
**依赖**：3.1。
**优先级建议**：4
**完成判据**：
- 六字段名在 src 归零；节点台账三口消费点零改动（grep 佐证签名未变）；
- 恢复局旗标读写行为对照（测试断言容器宿主）；
- CW 快速集全绿 + ruff 过。
**验收凭据形式**：grep 输出 + 测试名 + 测试命令输出。

## 3.6 载体拆除

**范围**：design #21——`ExecState` 类、`exec_state_of`/`bind_exec_state`、桩面存储、`CurrencyWarMatch.exec_state` 字段与 `__post_init__` 绑定删除；全仓 `exec_state_of`/`.exec_state`/`ExecState` 残留清零；测试仓 `test_cw_game_state_contract.py` §8 延迟绑定测试改写为容器语义。边界：`cw_exec_state.py` 模块本体保留（槽位表/BenchChar/apply_op_effect/换算函数）；模块改名/拆分不在本迭代。
**设计依据**：design §2.1 #21；§1（模块保留边界）。
**文件面**：`kernel/cw_exec_state.py`、`strategies/impl/cw_strategy.py`、全仓残留调用点、`sr-od-test/`。
**依赖**：3.2、3.3、3.4、3.5。
**优先级建议**：6
**完成判据**：
- `ExecState`/`exec_state_of`/`bind_exec_state`/`.exec_state` 全仓（src + sr-od-test）grep 归零（模块内域函数与 `cw_strategy_session.py` 头注历史指针按正本更新处置）；
- CW 快速集全绿；L3 全量 `uv run pytest sr-od-test/ -m "not slow and not legacy_baseline"` 全绿；
- ruff 过。
**验收凭据形式**：grep 输出 + L3 测试命令输出。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.6。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `flow/README.md` §2.5：三类状态分离 → 两类（观察/策略器），执行层状态类目退役声明 + 本迭代指针语义（载体消失，簿记归所宿）← 3.6
- `flow/session.md`：§2.4 表（执行层落点列改注退役去向）、§2 统计行 as-built 注、§4 as-built 注 ← 3.6
- `architecture.md`：§一 分层图「cw_exec_state 执行态簿记」行、§六 表 cw_exec_state 行（改域函数职责描述）← 3.6
- `game_state/README.md` §3.3 域清单：node_screen_refresh 写端申报、match_facts 域新增三字段、轮内互斥账字段、节点域 plane_node_sequences ← 3.3/3.4/3.5
- `game_state/fields.md`：§3.4.1-3.4.4 写端接通与新字段逐字段规格（含渠道签名/坐标系）← 3.3/3.4/3.5
- `screens/megastar.md`：选中标记宿主改 MandateState ← 3.3
- `screens/supply.md`：刷新已用双写/「先申报无写端」段、`_pending_chosen_supply` 暂存节 ← 3.2/3.3
- `screens/encounter.md`：刷新已用宿主 ← 3.3
- `screens/invest_strategy.md`：visit 复位集改容器计数口径 ← 3.3
- `screens/prep.md`：对账边界节（挂起记账消费段拆除后的口径）← 3.2
- `screens/plane_intel.md`：台账宿主注 ← 3.5
- `screens/battle_wait.md`、`flow/projection_contract.md`：ExecState 符号锚清理 ← 3.6
