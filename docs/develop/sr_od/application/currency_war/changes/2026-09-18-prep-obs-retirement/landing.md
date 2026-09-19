# 备战观察帧退役（gs.prep_obs）落地

## 3.1 部署名单换源 + cap 门槛（事故修复）

**范围**：决策帧组装层名单换容器源（entry.py:607-608）、wanted 臂实参换源（entry.py:574）、M7 的 deployed 读点换源（cw_equip_wear_plan.py:182）、cap 键单一源与 10^6 死分支退役（mandate.py `_deploy_plan_inputs`）、显式板满门（`deployed_count_of >= max_units_of`）与 `deploy_cap_full` 拒因落账（cw4_counters 计划级分键、帧级去重）、三锁测试与既有测试适配。**不含**：黑板字段删除（批 5 面）、晶矿路径腾席死码（不动）、停买/线状态判据式变更（只换输入源）。
**设计依据**：`details/cap-fix.md` 全文（总纲 §2 契约 1/2/3）。
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/entry.py`、`.../mandate_v1/mandate.py`、`kernel/cw_equip_wear_plan.py`（:182 读点）、`sr-od-test/test/sr_od/application/currency_war/`（部署相关测试文件）。
**依赖**：无
**优先级建议**：9
**完成判据**：
- 行为对照 `details/cap-fix.md` §方案-1~4：容器 3/3 满帧零拖拽发射、放行 False；未满帧照常部署；`deploy_cap_full` 落账帧级去重。
- 测试三锁（cap-fix.md §测试-1~3）全绿；失读等价性论证核对（cap-fix.md §方案-6）。
- 通用工程门：ruff 改面文件 + 直接受影响测试 + 相关测试全量（sr-od-test 基线 646 passed 不回退），依据项目 AGENTS.md §10。
**验收凭据形式**：新增测试名 + 全量 pytest 输出数字对照。

## 3.2 装备归位

**范围**：容器立 `occupied_equips` 域（键 `'front:1'` 形态）、装备观察写端上报（director 装配点，不改采集层）、M7 与 entry.py:793 帧装配及 entry.py:674 工具臂 owned 快照读源切换、`back_layout_slots` 消费改容器 `back_layout` Field 原值判读。**不含**：黑板字段删除（批 5）、识别 reader 变更。
**设计依据**：`details/obs-retirement.md` §阶段 3.2。
**文件面**：`kernel/cw_game_state.py`（新域）、`kernel/cw_equip_wear_plan.py`、`operations/cw_screen/cw_screen_prep.py`（装备观察写端，director 装配点）、`.../mandate_v1/entry.py`（:674/:793）、`sr-od-test/`（装备计划测试）。
**依赖**：3.1（同文件 entry.py 在飞面）
**优先级建议**：6
**完成判据**：
- 行为对照 obs-retirement.md §阶段 3.2：M7 计划输入全部来自容器（grep 无 obs.owned_equips/occupied_equips 消费）；None→fail 门方向不变。
- 通用工程门：同 3.1（AGENTS.md §10）。
**验收凭据形式**：装备计划测试全绿 + grep 清零输出。

## 3.3 占用改现算

**范围**：晶矿谓词席自由槽切换复用既有读口 `bench_free_slots`（零新立口，entry.py:141-146）。**不含**：双源对拍与前后排占用集（两条腿均为识别面互证，无容器消费——实施期修正，见详设 §阶段 3.3-2）；黑板字段删除（批 5）；投影推进面（批 5 随投影退役）。
**设计依据**：`details/obs-retirement.md` §阶段 3.3。
**文件面**：`.../mandate_v1/entry.py`、`sr-od-test/`。
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 行为对照 obs-retirement.md §阶段 3.3：晶矿谓词席自由槽来自 `bench_free_slots`（含宝箱/典籍占席用例）。
- 通用工程门：同 3.1。
**验收凭据形式**：晶矿谓词测试全绿（含箱/典籍占席用例）。

## 3.4 晶矿立域

**范围**：容器新域 `spheres`（`{color,x,y,r}` 列表）、观察写端上报（防抖留观察链）、晶矿臂读端切换**三处全量**（entry.py:507-509 探针、:492-495 席自由分支发射位、:170-186 `_ore_progress_sig` 签名两分量）、`ClickSpheres` kernel 逻辑态分支（载荷坐标精确摘除）与黑板晶矿腿删除、死码块晶矿/名单读点同批换源（entry.py:524/534-539）。
**设计依据**：`details/obs-retirement.md` §阶段 3.4；总纲 §2 契约 3/4。
**文件面**：`kernel/cw_game_state.py`（新域+读口+`apply_prep_action_logic` ClickSpheres 分支）、`operations/cw_screen/cw_screen_prep.py`（写端+黑板晶矿腿删）、`.../mandate_v1/entry.py`、`sr-od-test/`。
**依赖**：3.1（同文件 entry.py 在飞面）
**优先级建议**：5
**完成判据**：
- 行为对照 obs-retirement.md §阶段 3.4：三处晶矿消费全部来自容器域（grep `obs.spheres` 仅剩观察链写端）；采晶矿后容器按载荷精确摘除；点空由下一入口观察回补（既有机制）；`_ore_progress_sig` 分量为容器派生（防静默退化用例）。
- 通用工程门：同 3.1。
**验收凭据形式**：晶矿域读写单测（摘除/回补/签名退化防护用例）+ 晶矿臂测试全绿。

## 3.5 gs.prep_obs 退役

**范围**：容器 bench kind 区分写端补齐（`bench_view_from_obs` 参数化 `item_kind_by_slot`，观察链用同帧 boxes/tomes 槽号集细分）与 OpenBox/OpenTome 臂分派切换（读 bench kind 首槽，entry.py:458-461）、按字段去向表删除黑板字段与 `gs.prep_obs` 槽、动作后写端拓扑迁移（`_project_prep_obs` 整体删除，`apply_prep_action_logic` 统一调用于 `_act_execute` 执行点 + 写口词表补齐：OpenTome/OpenBookcard 腾席、WearEquip/工具原子装备腿、词表外 AssertionError 防线随迁）、宿主降级（控制信号留 op 局部）、缓存与 light 分支退役、bridge.py:179 obs 传递面收敛、`state_gold_trusted` 残留指引注释同步（cw_observation.py:2177-2184）、符号清零 grep。
**设计依据**：`details/obs-retirement.md` §阶段 3.5（字段去向表为准）。
**文件面**：`kernel/cw_game_state.py`（`bench_view_from_obs` 参数化+legacy tome 配对分支+写口词表补齐+prep_obs 槽删除）、`kernel/cw_prep_actions.py`、`operations/cw_screen/cw_screen_prep.py`、`strategies/impl/mandate_v1/bridge.py`（:179 决策入口 obs 传递面收敛）、`obs/cw_observation.py`（:2177-2184 指引注释）、`kernel/cw_equip_wear_plan.py` 残留、`sr-od-test/`。
**依赖**：3.1、3.2、3.3、3.4
**优先级建议**：4
**完成判据**：
- 行为对照 obs-retirement.md §阶段 3.5-5：符号清零清单（gs.prep_obs / 已删字段 / `_cached_` 系 / 黑板投影分支 / `state_gold_trusted` 指引）grep 为零；OpenBox/OpenTome 臂按 bench kind 分派正确（含 tome kind 写端用例）；全量测试绿。
- 实机一局 smoke（决策迹锚对照，候实机窗口——不阻代码收口、阻迭代收尾）。
- 通用工程门：同 3.1。
**验收凭据形式**：grep 清零输出 + OpenBox/OpenTome 分派用例 + 全量 pytest 数字 + smoke 决策迹对照。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1–3.5 全部。
**优先级建议**：0。
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `flow/projection_contract.md`：黑板帧读写契约退役、写端唯二收敛申报、晶矿域契约 ← 3.4/3.5
- `game_state/fields.md`：新增 occupied_equips/spheres 域、prep_obs 槽与黑板字段删除 ← 3.2/3.4/3.5
- `game_state/action-logic-state.md`：ClickSpheres 容器化、名单投影腿退役、OpenTome/OpenBookcard 容器腾席 ← 3.4/3.5
- `game_state/logic-updates/collect-ore.md`：「容器零写」翻转 ← 3.4
- `game_state/logic-updates/`（deploy/sell/wear 相关篇）：黑板输入源叙述清零 ← 3.1/3.2/3.5
- `flow/session.md`：prep_obs 相关契约行（宿主降级/退役）← 3.5
- `screens/prep.md`：备战环观察分层叙述（heavy/light、缓存、黑板字段）更新 ← 3.5
