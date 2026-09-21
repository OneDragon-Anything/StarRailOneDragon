# 事件屏刷新链统一 + 补给选卡即时上报 落地

> 阶段小节 = 账本唯一源（立任务照各节 `dag.py add`，criteria 预注册指向本节）；§12 通用工程门 = 项目提交流程惯例（ruff 改动文件 + 直接受影响测试全绿，不复述）。

## 3.1 补给选卡即时上报

**范围**：`kernel/cw_action_report/pick_supply.py` 单相化（删 `evidence` 参数与 `EVIDENCE_OVERLAY_CLOSED`，一口写 chosen_supply + owned + 单位腿 + 装备后果腿，未解析翻来源留证语义保持）；`CwActionPickSupplyOp.run` 删到账登记调用、确认后立即上报完整结果；`cw_screen_supply_node.py` 删 `_pending_supply`/`_apply_supply_landing`、act 选卡分支派发即 `round_success` 终结、模块头残留符号清理（`set_last_supply_pick`/`_LAST_SUPPLY_PICK` 段）；`_overlay_confirm.register_confirm_arrival` 与 `cw_exec_state.apply_confirm_effect` 的 ConfirmSupply 行退役。**不含**：刷新分支任何改动（3.2 辖内）。
**设计依据**：design.md §2.0B、§2.3（取舍 3/4）
**文件面**：`src/sr_od/application/currency_war/kernel/cw_action_report/pick_supply.py`、`kernel/cw_exec_state.py`、`operations/cw_op/cw_overlay_pick_action.py`、`operations/cw_screen/cw_screen_supply_node.py`、`operations/cw_screen/_overlay_confirm.py`、`sr-od-test/test/sr_od/application/currency_war/` 下受影响测试
**依赖**：无
**优先级建议**：8
**完成判据**：
- 行为对照 design.md §3 验收锚 1（新行为锁：fixture 剧本下确认点击后容器即持完整结果，无落地相补写面）
- `_pending_supply`/`_apply_supply_landing`/`EVIDENCE_OVERLAY_CLOSED`/`ConfirmSupply`（exec_state 分支语义）全仓 grep 零残留
- §12 通用工程门
**验收凭据形式**：新增 pick 即时上报行为锁测试 + `test_cw_supply_advance_wiring.py`/`test_cw_game_state_consume.py` 等受影响测试全绿

## 3.2 补给刷新闸观察化

**范围**：`CwScreenSupplyNodeObs` 加 `refresh_left` + `report_screen_supply_node_obs` 摄入（读缺跳写）；`_read_refresh_anchor` 扩双出 (count, point)；观察 node 同帧读数进 obs；刷新分支闸换源（剩余 ≤0 或 None = 拒绝 → 重调决策按原评分选；放行 = 点钮 + 2s + `round_success` 终结）、删实例旗标与计数写点；`supply_refresh_left` 新字段（无种子）+ `supply_refresh_used` 退役（字段/种子/`flow.py` 刷新闸源/`cw_sim_engine.py` observe 写/`cw_projection_audit.py` 行/`telemetry/schema.py` 值源注释）；`node_screen_refresh` 域版本 2→3。**不含**：遭遇屏（3.3 辖内）、kernel 判据函数签名（design.md §2.0A 保持）。
**设计依据**：design.md §2.0A、§2.1（补给）、§2.2 表、§2.3（取舍 1/2）
**文件面**：`operations/cw_screen/cw_screen_supply_node.py`、`kernel/cw_screen_report/supply_node.py`、`kernel/cw_game_state.py`、`kernel/cw_projection_audit.py`、`strategies/impl/flow.py`、`sim/cw_sim_engine.py`、`telemetry/schema.py`（仅注释）、`sr-od-test/` 受影响测试
**依赖**：3.1（同文件 `cw_screen_supply_node.py` 防冲突串行）
**优先级建议**：7
**完成判据**：
- 行为对照 design.md §3 验收锚 2（行为锁：剩余 1 → 点钮恰一次 + 终结交回；剩余 0/None → 零点击不终结按原评分选）
- `supply_refresh_used` 全仓 grep 零命中（验收锚 4 supply 半；telemetry 历史数据只读注释除外）
- §12 通用工程门
**验收凭据形式**：刷新闸行为锁测试（含 None 拒绝分支）+ sim 补给刷新段测试 + 受影响测试全绿

## 3.3 遭遇刷新链终结化与闸观察化

**范围**：同构 3.2 于遭遇屏——`encounter_refresh_left` 新字段 + `report_screen_encounter_obs` 摄入（`refresh_left` 现状不消费改摄入，读缺跳写）；刷新分支终结化（点钮 + 2s + `round_success` 交回，删 `_try_refresh` 重读半、二次覆盖写、分支重决策、per-visit 位读写）；`encounter_refresh_used`/`encounter_refreshed_in_visit` 退役（字段/种子/审计行/读写点）；`flow.py` 与 `strategies/impl/mandate_v1/bridge.py` 刷新旗标源改读 left；`node_screen_refresh` 域版本随批再 bump。**不含**：遭遇选卡分支的重入裁决与 `chosen_encounter` 写端（动作事实边界现行合法形态，design.md §2.1 明示不动）。
**设计依据**：design.md §2.0A、§2.1（遭遇）、§2.2 表
**文件面**：`operations/cw_screen/cw_screen_encounter.py`、`kernel/cw_screen_report/encounter.py`、`kernel/cw_game_state.py`、`kernel/cw_projection_audit.py`、`strategies/impl/flow.py`、`strategies/impl/mandate_v1/bridge.py`、`sr-od-test/` 受影响测试
**依赖**：3.2（共享 `cw_game_state.py`/`cw_projection_audit.py`/fields 域版本在飞面）
**优先级建议**：6
**完成判据**：
- 行为对照 design.md §3 验收锚 3（行为锁：点钮恰一次 + 访问终结；无同访问 `screenshot()` 重读面；剩余 0/None 按原评分选）
- `encounter_refresh_used`/`encounter_refreshed_in_visit` 全仓 grep 零命中（验收锚 4 收口）
- §12 通用工程门
**验收凭据形式**：遭遇刷新终结行为锁测试 + mandate 遭遇决策受影响测试全绿

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1、3.2、3.3 全部完成。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致（含各正本内 `changes/` 禁引纪律自查）。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `screens/supply.md`：§2 形态声明（派发即终结、零重入裁决）、§3 观察面（补节点条锚定写端 + refresh_left 摄入）、§4 动作面（选卡行上报改即时单相、刷新行改剩余闸）、§5 终结与交回、§6 状态上报面（supply_refresh_used 行退役）、§8 守卫（活锁防线改读缺拒绝语义）、§9 锁面 ← 3.1/3.2
- `screens/encounter.md`：刷新链节（终结化 + 剩余闸 + per-visit 位退役）← 3.3
- `screens/README.md`：§5.5 刷新行（遭遇/补给改终结语义、两相欠账段摘 supply）、§5.3 无关不动 ← 3.2/3.3
- `screens/op-layer.md`：§1.1（投资两屏即时上报条款扩展为事件单选族现役面）、§1.2（欠账标注收窄为 planner/equip）、§2.1（补给确认宿主表述复核）、§2.2（刷新计数出辖节改剩余语义全域）、§3（分型表 supply/encounter 行）← 3.1–3.3
- `flow/action_ops.md`：§4.5（欠账标注摘 supply 行、PickSupply 行描述更新）、§4.6（三刷新动作闸描述改剩余语义）← 3.1–3.3
- `flow/action_exec.md`：§2.1（补给确认行）、§2.2（固定等待族补给刷新 2s 登记）← 3.1/3.2
- `game_state/fields.md`：§3.4.1/§3.4.2 重写（剩余语义字段 + 终结形态 + 待证口径降级注记）← 3.2/3.3
- 兜底：正本更新批内全仓 grep `supply_refresh_used|encounter_refresh_used|encounter_refreshed_in_visit`，命中非历史注释即清 ← 收尾
