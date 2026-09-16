# execstate-dissolution 落地

> 阶段小节 = 账本唯一源；设计依据指向 [design.md](design.md)（下称 design）§2 处置表行号（#N = §2.1 表行）。修订基准 = attack.md 17 条（致命 [1] / 重要 [2]-[9] / 次要 [10]-[17]）。

## 3.1 死面与失败记忆删除

**范围**：design #1/#2/#10——删 `deploy_fail_counts`/`equip_drag_fail_counts`/`_supply_detour_done` 三字段；删 `cw_equip_wear_plan.py` 拉黑函数族与死读路径；`_build_equip_wear_plan` 去 `exec_state` 形参。
**设计依据**：design §2.1 #1/#2/#10；§2.3。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_equip_wear_plan.py`、`operations/cw_op/cw_op_equip_all.py`、`strategies/impl/mandate_v1/mandate.py`（后两文件 = 拉黑族 import 清理与调用面收签名，attack [4] 修正确认的实际爆炸半径）。
**依赖**：无。
**状态**：**已落地**（commit 83ea60e5d，T-1 done——账本首任务；文件面按实际执行回写）。

## 3.2 期望账拆除

**范围**：design #7/#8/#9/#11——删 `pending_buy_expect`/`xp_expect_ledger`/`cw_prep_pending_accts` 三字段及全部消费段（`_reconcile_buy_expect`/`_xp_ledger`/`_v2_post_frame_accounting` 期望账三通道：paddle 审计/drag_expect/equip_expect）；`_v2_post_frame_accounting` 的**纯观察审计通道保留不动**（faction_display/shop_pool/merge_preview，签名去 acct 参）；`cw_prep_expect.py` 随之无消费的 `BuyExpect`/`XpLedger`/`DragExpect`/`EquipExpect` 族拆除（存活函数逐一注明；r2-B）；`_pending_chosen_supply` 暂存拆除，选定确认时点直写容器 `chosen_supply`（**口径分叉按 design #11 显式申报注释**）；telemetry **仅删 `xp_expect_ledger` schema 字段**——supply 确认行 `refreshed` 值不属本阶段（归 3.3，attack [9]）。边界：不含 cw_reconcile/observe 失配路径；不含防重入族。
**设计依据**：design §2.1 #7/#8/#9/#11；§2.3 取舍二。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_prep_expect.py`、`operations/cw_screen/cw_screen_prep.py`、`operations/cw_screen/cw_screen_supply_node.py`、`kernel/cw_game_state.py`（chosen_supply 写端注释口径）、`telemetry/schema.py`（仅 xp 字段）、`kernel/cw_strategy_session.py`（头注清锚）、`sr-od-test/`。
**依赖**：3.1。
**优先级建议**：5
**完成判据**：
- 四字段名 + `BuyExpect`/`XpLedger`/`DragExpect`/`EquipExpect` 符号在 src 全仓归零（存活函数除外，逐一注明）（r2-B）；
- 补给选定路径行为对照：确认即容器 `chosen_supply` 有值（测试断言）；
- CW 快速集全绿 + ruff 过。
**验收凭据形式**：grep 输出 + 新增/改写测试名 + 测试命令输出。

## 3.3 防重入移交

**范围**：design #3/#4/#5/#6——megastar 旗标迁 `StrategyState.megastar_clicked`（**访问通道 = kernel `strategy_state_of`，None-safe 不冷建；禁 impl 侧 `state_of`**，design §2.2-4）；`_supply_refresh_used` 删除 + live 写端接容器（单点，本屏无注册件无双计面）；`_encounter_refresh_used`/`_invest_refresh_used_slots` 删除——**容器写端已在产（on_outcome 钩子），只删 ExecState 置位/清零/add 行，禁新增第二容器写点（双计毒化红线）**；三读点改容器计数对照；supply telemetry `refreshed` 值换源随 #4。边界：不含 megastar 决策逻辑变更；不含 `env_refresh_used`（不在范围，维持零写端申报不动）。
**设计依据**：design §2.1 #3/#4/#5/#6；§2.2-1a/-3/-4。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_game_state.py`、`operations/cw_screen/cw_screen_megastar.py`、`cw_screen_supply_node.py`、`cw_screen_encounter.py`、`cw_screen_invest_strategy.py`、`strategies/impl/mandate_v1/mandate_state.py`、`telemetry/schema.py`（refreshed 读点锚）、`sr-od-test/`。
**依赖**：3.1。
**优先级建议**：5
**完成判据**：
- 三旗标字段名在 src 归零；**三字段（supply/encounter/strategy）容器写端在产；`env_refresh_used` 维持零写端申报不动**（attack [5] 修正：非四字段）；
- megastar 防重入行为对照：同节点二次派发不重复点候选、observe 门 miss 复位（测试断言，StrategyState 宿主经 `strategy_state_of`）；
- encounter/strategy 刷新计数值与 3.3 前基线一致（单次刷新恰 +1，无双计——测试断言）；
- CW 快速集全绿 + ruff 过。
**验收凭据形式**：grep 输出 + 测试名 + 测试命令输出。

## 3.4 轮内账改判删除与新鲜度账迁移

**范围**：design #17/#18/#19——**#17 删**：`v2_round_key`/`v2_round_sold` 字段 + `kernel/cw_round_ledger.py::register_round_sold`（恒 no-op 僵尸）+ 唯一调用桩 `operations/cw_op/cw_sell_bench_action.py:67-72`（attack [1] 改判，原迁容器作废）；**`cw_round_ledger.py` 模块随唯一函数删除一并移除**（空壳 docstring 不留，r2-C）；**#18 迁**：`round_fresh_buys` Field（**新域 `round_ledger`** + gs_schema 域版本项；值形状 `{'phase': tuple|None, 'names': list[str]}`，record_fresh_buy 内部 set→list 转形，读端签名不变）；**#19 迁**：`cw4_swap_arm_on` → `ExecBooks.swap_arm_on`。边界：mandate `cw4_round_sold_names` 现役载体不动；`record_fresh_buy` 对外语义不变。
**设计依据**：design §2.1 #17/#18/#19；§2.2-1a/-1b/-2；§2.3 取舍三/四。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_game_state.py`（新域 + ExecBooks 组 + Field）、`kernel/cw_round_ledger.py`、`operations/cw_op/cw_sell_bench_action.py`、`kernel/cw_deploy_logic.py`、`operations/cw_screen/cw_screen_deploy.py`、`sr-od-test/`（**新增**：round_fresh_buys 宿主切换同口测试——attack [2] 修正：既有测试不存在，本阶段补）。
**依赖**：3.1。
**优先级建议**：4
**完成判据**：
- `v2_round_key`/`v2_round_sold`/`register_round_sold` 在 src 归零；`cw_sell_bench_action` 卖出落地路径行为对照（登记调用桩删除后落地零异常，测试断言）；
- `round_fresh_buys` 宿主切换同口测试绿（record_fresh_buy 写 → fresh_buys_of 读同容器，sim/live 同口）；
- `cw4_swap_arm_on` 在 src 归零，臂态位日志行为保留（容器宿主）；
- CW 快速集全绿 + ruff 过。
**验收凭据形式**：grep 输出 + 新增测试名 + 测试命令输出。

## 3.5 接管恢复/纠漂簿记/节点台账迁 GameState

**范围**：design #12/#13/#14/#15/#16/#20——`cw_resumed_match`/`cw_takeover_collect_done`/`cw_takeover_tries` 迁容器 Field（match_facts 域，**域版本 bump**，渠道 `logic_hook`）；`star_regression_count`/`bench_layout_epoch` 迁 **`ExecBooks`** 簿记组（design §2.2-1b；#15 族标签 = 留证采样簿记，#16 = 纠漂簿记）；`plane_node_ledger` 迁容器非 Field 簿记 `plane_node_sequences`，**`PlaneNodeLedger` 类迁 cw_game_state.py，三访问函数 + `fill_boss_by_position` 留守 cw_exec_state.py（函数内惰性 import 类）——消费面零改动申报的成立前提**（attack [11]）。边界：不含派生规则判定本体；不含 `session.star_pending_regression`（留 session，design §1 明确不解决④）；不含 `_star_stop_hook` 段退役（前置 = SIFT 修复，另批）。
**设计依据**：design §2.1 #12-#16/#20；§2.2-1b/-1c/-2。
**文件面**：`kernel/cw_exec_state.py`、`kernel/cw_game_state.py`、`kernel/cw_reconcile.py`、`operations/cw_loop.py`、`operations/cw_screen/cw_screen_prep.py`、`operations/cw_screen/cw_screen_buy_cards.py`、`operations/cw_op/cw_shop_action_ops.py`（后两文件 = #16 消费点，attack [3] 补）、`obs/cw_observation.py`、`sr-od-test/`。
**依赖**：3.1。
**优先级建议**：4
**完成判据**：
- 六字段名在 src 归零；节点台账三口签名不变（消费面 grep 佐证零改动）；
- 恢复局旗标读写行为对照（测试断言容器宿主）；match_facts 域版本 bump 落行（journal 断言）；
- CW 快速集全绿 + ruff 过。
**验收凭据形式**：grep 输出 + 测试名 + 测试命令输出。

## 3.6 载体拆除

**范围**：design #21——`ExecState` 类、`exec_state_of`/`bind_exec_state`、桩面存储、`CurrencyWarMatch.exec_state` 字段与 `__post_init__` 绑定删除；**符号引用（import/属性访问/构造）全仓归零**（attack [16] 修正口径；注释历史锚不在此判据辖内，随正本更新清单逐条处置——锚清单 = attack [16] 证据列）；`test_cw_game_state_contract.py` §8 延迟绑定测试删除。边界：`cw_exec_state.py` 模块本体保留（槽位表/BenchChar/apply_op_effect/换算函数/节点台账三访问函数）。
**设计依据**：design §2.1 #21；§1 模块保留边界。
**文件面**：`kernel/cw_exec_state.py`、`strategies/impl/cw_strategy.py`、全仓残留符号调用点、`sr-od-test/`。
**依赖**：3.2、3.3、3.4、3.5。
**优先级建议**：6
**完成判据**：
- `ExecState`/`exec_state_of`/`bind_exec_state` 的符号引用（import/属性访问/构造形态）在 src + sr-od-test 归零（`CurrencyWarMatch.exec_state` 属性访问同辖）；
- CW 快速集全绿；L3 全量 `uv run pytest sr-od-test/ -m "not slow and not legacy_baseline"` 全绿；
- ruff 过。
**验收凭据形式**：grep（符号形态）输出 + L3 测试命令输出。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.6。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `flow/README.md` §2.5：三类状态分离 → 两类（观察/策略器）+ StrategyState 正名（attack [8]）+ 执行层读写策略器状态通道一句（`strategy_state_of` None-safe，design §2.2-4）+ 执行层状态类目退役声明 ← 3.6
- `flow/README.md` §2.2：「期望态对账保留(现行有效)」句随 #9 失真，改两态制归一口径（attack [15]）← 3.2
- `flow/session.md`：§2.4 表（执行层落点列改注退役去向）、§2 统计行 as-built 注、§4 as-built 注；**§2.4 v2_round_* 行（「活写端 = register_round_sold / live 调用方 = cw_shop_action_ops」两断言已死）、§3.2 风险表同轮已卖集行、§6.2-4 恢复轮判读义务、§6.1 迁移指令对应句——随 #17 删除一并修正**（r2-A，← 3.4）← 3.4/3.6
- `architecture.md`：§一 分层图「cw_exec_state 执行态簿记」行、§六 表 cw_exec_state 行（改域函数职责描述）← 3.6
- `game_state/README.md` §3.3 域清单：node_screen_refresh 写端申报更新（三写端在产/supply live 接通）、match_facts 域增三字段（域版本 bump）、新增域 round_ledger、非 Field 簿记组 ExecBooks 与局级台账 plane_node_sequences（非域字段，单列工程结构组）← 3.3/3.4/3.5
- `game_state/fields.md`：§3.4.1-3.4.4 写端现状与逐字段规格（渠道/坐标系）、#12-#14/#18 字段规格、ExecBooks 簿记组与 plane_node_sequences 申报（gs_schema 域版本面）← 3.3/3.4/3.5
- `screens/megastar.md`：选中标记宿主改 StrategyState（经 strategy_state_of 通道）← 3.3
- `screens/supply.md`：刷新已用双写段消除 + 「先申报无写端」段终结 + `_pending_chosen_supply` 暂存节改确认即写口径 ← 3.2/3.3
- `screens/encounter.md`：刷新已用读源改容器 ← 3.3
- `screens/invest_strategy.md`：visit 复位集删除、闸 2 改容器计数口径 ← 3.3
- `screens/prep.md`：对账边界节（挂起记账消费段拆除后的口径）← 3.2
- `screens/plane_intel.md`：台账宿主注 ← 3.5
- `screens/battle_wait.md`、`flow/projection_contract.md`：ExecState 符号锚清理 ← 3.6
- 注释历史锚处置（attack [16] 清单）：mandate.py/shop.py/cw_screen_deploy.py/cw_screen_supply_node.py/cw_screen_encounter.py/cw_screen_invest_strategy.py/telemetry/schema.py 内 ExecState 字面注释锚 ← 3.6
