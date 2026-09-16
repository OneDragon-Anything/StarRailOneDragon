# turnstate-retirement 落地

## 3.1 阶段1：预算披露面独立迁移（先立后破，行为等价批）
**范围**：assembly.py 披露链三函数（`_budget`/`_disclose_budget`/`disclose_budget_at_shop_frame`）迁 `economy_cycle.py` 并合并为 `disclose_budget` + 保留 `disclose_budget_at_shop_frame`；`bridge.decide_prep_screen` 改调披露（替代 assemble 内嵌披露，时点不变）；cw_screen_buy_cards 调用点仅改 import。不含：TurnState 符号删除（阶段2）；不含 assembly.py 剩余部的清理。
**设计依据**：design.md §2.2
**文件面**：`src/.../strategies/impl/mandate_v1/{assembly.py, economy_cycle.py, bridge.py}`、`src/.../operations/cw_screen/cw_screen_buy_cards.py`；测试仓 `test_cw_budget_disclosure.py`、`test_cw_economy.py`
**依赖**：无
**优先级建议**：6
**完成判据**：
- 披露四字段+键戳语义逐字段不变（design.md §2.2 语义清单；载体 = test_cw_budget_disclosure 改造后全绿）
- 行为等价：sim batch 冒烟披露列产出不断流（本批零行为变化，A/B 非裁决仅确认）
- L1 快速集绿；触点文件 ruff 零告警
**验收凭据形式**：test_cw_budget_disclosure 输出 + L1 快速集输出 + sim batch 批头披露列抽样

## 3.2 阶段2：TurnState 层物理删除
**范围**：design.md §2.1 删除面全表（#1-#9）+ §2.3 注释口径修正 + §2.5 测试重构面；grep 清零复核。
**设计依据**：design.md §2.1/§2.3/§2.4/§2.5
**文件面**：src —— `turn_state.py`（删）、`assembly.py`（删余部）、`decision_assembly.py`（删 obs→Snapshot 半部，余量为空则整模块删）、`bridge.py`、`entry.py`、`mandate_v1_strategy.py`、`shop.py`（注释）、`cw_economy.py`（注释）、`cw_exec_state.py`（仅快照拷贝注释三行，与 execstate-dissolution 账本协调同文件在飞面）、`cw_vocab.py`（注释）、`telemetry/schema.py`（注释）、`mandate.py`（注释）、`contracts.py`（注释）；测试仓 —— §2.5 表列五文件
**依赖**：阶段1
**优先级建议**：6
**完成判据**：
- src + sr-od-test 全仓 grep `TurnState|DirectionView|BudgetView|_assemble_turn|snapshot_from_obs|hoard_consumer_domain|decide_from_turn` 零活引用（历史 ADR/decisions//changes/ 记录面豁免；flow/ 正本留末阶段）
- `snapshot_copy` 活消费方不受影响（cw_game_state.py 部署装配链照常，design.md §2.1 注）
- L1 快速集绿 + L3 全量绿（commit 前）；触点文件 ruff 零告警
**验收凭据形式**：grep 输出清单 + L3 全量输出

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：阶段2
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
- flow/projection_contract.md §1 四层表：删「决策视图」行；「快照视图」行产出端表述改「生产端（snapshot_from_obs）已随 turnstate-retirement 退役，契约本体候外溢批裁决」 ← 阶段2
- flow/projection_contract.md §3 不变式5：幂等装配条改写为披露面承诺——披露唯一写点 = `economy_cycle.disclose_budget`（备战决策入口 + 店开帧两调用点），禁决策消费，守卫锁 = test_cw_budget_disclosure ← 阶段2
- flow/projection_contract.md §4.1 时间线：删 assemble 环节，改后流程 = design.md §2 数据流图 ← 阶段2
- flow/projection_contract.md §6 G7 行：结案注（TurnState 层已随 turnstate-retirement 物理删除；hoard/hoard_readable 随 DirectionView 消亡） ← 阶段2
- flow/README.md：L24 备战决策 live 链口径（decide_from_turn → decide_prep_frame，去装配缝环节）、L92 依赖方向段（「装配链由注册桥壳覆写注入」表述删） ← 阶段2
