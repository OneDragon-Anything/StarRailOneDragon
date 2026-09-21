# 事件屏刷新链统一 + 补给选卡即时上报 落地

> 阶段小节 = 账本唯一源（立任务照各节 `dag.py add`，criteria 预注册指向本节）。
> **通用工程门**（定义 = 本节；源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节）：ruff 改动文件 + 直接受影响测试全绿。

## 3.1 补给选卡即时上报

**范围**：`kernel/cw_action_report/pick_supply.py` 单相化（删 `evidence` 参数与本文件 `EVIDENCE_OVERLAY_CLOSED` 常量，一口写 owned（规范名）+ 单位腿 + 装备后果腿，⓪双空兜底点卡「内容全未知」分支逐位保持，未解析翻来源留证语义保持；**chosen_supply 不进 report**，留守画面 op 选卡分支确认即写——`op-layer.md` §2.2 硬规则零改动）；`kernel/cw_events.py` 增装备注册表级**分层归一**入口（精确快道 → containment longest-first → 相似救援 LCS ≥0.75 唯一命中，多/零命中 = '' 禁猜；层级与键集歧义分析 = design §2.0B；planner 银狼锚 `normalize_equip_name` 语义不动，两入口分立；**param 零扩字段**——char_name/norm_item 即 report 全部输入）；`CwActionPickSupplyOp.run` 删到账登记调用、确认后立即上报完整结果；`cw_screen_supply_node.py` 选卡分支 norm_item 组装点换分层归一、删 `_pending_supply`/`_apply_supply_landing`、act 选卡分支派发即 `round_success` 终结、`set_last_supply_pick`/`_LAST_SUPPLY_PICK` **本文件全部注释引用**清理（模块头 + `_do_action` 行内；**不含** telemetry/schema.py 同款注释——3.2 文件面顺手清）；`_overlay_confirm.register_confirm_arrival` 与 `cw_exec_state.apply_confirm_effect` 的 ConfirmSupply 行退役；`picked` 快照保留组装（消费面声明为零，选定事实现场载荷）。**不含**：刷新分支任何改动（3.2 辖内）。
**设计依据**：design.md §2.0B、§2.1（补给 picked 段）、§2.3（取舍 3/4/6）
**文件面**：`src/sr_od/application/currency_war/kernel/cw_action_report/pick_supply.py`、`kernel/cw_events.py`、`kernel/cw_exec_state.py`、`operations/cw_op/cw_overlay_pick_action.py`、`operations/cw_screen/cw_screen_supply_node.py`、`operations/cw_screen/_overlay_confirm.py`、`sr-od-test/test/sr_od/application/currency_war/` 下受影响测试
**依赖**：无
**优先级建议**：8
**完成判据**：
- 行为对照 design.md §3 验收锚 1（新行为锁：fixture 剧本下确认点击后容器即持 owned+单位腿+后果腿；`chosen_supply` 三元组在派发前已写；画面 op 无落地相补写面；分层归一行为锁 = 特权/后缀族/互撞族完美 OCR 恒命中 + OCR 形变救援 + 多命中拒识返回 ''）
- grep 零残留（范围 = src + sr-od-test）：`kernel/cw_action_report/pick_supply.py` 定义的 `EVIDENCE_OVERLAY_CLOSED` 及其 supply 链导入点（`cw_screen_supply_node.py`、`test_cw_pick_channels_t60.py` 的 `SUPPLY_EVIDENCE` 面）、`_pending_supply`、`_apply_supply_landing`、`set_last_supply_pick`/`_LAST_SUPPLY_PICK`（豁免 = 无）；ConfirmSupply 语义残留 = `cw_exec_state`/`_overlay_confirm` 两分支 + pick op 登记调用（豁免 = telemetry 历史数据只读注释；**pick_equip/pick_planner 各自同名 `EVIDENCE_OVERLAY_CLOSED` 常量不在辖内**）
- 通用工程门
**验收凭据形式**：新增 pick 即时上报行为锁测试 + 分层归一行为锁测试（互撞族/形变/多命中三型用例）+ `test_cw_supply_advance_wiring.py`/`test_cw_game_state_consume.py` 等受影响测试全绿

## 3.2 补给刷新闸观察化

**范围**：`CwScreenSupplyNodeObs` 加 `refresh_left` + `report_screen_supply_node_obs` 摄入（读缺跳写）；`_read_refresh_anchor` 扩双出 (count, point)；观察 node 同帧读数进 obs；刷新分支闸换源（剩余 ≤0 或 None = 拒绝 → 重调决策按原评分选；放行 = 点钮 + 2s + `round_success` 终结）、删实例旗标与计数写点；选定快照 `picked['refreshed']` 布尔键改 `picked['refresh_left']`（值 = 容器 left 现值，可 None）；`supply_refresh_left` 新字段（无种子）+ `supply_refresh_used` 退役（字段/种子/`flow.py` 刷新闸源/`cw_sim_engine.py` observe 写改 left：节点入口先写初始 left=1、刷新 left−1 ≥0 截断/`cw_projection_audit.py` 行/`telemetry/schema.py` 注释语义改写——supply_pick 快照键变化 + :529 附近 `set_last_supply_pick` 陈旧注释顺手清）；`node_screen_refresh` 域版本 2→3。**不含**：遭遇屏（3.3 辖内）、kernel 判据函数签名（design.md §2.0A 保持）。
**设计依据**：design.md §2.0A、§2.1（补给）、§2.2 表、§2.3（取舍 1/2）
**文件面**：`operations/cw_screen/cw_screen_supply_node.py`、`kernel/cw_screen_report/supply_node.py`、`kernel/cw_game_state.py`、`kernel/cw_projection_audit.py`、`strategies/impl/flow.py`、`sim/cw_sim_engine.py`、`telemetry/schema.py`（仅注释）、`sr-od-test/` 受影响测试
**依赖**：3.1（同文件 `cw_screen_supply_node.py` 防冲突串行）
**优先级建议**：7
**完成判据**：
- 行为对照 design.md §3 验收锚 2（行为锁：剩余 1 → 点钮恰一次 + 终结交回；剩余 0/None → 零点击不终结按原评分选）
- grep 零命中（范围 = src + sr-od-test；豁免 = telemetry 历史数据只读注释）：`supply_refresh_used`（验收锚 4 supply 半）
- §3 验收锚 1 之选定快照：新行携 `refresh_left` 快照（行为锁断言 picked 键）
- 通用工程门
**验收凭据形式**：刷新闸行为锁测试（含 None 拒绝分支）+ sim 补给刷新段测试（初始 left=1 与 left−1 截断）+ 受影响测试全绿

## 3.3 遭遇链统一：刷新终结化 + 选卡派发即终结 + 奖励兑现回调

> 2026-09-21 用户裁定扩围：原 3.3（刷新链）之上追加三项——入口 2s 稳定期删除、选卡派发即终结（chosen 迁动作侧）、结算奖励兑现回调。原「不含：遭遇选卡分支的重入裁决与 chosen_encounter 写端」条款随之撤销。

**范围**（四块）：

- **刷新链终结化与闸观察化**（原 3.3）：`encounter_refresh_left` 新字段 + `report_screen_encounter_obs` 摄入（**摄入序照先例：options 空整函数早退不写，含 left**；读缺跳写）；刷新分支终结化（点钮 + 2s + `round_success` 交回，删 `_try_refresh` 重读半、二次覆盖写、分支重决策、per-visit 位读写）；`encounter_refresh_used`/`encounter_refreshed_in_visit` 退役（字段/种子/审计行/读写点）；`flow.py` 与 `strategies/impl/mandate_v1/bridge.py` 刷新旗标源改读 left；`node_screen_refresh` 域版本随批再 bump。
- **入口稳定期删除**（用户裁定）：观察 node 删 2s sleep + 重截，门命中即用 node runner 帧一次读（候选 + 剩余次数同帧同源不变）；`research/screen_flow_timing.md` #23 口径注同步改（用户裁定 supersession 旧「等 2s 才稳定」口径）。
- **选卡派发即终结 + chosen 迁动作侧**（用户裁定，投资两屏/补给 3.1 同形态）：删重入裁决（`_confirm_pending`/锚在重走/`_record_chosen`）；act 决策后派发 `CwActionPickEncounterOp` → `round_success` 终结交回外循环；`report_action_pick_encounter_param` 升格容器写（点完确认立即写 `gs.chosen_encounter = (难度, 奖励文本)`；值组装 = `gs.encounter` payload 槽 `options[param.idx]`，**param 零扩字段**；payload 离屏/idx 越界 = 缺陷留证不写，None 保持「无记录」，fail-closed）。**模块归宿 = 迁具名新模块 `kernel/cw_action_report/pick_encounter.py`**（照 pick_supply 先例,文件名 = 动作 snake;zero_writes 删函数 + 迁出注记）。**空候选分支**：`options` 空 = 零点击 `round_success` 终结交回外循环重进重读（现状盲选 idx0 派发确认一并退役，attack3 X2）。
- **结算奖励兑现回调**（用户裁定，新机制；attack3 X3/X4/X7 + R1 处置后形态，T-7 r2）：`CwOpSettleConfirm` 确认点击后（推进上报前，语义顺序）调 kernel 回调 `kernel/cw_encounter_selection.py::claim_encounter_reward`（纯容器读零读屏）——判遭遇 = 双证（`node_kind_of(gs) == 'encounter'` 读 `gs.node` 镜像英文 token ∧ `gs.settlement_ring` 尾行 `node_type == '遭遇'`；原「结算行 note」载体不可实现——note 仅落 journal 行，R1 定谳，落地取 ring 尾行形态）；达标 = **单判** `progress_delta > 0`（killed 不入判据：派生重叠 + hp 兜底腿遭遇局未证）；`progress_delta is None` = 删失不兑现；`chosen_encounter` None = 不兑现。假阴性申报（R4）：双证存在同源面，镜像缺失遭遇局 ring 行落 `'普通战斗'` → fail-closed 漏兑现（方向安全，归观察可靠性治理）。兑现 = 写 `encounter_reward_claimed`（新顶层字段 `tuple[int, str] | None`；写通道 `write_logic`，actor='CwOpSettleConfirm'；审计行新增；遥测 schema 接线候批申报；sim 零写端申报）**并随即清 `chosen_encounter`（同族 sig actor='CwOpSettleConfirm' 的 `write_logic(None)`，单次消费：镜像残留/驻留重入/结算覆盖陈旧三面一并收口，天然幂等零闩）**。**数值不直写**：金币真值 = `settle_truth` 结算读数、随机4费 = bench 观察（观察赢防双源），兑现记录 = 语义账面（**现役消费面 = 审计投影唯一；策略器收益对账读端挂账,外溢候选登记,R5**）。残余申报：本场结算覆盖失败 ∧ 上一场同为遭遇 ∧ 本场 chosen 已写的低频组合窗仍可能误记（语义账面脏行非资金操作;采 ring 尾行腿后该窗大半收口——ring 写点在结算覆盖 try 块外）。

**设计依据**：design.md §2.0A、§2.1（遭遇）、§2.2 表、§2.4（扩围增补）
**文件面**：`operations/cw_screen/cw_screen_encounter.py`、`operations/cw_op/cw_op_settle_confirm.py`、`operations/cw_op/cw_overlay_pick_action.py`、`kernel/cw_screen_report/encounter.py`、`kernel/cw_action_report/zero_writes.py`、`kernel/cw_action_report/pick_encounter.py`（新建具名模块,attack3 X6 落地形态;文件名 = 动作 snake 对齐包规约）、`kernel/cw_encounter_selection.py`、`kernel/cw_game_state.py`、`kernel/cw_projection_audit.py`、`strategies/impl/flow.py`、`strategies/impl/mandate_v1/bridge.py`、`docs/game/currency_war/research/screen_flow_timing.md`（仅 #23 口径注）、`sr-od-test/` 受影响测试
**依赖**：3.2（共享 `cw_game_state.py`/`cw_projection_audit.py`/fields 域版本在飞面）
**优先级建议**：6
**完成判据**：
- 行为对照 design.md §3 验收锚 3（行为锁：点钮恰一次 + 访问终结，无同访问 `screenshot()` 重读面；剩余 0/None 按原评分选；**候选读缺 = 零点击终结交回，零派发**；选卡派发即 `round_success` 零重入裁决轮；确认点击后容器即持 `chosen_encounter`；payload 离屏/越界缺陷留证不写；兑现三型 = 达标双证兑现且 `chosen_encounter` 随即清 / 未达标不写不清 / 删失或无 chosen 不写不清；重入轮二触发不重兑现）
- grep 零命中（范围 = src + sr-od-test；豁免 = telemetry 历史数据只读注释）：`encounter_refresh_used`/`encounter_refreshed_in_visit`（验收锚 4 收口）+ `_record_chosen`/`_confirm_pending`/`_try_refresh`（遭遇域）+ `zero_writes.py` 内 `pick_encounter` 迁出残留
- 文档判据（attack3 X9）：`research/screen_flow_timing.md` #23 注已带 supersession 标记（用户裁定 2026-09-21）
- 通用工程门
**验收凭据形式**：遭遇刷新终结行为锁 + 选卡即时上报行为锁 + 空候选零点击行为锁 + 奖励兑现回调行为锁（达标/未达标/删失/重入幂等四型）+ mandate 遭遇决策受影响测试全绿

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1、3.2、3.3 全部完成。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致（含各正本内 `changes/` 禁引纪律自查）。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `screens/supply.md`：§2 形态声明（派发即终结、零重入裁决）、§3 观察面（补节点条锚定写端 + refresh_left 摄入）、§4 动作面（选卡行上报改即时单相、刷新行改剩余闸）、§5 终结与交回、§6 状态上报面（ConfirmSupply 退役行 + chosen_supply 确认即写口径复核不变）、§8 守卫（活锁防线改读缺拒绝语义）、§9 锁面 ← 3.1/3.2
- `screens/encounter.md`：全文重写（入口稳定期删除、刷新链终结化 + 剩余闸、选卡派发即终结零重入裁决、chosen_encounter 迁动作侧、结算奖励兑现回调、per-visit 位退役）← 3.3
- `screens/README.md`：§5.5 刷新行（遭遇改终结语义、两相欠账段摘 supply）、§6 终结总表「单选族确认离开」行（补给改派发即终结）← 3.2/3.3
- `screens/op-layer.md`：§1.1（投资两屏即时上报条款扩展为事件单选族现役面 + 遭遇选卡迁派发即终结；重入裁决「仅限未迁移屏」清单收敛）、§1.2（欠账标注收窄为 planner/equip）、§1.4（遭遇刷新欠账标注摘除；chosen_* 动作事实边界条款遭遇例外改判——用户裁定迁移）、§2.1（补给确认宿主表述复核 + pick_encounter 零写例外撤销）、§2.2（刷新计数出辖节改剩余语义全域；动作事实边界条款遭遇腿迁移）、§3（分型表 supply/encounter 行）← 3.1–3.3
- `flow/action_ops.md`：§4.5（欠账标注摘 supply 行、PickSupply/PickEncounter 行描述更新）、§4.6（三刷新动作闸描述改剩余语义）、§2.2 固定等待族补遭遇/补给刷新 2s 登记（时序 #19/#23）← 3.1–3.3
- `flow/action_exec.md`：§2.1（补给确认行复核）← 3.1
- `game_state/fields.md`：§3.4.1/§3.4.2 重写（剩余语义字段 + 终结形态 + 待证口径降级注记 + `encounter_reward_claimed` 兑现记录字段节 + chosen_encounter 写端迁动作侧注记）；**§3.4 节点事件屏头部 chosen_\* 通用硬规则条款（:718-721 附近）补遭遇例外改判注**（遭遇迁动作侧发射即写，先例写法 = 投资域收窄条款形态）；**§4「事件选择」节（:1051-1060 附近）遭遇行改写**（发射即写、值组装 = payload 槽、盲选/越界不写、兑现后清）← 3.2/3.3（attack3 X5）
- 兜底：正本更新批内按验收锚 4 口径全仓 grep 三退役符号，命中非历史注释即清 ← 收尾
