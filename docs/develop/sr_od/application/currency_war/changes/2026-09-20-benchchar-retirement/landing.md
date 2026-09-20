# benchchar-retirement 落地

> 阶段小节 = 账本任务唯一源；设计依据 = [design.md](design.md) 对应节。验证命令：`$env:PYTHONPATH="src"; uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`（每阶段）；全量 `uv run pytest sr-od-test/ -m "not slow"`（P7 前）。每阶段独立 commit，逐文件点名 add；设计修订 → 本文件改 → 账本同步。

### 3.1 P0 前置锁

**范围**：写四件现状锁/凭据，不翻任何签名。①装备继承载体锁（merge 装备继承到载体的断言，测试仓现无）；②部署恒 held 锁（占位件部署拒因 item_slot 的回归网）；③开拓者归一现状锁（swap 上报有归一 / deploy_move 上报缺归一的现状行为锁）；④sim 保真对照基线（cw_sim_nodes 丢占位件槽+丢 equips、cw_sim_equips 丢占位件槽的现状记录留档）。
**设计依据**：design.md §3（前置锁）、§2.2 行为变化申报第 2 项。
**文件面**：sr-od-test/（新增测试）；.debug/currency_war/（保真基线记录）。
**依赖**：无。
**优先级建议**：10
**完成判据**：
- 四件锁/凭据齐，当前代码全绿；
- 锁的红绿判定与被锁行为一一对应（去掉被锁行为锁必须红）。
**验收凭据形式**：测试名清单 + sim 基线记录文件。

### 3.2 P1 kernel 计算层容器化

**范围**：`bench_place`/`_merge_bench`/`mutate_bench_deployed` 改吃容器形状；`tracked_books` 双列表迁 §2.3 定稿形状（bench/deployed 两槽位表 + 全部读写端闭合集）；9 个上报函数直用 BenchView/行 Unit；sim 两处 `bench_place` 直调（cw_sim_nodes/cw_sim_opening）同批改；collect_ore 删 `_bench_view_keep_items` 本地补丁；sim 记录保真修复两处随直构化落地（申报第 2 项）；执行链（cw_deploy_move_action）对 tracked 空槽/占用的读数同步切下标派生口径（design §2.2 迁移过渡口径，行为等价）。单提交单元。
**设计依据**：design.md §2.1、§2.3、§2.4（重写保留族）、§3 不变量 1-4 与前置锁节。
**文件面**：kernel/cw_game_state.py、kernel/cw_merge_simulate.py、kernel/cw_exec_state.py、kernel/cw_action_report/*、sim/cw_sim_nodes.py、sim/cw_sim_opening.py、operations/cw_op/cw_buy_card_action.py、operations/cw_op/cw_deploy_move_action.py（仅读数口径段）、策略 mandate_v1 的 tracked 同步点、tracked 读写端闭合集（§2.3 清单）、对应测试。
**依赖**：P0。
**优先级建议**：9
**完成判据**：
- §3 不变量 1-4 锁全绿（P0 锁作哨兵）；
- tracked 双列表新形状落地，读写端无 BenchChar 中间形；执行链读数无旧字段 getattr 柔取；
- sim 保真修复对照凭据附提交说明。
**验收凭据形式**：L1 全绿 + 保真对照记录 + 提交说明。

### 3.3 P2 落位载荷与执行面

**范围**：`CwActionDeployMoveParam` 增 `to_slot`；两个发射位（mandate 发射点/cw_loop 出战链）to_slot 透传接线——透传 kernel 指派现成第三元槽位，零行为变化（落位策略重写归 P3，本阶段不动发射逻辑）；执行器删「执行坐标边现读首空位」，按 (to_row, to_slot) 坐标翻译拖点；拖拽语义落码（目标槽有人 = 交换交互，禁静默换槽，占位非异常）；容器写侧落位宿主（cw_action_report/deploy_move.py 的 deployed_place 首空段）改按载荷 (to_row, to_slot) 落位，与执行拖点同源；sim 动作应用（cw_sim_actions）同规则建模（空=放置/占=交换）；`CwActionSwapDeployParam` 契约核对保持。
**设计依据**：design.md §2.2（载荷契约、拖拽语义、迁移过渡口径、sim 语义）。
**文件面**：kernel/cw_vocab.py、统一动作工厂与部署执行 op（deploy move 执行链）、kernel/cw_action_report/deploy_move.py（容器写侧落位宿主段）、sim/cw_sim_actions.py（sim 应用宿主）、operations/cw_loop.py 与 strategies/impl/mandate_v1/mandate.py（仅 to_slot 透传接线两处）、对应测试。
**依赖**：P1。
**优先级建议**：8
**完成判据**：
- 执行链与容器写侧均无首空位现读；载荷缺 to_slot 无编译面（发射位已接线）；
- 容器写侧落位与执行拖点同源，无分叉（锁）；
- sim 对「目标槽有人」的动作按交换语义应用（锁）；
- §3 不变量 2 部署恒 held 锁绿。
**验收凭据形式**：测试名（交换语义锁/执行坐标锁）+ L1 全绿。

### 3.4 P3 策略落位实现与出战链

**范围**：mandate_v1 内聚落位策略（人选 + 排 = comp 站位覆盖 > 注册表派生 > back 兜底 + 前排保证随迁 + 槽位选择）；`select_deployments`/`select_deployments_reasoned` 迁入策略层，kernel 版退役；出战链 `_battle_chain_deploy_moves` 改调策略层部署计划单一源；开拓者形态归一统一归口（§3.5 申报的缺陷修复）；行为变化申报第 1 项落地：sim A/B 对照 + 注册表前排角色排前排的新锁。
**设计依据**：design.md §2.2（落位策略、选人迁策略、出战链、行为变化申报第 1 项）、§3 不变量 5。
**文件面**：strategies/impl/mandate_v1/*（mandate/shop/_deploy_plan_inputs 链）、kernel/cw_deploy_logic.py（select/assign 迁出与残余）、operations/cw_loop.py（出战链）、kernel/cw_action_report/deploy_move.py 与 swap_deploy.py（归一口）、对应测试。
**依赖**：P2。
**优先级建议**：8
**完成判据**：
- mandate 落位策略为唯一落位决定点；kernel/执行链零落位决定（grep 无 assign/empty_deploy/首空位现读）；
- 开拓者归一口唯一（deploy_move 上报与 swap 同源）；
- sim A/B 对照报告（落位改前/改后指标）+ 新锁绿。
**验收凭据形式**：A/B 对照报告 + 测试名 + L1 全绿。

### 3.5 P4 策略与 kernel 消费面容器形状

**范围**：§4 外围消费面逐域迁移容器形状（含字段映射约定 §2.4）：策略判定域（sell_gate/predicates/criteria/mandate 判定残余/cw_deploy_logic 判定残余）、知识域（cw_comps/cw_economy/cw_intention/cw_events/cw_system_cards/cw_board_by_row/cw_bench_equips/cw_equip_wear_plan/cw_effect_inventory）、外围域（cw_line_switch/cw_launch_admission/cw_performance/cw_battle_calib/economy_cycle/cw_screen_prep/cw_shop_action_ops/cw_screen_planner/shop.py/criteria/sell.py/statefn/predicates.py）。`board_by_row`/`board_unique_key` 容器原生重写落此。
**设计依据**：design.md §2.1（faction 三类口径）、§2.4（映射约定）、§4（面清单）。
**文件面**：§4 外围消费面清单所列文件 + 对应测试。
**依赖**：P3。
**优先级建议**：7
**完成判据**：
- 清单域内无 BenchChar 中间形读取（逐域 grep）；
- faction 三类消费口径各有锁；
- §3 全部不变量锁绿。
**验收凭据形式**：逐域 grep 归零记录 + 测试名 + L1 全绿。

**裁定追加（2026-09-20 用户裁定 B，行为变化申报第 3 项）**：三处席空数读数（cw_line_switch.e_rounds 买刷截断 / proof c_sat 席位压力项 / economy_cycle `_scan_shop_buy_accounts`）从定长 9 基线统一改吃 `bench_free_slots`（capacity 跟随单一源）；新增三处消费行为锁（capacity=8 帧断言读数跟随）；三处 ⚠️ 挂账注释收敛为既定语义说明。落地批 = 追加任务（账本），非本节原范围。

### 3.6 P5 sim 帧退役与测试种子层

**范围**：`CwSimFrame`/`synthesize_from_game_state`/`feed_sim_truth` 退役；测试仓 builder 直写容器域（§2.5 载体）；种子 builder 含商店屏态域字段（承接现 synthesize_from_game_state 的 shop_open/shop_empty_off_screen 分支语义，字段语义在 builder 处声明）；种子重写（CwSimFrame 87 处/18 文件 + `BenchChar(` 直造 116 处/32 文件，名字表达纪律）；M1 投影锁语义逐字节保形；死函数删（economy_score/star_weighted_copies/state_equips_multiset）。
**设计依据**：design.md §2.4（sim 帧通道、死函数）、§2.5。
**文件面**：kernel/cw_vocab.py、kernel/cw_game_state.py（合成口段）、测试仓 `_cw_helpers` 与种子文件、对应 sim 测试。
**依赖**：P4。
**优先级建议**：7
**完成判据**：
- M1 投影锁逐字节保形（改前/改后投影输出 diff 为空）；
- 测试仓无 `CwSimFrame(`/`BenchChar(` 直造（grep 归零）；
- 种子全部经注册表可派生名字（抽查无注册表外值依赖，未知名除外）。
**验收凭据形式**：投影 diff 记录 + grep 归零记录 + L1 全绿。

### 3.7 P6 观察链直产

**范围**：`cw_identity_obs` SIFT 产形段直产 BenchView；`battle_prep_recognizer` extras_doc 声明的形状同步；observe spec 门直产 BenchView（`bench_view_from_obs`/`item_kind_by_slot` 随中间形消失）。
**设计依据**：design.md §2.1、§2.4。
**文件面**：obs/cw_identity_obs.py、obs/recognizers/battle_prep_recognizer.py、observe spec 门、对应测试。
**依赖**：P5。
**优先级建议**：6
**完成判据**：观察链无 BenchChar 中间形；extras_doc 与实际产出形状一致；识别域商店屏态语义不变（经 P5 种子域字段表达）。
**验收凭据形式**：测试名 + L1 全绿。

### 3.8 P7 收尾退役

**范围**：残余消费面（flow.py、entry.py、telemetry/schema.py、cw_loop 残余、sim/cw_sim_pool 等）；删除 §2.4 删除族全部符号与引用；全量 grep 归零（词表 = §4）；L3 全量；cw_registry.py 占位注释同步。
**设计依据**：design.md §2.4、§4。
**文件面**：§4 词表命中残余文件；正本 cw_registry.py 注释。
**依赖**：P6。
**优先级建议**：6
**完成判据**：
- §4 词表在 src+测试仓 grep 归零（保留重写族按新签名命中除外，逐一核对）；
- L3 全量绿。
**验收凭据形式**：grep 归零记录 + L3 通过记录。

### 3.9 P8 正本更新

**范围**：按正本更新清单逐条更新；清单清零 = 迭代收尾。
**设计依据**：本文件「正本更新清单」。
**文件面**：清单所列正本文档。
**依赖**：P7。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- strategy-docs/fields.md：§3.2.5（bench/deployed 域形状）← P1
- strategy-docs/fields.md：§4.2（tracked_books 形状）← P1
- strategy-docs/fields.md：§9（帧↔容器映射契约；P5 后帧已退役，节随删或改写为容器直产口径）← P5
- strategy-docs/action-logic-state.md：动作词表落位字段（to_slot）与出战链计划口径 ← P2/P3
- strategy-docs/projection_contract.md：状态面板读写契约中 BenchChar 形残留 ← P5
- data/cw_registry.py：占位件/形状相关注释 ← P7
