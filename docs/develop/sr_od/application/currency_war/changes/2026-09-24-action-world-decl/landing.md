# 2026-09-24-action-world-decl 落地

## 3.1 声明基建

**范围**：`WorldDecl` dataclass（kernel 新增）+ `LogicOutcome.world_decl` 字段 + 端口 `declare_world` + `SimBackend.advance` 骨架（分派表空实现，case 随后续批增量填充）+ `advance` 对账面骨架。边界：不动任何上报函数、不摘任何装饰器、不改派发点——本阶段产物全部处于「在库未接线」态。
**设计依据**：design.md §2.2 契约 1/2/3；details/world-decl.md §1、§3（对账面）。
**文件面**：`src/sr_od/application/currency_war/kernel/cw_game_state.py`（LogicOutcome）、`kernel/cw_event_hooks.py`（WorldDecl 落位，或独立小模块）、`sim/cw_sim_ports.py`、`sim/cw_sim_backend.py`、`sr-od-test/`（对照测试骨架）。
**依赖**：无。
**优先级建议**：5。
**完成判据**：
- `WorldDecl`/`world_decl` 字段/端口/advance 骨架与 design.md §2.2 契约 1/2/3 逐条一致；
- 端口未装时 `declare_world` no-op（实机零行为变化的机制前提）；
- 全量测试通过（新增字段不破坏既有构造点）。
**验收凭据形式**：测试名（对照测试骨架 + L1 全量）。

## 3.2 主链声明化（出战 / 遭遇 / 结算-节点推进 / 补给）

**范围**：start_battle、pick_encounter、settle_confirm/supply_confirm（`report_node_advance`）四个转移动作全链声明化——上报函数构造声明（`node_advance` 的 `next_screen` 按 kernel 节点日程真值表 + `effective_node_ord` 推导，R1 迁表件随本批，详设 §2 推导规则）并摘装饰器/emit；`report_node_advance` 返回形态 bool → LogicOutcome（两个 bool 消费点随本批改造）；对应动作 op 加喂入行 + round 结果 `data` 携带声明；`advance` 增 `node_advance`/`battle_resolve` 两 case（`on_transition_event` 摘对应 case）。边界：画面 op 派发点**零改动**（交回判断 = terminal 现状）。
**设计依据**：details/world-decl.md §2 表 #1-#4 + `node_advance` 推导规则、§1 签名改形申报、§3 分派表、§4 喂入与多支并喂契约、§5。
**文件面**：`kernel/cw_action_report/start_battle.py`、`kernel/cw_action_report/pick_encounter.py`、`kernel/cw_node_schedule.py`（新增：节点日程真值表自 `sim/cw_sim_plane_schedule.py` 迁入，R1 修法 (a)）、`sim/cw_sim_plane_schedule.py`（退役）、sim 消费点 import 改向（实测 = backend/测试；`kernel/cw_battle_calib.py` 模块注释指针随迁修正）、`kernel/cw_game_state.py`（report_node_advance 签名改形 + 声明构造）、`operations/cw_op/cw_start_battle_action.py`、`cw_pick_encounter_action.py`、`cw_op_settle_confirm.py`、`cw_pick_supply_action.py`（supply_confirm 喂入行真实落点，A2）、`sim/cw_sim_backend.py`、`sr-od-test/`。
**依赖**：3.1。
**优先级建议**：5。
**完成判据**：
- 四动作声明与 details/world-decl.md §2 表 #1-#4 逐位一致（对照测试；局终分支按推导规则确定性锁定：eff 超总长 → next_screen=''）；
- 四动作端到端只有声明一条驱动路径（事件 case 已摘）；
- sim e2e 种子 `container_snapshot` 与改前对拍逐位一致；
- 实机流程测试期望不改全过。
**验收凭据形式**：测试名 + e2e 对拍输出。

## 3.3 选卡族与箱 / 书册卡 / 关店声明化

**范围**：剩余 14 个转移动作（details/world-decl.md §2 表 #5-#18）全链声明化，同 3.2 口径；`advance` 增齐全部分派 case（含 `''` 纯转移分支）。6 个待核 `next_screen` 已由对抗审核定（attack.md §二核定表）并回填对照表，本阶段按回填终值实现即可。边界：overlay 触发面（事实事件/评估器）不动；画面 op 派发点零改动。
**设计依据**：details/world-decl.md §2 表 #5-#18（终值已回填）、§3 分派表（含 `''` 纯转移分支）、§4 喂入落点（投资两屏同指 `cw_pick_invest_action`）、§5。
**文件面**：`kernel/cw_action_report/`（zero_writes/pick_supply/pick_invest_env/pick_invest_strategy/pick_planner/open_bookcard/close_shop）、`operations/cw_op/` 对应动作 op（投资两屏 = `cw_pick_invest_action` 一 op 双 param）、`sim/cw_sim_backend.py`、`sr-od-test/`。
**依赖**：3.2。
**优先级建议**：5。
**完成判据**：
- 18 动作对照测试全绿（按对照表回填终值）；
- 18 动作全部单轨（事件 case 摘净，`on_transition_event` 剩空链或已删）；
- sim e2e 多种子对拍逐位一致；实机流程测试全过。
**验收凭据形式**：测试名 + e2e 对拍输出。

## 3.4 转移事件退役

**范围**：`cw_event_hooks.py` 转移半部删除（机制本体 + 模块头转移描述）；`SimBackend.on_transition_event` 与 `install_backend` 转移 sink 订阅删除；测试仓转移事件断言盘点（平移为声明对照测试或退役）；退役归零探针。事实事件半部与 overlay 评估器**零改动**。
**设计依据**：details/world-decl.md §6 退役清单、§7 验收面。
**文件面**：`kernel/cw_event_hooks.py`、`sim/cw_sim_backend.py`、`sim/cw_sim_ports.py`（如 install 契约涉及）、`sr-od-test/`。
**依赖**：3.3。
**优先级建议**：5。
**完成判据**：
- 退役符号归零（多形态探针，含跨行形态；对 src/ 与 sr-od-test/ 双仓跑）；
- sim e2e 多种子全过（退役后纯声明驱动）；
- L3 全量通过。
**验收凭据形式**：探针输出 + 测试名。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：全部落地阶段。
**优先级建议**：0。
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/currency_war/sim/sim-design.md` §6.3（事件钩子契约：转移半部 → WorldDecl 声明契约与 advance 推进）← 3.4
- `docs/develop/sr_od/application/currency_war/sim/sim-wiring.md`（装配描述涉及转移订阅处）← 3.4
- `docs/develop/sr_od/application/currency_war/architecture.md` 模块表（`cw_sim_plane_schedule.py` 行 → `cw_node_schedule.py`(kernel) 迁移后更新）← 3.2
- `docs/develop/sr_od/application/currency_war/flow/action_ops.md`（动作总册：声明列与喂入契约）← 3.3
- `docs/develop/sr_od/application/currency_war/screens/op-layer.md` §1.2（动作 op 契约：喂入行 + round data 携带声明）← 3.2
- `docs/develop/sr_od/application/currency_war/flow/projection_contract.md` §3.6（两执行面同源：声明消费面——sim 驱动/实机记账）← 3.4
