# 补给选择(PickSupply)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一;本动作契约正本 = [flow/action_ops.md](../../flow/action_ops.md) §4.5(PickSupply 行)。

## 1. 动作是什么

补给节点弹窗点选一个候选并确认,选中内容(角色/装备)随确认即时入账。词表 = `kernel/cw_vocab.py::CwActionPickSupplyParam`(字段:`idx` = 画面候选下标 0 起(payload 槽 options 列表序)、`reason` = 归因记录字段、`char_name` = 选中列角色名('' = 列无角色/兜底点卡路径)、`norm_item` = 选中列装备归一规范名('' = 未解析;`kernel/cw_events.py::normalize_registry_equip_name` 分层归一现算:精确快道 → containment longest-first → 相似救援唯一命中))。op 载体 = `operations/cw_op/cw_pick_supply_action.py::CwActionPickSupplyOp`(域 env = `OverlayPickExecEnv`;发射位 = `CwScreenSupplyNode._do_action` 经注册表工厂 `action_op_for` 派发)。

## 2. 逻辑态域集

**即时单相一口写**(用户裁定 2026-09-21 = [flow/action_ops.md](../../flow/action_ops.md) §1 增补 2;上报函数 = `kernel/cw_action_report/pick_supply.py::report_action_pick_supply_param`,确认点击后一次调用写全部效果逻辑态,无发射/落地两相、无到账登记、无证据闩):

- **装备腿(确定面)**:`norm_item` 在场 → owned += 归一规范名(`gs.equips` write_logic,账面恒标准名)+ 获得后果链 `kernel/cw_effect_inventory.py::apply_equip_acquire_consequence`(命中后果表送角色腿 → bench + 级联);`norm_item` = '' → 禁猜,equips 值不变翻来源 + `pick_supply_name_unresolved` 留证(fail-closed:错名不入账,观察覆盖自愈);
- **单位腿(确定面)**:`char_name` 在场 → `kernel/cw_effect_inventory.py::grant_bench_unit_cascade`(入席 1★ + 合成级联,与商店购买同语义);
- **内容全未知**(兜底点卡路径,char_name 与 norm_item 双空):bench/equips 值不变翻来源(`write_logic_rand`)+ `pick_supply_content_unresolved` 留证;
- **选择落地 `chosen_supply`**:画面 op `CwScreenSupplyNode` 选卡分支**确认即写 write_logic**(值 = (角色, 装备, 有钻石);渠道签名 family='logic_action'、actor='CwScreenSupplyNode',journal 记录为逻辑源非观察源;兜底点卡/刷新轮不写 = 真选守卫)——动作事实边界例外③([../screens/op-layer.md](../../screens/op-layer.md) §2.2),**非观察写端**;
- 刷新臂不在本动作:刷新圆钮机械点击留守画面 op 留守臂(刷新链 = `CwActionRefreshSupplyParam` 决策建议的执行半,终结形态交回);节点推进 = 确认点击落地即旁调 `kernel/cw_game_state.py::report_node_advance(trigger='supply_confirm')`(kernel 观察态门 = 唯一推进落账门)。

## 3. 确定面转移规则(逐条)

1. 点卡选中:定位点 = `env.target`(决策半从 screen_info/OCR 现算;op 类体内不自算)→ mouse_move + click → 固定等待 0.6s;
2. 确认:`round_by_find_and_click_area`(screenshot, '货币战争-补给', '按钮-确认', success_wait=1.5);
3. **即时自上报**:确认点击后无条件调 `report_action_pick_supply_param`(不判 confirm_result):装备腿 + 单位腿一口写;派发即终结,确认未生效由外循环按当前画面重识别重派(零判效零重试);
4. **推进上报**:`confirm_result.is_success` 门内旁调 `report_node_advance(trigger='supply_confirm')`(is_success 门 = 发出事实门,非判效;重复上报被 kernel 观察态门结构性挡)。

## 4. 随机面

补给候选内容(角色/装备/钻石)= 随机面归观察;上报按确定面即时入账(owned/入席/后果),真值以下一帧观察覆盖为准(两态制,观察赢);内容不可辨 = 受影响域值不变翻来源留证,禁猜、禁伪造确定面。

## 5. 拒绝语义

零验证确认链:确认未落地(overlay 残留)不重试不判效——下一轮外循环重识别重派;定位点缺失由决策半现算面处置(执行面不兜底坐标);归一件名多/零命中与内容双空 = 非拒绝面,按「内容未知/未解析」翻来源留证(上报 applied=True 受理,零效果写)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionPickSupplyParam`;`operations/cw_op/cw_pick_supply_action.py::CwActionPickSupplyOp` / `cw_overlay_pick_env.py::OverlayPickExecEnv`;`kernel/cw_action_report/pick_supply.py::report_action_pick_supply_param`(写语义单点);`kernel/cw_effect_inventory.py::grant_bench_unit_cascade` / `apply_equip_acquire_consequence`;`kernel/cw_events.py::normalize_registry_equip_name`(归一件名现算);`kernel/cw_game_state.py::chosen_supply` / `report_node_advance`;`operations/cw_screen/cw_screen_supply_node.py::CwScreenSupplyNode`(确认即写写点/发射位)。

## 7. 语义验证

行为锁 = `test_cw_supply_pick_immediate_report.py`(即时单相写序)/ `test_cw_pick_channels_t60.py`(分层归一)/ `test_cw_supply_advance_wiring.py`(推进接线)/ `test_cw_obs_arch_event_screens_step3.py`(chosen 确认即写),在册路径 = `sr-od-test/test/sr_od/application/currency_war/`;owned 真值 = 下一帧装备区读数观察覆盖。

## 8. 判例注记(发射期)

补给节点画面期;发射位 = 画面 op act 段经注册表工厂分派。

## 9. 依据

`kernel/cw_action_report/pick_supply.py` 模块头(写序/腿型/留证分型);`operations/cw_op/cw_pick_supply_action.py::CwActionPickSupplyOp` docstring 与 run 体(刷新臂留守/即时上报/推进旁调);[flow/action_ops.md](../../flow/action_ops.md) §4.5(PickSupply 行)与 §1 增补 2;[../fields.md](../fields.md) §3.2.15/§3.2.5(效果腿)/§3.4 头部(chosen 确认即写)/§4「事件选择」补给臂;[../../screens/supply.md](../../screens/supply.md) §4/§6(画面 op 侧契约)。
