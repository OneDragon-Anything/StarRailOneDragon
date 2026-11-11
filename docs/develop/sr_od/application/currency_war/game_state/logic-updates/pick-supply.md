# 补给选择(PickSupply)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号名引用路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一;本动作契约权威版本 = [flow/action_ops.md](../../flow/action_ops.md) §4.5(PickSupply 行)。

## 1. 动作是什么

补给节点弹窗点选一个候选并确认,选中内容(角色/装备组)随确认即时入账。动作类型(`kernel/cw_vocab.py` 清单中的类)= `CwActionPickSupplyParam`(字段:`idx` = 画面候选下标 0 起(payload 槽 options 列表序)、`reason` = 归因记录字段、`char_name` = 选中列角色名('' = 列无角色/兜底点卡路径)、`norm_item` = 选中列首件装备归一规范名('' = 未解析;`kernel/cw_events.py::normalize_registry_equip_name` 分层归一现算:精确快道 → containment longest-first → 相似救援唯一命中)、`extra_norm_items` = 列内附加装备归一规范名元组(画面 y 序 = norm_item 之后;'' 元素 = 该件归一未解析;归一逐件两段式同 norm_item;kw_only 且不入动作实例键,归因载荷不改变动作身份))。op 载体 = `operations/cw_op/cw_pick_supply_action.py::CwActionPickSupplyOp`(域 env = `OverlayPickExecEnv`;动作发出点 = `CwScreenSupplyNode._do_action` 经注册表工厂 `action_op_for` 派发)。

## 2. 逻辑态域集

**即时单相一口写**(用户裁定 2026-09-21;契约权威版本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.5;上报函数 = `kernel/cw_action_report/pick_supply.py::report_action_pick_supply_param`,确认点击后一次调用写全部效果逻辑态,无「先发出、后落地核对」两相、无到账登记、无证据标志):

- **装备写入(确定面,0..n 件)**:写入集合 = `norm_item` + `extra_norm_items`(选中列首件 + 附加件,主件 → 附加件画面 y 序):非空件逐件 owned += 归一规范名(`gs.equips` write_logic,账面恒标准名)+ 获得后果链 `kernel/cw_effect_inventory.py::apply_equip_acquire_consequence`(命中后果表送角色入席 → bench + 级联);'' 件(归一未解析)逐件禁猜,equips 值不变、来源标记翻转 + `pick_supply_name_unresolved` 保留证据(fail-closed:错名不入账,已解析件照常入账,观察覆盖自愈);`char_name` 非空 ∧ 写入集合全空 = **零装备名分支**:该列零装备名读数(char-only 列 / 件名全失读,读链层面不可分),装备域零写 + 保留证据(日志行 `[cw-pick-supply]` + 返回 reason=`no_equip_column` 载体)、零缺陷——治理旧「主件空 = 未解析」对 char-only 列的伪缺陷归因;失配由 equips 整表观察下一帧暴露(结构性 evidence 记录行待 kernel evidence-only 通道,已登记为待办);
- **角色入席(确定面)**:`char_name` 在场 → `kernel/cw_effect_inventory.py::grant_bench_unit_cascade`(入席 1★ + 合成级联,与商店购买同语义);
- **内容全未知**(兜底点卡路径,char_name/norm_item/extra_norm_items 三载荷全空):bench/equips 值不变、来源标记翻转(`write_logic_rand`)+ `pick_supply_content_unresolved` 保留证据;
- **选择落地 `chosen_supply`**:画面 op `CwScreenSupplyNode` 选卡分支**确认即写 write_logic**(值 = (角色, 装备名列表) 2 元组,OCR 原文画面 y 序,不带钻字段——带钻与否消费侧按 `kernel/cw_obs_core.DIAMOND_EQUIP_NAMES` 名单自列表派生;渠道签名 family='logic_action'、actor='CwScreenSupplyNode',journal 记录为逻辑源非观察源;兜底点卡/刷新轮不写 = 真选守卫)——动作事实边界例外③([../screens/op-layer.md](../../screens/op-layer.md) §2.2),**非观察写入方**;
- 刷新分支不在本动作:刷新圆钮机械点击留在画面 op 内置动作的分支(刷新链 = `CwActionRefreshSupplyParam` 决策建议的执行部分,终结形态=返回主循环);节点推进不在本动作——选卡确认零推进(旧「确认点击落地即上报 supply_confirm」随 2026-10-29 流程模型对齐废止),补给节点由出战动作上报 `report_node_advance(trigger='supply_finish')` 推进(判定语义正本 = [../node-derivation.md](../node-derivation.md))。

## 3. 确定面转移规则(逐条)

1. 点卡选中:定位点 = `env.target`(决策部分从 screen_info/OCR 现算;op 类体内不自算)→ mouse_move + click → 固定等待 0.6s;
2. 确认:`round_by_find_and_click_area`(screenshot, '货币战争-补给', '按钮-确认', success_wait=1.5);
3. **即时自上报**:确认点击后无条件调 `report_action_pick_supply_param`(不判 confirm_result):装备写入 + 角色入席一口写;点击发出后即结束本次访问(结束本次访问),确认未生效由外循环按当前画面重识别重派(零判效——发出后不读屏验证是否生效;零重试);
4. **确认点击后零推进**:本动作无节点推进步骤——补给节点推进归出战动作(选卡确认后回备战,出战点击上报 supply_finish;2026-10-29 流程模型对齐,判定语义正本 = [../node-derivation.md](../node-derivation.md))。

## 4. 随机面

补给候选内容(角色/装备/钻石)= 随机面归观察;上报按确定面即时入账(owned/入席/后果),真值以下一帧观察覆盖为准(两态制,以实际观察为准);内容不可辨 = 受影响域值不变、来源标记翻转并保留证据,禁猜、禁伪造确定面。

## 5. 拒绝语义

零验证确认链(确认后不读屏验证是否生效):确认未落地(overlay 残留)不重试不判效——下一轮外循环重识别重派;定位点缺失由决策部分现算面处置(执行面不兜底坐标);归一件名多/零命中与内容全未知(三载荷全空)= 非拒绝面,按载荷形态分型处置(上报 applied=True 受理):内容全未知 = 受影响域值不变、来源标记翻转并保留证据;写入集合含未解析件 = 该件来源标记翻转并保留证据、已解析件照常入账;char 非空 ∧ 写入集合全空 = 零装备名分支装备域零写零缺陷(§2),非「未解析」归因。

## 6. kernel 符号名引用

`kernel/cw_vocab.py::CwActionPickSupplyParam`;`operations/cw_op/cw_pick_supply_action.py::CwActionPickSupplyOp` / `cw_overlay_pick_env.py::OverlayPickExecEnv`;`kernel/cw_action_report/pick_supply.py::report_action_pick_supply_param`(写语义单点);`kernel/cw_effect_inventory.py::grant_bench_unit_cascade` / `apply_equip_acquire_consequence`;`kernel/cw_events.py::normalize_registry_equip_name`(归一件名现算);`kernel/cw_game_state.py::chosen_supply` / `report_node_advance`;`operations/cw_screen/cw_screen_supply_node.py::CwScreenSupplyNode`(确认即写的写入位置/动作发出点)。

## 7. 语义验证

行为测试 = `test_cw_supply_pick_immediate_report.py`(即时单相写序)/ `test_supply.py`(分层归一)/ `test_cw_supply_advance_wiring.py`(推进接入调用)/ `test_obs_arch_event_screens.py`(chosen 确认即写),已登记路径 = `sr-od-test/test/sr_od/application/currency_war/`;owned 真值 = 下一帧装备区读数观察覆盖。

## 8. 先例注记(动作发出阶段)

补给节点画面期;动作发出点 = 画面 op act 段经注册表工厂分派。

## 9. 依据

`kernel/cw_action_report/pick_supply.py` 模块头(写序/分支类型/保留证据分型);`operations/cw_op/cw_pick_supply_action.py::CwActionPickSupplyOp` docstring 与 run 体(刷新分支留在/即时上报/推进旁调);[flow/action_ops.md](../../flow/action_ops.md) §4.5(PickSupply 行);[../fields.md](../fields.md) §3.2.15/§3.2.5(效果写入)/§3.4 头部(chosen 确认即写)/§4「事件选择」补给分支;[../../screens/supply.md](../../screens/supply.md) §4/§6(画面 op 侧契约)。
