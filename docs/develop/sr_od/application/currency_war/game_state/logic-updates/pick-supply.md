# 补给选择(PickSupply)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。事件线 pick 族五篇之一(机械确认链纪律正本 = [flow/action_ops.md](../../flow/action_ops.md) §2.3/§4.4)。

## 1. 动作是什么

补给节点弹窗点选一个候选并确认,选中装备名随确认入账。词表 = `kernel/cw_vocab.py::CwActionPickSupplyParam`(`PickOption` 子类:字段 `idx` = 画面候选下标 0 起、`reason` = 归因记录字段)。op 载体 = `operations/cw_op/cw_overlay_pick_action.py::CwActionPickSupplyOp`(体迁自 `cw_screen_supply_node.py::CwScreenSupplyNode._do_action` 点卡确认半,替身缝 = 方法级桩保留;域 env = `OverlayPickExecEnv`)。

## 2. 逻辑态域集

**容器 GameState 主体零写**——事件线选择非逻辑态通道([../action-logic-state.md](../action-logic-state.md) §6);本族五类中**唯一带确认到账登记面**的一类:

- **确认到账 grant(确定面)**:确认收尾调 `operations/cw_screen/_overlay_confirm.py::register_confirm_arrival`(op='ConfirmSupply',item = 选中装备名)→ `kernel/cw_exec_state.py::apply_confirm_effect` dict `ConfirmSupply` 分支 → owned 库存 +1(`gs.equips` write_logic;实读帧照常覆盖)。登记输入 = `env.picked`('equip' 键);equip 未读到 = 无 item 不登记;
- **选择落地观察写端**:`chosen_supply`(容器 Field,值形 (角色, 装备, 有钻石))= 画面 op `CwScreenSupplyNode` 的观察写入边(`REGISTERED_ACTORS` 在册);
- 刷新臂不在本动作:刷新圆钮机械点击留守画面 op(刷新链 = `PickSupply.refresh` 决策建议的执行半,与遭遇屏 `_try_refresh` 同类);刷新建议词表 = `cw_vocab.py::RefreshSupply`(发射后交回重入型)。

## 3. 确定面转移规则(逐条)

1. 点卡选中:定位点 = `env.target`(决策半从 screen_info/OCR 现算;op 类体内不自算)→ mouse_move + click → 固定等待 0.6s;
2. 确认:`round_by_find_and_click_area`(screenshot, '货币战争-补给', '按钮-确认', success_wait=1.5);
3. **到账登记**(确认收尾写边,随确认链同体):`picked['equip']` 在场 → `register_confirm_arrival(match.session, 'ConfirmSupply', picked['equip'], produced_by='CwScreenSupplyNode')` → `apply_confirm_effect` owned +1;选定事实现役归宿 = journal chosen 域 + 到账登记。

## 4. 随机面

补给候选内容(角色/装备/钻石)= 随机面归观察;owned +1 的登记是粗粒度 expected(单轮即回备战覆盖点实读清账)。

## 5. 拒绝语义

零验证确认链:确认未落地(overlay 残留)不重试不判效——下一轮重入入口观察裁决;定位点缺失由决策半现算面处置(执行面不兜底坐标)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionPickSupplyParam` / `PickOption`;`operations/cw_op/cw_overlay_pick_action.py::CwActionPickSupplyOp` / `OverlayPickExecEnv`;`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival`;`kernel/cw_exec_state.py::apply_confirm_effect`(dict ConfirmSupply 分支);`kernel/cw_game_state.py::chosen_supply` / `REGISTERED_ACTORS`(CwScreenSupplyNode 行);`operations/cw_screen/cw_screen_supply_node.py::CwScreenSupplyNode`(替身缝/写点)。

## 7. 语义验证

到账登记链 = `register_confirm_arrival` 消费 `apply_confirm_effect` dict 分支(推进失败不阻塞执行链);owned 真值 = 下一帧装备区读数观察覆盖。无 M1 投影直锁对象。

## 8. 判例注记(发射期)

补给节点画面期;发射位 = 各 overlay 画面 op act 段经注册表工厂分派。

## 9. 依据

`operations/cw_op/cw_overlay_pick_action.py::CwActionPickSupplyOp` docstring(刷新臂留守裁定/到账登记时序);`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival` docstring(分道申报);[flow/action_ops.md](../../flow/action_ops.md) §4.4(pick 族行);[fields.md](../fields.md) §3.4(事件选择域组); screens/supply.md(画面 op 侧契约)。
