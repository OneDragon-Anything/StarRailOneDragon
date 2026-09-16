# turnstate-retirement 落地

## 通用工程门（单一定义；源 = 项目 AGENTS.md「测试规范」10.4 与「提交流程与协作边界」11）
改常量/签名/数据字段先 grep 消费点与测试断言值；只对自己修改的文件跑 `uv run ruff check` 零告警；直接受影响测试 + 全量 `uv run pytest sr-od-test/ -m "not slow and not legacy_baseline"` 通过才提交；`git add` 逐文件点名；提交后 `git show --stat` 复核入库面 = 申报面。各阶段判据以「通用工程门」引用本节，不另行复述。

## 3.1 阶段1：预算披露面原签名搬迁（先立后破，行为等价批）
**范围**：assembly.py 披露链三函数（`_budget`/`_disclose_budget`/`disclose_budget_at_shop_frame`）**原签名逐字迁** `economy_cycle.py`（`_budget` 仍返回 BudgetView、内嵌披露调用不变——存活至阶段2 的 `assemble` 依赖它供 `TurnState.budget` frozen 必填字段，供给链不得断）；assembly.py 改 import；cw_screen_buy_cards 调用点仅改 import 路径。不含：任何符号删除、任何签名/语义变更（合并形态归阶段2）。
**设计依据**：design.md §2.2（阶段1 形态）
**文件面**：`src/.../strategies/impl/mandate_v1/{assembly.py, economy_cycle.py}`、`src/.../operations/cw_screen/cw_screen_buy_cards.py`；测试仓 `test_cw_budget_disclosure.py`（如涉 import 路径）、`test_cw_economy.py`（import 随迁）
**依赖**：无
**优先级建议**：6
**完成判据**：
- 披露四字段+键戳语义逐字段不变（design.md §2.2 语义清单；载体 = test_cw_budget_disclosure 原样全绿——断言载体未改，直接验证搬迁等价）
- `assemble` 供给链不断：test_cw_migration_direction_layer 原样绿
- 行为等价：sim batch 冒烟决策分布无漂移确认（申报：披露面 sim 结构性不可见，披露产出验证归本判据第 1 条与实机 recorder 行）
- L1 快速集绿；触点文件 ruff 零告警
- 通用工程门：本文件「通用工程门」节
**验收凭据形式**：test_cw_budget_disclosure 输出 + L1 快速集输出 + sim batch 批头分布对照

## 3.2 阶段2：TurnState 层物理删除
**范围**：design.md §2.1 删除面全表（#1-#10）+ §2.2 阶段2 形态（`_budget`+`_disclose_budget` 合并为 `disclose_budget -> None`、bridge 调用点改挂原 `_assemble_turn` 调用位）+ §2.3 注释口径修正（含泛化反查收口）+ §2.5 测试重构面。
**设计依据**：design.md §2.1/§2.2/§2.3/§2.4/§2.5
**文件面**：src —— `turn_state.py`（删）、`assembly.py`（删余部）、`adapter.py`（删）、`decision_assembly.py`（删 obs→Snapshot 半部，余量为空则整模块删）、`bridge.py`、`entry.py`、`mandate_v1_strategy.py`、`mandate_state.py`（写端指针注释）、`shop.py`（注释）、`cw_economy.py`（注释）、`cw_screen_buy_cards.py`（注释）、`cw_exec_state.py`（仅快照拷贝注释两处）、`cw_vocab.py`（注释）、`telemetry/schema.py`（注释）、`mandate.py`（注释）、`contracts.py`（注释）、`telemetry/match_archive.py`（仅 §2.3 判别规则注释）；测试仓 —— §2.5 表列六文件
**依赖**：阶段1；execstate-dissolution 对应在飞阶段（同文件在飞面 = `cw_exec_state.py` + `telemetry/schema.py`，防冲突最小前置，两迭代账本对齐后开工）
**优先级建议**：6
**完成判据**：
- src + sr-od-test 全仓 grep `TurnState|DirectionView|BudgetView|_assemble_turn|snapshot_from_obs|hoard_consumer_domain|decide_from_turn` 零活引用（历史 ADR 记录/decisions 遗留/changes/ 豁免；flow/ 正本留末阶段；§2.3 反查样式同步清零）
- `snapshot_copy` 活消费方不受影响（cw_game_state.py 部署装配链照常）；armed 短路帧不披露语义逐位保持（design.md §2.2 落点规则）
- L1 快速集绿 + L3 全量绿（commit 前）；触点文件 ruff 零告警
- 通用工程门：本文件「通用工程门」节
**验收凭据形式**：grep 输出清单 + L3 全量输出 + sim batch 批头分布对照

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：阶段2
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
- flow/projection_contract.md §0 头注定位句：去「`TurnState` 视图」 ← 阶段2
- flow/projection_contract.md §1 四层表：删「决策视图」行；「快照视图」行产出端表述改「生产端（snapshot_from_obs）已随 turnstate-retirement 退役，契约本体候外溢批裁决」 ← 阶段2
- flow/projection_contract.md §3 不变式3：改写为 Snapshot 隔离承诺（TurnState 前半删除；申报 snapshot_copy 现役消费方 = cw_game_state 部署装配链；快照隔离不变式本体不消失） ← 阶段2
- flow/projection_contract.md §3 不变式5：幂等装配条改写为披露面承诺——披露唯一写点 = `economy_cycle.disclose_budget`（备战决策入口原 `_assemble_turn` 调用位 + 店开帧两调用点），禁决策消费，守卫锁 = test_cw_budget_disclosure ← 阶段2
- flow/projection_contract.md §4.1 时间线：删 assemble 环节，补前置发射位与披露落点，改后流程 = design.md §2 数据流图 ← 阶段2
- flow/projection_contract.md §6 G7 行：结案注（TurnState 层已随 turnstate-retirement 物理删除；hoard/hoard_readable 随 DirectionView 消亡） ← 阶段2
- flow/README.md 备战决策 live 链口径（decide_from_turn → decide_prep_frame，去装配缝环节，补前置发射位） ← 阶段2
- flow/README.md 依赖方向段：删「装配链由注册桥壳覆写注入（app 桶）」与「obs→Snapshot 装配半部在 app 桶（decision_assembly）」表述 ← 阶段2
- flow/README.md 篇导读行：projection_contract 条目描述去「TurnState 视图」 ← 阶段2
