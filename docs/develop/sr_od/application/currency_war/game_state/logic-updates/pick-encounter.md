# 遭遇选择(PickEncounter)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族分篇之一(同族共通面见各篇 §2 开头,机械确认链纪律正本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.5)。

## 1. 动作是什么

遭遇节点弹窗点选一张遭遇卡并确认。词表 = `kernel/cw_vocab.py::CwActionPickEncounterParam`(摊平后叶子类,原 `PickOption` 基类契约逐类重声明:字段 `idx` = 画面候选卡位下标 0 起(左→右)、`reason` = 归因记录字段)。op 载体 = `operations/cw_op/cw_pick_encounter_action.py::CwActionPickEncounterOp`,由画面 op `CwScreenEncounter.act` 经注册表工厂分派,无替身缝;域 env = `OverlayPickExecEnv`。

## 2. 逻辑态域集

写边(动作侧发射即写,依据 = [../../screens/op-layer.md](../../screens/op-layer.md) §2.2 例外三腿②):

- **`chosen_encounter` = 动作侧发射即写**:写端 = `kernel/cw_action_report/pick_encounter.py::report_action_pick_encounter_param`(确认点击后立即写),值组装 = 容器 `encounter` payload 槽 `options[param.idx]`;payload 离屏/越界 = `_emit_defect` 留证不写 fail-closed(`LogicOutcome(applied=False, reason='chosen_unresolved')`);兑现后清 = `kernel/cw_encounter_selection.py::claim_encounter_reward` 达标兑现写 `encounter_reward_claimed` 并清 chosen(单次消费)。字段规格单一源 = [../fields.md](../fields.md) §3.4.1。
- 画面 op 零容器写:容器唯一触点 = 观察侧 `report_screen_encounter_obs` 调用(`CwScreenEncounter.observe`)。
- 刷新不经本动作:刷新 = 终结动作交回外循环(op-layer.md §1.4),重进 = 入口重建,新选项由入口观察现读;原「同访问重决策、发射前覆盖写槽」形态已退役。

## 3. 确定面转移规则(逐条)

1. 点卡选中:卡位中心 = `kernel/cw_obs_core.py::area_center`('遭遇卡-其一'/'遭遇卡-其二';缺失 = 显式 round_fail 交回重读,禁兜底坐标);`idx == 0` 点左卡否则右卡(`safe_click`);
2. 固定等待 0.8s;
3. 确认机械交回 = `round_by_find_and_click_area`(建档「按钮-选择」查找点击,全族统一;area 缺失 = 显式失败交框架轮次,禁兜底坐标);轮次结果(末步 `round_*` 产物)经 `env.round_result` 旁路回传;
4. 发射即写:确认点击后立即 `report_action_pick_encounter_param`(§2)。

`idx` = 策略产候选下标,画面 op 直发策略产实例、流程侧零值域改写(词表/值域守卫在派发前,申报面 = [../../screens/encounter.md](../../screens/encounter.md) §2/§8)。

## 4. 随机面

遭遇卡面内容(难度档/奖励)= 随机面归观察;选择后果不记预期值。

## 5. 拒绝语义

零验证确认链:确认未落地(overlay 残留)不重试不判效——派发即终结,overlay 残留由外循环按当前画面重识别重派(op-layer.md §1.1,修法 = 点击链可靠性);卡位 area 缺失 = 显式 round_fail 零点击(禁兜底坐标,坐标单一真相源 = 建档)。发射即写 = 意图记录,暂态假值窗由重派覆盖自愈 + 兑现后清单次消费双防线(fields.md §3.4.1);report 层拒绝面 = payload 离屏/越界留证不写(`pick_encounter.py::report_action_pick_encounter_param` docstring)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionPickEncounterParam`;`operations/cw_op/cw_pick_encounter_action.py::CwActionPickEncounterOp` / `cw_overlay_pick_env.py::OverlayPickExecEnv`;`kernel/cw_action_report/pick_encounter.py::report_action_pick_encounter_param`;`kernel/cw_encounter_selection.py::claim_encounter_reward`;`operations/cw_screen/_overlay_confirm.py::safe_click`;`kernel/cw_obs_core.py::area_center`;`kernel/cw_game_state.py::chosen_encounter` / `encounter_reward_claimed`;`operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter`。

## 7. 语义验证

写语义单一源 = 具名上报函数(发射即写契约,上报函数族独占容器写,logic-updates/README.md 总则 1);验证锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_game_state_consume.py`(chosen 记录面:真选/离屏/越界,锁清单 = [../../screens/encounter.md](../../screens/encounter.md) §9)。

## 8. 判例注记(发射期)

遭遇节点画面期;发射位 = 画面 op act 段经注册表工厂分派(`cw_action_registry.py` 事件线 pick 族行)。

## 9. 依据

`operations/cw_op/cw_pick_encounter_action.py` 模块头与 `CwActionPickEncounterOp` docstring;`kernel/cw_action_report/pick_encounter.py` 模块头(发射即写契约);`cw_overlay_pick_env.py`(域 env 契约);[flow/action_ops.md](../../flow/action_ops.md) §4.5 PickEncounter 行;[../fields.md](../fields.md) §3.4.1(chosen 发射即写);[../../screens/op-layer.md](../../screens/op-layer.md) §1.4(刷新终结)、§2.2 例外三腿②。
